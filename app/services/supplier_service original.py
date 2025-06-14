# app/services/supplier_service.py

from datetime import datetime, timezone
import uuid
from typing import Dict, List, Optional, Tuple, Union
from decimal import Decimal
import logging

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session

from app.models.master import Supplier, Medicine, ChartOfAccounts
from app.models.transaction import (
    PurchaseOrderHeader, PurchaseOrderLine,
    SupplierInvoice, SupplierInvoiceLine, SupplierPayment
)
from app.services.database_service import get_db_session, get_entity_dict
from app.services.gl_service import create_supplier_invoice_gl_entries, create_supplier_payment_gl_entries
from app.services.inventory_service import record_stock_from_supplier_invoice

logger = logging.getLogger(__name__)

# ===================================================================
# Supplier Management
# ===================================================================

def create_supplier(
    hospital_id: uuid.UUID,
    supplier_data: Dict,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create a new supplier record
    
    Args:
        hospital_id: Hospital UUID
        supplier_data: Dictionary containing supplier information
        current_user_id: ID of the user creating the supplier
        session: Database session (optional)
        
    Returns:
        Dictionary containing created supplier details
    """
    if session is not None:
        return _create_supplier(session, hospital_id, supplier_data, current_user_id)
    
    with get_db_session() as new_session:
        return _create_supplier(new_session, hospital_id, supplier_data, current_user_id)

def _create_supplier(
    session: Session,
    hospital_id: uuid.UUID,
    supplier_data: Dict,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create a new supplier record within a session
    """
    try:
        # Check for duplicate supplier name
        existing_supplier = session.query(Supplier).filter(
            Supplier.hospital_id == hospital_id,
            Supplier.supplier_name == supplier_data['supplier_name']
        ).first()
        
        if existing_supplier:
            raise ValueError(f"Supplier with name '{supplier_data['supplier_name']}' already exists")
        
        # Check for duplicate GST number if provided
        if supplier_data.get('gst_registration_number'):
            existing_gst = session.query(Supplier).filter(
                Supplier.hospital_id == hospital_id,
                Supplier.gst_registration_number == supplier_data['gst_registration_number']
            ).first()
            
            if existing_gst:
                raise ValueError(f"Supplier with GST number '{supplier_data['gst_registration_number']}' already exists")
        
        # Create new supplier
        supplier = Supplier(
            hospital_id=hospital_id,
            supplier_name=supplier_data['supplier_name'],
            supplier_category=supplier_data.get('supplier_category'),
            supplier_address=supplier_data.get('supplier_address', {}),
            contact_person_name=supplier_data.get('contact_person_name'),
            contact_info=supplier_data.get('contact_info', {}),
            manager_name=supplier_data.get('manager_name'),
            manager_contact_info=supplier_data.get('manager_contact_info', {}),
            email=supplier_data.get('email'),
            black_listed=supplier_data.get('black_listed', False),
            performance_rating=supplier_data.get('performance_rating'),
            payment_terms=supplier_data.get('payment_terms'),
            gst_registration_number=supplier_data.get('gst_registration_number'),
            pan_number=supplier_data.get('pan_number'),
            tax_type=supplier_data.get('tax_type'),
            state_code=supplier_data.get('state_code'),
            bank_details=supplier_data.get('bank_details', {}),
            remarks=supplier_data.get('remarks'),
            status=supplier_data.get('status', 'active')
        )
        
        if current_user_id:
            supplier.created_by = current_user_id
            
        session.add(supplier)
        session.flush()
        
        # Return the created supplier
        return get_entity_dict(supplier)
        
    except Exception as e:
        logger.error(f"Error creating supplier: {str(e)}")
        session.rollback()
        raise

def update_supplier(
    supplier_id: uuid.UUID,
    supplier_data: Dict,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Update an existing supplier record
    
    Args:
        supplier_id: Supplier UUID
        supplier_data: Dictionary containing supplier information updates
        hospital_id: Hospital UUID for security
        current_user_id: ID of the user updating the supplier
        session: Database session (optional)
        
    Returns:
        Dictionary containing updated supplier details
    """
    if session is not None:
        return _update_supplier(session, supplier_id, supplier_data, hospital_id, current_user_id)
    
    with get_db_session() as new_session:
        return _update_supplier(new_session, supplier_id, supplier_data, hospital_id, current_user_id)

def _update_supplier(
    session: Session,
    supplier_id: uuid.UUID,
    supplier_data: Dict,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to update an existing supplier record within a session
    """
    try:
        # Get the supplier
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
        
        # Check for duplicate supplier name if being changed
        if 'supplier_name' in supplier_data and supplier_data['supplier_name'] != supplier.supplier_name:
            existing_supplier = session.query(Supplier).filter(
                Supplier.hospital_id == hospital_id,
                Supplier.supplier_name == supplier_data['supplier_name'],
                Supplier.supplier_id != supplier_id
            ).first()
            
            if existing_supplier:
                raise ValueError(f"Supplier with name '{supplier_data['supplier_name']}' already exists")
        
        # Check for duplicate GST number if being changed
        if 'gst_registration_number' in supplier_data and supplier_data['gst_registration_number'] != supplier.gst_registration_number:
            existing_gst = session.query(Supplier).filter(
                Supplier.hospital_id == hospital_id,
                Supplier.gst_registration_number == supplier_data['gst_registration_number'],
                Supplier.supplier_id != supplier_id
            ).first()
            
            if existing_gst:
                raise ValueError(f"Supplier with GST number '{supplier_data['gst_registration_number']}' already exists")
        
        # Update fields
        updatable_fields = [
            'supplier_name', 'supplier_category', 'supplier_address',
            'contact_person_name', 'contact_info', 'manager_name', 
            'manager_contact_info', 'email', 'black_listed', 
            'performance_rating', 'payment_terms', 'gst_registration_number',
            'pan_number', 'tax_type', 'state_code', 'bank_details',
            'remarks', 'status'
        ]
        
        for field in updatable_fields:
            if field in supplier_data:
                setattr(supplier, field, supplier_data[field])
        
        if current_user_id:
            supplier.updated_by = current_user_id
            
        # Update the timestamp
        supplier.updated_at = datetime.now(timezone.utc)
        
        session.flush()
        
        # Return the updated supplier
        return get_entity_dict(supplier)
        
    except Exception as e:
        logger.error(f"Error updating supplier: {str(e)}")
        session.rollback()
        raise

def get_supplier_by_id(
    supplier_id: uuid.UUID,
    hospital_id: uuid.UUID,
    session: Optional[Session] = None
) -> Dict:
    """
    Get a supplier by ID
    
    Args:
        supplier_id: Supplier UUID
        hospital_id: Hospital UUID for security
        session: Database session (optional)
        
    Returns:
        Dictionary containing supplier details
    """
    if session is not None:
        return _get_supplier_by_id(session, supplier_id, hospital_id)
    
    with get_db_session() as new_session:
        return _get_supplier_by_id(new_session, supplier_id, hospital_id)

def _get_supplier_by_id(
    session: Session,
    supplier_id: uuid.UUID,
    hospital_id: uuid.UUID
) -> Dict:
    """
    Internal function to get a supplier by ID within a session
    """
    try:
        # Get the supplier
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
            
        # Return the supplier as a dictionary
        return get_entity_dict(supplier)
        
    except Exception as e:
        logger.error(f"Error getting supplier: {str(e)}")
        raise

def search_suppliers(
    hospital_id: uuid.UUID,
    name: Optional[str] = None,
    category: Optional[str] = None,
    gst_number: Optional[str] = None,
    status: Optional[str] = None,
    blacklisted: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20,
    session: Optional[Session] = None
) -> Dict:
    """
    Search suppliers with filtering and pagination
    
    Args:
        hospital_id: Hospital UUID
        name: Filter by supplier name
        category: Filter by supplier category
        gst_number: Filter by GST number
        status: Filter by status
        blacklisted: Filter by blacklisted status
        page: Page number for pagination
        per_page: Number of items per page
        session: Database session (optional)
        
    Returns:
        Dictionary containing supplier list and pagination info
    """
    if session is not None:
        return _search_suppliers(
            session, hospital_id, name, category, gst_number, 
            status, blacklisted, page, per_page
        )
    
    with get_db_session() as new_session:
        return _search_suppliers(
            new_session, hospital_id, name, category, gst_number, 
            status, blacklisted, page, per_page
        )

def _search_suppliers(
    session: Session,
    hospital_id: uuid.UUID,
    name: Optional[str] = None,
    category: Optional[str] = None,
    gst_number: Optional[str] = None,
    status: Optional[str] = None,
    blacklisted: Optional[bool] = None,
    page: int = 1,
    per_page: int = 20
) -> Dict:
    """
    Internal function to search suppliers within a session
    """
    try:
        # Base query
        query = session.query(Supplier).filter_by(hospital_id=hospital_id)
        
        # Apply filters
        if name:
            query = query.filter(Supplier.supplier_name.ilike(f"%{name}%"))
            
        if category:
            query = query.filter(Supplier.supplier_category == category)
            
        if gst_number:
            query = query.filter(Supplier.gst_registration_number.ilike(f"%{gst_number}%"))
            
        if status:
            query = query.filter(Supplier.status == status)
            
        if blacklisted is not None:
            query = query.filter(Supplier.black_listed == blacklisted)
            
        # Count total for pagination
        total_count = query.count()
        
        # Apply pagination
        query = query.order_by(Supplier.supplier_name)
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Execute query
        suppliers = query.all()
        
        # Convert to dictionaries
        supplier_list = [get_entity_dict(supplier) for supplier in suppliers]
        
        # Prepare pagination info
        pagination = {
            'page': page,
            'per_page': per_page,
            'total_count': total_count,
            'total_pages': (total_count + per_page - 1) // per_page
        }
        
        return {
            'suppliers': supplier_list,
            'pagination': pagination
        }
        
    except Exception as e:
        logger.error(f"Error searching suppliers: {str(e)}")
        raise

# ===================================================================
# Purchase Order Management
# ===================================================================

def create_purchase_order(
    hospital_id: uuid.UUID,
    po_data: Dict,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create a new purchase order
    
    Args:
        hospital_id: Hospital UUID
        po_data: Dictionary containing PO header and line items
        current_user_id: ID of the user creating the PO
        session: Database session (optional)
        
    Returns:
        Dictionary containing created PO details
    """
    if session is not None:
        return _create_purchase_order(session, hospital_id, po_data, current_user_id)
    
    with get_db_session() as new_session:
        return _create_purchase_order(new_session, hospital_id, po_data, current_user_id)

def _create_purchase_order(
    session: Session,
    hospital_id: uuid.UUID,
    po_data: Dict,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create a purchase order within a session
    """
    try:
        # Validate supplier
        supplier_id = po_data.get('supplier_id')
        if not supplier_id:
            raise ValueError("Supplier ID is required")
            
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
            
        # Check if supplier is blacklisted
        if supplier.black_listed:
            raise ValueError(f"Supplier '{supplier.supplier_name}' is blacklisted")
            
        # Validate line items
        line_items = po_data.get('line_items', [])
        if not line_items:
            raise ValueError("At least one line item is required")
            
        # Generate PO number
        po_number = _generate_po_number(session, hospital_id)
        
        # Create PO header
        po_header = PurchaseOrderHeader(
            hospital_id=hospital_id,
            po_number=po_number,
            po_date=po_data.get('po_date', datetime.now(timezone.utc)),
            supplier_id=supplier_id,
            quotation_id=po_data.get('quotation_id'),
            quotation_date=po_data.get('quotation_date'),
            expected_delivery_date=po_data.get('expected_delivery_date'),
            currency_code=po_data.get('currency_code', 'INR'),
            exchange_rate=po_data.get('exchange_rate', 1.0),
            status='draft',
            deleted_flag=False
        )
        
        if current_user_id:
            po_header.created_by = current_user_id
            
        session.add(po_header)
        session.flush()  # To get the po_id
        
        # Create PO lines
        po_lines = []
        total_amount = Decimal('0')
        
        for item_data in line_items:
            # Validate medicine
            medicine_id = item_data.get('medicine_id')
            if not medicine_id:
                raise ValueError("Medicine ID is required for each line item")
                
            medicine = session.query(Medicine).filter_by(
                medicine_id=medicine_id,
                hospital_id=hospital_id
            ).first()
            
            if not medicine:
                raise ValueError(f"Medicine with ID {medicine_id} not found")
                
            # Calculate tax amounts
            # Check if interstate GST applies
            is_interstate = supplier.state_code != item_data.get('place_of_supply')
            
            units = Decimal(str(item_data.get('units', 0)))
            pack_purchase_price = Decimal(str(item_data.get('pack_purchase_price', 0)))
            pack_mrp = Decimal(str(item_data.get('pack_mrp', 0)))
            units_per_pack = Decimal(str(item_data.get('units_per_pack', 1)))
            
            # Calculate unit price
            unit_price = pack_purchase_price / units_per_pack if units_per_pack > 0 else Decimal('0')
            
            # Calculate tax amounts
            gst_rate = Decimal(str(item_data.get('gst_rate', medicine.gst_rate or 0)))
            
            # Set appropriate GST rates based on inter/intra state
            cgst_rate = Decimal('0')
            sgst_rate = Decimal('0')
            igst_rate = Decimal('0')
            
            if is_interstate:
                igst_rate = gst_rate
            else:
                cgst_rate = gst_rate / 2
                sgst_rate = gst_rate / 2
                
            # Calculate tax amounts
            taxable_amount = units * pack_purchase_price
            cgst = (taxable_amount * cgst_rate / 100).quantize(Decimal('0.01'))
            sgst = (taxable_amount * sgst_rate / 100).quantize(Decimal('0.01'))
            igst = (taxable_amount * igst_rate / 100).quantize(Decimal('0.01'))
            total_gst = cgst + sgst + igst
            
            # Calculate line total
            line_total = taxable_amount + total_gst
            total_amount += line_total
            
            # Create PO line
            po_line = PurchaseOrderLine(
                hospital_id=hospital_id,
                po_id=po_header.po_id,
                medicine_id=medicine_id,
                medicine_name=medicine.medicine_name,
                units=units,
                pack_purchase_price=pack_purchase_price,
                pack_mrp=pack_mrp,
                units_per_pack=units_per_pack,
                unit_price=unit_price,
                hsn_code=medicine.hsn_code or item_data.get('hsn_code'),
                gst_rate=gst_rate,
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                igst_rate=igst_rate,
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                total_gst=total_gst,
                line_total=line_total,
                expected_delivery_date=item_data.get('expected_delivery_date', po_header.expected_delivery_date)
            )
            
            if current_user_id:
                po_line.created_by = current_user_id
                
            session.add(po_line)
            po_lines.append(po_line)
            
        # Update header total amount
        po_header.total_amount = total_amount
        
        session.flush()
        
        # Return the created PO with lines
        result = get_entity_dict(po_header)
        result['line_items'] = [get_entity_dict(line) for line in po_lines]
        result['supplier_name'] = supplier.supplier_name
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating purchase order: {str(e)}")
        session.rollback()
        raise

def _generate_po_number(session: Session, hospital_id: uuid.UUID) -> str:
    """
    Generate a sequential purchase order number
    
    Args:
        session: Database session
        hospital_id: Hospital UUID
        
    Returns:
        Formatted PO number
    """
    # Get current financial year
    today = datetime.now()
    if today.month >= 4:  # Financial year starts in April
        fin_year_start = today.year
        fin_year_end = today.year + 1
    else:
        fin_year_start = today.year - 1
        fin_year_end = today.year
        
    fin_year = f"{fin_year_start}-{fin_year_end}"
    
    # Get the last PO number for this hospital and financial year
    last_po = session.query(PurchaseOrderHeader).filter(
        PurchaseOrderHeader.hospital_id == hospital_id,
        PurchaseOrderHeader.po_number.like(f"PO/{fin_year}/%")
    ).order_by(PurchaseOrderHeader.po_number.desc()).first()
    
    if last_po:
        # Extract the sequence number from the last PO number
        try:
            seq_num = int(last_po.po_number.split('/')[-1])
            new_seq_num = seq_num + 1
        except:
            # If parsing fails, start from 1
            new_seq_num = 1
    else:
        # No existing PO for this hospital and financial year
        new_seq_num = 1
        
    # Format the new PO number
    return f"PO/{fin_year}/{new_seq_num:05d}"

def update_purchase_order_status(
    po_id: uuid.UUID,
    status: str,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Update the status of a purchase order
    
    Args:
        po_id: Purchase Order UUID
        status: New status (draft, approved, received, cancelled)
        hospital_id: Hospital UUID for security
        current_user_id: ID of the user updating the status
        session: Database session (optional)
        
    Returns:
        Dictionary containing updated PO details
    """
    if session is not None:
        return _update_purchase_order_status(session, po_id, status, hospital_id, current_user_id)
    
    with get_db_session() as new_session:
        return _update_purchase_order_status(new_session, po_id, status, hospital_id, current_user_id)

def _update_purchase_order_status(
    session: Session,
    po_id: uuid.UUID,
    status: str,
    hospital_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to update the status of a purchase order within a session
    """
    try:
        # Validate status
        valid_statuses = ['draft', 'approved', 'received', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}")
            
        # Get the PO
        po = session.query(PurchaseOrderHeader).filter_by(
            po_id=po_id,
            hospital_id=hospital_id
        ).first()
        
        if not po:
            raise ValueError(f"Purchase order with ID {po_id} not found")
            
        # Check if status transition is allowed
        current_status = po.status
        
        # Rules for status transitions
        if current_status == 'cancelled':
            raise ValueError("Cannot change status of a cancelled purchase order")
            
        if current_status == 'received' and status != 'cancelled':
            raise ValueError("Received purchase orders can only be cancelled")
            
        if current_status == 'approved' and status == 'draft':
            raise ValueError("Cannot change status from approved to draft")
            
        # Update the status
        po.status = status
        
        if status == 'approved':
            po.approved_by = current_user_id
            
        if current_user_id:
            po.updated_by = current_user_id
            
        # Update the timestamp
        po.updated_at = datetime.now(timezone.utc)
        
        session.flush()
        
        # Return the updated PO with lines
        return get_po_with_lines(session, po)
        
    except Exception as e:
        logger.error(f"Error updating purchase order status: {str(e)}")
        session.rollback()
        raise

def get_po_with_lines(session: Session, po: PurchaseOrderHeader) -> Dict:
    """
    Helper function to get a PO with its line items
    
    Args:
        session: Database session
        po: Purchase order header
        
    Returns:
        Dictionary containing PO details with line items
    """
    # Get the line items
    lines = session.query(PurchaseOrderLine).filter_by(po_id=po.po_id).all()
    
    # Get the supplier
    supplier = session.query(Supplier).filter_by(supplier_id=po.supplier_id).first()
    
    # Convert to dictionary
    result = get_entity_dict(po)
    result['line_items'] = [get_entity_dict(line) for line in lines]
    
    if supplier:
        result['supplier_name'] = supplier.supplier_name
        
    return result

def get_purchase_order_by_id(
    po_id: uuid.UUID,
    hospital_id: uuid.UUID,
    session: Optional[Session] = None
) -> Dict:
    """
    Get a purchase order by ID with its line items
    
    Args:
        po_id: Purchase Order UUID
        hospital_id: Hospital UUID for security
        session: Database session (optional)
        
    Returns:
        Dictionary containing PO details with line items
    """
    if session is not None:
        return _get_purchase_order_by_id(session, po_id, hospital_id)
    
    with get_db_session() as new_session:
        return _get_purchase_order_by_id(new_session, po_id, hospital_id)

def _get_purchase_order_by_id(
    session: Session,
    po_id: uuid.UUID,
    hospital_id: uuid.UUID
) -> Dict:
    """
    Internal function to get a purchase order by ID within a session
    """
    try:
        # Get the PO
        po = session.query(PurchaseOrderHeader).filter_by(
            po_id=po_id,
            hospital_id=hospital_id
        ).first()
        
        if not po:
            raise ValueError(f"Purchase order with ID {po_id} not found")
            
        # Return the PO with lines
        return get_po_with_lines(session, po)
        
    except Exception as e:
        logger.error(f"Error getting purchase order: {str(e)}")
        raise

def search_purchase_orders(
    hospital_id: uuid.UUID,
    supplier_id: Optional[uuid.UUID] = None,
    po_number: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 20,
    session: Optional[Session] = None
) -> Dict:
    """
    Search purchase orders with filtering and pagination
    
    Args:
        hospital_id: Hospital UUID
        supplier_id: Filter by supplier ID
        po_number: Filter by PO number
        status: Filter by status
        start_date: Filter by start date
        end_date: Filter by end date
        page: Page number for pagination
        per_page: Number of items per page
        session: Database session (optional)
        
    Returns:
        Dictionary containing PO list and pagination info
    """
    if session is not None:
        return _search_purchase_orders(
            session, hospital_id, supplier_id, po_number, 
            status, start_date, end_date, page, per_page
        )
    
    with get_db_session() as new_session:
        return _search_purchase_orders(
            new_session, hospital_id, supplier_id, po_number, 
            status, start_date, end_date, page, per_page
        )

# def _search_supplier_invoices(
#     session: Session,
#     hospital_id: uuid.UUID,
#     supplier_id: Optional[uuid.UUID] = None,
#     invoice_number: Optional[str] = None,
#     payment_status: Optional[str] = None,
#     start_date: Optional[datetime] = None,
#     end_date: Optional[datetime] = None,
#     page: int = 1,
#     per_page: int = 20
# ) -> Dict:
#     """
#     Internal function to search supplier invoices within a session
#     """
#     try:
#         # Base query
#         query = session.query(SupplierInvoice).filter_by(hospital_id=hospital_id)
        
#         # Apply filters
#         if supplier_id:
#             query = query.filter(SupplierInvoice.supplier_id == supplier_id)
            
#         if invoice_number:
#             query = query.filter(SupplierInvoice.supplier_invoice_number.ilike(f"%{invoice_number}%"))
            
#         if payment_status:
#             query = query.filter(SupplierInvoice.payment_status == payment_status)
            
#         if start_date:
#             query = query.filter(SupplierInvoice.invoice_date >= start_date)
            
#         if end_date:
#             query = query.filter(SupplierInvoice.invoice_date <= end_date)
            
#         # Count total for pagination
#         total_count = query.count()
        
#         # Apply pagination
#         query = query.order_by(desc(SupplierInvoice.invoice_date))
#         query = query.offset((page - 1) * per_page).limit(per_page)
        
#         # Execute query
#         invoices = query.all()
        
#         # Convert to dictionaries
#         invoice_list = []
        
#         for invoice in invoices:
#             invoice_dict = get_entity_dict(invoice)
            
#             # Get the supplier name
#             supplier = session.query(Supplier).filter_by(supplier_id=invoice.supplier_id).first()
#             if supplier:
#                 invoice_dict['supplier_name'] = supplier.supplier_name
                
#             # Add line count
#             line_count = session.query(SupplierInvoiceLine).filter_by(invoice_id=invoice.invoice_id).count()
#             invoice_dict['line_count'] = line_count
            
#             # Get payment total
#             payment_total = session.query(func.sum(SupplierPayment.amount)).filter_by(
#                 invoice_id=invoice.invoice_id
#             ).scalar() or 0
            
#             invoice_dict['payment_total'] = float(payment_total)
#             invoice_dict['balance_due'] = float(invoice.total_amount - Decimal(payment_total))
            
#             invoice_list.append(invoice_dict)
        
#         # Prepare pagination info
#         pagination = {
#             'page': page,
#             'per_page': per_page,
#             'total_count': total_count,
#             'total_pages': (total_count + per_page - 1) // per_page
#         }
        
#         return {
#             'invoices': invoice_list,
#             'pagination': pagination
#         }
        
#     except Exception as e:
#         logger.error(f"Error searching supplier invoices: {str(e)}")
#         raise

# ===================================================================
# Supplier Payment Management
# ===================================================================

def record_supplier_payment(
    hospital_id: uuid.UUID,
    payment_data: Dict,
    create_gl_entries: bool = True,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Record a payment to a supplier
    
    Args:
        hospital_id: Hospital UUID
        payment_data: Dictionary containing payment information
        create_gl_entries: Whether to create GL entries
        current_user_id: ID of the user recording the payment
        session: Database session (optional)
        
    Returns:
        Dictionary containing created payment details
    """
    if session is not None:
        return _record_supplier_payment(
            session, hospital_id, payment_data, create_gl_entries, current_user_id
        )
    
    with get_db_session() as new_session:
        return _record_supplier_payment(
            new_session, hospital_id, payment_data, create_gl_entries, current_user_id
        )

def _record_supplier_payment(
    session: Session,
    hospital_id: uuid.UUID,
    payment_data: Dict,
    create_gl_entries: bool = True,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to record a payment to a supplier within a session
    """
    try:
        # Validate supplier
        supplier_id = payment_data.get('supplier_id')
        if not supplier_id:
            raise ValueError("Supplier ID is required")
            
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
        
        # Validate invoice if provided
        invoice = None
        invoice_id = payment_data.get('invoice_id')
        
        if invoice_id:
            invoice = session.query(SupplierInvoice).filter_by(
                invoice_id=invoice_id,
                hospital_id=hospital_id,
                supplier_id=supplier_id
            ).first()
            
            if not invoice:
                raise ValueError(f"Supplier invoice with ID {invoice_id} not found for this supplier")
                
            # Check if invoice is already fully paid
            payment_total = session.query(func.sum(SupplierPayment.amount)).filter_by(
                invoice_id=invoice_id
            ).scalar() or 0
            
            balance_due = invoice.total_amount - Decimal(payment_total)
            
            if balance_due <= 0:
                raise ValueError(f"Invoice {invoice.supplier_invoice_number} is already fully paid")
                
            # Check if payment amount exceeds balance due
            payment_amount = Decimal(str(payment_data.get('amount', 0)))
            
            if payment_amount > balance_due:
                raise ValueError(f"Payment amount {payment_amount} exceeds balance due {balance_due}")
        
        # Create payment record
        payment = SupplierPayment(
            hospital_id=hospital_id,
            supplier_id=supplier_id,
            invoice_id=invoice_id,
            payment_date=payment_data.get('payment_date', datetime.now(timezone.utc)),
            payment_method=payment_data.get('payment_method', 'bank_transfer'),
            currency_code=payment_data.get('currency_code', 'INR'),
            exchange_rate=payment_data.get('exchange_rate', 1.0),
            amount=Decimal(str(payment_data.get('amount', 0))),
            reference_no=payment_data.get('reference_no'),
            status=payment_data.get('status', 'completed'),
            notes=payment_data.get('notes'),
            reconciliation_status='pending'
        )
        
        if current_user_id:
            payment.created_by = current_user_id
            
        session.add(payment)
        session.flush()  # To get the payment_id
        
        # Update invoice payment status if applicable
        if invoice:
            # Get updated payment total
            new_payment_total = session.query(func.sum(SupplierPayment.amount)).filter_by(
                invoice_id=invoice_id
            ).scalar() or 0
            
            new_balance_due = invoice.total_amount - Decimal(new_payment_total)
            
            # Update payment status
            if new_balance_due <= 0:
                invoice.payment_status = 'paid'
            else:
                invoice.payment_status = 'partial'
                
            session.flush()
            
        # Create GL entries if requested
        gl_transaction = None
        if create_gl_entries:
            gl_result = create_supplier_payment_gl_entries(
                payment.payment_id,
                current_user_id,
                session
            )
            
        # Return the created payment
        result = get_entity_dict(payment)
        result['supplier_name'] = supplier.supplier_name
        
        if invoice:
            result['invoice_number'] = invoice.supplier_invoice_number
            result['invoice_amount'] = float(invoice.total_amount)
            result['payment_status'] = invoice.payment_status
            
        return result
        
    except Exception as e:
        logger.error(f"Error recording supplier payment: {str(e)}")
        session.rollback()
        raise

def get_supplier_payment_history(
    supplier_id: uuid.UUID,
    hospital_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get payment history for a supplier
    
    Args:
        supplier_id: Supplier UUID
        hospital_id: Hospital UUID for security
        start_date: Filter by start date
        end_date: Filter by end date
        session: Database session (optional)
        
    Returns:
        List of payment records
    """
    if session is not None:
        return _get_supplier_payment_history(session, supplier_id, hospital_id, start_date, end_date)
    
    with get_db_session() as new_session:
        return _get_supplier_payment_history(new_session, supplier_id, hospital_id, start_date, end_date)

def _get_supplier_payment_history(
    session: Session,
    supplier_id: uuid.UUID,
    hospital_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict]:
    """
    Internal function to get payment history for a supplier within a session
    """
    try:
        # Validate supplier
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
            
        # Query payments
        query = session.query(SupplierPayment).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        )
        
        # Apply date filters
        if start_date:
            query = query.filter(SupplierPayment.payment_date >= start_date)
            
        if end_date:
            query = query.filter(SupplierPayment.payment_date <= end_date)
            
        # Order by date
        query = query.order_by(desc(SupplierPayment.payment_date))
        
        # Execute query
        payments = query.all()
        
        # Convert to dictionaries with invoice details
        results = []
        
        for payment in payments:
            payment_dict = get_entity_dict(payment)
            
            # Add invoice details if available
            if payment.invoice_id:
                invoice = session.query(SupplierInvoice).filter_by(invoice_id=payment.invoice_id).first()
                if invoice:
                    payment_dict['invoice_number'] = invoice.supplier_invoice_number
                    payment_dict['invoice_date'] = invoice.invoice_date
                    payment_dict['invoice_amount'] = float(invoice.total_amount)
                    
            results.append(payment_dict)
            
        return results
        
    except Exception as e:
        logger.error(f"Error getting supplier payment history: {str(e)}")
        raise

def get_pending_supplier_invoices(
    hospital_id: uuid.UUID,
    supplier_id: Optional[uuid.UUID] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get unpaid or partially paid supplier invoices
    
    Args:
        hospital_id: Hospital UUID
        supplier_id: Filter by supplier ID (optional)
        session: Database session (optional)
        
    Returns:
        List of invoices with payment information
    """
    if session is not None:
        return _get_pending_supplier_invoices(session, hospital_id, supplier_id)
    
    with get_db_session() as new_session:
        return _get_pending_supplier_invoices(new_session, hospital_id, supplier_id)

def _get_pending_supplier_invoices(
    session: Session,
    hospital_id: uuid.UUID,
    supplier_id: Optional[uuid.UUID] = None
) -> List[Dict]:
    """
    Internal function to get pending supplier invoices within a session
    """
    try:
        # Base query for unpaid or partially paid invoices
        query = session.query(SupplierInvoice).filter(
            SupplierInvoice.hospital_id == hospital_id,
            SupplierInvoice.payment_status.in_(['unpaid', 'partial'])
        )
        
        # Apply supplier filter if provided
        if supplier_id:
            query = query.filter(SupplierInvoice.supplier_id == supplier_id)
            
        # Order by date (oldest first)
        query = query.order_by(SupplierInvoice.invoice_date)
        
        # Execute query
        invoices = query.all()
        
        # Convert to dictionaries with payment details
        results = []
        
        for invoice in invoices:
            invoice_dict = get_entity_dict(invoice)
            
            # Get supplier information
            supplier = session.query(Supplier).filter_by(supplier_id=invoice.supplier_id).first()
            if supplier:
                invoice_dict['supplier_name'] = supplier.supplier_name
                
            # Get payment information
            payment_total = session.query(func.sum(SupplierPayment.amount)).filter_by(
                invoice_id=invoice.invoice_id
            ).scalar() or 0
            
            payment_total = Decimal(payment_total)
            balance_due = invoice.total_amount - payment_total
            
            invoice_dict['payment_total'] = float(payment_total)
            invoice_dict['balance_due'] = float(balance_due)
            
            # Get payment history
            payments = session.query(SupplierPayment).filter_by(
                invoice_id=invoice.invoice_id
            ).order_by(SupplierPayment.payment_date).all()
            
            invoice_dict['payments'] = [get_entity_dict(payment) for payment in payments]
            
            results.append(invoice_dict)
            
        return results
        
    except Exception as e:
        logger.error(f"Error getting pending supplier invoices: {str(e)}")
        raise# Continuation of supplier_service.py

# def _search_purchase_orders(
#     session: Session,
#     hospital_id: uuid.UUID,
#     supplier_id: Optional[uuid.UUID] = None,
#     po_number: Optional[str] = None,
#     status: Optional[str] = None,
#     start_date: Optional[datetime] = None,
#     end_date: Optional[datetime] = None,
#     page: int = 1,
#     per_page: int = 20
# ) -> Dict:
#     """
#     Internal function to search purchase orders within a session
#     """
#     try:
#         # Base query
#         query = session.query(PurchaseOrderHeader).filter_by(hospital_id=hospital_id)
        
#         # Apply filters
#         if supplier_id:
#             query = query.filter(PurchaseOrderHeader.supplier_id == supplier_id)
            
#         if po_number:
#             query = query.filter(PurchaseOrderHeader.po_number.ilike(f"%{po_number}%"))
            
#         if status:
#             query = query.filter(PurchaseOrderHeader.status == status)
            
#         if start_date:
#             query = query.filter(PurchaseOrderHeader.po_date >= start_date)
            
#         if end_date:
#             query = query.filter(PurchaseOrderHeader.po_date <= end_date)
            
#         # Count total for pagination
#         total_count = query.count()
        
#         # Apply pagination
#         query = query.order_by(desc(PurchaseOrderHeader.po_date))
#         query = query.offset((page - 1) * per_page).limit(per_page)
        
#         # Execute query
#         pos = query.all()
        
#         # Convert to dictionaries
#         po_list = []
        
#         for po in pos:
#             po_dict = get_entity_dict(po)
            
#             # Get the supplier name
#             supplier = session.query(Supplier).filter_by(supplier_id=po.supplier_id).first()
#             if supplier:
#                 po_dict['supplier_name'] = supplier.supplier_name
                
#             # Add line count
#             line_count = session.query(PurchaseOrderLine).filter_by(po_id=po.po_id).count()
#             po_dict['line_count'] = line_count
            
#             po_list.append(po_dict)
        
#         # Prepare pagination info
#         pagination = {
#             'page': page,
#             'per_page': per_page,
#             'total_count': total_count,
#             'total_pages': (total_count + per_page - 1) // per_page
#         }
        
#         return {
#             'purchase_orders': po_list,
#             'pagination': pagination
#         }
        
#     except Exception as e:    
#         logger.error(f"Error searching purchase orders: {str(e)}")
#         raise

# ===================================================================
# Supplier Invoice Management
# ===================================================================

def create_supplier_invoice(
    hospital_id: uuid.UUID,
    invoice_data: Dict,
    create_stock_entries: bool = True,
    create_gl_entries: bool = True,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create a supplier invoice
    
    Args:
        hospital_id: Hospital UUID
        invoice_data: Dictionary containing invoice header and line items
        create_stock_entries: Whether to create inventory entries
        create_gl_entries: Whether to create GL entries
        current_user_id: ID of the user creating the invoice
        session: Database session (optional)
        
    Returns:
        Dictionary containing created invoice details
    """
    if session is not None:
        return _create_supplier_invoice(
            session, hospital_id, invoice_data, 
            create_stock_entries, create_gl_entries, current_user_id
        )
    
    with get_db_session() as new_session:
        return _create_supplier_invoice(
            new_session, hospital_id, invoice_data, 
            create_stock_entries, create_gl_entries, current_user_id
        )

def _create_supplier_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_data: Dict,
    create_stock_entries: bool = True,
    create_gl_entries: bool = True,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to create a supplier invoice within a session
    """
    try:
        # Validate supplier
        supplier_id = invoice_data.get('supplier_id')
        if not supplier_id:
            raise ValueError("Supplier ID is required")
            
        supplier = session.query(Supplier).filter_by(
            supplier_id=supplier_id,
            hospital_id=hospital_id
        ).first()
        
        if not supplier:
            raise ValueError(f"Supplier with ID {supplier_id} not found")
            
        # Check if supplier is blacklisted
        if supplier.black_listed:
            raise ValueError(f"Supplier '{supplier.supplier_name}' is blacklisted")
            
        # Validate line items
        line_items = invoice_data.get('line_items', [])
        if not line_items:
            raise ValueError("At least one line item is required")
            
        # Get PO if provided
        po = None
        po_id = invoice_data.get('po_id')
        if po_id:
            po = session.query(PurchaseOrderHeader).filter_by(
                po_id=po_id,
                hospital_id=hospital_id
            ).first()
            
            if not po:
                raise ValueError(f"Purchase order with ID {po_id} not found")
                
            # Check if PO is cancelled
            if po.status == 'cancelled':
                raise ValueError("Cannot create invoice for a cancelled purchase order")
                
            # Check if supplier matches
            if po.supplier_id != supplier_id:
                raise ValueError("Invoice supplier does not match purchase order supplier")
            
        # Create invoice header
        invoice = SupplierInvoice(
            hospital_id=hospital_id,
            po_id=po_id,
            supplier_id=supplier_id,
            supplier_invoice_number=invoice_data.get('supplier_invoice_number'),
            invoice_date=invoice_data.get('invoice_date', datetime.now(timezone.utc)),
            supplier_gstin=invoice_data.get('supplier_gstin', supplier.gst_registration_number),
            place_of_supply=invoice_data.get('place_of_supply', supplier.state_code),
            reverse_charge=invoice_data.get('reverse_charge', False),
            currency_code=invoice_data.get('currency_code', 'INR'),
            exchange_rate=invoice_data.get('exchange_rate', 1.0),
            cgst_amount=Decimal('0'),
            sgst_amount=Decimal('0'),
            igst_amount=Decimal('0'),
            total_gst_amount=Decimal('0'),
            total_amount=Decimal('0'),
            itc_eligible=invoice_data.get('itc_eligible', True),
            payment_status='unpaid',
            due_date=invoice_data.get('due_date')
        )
        
        if current_user_id:
            invoice.created_by = current_user_id
            
        session.add(invoice)
        session.flush()  # To get the invoice_id
        
        # Create invoice lines
        invoice_lines = []
        total_amount = Decimal('0')
        total_cgst = Decimal('0')
        total_sgst = Decimal('0')
        total_igst = Decimal('0')
        
        for item_data in line_items:
            # Validate medicine
            medicine_id = item_data.get('medicine_id')
            if not medicine_id:
                raise ValueError("Medicine ID is required for each line item")
                
            medicine = session.query(Medicine).filter_by(
                medicine_id=medicine_id,
                hospital_id=hospital_id
            ).first()
            
            if not medicine:
                raise ValueError(f"Medicine with ID {medicine_id} not found")
                
            # Check if interstate GST applies
            is_interstate = supplier.state_code != invoice.place_of_supply
            
            units = Decimal(str(item_data.get('units', 0)))
            pack_purchase_price = Decimal(str(item_data.get('pack_purchase_price', 0)))
            pack_mrp = Decimal(str(item_data.get('pack_mrp', 0)))
            units_per_pack = Decimal(str(item_data.get('units_per_pack', 1)))
            
            # Calculate unit price
            unit_price = pack_purchase_price / units_per_pack if units_per_pack > 0 else Decimal('0')
            
            # Handle discounts (Business Rule #3)
            is_free_item = item_data.get('is_free_item', False)
            referenced_line_id = item_data.get('referenced_line_id')
            discount_percent = Decimal(str(item_data.get('discount_percent', 0)))
            discount_amount = Decimal('0')
            pre_gst_discount = item_data.get('pre_gst_discount', True)
            
            # Free items have zero price
            if is_free_item:
                pack_purchase_price = Decimal('0')
                unit_price = Decimal('0')
            else:
                # Calculate discount amount
                if discount_percent > 0:
                    discount_amount = (units * pack_purchase_price * discount_percent / 100).quantize(Decimal('0.01'))
            
            # Calculate taxable amount
            taxable_amount = units * pack_purchase_price
            if discount_amount > 0 and pre_gst_discount:
                taxable_amount -= discount_amount
                
            # Calculate tax amounts
            gst_rate = Decimal(str(item_data.get('gst_rate', medicine.gst_rate or 0)))
            
            # Set appropriate GST rates based on inter/intra state
            cgst_rate = Decimal('0')
            sgst_rate = Decimal('0')
            igst_rate = Decimal('0')
            
            if is_interstate:
                igst_rate = gst_rate
            else:
                cgst_rate = gst_rate / 2
                sgst_rate = gst_rate / 2
                
            # Calculate tax amounts
            cgst = (taxable_amount * cgst_rate / 100).quantize(Decimal('0.01'))
            sgst = (taxable_amount * sgst_rate / 100).quantize(Decimal('0.01'))
            igst = (taxable_amount * igst_rate / 100).quantize(Decimal('0.01'))
            total_gst = cgst + sgst + igst
            
            # Calculate line total
            line_total = taxable_amount + total_gst
            
            # If discount is post-GST, apply it to the final amount
            if discount_amount > 0 and not pre_gst_discount:
                line_total -= discount_amount
                
            # Add to totals
            total_amount += line_total
            total_cgst += cgst
            total_sgst += sgst
            total_igst += igst
            
            # Create invoice line
            invoice_line = SupplierInvoiceLine(
                hospital_id=hospital_id,
                invoice_id=invoice.invoice_id,
                medicine_id=medicine_id,
                medicine_name=medicine.medicine_name,
                units=units,
                pack_purchase_price=pack_purchase_price,
                pack_mrp=pack_mrp,
                units_per_pack=units_per_pack,
                unit_price=unit_price,
                is_free_item=is_free_item,
                referenced_line_id=referenced_line_id,
                discount_percent=discount_percent,
                discount_amount=discount_amount,
                pre_gst_discount=pre_gst_discount,
                taxable_amount=taxable_amount,
                hsn_code=medicine.hsn_code or item_data.get('hsn_code'),
                gst_rate=gst_rate,
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                igst_rate=igst_rate,
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                total_gst=total_gst,
                line_total=line_total,
                batch_number=item_data.get('batch_number'),
                manufacturing_date=item_data.get('manufacturing_date'),
                expiry_date=item_data.get('expiry_date'),
                itc_eligible=item_data.get('itc_eligible', invoice.itc_eligible)
            )
            
            if current_user_id:
                invoice_line.created_by = current_user_id
                
            session.add(invoice_line)
            invoice_lines.append(invoice_line)
            
        # Update invoice totals
        invoice.cgst_amount = total_cgst
        invoice.sgst_amount = total_sgst
        invoice.igst_amount = total_igst
        invoice.total_gst_amount = total_cgst + total_sgst + total_igst
        invoice.total_amount = total_amount
        
        session.flush()
        
        # Create stock entries if requested
        if create_stock_entries:
            stock_result = record_stock_from_supplier_invoice(
                invoice.invoice_id,
                current_user_id,
                session
            )
            
        # Create GL entries if requested
        gl_transaction = None
        if create_gl_entries:
            gl_result = create_supplier_invoice_gl_entries(
                invoice.invoice_id,
                current_user_id,
                session
            )
            
        # Return the created invoice with lines
        result = get_entity_dict(invoice)
        result['line_items'] = [get_entity_dict(line) for line in invoice_lines]
        result['supplier_name'] = supplier.supplier_name
        
        return result
        
    except Exception as e:
        logger.error(f"Error creating supplier invoice: {str(e)}")
        session.rollback()
        raise

def get_supplier_invoice_by_id(
    invoice_id: uuid.UUID,
    hospital_id: uuid.UUID,
    include_payments: bool = True,
    session: Optional[Session] = None
) -> Dict:
    """
    Get a supplier invoice by ID with its line items
    
    Args:
        invoice_id: Supplier Invoice UUID
        hospital_id: Hospital UUID for security
        include_payments: Whether to include payment details
        session: Database session (optional)
        
    Returns:
        Dictionary containing invoice details with line items
    """
    if session is not None:
        return _get_supplier_invoice_by_id(session, invoice_id, hospital_id, include_payments)
    
    with get_db_session() as new_session:
        return _get_supplier_invoice_by_id(new_session, invoice_id, hospital_id, include_payments)

def _get_supplier_invoice_by_id(
    session: Session,
    invoice_id: uuid.UUID,
    hospital_id: uuid.UUID,
    include_payments: bool = True
) -> Dict:
    """
    Internal function to get a supplier invoice by ID within a session
    """
    try:
        # Get the invoice
        invoice = session.query(SupplierInvoice).filter_by(
            invoice_id=invoice_id,
            hospital_id=hospital_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Supplier invoice with ID {invoice_id} not found")
            
        # Get the line items
        lines = session.query(SupplierInvoiceLine).filter_by(
            invoice_id=invoice_id
        ).all()
        
        # Get the supplier
        supplier = session.query(Supplier).filter_by(
            supplier_id=invoice.supplier_id
        ).first()
        
        # Convert to dictionary
        result = get_entity_dict(invoice)
        result['line_items'] = [get_entity_dict(line) for line in lines]
        
        if supplier:
            result['supplier_name'] = supplier.supplier_name
            result['supplier_address'] = supplier.supplier_address
            result['contact_info'] = supplier.contact_info
            
        # Include payments if requested
        if include_payments:
            payments = session.query(SupplierPayment).filter_by(
                invoice_id=invoice_id
            ).all()
            
            result['payments'] = [get_entity_dict(payment) for payment in payments]
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting supplier invoice: {str(e)}")
        raise

def search_supplier_invoices(
    hospital_id: uuid.UUID,
    supplier_id: Optional[uuid.UUID] = None,
    invoice_number: Optional[str] = None,
    payment_status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 20,
    session: Optional[Session] = None
) -> Dict:
    """
    Search supplier invoices with filtering and pagination
    
    Args:
        hospital_id: Hospital UUID
        supplier_id: Filter by supplier ID
        invoice_number: Filter by invoice number
        payment_status: Filter by payment status
        start_date: Filter by start date
        end_date: Filter by end date
        page: Page number for pagination
        per_page: Number of items per page
        session: Database session (optional)
        
    Returns:
        Dictionary containing invoice list and pagination info
    """
    if session is not None:
        return _search_supplier_invoices(
            session, hospital_id, supplier_id, invoice_number, 
            payment_status, start_date, end_date, page, per_page
        )
    
    with get_db_session() as new_session:
        return _search_supplier_invoices(
            new_session, hospital_id, supplier_id, invoice_number, 
            payment_status, start_date, end_date, page, per_page
        )