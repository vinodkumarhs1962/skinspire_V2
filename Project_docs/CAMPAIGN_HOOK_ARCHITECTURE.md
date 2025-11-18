# Campaign Hook Architecture - Plugin Design

**Date**: 2025-11-17
**Version**: 1.0
**Status**: Design Phase - Future Implementation
**Priority**: LOW (After GST/MRP versioning)

---

## Executive Summary

This document outlines a **plugin-based architecture** for promotional campaigns that keeps campaign logic OUT of core pricing. Hospitals can implement their own campaign rules via API hooks without modifying core code.

---

## Design Philosophy

### Core Principles

1. **Separation of Concerns**: Core pricing handles only base pricing and GST
2. **Hospital-Specific Logic**: Each hospital can have unique campaign rules
3. **Plugin Architecture**: Campaign logic injected via hooks, not hardcoded
4. **Optional Feature**: System works perfectly without campaigns
5. **Zero Core Impact**: Adding/removing campaigns doesn't affect core pricing

---

## Architecture

### Component Layers

```
┌─────────────────────────────────────────────────────────┐
│  Invoice Creation (billing_service.py)                  │
│  - Gets base price from entity_pricing_tax_config       │
│  - Calls campaign hook IF configured                    │
│  - Uses result or falls back to base price              │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Campaign Hook Interface (Optional)                      │
│  - Hospital-specific campaign logic                      │
│  - External service or Python module                     │
│  - Returns discount amount or modified price             │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Hospital Campaign Engine (Hospital Implements)          │
│  - Custom rules (festivals, loyalty, volume, etc.)      │
│  - Custom database tables (if needed)                   │
│  - Custom business logic                                │
└─────────────────────────────────────────────────────────┘
```

---

## Hook Interface Definition

### Configuration Table

```sql
CREATE TABLE campaign_hook_config (
    hook_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Hook Type
    hook_type VARCHAR(50) NOT NULL,  -- 'api_endpoint', 'python_module', 'disabled'

    -- API Endpoint Configuration
    api_endpoint_url VARCHAR(500),
    api_auth_token TEXT,
    api_timeout_ms INTEGER DEFAULT 3000,

    -- Python Module Configuration
    python_module_path VARCHAR(200),  -- e.g., 'custom.skinspire_campaigns'
    python_function_name VARCHAR(100), -- e.g., 'calculate_discount'

    -- Fallback Behavior
    on_error_action VARCHAR(50) DEFAULT 'use_base_price',  -- 'use_base_price', 'fail_invoice'

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### API Contract

**Request** (from core to campaign hook):
```json
{
  "hospital_id": "uuid",
  "entity_type": "medicine",
  "entity_id": "uuid",
  "entity_name": "XYZ Cream",
  "base_price": 550.00,
  "quantity": 2,
  "patient_id": "uuid",
  "patient_info": {
    "previous_visit_count": 5,
    "total_spent": 25000,
    "membership_tier": "gold"
  },
  "invoice_date": "2025-07-15T10:30:00Z",
  "invoice_total": 1200.00,
  "context": {
    "branch_id": "uuid",
    "staff_id": "uuid"
  }
}
```

**Response** (from campaign hook to core):
```json
{
  "apply_discount": true,
  "discount_type": "percentage",
  "discount_value": 20.0,
  "discount_amount": 110.00,
  "final_price": 440.00,
  "campaign_reference": "DIWALI2025",
  "campaign_description": "Diwali Festival Offer - 20% off",
  "metadata": {
    "campaign_id": "xyz",
    "usage_count": 1
  }
}
```

**No Discount Response**:
```json
{
  "apply_discount": false,
  "final_price": 550.00
}
```

**Error Response**:
```json
{
  "error": true,
  "error_message": "Campaign service temporarily unavailable",
  "fallback_to_base_price": true
}
```

---

## Core Integration

### File: app/services/pricing_tax_service.py (Addition)

```python
def get_final_pricing_with_campaigns(
    session: Session,
    hospital_id: str,
    entity_type: str,
    entity_id: str,
    quantity: Decimal,
    applicable_date: date,
    patient_id: Optional[str] = None,
    invoice_total: Optional[Decimal] = None,
    **context
) -> Dict:
    """
    Get final pricing with optional campaign discounts applied.

    Flow:
    1. Get base pricing from entity_pricing_tax_config
    2. Check if campaign hook is configured
    3. If configured, call hook and apply discount
    4. If not configured or error, use base price

    Returns:
        Dict with pricing, tax, and discount information
    """

    # Step 1: Get base pricing and GST (ALWAYS)
    base_pricing_tax = get_applicable_pricing_and_tax(
        session, hospital_id, entity_type, entity_id, applicable_date
    )

    base_price = base_pricing_tax.get('applicable_price', Decimal('0'))

    # Step 2: Check for campaign hook
    hook_config = _get_campaign_hook_config(session, hospital_id)

    if not hook_config or not hook_config.get('is_active'):
        # No campaign hook configured - use base price
        logger.info(f"No campaign hook configured for hospital {hospital_id}. Using base price.")
        return {
            **base_pricing_tax,
            'base_price': base_price,
            'discount_amount': Decimal('0'),
            'final_price': base_price,
            'campaign_applied': False
        }

    # Step 3: Call campaign hook
    try:
        campaign_result = _call_campaign_hook(
            hook_config=hook_config,
            hospital_id=hospital_id,
            entity_type=entity_type,
            entity_id=entity_id,
            base_price=base_price,
            quantity=quantity,
            patient_id=patient_id,
            invoice_total=invoice_total,
            invoice_date=applicable_date,
            **context
        )

        if campaign_result.get('apply_discount'):
            logger.info(f"Campaign discount applied: {campaign_result.get('campaign_reference')} - ₹{campaign_result.get('discount_amount')}")
            return {
                **base_pricing_tax,
                'base_price': base_price,
                'discount_amount': campaign_result.get('discount_amount', Decimal('0')),
                'final_price': campaign_result.get('final_price', base_price),
                'campaign_applied': True,
                'campaign_reference': campaign_result.get('campaign_reference'),
                'campaign_description': campaign_result.get('campaign_description'),
                'campaign_metadata': campaign_result.get('metadata', {})
            }
        else:
            # Hook returned no discount
            return {
                **base_pricing_tax,
                'base_price': base_price,
                'discount_amount': Decimal('0'),
                'final_price': base_price,
                'campaign_applied': False
            }

    except Exception as e:
        logger.error(f"Campaign hook error: {str(e)}", exc_info=True)

        # Fallback based on configuration
        if hook_config.get('on_error_action') == 'fail_invoice':
            raise ValueError(f"Campaign service error: {str(e)}")
        else:
            # Default: use base price
            logger.warning(f"Campaign hook failed. Falling back to base price.")
            return {
                **base_pricing_tax,
                'base_price': base_price,
                'discount_amount': Decimal('0'),
                'final_price': base_price,
                'campaign_applied': False,
                'campaign_error': str(e)
            }


