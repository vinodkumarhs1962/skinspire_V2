# app/services/billing_service.py

import uuid
import logging
import json
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, text, or_, case
from sqlalchemy.sql.expression import select, update
# from weasyprint import HTML, CSS

# Flask imports
from flask import current_app, url_for, render_template

# ReportLab imports for PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# Email and messaging imports
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import requests  # For WhatsApp API calls

from app.models.master import Hospital, Package, Service, Medicine, ChartOfAccounts, Patient, Branch
from app.models.transaction import (
    InvoiceHeader, InvoiceLineItem, PaymentDetail, GLTransaction, GLEntry, GSTLedger,
    Inventory, PatientAdvancePayment, AdvanceAdjustment
)
from app.models.config import InvoiceSequence
from app.services.gl_service import (
    create_invoice_gl_entries,
    create_payment_gl_entries,
    create_refund_gl_entries,
    process_void_invoice_gl_entries
)
from app.services.inventory_service import update_inventory_for_invoice
from app.services.database_service import get_db_session, get_entity_dict, get_detached_copy
# from app.services.subledger_service import create_ar_subledger_entry

# from app.utils.pdf_utils import generate_invoice_pdf

# Phase 3: Invoice split configuration
from app.config.modules.patient_invoice_config import (
    INVOICE_SPLIT_CONFIGS,
    get_invoice_split_config,
    categorize_line_item
)
from app.config.core_definitions import InvoiceSplitCategory
# from app.utils.file_utils import store_temporary_file
# from app.services.email_service import send_email_with_attachment
# from app.services.whatsapp_service import send_whatsapp_message

# Configure logger
logger = logging.getLogger(__name__)

