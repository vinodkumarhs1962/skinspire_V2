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
    logger.info(f"Invoice Creation Request Received")
    logger.info(f"Hospital ID: {hospital_id}")
    logger.info(f"Branch ID: {branch_id}")
    logger.info(f"Patient ID: {patient_id}")
    logger.info(f"Invoice Date: {invoice_date}")
    logger.info(f"Number of Line Items: {len(line_items)}")
    logger.info(f"Current User ID: {current_user_id}")

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
    Internal function to create invoices based on business rules
    
    This implementation handles the grouping of line items by type and GST applicability,
    and creates multiple invoices as needed according to business rules.
    """
    try:
        # Detailed logging at the start of the method
        logger.info("Starting invoice creation process")
        logger.info(f"Hospital ID: {hospital_id}")
        logger.info(f"Branch ID: {branch_id}")
        logger.info(f"Patient ID: {patient_id}")
        logger.info(f"Invoice Date: {invoice_date}")
        logger.info(f"Notes: {notes}")
        logger.info(f"Current User ID: {current_user_id}")

        # Get hospital pharmacy registration
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
        if not hospital:
            logger.error(f"Hospital with ID {hospital_id} not found")
            raise ValueError(f"Hospital with ID {hospital_id} not found")

        # Initialize has_valid_pharmacy_registration flag
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
                    
        # Log pharmacy registration status
        logger.info(f"Hospital has valid pharmacy registration: {has_valid_pharmacy_registration}")
            
        # Access property within session
        has_pharmacy_registration = False
        if hospital.pharmacy_registration_number is not None:
            has_pharmacy_registration = True
        
        # Log pharmacy registration status
        logger.info(f"Hospital Pharmacy Registration: {bool(hospital.pharmacy_registration_number)}")

        # Group line items by type and GST applicability
        # Detailed logging for item grouping
        logger.info("Grouping line items")

        product_service_gst_items = []
        product_service_non_gst_items = []
        prescription_items = []
        
        for item in line_items:
            # Log each item details
            logger.info(f"Processing Item: Type={item.get('item_type')}, ID={item.get('item_id')}, Name={item.get('item_name')}")
            
            # Process each line item based on type
            if item['item_type'] in ['Product', 'Service', 'Misc', 'Package']:
                # Check if item is GST exempt
                is_gst_exempt = _get_item_gst_exempt_status(session, item)
                logger.info(f"Item GST Status: {'Exempt' if is_gst_exempt else 'Taxable'}")

                if is_gst_exempt:
                    product_service_non_gst_items.append(item)
                else:
                    product_service_gst_items.append(item)
            elif item['item_type'] == 'Prescription':
                prescription_items.append(item)
            elif item['item_type'] == 'Medicine':
                # For Medicine items, check for prescription requirement
                medicine = session.query(Medicine).filter_by(medicine_id=item['item_id']).first()
                
                # If included_in_consultation flag is set, treat as prescription
                if item.get('included_in_consultation', False):
                    logger.info(f"Medicine included in consultation, adding to prescription items")
                    prescription_items.append(item)
                # Otherwise if prescription is required by medicine config
                elif medicine and getattr(medicine, 'prescription_required', False):
                    logger.info(f"Medicine requires prescription, adding to prescription items")
                    prescription_items.append(item)
                else:
                    # Treat as standard product with GST check
                    is_gst_exempt = _get_item_gst_exempt_status(session, item)
                    logger.info(f"Medicine GST Status: {'Exempt' if is_gst_exempt else 'Taxable'}")
                    
                    if is_gst_exempt:
                        product_service_non_gst_items.append(item)
                    else:
                        product_service_gst_items.append(item)
        
        # Log item groups
        logger.info(f"GST Items Count: {len(product_service_gst_items)}")
        logger.info(f"Non-GST Items Count: {len(product_service_non_gst_items)}")
        logger.info(f"Prescription Items Count: {len(prescription_items)}")

        # Create invoices based on grouped items
        created_invoices = []
        
        # Handle prescription items based on pharmacy registration
        if prescription_items:
            if has_valid_pharmacy_registration:
                # With valid pharmacy registration, treat prescriptions as individual items
                for item in prescription_items:
                    # Check if item is included in consultation
                    if item.get('included_in_consultation', False):
                        # Even with valid registration, "included in consultation" items 
                        # are added to GST invoice as normal medicine items
                        product_service_gst_items.append(item)
                    else:
                        # Regular prescription items go into the GST invoice
                        product_service_gst_items.append(item)
            else:
                # WITHOUT valid pharmacy registration, consolidate prescription items
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
                    'is_consolidated_prescription': True,  # Add a flag to identify this as consolidated
                    'is_gst_exempt': True  # Mark as GST exempt
                }
                
                # Add the consolidated item to non-GST items instead of GST items
                product_service_non_gst_items.append(consolidated_prescription_item)
                
                # Still update inventory for medicine items
                _update_prescription_inventory(
                    session, hospital_id, prescription_items, patient_id, current_user_id
                )
        
        # 1. Create GST invoice for Product/Service/Misc items
        if product_service_gst_items:
            logger.info("Creating GST Invoice for Product/Service Items")
            gst_invoice = _create_single_invoice(
                session, hospital_id, branch_id, patient_id, invoice_date,
                product_service_gst_items, True, "Product/Service", notes, current_user_id
            )
            created_invoices.append(gst_invoice)
            logger.info(f"GST Invoice Created: {gst_invoice.invoice_number}")

            # Add subledger entry for GST invoice
            try:
                # Get GL transaction associated with this invoice
                gl_transaction = session.query(GLTransaction).filter_by(
                    invoice_header_id=gst_invoice.invoice_id
                ).first()
                
                gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None
                
                # Import here to avoid circular imports
                from app.services.subledger_service import create_ar_subledger_entry
                
                # Create AR subledger entry
                create_ar_subledger_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=branch_id,
                    patient_id=patient_id,
                    entry_type='invoice',
                    reference_id=gst_invoice.invoice_id,
                    reference_type='invoice',
                    reference_number=gst_invoice.invoice_number,
                    debit_amount=gst_invoice.grand_total,
                    credit_amount=Decimal('0'),
                    transaction_date=invoice_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=current_user_id
                )
                
                logger.info(f"Created AR subledger entry for GST invoice {gst_invoice.invoice_number}")
                
            except Exception as e:
                logger.error(f"Error creating AR subledger entry for GST invoice: {str(e)}")
                # Don't let subledger creation failure stop the invoice creation
                # Just log the error and continue

        # 2. Create Non-GST invoice for Product/Service/Misc items
        if product_service_non_gst_items:
            non_gst_invoice = _create_single_invoice(
                session, hospital_id, branch_id, patient_id, invoice_date,
                product_service_non_gst_items, False, "Product/Service", notes, current_user_id
            )
            created_invoices.append(non_gst_invoice)
            logger.info(f"Non-GST Invoice Created: {non_gst_invoice.invoice_number}")
            
            # Add subledger entry for Non-GST invoice
            try:
                # Get GL transaction associated with this invoice
                gl_transaction = session.query(GLTransaction).filter_by(
                    invoice_header_id=non_gst_invoice.invoice_id
                ).first()
                
                gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None
                
                # Import here to avoid circular imports
                from app.services.subledger_service import create_ar_subledger_entry
                
                # Create AR subledger entry
                create_ar_subledger_entry(
                    session=session,
                    hospital_id=hospital_id,
                    branch_id=branch_id,
                    patient_id=patient_id,
                    entry_type='invoice',
                    reference_id=non_gst_invoice.invoice_id,
                    reference_type='invoice',
                    reference_number=non_gst_invoice.invoice_number,
                    debit_amount=non_gst_invoice.grand_total,
                    credit_amount=Decimal('0'),
                    transaction_date=invoice_date,
                    gl_transaction_id=gl_transaction_id,
                    current_user_id=current_user_id
                )
                
                logger.info(f"Created AR subledger entry for Non-GST invoice {non_gst_invoice.invoice_number}")
                
            except Exception as e:
                logger.error(f"Error creating AR subledger entry for Non-GST invoice: {str(e)}")
                # Don't let subledger creation failure stop the invoice creation
                # Just log the error and continue
        
        # Create detached copies of all created invoices before returning
        invoice_dicts = []
        for invoice in created_invoices:
            # Use get_entity_dict to convert to dictionary with all relationships
            invoice_dict = get_entity_dict(invoice)
            invoice_dicts.append(invoice_dict)
        
        # Add this line to explicitly commit the transaction
        session.commit()  # <-- ADD THIS LINE

        # Log final invoice creation result
        logger.info(f"Total Invoices Created: {len(created_invoices)}")
        logger.info("Invoice Creation Process Completed Successfully")

        # Return all created invoices as dictionaries
        return {
            'invoices': invoice_dicts,
            'count': len(created_invoices)
        }
        
    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}")
        logger.error(f"Error Details: {str(e)}")

        # Log input parameters for debugging
        logger.error(f"Hospital ID: {hospital_id}")
        logger.error(f"Branch ID: {branch_id}")
        logger.error(f"Patient ID: {patient_id}")
        logger.error(f"Number of Line Items: {len(line_items)}")
        
        # Optional: Log line items for detailed error investigation
        for idx, item in enumerate(line_items, 1):
            logger.error(f"Line Item {idx}: {item}")

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
            
        elif item_type == 'Medicine':
            medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
            return medicine.is_gst_exempt if medicine else False
            
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

def _update_prescription_inventory(
    session: Session,
    hospital_id: uuid.UUID,
    prescription_items: List[Dict],
    patient_id: uuid.UUID,
    current_user_id: Optional[str] = None
):
    """
    Update inventory for prescription items even when consolidated
    
    Args:
        session: Database session
        hospital_id: Hospital UUID
        prescription_items: List of prescription items
        patient_id: Patient UUID
        current_user_id: User ID performing the action
    """
    # Create a dummy invoice ID for inventory tracking
    dummy_invoice_id = uuid.uuid4()
    
    for item in prescription_items:
        medicine_id = item.get('medicine_id') or item.get('item_id')
        if medicine_id:
            # Create inventory transaction for this prescription
            medicine_name = item.get('item_name', 'Unknown Medicine')
            quantity = Decimal(str(item.get('quantity', 1)))
            batch = item.get('batch')
            
            # Get the latest inventory entry for this medicine and batch
            latest_inventory = session.query(Inventory).filter(
                Inventory.hospital_id == hospital_id,
                Inventory.medicine_id == medicine_id,
                Inventory.batch == batch
            ).order_by(Inventory.created_at.desc()).first()
            
            if latest_inventory:
                # Calculate current stock after this transaction
                current_stock = latest_inventory.current_stock - quantity
                
                # Create inventory transaction
                inventory_entry = Inventory(
                    hospital_id=hospital_id,
                    stock_type='Prescription',
                    medicine_id=medicine_id,
                    medicine_name=medicine_name,
                    bill_id=dummy_invoice_id,
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
                    transaction_date=datetime.now(timezone.utc)
                )
                
                if current_user_id:
                    inventory_entry.created_by = current_user_id
                    
                session.add(inventory_entry)
                
    session.flush()

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
        line_item = _process_invoice_line_item(session, hospital_id, item, is_interstate)
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
    
    # Update inventory for medicines
    if any(item.get('item_type') in ['Medicine', 'Prescription'] for item in processed_line_items):
        try:
            update_inventory_for_invoice(
                hospital_id=hospital_id,
                invoice_id=invoice.invoice_id,
                patient_id=patient_id,
                line_items=processed_line_items,
                current_user_id=current_user_id,
                session=session
            )
        except Exception as e:
            logger.warning(f"Error updating inventory: {str(e)}")
    
    # Create GL entries
    try:
        create_invoice_gl_entries(invoice.invoice_id, session=session)
    except Exception as e:
        logger.warning(f"Error creating GL entries: {str(e)}")
    
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

def _process_invoice_line_item(session: Session, hospital_id: uuid.UUID, item: Dict, is_interstate: bool) -> Dict:
    """
    Process a line item for invoice creation, calculating amounts and taxes
    
    Args:
        session: Database session
        hospital_id: Hospital UUID
        item: Line item data
        is_interstate: Whether this is an interstate transaction
        
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
        gst_rate = Decimal('0')
        is_gst_exempt = True
        hsn_sac_code = None
        cost_price = None
        
        # For Doctor's Examination, set GST to zero regardless of database values
        if is_doctors_examination:
            gst_rate = Decimal('0')
            is_gst_exempt = True
        else:
            # For other items, get details from the database
            if item_type == 'Package':
                package = session.query(Package).filter_by(package_id=item_id).first()
                if package:
                    gst_rate = package.gst_rate or Decimal('0')
                    is_gst_exempt = package.is_gst_exempt
            
            elif item_type == 'Service':
                service = session.query(Service).filter_by(service_id=item_id).first()
                if service:
                    gst_rate = service.gst_rate or Decimal('0')
                    is_gst_exempt = service.is_gst_exempt
                    hsn_sac_code = service.sac_code
            
            elif item_type in ['Medicine', 'Prescription']:
                medicine = session.query(Medicine).filter_by(medicine_id=item_id).first()
                if medicine:
                    gst_rate = medicine.gst_rate or Decimal('0')
                    is_gst_exempt = medicine.is_gst_exempt
                    hsn_sac_code = medicine.hsn_code
                    cost_price = medicine.cost_price
        
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
            if item_type in ['Medicine', 'Prescription']:
                # Use the specialized function for medicines (MRP-based)
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
                # For services/packages, calculate GST on pre-discount amount (original price)
                # and apply discount to taxable value
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
            'included_in_consultation': item.get('included_in_consultation', False)
        }
        
        # Add ID fields based on type
        if item_type == 'Package':
            processed_item['package_id'] = item_id
        elif item_type == 'Service':
            processed_item['service_id'] = item_id
        elif item_type in ['Medicine', 'Prescription']:
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
        # Process only medicine/prescription items
        for item in line_items:
            if item.get('item_type') in ['Medicine', 'Prescription']:
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
                    transaction_date=datetime.now(timezone.utc)
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

