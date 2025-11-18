# app/services/inventory_service.py

from datetime import datetime, timezone, timedelta
import uuid
from typing import Dict, List, Optional, Tuple, Union
from decimal import Decimal
import logging

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.orm import Session

from app.models.master import Medicine, ChartOfAccounts
from app.models.transaction import Inventory, SupplierInvoice, SupplierInvoiceLine
from app.services.database_service import get_db_session, get_entity_dict

logger = logging.getLogger(__name__)

def record_opening_stock(
    hospital_id: uuid.UUID,
    medicine_id: uuid.UUID,
    batch: str,
    expiry: datetime,
    quantity: Decimal,
    pack_purchase_price: Decimal,
    pack_mrp: Decimal,
    units_per_pack: Decimal,
    location: Optional[str] = None,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Record opening stock for a medicine
    
    Args:
        hospital_id: Hospital UUID
        medicine_id: Medicine UUID
        batch: Batch number
        expiry: Expiry date
        quantity: Quantity
        pack_purchase_price: Purchase price per pack
        pack_mrp: MRP per pack
        units_per_pack: Units per pack
        location: Storage location
        current_user_id: ID of the user recording the stock
        session: Database session (optional)
        
    Returns:
        Dictionary containing created inventory record
    """
    if session is not None:
        return _record_opening_stock(
            session, hospital_id, medicine_id, batch, expiry, quantity,
            pack_purchase_price, pack_mrp, units_per_pack, location, current_user_id
        )
    
    with get_db_session() as new_session:
        return _record_opening_stock(
            new_session, hospital_id, medicine_id, batch, expiry, quantity,
            pack_purchase_price, pack_mrp, units_per_pack, location, current_user_id
        )

def _record_opening_stock(
    session: Session,
    hospital_id: uuid.UUID,
    medicine_id: uuid.UUID,
    batch: str,
    expiry: datetime,
    quantity: Decimal,
    pack_purchase_price: Decimal,
    pack_mrp: Decimal,
    units_per_pack: Decimal,
    location: Optional[str] = None,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to record opening stock for a medicine within a session
    """
    try:
        # Get medicine details
        medicine = session.query(Medicine).filter_by(
            hospital_id=hospital_id, medicine_id=medicine_id
        ).first()
        
        if not medicine:
            raise ValueError(f"Medicine with ID {medicine_id} not found")
        
        # Calculate unit price
        unit_price = pack_purchase_price / units_per_pack if units_per_pack > 0 else pack_purchase_price
        
        # Check if there's already an entry for this medicine and batch
        existing_entry = session.query(Inventory).filter(
            Inventory.hospital_id == hospital_id,
            Inventory.medicine_id == medicine_id,
            Inventory.batch == batch
        ).first()
        
        if existing_entry:
            raise ValueError(f"Opening stock for medicine {medicine.medicine_name} batch {batch} already exists")
        
        # Create inventory record
        inventory_entry = Inventory(
            hospital_id=hospital_id,
            stock_type='Opening Stock',
            medicine_id=medicine_id,
            medicine_name=medicine.medicine_name,
            medicine_category=medicine.category.name if medicine.category else None,
            batch=batch,
            expiry=expiry,
            pack_purchase_price=pack_purchase_price,
            pack_mrp=pack_mrp,
            units_per_pack=units_per_pack,
            unit_price=unit_price,
            sale_price=pack_mrp / units_per_pack if units_per_pack > 0 else pack_mrp,
            units=quantity,
            current_stock=quantity,
            location=location,
            transaction_date=datetime.now(timezone.utc)
        )
        
        if current_user_id:
            inventory_entry.created_by = current_user_id
            
        session.add(inventory_entry)
        
        # Update medicine current stock
        medicine.current_stock = (medicine.current_stock or 0) + quantity
        
        session.flush()
        
        return get_entity_dict(inventory_entry)
        
    except Exception as e:
        logger.error(f"Error recording opening stock: {str(e)}")
        session.rollback()
        raise

def record_stock_adjustment(
    hospital_id: uuid.UUID,
    medicine_id: uuid.UUID,
    batch: str,
    adjustment_quantity: Decimal,
    reason: str,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Record a stock adjustment
    
    Args:
        hospital_id: Hospital UUID
        medicine_id: Medicine UUID
        batch: Batch number
        adjustment_quantity: Adjustment quantity (positive for increase, negative for decrease)
        reason: Reason for adjustment
        current_user_id: ID of the user recording the adjustment
        session: Database session (optional)
        
    Returns:
        Dictionary containing created inventory record
    """
    if session is not None:
        return _record_stock_adjustment(
            session, hospital_id, medicine_id, batch, adjustment_quantity, reason, current_user_id
        )
    
    with get_db_session() as new_session:
        return _record_stock_adjustment(
            new_session, hospital_id, medicine_id, batch, adjustment_quantity, reason, current_user_id
        )

def _record_stock_adjustment(
    session: Session,
    hospital_id: uuid.UUID,
    medicine_id: uuid.UUID,
    batch: str,
    adjustment_quantity: Decimal,
    reason: str,
    current_user_id: Optional[str] = None
) -> Dict:
    """
    Internal function to record a stock adjustment within a session
    """
    try:
        # Get medicine details
        medicine = session.query(Medicine).filter_by(
            hospital_id=hospital_id, medicine_id=medicine_id
        ).first()
        
        if not medicine:
            raise ValueError(f"Medicine with ID {medicine_id} not found")
        
        # Get the latest inventory entry for this medicine and batch
        latest_inventory = session.query(Inventory).filter(
            Inventory.hospital_id == hospital_id,
            Inventory.medicine_id == medicine_id,
            Inventory.batch == batch
        ).order_by(Inventory.created_at.desc()).first()
        
        if not latest_inventory:
            raise ValueError(f"No inventory found for medicine {medicine.medicine_name}, batch {batch}")
        
        # Calculate new stock level
        new_stock = latest_inventory.current_stock + adjustment_quantity
        
        # Validate adjustment
        if new_stock < 0:
            raise ValueError(f"Adjustment would result in negative stock ({new_stock})")
        
        # Create inventory adjustment record
        inventory_entry = Inventory(
            hospital_id=hospital_id,
            stock_type='Adjustment',
            medicine_id=medicine_id,
            medicine_name=medicine.medicine_name,
            medicine_category=medicine.category.name if medicine.category else None,
            batch=batch,
            expiry=latest_inventory.expiry,
            pack_purchase_price=latest_inventory.pack_purchase_price,
            pack_mrp=latest_inventory.pack_mrp,
            units_per_pack=latest_inventory.units_per_pack,
            unit_price=latest_inventory.unit_price,
            sale_price=latest_inventory.sale_price,
            units=adjustment_quantity,
            current_stock=new_stock,
            reason=reason,
            location=latest_inventory.location,
            transaction_date=datetime.now(timezone.utc)
        )
        
        if current_user_id:
            inventory_entry.created_by = current_user_id
            
        session.add(inventory_entry)
        
        # Update medicine current stock
        medicine.current_stock = (medicine.current_stock or 0) + adjustment_quantity
        
        session.flush()
        
        return get_entity_dict(inventory_entry)
        
    except Exception as e:
        logger.error(f"Error recording stock adjustment: {str(e)}")
        session.rollback()
        raise

def record_stock_from_supplier_invoice(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Record inventory based on a supplier invoice
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Supplier Invoice UUID
        current_user_id: ID of the user recording the stock
        session: Database session (optional)
        
    Returns:
        List of dictionaries containing created inventory records
    """
    if session is not None:
        return _record_stock_from_supplier_invoice(
            session, hospital_id, invoice_id, current_user_id
        )
    
    with get_db_session() as new_session:
        return _record_stock_from_supplier_invoice(
            new_session, hospital_id, invoice_id, current_user_id
        )

def _record_stock_from_supplier_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> List[Dict]:
    """
    Internal function to record inventory based on a supplier invoice within a session
    """
    try:
        # Get the invoice with line items
        invoice = session.query(SupplierInvoice).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).first()
        
        if not invoice:
            raise ValueError(f"Supplier invoice with ID {invoice_id} not found")
        
        line_items = session.query(SupplierInvoiceLine).filter_by(
            hospital_id=hospital_id, invoice_id=invoice_id
        ).all()
        
        if not line_items:
            raise ValueError(f"No line items found for supplier invoice ID {invoice_id}")
        
        inventory_entries = []
        
        for item in line_items:
            # Skip free items as they're handled with their referenced items
            if item.is_free_item:
                continue
                
            # Get medicine details
            medicine = session.query(Medicine).filter_by(
                hospital_id=hospital_id, medicine_id=item.medicine_id
            ).first()
            
            if not medicine:
                raise ValueError(f"Medicine with ID {item.medicine_id} not found")
            
            # Calculate unit price and current stock
            unit_price = item.pack_purchase_price / item.units_per_pack if item.units_per_pack > 0 else item.pack_purchase_price
            
            # Check if there's existing stock for this batch
            latest_inventory = session.query(Inventory).filter(
                Inventory.hospital_id == hospital_id,
                Inventory.medicine_id == item.medicine_id,
                Inventory.batch == item.batch_number
            ).order_by(Inventory.created_at.desc()).first()
            
            current_stock = (latest_inventory.current_stock if latest_inventory else 0) + item.units
            
            # Create inventory record
            inventory_entry = Inventory(
                hospital_id=hospital_id,
                stock_type='Purchase',
                medicine_id=item.medicine_id,
                medicine_name=item.medicine_name,
                medicine_category=medicine.category.name if medicine.category else None,
                distributor_invoice_no=invoice.supplier_invoice_number,
                batch=item.batch_number,
                expiry=item.expiry_date,
                pack_purchase_price=item.pack_purchase_price,
                pack_mrp=item.pack_mrp,
                units_per_pack=item.units_per_pack,
                unit_price=unit_price,
                sale_price=item.pack_mrp / item.units_per_pack if item.units_per_pack > 0 else item.pack_mrp,
                units=item.units,
                cgst=item.cgst,
                sgst=item.sgst,
                igst=item.igst,
                total_gst=item.total_gst,
                current_stock=current_stock,
                transaction_date=invoice.invoice_date
            )
            
            if current_user_id:
                inventory_entry.created_by = current_user_id
                
            session.add(inventory_entry)
            inventory_entries.append(inventory_entry)
            
            # Also handle any free items related to this item
            free_items = session.query(SupplierInvoiceLine).filter(
                SupplierInvoiceLine.hospital_id == hospital_id,
                SupplierInvoiceLine.invoice_id == invoice_id,
                SupplierInvoiceLine.is_free_item == True,
                SupplierInvoiceLine.referenced_line_id == item.line_id
            ).all()
            
            for free_item in free_items:
                # Create inventory record for the free item
                free_current_stock = current_stock + free_item.units
                
                free_inventory_entry = Inventory(
                    hospital_id=hospital_id,
                    stock_type='Purchase (Free)',
                    medicine_id=free_item.medicine_id,
                    medicine_name=free_item.medicine_name,
                    medicine_category=medicine.category.name if medicine.category else None,
                    distributor_invoice_no=invoice.supplier_invoice_number,
                    batch=free_item.batch_number,
                    expiry=free_item.expiry_date,
                    pack_purchase_price=Decimal('0'),  # Free items have zero cost
                    pack_mrp=free_item.pack_mrp,
                    units_per_pack=free_item.units_per_pack,
                    unit_price=Decimal('0'),
                    sale_price=free_item.pack_mrp / free_item.units_per_pack if free_item.units_per_pack > 0 else free_item.pack_mrp,
                    units=free_item.units,
                    current_stock=free_current_stock,
                    transaction_date=invoice.invoice_date
                )
                
                if current_user_id:
                    free_inventory_entry.created_by = current_user_id
                    
                session.add(free_inventory_entry)
                inventory_entries.append(free_inventory_entry)
                
                # Update current stock for subsequent entries
                current_stock = free_current_stock
            
            # Update medicine current stock
            medicine.current_stock = (medicine.current_stock or 0) + item.units + sum(free_item.units for free_item in free_items)
            
        session.flush()
        
        return [get_entity_dict(entry) for entry in inventory_entries]
        
    except Exception as e:
        logger.error(f"Error recording stock from supplier invoice: {str(e)}")
        session.rollback()
        raise

def get_stock_details(
    hospital_id: uuid.UUID,
    medicine_id: Optional[uuid.UUID] = None,
    batch: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get current stock details with batch information
    
    Args:
        hospital_id: Hospital UUID
        medicine_id: Medicine UUID (optional)
        batch: Batch number (optional)
        session: Database session (optional)
        
    Returns:
        List of dictionaries containing stock details by medicine and batch
    """
    if session is not None:
        return _get_stock_details(session, hospital_id, medicine_id, batch)
    
    with get_db_session() as new_session:
        return _get_stock_details(new_session, hospital_id, medicine_id, batch)

def _get_stock_details(
    session: Session,
    hospital_id: uuid.UUID,
    medicine_id: Optional[uuid.UUID] = None,
    batch: Optional[str] = None
) -> List[Dict]:
    """
    Internal function to get current stock details with batch information within a session
    """
    try:
        # Get latest inventory for each medicine by batch
        # We'll use a window function to find the latest entry for each medicine/batch
        from sqlalchemy.sql import text
        
        query = text("""
            WITH latest_inventory AS (
                SELECT 
                    i.*,
                    ROW_NUMBER() OVER (PARTITION BY i.medicine_id, i.batch ORDER BY i.created_at DESC) as rn
                FROM inventory i
                WHERE i.hospital_id = :hospital_id
                    AND (:medicine_id IS NULL OR i.medicine_id = :medicine_id)
                    AND (:batch IS NULL OR i.batch = :batch)
            )
            SELECT * FROM latest_inventory
            WHERE rn = 1 AND current_stock > 0
            ORDER BY medicine_name, expiry
        """)
        
        result = session.execute(query, {
            'hospital_id': hospital_id,
            'medicine_id': medicine_id,
            'batch': batch
        })
        
        # Convert to list of dictionaries
        stock_details = []
        for row in result:
            # Create a dict from the row
            row_dict = {column: getattr(row, column) for column in row._mapping.keys()}
            stock_details.append(row_dict)
            
        return stock_details
        
    except Exception as e:
        logger.error(f"Error getting stock details: {str(e)}")
        raise

def get_low_stock_medicines(
    hospital_id: uuid.UUID,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get medicines with stock below safety level
    
    Args:
        hospital_id: Hospital UUID
        session: Database session (optional)
        
    Returns:
        List of dictionaries containing low stock medicine details
    """
    if session is not None:
        return _get_low_stock_medicines(session, hospital_id)
    
    with get_db_session() as new_session:
        return _get_low_stock_medicines(new_session, hospital_id)

def _get_low_stock_medicines(
    session: Session,
    hospital_id: uuid.UUID
) -> List[Dict]:
    """
    Internal function to get medicines with stock below safety level within a session
    """
    try:
        # Query medicines where current stock is below safety stock
        medicines = session.query(Medicine).filter(
            Medicine.hospital_id == hospital_id,
            Medicine.safety_stock > 0,
            Medicine.current_stock < Medicine.safety_stock
        ).all()
        
        # Convert to dictionaries with additional info
        result = []
        for medicine in medicines:
            medicine_dict = get_entity_dict(medicine)
            medicine_dict['required_quantity'] = medicine.safety_stock - (medicine.current_stock or 0)
            result.append(medicine_dict)
            
        return result
        
    except Exception as e:
        logger.error(f"Error getting low stock medicines: {str(e)}")
        raise

def get_expiring_medicines(
    hospital_id: uuid.UUID,
    days: int = 90,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get medicines that will expire within the specified number of days
    
    Args:
        hospital_id: Hospital UUID
        days: Number of days to check for expiry
        session: Database session (optional)
        
    Returns:
        List of dictionaries containing expiring medicine details
    """
    if session is not None:
        return _get_expiring_medicines(session, hospital_id, days)
    
    with get_db_session() as new_session:
        return _get_expiring_medicines(new_session, hospital_id, days)

def _get_expiring_medicines(
    session: Session,
    hospital_id: uuid.UUID,
    days: int = 90
) -> List[Dict]:
    """
    Internal function to get medicines that will expire within the specified days
    """
    try:
        # Calculate the date range
        today = datetime.now(timezone.utc).date()
        expiry_date = today + timedelta(days=days)
        
        # We'll use a window function to find the latest entry for each medicine/batch
        from sqlalchemy.sql import text
        
        query = text("""
            WITH latest_inventory AS (
                SELECT 
                    i.*,
                    ROW_NUMBER() OVER (PARTITION BY i.medicine_id, i.batch ORDER BY i.created_at DESC) as rn
                FROM inventory i
                WHERE i.hospital_id = :hospital_id
            )
            SELECT li.* FROM latest_inventory li
            WHERE li.rn = 1 
              AND li.current_stock > 0 
              AND li.expiry BETWEEN :today AND :expiry_date
            ORDER BY li.expiry
        """)
        
        result = session.execute(query, {
            'hospital_id': hospital_id,
            'today': today,
            'expiry_date': expiry_date
        })
        
        # Convert to list of dictionaries
        expiring_items = []
        for row in result:
            # Create a dict from the row
            row_dict = {column: getattr(row, column) for column in row._mapping.keys()}
            
            # Calculate days until expiry
            days_until_expiry = (row_dict['expiry'] - today).days
            row_dict['days_until_expiry'] = days_until_expiry
            
            expiring_items.append(row_dict)
            
        return expiring_items
        
    except Exception as e:
        logger.error(f"Error getting expiring medicines: {str(e)}")
        raise

def get_inventory_movement(
    hospital_id: uuid.UUID,
    medicine_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
    session: Optional[Session] = None
) -> Dict:
    """
    Get inventory movement for a specified period
    
    Args:
        hospital_id: Hospital UUID
        medicine_id: Medicine UUID (optional)
        date_from: Start date (optional)
        date_to: End date (optional)
        page: Page number (starting from 1)
        page_size: Number of results per page
        session: Database session (optional)
        
    Returns:
        Dictionary containing paginated inventory movement records
    """
    if session is not None:
        return _get_inventory_movement(
            session, hospital_id, medicine_id, date_from, date_to, page, page_size
        )
    
    with get_db_session() as new_session:
        return _get_inventory_movement(
            new_session, hospital_id, medicine_id, date_from, date_to, page, page_size
        )

def _get_inventory_movement(
    session: Session,
    hospital_id: uuid.UUID,
    medicine_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50
) -> Dict:
    """
    Internal function to get inventory movement for a specified period within a session
    """
    try:
        # Build query
        query = session.query(Inventory).filter(
            Inventory.hospital_id == hospital_id
        )
        
        # Apply filters
        if medicine_id:
            query = query.filter(Inventory.medicine_id == medicine_id)
            
        if date_from:
            query = query.filter(Inventory.transaction_date >= date_from)
            
        if date_to:
            query = query.filter(Inventory.transaction_date <= date_to)
            
        # Count total matching records
        total_count = query.count()
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(Inventory.transaction_date.desc())
        query = query.offset(offset).limit(page_size)
        
        # Execute query
        inventory_records = query.all()
        
        # Convert to dictionaries
        result = {
            'items': [get_entity_dict(record) for record in inventory_records],
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'pages': (total_count + page_size - 1) // page_size
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting inventory movement: {str(e)}")
        raise

def get_available_batches_for_item(
    item_id: uuid.UUID,
    hospital_id: uuid.UUID,
    branch_id: Optional[uuid.UUID] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get all available batches for an item, sorted by expiry date (FIFO)
    Used for manual batch selection dropdown in invoice creation

    Args:
        item_id: Medicine/Item UUID
        hospital_id: Hospital UUID
        branch_id: Branch UUID (optional, for future branch-level inventory)
        session: Database session (optional)

    Returns:
        List of dicts with batch info:
        - batch_number
        - expiry_date
        - available_qty
        - unit_price
        - sale_price
        - display (formatted string)
    """
    if session is not None:
        return _get_available_batches_for_item(session, item_id, hospital_id, branch_id)

    with get_db_session() as new_session:
        return _get_available_batches_for_item(new_session, item_id, hospital_id, branch_id)

def _get_available_batches_for_item(
    session: Session,
    item_id: uuid.UUID,
    hospital_id: uuid.UUID,
    branch_id: Optional[uuid.UUID] = None
) -> List[Dict]:
    """
    Internal function to get all available batches for an item
    """
    try:
        from sqlalchemy.sql import text

        # Query to get latest inventory for each batch with available stock
        query = text("""
            WITH latest_inventory AS (
                SELECT
                    i.*,
                    ROW_NUMBER() OVER (PARTITION BY i.batch ORDER BY i.created_at DESC) as rn
                FROM inventory i
                WHERE i.hospital_id = :hospital_id
                  AND i.medicine_id = :item_id
            )
            SELECT
                batch,
                expiry,
                current_stock,
                unit_price,
                sale_price
            FROM latest_inventory
            WHERE rn = 1 AND current_stock > 0
            ORDER BY expiry ASC  -- FIFO: oldest expiry first
        """)

        result = session.execute(query, {
            'hospital_id': hospital_id,
            'item_id': item_id
        })

        # Format batches for dropdown display
        batches = []
        for row in result:
            batch_data = {
                'batch_number': row.batch,
                'expiry_date': row.expiry.strftime('%Y-%m-%d') if row.expiry else '',
                'available_qty': float(row.current_stock),
                'unit_price': float(row.unit_price) if row.unit_price else 0,
                'sale_price': float(row.sale_price) if row.sale_price else 0,
                'display': f"{row.batch} (Exp: {row.expiry.strftime('%d/%b/%Y') if row.expiry else 'N/A'}) - Avail: {int(row.current_stock)} units"
            }
            batches.append(batch_data)

        return batches

    except Exception as e:
        logger.error(f"Error getting available batches for item: {str(e)}")
        raise

def get_batch_selection_for_invoice(
    hospital_id: uuid.UUID,
    medicine_id: uuid.UUID,
    quantity_needed: Decimal,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get batch selection for invoice based on FIFO

    Args:
        hospital_id: Hospital UUID
        medicine_id: Medicine UUID
        quantity_needed: Quantity needed for invoice
        session: Database session (optional)

    Returns:
        List of dictionaries containing batch selection with quantities
    """
    if session is not None:
        return _get_batch_selection_for_invoice(
            session, hospital_id, medicine_id, quantity_needed
        )

    with get_db_session() as new_session:
        return _get_batch_selection_for_invoice(
            new_session, hospital_id, medicine_id, quantity_needed
        )

def _get_batch_selection_for_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    medicine_id: uuid.UUID,
    quantity_needed: Decimal
) -> List[Dict]:
    """
    Internal function to get batch selection for invoice based on FIFO
    """
    try:
        # CONSOLIDATE multiple inventory records for same batch
        # Aggregate stock across all records, allocate FIFO by earliest expiry
        from sqlalchemy.sql import text

        query = text("""
            SELECT
                i.batch,
                MIN(i.expiry) as expiry,  -- Earliest expiry for FIFO
                SUM(i.current_stock) as current_stock,  -- Total stock across all records
                -- Weighted average price based on stock
                SUM(i.sale_price * i.current_stock) / NULLIF(SUM(i.current_stock), 0) as sale_price,
                SUM(i.unit_price * i.current_stock) / NULLIF(SUM(i.current_stock), 0) as unit_price,
                MAX(i.pack_mrp) as pack_mrp
            FROM inventory i
            WHERE i.hospital_id = :hospital_id
              AND i.medicine_id = :medicine_id
              AND i.current_stock > 0  -- Only batches with stock
            GROUP BY i.batch
            ORDER BY MIN(i.expiry)  -- FIFO based on earliest expiry
        """)
        
        result = session.execute(query, {
            'hospital_id': hospital_id,
            'medicine_id': medicine_id
        })
        
        # Process batches based on FIFO
        remaining_quantity = quantity_needed
        batch_selection = []
        
        for row in result:
            # Convert row to dict
            batch_info = {column: getattr(row, column) for column in row._mapping.keys()}
            
            if remaining_quantity <= 0:
                break
                
            available_quantity = batch_info['current_stock']
            
            if available_quantity <= 0:
                continue
                
            # Calculate how much to take from this batch
            if available_quantity >= remaining_quantity:
                quantity_from_batch = remaining_quantity
                remaining_quantity = 0
            else:
                quantity_from_batch = available_quantity
                remaining_quantity -= available_quantity
            
            # Add to selection
            selection = {
                'batch': batch_info['batch'],
                'expiry_date': batch_info['expiry'],
                'quantity': quantity_from_batch,
                'unit_price': batch_info['unit_price'],
                'sale_price': batch_info['sale_price']
            }
            
            batch_selection.append(selection)
        
        if remaining_quantity > 0:
            logger.warning(f"Insufficient stock for medicine ID {medicine_id}. " +
                          f"Needed: {quantity_needed}, Available: {quantity_needed - remaining_quantity}")
            
        return batch_selection
        
    except Exception as e:
        logger.error(f"Error getting batch selection: {str(e)}")
        raise

def get_medicine_consumption_report(
    hospital_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
    category_id: Optional[uuid.UUID] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Get medicine consumption report for a specified period
    
    Args:
        hospital_id: Hospital UUID
        date_from: Start date
        date_to: End date
        category_id: Medicine category ID (optional)
        session: Database session (optional)
        
    Returns:
        List of dictionaries containing medicine consumption details
    """
    if session is not None:
        return _get_medicine_consumption_report(
            session, hospital_id, date_from, date_to, category_id
        )
    
    with get_db_session() as new_session:
        return _get_medicine_consumption_report(
            new_session, hospital_id, date_from, date_to, category_id
        )

def _get_medicine_consumption_report(
    session: Session,
    hospital_id: uuid.UUID,
    date_from: datetime,
    date_to: datetime,
    category_id: Optional[uuid.UUID] = None
) -> List[Dict]:
    """
    Internal function to get medicine consumption report for a specified period
    """
    try:
        # Query inventory transactions for consumption (negative units)
        query = session.query(
            Inventory.medicine_id,
            Inventory.medicine_name,
            Inventory.medicine_category,
            func.sum(Inventory.units * -1).label('consumed_quantity'),
            func.sum(Inventory.unit_price * Inventory.units * -1).label('cost_value'),
            func.sum(Inventory.sale_price * Inventory.units * -1).label('sale_value')
        ).filter(
            Inventory.hospital_id == hospital_id,
            Inventory.transaction_date.between(date_from, date_to),
            Inventory.units < 0  # Only outgoing transactions
        )
        
        if category_id:
            # Join with Medicine to filter by category
            query = query.join(Medicine, Inventory.medicine_id == Medicine.medicine_id)
            query = query.filter(Medicine.category_id == category_id)
            
        query = query.group_by(
            Inventory.medicine_id,
            Inventory.medicine_name,
            Inventory.medicine_category
        )
        
        query = query.order_by(func.sum(Inventory.units * -1).desc())
        
        # Execute query
        result = query.all()
        
        # Convert to list of dictionaries
        consumption_report = []
        for row in result:
            consumption_report.append({
                'medicine_id': row.medicine_id,
                'medicine_name': row.medicine_name,
                'category': row.medicine_category,
                'consumed_quantity': row.consumed_quantity,
                'cost_value': row.cost_value,
                'sale_value': row.sale_value,
                'profit': row.sale_value - row.cost_value if row.sale_value and row.cost_value else None
            })
            
        return consumption_report
        
    except Exception as e:
        logger.error(f"Error getting medicine consumption report: {str(e)}")
        raise

def consume_medicine_for_procedure(
    hospital_id: uuid.UUID,
    service_id: uuid.UUID,
    patient_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Consume medicines for a procedure based on standard consumption
    
    Args:
        hospital_id: Hospital UUID
        service_id: Service UUID
        patient_id: Patient UUID
        current_user_id: ID of the user recording the consumption
        session: Database session (optional)
        
    Returns:
        List of dictionaries containing consumed medicine details
    """
    if session is not None:
        return _consume_medicine_for_procedure(
            session, hospital_id, service_id, patient_id, current_user_id
        )
    
    with get_db_session() as new_session:
        return _consume_medicine_for_procedure(
            new_session, hospital_id, service_id, patient_id, current_user_id
        )

def _consume_medicine_for_procedure(
    session: Session,
    hospital_id: uuid.UUID,
    service_id: uuid.UUID,
    patient_id: uuid.UUID,
    current_user_id: Optional[str] = None
) -> List[Dict]:
    """
    Internal function to consume medicines for a procedure based on standard consumption
    """
    try:
        from app.models.master import ConsumableStandard, Service
        
        # Get service details
        service = session.query(Service).filter_by(
            hospital_id=hospital_id, service_id=service_id
        ).first()
        
        if not service:
            raise ValueError(f"Service with ID {service_id} not found")
        
        # Get standard consumables for this service
        consumable_standards = session.query(ConsumableStandard).filter_by(
            hospital_id=hospital_id, service_id=service_id, is_active=True
        ).all()
        
        if not consumable_standards:
            logger.warning(f"No standard consumables defined for service ID {service_id}")
            return []
        
        consumption_entries = []
        
        for standard in consumable_standards:
            # Get medicine details
            medicine = session.query(Medicine).filter_by(
                hospital_id=hospital_id, medicine_id=standard.medicine_id
            ).first()
            
            if not medicine:
                logger.warning(f"Medicine with ID {standard.medicine_id} not found")
                continue
            
            # Check if this is a consumable
            if not medicine.is_consumable:
                logger.warning(f"Medicine {medicine.medicine_name} is not marked as a consumable")
                continue
            
            # Get batches to consume (FIFO)
            batch_selection = _get_batch_selection_for_invoice(
                session, hospital_id, standard.medicine_id, standard.standard_quantity
            )
            
            if not batch_selection or sum(batch['quantity'] for batch in batch_selection) < standard.standard_quantity:
                logger.warning(f"Insufficient stock for consumable {medicine.medicine_name}")
                continue
            
            # Consume from each batch
            for batch in batch_selection:
                # Create inventory consumption record
                inventory_entry = Inventory(
                    hospital_id=hospital_id,
                    stock_type='Procedure Consumption',
                    medicine_id=standard.medicine_id,
                    medicine_name=medicine.medicine_name,
                    medicine_category=medicine.category.name if medicine.category else None,
                    patient_id=patient_id,
                    procedure_id=service_id,
                    batch=batch['batch'],
                    expiry=batch['expiry_date'],
                    unit_price=batch['unit_price'],
                    sale_price=batch['sale_price'],
                    units=-batch['quantity'],  # Negative for consumption
                    current_stock=0,  # Will be updated below
                    reason=f"Used in {service.service_name}",
                    transaction_date=datetime.now(timezone.utc)
                )
                
                if current_user_id:
                    inventory_entry.created_by = current_user_id
                
                # Get the latest inventory for this batch to update current stock
                latest_inventory = session.query(Inventory).filter(
                    Inventory.hospital_id == hospital_id,
                    Inventory.medicine_id == standard.medicine_id,
                    Inventory.batch == batch['batch']
                ).order_by(Inventory.created_at.desc()).first()
                
                if latest_inventory:
                    inventory_entry.current_stock = latest_inventory.current_stock - batch['quantity']
                    
                session.add(inventory_entry)
                consumption_entries.append(inventory_entry)
                
                # Update medicine current stock
                medicine.current_stock = (medicine.current_stock or 0) - batch['quantity']
            
        session.flush()
        
        return [get_entity_dict(entry) for entry in consumption_entries]
        
    except Exception as e:
        logger.error(f"Error consuming medicine for procedure: {str(e)}")
        session.rollback()
        raise

# Function to add to app/services/inventory_service.py

def update_inventory_for_invoice(
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    patient_id: uuid.UUID,
    line_items: List[Dict],
    void: bool = False,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> List[Dict]:
    """
    Update inventory based on invoice line items
    
    Args:
        hospital_id: Hospital UUID
        invoice_id: Invoice UUID
        patient_id: Patient UUID
        line_items: List of line item dictionaries
        void: Whether this is a void operation (reverses the stock movement)
        current_user_id: ID of the user creating the invoice
        session: Database session (optional)
        
    Returns:
        List of dictionaries containing created inventory records
    """
    if session is not None:
        return _update_inventory_for_invoice(
            session, hospital_id, invoice_id, patient_id, line_items, void, current_user_id
        )
    
    with get_db_session() as new_session:
        return _update_inventory_for_invoice(
            new_session, hospital_id, invoice_id, patient_id, line_items, void, current_user_id
        )

def _update_inventory_for_invoice(
    session: Session,
    hospital_id: uuid.UUID,
    invoice_id: uuid.UUID,
    patient_id: uuid.UUID,
    line_items: List[Dict],
    void: bool = False,
    current_user_id: Optional[str] = None
) -> List[Dict]:
    """
    Internal function to update inventory based on invoice line items
    """
    try:
        inventory_entries = []
        
        # Filter line items to only include medicines
        medicine_items = [item for item in line_items if item.get('item_type') == 'Medicine']
        
        for item in medicine_items:
            medicine_id = item.get('medicine_id')
            
            # Skip if no medicine ID or if included in consultation
            if not medicine_id or item.get('included_in_consultation', False):
                continue
                
            # Get medicine details
            medicine = session.query(Medicine).filter_by(
                hospital_id=hospital_id, medicine_id=medicine_id
            ).first()
            
            if not medicine:
                logger.warning(f"Medicine with ID {medicine_id} not found")
                continue
            
            # Determine quantity sign based on void status
            quantity = Decimal(str(item.get('quantity', 1)))
            units_sign = 1 if void else -1  # Negative for sales, positive for voids
            
            # Get batch info
            batch = item.get('batch')
            
            if not batch:
                logger.warning(f"No batch specified for medicine {medicine.medicine_name}")
                continue
            
            # Get the latest inventory for this batch
            latest_inventory = session.query(Inventory).filter(
                Inventory.hospital_id == hospital_id,
                Inventory.medicine_id == medicine_id,
                Inventory.batch == batch
            ).order_by(Inventory.created_at.desc()).first()
            
            if not latest_inventory:
                logger.warning(f"No inventory found for medicine {medicine.medicine_name}, batch {batch}")
                continue

            # Validate inventory for sales (not voids)
            if not void:
                # Validate sufficient stock
                available_stock = latest_inventory.current_stock
                if available_stock < quantity:
                    raise ValueError(
                        f"Inventory Error: Insufficient stock for {medicine.medicine_name} (Batch: {batch}). "
                        f"Available: {available_stock}, Requested: {quantity}"
                    )

                # Validate expiry date exists
                if not latest_inventory.expiry:
                    raise ValueError(
                        f"Inventory Error: Expiry date missing for {medicine.medicine_name} (Batch: {batch})"
                    )

                # Validate expiry date has not passed
                # BYPASS for test user (7777777777) to allow testing with old expiry dates
                from datetime import date
                is_test_user = current_user_id == '7777777777'

                if is_test_user and latest_inventory.expiry < date.today():
                    logger.warning(f"🧪 TEST MODE: Bypassing expiry validation for user {current_user_id} - "
                                 f"{medicine.medicine_name} (Batch: {batch}, Expired: {latest_inventory.expiry.strftime('%d-%b-%Y')})")

                if not is_test_user and latest_inventory.expiry < date.today():
                    raise ValueError(
                        f"Inventory Error: Cannot dispense expired medicine - {medicine.medicine_name} "
                        f"(Batch: {batch}, Expired: {latest_inventory.expiry.strftime('%d-%b-%Y')})"
                    )

            # Calculate current stock after this transaction
            current_stock = latest_inventory.current_stock + (units_sign * quantity)

            # Extract GST values and calculate per-unit amounts
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

            # Create inventory transaction for this sale/void
            stock_type = 'Void' if void else 'Sales'

            inventory_entry = Inventory(
                hospital_id=hospital_id,
                stock_type=stock_type,
                medicine_id=medicine_id,
                medicine_name=medicine.medicine_name,
                medicine_category=medicine.category.name if medicine.category else None,
                bill_id=invoice_id,
                patient_id=patient_id,
                batch=batch,
                expiry=latest_inventory.expiry,
                pack_purchase_price=latest_inventory.pack_purchase_price,
                pack_mrp=latest_inventory.pack_mrp,
                units_per_pack=latest_inventory.units_per_pack,
                unit_price=latest_inventory.unit_price,
                sale_price=item.get('unit_price', latest_inventory.sale_price),
                units=units_sign * quantity,  # Negative for sales, positive for voids
                cgst=cgst_per_unit,
                sgst=sgst_per_unit,
                igst=igst_per_unit,
                total_gst=total_gst_per_unit,
                current_stock=current_stock,
                transaction_date=datetime.now(timezone.utc),
                reason=f"{'Void of' if void else ''} Invoice #{invoice_id}"
            )
            
            if current_user_id:
                inventory_entry.created_by = current_user_id
                
            session.add(inventory_entry)
            inventory_entries.append(inventory_entry)
            
            # Update medicine current stock
            medicine.current_stock = (medicine.current_stock or 0) + (units_sign * quantity)
            
        session.flush()
        
        return [get_entity_dict(entry) for entry in inventory_entries]
        
    except Exception as e:
        logger.error(f"Error updating inventory for invoice: {str(e)}")
        session.rollback()
        raise