def create_invoice(
    hospital_id: uuid.UUID,
    branch_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_date: datetime,
    line_items: List[Dict],
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    # Add comprehensive logging at the entry point
    logger.info("=" * 80)
    logger.info("INVOICE CREATION REQUEST RECEIVED")
    logger.info("=" * 80)
    logger.info(f"Hospital ID: {hospital_id}")
    logger.info(f"Branch ID: {branch_id}")
    logger.info(f"Patient ID: {patient_id}")
    logger.info(f"Invoice Date: {invoice_date}")
    logger.info(f"Number of Line Items: {len(line_items)}")
    logger.info(f"Current User ID: {current_user_id}")

    # Validate line items
    if not line_items or len(line_items) == 0:
        logger.error("❌ No line items provided!")
        raise ValueError("Please add at least one line item before creating the invoice")

    # Log line items details
    for idx, item in enumerate(line_items, 1):
        logger.info(f"Line Item {idx}: Type={item.get('item_type')}, ID={item.get('item_id')}, Name={item.get('item_name')}")

    """
    Create invoices based on line items and business rules
    
    This function processes line items and creates appropriate invoices:
    1. For Product/Service/Misc: Creates separate GST and non-GST invoices
    2. For Prescription: Creates either a drug invoice or consolidates under Doctor's Examination
    
    Args:
        hospital_id: Hospital UUID
        branch_id: Branch UUID
        patient_id: Patient UUID
        invoice_date: Invoice date
        line_items: List of line items with details
        notes: Optional notes
        current_user_id: ID of the user creating the invoice
        session: Database session (optional)
        
    Returns:
        Dictionary containing created invoice details
    """
    if session is not None:
        return _create_invoice(
            session, hospital_id, branch_id, patient_id, invoice_date,
            line_items, notes, current_user_id
        )
    
    with get_db_session() as new_session:
        return _create_invoice(
            new_session, hospital_id, branch_id, patient_id, invoice_date,
            line_items, notes, current_user_id
        )

def _create_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    branch_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_date: datetime,
    line_items: List[Dict],
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Create invoices with Phase 3: 4-way split for tax compliance

    This implementation splits a single patient transaction into 4 separate auditable tax documents:
    1. Service & Package Invoice
    2. GST Medicines/Products Invoice
    3. GST Exempt Medicines/Products Invoice
    4. Prescription/Composite Invoice

    All invoices are linked via parent_transaction_id for tracking
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting Phase 3: 4-way invoice creation")
        logger.info("=" * 80)
        logger.info(f"Hospital ID: {hospital_id}")
        logger.info(f"Branch ID: {branch_id}")
        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Invoice Date: {invoice_date}")
        logger.info(f"Notes: {notes}")
        logger.info(f"Current User ID: {current_user_id}")
        logger.info(f"Total Line Items: {len(line_items)}")

        # Get hospital and pharmacy registration status
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        if not hospital:
            raise ValueError(f"Hospital with ID {hospital_id} not found")

        has_valid_pharmacy_registration = _check_pharmacy_registration(hospital)

        # Group line items by the 4 invoice categories
        categorized_items = {
            InvoiceSplitCategory.SERVICE_PACKAGE: [],
            InvoiceSplitCategory.GST_MEDICINES: [],
            InvoiceSplitCategory.GST_EXEMPT_MEDICINES: [],
            InvoiceSplitCategory.PRESCRIPTION_COMPOSITE: []
        }

        for item in line_items:
            item_type = item['item_type']
            is_gst_exempt = _get_item_gst_exempt_status(session, item)

            # Determine if this is a prescription item
            is_prescription = (item_type == 'Prescription') or item.get('included_in_consultation', False)

            # For Medicine type, check if prescription is required
            if item_type == 'Medicine' and not is_prescription:
                medicine = session.query(Medicine).filter_by(medicine_id=item['item_id']).first()
                if medicine and getattr(medicine, 'prescription_required', False):
                    is_prescription = True

            # Categorize item using helper function
            category = categorize_line_item(item_type, is_gst_exempt, is_prescription)

            if category:
                categorized_items[category].append(item)
                logger.info(f"Item '{item.get('item_name')}' → {category.value} (Type: {item_type}, GST Exempt: {is_gst_exempt}, Prescription: {is_prescription})")
            else:
                logger.warning(f"Could not categorize item: {item}")

        # Log category counts
        for category, items in categorized_items.items():
            logger.info(f"{category.value}: {len(items)} items")

        # NEW APPROACH: Flag prescription items for consolidated printing (but store individually)
        if not has_valid_pharmacy_registration:
            prescription_items = categorized_items[InvoiceSplitCategory.PRESCRIPTION_COMPOSITE]
            if prescription_items:
                logger.info("No valid pharmacy registration - flagging prescription items for consolidated printing")

                # Generate a unique consolidation group ID for all prescription items in this invoice
                consolidation_group_id = uuid.uuid4()

                # Flag each prescription item (they remain as individual line items in database)
                for item in prescription_items:
                    item['is_prescription_item'] = True
                    item['consolidation_group_id'] = consolidation_group_id
                    item['print_as_consolidated'] = True  # Hospital has no drug license

                # IMPORTANT: Inventory tracking is REQUIRED regardless of pharmacy license
                # Pharmacy license only affects billing format (consolidated vs individual)
                # Inventory must track: batch, expiry, stock deduction for all prescription drugs
                _update_prescription_inventory(
                    session, hospital_id, prescription_items, patient_id, current_user_id
                )

                logger.info(f"Flagged {len(prescription_items)} prescription items with consolidation_group_id: {consolidation_group_id}")
                logger.info("Items will be stored individually but print as 'Doctor's Examination and Treatment'")
                logger.info("Inventory deducted with batch/expiry validation")
        else:
            # Hospital has drug license - prescription items print individually
            prescription_items = categorized_items[InvoiceSplitCategory.PRESCRIPTION_COMPOSITE]
            if prescription_items:
                logger.info("Valid pharmacy registration - prescription items will print individually")
                for item in prescription_items:
                    item['is_prescription_item'] = True
                    item['print_as_consolidated'] = False  # Has drug license, print as individual items

        # Create invoices for non-empty categories
        created_invoices = []
        parent_invoice_id = None
        split_sequence = 1

        for category in [
            InvoiceSplitCategory.SERVICE_PACKAGE,
            InvoiceSplitCategory.GST_MEDICINES,
            InvoiceSplitCategory.GST_EXEMPT_MEDICINES,
            InvoiceSplitCategory.PRESCRIPTION_COMPOSITE
        ]:
            items = categorized_items[category]
            if not items:
                logger.info(f"Skipping {category.value} - no items")
                continue

            config = get_invoice_split_config(category)
            if not config:
                logger.error(f"No configuration found for category: {category}")
                continue

            logger.info(f"Creating invoice for {config.name} ({len(items)} items)")

            # Deduct inventory for medicine-based categories (OTC, Product, Consumable)
            # Note: PRESCRIPTION_COMPOSITE inventory is already deducted earlier in the flow
            if category in [InvoiceSplitCategory.GST_MEDICINES, InvoiceSplitCategory.GST_EXEMPT_MEDICINES]:
                medicine_items = [item for item in items if item.get('item_type') in ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']]
                if medicine_items:
                    logger.info(f"Deducting inventory for {len(medicine_items)} medicine items in {category.value}")
                    _update_prescription_inventory(
                        session, hospital_id, medicine_items, patient_id, current_user_id
                    )

            # Create invoice for this category
            invoice = _create_single_invoice_with_category(
                session=session,
                hospital_id=hospital_id,
                branch_id=branch_id,
                patient_id=patient_id,
                invoice_date=invoice_date,
                line_items=items,
                category=category,
                config=config,
                notes=notes,
                current_user_id=current_user_id,
                parent_invoice_id=parent_invoice_id,
                split_sequence=split_sequence
            )

            # First invoice becomes parent
            if parent_invoice_id is None:
                parent_invoice_id = invoice.invoice_id
                logger.info(f"Parent invoice set: {invoice.invoice_number}")

            created_invoices.append(invoice)
            split_sequence += 1

            logger.info(f"✓ Created {config.name}: {invoice.invoice_number} (₹{invoice.grand_total})")

            # Create AR subledger entries - ONE PER LINE ITEM (for payment allocation)
            try:
                gl_transaction = session.query(GLTransaction).filter_by(
                    invoice_header_id=invoice.invoice_id
                ).first()

                gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None

                from app.services.subledger_service import create_ar_subledger_entry
                from app.models.transaction import InvoiceLineItem

                # Get all line items for this invoice
                invoice_line_items = session.query(InvoiceLineItem).filter(
                    InvoiceLineItem.invoice_id == invoice.invoice_id
                ).all()

                ar_entry_count = 0
                for line_item in invoice_line_items:
                    # Determine description based on item type
                    if line_item.item_type == 'Service':
                        description = f'Invoice {invoice.invoice_number} - Service: {line_item.item_name}'
                    elif line_item.item_type == 'Medicine':
                        description = f'Invoice {invoice.invoice_number} - Medicine: {line_item.item_name}'
                    elif line_item.item_type == 'Package':
                        description = f'Invoice {invoice.invoice_number} - Package: {line_item.item_name}'
                    else:
                        description = f'Invoice {invoice.invoice_number} - {line_item.item_name}'

                    # Create AR entry for THIS line item
                    create_ar_subledger_entry(
                        session=session,
                        hospital_id=hospital_id,
                        branch_id=branch_id,
                        patient_id=patient_id,
                        entry_type='invoice',
                        reference_id=invoice.invoice_id,
                        reference_type='invoice',
                        reference_number=invoice.invoice_number,
                        reference_line_item_id=line_item.line_item_id,  # ✅ LINE ITEM REFERENCE
                        debit_amount=line_item.line_total,  # ✅ LINE ITEM AMOUNT (not invoice total)
                        credit_amount=Decimal('0'),
                        transaction_date=invoice_date,
                        gl_transaction_id=gl_transaction_id,
                        current_user_id=current_user_id
                    )
                    ar_entry_count += 1
                    logger.debug(f"Created AR entry for line item {line_item.line_item_id}: {line_item.item_type} - {line_item.item_name} (₹{line_item.line_total})")

                logger.info(f"✓ Created {ar_entry_count} AR subledger entries (line-item level) for {invoice.invoice_number}")

            except Exception as e:
                logger.error(f"Error creating AR subledger entries: {str(e)}", exc_info=True)
                # Don't let subledger creation failure stop the invoice creation

        # CRITICAL FIX: Update parent invoice to set is_split_invoice = True
        # The parent invoice was created first with parent_invoice_id = None,
        # so is_split_invoice was set to False. Now we need to update it.
        if len(created_invoices) > 1 and parent_invoice_id:
            parent_invoice = session.query(InvoiceHeader).filter_by(
                invoice_id=parent_invoice_id
            ).first()
            if parent_invoice:
                parent_invoice.is_split_invoice = True
                parent_invoice.split_reason = "TAX_COMPLIANCE_SPLIT"
                session.flush()
                logger.info(f"✓ Updated parent invoice {parent_invoice.invoice_number}: is_split_invoice = True")

        # Detach invoices from session BEFORE committing to avoid session closure issues
        detached_invoices = [get_detached_copy(inv) for inv in created_invoices]

        # Commit transaction
        session.commit()

        # Convert detached copies to dictionaries
        invoice_dicts = [get_entity_dict(inv) for inv in detached_invoices]

        logger.info("=" * 80)
        logger.info(f"✓ Phase 3 Complete: Created {len(detached_invoices)} invoices")
        logger.info(f"  Parent Invoice ID: {parent_invoice_id}")
        for inv in detached_invoices:
            logger.info(f"  - {inv.invoice_number} (Seq: {inv.split_sequence}): ₹{inv.grand_total}")
        logger.info("=" * 80)

        # Convert parent_invoice_id to string
        parent_id_str = str(parent_invoice_id) if parent_invoice_id else None
        logger.info(f"🔍 Returning parent_invoice_id: {parent_id_str} (type: {type(parent_id_str)})")

        return {
            'invoices': invoice_dicts,
            'count': len(detached_invoices),
            'parent_invoice_id': parent_id_str
        }

    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
        session.rollback()
        raise

def _get_item_gst_exempt_status(session: Session, item: Dict) -> bool:
    """
    Check if an item is GST exempt based on its type and ID
    
    Args:
        session: Database session
        item: Line item data
        
    Returns:
        bool: True if GST exempt, False otherwise
    """
    try:
        item_type = item['item_type']
        item_id = item['item_id']
        
        if item_type == 'Package':
            package = session.query(Package).filter_by(package_id=item_id).first()
            return package.is_gst_exempt if package else False
            
        elif item_type == 'Service':
            service = session.query(Service).filter_by(service_id=item_id).first()
            return service.is_gst_exempt if service else False

        elif item_type in ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']:
            # All medicine types check the Medicine table for GST exempt status
            medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
            if medicine:
                is_exempt = medicine.is_gst_exempt if hasattr(medicine, 'is_gst_exempt') else False
                logger.info(f"GST exempt check for '{medicine.medicine_name}' (Type: {item_type}): {is_exempt}")
                return is_exempt
            else:
                logger.warning(f"Medicine not found for item_id: {item_id}, item_type: {item_type}")
                return False

        return False
        
    except Exception as e:
        logger.error(f"Error checking GST exempt status: {str(e)}")
        return False

def _get_treatment_service_id(session: Session, hospital_id: uuid.UUID) -> uuid.UUID:
    """
    Get or create a service for Doctor's Examination and Treatment
    
    Args:
        session: Database session
        hospital_id: Hospital UUID
        
    Returns:
        UUID of the service
    """
    service_name = "Doctor's Examination and Treatment"
    
    # Check if service already exists
    service = session.query(Service).filter_by(
        hospital_id=hospital_id,
        service_name=service_name
    ).first()
    
    if service:
        return service.service_id
    
    # Create service if not exists
    new_service = Service(
        hospital_id=hospital_id,
        service_name=service_name,
        code="DRET",
        description="Combined prescription items as per drug rules",
        service_type="Medical",
        duration_minutes=0,
        price=Decimal('0'),
        gst_rate=Decimal('18'),  # Standard GST rate
        is_gst_exempt=False,
        sac_code="9993",  # Standard SAC code for healthcare services
        is_active=True
    )
    
    session.add(new_service)
    session.flush()
    
    return new_service.service_id

def _check_pharmacy_registration(hospital: Hospital) -> bool:
    """
    Check if hospital has valid pharmacy registration

    Args:
        hospital: Hospital model instance

    Returns:
        True if hospital has valid pharmacy registration, False otherwise
    """
    has_valid_pharmacy_registration = False

    # Check if hospital has pharmacy registration number
    if hospital.pharmacy_registration_number:
        # Check for registration validity with database column name
        if hasattr(hospital, 'pharmacy_registration_valid_until'):
            # Check if registration is still valid
            if hospital.pharmacy_registration_valid_until >= datetime.now(timezone.utc).date():
                has_valid_pharmacy_registration = True
        # Fallback to model attribute name in case model was used to create objects
        elif hasattr(hospital, 'pharmacy_reg_valid_until'):
            # Check if registration is still valid
            if hospital.pharmacy_reg_valid_until >= datetime.now(timezone.utc).date():
                has_valid_pharmacy_registration = True

    logger.info(f"Hospital has valid pharmacy registration: {has_valid_pharmacy_registration}")
    return has_valid_pharmacy_registration

def _consolidate_prescription_items(
    session: Session,
    hospital_id: uuid.UUID,
    prescription_items: List[Dict],
    patient_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Consolidate prescription items into a single "Doctor's Examination and Treatment" service item

    Args:
        session: Database session
        hospital_id: Hospital UUID
        prescription_items: List of prescription line items
        patient_id: Patient UUID
        current_user_id: User ID performing the action

    Returns:
        Consolidated line item dictionary
    """
    # Calculate total amount for all prescription items
    total_prescription_amount = Decimal('0')
    for item in prescription_items:
        quantity = Decimal(str(item.get('quantity', 1)))
        unit_price = Decimal(str(item.get('unit_price', 0)))
        total_prescription_amount += quantity * unit_price

    # Create a consolidated item for Doctor's examination and treatment
    treatment_service_id = _get_treatment_service_id(session, hospital_id)
    consolidated_prescription_item = {
        'item_type': 'Service',
        'item_id': treatment_service_id,
        'item_name': "Doctor's Examination and Treatment",
        'quantity': Decimal('1'),
        'unit_price': total_prescription_amount,
        'discount_percent': Decimal('0'),
        'is_consolidated_prescription': True,  # Flag to identify this as consolidated
        'is_gst_exempt': True  # Mark as GST exempt
    }

    # Update inventory for medicine items
    _update_prescription_inventory(
        session, hospital_id, prescription_items, patient_id, current_user_id
    )

    logger.info(f"Consolidated {len(prescription_items)} prescription items into single service item: ₹{total_prescription_amount}")

    return consolidated_prescription_item

def _update_prescription_inventory(
    session: Session,
    hospital_id: uuid.UUID,
    prescription_items: List[Dict],
    patient_id: uuid.UUID,
    current_user_id: Optional[str] = None
):
    """
    Update inventory for medicine items (Prescription, OTC, Product, Consumable)

    Validates:
    - Batch number exists
    - Expiry date exists
    - Sufficient stock available

    Args:
        session: Database session
        hospital_id: Hospital UUID
        prescription_items: List of medicine items (any type)
        patient_id: Patient UUID
        current_user_id: User ID performing the action

    Raises:
        ValueError: If batch not found, insufficient stock, or validation fails
    """
    # Create a dummy invoice ID for inventory tracking
    dummy_invoice_id = uuid.uuid4()

    for item in prescription_items:
        medicine_id = item.get('medicine_id') or item.get('item_id')
        if not medicine_id:
            continue

        # Get item details
        medicine_name = item.get('item_name', 'Unknown Medicine')
        quantity = Decimal(str(item.get('quantity', 1)))
        batch = item.get('batch')

        # Validate batch is provided
        if not batch:
            raise ValueError(f"Inventory Error: Batch number required for {medicine_name}")

        # Get ALL inventory records for this batch with positive stock (FIFO order)
        # Order by expiry first (FIFO), then created_at (oldest first)
        inventory_records = session.query(Inventory).filter(
            Inventory.hospital_id == hospital_id,
            Inventory.medicine_id == medicine_id,
            Inventory.batch == batch,
            Inventory.current_stock > 0
        ).order_by(
            Inventory.expiry.asc(),
            Inventory.created_at.asc()
        ).all()

        # Validate inventory exists for this batch
        if not inventory_records:
            raise ValueError(
                f"Inventory Error: No stock available for Batch {batch} of {medicine_name}. "
                f"Please verify batch number."
            )

        # Calculate total available stock across all records
        total_available_stock = sum(record.current_stock for record in inventory_records)

        # Validate sufficient total stock available
        if total_available_stock < quantity:
            raise ValueError(
                f"Inventory Error: Insufficient stock for {medicine_name} (Batch: {batch}). "
                f"Available: {total_available_stock}, Requested: {quantity}"
            )

        # Validate expiry date on first record (earliest expiry due to FIFO ordering)
        first_record = inventory_records[0]
        if not first_record.expiry:
            raise ValueError(f"Inventory Error: Expiry date missing for {medicine_name} (Batch: {batch})")

        # Validate expiry date has not passed
        # BYPASS for test user (7777777777) to allow testing with old expiry dates
        from datetime import date
        is_test_user = current_user_id == '7777777777'

        if is_test_user and first_record.expiry < date.today():
            logger.warning(f"🧪 TEST MODE: Bypassing expiry validation for user {current_user_id} - "
                         f"{medicine_name} (Batch: {batch}, Expired: {first_record.expiry.strftime('%d-%b-%Y')})")

        if not is_test_user and first_record.expiry < date.today():
            raise ValueError(
                f"Inventory Error: Cannot dispense expired medicine - {medicine_name} "
                f"(Batch: {batch}, Expired: {first_record.expiry.strftime('%d-%b-%Y')})"
            )

        # Extract GST values from line item (per-unit amounts)
        cgst_amount = Decimal(str(item.get('cgst_amount', 0)))
        sgst_amount = Decimal(str(item.get('sgst_amount', 0)))
        igst_amount = Decimal(str(item.get('igst_amount', 0)))
        total_gst_amount = Decimal(str(item.get('total_gst_amount', 0)))

        # Calculate per-unit GST (line item GST is for total quantity)
        if quantity > 0:
            cgst_per_unit = cgst_amount / quantity
            sgst_per_unit = sgst_amount / quantity
            igst_per_unit = igst_amount / quantity
            total_gst_per_unit = total_gst_amount / quantity
        else:
            cgst_per_unit = sgst_per_unit = igst_per_unit = total_gst_per_unit = Decimal('0')

        # Distribute deduction across inventory records using FIFO
        remaining_qty = quantity
        logger.info(f"🔄 Distributing {quantity} units of {medicine_name} (Batch: {batch}) across {len(inventory_records)} inventory records")

        for idx, inv_record in enumerate(inventory_records):
            if remaining_qty <= 0:
                break

            # Determine how much to deduct from this record
            qty_to_deduct = min(remaining_qty, inv_record.current_stock)

            # Calculate new stock for this record
            new_current_stock = inv_record.current_stock - qty_to_deduct

            logger.info(f"  📦 Record {idx + 1}/{len(inventory_records)}: "
                       f"Deducting {qty_to_deduct} units (was {inv_record.current_stock}, now {new_current_stock})")

            # Create inventory transaction for this portion
            inventory_entry = Inventory(
                hospital_id=hospital_id,
                stock_type='Prescription',
                medicine_id=medicine_id,
                medicine_name=medicine_name,
                bill_id=dummy_invoice_id,
                patient_id=patient_id,
                batch=batch,
                expiry=inv_record.expiry,
                pack_purchase_price=inv_record.pack_purchase_price,
                pack_mrp=inv_record.pack_mrp,
                units_per_pack=inv_record.units_per_pack,
                unit_price=inv_record.unit_price,
                sale_price=item.get('unit_price', inv_record.unit_price),
                units=-qty_to_deduct,  # Negative for outgoing stock
                current_stock=new_current_stock,  # Updated stock for this record
                transaction_date=datetime.now(timezone.utc),
                # GST values (per unit) - same for all distributed transactions
                cgst=cgst_per_unit,
                sgst=sgst_per_unit,
                igst=igst_per_unit,
                total_gst=total_gst_per_unit
            )

            if current_user_id:
                inventory_entry.created_by = current_user_id

            session.add(inventory_entry)

            # Update remaining quantity
            remaining_qty -= qty_to_deduct

        logger.info(f"✅ Prescription inventory deducted: {medicine_name} - Batch: {batch}, "
                   f"Total Qty: {quantity}, Distributed across {len([r for r in inventory_records if r.current_stock >= 0])} records")

    session.flush()

def _create_single_invoice_with_category(
    session: Session,
    hospital_id: uuid.UUID,
    branch_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_date: datetime,
    line_items: List[Dict],
    category: InvoiceSplitCategory,
    config: 'InvoiceSplitConfig',
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    parent_invoice_id: Optional[uuid.UUID] = None,
    split_sequence: int = 1
) -> InvoiceHeader:
    """
    Create a single invoice for a specific category (Phase 3)

    This replaces _create_single_invoice with category-aware logic for tax compliance

    Args:
        session: Database session
        hospital_id: Hospital UUID
        branch_id: Branch UUID
        patient_id: Patient UUID
        invoice_date: Invoice date
        line_items: List of line items for this category
        category: Invoice split category
        config: Configuration for this category
        notes: Optional notes
        current_user_id: User ID
        parent_invoice_id: Parent invoice ID for linking
        split_sequence: Sequence number for this split (1-4)

    Returns:
        Created invoice header
    """
    # Validate inventory availability first - AGGREGATE quantities for same batch
    # Group line items by medicine_id and batch to handle duplicates
    batch_quantities = {}
    for item in line_items:
        if item.get('item_type') in ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']:
            medicine_id = item.get('item_id')
            batch = item.get('batch')
            quantity = Decimal(str(item.get('quantity', 1)))

            # Log for debugging
            logger.info(f"Inventory check - Item: {item.get('item_name')}, Medicine ID: {medicine_id}, Batch: {batch}, Qty: {quantity}")

            if not medicine_id or not batch:
                logger.warning(f"Skipping inventory check for {item.get('item_name')} - missing medicine_id or batch")
                continue

            # Aggregate quantities for same medicine + batch combination
            key = (medicine_id, batch)
            if key not in batch_quantities:
                batch_quantities[key] = {
                    'medicine_id': medicine_id,
                    'batch': batch,
                    'total_quantity': Decimal('0'),
                    'item_name': item.get('item_name', 'Unknown Medicine')
                }
            batch_quantities[key]['total_quantity'] += quantity
            logger.info(f"Aggregated total for {item.get('item_name')} Batch {batch}: {batch_quantities[key]['total_quantity']}")

    # Now validate aggregated quantities against available stock
    for key, batch_info in batch_quantities.items():
        medicine_id = batch_info['medicine_id']
        batch = batch_info['batch']
        total_quantity = batch_info['total_quantity']
        item_name = batch_info['item_name']

        # Get the latest inventory entry for this medicine and batch
        latest_inventory = session.query(Inventory).filter(
            Inventory.hospital_id == hospital_id,
            Inventory.medicine_id == medicine_id,
            Inventory.batch == batch
        ).order_by(Inventory.created_at.desc()).first()

        if not latest_inventory:
            raise ValueError(f"Inventory not found for {item_name} (Batch: {batch})")

        # Check if there's enough stock for TOTAL quantity across all line items
        if latest_inventory.current_stock < total_quantity:
            raise ValueError(
                f"Insufficient stock for {item_name} (Batch: {batch}). "
                f"Available: {latest_inventory.current_stock}, Requested: {total_quantity}"
            )

    # Generate invoice number using category prefix with thread-safe locking
    invoice_number = generate_invoice_number_with_category(
        hospital_id, category, config, session, current_user_id
    )

    # Determine if this is GST invoice based on category
    is_gst_invoice = category in [
        InvoiceSplitCategory.GST_MEDICINES,
        InvoiceSplitCategory.SERVICE_PACKAGE  # Can be either
    ]

    # Determine invoice type
    invoice_type_map = {
        InvoiceSplitCategory.SERVICE_PACKAGE: "Service",
        InvoiceSplitCategory.GST_MEDICINES: "Product",
        InvoiceSplitCategory.GST_EXEMPT_MEDICINES: "Product",
        InvoiceSplitCategory.PRESCRIPTION_COMPOSITE: "Prescription"
    }
    invoice_type = invoice_type_map.get(category, "Service")

    # Get default GL account for this invoice type
    default_gl_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.invoice_type_mapping == invoice_type,
        ChartOfAccounts.is_active == True
    ).first()

    gl_account_id = default_gl_account.account_id if default_gl_account else None

    # Get place of supply and interstate status
    place_of_supply = _get_default_place_of_supply(session, hospital_id)
    is_interstate = False

    # Initialize totals
    total_amount = Decimal('0')
    total_discount = Decimal('0')
    total_taxable_value = Decimal('0')
    total_cgst_amount = Decimal('0')
    total_sgst_amount = Decimal('0')
    total_igst_amount = Decimal('0')

    # Process line items
    processed_line_items = []
    for item in line_items:
        line_item = _process_invoice_line_item(session, hospital_id, item, is_interstate, invoice_date)
        processed_line_items.append(line_item)

        # Update totals
        total_amount += line_item.get('line_total', Decimal('0'))
        total_discount += line_item.get('discount_amount', Decimal('0'))
        total_taxable_value += line_item.get('taxable_amount', Decimal('0'))
        total_cgst_amount += line_item.get('cgst_amount', Decimal('0'))
        total_sgst_amount += line_item.get('sgst_amount', Decimal('0'))
        total_igst_amount += line_item.get('igst_amount', Decimal('0'))

    grand_total = total_amount

    # Create invoice header with split tracking fields
    invoice = InvoiceHeader(
        hospital_id=hospital_id,
        branch_id=branch_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_type=invoice_type,
        is_gst_invoice=is_gst_invoice,
        patient_id=patient_id,
        place_of_supply=place_of_supply,
        is_interstate=is_interstate,
        currency_code='INR',
        exchange_rate=Decimal('1.0'),
        total_amount=total_amount,
        total_discount=total_discount,
        total_taxable_value=total_taxable_value,
        total_cgst_amount=total_cgst_amount,
        total_sgst_amount=total_sgst_amount,
        total_igst_amount=total_igst_amount,
        grand_total=grand_total,
        paid_amount=Decimal('0'),
        balance_due=grand_total,
        gl_account_id=gl_account_id,
        notes=notes,
        # Phase 3: Split invoice tracking fields
        parent_transaction_id=parent_invoice_id,
        split_sequence=split_sequence,
        is_split_invoice=(parent_invoice_id is not None),
        split_reason="TAX_COMPLIANCE_SPLIT" if parent_invoice_id else None
    )

    if current_user_id:
        invoice.created_by = current_user_id

    session.add(invoice)
    session.flush()

    # Create line items
    for item_data in processed_line_items:
        line_item = InvoiceLineItem(
            hospital_id=hospital_id,
            invoice_id=invoice.invoice_id,
            package_id=item_data.get('package_id'),
            service_id=item_data.get('service_id'),
            medicine_id=item_data.get('medicine_id'),
            item_type=item_data.get('item_type'),
            item_name=item_data.get('item_name'),
            hsn_sac_code=item_data.get('hsn_sac_code'),
            batch=item_data.get('batch'),
            expiry_date=item_data.get('expiry_date'),
            included_in_consultation=item_data.get('included_in_consultation', False),
            # Prescription consolidation flags
            is_prescription_item=item_data.get('is_prescription_item', False),
            consolidation_group_id=item_data.get('consolidation_group_id'),
            print_as_consolidated=item_data.get('print_as_consolidated', False),
            quantity=item_data.get('quantity', Decimal('1')),
            unit_price=item_data.get('unit_price'),
            discount_percent=item_data.get('discount_percent', Decimal('0')),
            discount_amount=item_data.get('discount_amount', Decimal('0')),
            taxable_amount=item_data.get('taxable_amount'),
            gst_rate=item_data.get('gst_rate'),
            cgst_rate=item_data.get('cgst_rate'),
            sgst_rate=item_data.get('sgst_rate'),
            igst_rate=item_data.get('igst_rate'),
            cgst_amount=item_data.get('cgst_amount', Decimal('0')),
            sgst_amount=item_data.get('sgst_amount', Decimal('0')),
            igst_amount=item_data.get('igst_amount', Decimal('0')),
            total_gst_amount=item_data.get('total_gst_amount', Decimal('0')),
            line_total=item_data.get('line_total'),
            cost_price=item_data.get('cost_price'),
            profit_margin=item_data.get('profit_margin')
        )

        if current_user_id:
            line_item.created_by = current_user_id

        session.add(line_item)

    session.flush()

    # Update inventory for all medicine types (Medicine, Prescription, OTC, Product, Consumable)
    medicine_types = ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']
    if any(item.get('item_type') in medicine_types for item in processed_line_items):
        try:
            logger.info(f"Updating inventory for invoice {invoice.invoice_number} with {len([i for i in processed_line_items if i.get('item_type') in medicine_types])} medicine items")
            update_inventory_for_invoice(
                hospital_id=hospital_id,
                invoice_id=invoice.invoice_id,
                patient_id=patient_id,
                line_items=processed_line_items,
                current_user_id=current_user_id,
                session=session
            )
            logger.info(f"✅ Inventory updated successfully for invoice {invoice.invoice_number}")
        except Exception as e:
            logger.error(f"❌ Error updating inventory for invoice {invoice.invoice_number}: {str(e)}")
            logger.exception(e)
            # Don't fail the entire invoice creation if inventory update fails

    # Create GL entries (Dr AR, Cr Revenue)
    try:
        create_invoice_gl_entries(
            invoice_id=invoice.invoice_id,
            session=session,
            current_user_id=current_user_id
        )
        logger.info(f"✅ GL entries created for invoice {invoice.invoice_number}")
    except Exception as e:
        logger.error(f"❌ Error creating GL entries for invoice {invoice.invoice_number}: {str(e)}")
        # Don't fail the entire invoice creation if GL entries fail
        # GL entries can be created later via reconciliation

    logger.info(f"Created {config.name} invoice: {invoice_number} with {len(processed_line_items)} items")

    # Save invoice PDF to EMR-compliant document folder
    try:
        pdf_path = save_invoice_pdf_to_file(
            invoice_id=invoice.invoice_id,
            hospital_id=hospital_id,
            patient_id=patient_id,
            invoice_number=invoice_number,
            session=session,
            current_user_id=current_user_id
        )
        if pdf_path:
            logger.info(f"✅ Saved invoice document to {pdf_path}")
        else:
            logger.warning(f"⚠️ Failed to save invoice document for {invoice_number}")
    except Exception as e:
        logger.error(f"❌ Error saving invoice document for {invoice_number}: {str(e)}")
        # Don't fail the entire invoice creation if PDF saving fails

    return invoice

def _create_single_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    branch_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_date: datetime,
    line_items: List[Dict],
    is_gst_invoice: bool,
    invoice_type: str,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> InvoiceHeader:
    """
    Create a single invoice with the given line items
    
    Args:
        session: Database session
        hospital_id: Hospital UUID
        branch_id: Branch UUID
        patient_id: Patient UUID
        invoice_date: Invoice date
        line_items: List of line items
        is_gst_invoice: Whether this is a GST invoice
        invoice_type: Type of invoice
        notes: Optional notes
        current_user_id: User ID
        
    Returns:
        Created invoice header
    """

    # Validate inventory availability first
    for item in line_items:
        if item.get('item_type') in ['Medicine', 'Prescription']:
            medicine_id = item.get('item_id')
            batch = item.get('batch')
            quantity = Decimal(str(item.get('quantity', 1)))
            
            if not medicine_id or not batch:
                continue
                
            # Get the latest inventory entry for this medicine and batch
            latest_inventory = session.query(Inventory).filter(
                Inventory.hospital_id == hospital_id,
                Inventory.medicine_id == medicine_id,
                Inventory.batch == batch
            ).order_by(Inventory.created_at.desc()).first()
            
            if not latest_inventory:
                raise ValueError(f"Inventory not found for medicine {medicine_id}, batch {batch}")
                
            # Check if there's enough stock
            if latest_inventory.current_stock < quantity:
                # Get medicine name for better error message
                medicine = session.query(Medicine).filter_by(medicine_id=medicine_id).first()
                medicine_name = medicine.medicine_name if medicine else "Unknown Medicine"
                raise ValueError(f"Insufficient stock for {medicine_name} (Batch: {batch}). Available: {latest_inventory.current_stock}, Requested: {quantity}")

    # Generate invoice number
    invoice_number = generate_invoice_number(hospital_id, is_gst_invoice, invoice_type, session)
    
    # Get default GL account for this invoice type
    default_gl_account = session.query(ChartOfAccounts).filter(
        ChartOfAccounts.hospital_id == hospital_id,
        ChartOfAccounts.invoice_type_mapping == invoice_type,
        ChartOfAccounts.is_active == True
    ).first()
    
    gl_account_id = default_gl_account.account_id if default_gl_account else None
    
    # Get place of supply and interstate status
    place_of_supply = _get_default_place_of_supply(session, hospital_id)
    is_interstate = False  # Default to intrastate
    
    # Initialize totals
    total_amount = Decimal('0')
    total_discount = Decimal('0')
    total_taxable_value = Decimal('0')
    total_cgst_amount = Decimal('0')
    total_sgst_amount = Decimal('0')
    total_igst_amount = Decimal('0')
    
    # Process line items
    processed_line_items = []

    for item in line_items:
        line_item = _process_invoice_line_item(session, hospital_id, item, is_interstate, invoice_date)
        processed_line_items.append(line_item)
        
        # Update totals
        total_amount += line_item.get('line_total', Decimal('0'))
        total_discount += line_item.get('discount_amount', Decimal('0'))
        total_taxable_value += line_item.get('taxable_amount', Decimal('0'))
        total_cgst_amount += line_item.get('cgst_amount', Decimal('0'))
        total_sgst_amount += line_item.get('sgst_amount', Decimal('0'))
        total_igst_amount += line_item.get('igst_amount', Decimal('0'))
    
    # Calculate grand total
    grand_total = total_amount
    
    # Create invoice header
    invoice = InvoiceHeader(
        hospital_id=hospital_id,
        branch_id=branch_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_type=invoice_type,
        is_gst_invoice=is_gst_invoice,
        patient_id=patient_id,
        place_of_supply=place_of_supply,
        is_interstate=is_interstate,
        currency_code='INR',  # Default to INR
        exchange_rate=Decimal('1.0'),
        total_amount=total_amount,
        total_discount=total_discount,
        total_taxable_value=total_taxable_value,
        total_cgst_amount=total_cgst_amount,
        total_sgst_amount=total_sgst_amount,
        total_igst_amount=total_igst_amount,
        grand_total=grand_total,
        paid_amount=Decimal('0'),
        balance_due=grand_total,
        gl_account_id=gl_account_id,
        notes=notes
    )
    
    if current_user_id:
        invoice.created_by = current_user_id
        
    session.add(invoice)
    session.flush()
    
    # Create line items
    for item_data in processed_line_items:
        line_item = InvoiceLineItem(
            hospital_id=hospital_id,
            invoice_id=invoice.invoice_id,
            package_id=item_data.get('package_id'),
            service_id=item_data.get('service_id'),
            medicine_id=item_data.get('medicine_id'),
            item_type=item_data.get('item_type'),
            item_name=item_data.get('item_name'),
            hsn_sac_code=item_data.get('hsn_sac_code'),
            batch=item_data.get('batch'),
            expiry_date=item_data.get('expiry_date'),
            included_in_consultation=item_data.get('included_in_consultation', False),
            # Prescription consolidation flags
            is_prescription_item=item_data.get('is_prescription_item', False),
            consolidation_group_id=item_data.get('consolidation_group_id'),
            print_as_consolidated=item_data.get('print_as_consolidated', False),
            quantity=item_data.get('quantity', Decimal('1')),
            unit_price=item_data.get('unit_price'),
            discount_percent=item_data.get('discount_percent', Decimal('0')),
            discount_amount=item_data.get('discount_amount', Decimal('0')),
            taxable_amount=item_data.get('taxable_amount'),
            gst_rate=item_data.get('gst_rate'),
            cgst_rate=item_data.get('cgst_rate'),
            sgst_rate=item_data.get('sgst_rate'),
            igst_rate=item_data.get('igst_rate'),
            cgst_amount=item_data.get('cgst_amount', Decimal('0')),
            sgst_amount=item_data.get('sgst_amount', Decimal('0')),
            igst_amount=item_data.get('igst_amount', Decimal('0')),
            total_gst_amount=item_data.get('total_gst_amount', Decimal('0')),
            line_total=item_data.get('line_total'),
            cost_price=item_data.get('cost_price'),
            profit_margin=item_data.get('profit_margin')
        )
        
        if current_user_id:
            line_item.created_by = current_user_id
            
        session.add(line_item)
        
    session.flush()
    
    # Update inventory for all medicine types (Medicine, Prescription, OTC, Product, Consumable)
    medicine_types = ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']
    if any(item.get('item_type') in medicine_types for item in processed_line_items):
        try:
            logger.info(f"Updating inventory for invoice {invoice.invoice_number} with {len([i for i in processed_line_items if i.get('item_type') in medicine_types])} medicine items")
            update_inventory_for_invoice(
                hospital_id=hospital_id,
                invoice_id=invoice.invoice_id,
                patient_id=patient_id,
                line_items=processed_line_items,
                current_user_id=current_user_id,
                session=session
            )
            logger.info(f"✅ Inventory updated successfully for invoice {invoice.invoice_number}")
        except Exception as e:
            logger.error(f"❌ Error updating inventory for invoice {invoice.invoice_number}: {str(e)}")
            logger.exception(e)
            # Don't fail the entire invoice creation if inventory update fails

    # Create GL entries (Dr AR, Cr Revenue)
    try:
        create_invoice_gl_entries(
            invoice_id=invoice.invoice_id,
            session=session,
            current_user_id=current_user_id
        )
        logger.info(f"✅ GL entries created for invoice {invoice.invoice_number}")
    except Exception as e:
        logger.error(f"❌ Error creating GL entries for invoice {invoice.invoice_number}: {str(e)}")
        # Don't fail the entire invoice creation if GL entries fail
        # GL entries can be created later via reconciliation

    return invoice

# Function in billing_service.py to be updated

def calculate_doctors_examination_gst(price, quantity, discount_percent, gst_rate, is_interstate):
    """
    Special calculation for Medicine/Prescription items with GST included in MRP.
    
    Args:
        price: Unit price (MRP)
        quantity: Quantity
        discount_percent: Discount percentage
        gst_rate: GST rate percentage
        is_interstate: Whether this is an interstate transaction
        
    Returns:
        Dictionary with calculated values
    """
    # Calculate pre-discount amount (MRP)
    pre_discount_amount = quantity * price
    
    # For MRP-based items, GST is included in MRP, so reverse calculate
    gst_factor = gst_rate / Decimal('100')
    base_before_gst = pre_discount_amount / (1 + gst_factor)
    
    # Calculate discount on taxable value (base_before_gst), not MRP
    discount_amount = (base_before_gst * discount_percent) / 100
    
    # Taxable amount after discount
    taxable_amount = base_before_gst - discount_amount
    
    # Calculate GST amounts (on taxable amount after discount)
    if is_interstate:
        # Interstate: only IGST
        igst_amount = taxable_amount * gst_factor
        cgst_amount = Decimal('0')
        sgst_amount = Decimal('0')
    else:
        # Intrastate: CGST + SGST
        igst_amount = Decimal('0')
        half_gst_rate = gst_factor / 2
        cgst_amount = taxable_amount * half_gst_rate
        sgst_amount = taxable_amount * half_gst_rate
    
    total_gst_amount = cgst_amount + sgst_amount + igst_amount
    
    # Line total is taxable amount plus GST
    line_total = taxable_amount + total_gst_amount
    
    return {
        'base_before_gst': base_before_gst,
        'taxable_amount': taxable_amount,
        'discount_amount': discount_amount,
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
        'igst_amount': igst_amount,
        'total_gst_amount': total_gst_amount,
        'line_total': line_total
    }

def _process_invoice_line_item(session: Session, hospital_id: uuid.UUID, item: Dict, is_interstate: bool, invoice_date: datetime = None) -> Dict:
    """
    Process a line item for invoice creation, calculating amounts and taxes

    Args:
        session: Database session
        hospital_id: Hospital UUID
        item: Line item data
        is_interstate: Whether this is an interstate transaction
        invoice_date: Invoice date for versioned pricing/tax lookup

    Returns:
        Processed line item with calculated fields
    """
    try:
        item_type = item['item_type']
        item_id = item['item_id']
        item_name = item['item_name']
        quantity = Decimal(str(item.get('quantity', 1)))
        unit_price = Decimal(str(item.get('unit_price', 0)))
        discount_percent = Decimal(str(item.get('discount_percent', 0)))
        
        # Check for Doctor's Examination or included in consultation
        is_doctors_examination = (item_name == "Doctor's Examination and Treatment" or 
                                 item.get('is_consolidated_prescription', False))

        # For Doctor's Examination, override GST settings to make it GST exempt
        if is_doctors_examination:
            gst_rate = Decimal('0')
            is_gst_exempt = True
    
            # Also override discount to be zero for Doctor's Examination
            discount_percent = Decimal('0')

        # Get item details from the database based on type
        # CRITICAL: Default is_gst_exempt to FALSE (items are taxable unless proven exempt)
        gst_rate = Decimal('0')
        is_gst_exempt = False  # FIXED: Changed from True to False
        hsn_sac_code = None
        cost_price = None
        gst_inclusive = False  # Medicine MRP includes GST

        # For Doctor's Examination, set GST to zero regardless of database values
        if is_doctors_examination:
            gst_rate = Decimal('0')
            is_gst_exempt = True
        else:
            # For other items, get details from the database
            if item_type == 'Package':
                package = session.query(Package).filter_by(package_id=item_id).first()
                if package:
                    # Get pricing and GST applicable on invoice date (date-based versioning)
                    from app.services.pricing_tax_service import get_applicable_pricing_and_tax
                    # Use the invoice_date parameter (convert to date if it's a datetime)
                    applicable_date = invoice_date if invoice_date else datetime.now(timezone.utc)
                    if isinstance(applicable_date, datetime):
                        applicable_date = applicable_date.date()

                    pricing_tax = get_applicable_pricing_and_tax(
                        session=session,
                        hospital_id=hospital_id,
                        entity_type='package',
                        entity_id=item_id,
                        applicable_date=applicable_date
                    )

                    # Use versioned GST rates (not current master table rates)
                    gst_rate = pricing_tax['gst_rate']
                    is_gst_exempt = pricing_tax['is_gst_exempt']

                    logger.info(f"Package '{package.package_name}': Using {pricing_tax['source']} - "
                               f"gst_rate={gst_rate}%, is_gst_exempt={is_gst_exempt} for date {applicable_date}")

            elif item_type == 'Service':
                service = session.query(Service).filter_by(service_id=item_id).first()
                if service:
                    # Get pricing and GST applicable on invoice date (date-based versioning)
                    from app.services.pricing_tax_service import get_applicable_pricing_and_tax
                    # Use the invoice_date parameter (convert to date if it's a datetime)
                    applicable_date = invoice_date if invoice_date else datetime.now(timezone.utc)
                    if isinstance(applicable_date, datetime):
                        applicable_date = applicable_date.date()

                    pricing_tax = get_applicable_pricing_and_tax(
                        session=session,
                        hospital_id=hospital_id,
                        entity_type='service',
                        entity_id=item_id,
                        applicable_date=applicable_date
                    )

                    # Use versioned GST rates (not current master table rates)
                    gst_rate = pricing_tax['gst_rate']
                    is_gst_exempt = pricing_tax['is_gst_exempt']
                    hsn_sac_code = service.sac_code

                    logger.info(f"Service '{service.service_name}': Using {pricing_tax['source']} - "
                               f"gst_rate={gst_rate}%, is_gst_exempt={is_gst_exempt} for date {applicable_date}")

            elif item_type in ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']:
                # FIXED: Include all medicine item types
                medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
                if medicine:
                    # Get pricing and GST applicable on invoice date (date-based versioning)
                    from app.services.pricing_tax_service import get_applicable_pricing_and_tax
                    # Use passed invoice_date or default to now
                    effective_date = invoice_date or datetime.now(timezone.utc)
                    if isinstance(effective_date, datetime):
                        effective_date = effective_date.date()
                    else:
                        effective_date = effective_date

                    pricing_tax = get_applicable_pricing_and_tax(
                        session=session,
                        hospital_id=hospital_id,
                        entity_type='medicine',
                        entity_id=item_id,
                        applicable_date=effective_date
                    )

                    # Use versioned GST rates (not current master table rates)
                    gst_rate = pricing_tax['gst_rate']
                    is_gst_exempt = pricing_tax['is_gst_exempt']
                    gst_inclusive = pricing_tax.get('gst_inclusive', True)
                    hsn_sac_code = medicine.hsn_code
                    cost_price = pricing_tax.get('cost_price') or medicine.cost_price

                    logger.info(f"Medicine '{medicine.medicine_name}': Using {pricing_tax['source']} - "
                               f"gst_rate={gst_rate}%, is_gst_exempt={is_gst_exempt} for date {effective_date}")
                else:
                    logger.warning(f"Medicine not found for item_id: {item_id}, item_name: {item_name}")
        
        # Calculate amounts
        pre_discount_amount = quantity * unit_price
        
        cgst_rate = Decimal('0')
        sgst_rate = Decimal('0')
        igst_rate = Decimal('0')
        cgst_amount = Decimal('0')
        sgst_amount = Decimal('0')
        igst_amount = Decimal('0')
        total_gst_amount = Decimal('0')
        
        if not is_gst_exempt and gst_rate > 0:
            # Check if this is a medicine type AND if GST is inclusive (MRP includes GST)
            is_medicine_type = item_type in ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']

            if is_medicine_type and gst_inclusive:
                # For medicines with GST INCLUDED in MRP (gst_inclusive=True)
                # Use specialized reverse-calculation function
                logger.info(f"Using MRP-inclusive GST calculation for {item_name} (gst_inclusive=True)")
                result = calculate_doctors_examination_gst(
                    unit_price, quantity, discount_percent, gst_rate, is_interstate
                )

                base_before_gst = result['base_before_gst']
                taxable_amount = result['taxable_amount']
                discount_amount = result['discount_amount']
                cgst_amount = result['cgst_amount']
                sgst_amount = result['sgst_amount']
                igst_amount = result['igst_amount']
                total_gst_amount = result['total_gst_amount']
                line_total = result['line_total']

                if is_interstate:
                    igst_rate = gst_rate
                else:
                    cgst_rate = gst_rate / 2
                    sgst_rate = gst_rate / 2
            else:
                # For services/packages OR medicines with GST EXCLUSIVE (gst_inclusive=False)
                # Calculate GST on top of price
                if is_medicine_type:
                    logger.info(f"Using standard GST calculation for {item_name} (gst_inclusive=False)")

                if is_interstate:
                    igst_rate = gst_rate
                    # Calculate discount on pre-discount amount
                    discount_amount = (pre_discount_amount * discount_percent) / 100
                    taxable_amount = pre_discount_amount - discount_amount
                    # Calculate GST on original price (pre-discount)
                    igst_amount = (pre_discount_amount * igst_rate) / 100
                    total_gst_amount = igst_amount
                else:
                    cgst_rate = gst_rate / 2
                    sgst_rate = gst_rate / 2
                    # Calculate discount on pre-discount amount
                    discount_amount = (pre_discount_amount * discount_percent) / 100
                    taxable_amount = pre_discount_amount - discount_amount
                    # Calculate GST on original price (pre-discount)
                    cgst_amount = (pre_discount_amount * cgst_rate) / 100
                    sgst_amount = (pre_discount_amount * sgst_rate) / 100
                    total_gst_amount = cgst_amount + sgst_amount
                
                # Line total is taxable amount (post-discount) plus GST
                line_total = taxable_amount + total_gst_amount
        else:
            # If GST exempt or zero rate
            discount_amount = (pre_discount_amount * discount_percent) / 100
            taxable_amount = pre_discount_amount - discount_amount
            line_total = taxable_amount
        
        # Calculate profit margin for medicines
        profit_margin = None
        if cost_price is not None and unit_price > 0:
            profit_margin = ((unit_price - cost_price) / unit_price) * 100
        
        # Construct processed line item
        processed_item = {
            'item_type': item_type,
            'item_name': item_name,
            'hsn_sac_code': hsn_sac_code,
            'quantity': quantity,
            'unit_price': unit_price,
            'discount_percent': discount_percent,
            'discount_amount': discount_amount,
            'taxable_amount': taxable_amount,
            'gst_rate': gst_rate,
            'cgst_rate': cgst_rate,
            'sgst_rate': sgst_rate,
            'igst_rate': igst_rate,
            'cgst_amount': cgst_amount,
            'sgst_amount': sgst_amount,
            'igst_amount': igst_amount,
            'total_gst_amount': total_gst_amount,
            'line_total': line_total,
            'cost_price': cost_price,
            'profit_margin': profit_margin,
            'included_in_consultation': item.get('included_in_consultation', False),
            # Prescription consolidation flags (new fields for split invoice tracking)
            'is_prescription_item': item.get('is_prescription_item', False),
            'consolidation_group_id': item.get('consolidation_group_id'),
            'print_as_consolidated': item.get('print_as_consolidated', False)
        }

        # Add ID fields based on type
        if item_type == 'Package':
            processed_item['package_id'] = item_id
        elif item_type == 'Service':
            processed_item['service_id'] = item_id
        elif item_type in ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']:
            # All medicine types need medicine_id, batch, and expiry_date
            processed_item['medicine_id'] = item_id
            processed_item['batch'] = item.get('batch')
            processed_item['expiry_date'] = item.get('expiry_date')

        return processed_item
        
    except Exception as e:
        logger.error(f"Error processing invoice line item: {str(e)}")
        raise

def _get_default_place_of_supply(session: Session, hospital_id: uuid.UUID) -> str:
    """
    Get default place of supply from hospital state
    
    Args:
        session: Database session
        hospital_id: Hospital UUID
        
    Returns:
        State code for place of supply
    """
    hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
    
    if hospital:
        # Check for state_code directly in Hospital
        if hospital.state_code:
            return hospital.state_code
            
        # Check in address if available
        if hospital.address and 'state_code' in hospital.address:
            return hospital.address['state_code']
    
    return '27'  # Default to Maharashtra

def generate_invoice_number(
    hospital_id: uuid.UUID, 
    is_gst_invoice: bool, 
    invoice_type: str, 
    session: Session
) -> str:
    """
    Generate a sequential invoice number based on hospital settings, GST status, and invoice type
    
    Args:
        hospital_id: Hospital UUID
        is_gst_invoice: Whether this is a GST invoice
        invoice_type: Type of invoice (Service, Product, Prescription)
        session: Database session
        
    Returns:
        Formatted invoice number
    """
    # Get current financial year (April-March in India)
    now = datetime.now(timezone.utc)
    current_month = now.month
    
    if current_month >= 4:  # April onwards is new financial year
        fin_year = f"{now.year}-{now.year + 1}"
    else:
        fin_year = f"{now.year - 1}-{now.year}"
        
    # Get hospital information
    hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
    if not hospital:
        raise ValueError(f"Hospital with ID {hospital_id} not found")
        
    # Determine prefix based on GST or non-GST invoice and type
    if is_gst_invoice:
        if invoice_type == 'Prescription':
            prefix = "DRG"  # Drug invoice
        else:
            prefix = "GST"  # Regular GST invoice
    else:
        prefix = "NGS"  # Non-GST invoice
    
    # Get the latest invoice number for this type and financial year
    # Include both active and cancelled/voided invoices
    latest_invoice = session.query(InvoiceHeader).filter(
        InvoiceHeader.hospital_id == hospital_id,
        InvoiceHeader.is_gst_invoice == is_gst_invoice,
        InvoiceHeader.invoice_type == invoice_type,
        InvoiceHeader.invoice_number.like(f"{prefix}/{fin_year}/%")
    ).order_by(InvoiceHeader.created_at.desc()).first()
    
    if latest_invoice:
        # Extract the sequence number and increment
        seq_num = int(latest_invoice.invoice_number.split('/')[-1]) + 1
    else:
        # Start with 1 if no invoices exist for this type and year
        seq_num = 1
        
    # Format: GST/2024-2025/00001 or NGS/2024-2025/00001 or DRG/2024-2025/00001
    invoice_number = f"{prefix}/{fin_year}/{seq_num:05d}"

    return invoice_number

def get_next_invoice_sequence(
    hospital_id: uuid.UUID,
    prefix: str,
    financial_year: str,
    starting_number: int,
    session: Session,
    user_id: Optional[str] = None
) -> int:
    """
    Thread-safe sequence generation using row-level locking

    Args:
        hospital_id: Hospital UUID
        prefix: Invoice prefix (SVC, MED, EXM, RX)
        financial_year: Financial year (YYYY-YYYY)
        starting_number: Starting sequence number if creating new
        session: Database session
        user_id: User ID for audit trail

    Returns:
        Next sequence number
    """
    # Lock the row for this hospital/prefix/year combination
    sequence_record = session.query(InvoiceSequence).filter(
        InvoiceSequence.hospital_id == hospital_id,
        InvoiceSequence.prefix == prefix,
        InvoiceSequence.financial_year == financial_year
    ).with_for_update().first()

    if sequence_record:
        # Increment existing sequence
        sequence_record.current_sequence += 1
        sequence_record.updated_by = user_id
        next_seq = sequence_record.current_sequence
        logger.info(f"Incremented sequence {prefix}/{financial_year} to {next_seq}")
    else:
        # Create new sequence record
        sequence_record = InvoiceSequence(
            hospital_id=hospital_id,
            prefix=prefix,
            financial_year=financial_year,
            current_sequence=starting_number,
            created_by=user_id,
            updated_by=user_id
        )
        session.add(sequence_record)
        next_seq = starting_number
        logger.info(f"Created new sequence {prefix}/{financial_year} starting at {next_seq}")

    session.flush()  # Ensure sequence is written before returning
    return next_seq


def generate_invoice_number_with_category(
    hospital_id: uuid.UUID,
    category: InvoiceSplitCategory,
    config: 'InvoiceSplitConfig',
    session: Session,
    user_id: Optional[str] = None
) -> str:
    """
    Generate invoice number with category-specific prefix for Phase 3 split invoices
    UPDATED: Now uses thread-safe sequence table with row-level locking

    Args:
        hospital_id: Hospital UUID
        category: Invoice split category
        config: Configuration for this category
        session: Database session
        user_id: User ID for audit trail (optional)

    Returns:
        Formatted invoice number (e.g., SVC/2024-2025/00001)
    """
    # Get financial year
    now = datetime.now(timezone.utc)
    current_month = now.month

    if current_month >= 4:
        fin_year = f"{now.year}-{now.year + 1}"
    else:
        fin_year = f"{now.year - 1}-{now.year}"

    prefix = config.prefix

    # Get next sequence number using thread-safe locking
    seq_num = get_next_invoice_sequence(
        hospital_id=hospital_id,
        prefix=prefix,
        financial_year=fin_year,
        starting_number=config.starting_number,
        session=session,
        user_id=user_id
    )

    # Format: PREFIX/FIN_YEAR/SEQ (e.g., SVC/2024-2025/00001)
    invoice_number = f"{prefix}/{fin_year}/{seq_num:05d}"

    logger.info(f"Generated thread-safe invoice number for {category.value}: {invoice_number}")

    return invoice_number

def update_inventory_for_invoice(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    patient_id: uuid.UUID,
    line_items: List[Dict],
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> None:
    """
    Update inventory records based on invoice line items
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        patient_id: Patient UUID
        line_items: Processed line items
        current_user_id: User ID
        session: Database session (optional)
    """
    if session is not None:
        return _update_inventory_for_invoice(
            session, hospital_id, invoice_id, patient_id, line_items, current_user_id
        )
    
    with get_db_session() as new_session:
        return _update_inventory_for_invoice(
            new_session, hospital_id, invoice_id, patient_id, line_items, current_user_id
        )

def _update_inventory_for_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    patient_id: uuid.UUID,
    line_items: List[Dict],
    current_user_id: Optional[str] = None
) -> None:
    """
    Internal function to update inventory records based on invoice line items
    """
    try:
        # Process all medicine types (Medicine, Prescription, OTC, Product, Consumable)
        medicine_types = ['Medicine', 'Prescription', 'OTC', 'Product', 'Consumable']
        for item in line_items:
            if item.get('item_type') in medicine_types:
                medicine_id = item.get('medicine_id')
                if not medicine_id:
                    continue
                    
                medicine_name = item.get('item_name', 'Unknown Medicine')
                quantity = item.get('quantity', Decimal('1'))
                batch = item.get('batch')
                
                if not batch:
                    logger.warning(f"No batch specified for medicine {medicine_id} in invoice {invoice_id}")
                    continue
                
                # Get the latest inventory entry for this medicine and batch
                latest_inventory = session.query(Inventory).filter(
                    Inventory.hospital_id == hospital_id,
                    Inventory.medicine_id == medicine_id,
                    Inventory.batch == batch
                ).order_by(Inventory.created_at.desc()).first()
                
                if not latest_inventory:
                    logger.warning(f"No inventory found for medicine {medicine_id}, batch {batch}")
                    continue
                
                # Double-check if there's enough stock before updating
                if latest_inventory.current_stock < quantity:
                    raise ValueError(f"Insufficient stock for {medicine_name} (Batch: {batch}). Available: {latest_inventory.current_stock}, Requested: {quantity}")
                
                # Calculate current stock after this transaction
                current_stock = latest_inventory.current_stock - quantity

                # Extract GST values from line item (per-unit amounts)
                cgst_amount = Decimal(str(item.get('cgst_amount', 0)))
                sgst_amount = Decimal(str(item.get('sgst_amount', 0)))
                igst_amount = Decimal(str(item.get('igst_amount', 0)))
                total_gst_amount = Decimal(str(item.get('total_gst_amount', 0)))

                # Calculate per-unit GST (line item GST is for total quantity)
                if quantity > 0:
                    cgst_per_unit = cgst_amount / quantity
                    sgst_per_unit = sgst_amount / quantity
                    igst_per_unit = igst_amount / quantity
                    total_gst_per_unit = total_gst_amount / quantity
                else:
                    cgst_per_unit = sgst_per_unit = igst_per_unit = total_gst_per_unit = Decimal('0')

                # Create inventory transaction
                inventory_entry = Inventory(
                    hospital_id=hospital_id,
                    stock_type='Sale',
                    medicine_id=medicine_id,
                    medicine_name=medicine_name,
                    bill_id=invoice_id,
                    patient_id=patient_id,
                    batch=batch,
                    expiry=latest_inventory.expiry,
                    pack_purchase_price=latest_inventory.pack_purchase_price,
                    pack_mrp=latest_inventory.pack_mrp,
                    units_per_pack=latest_inventory.units_per_pack,
                    unit_price=latest_inventory.unit_price,
                    sale_price=item.get('unit_price', latest_inventory.unit_price),
                    units=-quantity,  # Negative for outgoing stock
                    current_stock=current_stock,
                    transaction_date=datetime.now(timezone.utc),
                    # GST values (per unit)
                    cgst=cgst_per_unit,
                    sgst=sgst_per_unit,
                    igst=igst_per_unit,
                    total_gst=total_gst_per_unit
                )
                
                if current_user_id:
                    inventory_entry.created_by = current_user_id
                    
                session.add(inventory_entry)
                
        session.flush()

    except Exception as e:
        logger.error(f"Error updating inventory for invoice: {str(e)}")
        session.rollback()
        raise

def _reverse_inventory_for_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> None:
    """
    Internal function to reverse inventory transactions for a voided invoice
    """
    try:
        # Find all inventory records related to this invoice
        inventory_transactions = session.query(Inventory).filter(
            Inventory.hospital_id == hospital_id,
            Inventory.bill_id == invoice_id
        ).all()
        
        if not inventory_transactions:
            logger.info(f"No inventory transactions found for invoice {invoice_id}")
            return
            
        for transaction in inventory_transactions:
            # Create a reversal entry with opposite units
            reversal_entry = Inventory(
                hospital_id=hospital_id,
                stock_type='Void',
                medicine_id=transaction.medicine_id,
                medicine_name=transaction.medicine_name,
                bill_id=invoice_id,
                patient_id=transaction.patient_id,
                batch=transaction.batch,
                expiry=transaction.expiry,
                pack_purchase_price=transaction.pack_purchase_price,
                pack_mrp=transaction.pack_mrp,
                units_per_pack=transaction.units_per_pack,
                unit_price=transaction.unit_price,
                sale_price=transaction.sale_price,
                units=-transaction.units,  # Reverse the units (negative becomes positive)
                current_stock=transaction.current_stock - transaction.units,  # Adjust stock back
                transaction_date=datetime.now(timezone.utc),
                # notes=f"Reversal for voided invoice {invoice_id}"
            )
            
            if current_user_id:
                reversal_entry.created_by = current_user_id
                
            session.add(reversal_entry)
            
        session.flush()

    except Exception as e:
        logger.error(f"Error reversing inventory for invoice: {str(e)}")
        session.rollback()
        raise

# GL entry functions are now fully imported from gl_service.py
# Local stub functions removed - using real implementation from gl_service

def _reverse_gl_entries_for_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> None:
    """
    Internal function to reverse general ledger entries for a voided invoice
    """
    try:
        # Get invoice details
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id,
            invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Find existing GL entries for this invoice
        gl_entries = session.query(GLTransaction).filter(
            GLTransaction.hospital_id == hospital_id,
            GLTransaction.reference_id == str(invoice_id),
            GLTransaction.transaction_type == 'Invoice'
        ).all()
        
        if not gl_entries:
            logger.info(f"No GL entries found for invoice {invoice.invoice_number}")
            return
            
        # Create reversal entries for each GL entry
        for entry in gl_entries:
            reversal_entry = GLTransaction(
                hospital_id=hospital_id,
                transaction_date=datetime.now(timezone.utc),
                account_id=entry.account_id,
                transaction_type='Void Invoice',
                reference_id=str(invoice_id),
                description=f"Void of invoice {invoice.invoice_number}",
                debit_amount=entry.credit_amount,  # Swap debit and credit
                credit_amount=entry.debit_amount
            )
            
            if current_user_id:
                reversal_entry.created_by = current_user_id
            
            session.add(reversal_entry)
            
        session.flush()
        logger.info(f"GL entries reversed for voided invoice {invoice.invoice_number}")
        
    except Exception as e:
        logger.error(f"Error reversing GL entries for invoice: {str(e)}")
        session.rollback()
        raise

def get_invoice_by_id(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    session: Optional[Session] = None
) -> Dict:
    """
    Get invoice details by ID
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        session: Database session (optional)
        
    Returns:
        Invoice details as dictionary
    """
    if session is not None:
        return _get_invoice_by_id(session, hospital_id, invoice_id)
    
    with get_db_session() as new_session:
        return _get_invoice_by_id(new_session, hospital_id, invoice_id)

def _get_invoice_by_id(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID
) -> Dict:
    """
    Internal function to get invoice details by ID with package discontinuation status
    """
    try:
        # Import models needed for joins
        from app.models.transaction import PackagePaymentPlan, PatientCreditNote

        # Query invoice with line items
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id,
            invoice_id=invoice_id
        ).first()

        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")

        # Get line items with package discontinuation status (LEFT JOIN)
        line_items_query = session.query(
            InvoiceLineItem,
            PackagePaymentPlan.status.label('package_plan_status'),
            PackagePaymentPlan.discontinued_at,
            PackagePaymentPlan.discontinuation_reason,
            PackagePaymentPlan.plan_id,
            PatientCreditNote.credit_note_id,
            PatientCreditNote.credit_note_number,
            PatientCreditNote.total_amount.label('refund_amount')
        ).outerjoin(
            PackagePaymentPlan,
            and_(
                InvoiceLineItem.invoice_id == PackagePaymentPlan.invoice_id,
                InvoiceLineItem.package_id == PackagePaymentPlan.package_id
            )
        ).outerjoin(
            PatientCreditNote,
            and_(
                PatientCreditNote.plan_id == PackagePaymentPlan.plan_id,
                PatientCreditNote.reason_code == 'plan_discontinued'
            )
        ).filter(
            InvoiceLineItem.hospital_id == hospital_id,
            InvoiceLineItem.invoice_id == invoice_id
        ).all()

        # Create detached copies
        invoice_dict = get_entity_dict(invoice)

        # Process line items with discontinuation status
        line_items_dict = []
        for item, plan_status, discontinued_at, reason, plan_id, cn_id, cn_number, refund in line_items_query:
            item_dict = get_entity_dict(item)

            # Compute display status (not stored in database!)
            if plan_status == 'discontinued':
                item_dict['display_status'] = 'discontinued'
                item_dict['status_badge'] = 'warning'
                item_dict['status_text'] = 'Discontinued'
                item_dict['status_icon'] = '⚠️'
                item_dict['is_discontinued'] = True
                item_dict['discontinued_at'] = discontinued_at
                item_dict['discontinuation_reason'] = reason
                item_dict['plan_id'] = str(plan_id) if plan_id else None
                item_dict['credit_note_id'] = str(cn_id) if cn_id else None
                item_dict['credit_note_number'] = cn_number
                item_dict['refund_amount'] = float(refund) if refund else 0
                item_dict['net_amount'] = float(item.line_total) - (float(refund) if refund else 0)
            elif plan_status == 'completed':
                item_dict['display_status'] = 'completed'
                item_dict['status_badge'] = 'success'
                item_dict['status_text'] = 'Completed'
                item_dict['status_icon'] = '✓'
                item_dict['is_discontinued'] = False
                item_dict['plan_id'] = str(plan_id) if plan_id else None
            elif plan_status == 'active':
                item_dict['display_status'] = 'active'
                item_dict['status_badge'] = 'info'
                item_dict['status_text'] = 'Active'
                item_dict['status_icon'] = '▶'
                item_dict['is_discontinued'] = False
                item_dict['plan_id'] = str(plan_id) if plan_id else None
            else:
                # Service or Medicine (no package plan)
                item_dict['display_status'] = 'active'
                item_dict['status_badge'] = 'secondary'
                item_dict['status_text'] = 'Active'
                item_dict['status_icon'] = ''
                item_dict['is_discontinued'] = False

            line_items_dict.append(item_dict)

        # Add line items to invoice dictionary
        invoice_dict['line_items'] = line_items_dict

        # Check for consolidated prescription
        invoice_dict['is_consolidated_prescription'] = False
        if invoice.invoice_type == 'Service':
            for item_dict in line_items_dict:
                if item_dict.get('item_name') == "Doctor's Examination and Treatment":
                    invoice_dict['is_consolidated_prescription'] = True
                    break

        return invoice_dict

    except Exception as e:
        logger.error(f"Error getting invoice by ID: {str(e)}")
        raise

def search_invoices(
    hospital_id: uuid.UUID,
    filters: Dict = None,
    page: int = 1,
    page_size: int = 10,
    session: Optional[Session] = None
) -> Dict:
    """
    Search invoices with filters and pagination
    
    Args:
        hospital_id: Hospital UUID
        filters: Search filters
        page: Page number
        page_size: Page size
        session: Database session (optional)
        
    Returns:
        Dict with invoices, count, and pagination info
    """
    if session is not None:
        return _search_invoices(session, hospital_id, filters, page, page_size)
    
    with get_db_session() as new_session:
        return _search_invoices(new_session, hospital_id, filters, page, page_size)

def _search_invoices(
    session: Session,
    hospital_id: uuid.UUID,
    filters: Dict = None,
    page: int = 1,
    page_size: int = 10
) -> Dict:
    """
    Internal function to search invoices with filters and pagination
    """
    try:
        # Start with base query
        query = session.query(InvoiceHeader).filter_by(hospital_id=hospital_id)
        
        # Apply filters if provided
        if filters:
            if 'invoice_number' in filters and filters['invoice_number']:
                query = query.filter(InvoiceHeader.invoice_number.ilike(f"%{filters['invoice_number']}%"))
                
            if 'patient_id' in filters and filters['patient_id']:
                query = query.filter(InvoiceHeader.patient_id == filters['patient_id'])
                
            if 'invoice_type' in filters and filters['invoice_type']:
                query = query.filter(InvoiceHeader.invoice_type == filters['invoice_type'])
                
            if 'is_gst_invoice' in filters:
                query = query.filter(InvoiceHeader.is_gst_invoice == filters['is_gst_invoice'])
                
            if 'date_from' in filters and filters['date_from']:
                query = query.filter(InvoiceHeader.invoice_date >= filters['date_from'])
                
            if 'date_to' in filters and filters['date_to']:
                query = query.filter(InvoiceHeader.invoice_date <= filters['date_to'])
                
            if 'payment_status' in filters and filters['payment_status']:
                if filters['payment_status'] == 'paid':
                    query = query.filter(InvoiceHeader.balance_due == 0)
                elif filters['payment_status'] == 'partial':
                    query = query.filter(InvoiceHeader.paid_amount > 0, InvoiceHeader.balance_due > 0)
                elif filters['payment_status'] == 'unpaid':
                    query = query.filter(InvoiceHeader.paid_amount == 0)
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(InvoiceHeader.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Get results
        invoices = query.all()
        
        # Create detached copies
        invoice_dicts = []
        for invoice in invoices:
            invoice_dict = get_entity_dict(invoice)
            
            # Get patient name
            from app.models.master import Patient
            patient = session.query(Patient).filter_by(patient_id=invoice.patient_id).first()
            if patient:
                invoice_dict['patient_name'] = patient.full_name
                invoice_dict['patient_mrn'] = patient.mrn
            
            invoice_dicts.append(invoice_dict)
        
        # Calculate pagination info
        total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
        
        return {
            'items': invoice_dicts,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'pages': total_pages
        }
        
    except Exception as e:
        logger.error(f"Error searching invoices: {str(e)}")
        raise

# In billing_service.py, update the record_payment function with explicit commit

def record_payment(
    hospital_id, invoice_id, payment_date,
    cash_amount=Decimal('0'), credit_card_amount=Decimal('0'),
    debit_card_amount=Decimal('0'), upi_amount=Decimal('0'),
    card_number_last4=None, card_type=None, upi_id=None,
    reference_number=None, handle_excess=True, recorded_by=None,
    save_as_draft=False, approval_threshold=Decimal('100000'), session=None
):
    """
    Record a payment against an invoice with approval workflow support

    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        payment_date: Payment date
        cash_amount: Cash payment amount
        credit_card_amount: Credit card payment amount
        debit_card_amount: Debit card payment amount
        upi_amount: UPI payment amount
        card_number_last4: Last 4 digits of card (for card payments)
        card_type: Type of card (for card payments)
        upi_id: UPI ID (for UPI payments)
        reference_number: Payment reference number
        handle_excess: Whether to create advance payment for excess amount
        recorded_by: ID of the user recording the payment
        save_as_draft: Save as draft without posting (default: False)
        approval_threshold: Amount threshold requiring approval (default: ₹100,000)
        session: Database session (optional)

    Returns:
        Dictionary containing created payment details and workflow status
    """
    if session is not None:
        # If session is provided, use it without committing
        return _record_payment(
            session, hospital_id, invoice_id, payment_date,
            cash_amount, credit_card_amount, debit_card_amount, upi_amount,
            card_number_last4, card_type, upi_id, reference_number,
            handle_excess, recorded_by, save_as_draft, approval_threshold
        )

    # If no session provided, create a new one and explicitly commit
    with get_db_session() as new_session:
        result = _record_payment(
            new_session, hospital_id, invoice_id, payment_date,
            cash_amount, credit_card_amount, debit_card_amount, upi_amount,
            card_number_last4, card_type, upi_id, reference_number,
            handle_excess, recorded_by, save_as_draft, approval_threshold
        )

        # Add explicit commit for this critical operation
        new_session.commit()

        # Invalidate payment receipts cache
        try:
            from app.engine.universal_service_cache import invalidate_service_cache_for_entity
            invalidate_service_cache_for_entity('patient_payment_receipts', cascade=False)
            logger.info("Invalidated patient_payment_receipts cache after recording payment")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")

        return result

def _record_payment(
    session, hospital_id, invoice_id, payment_date,
    cash_amount=Decimal('0'), credit_card_amount=Decimal('0'),
    debit_card_amount=Decimal('0'), upi_amount=Decimal('0'),
    card_number_last4=None, card_type=None, upi_id=None,
    reference_number=None, handle_excess=True, recorded_by=None,
    save_as_draft=False, approval_threshold=Decimal('100000')
):
    """Internal function to record a payment against an invoice in the database with workflow support"""
    try:
        # Get the invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Calculate total payment amount
        total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount

        # ============================================================================
        # WORKFLOW STATUS DETERMINATION
        # ============================================================================
        from datetime import datetime, timezone

        # Determine workflow status based on draft flag and approval threshold
        if save_as_draft:
            workflow_status = 'draft'
            requires_approval = False
            should_post_gl = False
            logger.info(f"Payment saved as draft - will not post GL entries")
        elif total_payment >= approval_threshold:
            workflow_status = 'pending_approval'
            requires_approval = True
            should_post_gl = False
            logger.info(f"Payment amount {total_payment} >= threshold {approval_threshold} - requires approval")
        else:
            workflow_status = 'approved'
            requires_approval = False
            should_post_gl = True
            logger.info(f"Payment amount {total_payment} < threshold {approval_threshold} - auto-approved")

        # Check if payment exceeds balance due - now just a warning
        excess_amount = Decimal('0')
        if total_payment > invoice.balance_due:
            excess_amount = total_payment - invoice.balance_due
            logger.warning(f"Payment amount {total_payment} exceeds balance due {invoice.balance_due}. Excess: {excess_amount}")

        # Determine how much of the payment to apply to this invoice
        payment_to_apply = min(total_payment, invoice.balance_due)
        remaining_payment = total_payment - payment_to_apply
        
        # Create payment record for primary invoice with full amount
        # (this maintains backward compatibility with existing reports/queries)
        payment = PaymentDetail(
            hospital_id=hospital_id,
            invoice_id=invoice_id,
            payment_date=payment_date,
            cash_amount=cash_amount,
            credit_card_amount=credit_card_amount,
            debit_card_amount=debit_card_amount,
            upi_amount=upi_amount,
            currency_code=invoice.currency_code,
            exchange_rate=invoice.exchange_rate,
            card_number_last4=card_number_last4,
            card_type=card_type,
            upi_id=upi_id,
            reference_number=reference_number,
            total_amount=total_payment,
            reconciliation_status='pending',
            # Workflow fields
            workflow_status=workflow_status,
            requires_approval=requires_approval,
            gl_posted=False,  # Will be set to True after GL posting
            is_deleted=False,
            is_reversed=False
        )

        # Set workflow tracking fields
        if recorded_by:
            payment.created_by = recorded_by

            # Set submission tracking (if not draft)
            if workflow_status != 'draft':
                payment.submitted_by = recorded_by
                payment.submitted_at = datetime.now(timezone.utc)

            # Set approval tracking (if auto-approved)
            if workflow_status == 'approved':
                payment.approved_by = recorded_by
                payment.approved_at = datetime.now(timezone.utc)
            
        session.add(payment)
        # REMOVED: session.flush() - Causes UUID comparison error when existing payments are loaded
        # Payment ID will be available after commit

        # Add debug logging to verify values before update
        logger.debug(f"Before update: Invoice {invoice.invoice_number}, paid={invoice.paid_amount}, balance={invoice.balance_due}")
        
        # Update primary invoice with the amount that applies to it
        invoice.paid_amount += payment_to_apply
        invoice.balance_due -= payment_to_apply
        
        if invoice.balance_due <= 0:
            invoice.balance_due = Decimal('0')
            
        if recorded_by:
            invoice.updated_by = recorded_by
            
        # Add debug logging to verify values after update
        logger.debug(f"After update: Invoice {invoice.invoice_number}, paid={invoice.paid_amount}, balance={invoice.balance_due}")

        # Create GL entries for this payment (only if auto-approved)
        # NOTE: We need to flush to get payment_id before GL posting
        if should_post_gl:
            try:
                # Flush to get payment_id (UUID fix ensures no comparison errors)
                session.flush()

                # Import here to avoid circular imports
                from app.services.gl_service import create_payment_gl_entries
                create_payment_gl_entries(payment.payment_id, recorded_by, session=session)

                # Mark payment as GL posted
                payment.gl_posted = True
                payment.posting_date = datetime.now(timezone.utc)
                logger.info(f"GL entries posted for payment {payment.payment_id}")

            except Exception as e:
                logger.warning(f"Error creating payment GL entries: {str(e)}")
                # Continue without GL entries as this is not critical for payment recording
        else:
            logger.info(f"GL posting skipped - payment status is {workflow_status}")
        
        # Create AR subledger entries for payment with line-item allocation (only if auto-approved)
        if should_post_gl:  # Only create AR entry when GL is posted
            try:
                from app.services.subledger_service import create_ar_subledger_entry, get_line_item_ar_balance
                from app.models.transaction import InvoiceLineItem
                from sqlalchemy import case

                # Get GL transaction if available
                gl_transaction_id = None
                if payment.gl_entry_id:
                    gl_transaction_id = payment.gl_entry_id

                # Get invoice line items ordered by payment priority (Medicine → Service → Package)
                line_items = session.query(InvoiceLineItem).filter(
                    InvoiceLineItem.invoice_id == invoice_id
                ).order_by(
                    case(
                        (InvoiceLineItem.item_type == 'Medicine', 1),  # Priority 1 - Medicine FIRST
                        (InvoiceLineItem.item_type == 'Service', 2),   # Priority 2 - Service SECOND
                        (InvoiceLineItem.item_type == 'Package', 3),   # Priority 3 - Package LAST
                        else_=4
                    ),
                    InvoiceLineItem.line_item_id
                ).all()

                remaining_payment = total_payment
                allocation_log = []

                logger.info(f"Allocating payment of ₹{total_payment} across {len(line_items)} line items (Priority: Medicine → Service → Package)")

                for line_item in line_items:
                    if remaining_payment <= 0:
                        logger.debug(f"  Line item {line_item.item_name}: ₹0 (no payment remaining)")
                        break

                    # Get current AR balance for this line item
                    try:
                        line_balance = get_line_item_ar_balance(
                            hospital_id=hospital_id,
                            patient_id=invoice.patient_id,
                            line_item_id=line_item.line_item_id,
                            session=session
                        )
                    except Exception as balance_err:
                        logger.warning(f"Could not get balance for line item {line_item.line_item_id}: {balance_err}")
                        line_balance = line_item.line_total  # Fallback to line total

                    if line_balance <= 0:
                        logger.debug(f"  {line_item.item_type} - {line_item.item_name}: Already paid (balance: ₹{line_balance})")
                        continue  # Already paid or overpaid

                    # Allocate payment to this line item
                    allocated = min(line_balance, remaining_payment)

                    # Create AR credit entry for this line item
                    create_ar_subledger_entry(
                        session=session,
                        hospital_id=hospital_id,
                        branch_id=invoice.branch_id,
                        patient_id=invoice.patient_id,
                        entry_type='payment',
                        reference_id=payment.payment_id,
                        reference_type='payment',
                        reference_number=reference_number or f"PAY-{payment.payment_id}",
                        reference_line_item_id=line_item.line_item_id,  # ✅ Line item reference
                        debit_amount=Decimal('0'),
                        credit_amount=allocated,  # ✅ Allocated amount (not total payment)
                        transaction_date=payment_date,
                        gl_transaction_id=gl_transaction_id,
                        current_user_id=recorded_by
                    )

                    remaining_payment -= allocated
                    balance_after = line_balance - allocated

                    allocation_log.append({
                        'line_item_id': str(line_item.line_item_id),
                        'item_type': line_item.item_type,
                        'item_name': line_item.item_name,
                        'line_total': float(line_item.line_total),
                        'balance_before': float(line_balance),
                        'allocated': float(allocated),
                        'balance_after': float(balance_after)
                    })

                    logger.info(f"  ✓ {line_item.item_type} - {line_item.item_name}: Allocated ₹{allocated} (balance: ₹{line_balance} → ₹{balance_after})")

                logger.info(f"✓ Payment allocated across {len(allocation_log)} line items. Remaining: ₹{remaining_payment}")

                # Log allocation details at debug level
                if allocation_log:
                    logger.debug(f"Allocation details: {allocation_log}")

            except Exception as e:
                logger.error(f"Error creating AR subledger entries with allocation: {str(e)}", exc_info=True)
                # Continue - AR subledger is not critical for payment recording
        
        # Distribute excess payment to related invoices if any
        if remaining_payment > 0:
            try:
                # Find related invoices (created within 5 minutes of this invoice)
                created_time = invoice.created_at
                time_window = timedelta(minutes=5)
                
                related_invoices = session.query(InvoiceHeader).filter(
                    InvoiceHeader.hospital_id == hospital_id,
                    InvoiceHeader.patient_id == invoice.patient_id,
                    InvoiceHeader.created_at >= created_time - time_window,
                    InvoiceHeader.created_at <= created_time + time_window,
                    InvoiceHeader.invoice_id != invoice_id,
                    InvoiceHeader.is_cancelled == False,  # Exclude cancelled invoices
                    InvoiceHeader.balance_due > 0  # Only those with outstanding balance
                ).order_by(InvoiceHeader.invoice_date).all()
                
                logger.info(f"Found {len(related_invoices)} related invoices with outstanding balance")
                
                # Distribute remaining payment to related invoices
                for related in related_invoices:
                    if remaining_payment <= 0:
                        break
                        
                    payment_for_related = min(remaining_payment, related.balance_due)
                    
                    logger.info(f"Distributing {payment_for_related} to related invoice {related.invoice_number}")
                    
                    # Proportionally distribute payment methods
                    proportion = payment_for_related / total_payment if total_payment > 0 else 0
                    related_cash = cash_amount * proportion if cash_amount > 0 else Decimal('0')
                    related_credit = credit_card_amount * proportion if credit_card_amount > 0 else Decimal('0')
                    related_debit = debit_card_amount * proportion if debit_card_amount > 0 else Decimal('0')
                    related_upi = upi_amount * proportion if upi_amount > 0 else Decimal('0')
                    
                    # Create payment record for related invoice
                    related_payment = PaymentDetail(
                        hospital_id=hospital_id,
                        invoice_id=related.invoice_id,
                        payment_date=payment_date,
                        cash_amount=related_cash,
                        credit_card_amount=related_credit,
                        debit_card_amount=related_debit,
                        upi_amount=related_upi,
                        currency_code=related.currency_code,
                        exchange_rate=related.exchange_rate,
                        card_number_last4=card_number_last4,
                        card_type=card_type,
                        upi_id=upi_id,
                        reference_number=reference_number,
                        total_amount=payment_for_related,
                        reconciliation_status='pending',
                        notes=f"Auto-distributed from excess payment for invoice {invoice.invoice_number}",
                        # Workflow fields (same as primary payment)
                        workflow_status=workflow_status,
                        requires_approval=requires_approval,
                        gl_posted=False,
                        is_deleted=False,
                        is_reversed=False
                    )

                    # Set workflow tracking fields
                    if recorded_by:
                        related_payment.created_by = recorded_by

                        # Set submission tracking (if not draft)
                        if workflow_status != 'draft':
                            related_payment.submitted_by = recorded_by
                            related_payment.submitted_at = datetime.now(timezone.utc)

                        # Set approval tracking (if auto-approved)
                        if workflow_status == 'approved':
                            related_payment.approved_by = recorded_by
                            related_payment.approved_at = datetime.now(timezone.utc)
                        
                    session.add(related_payment)
                    session.flush()

                    # Update related invoice
                    related.paid_amount += payment_for_related
                    related.balance_due -= payment_for_related
                    
                    if related.balance_due <= 0:
                        related.balance_due = Decimal('0')
                    
                    if recorded_by:
                        related.updated_by = recorded_by
                        
                    # Reduce remaining payment
                    remaining_payment -= payment_for_related
                    
                    logger.info(f"After distribution: Invoice {related.invoice_number}, paid={related.paid_amount}, balance={related.balance_due}")

                    # Create AR subledger entry for related payment (only if auto-approved)
                    if should_post_gl:
                        try:
                            from app.services.subledger_service import create_ar_subledger_entry

                            # Get GL transaction if available
                            gl_transaction_id = None
                            if related_payment.gl_entry_id:
                                gl_transaction_id = related_payment.gl_entry_id

                            create_ar_subledger_entry(
                                session=session,
                                hospital_id=hospital_id,
                                branch_id=related.branch_id,
                                patient_id=related.patient_id,
                                entry_type='payment',
                                reference_id=related_payment.payment_id,
                                reference_type='payment',
                                reference_number=reference_number or f"PAY-{related_payment.payment_id}",
                                debit_amount=Decimal('0'),
                                credit_amount=payment_for_related,
                                transaction_date=payment_date,
                                gl_transaction_id=gl_transaction_id,
                                current_user_id=recorded_by
                            )
                            logger.info(f"AR subledger entry created for related payment {related_payment.payment_id}")

                        except Exception as e:
                            logger.warning(f"Error creating AR subledger for related payment: {str(e)}")
                            # Continue - AR subledger is not critical
                
                # If there's still remaining payment after applying to all related invoices
                # and handle_excess is True, create an advance payment
                if remaining_payment > 0 and handle_excess:
                    logger.info(f"Creating advance payment of {remaining_payment} from excess payment")
                    
                    # Create advance payment record
                    advance_payment = _handle_excess_payment(
                        session=session,
                        hospital_id=hospital_id,
                        patient_id=invoice.patient_id,
                        invoice_id=invoice_id,
                        payment_id=payment.payment_id,
                        excess_amount=remaining_payment,
                        payment_date=payment_date,
                        notes=f"Excess payment from invoice #{invoice.invoice_number}",
                        current_user_id=recorded_by
                    )
                    
                    logger.info(f"Created advance payment: {advance_payment['advance_id']}")
                
            except Exception as e:
                logger.warning(f"Error handling excess payment: {str(e)}")
                # Continue without handling excess as this is an enhancement to existing functionality
        
        # Return the created payment with excess amount information
        result = get_entity_dict(payment)
        
        # Add excess amount information
        if excess_amount > 0 and handle_excess:
            result['excess_amount'] = excess_amount
            result['excess_handled'] = True
        
        return result
        
    except Exception as e:
        logger.error(f"Error recording payment: {str(e)}")
        # Don't rollback here - let the calling function handle transaction management
        raise


# ============================================================================
# MULTI-INVOICE PAYMENT RECORDING
# ============================================================================

def record_multi_invoice_payment(
    hospital_id,
    invoice_allocations,  # List of {invoice_id, allocated_amount}
    payment_date,
    cash_amount=Decimal('0'),
    credit_card_amount=Decimal('0'),
    debit_card_amount=Decimal('0'),
    upi_amount=Decimal('0'),
    card_number_last4=None,
    card_type=None,
    upi_id=None,
    reference_number=None,
    recorded_by=None,
    save_as_draft=False,
    approval_threshold=Decimal('100000'),
    allow_overpayment=False,  # ✅ NEW: Require explicit confirmation for overpayments
    session=None
):
    """
    Record a SINGLE payment allocated across MULTIPLE invoices

    Creates:
    - ONE payment_details record (invoice_id = NULL for multi-invoice)
    - Multiple ar_subledger entries linking payment to invoices
    - Updates each invoice's paid_amount and balance_due

    Args:
        hospital_id: Hospital UUID
        invoice_allocations: List of dicts with 'invoice_id' and 'allocated_amount'
                            Example: [
                                {'invoice_id': 'uuid1', 'allocated_amount': Decimal('2000')},
                                {'invoice_id': 'uuid2', 'allocated_amount': Decimal('1500')}
                            ]
        payment_date: Payment date
        cash_amount, credit_card_amount, debit_card_amount, upi_amount: Payment method breakdowns
        card_number_last4, card_type, upi_id: Payment method details
        reference_number: Payment reference number
        recorded_by: User ID recording the payment
        save_as_draft: Save as draft without posting
        approval_threshold: Amount threshold requiring approval
        session: Database session (optional)

    Returns:
        Dictionary containing created payment details and allocation info
    """
    if session is not None:
        return _record_multi_invoice_payment(
            session, hospital_id, invoice_allocations, payment_date,
            cash_amount, credit_card_amount, debit_card_amount, upi_amount,
            card_number_last4, card_type, upi_id, reference_number,
            recorded_by, save_as_draft, approval_threshold, allow_overpayment
        )

    # Create new session and commit
    with get_db_session() as new_session:
        try:
            result = _record_multi_invoice_payment(
                new_session, hospital_id, invoice_allocations, payment_date,
                cash_amount, credit_card_amount, debit_card_amount, upi_amount,
                card_number_last4, card_type, upi_id, reference_number,
                recorded_by, save_as_draft, approval_threshold, allow_overpayment
            )

            # Commit the transaction
            new_session.commit()
            logger.info("✅ Transaction committed successfully")

            # Invalidate cache (after successful commit)
            try:
                from app.engine.universal_service_cache import invalidate_service_cache_for_entity
                invalidate_service_cache_for_entity('patient_payment_receipts', cascade=False)
                logger.info("Invalidated patient_payment_receipts cache after multi-invoice payment")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {str(e)}")

            return result

        except Exception as e:
            # Rollback on any error
            new_session.rollback()
            logger.error(f"❌ Transaction rolled back due to error: {str(e)}")
            raise


def _record_multi_invoice_payment(
    session,
    hospital_id,
    invoice_allocations,
    payment_date,
    cash_amount,
    credit_card_amount,
    debit_card_amount,
    upi_amount,
    card_number_last4,
    card_type,
    upi_id,
    reference_number,
    recorded_by,
    save_as_draft,
    approval_threshold,
    allow_overpayment
):
    """Internal function to record multi-invoice payment"""
    try:
        from datetime import datetime, timezone

        # Validate input
        if not invoice_allocations or len(invoice_allocations) == 0:
            raise ValueError("invoice_allocations must contain at least one invoice")

        # Calculate total payment amount
        total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount

        # Calculate total allocated amount to invoices
        total_allocated = sum(Decimal(str(alloc.get('allocated_amount', 0))) for alloc in invoice_allocations)

        # NOTE: We don't validate total_payment == total_allocated here because:
        # - Payment may also be allocated to package installments (handled separately)
        # - Payment may be partially allocated (overpayment scenario)
        # - User manually specifies allocation amounts in the form

        logger.info(f"💰 Multi-invoice payment: Total payment methods = ₹{total_payment}, Total to invoices = ₹{total_allocated}")

        # Get patient_id from first invoice (all invoices should be for same patient)
        first_invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id,
            invoice_id=invoice_allocations[0]['invoice_id']
        ).first()

        if not first_invoice:
            raise ValueError(f"First invoice {invoice_allocations[0]['invoice_id']} not found")

        patient_id = first_invoice.patient_id

        # ========================================================================
        # VALIDATE INVOICE BALANCES AND DETECT OVERPAYMENTS
        # ========================================================================
        # Check each invoice to see if it's already fully paid
        overpayment_warnings = []

        for alloc in invoice_allocations:
            invoice = session.query(InvoiceHeader).filter_by(
                hospital_id=hospital_id,
                invoice_id=alloc['invoice_id']
            ).first()

            if not invoice:
                continue

            allocated_amount = Decimal(str(alloc['allocated_amount']))

            # Check if invoice is fully paid
            if invoice.balance_due <= 0:
                overpayment_warnings.append({
                    'invoice_id': str(invoice.invoice_id),
                    'invoice_number': invoice.invoice_number,
                    'balance_due': float(invoice.balance_due),
                    'allocated_amount': float(allocated_amount),
                    'message': f"Invoice {invoice.invoice_number} is already fully paid (balance: ₹{invoice.balance_due}). Payment of ₹{allocated_amount} will be recorded as advance."
                })
            # Check if payment exceeds remaining balance
            elif allocated_amount > invoice.balance_due:
                excess = allocated_amount - invoice.balance_due
                overpayment_warnings.append({
                    'invoice_id': str(invoice.invoice_id),
                    'invoice_number': invoice.invoice_number,
                    'balance_due': float(invoice.balance_due),
                    'allocated_amount': float(allocated_amount),
                    'excess_amount': float(excess),
                    'message': f"Invoice {invoice.invoice_number} has balance ₹{invoice.balance_due} but payment is ₹{allocated_amount}. Excess ₹{excess} will be recorded as advance."
                })

        # If there are overpayment warnings, check if explicitly allowed
        if overpayment_warnings and not allow_overpayment:
            logger.error(f"🚫 Overpayment detected for {len(overpayment_warnings)} invoice(s) - Blocking transaction")
            for warning in overpayment_warnings:
                logger.error(f"  - {warning['message']}")

            # Return error with detailed warnings for user confirmation
            return {
                'success': False,
                'error': 'overpayment_detected',
                'message': 'One or more invoices would be overpaid. Please review and confirm.',
                'overpayment_warnings': overpayment_warnings,
                'requires_confirmation': True
            }

        # If overpayment is explicitly allowed, log it
        if overpayment_warnings and allow_overpayment:
            logger.warning(f"⚠️ Overpayment detected for {len(overpayment_warnings)} invoice(s) - ALLOWED by user")
            for warning in overpayment_warnings:
                logger.warning(f"  - {warning['message']}")

        # Determine workflow status
        if save_as_draft:
            workflow_status = 'draft'
            requires_approval = False
            should_post_gl = False
        elif total_payment >= approval_threshold:
            workflow_status = 'pending_approval'
            requires_approval = True
            should_post_gl = False
        else:
            workflow_status = 'approved'
            requires_approval = False
            should_post_gl = True

        # ========================================================================
        # CREATE PAYMENT_DETAILS RECORD (invoice_id = NULL for multi-invoice)
        # ========================================================================

        payment = PaymentDetail(
            payment_id=uuid.uuid4(),
            hospital_id=hospital_id,
            invoice_id=None,  # ✅ NULL for multi-invoice payments
            payment_date=payment_date,
            total_amount=total_payment,
            cash_amount=cash_amount,
            credit_card_amount=credit_card_amount,
            debit_card_amount=debit_card_amount,
            upi_amount=upi_amount,
            card_number_last4=card_number_last4,
            card_type=card_type,
            upi_id=upi_id,
            reference_number=reference_number,
            workflow_status=workflow_status,
            requires_approval=requires_approval,
            gl_posted=False,
            created_by=recorded_by or 'system',
            created_at=datetime.now(timezone.utc),
            is_deleted=False
        )

        # ✅ Set submission tracking (if not draft)
        if workflow_status != 'draft':
            payment.submitted_by = recorded_by or 'system'
            payment.submitted_at = datetime.now(timezone.utc)

        if workflow_status == 'approved':
            payment.approved_by = recorded_by or 'system'
            payment.approved_at = datetime.now(timezone.utc)

        session.add(payment)
        session.flush()  # Get payment_id

        # ✅ Populate new traceability fields (Added: 2025-11-15)
        payment.patient_id = patient_id
        payment.branch_id = first_invoice.branch_id
        payment.payment_source = 'multi_invoice'
        payment.invoice_count = len(invoice_allocations)
        payment.recorded_by = recorded_by

        logger.info(f"✓ Created payment {payment.payment_id} for ₹{total_payment} across {len(invoice_allocations)} invoices")

        # ========================================================================
        # POST GL ENTRIES (if auto-approved)
        # ========================================================================
        gl_transaction_id = None
        if should_post_gl:
            try:
                from app.services.gl_service import create_multi_invoice_payment_gl_entries
                logger.info(f"📊 Creating GL entries for multi-invoice payment...")

                gl_result = create_multi_invoice_payment_gl_entries(
                    payment_id=payment.payment_id,
                    invoice_count=len(invoice_allocations),
                    current_user_id=recorded_by,  # Fixed: was created_by (undefined variable)
                    session=session
                )

                if gl_result and gl_result.get('success'):
                    gl_transaction_id = gl_result.get('transaction_id')
                    logger.info(f"✅ GL transaction created: {gl_transaction_id}")
                else:
                    logger.warning(f"⚠️ GL posting failed but payment created: {gl_result.get('error', 'Unknown error')}")
                    gl_transaction_id = None

            except Exception as e:
                logger.error(f"❌ Error creating GL entries: {e}", exc_info=True)
                # Don't fail the whole payment if GL posting fails
                gl_transaction_id = None

        # ========================================================================
        # CREATE AR_SUBLEDGER ENTRIES FOR EACH INVOICE ALLOCATION (LINE-ITEM LEVEL)
        # ========================================================================
        # ✅ CRITICAL FIX: AR entries must ALWAYS be created, regardless of GL posting status
        # AR tracks invoice payments immediately, GL posting can be deferred until approval

        allocation_results = []

        try:
            from app.services.subledger_service import create_ar_subledger_entry

            # Wrap entire AR entry creation in no_autoflush to prevent premature flushes
            with session.no_autoflush:
                for alloc in invoice_allocations:
                    invoice_id = alloc['invoice_id']
                    allocated_amount_for_invoice = Decimal(str(alloc['allocated_amount']))

                    # Get invoice details
                    invoice = session.query(InvoiceHeader).filter_by(
                        hospital_id=hospital_id,
                        invoice_id=invoice_id
                    ).first()

                    if not invoice:
                        logger.warning(f"Invoice {invoice_id} not found - skipping allocation")
                        continue

                    # ✅ Get invoice line items ordered by PAYMENT PRIORITY: Medicine → Service → Package
                    line_items = session.query(InvoiceLineItem).filter(
                        InvoiceLineItem.invoice_id == invoice_id
                    ).order_by(
                        case(
                            (InvoiceLineItem.item_type == 'Medicine', 1),  # Priority 1 - Medicine FIRST
                            (InvoiceLineItem.item_type == 'Service', 2),   # Priority 2 - Service SECOND
                            (InvoiceLineItem.item_type == 'Package', 3),   # Priority 3 - Package LAST
                            else_=4
                        ),
                        InvoiceLineItem.line_item_id
                    ).all()

                    remaining_for_invoice = allocated_amount_for_invoice
                    line_allocation_log = []

                    logger.info(f"  Allocating ₹{allocated_amount_for_invoice} to invoice {invoice.invoice_number} across {len(line_items)} line items")

                    # ✅ Allocate payment across LINE ITEMS in priority order
                    for line_item in line_items:
                        if remaining_for_invoice <= 0:
                            break

                        # Get current AR balance for this line item
                        try:
                            line_balance = get_line_item_ar_balance(
                                hospital_id=hospital_id,
                                patient_id=invoice.patient_id,
                                line_item_id=line_item.line_item_id,
                                session=session
                            )
                        except Exception as balance_err:
                            logger.warning(f"Could not get balance for line item {line_item.line_item_id}: {balance_err}")
                            line_balance = line_item.line_total  # Fallback to line total

                        if line_balance <= 0:
                            logger.debug(f"    {line_item.item_type} - {line_item.item_name}: Already paid (balance: ₹{line_balance})")
                            continue  # Already paid

                        # ✅ Allocate to this LINE ITEM
                        allocated_to_line = min(line_balance, remaining_for_invoice)

                        # ✅ Create AR credit entry for this LINE ITEM
                        create_ar_subledger_entry(
                            session=session,
                            hospital_id=hospital_id,
                            branch_id=invoice.branch_id,
                            patient_id=invoice.patient_id,
                            entry_type='payment',
                            reference_id=payment.payment_id,  # Payment ID
                            reference_type='payment',
                            reference_number=reference_number or f"PAY-{payment.payment_id}",
                            reference_line_item_id=line_item.line_item_id,  # ✅ LINE ITEM reference
                            debit_amount=Decimal('0'),
                            credit_amount=allocated_to_line,  # ✅ Allocated to THIS line item
                            transaction_date=payment_date,
                            gl_transaction_id=gl_transaction_id,
                            current_user_id=recorded_by
                        )

                        remaining_for_invoice -= allocated_to_line
                        balance_after = line_balance - allocated_to_line

                        line_allocation_log.append({
                            'line_item_id': str(line_item.line_item_id),
                            'item_type': line_item.item_type,
                            'item_name': line_item.item_name,
                            'line_total': float(line_item.line_total),
                            'balance_before': float(line_balance),
                            'allocated': float(allocated_to_line),
                            'balance_after': float(balance_after)
                        })

                        logger.info(f"    ✓ {line_item.item_type} - {line_item.item_name}: Allocated ₹{allocated_to_line} (balance: ₹{line_balance} → ₹{balance_after})")

                    # Update invoice paid amount and balance
                    actual_allocated = allocated_amount_for_invoice - remaining_for_invoice
                    invoice.paid_amount = (invoice.paid_amount or Decimal('0')) + actual_allocated
                    invoice.balance_due = invoice.grand_total - invoice.paid_amount

                    allocation_results.append({
                        'invoice_id': str(invoice_id),
                        'invoice_number': invoice.invoice_number,
                        'allocated_amount': float(actual_allocated),
                        'invoice_total': float(invoice.grand_total),
                        'new_balance': float(invoice.balance_due),
                        'line_items_allocated': len(line_allocation_log)
                    })

                    logger.info(f"  ✓ Invoice {invoice.invoice_number}: Allocated ₹{actual_allocated} across {len(line_allocation_log)} line items (balance: ₹{invoice.balance_due})")

                logger.info(f"✓ Created AR subledger entries for {len(allocation_results)} invoices with line-item level allocation")

        except Exception as e:
            logger.error(f"Error creating AR subledger entries: {str(e)}")
            raise

        return {
            'success': True,
            'payment_id': str(payment.payment_id),
            'total_amount': float(total_payment),
            'workflow_status': workflow_status,
            'requires_approval': requires_approval,
            'gl_posted': payment.gl_posted,
            'invoice_count': len(invoice_allocations),
            'allocations': allocation_results,
            'overpayment_warnings': overpayment_warnings,  # ✅ NEW: Include overpayment warnings
            'has_overpayment': len(overpayment_warnings) > 0,  # ✅ NEW: Flag for easy checking
            'message': f"Payment of ₹{total_payment} recorded across {len(invoice_allocations)} invoices"
        }

    except Exception as e:
        logger.error(f"❌ FATAL ERROR in multi-invoice payment: {str(e)}", exc_info=True)
        logger.error(f"❌ Payment will be rolled back. No partial data will be saved.")
        raise


# ============================================================================
# PAYMENT WORKFLOW FUNCTIONS
# ============================================================================

def approve_payment(
    payment_id: uuid.UUID,
    approved_by: str,
    hospital_id: uuid.UUID,
    session: Optional[Session] = None
) -> Dict:
    """
    Approve a pending payment and post GL entries

    Args:
        payment_id: Payment ID to approve
        approved_by: User ID of approver
        hospital_id: Hospital ID for security check
        session: Database session (optional)

    Returns:
        Dictionary with success status and payment details
    """
    from datetime import datetime, timezone

    def _approve_payment(session, payment_id, approved_by, hospital_id):
        try:
            # Get the payment
            payment = session.query(PaymentDetail).filter_by(
                payment_id=payment_id,
                hospital_id=hospital_id
            ).first()

            if not payment:
                return {
                    'success': False,
                    'error': f"Payment {payment_id} not found"
                }

            # Verify payment is in pending_approval status
            if payment.workflow_status != 'pending_approval':
                return {
                    'success': False,
                    'error': f"Payment is not pending approval (current status: {payment.workflow_status})"
                }

            # Update workflow status
            payment.workflow_status = 'approved'
            payment.approved_by = approved_by
            payment.approved_at = datetime.now(timezone.utc)
            payment.updated_by = approved_by

            # Post GL entries
            try:
                from app.services.gl_service import create_payment_gl_entries
                create_payment_gl_entries(payment_id, approved_by, session=session)

                # Mark as GL posted
                payment.gl_posted = True
                payment.posting_date = datetime.now(timezone.utc)

                logger.info(f"GL entries posted for approved payment {payment_id}")

            except Exception as e:
                logger.error(f"Error posting GL entries for payment {payment_id}: {str(e)}")
                return {
                    'success': False,
                    'error': f"Failed to post GL entries: {str(e)}"
                }

            # Create AR subledger entry
            try:
                from app.services.subledger_service import create_ar_subledger_entry

                # Get invoice details
                invoice = session.query(InvoiceHeader).filter_by(
                    invoice_id=payment.invoice_id
                ).first()

                if invoice:
                    # Get GL transaction
                    gl_transaction = None
                    if hasattr(payment, 'gl_entry_id') and payment.gl_entry_id:
                        gl_transaction = session.query(GLTransaction).filter_by(
                            transaction_id=payment.gl_entry_id
                        ).first()

                    gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None

                    create_ar_subledger_entry(
                        session=session,
                        hospital_id=hospital_id,
                        branch_id=invoice.branch_id,
                        patient_id=invoice.patient_id,
                        entry_type='payment',
                        reference_id=payment_id,
                        reference_type='payment',
                        reference_number=payment.reference_number or f"Payment-{payment_id}",
                        debit_amount=Decimal('0'),
                        credit_amount=payment.total_amount,
                        transaction_date=payment.payment_date,
                        gl_transaction_id=gl_transaction_id,
                        current_user_id=approved_by
                    )

                    logger.info(f"Created AR subledger entry for approved payment {payment_id}")

            except Exception as e:
                logger.warning(f"Error creating AR subledger entry: {str(e)}")
                # Continue - AR subledger is not critical

            return {
                'success': True,
                'data': get_entity_dict(payment),
                'message': f"Payment {payment_id} approved successfully"
            }

        except Exception as e:
            logger.error(f"Error approving payment: {str(e)}")
            raise

    # Execute with transaction management
    if session is not None:
        return _approve_payment(session, payment_id, approved_by, hospital_id)

    with get_db_session() as new_session:
        result = _approve_payment(new_session, payment_id, approved_by, hospital_id)
        new_session.commit()

        # Invalidate cache
        try:
            from app.engine.universal_service_cache import invalidate_service_cache_for_entity
            invalidate_service_cache_for_entity('patient_payment_receipts', cascade=False)
            logger.info("Invalidated patient_payment_receipts cache after approving payment")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")

        return result


def reject_payment(
    payment_id: uuid.UUID,
    rejected_by: str,
    rejection_reason: str,
    hospital_id: uuid.UUID,
    session: Optional[Session] = None
) -> Dict:
    """
    Reject a pending payment

    Args:
        payment_id: Payment ID to reject
        rejected_by: User ID of rejector
        rejection_reason: Reason for rejection
        hospital_id: Hospital ID for security check
        session: Database session (optional)

    Returns:
        Dictionary with success status and payment details
    """
    from datetime import datetime, timezone

    def _reject_payment(session, payment_id, rejected_by, rejection_reason, hospital_id):
        try:
            # Get the payment
            payment = session.query(PaymentDetail).filter_by(
                payment_id=payment_id,
                hospital_id=hospital_id
            ).first()

            if not payment:
                return {
                    'success': False,
                    'error': f"Payment {payment_id} not found"
                }

            # Verify payment is in pending_approval status
            if payment.workflow_status != 'pending_approval':
                return {
                    'success': False,
                    'error': f"Payment is not pending approval (current status: {payment.workflow_status})"
                }

            # Update workflow status
            payment.workflow_status = 'rejected'
            payment.rejected_by = rejected_by
            payment.rejected_at = datetime.now(timezone.utc)
            payment.rejection_reason = rejection_reason
            payment.updated_by = rejected_by

            session.flush()

            logger.info(f"Payment {payment_id} rejected by {rejected_by}: {rejection_reason}")

            return {
                'success': True,
                'data': get_entity_dict(payment),
                'message': f"Payment {payment_id} rejected successfully"
            }

        except Exception as e:
            logger.error(f"Error rejecting payment: {str(e)}")
            raise

    # Execute with transaction management
    if session is not None:
        return _reject_payment(session, payment_id, rejected_by, rejection_reason, hospital_id)

    with get_db_session() as new_session:
        result = _reject_payment(new_session, payment_id, rejected_by, rejection_reason, hospital_id)
        new_session.commit()

        # Invalidate cache
        try:
            from app.engine.universal_service_cache import invalidate_service_cache_for_entity
            invalidate_service_cache_for_entity('patient_payment_receipts', cascade=False)
            logger.info("Invalidated patient_payment_receipts cache after rejecting payment")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")

        return result


def reverse_payment(
    payment_id: uuid.UUID,
    reversed_by: str,
    reversal_reason: str,
    hospital_id: uuid.UUID,
    session: Optional[Session] = None
) -> Dict:
    """
    Reverse an approved payment with GL reversal

    Args:
        payment_id: Payment ID to reverse
        reversed_by: User ID of user reversing the payment
        reversal_reason: Reason for reversal
        hospital_id: Hospital ID for security check
        session: Database session (optional)

    Returns:
        Dictionary with success status and payment details
    """
    from datetime import datetime, timezone

    def _reverse_payment(session, payment_id, reversed_by, reversal_reason, hospital_id):
        try:
            # Get the payment
            payment = session.query(PaymentDetail).filter_by(
                payment_id=payment_id,
                hospital_id=hospital_id
            ).first()

            if not payment:
                return {
                    'success': False,
                    'error': f"Payment {payment_id} not found"
                }

            # Verify payment is approved and not already reversed
            if payment.workflow_status != 'approved':
                return {
                    'success': False,
                    'error': f"Only approved payments can be reversed (current status: {payment.workflow_status})"
                }

            if payment.is_reversed:
                return {
                    'success': False,
                    'error': "Payment is already reversed"
                }

            # Verify payment has been GL posted
            if not payment.gl_posted:
                return {
                    'success': False,
                    'error': "Payment has not been GL posted and cannot be reversed"
                }

            # Get the invoice to update amounts
            invoice = session.query(InvoiceHeader).filter_by(
                invoice_id=payment.invoice_id,
                hospital_id=hospital_id
            ).first()

            if not invoice:
                return {
                    'success': False,
                    'error': f"Invoice {payment.invoice_id} not found"
                }

            # Create reversing GL entries
            reversal_gl_entry_id = None
            try:
                from app.services.gl_service import reverse_payment_gl_entries
                reversal_result = reverse_payment_gl_entries(
                    payment_id=payment_id,
                    reversal_reason=reversal_reason,
                    current_user_id=reversed_by,
                    session=session
                )

                if reversal_result.get('success'):
                    reversal_gl_entry_id = reversal_result.get('reversal_transaction_id')
                    logger.info(f"GL entries reversed for payment {payment_id}")
                else:
                    return {
                        'success': False,
                        'error': f"Failed to reverse GL entries: {reversal_result.get('error')}"
                    }

            except Exception as e:
                logger.error(f"Error reversing GL entries for payment {payment_id}: {str(e)}")
                return {
                    'success': False,
                    'error': f"Failed to reverse GL entries: {str(e)}"
                }

            # Update payment record
            payment.is_reversed = True
            payment.reversed_by = reversed_by
            payment.reversed_at = datetime.now(timezone.utc)
            payment.reversal_reason = reversal_reason
            payment.reversal_gl_entry_id = reversal_gl_entry_id
            payment.workflow_status = 'reversed'
            payment.updated_by = reversed_by

            # Update invoice amounts (reverse the payment)
            invoice.paid_amount -= payment.total_amount
            if invoice.paid_amount < 0:
                invoice.paid_amount = Decimal('0')

            invoice.balance_due += payment.total_amount
            if invoice.balance_due > invoice.total_amount:
                invoice.balance_due = invoice.total_amount

            invoice.updated_by = reversed_by

            # Create reversing AR subledger entry
            try:
                from app.services.subledger_service import create_ar_subledger_entry

                create_ar_subledger_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=invoice.branch_id,
                    patient_id=invoice.patient_id,
                    entry_type='payment_reversal',
                    reference_id=payment_id,
                    reference_type='payment_reversal',
                    reference_number=f"REV-{payment.reference_number or payment_id}",
                    debit_amount=payment.total_amount,  # Debit reverses the credit
                    credit_amount=Decimal('0'),
                    transaction_date=datetime.now(timezone.utc),
                    gl_transaction_id=reversal_gl_entry_id,
                    current_user_id=reversed_by
                )

                logger.info(f"Created reversing AR subledger entry for payment {payment_id}")

            except Exception as e:
                logger.warning(f"Error creating reversing AR subledger entry: {str(e)}")
                # Continue - AR subledger is not critical

            session.flush()

            logger.info(f"Payment {payment_id} reversed by {reversed_by}: {reversal_reason}")

            return {
                'success': True,
                'data': get_entity_dict(payment),
                'message': f"Payment {payment_id} reversed successfully",
                'reversal_gl_entry_id': reversal_gl_entry_id
            }

        except Exception as e:
            logger.error(f"Error reversing payment: {str(e)}")
            raise

    # Execute with transaction management
    if session is not None:
        return _reverse_payment(session, payment_id, reversed_by, reversal_reason, hospital_id)

    with get_db_session() as new_session:
        result = _reverse_payment(new_session, payment_id, reversed_by, reversal_reason, hospital_id)
        new_session.commit()

        # Invalidate cache
        try:
            from app.engine.universal_service_cache import invalidate_service_cache_for_entity
            invalidate_service_cache_for_entity('patient_payment_receipts', cascade=False)
            logger.info("Invalidated patient_payment_receipts cache after reversing payment")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {str(e)}")

        return result


def void_invoice(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    reason: str,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Void an invoice (mark as cancelled)
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        reason: Reason for voiding
        current_user_id: ID of the user voiding the invoice
        session: Database session (optional)
        
    Returns:
        Dictionary containing updated invoice details
    """
    # This function follows the existing pattern used in other service functions
    if session is not None:
        # If session is provided, use it directly
        return _void_invoice(session, hospital_id, invoice_id, reason, current_user_id)
    
    # If no session provided, use context manager pattern
    with get_db_session() as new_session:
        # Using the existing get_db_session that should handle commit
        result = _void_invoice(new_session, hospital_id, invoice_id, reason, current_user_id)
        
        # Explicitly commit the transaction to ensure changes are saved
        new_session.commit()
        
        return result

def _void_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    reason: str,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to void an invoice within a session
    """
    try:
        # Get the invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Store invoice number before any potential session issues
        invoice_number = invoice.invoice_number
        
        # Check if invoice has payments
        payment_count = session.query(PaymentDetail).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).count()
        
        if payment_count > 0:
            raise ValueError("Cannot void an invoice with recorded payments")
        
        # Mark the invoice as cancelled
        invoice.is_cancelled = True
        invoice.cancellation_reason = reason
        invoice.cancelled_at = datetime.now(timezone.utc)
        
        if current_user_id:
            invoice.updated_by = current_user_id
            
        # Process inventory reversals for this invoice
        _reverse_inventory_for_invoice(
            session, hospital_id, invoice_id, current_user_id
        )
        
        # Process GL reversals
        _reverse_gl_entries_for_invoice(
            session, hospital_id, invoice_id, current_user_id
        )
        
        # Make changes visible within the session
        session.flush()
        
        # Log the operation's success using the stored invoice_number
        logger.info(f"Invoice {invoice_number} successfully marked as cancelled")
        
        # Create a detached copy to return
        invoice_dict = get_entity_dict(invoice)
        
        return invoice_dict
    except Exception as e:
        # Log the error
        logger.error(f"Error voiding invoice: {str(e)}")
        # Explicitly roll back the session in case of errors
        session.rollback()
        raise

    

def get_batch_selection_for_invoice(hospital_id, medicine_id, quantity_needed):
    """
    Get available batches for a medicine for invoice creation using FIFO
    
    Args:
        hospital_id (uuid): Hospital ID
        medicine_id (uuid): Medicine ID
        quantity_needed (Decimal): Quantity needed for invoice
        
    Returns:
        List of batches with quantities
    """
    from app.services.database_service import get_db_session
    from app.models.master import Stock
    from decimal import Decimal
    import uuid
    
    batches = []
    
    with get_db_session() as session:
        # Get available batches sorted by expiry date (FIFO)
        stock_items = session.query(Stock).filter(
            Stock.hospital_id == hospital_id,
            Stock.medicine_id == medicine_id,
            Stock.quantity_available > 0
        ).order_by(Stock.expiry_date.asc()).all()
        
        remaining_quantity = Decimal(str(quantity_needed))
        
        for stock in stock_items:
            if remaining_quantity <= 0:
                break
                
            batch_quantity = min(stock.quantity_available, remaining_quantity)
            
            batches.append({
                'batch_id': str(stock.batch_id),
                'batch_number': stock.batch_number,
                'expiry_date': stock.expiry_date.strftime('%Y-%m-%d') if stock.expiry_date else None,
                'quantity_available': float(stock.quantity_available),
                'quantity_allocated': float(batch_quantity),
                'unit_cost': float(stock.unit_cost)
            })
            
            remaining_quantity -= batch_quantity
        
        # If we couldn't allocate enough, still return what we have
        return {
            'batches': batches,
            'total_available': sum(b['quantity_available'] for b in batches),
            'total_allocated': sum(b['quantity_allocated'] for b in batches),
            'is_sufficient': remaining_quantity <= 0
        }

def issue_refund(
    hospital_id: uuid.UUID,
    payment_id: uuid.UUID,
    refund_amount: Decimal,
    refund_date: datetime,
    refund_reason: str,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Issue a refund for a payment
    
    Args:
        hospital_id: Hospital UUID
        payment_id: Payment UUID
        refund_amount: Amount to refund
        refund_date: Date of refund
        refund_reason: Reason for refund
        current_user_id: ID of the user issuing the refund
        session: Database session (optional)
        
    Returns:
        Dictionary containing updated payment details
    """
    if session is not None:
        return _issue_refund(
            session, hospital_id, payment_id, refund_amount, refund_date, 
            refund_reason, current_user_id
        )
    
    with get_db_session() as new_session:
        return _issue_refund(
            new_session, hospital_id, payment_id, refund_amount, refund_date, 
            refund_reason, current_user_id
        )

def _issue_refund(
    session: Session,
    hospital_id: uuid.UUID,
    payment_id: uuid.UUID,
    refund_amount: Decimal,
    refund_date: datetime,
    refund_reason: str,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to issue a refund for a payment within a session
    """
    try:
        # Get the payment
        payment = session.query(PaymentDetail).filter_by(
            hospital_id=hospital_id, payment_id=payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")
        
        # Check if refund amount exceeds payment amount
        if refund_amount > payment.total_amount - payment.refunded_amount:
            raise ValueError(f"Refund amount {refund_amount} exceeds available amount " 
                             f"{payment.total_amount - payment.refunded_amount}")
        
        # Update payment with refund information
        payment.refunded_amount += refund_amount
        payment.refund_date = refund_date
        payment.refund_reason = refund_reason
        
        if current_user_id:
            payment.updated_by = current_user_id
            
        # Get the associated invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=payment.invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice associated with payment ID {payment_id} not found")
        
        # Update invoice totals
        invoice.paid_amount -= refund_amount
        invoice.balance_due += refund_amount
        
        if current_user_id:
            invoice.updated_by = current_user_id
            
        session.flush()
        
        # Create GL entries for this refund
        try:
            # Import here to avoid circular imports
            from app.services.gl_service import create_refund_gl_entries
            create_refund_gl_entries(payment.payment_id, refund_amount, current_user_id, session=session)
        except Exception as e:
            logger.warning(f"Error creating refund GL entries: {str(e)}")
            # Continue without GL entries as this is not critical for refund processing
        
        # Return the updated payment
        return get_entity_dict(payment)
        
    except Exception as e:
        logger.error(f"Error issuing refund: {str(e)}")
        session.rollback()
        raise

    
def _store_prescription_mapping(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    prescription_items: List[Dict],
    current_user_id: Optional[str] = None
):
    """
    Store internal mapping between an invoice and its prescription items
    
    This allows later retrieval of which specific medicines were included
    in a consolidated "Doctor's Examination and Treatment" line item
    """
    try:
        # Create a new PrescriptionInvoiceMap model and table if needed
        from app.models.transaction import PrescriptionInvoiceMap
        
        for item in prescription_items:
            mapping = PrescriptionInvoiceMap(
                hospital_id=hospital_id,
                invoice_id=invoice_id,
                medicine_id=item.get('medicine_id') or item.get('item_id'),
                medicine_name=item.get('item_name'),
                batch=item.get('batch'),
                expiry_date=item.get('expiry_date'),
                quantity=item.get('quantity'),
                unit_price=item.get('unit_price')
            )
            
            if current_user_id:
                mapping.created_by = current_user_id
                
            session.add(mapping)
            
        session.flush()
        
    except Exception as e:
        logger.warning(f"Error storing prescription mapping: {str(e)}")
        # Don't fail the entire transaction if this fails
        # Just log the error

def number_to_words(number):
    """
    Convert a number to words for the invoice
    
    Args:
        number: Numeric value to convert
        
    Returns:
        String representation of the number in words
    """
    try:
        import num2words
        
        # Convert Decimal to float for compatibility with num2words
        if isinstance(number, Decimal):
            number = float(number)
            
        # Get the integer and fractional parts
        integer_part = int(number)
        fractional_part = int(round((number - integer_part) * 100))
        
        # Convert to words
        words = num2words.num2words(integer_part, lang='en_IN').title()
        
        # Add the decimal part if present
        if fractional_part > 0:
            words += f" And {num2words.num2words(fractional_part, lang='en_IN').title()} Paise"
            
        return words
    except ImportError:
        # Fallback if num2words is not available
        return f"Rupees {number:.2f}"
    except Exception as e:
        logger.error(f"Error converting number to words: {str(e)}")
        return f"Rupees {number:.2f}"

def generate_invoice_pdf(invoice_id, hospital_id, current_user_id=None, session=None):
    """
    Generate a PDF version of the invoice
    
    Args:
        invoice_id: UUID of the invoice
        hospital_id: UUID of the hospital
        current_user_id: ID of the current user (optional)
        session: Database session (optional)
        
    Returns:
        PDF data as bytes
    """
    try:
        import tempfile
        from importlib import import_module
        
        # Check if WeasyPrint is available
        try:
            weasyprint = import_module('weasyprint')
        except ImportError:
            logger.error("WeasyPrint module not available for PDF generation")
            raise ImportError("PDF generation requires WeasyPrint module")
        
        # Use the provided session or create a new one
        if session is not None:
            pdf_data = _generate_invoice_pdf(session, invoice_id, hospital_id, current_user_id)
        else:
            with get_db_session() as new_session:
                pdf_data = _generate_invoice_pdf(new_session, invoice_id, hospital_id, current_user_id)
        
        return pdf_data
    
    except Exception as e:
        logger.error(f"Error generating invoice PDF: {str(e)}")
        raise

def _generate_invoice_pdf(session, invoice_id, hospital_id, current_user_id=None):
    """Internal function to generate PDF within a session"""
    from flask import render_template, current_app
    
    # Get invoice data
    invoice = get_invoice_by_id(hospital_id, invoice_id, session=session)
    
    # Get patient details
    patient = None
    patient_record = session.query(Patient).filter_by(
        hospital_id=hospital_id,
        patient_id=invoice['patient_id']
    ).first()
    
    if patient_record:
        patient = {
            'name': patient_record.full_name,
            'mrn': patient_record.mrn,
            'contact_info': patient_record.contact_info,
            'personal_info': {}  # Exclude personal_info to remove gender
        }
    
    # Get hospital details
    hospital = None
    hospital_record = session.query(Hospital).filter_by(
        hospital_id=hospital_id
    ).first()
    
    if hospital_record:
        hospital = {
            'name': hospital_record.name,
            'address': hospital_record.address.get('full_address', '') if hospital_record.address else '',
            'phone': hospital_record.contact_details.get('phone', '') if hospital_record.contact_details else '',
            'email': hospital_record.contact_details.get('email', '') if hospital_record.contact_details else '',
            'gst_registration_number': hospital_record.gst_registration_number
        }
    
    # Convert amount to words
    amount_in_words = number_to_words(invoice['grand_total'])
    
    # Retrieve any invoice customization settings
    use_preprinted_stationery = False
    
    # Get payments for this invoice
    payments = []
    payment_records = session.query(PaymentDetail).filter_by(
        hospital_id=hospital_id,
        invoice_id=invoice_id
    ).all()
    
    for payment in payment_records:
        payments.append(get_entity_dict(payment))
    
    # Add payments to invoice data
    invoice['payments'] = payments
    
    # Generate tax groups for GST summary
    tax_groups = {}
    for item in invoice['line_items']:
        gst_rate = item.get('gst_rate', 0)
        if gst_rate not in tax_groups:
            tax_groups[gst_rate] = {
                'taxable_value': 0,
                'cgst_amount': 0,
                'sgst_amount': 0,
                'igst_amount': 0
            }
        
        tax_groups[gst_rate]['taxable_value'] += item.get('taxable_amount', 0)
        tax_groups[gst_rate]['cgst_amount'] += item.get('cgst_amount', 0)
        tax_groups[gst_rate]['sgst_amount'] += item.get('sgst_amount', 0)
        tax_groups[gst_rate]['igst_amount'] += item.get('igst_amount', 0)
    
    # Create a context dictionary with all template variables
    context = {
        'invoice': invoice,
        'patient': patient,
        'hospital': hospital,
        'amount_in_words': amount_in_words,
        'tax_groups': tax_groups,
        'use_preprinted_stationery': use_preprinted_stationery
    }
    
    # Render the HTML template using the Flask app's render_template function
    with current_app.app_context():
        html_content = render_template('billing/print_invoice.html', **context)
    
    # Convert HTML to PDF
    pdf = HTML(string=html_content).write_pdf()
    
    return pdf


def save_invoice_pdf_to_file(
    invoice_id: uuid.UUID,
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_number: str,
    session: Session,
    current_user_id: Optional[str] = None
) -> Optional[str]:
    """
    Generate and save invoice PDF to EMR-compliant document folder

    Args:
        invoice_id: Invoice UUID
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        invoice_number: Invoice number (e.g., SVC/2025-2026/00001)
        session: Database session
        current_user_id: User ID for audit trail

    Returns:
        File path where PDF was saved, or None if generation failed
    """
    try:
        from flask import current_app, render_template
        import os
        from pathlib import Path

        logger.info(f"Generating PDF for invoice {invoice_number}")

        # Get invoice data using existing function
        invoice = _get_invoice_by_id(session, hospital_id, invoice_id)

        # Get patient details
        patient = None
        patient_record = session.query(Patient).filter_by(
            hospital_id=hospital_id,
            patient_id=patient_id
        ).first()

        if patient_record:
            patient = {
                'name': patient_record.full_name,
                'mrn': patient_record.mrn,
                'contact_info': patient_record.contact_info,
                'personal_info': {}
            }

        # Get hospital details
        hospital = None
        hospital_record = session.query(Hospital).filter_by(
            hospital_id=hospital_id
        ).first()

        if hospital_record:
            hospital = {
                'name': hospital_record.name,
                'address': hospital_record.address.get('full_address', '') if hospital_record.address else '',
                'phone': hospital_record.contact_details.get('phone', '') if hospital_record.contact_details else '',
                'email': hospital_record.contact_details.get('email', '') if hospital_record.contact_details else '',
                'gst_registration_number': hospital_record.gst_registration_number,
                'pharmacy_registration_number': hospital_record.pharmacy_registration_number
            }

            # Add pharmacy registration validity
            if hasattr(hospital_record, 'pharmacy_registration_valid_until'):
                hospital['pharmacy_registration_valid_until'] = hospital_record.pharmacy_registration_valid_until
            elif hasattr(hospital_record, 'pharmacy_reg_valid_until'):
                hospital['pharmacy_reg_valid_until'] = hospital_record.pharmacy_reg_valid_until

        # Convert amount to words
        amount_in_words = number_to_words(invoice['grand_total'])

        # Generate tax groups for GST summary
        tax_groups = {}
        total_taxable = 0
        total_cgst = 0
        total_sgst = 0
        total_igst = 0

        for item in invoice['line_items']:
            gst_rate = item.get('gst_rate', 0)
            if gst_rate not in tax_groups:
                tax_groups[gst_rate] = {
                    'taxable_value': 0,
                    'cgst_amount': 0,
                    'sgst_amount': 0,
                    'igst_amount': 0
                }

            tax_groups[gst_rate]['taxable_value'] += item.get('taxable_amount', 0)
            tax_groups[gst_rate]['cgst_amount'] += item.get('cgst_amount', 0)
            tax_groups[gst_rate]['sgst_amount'] += item.get('sgst_amount', 0)
            tax_groups[gst_rate]['igst_amount'] += item.get('igst_amount', 0)

            total_taxable += item.get('taxable_amount', 0)
            total_cgst += item.get('cgst_amount', 0)
            total_sgst += item.get('sgst_amount', 0)
            total_igst += item.get('igst_amount', 0)

        # Add totals to invoice for template
        invoice['tax_groups'] = tax_groups
        invoice['total_taxable'] = total_taxable
        invoice['total_cgst'] = total_cgst
        invoice['total_sgst'] = total_sgst
        invoice['total_igst'] = total_igst

        # Create context dictionary
        context = {
            'invoice': invoice,
            'patient': patient,
            'hospital': hospital,
            'amount_in_words': amount_in_words,
            'logo_url': None  # Can be enhanced later with actual logo path
        }

        # Render HTML template
        with current_app.app_context():
            html_content = render_template('billing/print_invoice.html', **context)

        # For now, save HTML content instead of PDF (PDF generation can be added later with weasyprint or similar)
        # This allows the system to work immediately while we can enhance with actual PDF later

        # Create directory structure: documents/patients/{patient_id}/invoices/
        base_path = Path(current_app.root_path).parent / 'documents' / 'patients' / str(patient_id) / 'invoices'
        base_path.mkdir(parents=True, exist_ok=True)

        # Sanitize invoice number for filename (replace / with -)
        safe_invoice_number = invoice_number.replace('/', '-')

        # Save HTML file (we'll enhance this to PDF later)
        file_path = base_path / f"{safe_invoice_number}.html"

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"✓ Saved invoice HTML to {file_path}")

        # Return relative path for storage in database if needed
        relative_path = f"documents/patients/{patient_id}/invoices/{safe_invoice_number}.html"

        return str(relative_path)

    except Exception as e:
        logger.error(f"Error saving invoice PDF: {str(e)}")
        logger.exception(e)
        # Don't raise - PDF saving should not block invoice creation
        return None


def create_advance_payment(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    amount: Decimal,
    payment_date: datetime,
    cash_amount: Decimal = Decimal('0'),
    credit_card_amount: Decimal = Decimal('0'),
    debit_card_amount: Decimal = Decimal('0'),
    upi_amount: Decimal = Decimal('0'),
    card_number_last4: Optional[str] = None,
    card_type: Optional[str] = None,
    upi_id: Optional[str] = None,
    reference_number: Optional[str] = None,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create a new advance payment for a patient
    
    Args:
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        amount: Total payment amount
        payment_date: Date of payment
        cash_amount: Cash payment amount
        credit_card_amount: Credit card payment amount
        debit_card_amount: Debit card payment amount
        upi_amount: UPI payment amount
        card_number_last4: Last 4 digits of card (for card payments)
        card_type: Type of card (for card payments)
        upi_id: UPI ID (for UPI payments)
        reference_number: Payment reference number
        notes: Optional notes
        current_user_id: ID of the user creating the advance
        session: Database session (optional)
    
    Returns:
        Dictionary containing created advance payment details
    """
    if session is not None:
        return _create_advance_payment(
            session, hospital_id, patient_id, amount, payment_date,
            cash_amount, credit_card_amount, debit_card_amount, upi_amount,
            card_number_last4, card_type, upi_id, reference_number,
            notes, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _create_advance_payment(
            new_session, hospital_id, patient_id, amount, payment_date,
            cash_amount, credit_card_amount, debit_card_amount, upi_amount,
            card_number_last4, card_type, upi_id, reference_number,
            notes, current_user_id
        )
        
        # Explicit commit for this critical operation
        new_session.commit()
        
        return result

def _create_advance_payment(
    session: Session,
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    amount: Decimal,
    payment_date: datetime,
    cash_amount: Decimal = Decimal('0'),
    credit_card_amount: Decimal = Decimal('0'),
    debit_card_amount: Decimal = Decimal('0'),
    upi_amount: Decimal = Decimal('0'),
    card_number_last4: Optional[str] = None,
    card_type: Optional[str] = None,
    upi_id: Optional[str] = None,
    reference_number: Optional[str] = None,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal function to create an advance payment within a session"""
    try:
        # Verify patient exists
        patient = session.query(Patient).filter_by(
            hospital_id=hospital_id, patient_id=patient_id
        ).first()
        
        if not patient:
            raise ValueError(f"Patient with ID {patient_id} not found")
        
        # Get hospital currency
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        currency_code = hospital.default_currency or 'INR'
        
        # Create advance payment record
        advance_payment = PatientAdvancePayment(
            hospital_id=hospital_id,
            patient_id=patient_id,
            amount=amount,
            payment_date=payment_date,
            cash_amount=cash_amount,
            credit_card_amount=credit_card_amount,
            debit_card_amount=debit_card_amount,
            upi_amount=upi_amount,
            currency_code=currency_code,
            exchange_rate=Decimal('1.0'),  # Default to 1.0
            card_number_last4=card_number_last4,
            card_type=card_type,
            upi_id=upi_id,
            reference_number=reference_number,
            notes=notes,
            available_balance=amount  # Initial balance equals full amount
        )
        
        if current_user_id:
            advance_payment.created_by = current_user_id
            
        session.add(advance_payment)
        session.flush()
        
        # Create GL entries for this advance payment
        try:
            # Import here to avoid circular imports
            from app.services.gl_service import create_advance_payment_gl_entries
            create_advance_payment_gl_entries(advance_payment.advance_id, current_user_id, session=session)
        except Exception as e:
            logger.warning(f"Error creating advance payment GL entries: {str(e)}")
            # Continue without GL entries as this is not critical
        
        # Create subledger entry for the advance payment
        try:
            # Get branch_id from patient record
            branch_id = getattr(patient, 'branch_id', None)
            
            # If patient doesn't have branch_id, use a default branch
            if not branch_id:
                # Get any branch for this hospital
                branch = session.query(Branch).filter_by(
                    hospital_id=hospital_id,
                    is_active=True
                ).first()
                
                branch_id = branch.branch_id if branch else None
                
            if branch_id:
                # Get GL transaction associated with this advance payment
                gl_transaction = None
                if hasattr(advance_payment, 'gl_entry_id') and advance_payment.gl_entry_id:
                    gl_transaction = session.query(GLTransaction).filter_by(
                        transaction_id=advance_payment.gl_entry_id
                    ).first()
                
                gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None
                
                # Import here to avoid circular imports
                from app.services.subledger_service import create_advance_payment_ar_entry
                
                # Create AR subledger entry for advance payment
                create_advance_payment_ar_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=branch_id,
                    patient_id=patient_id,
                    advance_id=advance_payment.advance_id,
                    amount=amount,
                    reference_number=reference_number or f"Advance-{advance_payment.advance_id}",
                    transaction_date=payment_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=current_user_id
                )
                
                logger.info(f"Created AR subledger entry for advance payment {advance_payment.advance_id}")
            else:
                logger.warning(f"Could not create subledger entry for advance payment - no branch ID available")
        except Exception as e:
            logger.error(f"Error creating AR subledger entry for advance payment: {str(e)}")
            # Don't let subledger creation failure stop the advance payment creation
            # Just log the error and continue
        
        # Return the created advance payment
        return get_entity_dict(advance_payment)
        
    except Exception as e:
        logger.error(f"Error creating advance payment: {str(e)}")
        session.rollback()
        raise

def get_patient_advance_balance(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    session: Optional[Session] = None
) -> Decimal:
    """
    Get current advance balance for a patient
    
    Args:
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        session: Database session (optional)
    
    Returns:
        Current advance balance
    """
    if session is not None:
        return _get_patient_advance_balance(session, hospital_id, patient_id)
    
    with get_db_session() as new_session:
        return _get_patient_advance_balance(new_session, hospital_id, patient_id)

def _get_patient_advance_balance(
    session: Session,
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID
) -> Decimal:
    """Internal function to get patient advance balance within a session"""
    try:
        # Calculate total available balance from all active advance payments
        result = session.query(func.sum(PatientAdvancePayment.available_balance))\
            .filter(
                PatientAdvancePayment.hospital_id == hospital_id,
                PatientAdvancePayment.patient_id == patient_id,
                PatientAdvancePayment.is_active == True
            ).scalar()
        
        # Return 0 if no advance payments found
        return result or Decimal('0')
        
    except Exception as e:
        logger.error(f"Error getting patient advance balance: {str(e)}")
        raise

def get_patient_advance_payments(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get all advance payments for a patient
    
    Args:
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        session: Database session (optional)
    
    Returns:
        List of advance payment dictionaries
    """
    if session is not None:
        return _get_patient_advance_payments(session, hospital_id, patient_id)
    
    with get_db_session() as new_session:
        return _get_patient_advance_payments(new_session, hospital_id, patient_id)

def _get_patient_advance_payments(
    session: Session,
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID
) -> List[Dict]:
    """Internal function to get patient advance payments within a session"""
    try:
        # Get all advance payments for the patient
        advance_payments = session.query(PatientAdvancePayment)\
            .filter(
                PatientAdvancePayment.hospital_id == hospital_id,
                PatientAdvancePayment.patient_id == patient_id
            )\
            .order_by(PatientAdvancePayment.payment_date.desc())\
            .all()
        
        # Convert to dictionaries
        return [get_entity_dict(payment) for payment in advance_payments]
        
    except Exception as e:
        logger.error(f"Error getting patient advance payments: {str(e)}")
        raise

def apply_advance_payment(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal,
    adjustment_date: datetime,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Apply advance payment to an invoice
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        amount: Amount to apply from advance
        adjustment_date: Date of adjustment
        notes: Optional notes
        current_user_id: ID of the user applying the advance
        session: Database session (optional)
    
    Returns:
        Dictionary containing adjustment details
    """
    if session is not None:
        return _apply_advance_payment(
            session, hospital_id, invoice_id, amount, adjustment_date, 
            notes, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _apply_advance_payment(
            new_session, hospital_id, invoice_id, amount, adjustment_date, 
            notes, current_user_id
        )
        
        # Explicit commit for this critical operation
        new_session.commit()
        
        return result

def _apply_advance_payment(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    amount: Decimal,
    adjustment_date: datetime,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal function to apply advance payment within a session"""
    try:
        # Get the invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Verify the amount doesn't exceed invoice balance
        if amount > invoice.balance_due:
            raise ValueError(f"Adjustment amount {amount} exceeds invoice balance due {invoice.balance_due}")
        
        # Get patient ID from the invoice
        patient_id = invoice.patient_id
        
        # Get available advance balance
        available_balance = _get_patient_advance_balance(session, hospital_id, patient_id)
        
        if amount > available_balance:
            raise ValueError(f"Adjustment amount {amount} exceeds available advance balance {available_balance}")
        
        # Get advance payments with available balance
        advance_payments = session.query(PatientAdvancePayment)\
            .filter(
                PatientAdvancePayment.hospital_id == hospital_id,
                PatientAdvancePayment.patient_id == patient_id,
                PatientAdvancePayment.available_balance > 0,
                PatientAdvancePayment.is_active == True
            )\
            .order_by(PatientAdvancePayment.payment_date)\
            .all()
        
        remaining_amount = amount
        adjustments = []
        
        # Apply adjustment to each advance payment until the full amount is used
        for advance in advance_payments:
            if remaining_amount <= 0:
                break
                
            adjustment_amount = min(remaining_amount, advance.available_balance)
            
            # Create adjustment record
            adjustment = AdvanceAdjustment(
                hospital_id=hospital_id,
                advance_id=advance.advance_id,
                invoice_id=invoice_id,
                amount=adjustment_amount,
                adjustment_date=adjustment_date,
                notes=notes
            )
            
            if current_user_id:
                adjustment.created_by = current_user_id
                
            session.add(adjustment)
            
            # Update advance payment available balance
            advance.available_balance -= adjustment_amount
            
            # Create payment record for this adjustment
            payment = PaymentDetail(
                hospital_id=hospital_id,
                invoice_id=invoice_id,
                payment_date=adjustment_date,
                cash_amount=Decimal('0'),
                credit_card_amount=Decimal('0'),
                debit_card_amount=Decimal('0'),
                upi_amount=Decimal('0'),
                currency_code=invoice.currency_code,
                exchange_rate=invoice.exchange_rate,
                reference_number=f"Adv #{str(advance.advance_id)[:8]}",
                total_amount=adjustment_amount,
                reconciliation_status='reconciled',
                notes=f"Payment from advance {advance.advance_id}"
            )
            
            if current_user_id:
                payment.created_by = current_user_id
                
            session.add(payment)
            session.flush()
            
            # Link the payment to the adjustment
            adjustment.payment_id = payment.payment_id
            session.flush()
            
            # Create GL entries for the advance adjustment
            try:
                # Import here to avoid circular imports
                from app.services.gl_service import create_advance_adjustment_gl_entries

                gl_transaction_id = create_advance_adjustment_gl_entries(
                    session=session,
                    hospital_id=hospital_id,
                    advance_id=advance.advance_id,
                    invoice_id=invoice_id,
                    adjustment_amount=adjustment_amount,
                    adjustment_date=adjustment_date,
                    invoice_number=invoice.invoice_number,
                    current_user_id=current_user_id
                )

                logger.info(f"Created GL entries for advance adjustment {adjustment.adjustment_id}")

            except Exception as e:
                logger.error(f"Error creating GL entries for advance adjustment: {str(e)}")
                # Continue even if GL posting fails
                gl_transaction_id = None

            # Create AR subledger entries for the advance adjustment
            try:
                # Import here to avoid circular imports
                from app.services.subledger_service import create_ar_subledger_entry

                # Create credit entry to reduce invoice balance
                create_ar_subledger_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=invoice.branch_id,
                    patient_id=invoice.patient_id,
                    entry_type='payment',
                    reference_id=payment.payment_id,
                    reference_type='payment',
                    reference_number=f"Adv #{str(advance.advance_id)[:8]}",
                    debit_amount=Decimal('0'),
                    credit_amount=adjustment_amount,
                    transaction_date=adjustment_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=current_user_id
                )

                logger.info(f"Created AR subledger entry for advance payment {payment.payment_id}")

            except Exception as e:
                logger.error(f"Error creating AR subledger entry for advance payment: {str(e)}")
                # Don't let subledger creation failure stop the advance payment application
                # Just log the error and continue

            # Add to adjustments list
            adjustments.append(get_entity_dict(adjustment))
            
            # Reduce remaining amount
            remaining_amount -= adjustment_amount
        
        # Update invoice paid amount and balance due
        invoice.paid_amount += amount
        invoice.balance_due -= amount
        
        if invoice.balance_due < 0:
            invoice.balance_due = Decimal('0')
            
        if current_user_id:
            invoice.updated_by = current_user_id
            
        session.flush()
        
        # Return adjustments
        return {
            'total_amount': amount,
            'adjustments': adjustments
        }
        
    except Exception as e:
        logger.error(f"Error applying advance payment: {str(e)}")
        session.rollback()
        raise

def handle_excess_payment(
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payment_id: uuid.UUID,
    excess_amount: Decimal,
    payment_date: datetime,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Handle excess payment by creating an advance payment
    
    Args:
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        invoice_id: Invoice UUID
        payment_id: Original payment UUID
        excess_amount: Excess amount to be converted to advance
        payment_date: Date of payment
        notes: Optional notes
        current_user_id: ID of the user creating the advance
        session: Database session (optional)
    
    Returns:
        Dictionary containing created advance payment details
    """
    if session is not None:
        return _handle_excess_payment(
            session, hospital_id, patient_id, invoice_id, payment_id,
            excess_amount, payment_date, notes, current_user_id
        )
    
    with get_db_session() as new_session:
        result = _handle_excess_payment(
            new_session, hospital_id, patient_id, invoice_id, payment_id,
            excess_amount, payment_date, notes, current_user_id
        )
        
        # Explicit commit for this critical operation
        new_session.commit()
        
        return result

def _handle_excess_payment(
    session: Session,
    hospital_id: uuid.UUID,
    patient_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payment_id: uuid.UUID,
    excess_amount: Decimal,
    payment_date: datetime,
    notes: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """Internal function to handle excess payment within a session"""
    try:
        # Get the original payment
        payment = session.query(PaymentDetail).filter_by(
            hospital_id=hospital_id, payment_id=payment_id
        ).first()
        
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")
        
        # Get the invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Create advance payment with same payment method distribution as original
        total_payment = payment.total_amount
        proportion = excess_amount / total_payment if total_payment > 0 else 0
        
        advance_cash = payment.cash_amount * proportion if payment.cash_amount > 0 else Decimal('0')
        advance_credit = payment.credit_card_amount * proportion if payment.credit_card_amount > 0 else Decimal('0')
        advance_debit = payment.debit_card_amount * proportion if payment.debit_card_amount > 0 else Decimal('0')
        advance_upi = payment.upi_amount * proportion if payment.upi_amount > 0 else Decimal('0')
        
        # Create advance payment
        advance_payment = PatientAdvancePayment(
            hospital_id=hospital_id,
            patient_id=patient_id,
            amount=excess_amount,
            payment_date=payment_date,
            cash_amount=advance_cash,
            credit_card_amount=advance_credit,
            debit_card_amount=advance_debit,
            upi_amount=advance_upi,
            currency_code=payment.currency_code,
            exchange_rate=payment.exchange_rate,
            card_number_last4=payment.card_number_last4,
            card_type=payment.card_type,
            upi_id=payment.upi_id,
            reference_number=payment.reference_number,
            notes=notes or f"Excess payment from invoice #{invoice.invoice_number}",
            available_balance=excess_amount
        )
        
        if current_user_id:
            advance_payment.created_by = current_user_id
            
        session.add(advance_payment)
        session.flush()
        
        # Create GL entries for this advance payment (if needed)
        try:
            # Import here to avoid circular imports
            from app.services.gl_service import create_advance_payment_gl_entries
            create_advance_payment_gl_entries(advance_payment.advance_id, current_user_id, session=session)
        except Exception as e:
            logger.warning(f"Error creating advance payment GL entries: {str(e)}")
            # Continue without GL entries as this is not critical
        
        # Return the created advance payment
        return get_entity_dict(advance_payment)

    except Exception as e:
        logger.error(f"Error handling excess payment: {str(e)}")
        session.rollback()
        raise


# ============================================================================
# PACKAGE INSTALLMENT PAYMENT RECORDING
# ============================================================================

def create_package_installment_payment_record(
    session,
    hospital_id,
    patient_id,
    branch_id,
    payment_date,
    total_amount,
    cash_amount=Decimal('0'),
    credit_card_amount=Decimal('0'),
    debit_card_amount=Decimal('0'),
    upi_amount=Decimal('0'),
    card_number_last4=None,
    card_type=None,
    upi_id=None,
    reference_number=None,
    recorded_by=None,
    save_as_draft=False,
    approval_threshold=Decimal('100000')
):
    """
    Create a payment record for package installment payment (no invoice allocations)

    This is used when a payment is made ONLY toward package installments,
    with NO invoice allocations.

    Args:
        session: Database session (required)
        hospital_id: Hospital UUID
        patient_id: Patient UUID
        branch_id: Branch UUID
        payment_date: Payment date
        total_amount: Total payment amount
        cash_amount, credit_card_amount, debit_card_amount, upi_amount: Payment method breakdowns
        card_number_last4, card_type, upi_id: Payment method details
        reference_number: Payment reference number
        recorded_by: User ID recording the payment
        save_as_draft: Save as draft without posting
        approval_threshold: Amount threshold requiring approval

    Returns:
        Dictionary containing payment_id and other details
    """
    try:
        from datetime import datetime, timezone

        # Determine workflow status
        if save_as_draft:
            workflow_status = 'draft'
            requires_approval = False
            should_post_gl = False
        elif total_amount >= approval_threshold:
            workflow_status = 'pending_approval'
            requires_approval = True
            should_post_gl = False
        else:
            workflow_status = 'approved'
            requires_approval = False
            should_post_gl = True

        # ========================================================================
        # CREATE PAYMENT_DETAILS RECORD (invoice_id = NULL for package-only)
        # ========================================================================

        payment = PaymentDetail(
            payment_id=uuid.uuid4(),
            hospital_id=hospital_id,
            invoice_id=None,  # ✅ NULL for package installment-only payments
            payment_date=payment_date,
            total_amount=total_amount,
            cash_amount=cash_amount,
            credit_card_amount=credit_card_amount,
            debit_card_amount=debit_card_amount,
            upi_amount=upi_amount,
            card_number_last4=card_number_last4,
            card_type=card_type,
            upi_id=upi_id,
            reference_number=reference_number,
            workflow_status=workflow_status,
            requires_approval=requires_approval,
            gl_posted=False,
            created_by=recorded_by or 'system',
            created_at=datetime.now(timezone.utc),
            is_deleted=False
        )

        # ✅ Set submission tracking (if not draft)
        if workflow_status != 'draft':
            payment.submitted_by = recorded_by or 'system'
            payment.submitted_at = datetime.now(timezone.utc)

        if workflow_status == 'approved':
            payment.approved_by = recorded_by or 'system'
            payment.approved_at = datetime.now(timezone.utc)

        session.add(payment)
        session.flush()  # Get payment_id

        # ✅ Populate new traceability fields
        payment.patient_id = patient_id
        payment.branch_id = branch_id
        payment.payment_source = 'package_installment'
        payment.invoice_count = 0
        payment.recorded_by = recorded_by

        logger.info(f"✓ Created package installment payment {payment.payment_id} for ₹{total_amount}")

        # ========================================================================
        # POST GL ENTRIES (if auto-approved)
        # ========================================================================
        # NOTE: GL posting for package installments is handled separately
        # The installment payment service will create the GL entries

        return {
            'success': True,
            'payment_id': str(payment.payment_id),
            'payment_number': payment.reference_number,
            'workflow_status': workflow_status,
            'requires_approval': requires_approval
        }

    except Exception as e:
        logger.error(f"Error creating package installment payment record: {str(e)}", exc_info=True)
        raise