def create_invoice_gl_entries(
    invoice_id: uuid.UUID,
    session: Optional[Session] = None
) -> None:
    """
    Create general ledger entries for an invoice
    
    Args:
        invoice_id: Invoice UUID
        session: Database session (optional)
    """
    if session is not None:
        return _create_invoice_gl_entries(session, invoice_id)
    
    with get_db_session() as new_session:
        return _create_invoice_gl_entries(new_session, invoice_id)

def _create_invoice_gl_entries(
    session: Session,
    invoice_id: uuid.UUID
) -> None:
    """
    Internal function to create general ledger entries for an invoice
    """
    try:
        # Get invoice details
        invoice = session.query(InvoiceHeader).filter_by(invoice_id=invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # GL entry logic to be implemented as per accounting rules
        # This will involve creating entries in the journal_entries table
        logger.info(f"GL entries created for invoice {invoice.invoice_number}")
        
    except Exception as e:
        logger.error(f"Error creating GL entries for invoice: {str(e)}")
        session.rollback()
        raise

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
    Internal function to get invoice details by ID
    """
    try:
        # Query invoice with line items
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id,
            invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Get line items
        line_items = session.query(InvoiceLineItem).filter_by(
            hospital_id=hospital_id,
            invoice_id=invoice_id
        ).all()
        
        # Create detached copies
        invoice_dict = get_entity_dict(invoice)
        line_items_dict = [get_entity_dict(item) for item in line_items]
        
        # Add line items to invoice dictionary
        invoice_dict['line_items'] = line_items_dict
        
        # Check for consolidated prescription
        invoice_dict['is_consolidated_prescription'] = False
        if invoice.invoice_type == 'Service':
            for item in line_items:
                if item.item_name == "Doctor's Examination and Treatment":
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
    reference_number=None, handle_excess=True, recorded_by=None, session=None
):
    """
    Record a payment against an invoice
    
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
        session: Database session (optional)
        
    Returns:
        Dictionary containing created payment details
    """
    if session is not None:
        # If session is provided, use it without committing
        return _record_payment(
            session, hospital_id, invoice_id, payment_date, 
            cash_amount, credit_card_amount, debit_card_amount, upi_amount,
            card_number_last4, card_type, upi_id, reference_number, 
            handle_excess, recorded_by
        )
    
    # If no session provided, create a new one and explicitly commit
    with get_db_session() as new_session:
        result = _record_payment(
            new_session, hospital_id, invoice_id, payment_date, 
            cash_amount, credit_card_amount, debit_card_amount, upi_amount,
            card_number_last4, card_type, upi_id, reference_number, 
            handle_excess, recorded_by
        )
        
        # Add explicit commit for this critical operation
        new_session.commit()
        
        return result

def _record_payment(
    session, hospital_id, invoice_id, payment_date,
    cash_amount=Decimal('0'), credit_card_amount=Decimal('0'),
    debit_card_amount=Decimal('0'), upi_amount=Decimal('0'),
    card_number_last4=None, card_type=None, upi_id=None, 
    reference_number=None, handle_excess=True, recorded_by=None
):
    """Internal function to record a payment against an invoice in the database"""
    try:
        # Get the invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Calculate total payment amount
        total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount
        
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
            reconciliation_status='pending'
        )
        
        if recorded_by:
            payment.created_by = recorded_by
            
        session.add(payment)
        session.flush()  # Make changes visible within transaction
        
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
        
        # Create GL entries for this payment
        try:
            # Import here to avoid circular imports
            from app.services.gl_service import create_payment_gl_entries
            create_payment_gl_entries(payment.payment_id, recorded_by, session=session)
        except Exception as e:
            logger.warning(f"Error creating payment GL entries: {str(e)}")
            # Continue without GL entries as this is not critical for payment recording
        
        # Create AR subledger entry for the payment
        try:
            # Get GL transaction associated with this payment
            gl_transaction = None
            if hasattr(payment, 'gl_entry_id') and payment.gl_entry_id:
                gl_transaction = session.query(GLTransaction).filter_by(
                    transaction_id=payment.gl_entry_id
                ).first()
            
            gl_transaction_id = gl_transaction.transaction_id if gl_transaction else None
            
            # Import here to avoid circular imports
            from app.services.subledger_service import create_ar_subledger_entry
            
            # Create AR subledger entry
            create_ar_subledger_entry(
                session=session,
                hospital_id=hospital_id,
                branch_id=invoice.branch_id,
                patient_id=invoice.patient_id,
                entry_type='payment',
                reference_id=payment.payment_id,
                reference_type='payment',
                reference_number=reference_number or f"Payment-{payment.payment_id}",
                debit_amount=Decimal('0'),
                credit_amount=payment_to_apply,  # Only apply the amount that went to this invoice
                transaction_date=payment_date,
                gl_transaction_id=gl_transaction_id,
                current_user_id=recorded_by
            )
            
            logger.info(f"Created AR subledger entry for payment {payment.payment_id}")
            
        except Exception as e:
            logger.error(f"Error creating AR subledger entry for payment {payment.payment_id}: {str(e)}")
            # Don't let subledger creation failure stop the payment recording
            # Just log the error and continue
        
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
                        notes=f"Auto-distributed from excess payment for invoice {invoice.invoice_number}"
                    )
                    
                    if recorded_by:
                        related_payment.created_by = recorded_by
                        
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
                    
                    # Create AR subledger entry for the related payment
                    try:
                        # Create AR subledger entry
                        create_ar_subledger_entry(
                            session=session,
                            hospital_id=hospital_id,
                            branch_id=related.branch_id,
                            patient_id=related.patient_id,
                            entry_type='payment',
                            reference_id=related_payment.payment_id,
                            reference_type='payment',
                            reference_number=reference_number or f"Payment-{related_payment.payment_id}",
                            debit_amount=Decimal('0'),
                            credit_amount=payment_for_related,
                            transaction_date=payment_date,
                            gl_transaction_id=None,  # We might not have this readily available
                            current_user_id=recorded_by
                        )
                        
                        logger.info(f"Created AR subledger entry for related payment {related_payment.payment_id}")
                        
                    except Exception as e:
                        logger.error(f"Error creating AR subledger entry for related payment: {str(e)}")
                        logger.error(f"Related invoice details - ID: {related.invoice_id}, Number: {related.invoice_number}")
                        logger.error(f"Payment details - ID: {related_payment.payment_id}, Amount: {payment_for_related}")
                        # Continue with the rest of the process
                
                session.flush()
                
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
                    gl_transaction_id=None,
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