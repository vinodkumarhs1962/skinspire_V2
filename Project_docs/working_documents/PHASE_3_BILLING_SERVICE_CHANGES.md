# Billing Service Changes for Phase 3 - Implementation Guide

**File**: `app/services/billing_service.py`
**Date**: 2025-01-07 00:35

---

## Required Changes

### 1. Import Configuration (Add after line 49)

```python
# Import invoice split configuration
from app.config.modules.patient_invoice_config import (
    INVOICE_SPLIT_CONFIGS,
    get_invoice_split_config,
    categorize_line_item
)
from app.config.core_definitions import InvoiceSplitCategory
```

### 2. Modify `_create_invoice()` Function (Lines 113-396)

**Current Logic** (2-way split):
- Groups into: `product_service_gst_items`, `product_service_non_gst_items`, `prescription_items`
- Creates 2 invoices: GST and Non-GST

**New Logic** (4-way split):

```python
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
    """Create invoices with 4-way split for tax compliance"""

    try:
        logger.info("Starting Phase 3: 4-way invoice creation")

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
            is_prescription = (item_type == 'Prescription') or item.get('included_in_consultation', False)

            # Categorize item
            category = categorize_line_item(item_type, is_gst_exempt, is_prescription)

            if category:
                categorized_items[category].append(item)
                logger.info(f"Item '{item.get('item_name')}' → {category.value}")
            else:
                logger.warning(f"Could not categorize item: {item}")

        # Log category counts
        for category, items in categorized_items.items():
            logger.info(f"{category.value}: {len(items)} items")

        # Handle prescription consolidation if no pharmacy registration
        if not has_valid_pharmacy_registration:
            prescription_items = categorized_items[InvoiceSplitCategory.PRESCRIPTION_COMPOSITE]
            if prescription_items:
                # Consolidate to "Doctor's Examination"
                consolidated_item = _consolidate_prescription_items(
                    session, hospital_id, prescription_items, patient_id, current_user_id
                )
                # Add to Service category
                categorized_items[InvoiceSplitCategory.SERVICE_PACKAGE].append(consolidated_item)
                # Clear prescription category
                categorized_items[InvoiceSplitCategory.PRESCRIPTION_COMPOSITE] = []

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
                continue

            config = get_invoice_split_config(category)
            if not config:
                logger.error(f"No configuration found for category: {category}")
                continue

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

            created_invoices.append(invoice)
            split_sequence += 1

            logger.info(f"Created {config.name}: {invoice.invoice_number}")

        # Commit transaction
        session.commit()

        # Convert to dictionaries
        invoice_dicts = [get_entity_dict(inv) for inv in created_invoices]

        logger.info(f"Total Invoices Created: {len(created_invoices)}")
        return {
            'invoices': invoice_dicts,
            'count': len(created_invoices),
            'parent_invoice_id': str(parent_invoice_id) if parent_invoice_id else None
        }

    except Exception as e:
        logger.error(f"Error creating invoice: {str(e)}", exc_info=True)
        session.rollback()
        raise
```

### 3. Create New Helper Function

```python
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
    Create a single invoice for a specific category

    This replaces _create_single_invoice with category-aware logic
    """

    # Validate inventory
    for item in line_items:
        if item.get('item_type') in ['Medicine', 'Prescription', 'OTC']:
            _validate_inventory(session, hospital_id, item)

    # Generate invoice number using category prefix
    invoice_number = generate_invoice_number_with_category(
        hospital_id, category, config, session
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
        line_item = _process_invoice_line_item(session, hospital_id, item, is_interstate)
        processed_line_items.append(line_item)

        # Update totals
        total_amount += line_item.get('line_total', Decimal('0'))
        total_discount += line_item.get('discount_amount', Decimal('0'))
        total_taxable_value += line_item.get('taxable_amount', Decimal('0'))
        total_cgst_amount += line_item.get('cgst_amount', Decimal('0'))
        total_sgst_amount += line_item.get('sgst_amount', Decimal('0'))
        total_igst_amount += line_item.get('igst_amount', Decimal('0'))

    grand_total = total_amount

    # Create invoice header
    invoice = InvoiceHeader(
        invoice_id=uuid.uuid4(),
        hospital_id=hospital_id,
        branch_id=branch_id,
        patient_id=patient_id,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_type=invoice_type,
        is_gst_invoice=is_gst_invoice,
        place_of_supply=place_of_supply,
        is_interstate=is_interstate,
        total_amount=total_amount,
        total_discount=total_discount,
        total_taxable_value=total_taxable_value,
        total_cgst_amount=total_cgst_amount,
        total_sgst_amount=total_sgst_amount,
        total_igst_amount=total_igst_amount,
        grand_total=grand_total,
        balance_due=grand_total,
        notes=notes,
        created_by=current_user_id,
        # Split invoice fields
        parent_transaction_id=parent_invoice_id,
        split_sequence=split_sequence,
        is_split_invoice=(parent_invoice_id is not None),
        split_reason="TAX_COMPLIANCE_SPLIT" if parent_invoice_id else None
    )

    session.add(invoice)
    session.flush()  # Get invoice_id

    # Create line items
    for line_data in processed_line_items:
        line_item = InvoiceLineItem(
            line_item_id=uuid.uuid4(),
            hospital_id=hospital_id,
            invoice_id=invoice.invoice_id,
            # ... populate all fields from line_data
        )
        session.add(line_item)

    # Update inventory
    update_inventory_for_invoice(invoice.invoice_id, session)

    # Create GL entries
    create_invoice_gl_entries(invoice.invoice_id, session)

    return invoice
```

### 4. Modify `generate_invoice_number()` Function

```python
def generate_invoice_number_with_category(
    hospital_id: uuid.UUID,
    category: InvoiceSplitCategory,
    config: 'InvoiceSplitConfig',
    session: Session
) -> str:
    """
    Generate invoice number with category-specific prefix

    Format: {PREFIX}/{FIN_YEAR}/{SEQ}
    Example: SVC/2024-2025/00001
    """
    # Get financial year
    now = datetime.now(timezone.utc)
    current_month = now.month

    if current_month >= 4:
        fin_year = f"{now.year}-{now.year + 1}"
    else:
        fin_year = f"{now.year - 1}-{now.year}"

    prefix = config.prefix

    # Get latest invoice number for this category and financial year
    latest_invoice = session.query(InvoiceHeader).filter(
        InvoiceHeader.hospital_id == hospital_id,
        InvoiceHeader.invoice_number.like(f"{prefix}/{fin_year}/%")
    ).order_by(InvoiceHeader.created_at.desc()).first()

    if latest_invoice:
        seq_num = int(latest_invoice.invoice_number.split('/')[-1]) + 1
    else:
        seq_num = config.starting_number

    invoice_number = f"{prefix}/{fin_year}/{seq_num:05d}"
    return invoice_number
```

---

## Testing Checklist

- [ ] Service + Package items → SVC invoice created
- [ ] OTC with GST → MED invoice created
- [ ] OTC without GST → EXM invoice created
- [ ] Prescription items → RX invoice created
- [ ] All 4 invoices linked with parent_transaction_id
- [ ] Each invoice has correct split_sequence (1-4)
- [ ] Invoice numbers use correct prefixes
- [ ] Serial numbers increment correctly per category
- [ ] Without pharmacy registration → prescriptions consolidated
- [ ] With pharmacy registration → prescriptions as individual items
- [ ] Inventory deducted correctly
- [ ] GL entries created for all invoices
- [ ] All invoices visible in invoice list

---

**Implementation Status**: Documentation Complete | Code Changes Pending
**Next Step**: Implement the changes in billing_service.py