def _get_campaign_hook_config(session: Session, hospital_id: str) -> Optional[Dict]:
    """Get campaign hook configuration for hospital"""
    from app.models.config import CampaignHookConfig

    config = session.query(CampaignHookConfig).filter_by(
        hospital_id=hospital_id,
        is_active=True
    ).first()

    if not config:
        return None

    return {
        'hook_type': config.hook_type,
        'api_endpoint_url': config.api_endpoint_url,
        'api_auth_token': config.api_auth_token,
        'api_timeout_ms': config.api_timeout_ms or 3000,
        'python_module_path': config.python_module_path,
        'python_function_name': config.python_function_name,
        'on_error_action': config.on_error_action or 'use_base_price',
        'is_active': config.is_active
    }


def _call_campaign_hook(
    hook_config: Dict,
    hospital_id: str,
    entity_type: str,
    entity_id: str,
    base_price: Decimal,
    quantity: Decimal,
    patient_id: Optional[str],
    invoice_total: Optional[Decimal],
    invoice_date: date,
    **context
) -> Dict:
    """
    Call the campaign hook based on configuration.
    Supports API endpoint or Python module.
    """

    if hook_config['hook_type'] == 'api_endpoint':
        return _call_api_campaign_hook(hook_config, locals())

    elif hook_config['hook_type'] == 'python_module':
        return _call_python_campaign_hook(hook_config, locals())

    else:
        raise ValueError(f"Unknown hook_type: {hook_config['hook_type']}")


def _call_api_campaign_hook(hook_config: Dict, params: Dict) -> Dict:
    """Call external API for campaign calculation"""
    import requests
    import json

    url = hook_config['api_endpoint_url']
    timeout_ms = hook_config['api_timeout_ms']

    # Build request payload
    payload = {
        'hospital_id': str(params['hospital_id']),
        'entity_type': params['entity_type'],
        'entity_id': str(params['entity_id']),
        'base_price': float(params['base_price']),
        'quantity': float(params['quantity']),
        'patient_id': str(params['patient_id']) if params['patient_id'] else None,
        'invoice_date': params['invoice_date'].isoformat(),
        'invoice_total': float(params['invoice_total']) if params['invoice_total'] else None,
        'context': params.get('context', {})
    }

    # Add auth header if configured
    headers = {'Content-Type': 'application/json'}
    if hook_config.get('api_auth_token'):
        headers['Authorization'] = f"Bearer {hook_config['api_auth_token']}"

    # Call API
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=timeout_ms / 1000.0
    )

    response.raise_for_status()

    return response.json()


def _call_python_campaign_hook(hook_config: Dict, params: Dict) -> Dict:
    """Call Python module function for campaign calculation"""
    import importlib

    module_path = hook_config['python_module_path']
    function_name = hook_config['python_function_name']

    # Dynamically import module
    module = importlib.import_module(module_path)
    campaign_function = getattr(module, function_name)

    # Call function
    result = campaign_function(
        hospital_id=params['hospital_id'],
        entity_type=params['entity_type'],
        entity_id=params['entity_id'],
        base_price=params['base_price'],
        quantity=params['quantity'],
        patient_id=params['patient_id'],
        invoice_total=params['invoice_total'],
        invoice_date=params['invoice_date'],
        **params.get('context', {})
    )

    return result
