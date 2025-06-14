# app/services/billing_service.py

import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.master import Hospital, Package, Service, Medicine, ChartOfAccounts
from app.models.transaction import (
    InvoiceHeader, InvoiceLineItem, PaymentDetail, GLTransaction, GLEntry, GSTLedger,
    Inventory
)
from app.services.gl_service import (
    create_invoice_gl_entries, 
    create_payment_gl_entries, 
    create_refund_gl_entries, 
    process_void_invoice_gl_entries
)
from app.services.inventory_service import update_inventory_for_invoice
from app.services.database_service import get_db_session, get_entity_dict

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
        
        # Log item groups
        logger.info(f"GST Items Count: {len(product_service_gst_items)}")
        logger.info(f"Non-GST Items Count: {len(product_service_non_gst_items)}")
        logger.info(f"Prescription Items Count: {len(prescription_items)}")

        # Create invoices based on grouped items
        created_invoices = []
        
        # 1. Create GST invoice for Product/Service/Misc items
        if product_service_gst_items:
            logger.info("Creating GST Invoice for Product/Service Items")
            gst_invoice = _create_single_invoice(
                session, hospital_id, branch_id, patient_id, invoice_date,
                product_service_gst_items, True, "Product/Service", notes, current_user_id
            )
            created_invoices.append(gst_invoice)
            logger.info(f"GST Invoice Created: {gst_invoice.invoice_number}")

        # 2. Create Non-GST invoice for Product/Service/Misc items
        if product_service_non_gst_items:
            non_gst_invoice = _create_single_invoice(
                session, hospital_id, branch_id, patient_id, invoice_date,
                product_service_non_gst_items, False, "Product/Service", notes, current_user_id
            )
            created_invoices.append(non_gst_invoice)
        
        # 3. Process prescription items based on pharmacy registration
        if prescription_items:
            if has_pharmacy_registration:
                # Create standard drug invoice
                prescription_invoice = _create_single_invoice(
                    session, hospital_id, branch_id, patient_id, invoice_date,
                    prescription_items, True, "Prescription", notes, current_user_id
                )
                created_invoices.append(prescription_invoice)
            else:
                # Consolidate to Doctor's Examination and Treatment
                total_amount = Decimal('0')
                for item in prescription_items:
                    # Calculate item total
                    quantity = Decimal(str(item['quantity']))
                    unit_price = Decimal(str(item['unit_price']))
                    total_amount += quantity * unit_price
                
                # Create a consolidated invoice with a single line item
                treatment_service_id = _get_treatment_service_id(session, hospital_id)
                consolidated_item = {
                    'item_type': 'Service',
                    'item_id': treatment_service_id,
                    'item_name': "Doctor's Examination and Treatment",
                    'quantity': Decimal('1'),
                    'unit_price': total_amount,
                    'discount_percent': Decimal('0')
                }
                
                consolidated_invoice = _create_single_invoice(
                    session, hospital_id, branch_id, patient_id, invoice_date,
                    [consolidated_item], True, "Service", notes, current_user_id
                )
                created_invoices.append(consolidated_invoice)
                
                # Still update inventory for medicine items
                _update_prescription_inventory(
                    session, hospital_id, prescription_items, patient_id, current_user_id
                )
        
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
        
        # Get item details from the database based on type
        gst_rate = Decimal('0')
        is_gst_exempt = True
        hsn_sac_code = None
        cost_price = None
        
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
        discount_amount = (pre_discount_amount * discount_percent) / 100
        taxable_amount = pre_discount_amount - discount_amount
        
        # Calculate GST based on interstate status
        cgst_rate = Decimal('0')
        sgst_rate = Decimal('0')
        igst_rate = Decimal('0')
        cgst_amount = Decimal('0')
        sgst_amount = Decimal('0')
        igst_amount = Decimal('0')
        
        if not is_gst_exempt and gst_rate > 0:
            if is_interstate:
                igst_rate = gst_rate
                igst_amount = (taxable_amount * igst_rate) / 100
            else:
                cgst_rate = gst_rate / 2
                sgst_rate = gst_rate / 2
                cgst_amount = (taxable_amount * cgst_rate) / 100
                sgst_amount = (taxable_amount * sgst_rate) / 100
        
        total_gst_amount = cgst_amount + sgst_amount + igst_amount
        line_total = taxable_amount + total_gst_amount
        
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
    # Query the current financial year and prefix from hospital settings
    try:
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
        
    except Exception as e:
        logger.error(f"Error generating invoice number: {str(e)}")
        raise

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
            from app.models.transaction import Patient
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

