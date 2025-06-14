# Core Services Functionality Implemented

## Overview

This document describes the functionality implemented across multiple services in the SkinSpire Hospital Management System, with a focus on the integration between the billing, inventory, and general ledger (GL) services. The implementation follows best practices for service integration while maintaining backward compatibility with existing code.

## 1. Billing and Inventory Integration

### Enhanced Functionality

**Centralized Inventory Updates from Billing**
- Added a new function `update_inventory_for_invoice()` in the inventory service that handles all medicine inventory updates from invoice creation in a single transaction
- Implemented FIFO (First In, First Out) stock selection based on expiry dates
- Added support for void operations that correctly reverse inventory movements

**Backward Compatibility**
- Maintained the original `_update_inventory_for_invoice_item()` function in the billing service
- Implemented a fallback mechanism when the new inventory service function fails
- Added proper logging to track when fallback occurs

**Key Benefits**
- Proper separation of concerns with inventory operations handled by the inventory service
- More consistent inventory tracking with centralized management
- Improved error handling and transaction integrity
- No disruption to existing functionality

### Implementation Details

#### Inventory Service Enhancement
```python
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
    """
    # Function processes all medicine line items from an invoice in a batch
    # Supports regular sales and void operations
    # Returns inventory records created
```

#### Billing Service Integration
```python
# In _create_invoice function:
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
    logger.warning(f"Error updating inventory with new method, falling back to legacy method: {str(e)}")
    # Fallback to legacy method
```

## 2. Billing and General Ledger Integration

### Enhanced Functionality

**Complete Accounting Cycle**
- Added `create_refund_gl_entries()` to create proper accounting entries for refunds
- Added `process_void_invoice_gl_entries()` to handle GL entries for voided invoices
- Integrated with existing `create_invoice_gl_entries()` and `create_payment_gl_entries()` functions

**Robust Error Handling**
- Implemented try-except blocks for all GL operations
- Added warning logs when GL operations fail
- Ensured core billing functionality continues even if GL operations fail

**Key Benefits**
- Complete financial tracking for all billing operations
- Proper GST/tax liability management
- Accurate financial reporting
- Non-disruptive integration

### Implementation Details

#### GL Service Enhancements

**New Functions**:
```python
def create_refund_gl_entries(
    payment_id: uuid.UUID,
    refund_amount: Decimal,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Create general ledger entries for a payment refund
    """
    # Creates accounting entries for refunds with proper proportions across payment methods
```

```python
def process_void_invoice_gl_entries(
    void_invoice_id: uuid.UUID,
    original_invoice_id: uuid.UUID,
    current_user_id: Optional[str] = None,
    session: Optional[Session] = None
) -> Dict:
    """
    Process GL entries for a voided invoice
    """
    # Creates reversing entries for voided invoices
```

#### Billing Service Integration

```python
# In _record_payment function:
try:
    create_payment_gl_entries(payment.payment_id, current_user_id, session=session)
except Exception as e:
    logger.warning(f"Error creating payment GL entries: {str(e)}")
    # Continue without GL entries as this is not critical for payment recording
```

```python
# In _issue_refund function:
try:
    create_refund_gl_entries(payment.payment_id, refund_amount, current_user_id, session=session)
except Exception as e:
    logger.warning(f"Error creating refund GL entries: {str(e)}")
    # Continue without GL entries as this is not critical
```

## 3. Transaction Processing Flow

### Invoice Creation Flow

1. **Billing Service**: Create invoice header and line items
2. **Inventory Service**: Update inventory for medicine items
   - Decrease stock levels
   - Record batch and expiry information
   - Update medicine current stock totals
3. **GL Service**: Create accounting entries
   - Debit Accounts Receivable
   - Credit Revenue accounts by type
   - Credit Tax Liability accounts (CGST/SGST/IGST)
   - Update GST ledger for tax reporting

### Payment Processing Flow

1. **Billing Service**: Record payment against invoice
   - Update invoice paid amount and balance due
2. **GL Service**: Create accounting entries
   - Debit Cash/Card/UPI accounts
   - Credit Accounts Receivable

### Refund Processing Flow

1. **Billing Service**: Record refund against payment
   - Update payment refund amount and date
   - Update invoice paid amount and balance due
2. **GL Service**: Create accounting entries
   - Debit Accounts Receivable
   - Credit Cash/Card/UPI accounts proportionally

### Void Invoice Flow

1. **Billing Service**: Create void invoice with negative amounts
   - Create negative line items
2. **Inventory Service**: Reverse inventory movements
   - Increase stock levels
   - Record reason as void
3. **GL Service**: Create reversing accounting entries
   - Credit Accounts Receivable
   - Debit Revenue accounts
   - Debit Tax Liability accounts

## 4. Cross-Service Integration Pattern

The implementation follows these integration patterns:

1. **Service Separation**: Each service (billing, inventory, GL) maintains its own domain responsibility
2. **Try-Catch Integration**: Non-critical service calls are wrapped in try-except blocks to prevent cascade failures
3. **Fallback Mechanisms**: Legacy methods are retained for backward compatibility
4. **Consistent Transaction Management**: Session is passed between services to maintain transaction integrity
5. **Centralized Logging**: All services log to a central logger for easier debugging
6. **Audit Trails**: User ID is passed to all service functions for audit purposes

## 5. Future Enhancements

The current implementation provides a solid foundation for cross-service integration. Future enhancements could include:

1. **Event-based Integration**: Move to an event-based system where services communicate through events
2. **Asynchronous Processing**: Make non-critical operations asynchronous for better performance
3. **Circuit Breaker Pattern**: Implement circuit breakers to handle temporary service failures
4. **Service Health Monitoring**: Add health checks for each service
5. **API Gateway**: Implement an API gateway for external integration

## Conclusion

The implemented functionality provides comprehensive integration between the billing, inventory and GL services while maintaining backward compatibility. This ensures proper financial and inventory tracking for all billing operations while maintaining the robustness of the system through appropriate error handling and fallback mechanisms.