```

---

## Hospital Implementation Examples

### Example 1: External API Service

**Hospital "A" Configuration**:
```sql
INSERT INTO campaign_hook_config (hospital_id, hook_type, api_endpoint_url, api_auth_token)
VALUES (
    'hospital-uuid',
    'api_endpoint',
    'https://campaigns.hospitala.com/api/v1/calculate-discount',
    'secret-token-abc123'
);
```

**Hospital "A" implements their own service** that receives requests and returns discounts based on their custom logic.

### Example 2: Python Module Plugin

**Hospital "B" Configuration**:
```sql
INSERT INTO campaign_hook_config (hospital_id, hook_type, python_module_path, python_function_name)
VALUES (
    'hospital-uuid',
    'python_module',
    'custom.hospitalb_campaigns',
    'calculate_discount'
);
```

**Hospital "B" creates Python module**:
```python
# custom/hospitalb_campaigns.py

def calculate_discount(
    hospital_id,
    entity_type,
    entity_id,
    base_price,
    quantity,
    patient_id,
    invoice_total,
    invoice_date,
    **context
):
    """
    Hospital B's custom campaign logic
    """
    from decimal import Decimal
    from datetime import datetime

    # Custom logic: Diwali discount
    if invoice_date.month == 10 and invoice_date.day >= 20:
        return {
            'apply_discount': True,
            'discount_type': 'percentage',
            'discount_value': 25.0,
            'discount_amount': float(base_price * Decimal('0.25')),
            'final_price': float(base_price * Decimal('0.75')),
            'campaign_reference': 'DIWALI2025',
            'campaign_description': 'Diwali Festival - 25% off'
        }

    # Custom logic: Volume discount
    if quantity >= 10:
        return {
            'apply_discount': True,
            'discount_type': 'percentage',
            'discount_value': 15.0,
            'discount_amount': float(base_price * Decimal('0.15')),
            'final_price': float(base_price * Decimal('0.85')),
            'campaign_reference': 'BULK15',
            'campaign_description': 'Bulk Purchase - 15% off'
        }

    # No discount
    return {
        'apply_discount': False,
        'final_price': float(base_price)
    }
```

### Example 3: No Campaigns (Default)

**Hospital "C" Configuration**: No record in `campaign_hook_config`

**Behavior**: System uses base price from `entity_pricing_tax_config`. No discounts applied.

---

## Integration in Invoice Creation

### File: app/services/billing_service.py

```python
from app.services.pricing_tax_service import get_final_pricing_with_campaigns

# Clean, simple integration
pricing_info = get_final_pricing_with_campaigns(
    session=session,
    hospital_id=hospital_id,
    entity_type='medicine',
    entity_id=medicine_id,
    quantity=quantity,
    applicable_date=invoice_date.date(),
    patient_id=patient_id,
    invoice_total=estimated_invoice_total
)

# Use pricing_info
unit_price = pricing_info['final_price']
gst_rate = pricing_info['gst_rate']
discount_amount = pricing_info['discount_amount']
campaign_ref = pricing_info.get('campaign_reference', '')

# Log campaign if applied
if pricing_info.get('campaign_applied'):
    logger.info(f"Campaign applied: {campaign_ref} - Discount: ₹{discount_amount}")
```

**That's it!** No complex campaign logic in core billing service.

---

## Benefits

### Clean Architecture ✅
- Core remains simple and maintainable
- Campaign complexity isolated in hospital-specific code
- Easy to add/remove campaigns without core changes

### Hospital Flexibility ✅
- Each hospital can implement unique rules
- Can use external service or Python module
- Full control over campaign logic

### Zero Core Impact ✅
- System works perfectly without campaigns
- Adding campaigns doesn't modify core code
- Removing campaigns is just configuration change

### Scalability ✅
- Campaign service can scale independently
- Can use separate database for campaign data
- No performance impact on core pricing

---

## Implementation Priority

**Phase 1 (NOW)**:
- ✅ Entity pricing and GST versioning (mandatory for compliance)
- ❌ Campaign hooks (not needed yet)

**Phase 2 (FUTURE - When hospitals request campaigns)**:
- Create `campaign_hook_config` table
- Add hook calling logic to `pricing_tax_service.py`
- Document API contract for hospitals
- Provide sample Python module template

**Phase 3 (OPTIONAL - Hospital-specific)**:
- Each hospital implements their own campaign logic
- Either as external API or Python module
- Hospital maintains their campaign code

---

## Summary

| Aspect | Design Decision |
|--------|----------------|
| **Core Complexity** | Minimal - just calls hook if configured |
| **Hospital Flexibility** | Maximum - full control over campaign logic |
| **Maintenance** | Easy - hospital maintains their own campaigns |
| **Performance** | Isolated - campaign service scaled independently |
| **Implementation Priority** | LOW - do after GST/MRP versioning |

---

**Status**: ✅ **ARCHITECTURE DEFINED - Future Implementation**

*Designed by: Claude Code*
*Date: 2025-11-17*
*Priority: LOW (After core pricing/GST versioning)*