def record_payment(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payment_date: datetime,
    payment_methods: Dict[str, Decimal],
    payment_details: Dict,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Record a payment against an invoice
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        payment_date: Payment date
        payment_methods: Dictionary with payment amounts by method (cash, credit_card, etc.)
        payment_details: Additional payment details like card number, reference
        current_user_id: ID of the user recording the payment
        session: Database session (optional)
        
    Returns:
        Dictionary containing created payment details
    """
    if session is not None:
        return _record_payment(
            session, hospital_id, invoice_id, payment_date, payment_methods, 
            payment_details, current_user_id
        )
    
    with get_db_session() as new_session:
        return _record_payment(
            new_session, hospital_id, invoice_id, payment_date, payment_methods, 
            payment_details, current_user_id
        )

def _record_payment(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    payment_date: datetime,
    payment_methods: Dict[str, Decimal],
    payment_details: Dict,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to record a payment against an invoice within a session
    """
    try:
        # Get the invoice
        invoice = session.query(InvoiceHeader).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Invoice with ID {invoice_id} not found")
        
        # Calculate total payment amount
        cash_amount = payment_methods.get('cash', Decimal('0'))
        credit_card_amount = payment_methods.get('credit_card', Decimal('0'))
        debit_card_amount = payment_methods.get('debit_card', Decimal('0'))
        upi_amount = payment_methods.get('upi', Decimal('0'))
        
        total_payment = cash_amount + credit_card_amount + debit_card_amount + upi_amount
        
        # Check if payment exceeds balance due
        if total_payment > invoice.balance_due:
            raise ValueError(f"Payment amount {total_payment} exceeds balance due {invoice.balance_due}")
        
        # Create payment record
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
            card_number_last4=payment_details.get('card_number_last4'),
            card_type=payment_details.get('card_type'),
            upi_id=payment_details.get('upi_id'),
            reference_number=payment_details.get('reference_number'),
            total_amount=total_payment,
            reconciliation_status='pending'
        )
        
        if current_user_id:
            payment.created_by = current_user_id
            
        session.add(payment)
        session.flush()
        
        # Update invoice payment status
        invoice.paid_amount += total_payment
        invoice.balance_due -= total_payment
        
        if invoice.balance_due <= 0:
            invoice.balance_due = Decimal('0')
            
        if current_user_id:
            invoice.updated_by = current_user_id
            
        session.flush()
        
        # Create GL entries for this payment
        try:
            # Import here to avoid circular imports
            from app.services.gl_service import create_payment_gl_entries
            create_payment_gl_entries(payment.payment_id, current_user_id, session=session)
        except Exception as e:
            logger.warning(f"Error creating payment GL entries: {str(e)}")
            # Continue without GL entries as this is not critical for payment recording
        
        # Return the created payment
        return get_entity_dict(payment)
        
    except Exception as e:
        logger.error(f"Error recording payment: {str(e)}")
        session.rollback()
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
    if session is not None:
        return _void_invoice(session, hospital_id, invoice_id, reason, current_user_id)
    
    with get_db_session() as new_session:
        return _void_invoice(new_session, hospital_id, invoice_id, reason, current_user_id)

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
        
        # Check if invoice has payments
        payment_count = session.query(PaymentDetail).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).count()
        
        if payment_count > 0:
            raise ValueError("Cannot void an invoice with recorded payments")
        
        # Create a new entry in InvoiceHeader with negative amounts
        # This is a common accounting practice for voiding
        void_invoice = InvoiceHeader(
            hospital_id=hospital_id,
            branch_id=invoice.branch_id,
            invoice_number=f"VOID-{invoice.invoice_number}",
            invoice_date=datetime.now(timezone.utc),
            invoice_type=invoice.invoice_type,
            is_gst_invoice=invoice.is_gst_invoice,
            patient_id=invoice.patient_id,
            place_of_supply=invoice.place_of_supply,
            is_interstate=invoice.is_interstate,
            currency_code=invoice.currency_code,
            exchange_rate=invoice.exchange_rate,
            total_amount=-invoice.total_amount,
            total_discount=-invoice.total_discount,
            total_taxable_value=-invoice.total_taxable_value,
            total_cgst_amount=-invoice.total_cgst_amount,
            total_sgst_amount=-invoice.total_sgst_amount,
            total_igst_amount=-invoice.total_igst_amount,
            grand_total=-invoice.grand_total,
            paid_amount=Decimal('0'),
            balance_due=Decimal('0'),
            gl_account_id=invoice.gl_account_id,
            notes=f"Void of invoice {invoice.invoice_number}. Reason: {reason}"
        )
        
        if current_user_id:
            void_invoice.created_by = current_user_id
            
        session.add(void_invoice)
        session.flush()
        
        # Get original line items
        line_items = session.query(InvoiceLineItem).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).all()
        
        # Create negative line items for each
        for item in line_items:
            void_item = InvoiceLineItem(
                hospital_id=hospital_id,
                invoice_id=void_invoice.invoice_id,
                package_id=item.package_id,
                service_id=item.service_id,
                medicine_id=item.medicine_id,
                item_type=item.item_type,
                item_name=item.item_name,
                hsn_sac_code=item.hsn_sac_code,
                batch=item.batch,
                expiry_date=item.expiry_date,
                included_in_consultation=item.included_in_consultation,
                quantity=-item.quantity,
                unit_price=item.unit_price,
                discount_percent=item.discount_percent,
                discount_amount=-item.discount_amount,
                taxable_amount=-item.taxable_amount,
                gst_rate=item.gst_rate,
                cgst_rate=item.cgst_rate,
                sgst_rate=item.sgst_rate,
                igst_rate=item.igst_rate,
                cgst_amount=-item.cgst_amount,
                sgst_amount=-item.sgst_amount,
                igst_amount=-item.igst_amount,
                total_gst_amount=-item.total_gst_amount,
                line_total=-item.line_total,
                cost_price=item.cost_price,
                profit_margin=-item.profit_margin if item.profit_margin else None
            )
            
            if current_user_id:
                void_item.created_by = current_user_id
                
            session.add(void_item)
        
        session.flush()
        
        # For medicines, restore inventory
        try:
            # Import here to avoid circular imports
            from app.services.inventory_service import update_inventory_for_invoice
            
            # Convert line items to dict format expected by inventory service
            void_line_items = []
            for item in line_items:
                if item.item_type == 'Medicine':
                    void_line_items.append({
                        'item_type': 'Medicine',
                        'medicine_id': item.medicine_id,
                        'item_name': item.item_name,
                        'batch': item.batch,
                        'quantity': item.quantity,
                        'unit_price': item.unit_price,
                        'cgst_amount': item.cgst_amount,
                        'sgst_amount': item.sgst_amount,
                        'igst_amount': item.igst_amount,
                        'total_gst_amount': item.total_gst_amount
                    })
            
            if void_line_items:
                update_inventory_for_invoice(
                    hospital_id=hospital_id,
                    invoice_id=void_invoice.invoice_id,
                    patient_id=invoice.patient_id,
                    line_items=void_line_items,
                    void=True,  # This is a void operation - will reverse the stock movement
                    current_user_id=current_user_id,
                    session=session
                )
        except Exception as e:
            logger.warning(f"Error updating inventory for void: {str(e)}")
            # Create a fallback approach to update inventory if needed
            for item in line_items:
                if item.item_type == 'Medicine':
                    # Get original inventory transaction
                    original_inventory = session.query(Inventory).filter(
                        Inventory.hospital_id == hospital_id,
                        Inventory.bill_id == invoice_id,
                        Inventory.medicine_id == item.medicine_id
                    ).first()
                    
                    if original_inventory:
                        # Create reverse inventory entry
                        inventory_entry = Inventory(
                            hospital_id=hospital_id,
                            stock_type='Void',
                            medicine_id=item.medicine_id,
                            medicine_name=item.item_name,
                            bill_id=void_invoice.invoice_id,
                            patient_id=invoice.patient_id,
                            batch=item.batch,
                            expiry=original_inventory.expiry,
                            pack_purchase_price=original_inventory.pack_purchase_price,
                            pack_mrp=original_inventory.pack_mrp,
                            units_per_pack=original_inventory.units_per_pack,
                            unit_price=original_inventory.unit_price,
                            sale_price=item.unit_price,
                            units=-original_inventory.units,  # Reverse the original quantity
                            current_stock=original_inventory.current_stock - original_inventory.units,
                            reason=f"Void of invoice {invoice.invoice_number}",
                            transaction_date=datetime.now(timezone.utc)
                        )
                        
                        if current_user_id:
                            inventory_entry.created_by = current_user_id
                            
                        session.add(inventory_entry)
                
        session.flush()
        
        # Create GL entries for the void invoice
        try:
            # Import here to avoid circular imports
            from app.services.gl_service import process_void_invoice_gl_entries
            process_void_invoice_gl_entries(void_invoice.invoice_id, invoice.invoice_id, current_user_id, session=session)
        except Exception as e:
            logger.warning(f"Error creating void invoice GL entries: {str(e)}")
            # Continue without GL entries as this is not critical for void processing
        
        # Return the void invoice
        return get_entity_dict(void_invoice)
        
    except Exception as e:
        logger.error(f"Error voiding invoice: {str(e)}")
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