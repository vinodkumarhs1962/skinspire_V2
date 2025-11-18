"""
Campaign Hook Service - Plugin Architecture for Hospital-Specific Promotional Campaigns

This service provides a clean plugin system that allows hospitals to implement
custom campaign logic without modifying core code.

Supports multiple hook types:
- Python modules: Call Python functions directly
- API endpoints: HTTP calls to external services
- SQL functions: PostgreSQL stored procedures

Author: Claude Code
Date: 2025-11-17
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import importlib
import requests
import json

from app.models.config import CampaignHookConfig

logger = logging.getLogger(__name__)


class CampaignHookResult:
    """Result of applying a campaign hook"""

    def __init__(self):
        self.hook_applied = False
        self.hook_name: Optional[str] = None
        self.hook_id: Optional[str] = None
        self.original_price: Optional[Decimal] = None
        self.adjusted_price: Optional[Decimal] = None
        self.discount_amount: Optional[Decimal] = None
        self.discount_percentage: Optional[Decimal] = None
        self.campaign_message: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.error: Optional[str] = None

    @property
    def has_discount(self) -> bool:
        """Check if any discount was applied"""
        return self.discount_amount is not None and self.discount_amount > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'hook_applied': self.hook_applied,
            'hook_name': self.hook_name,
            'hook_id': str(self.hook_id) if self.hook_id else None,
            'original_price': float(self.original_price) if self.original_price else None,
            'adjusted_price': float(self.adjusted_price) if self.adjusted_price else None,
            'discount_amount': float(self.discount_amount) if self.discount_amount else None,
            'discount_percentage': float(self.discount_percentage) if self.discount_percentage else None,
            'campaign_message': self.campaign_message,
            'metadata': self.metadata,
            'error': self.error
        }


def apply_campaign_hooks(
    session: Session,
    hospital_id: str,
    entity_type: str,  # 'medicine', 'service', 'package'
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    context: Optional[Dict[str, Any]] = None
) -> CampaignHookResult:
    """
    Apply campaign hooks to get promotional pricing.

    This is the main entry point for campaign pricing. It:
    1. Finds active hooks for the hospital/entity type
    2. Executes hooks in priority order
    3. Returns the first hook that applies a discount

    Args:
        session: Database session
        hospital_id: Hospital UUID
        entity_type: 'medicine', 'service', 'package'
        entity_id: Entity UUID
        base_price: Base price before campaign
        applicable_date: Date for which to apply campaign
        context: Additional context (patient_id, quantity, etc.)

    Returns:
        CampaignHookResult with pricing information
    """
    result = CampaignHookResult()
    result.original_price = base_price

    try:
        # Find active hooks for this hospital and entity type
        hooks = _get_active_hooks(
            session=session,
            hospital_id=hospital_id,
            entity_type=entity_type,
            applicable_date=applicable_date
        )

        if not hooks:
            logger.debug(f"No active campaign hooks found for hospital {hospital_id}, entity_type {entity_type}")
            return result

        logger.info(f"Found {len(hooks)} active campaign hook(s) for {entity_type}")

        # Execute hooks in priority order (lower priority number = higher priority)
        for hook in sorted(hooks, key=lambda h: h.priority):
            try:
                hook_result = _execute_hook(
                    session=session,
                    hook=hook,
                    entity_id=entity_id,
                    base_price=base_price,
                    applicable_date=applicable_date,
                    context=context or {}
                )

                # If hook applied a discount, use it and stop
                if hook_result and hook_result.has_discount:
                    logger.info(f"Campaign hook '{hook.hook_name}' applied: "
                              f"{base_price} → {hook_result.adjusted_price} "
                              f"(discount: {hook_result.discount_amount})")
                    return hook_result

            except Exception as e:
                logger.error(f"Error executing campaign hook '{hook.hook_name}': {str(e)}", exc_info=True)
                # Continue to next hook on error
                continue

        # No hooks applied
        logger.debug("No campaign hooks applied discount")
        return result

    except Exception as e:
        logger.error(f"Error in apply_campaign_hooks: {str(e)}", exc_info=True)
        result.error = str(e)
        return result


def _get_active_hooks(
    session: Session,
    hospital_id: str,
    entity_type: str,
    applicable_date: date
) -> List[CampaignHookConfig]:
    """
    Get active campaign hooks for hospital and entity type.

    Returns hooks that are:
    - Active (is_active = true)
    - Not deleted (is_deleted = false)
    - Applicable to entity type
    - Within effective period
    """
    # Build entity type filter
    if entity_type == 'medicine':
        entity_filter = CampaignHookConfig.applies_to_medicines == True
    elif entity_type == 'service':
        entity_filter = CampaignHookConfig.applies_to_services == True
    elif entity_type == 'package':
        entity_filter = CampaignHookConfig.applies_to_packages == True
    else:
        return []

    # Query active hooks
    hooks = session.query(CampaignHookConfig).filter(
        and_(
            CampaignHookConfig.hospital_id == hospital_id,
            CampaignHookConfig.is_active == True,
            CampaignHookConfig.is_deleted == False,
            entity_filter,
            or_(
                CampaignHookConfig.effective_from == None,
                CampaignHookConfig.effective_from <= applicable_date
            ),
            or_(
                CampaignHookConfig.effective_to == None,
                CampaignHookConfig.effective_to >= applicable_date
            )
        )
    ).all()

    return hooks


def _execute_hook(
    session: Session,
    hook: CampaignHookConfig,
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    context: Dict[str, Any]
) -> Optional[CampaignHookResult]:
    """
    Execute a campaign hook based on its type.

    Dispatches to appropriate executor:
    - python_module: Call Python function
    - api_endpoint: HTTP call
    - sql_function: Database stored procedure
    """
    if hook.hook_type == 'python_module':
        return _execute_python_hook(hook, entity_id, base_price, applicable_date, context)
    elif hook.hook_type == 'api_endpoint':
        return _execute_api_hook(hook, entity_id, base_price, applicable_date, context)
    elif hook.hook_type == 'sql_function':
        return _execute_sql_hook(session, hook, entity_id, base_price, applicable_date, context)
    else:
        logger.warning(f"Unknown hook type: {hook.hook_type}")
        return None


def _execute_python_hook(
    hook: CampaignHookConfig,
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    context: Dict[str, Any]
) -> Optional[CampaignHookResult]:
    """
    Execute a Python module hook.

    Expected hook function signature:
        def hook_function(
            entity_id: str,
            base_price: Decimal,
            applicable_date: date,
            hook_config: Dict,
            context: Dict
        ) -> Optional[Dict]:

    Expected return value (if discount applies):
        {
            'adjusted_price': Decimal,
            'discount_amount': Decimal,
            'discount_percentage': Decimal (optional),
            'message': str (optional),
            'metadata': Dict (optional)
        }

    Returns None if no discount applies.
    """
    try:
        # Import the module
        module = importlib.import_module(hook.hook_module_path)

        # Get the function
        hook_function = getattr(module, hook.hook_function_name)

        # Call the hook function
        hook_result = hook_function(
            entity_id=entity_id,
            base_price=base_price,
            applicable_date=applicable_date,
            hook_config=hook.hook_config or {},
            context=context
        )

        # If no discount, return None
        if not hook_result:
            return None

        # Build result
        result = CampaignHookResult()
        result.hook_applied = True
        result.hook_name = hook.hook_name
        result.hook_id = str(hook.hook_id)
        result.original_price = base_price
        result.adjusted_price = Decimal(str(hook_result.get('adjusted_price', base_price)))
        result.discount_amount = Decimal(str(hook_result.get('discount_amount', 0)))
        result.discount_percentage = Decimal(str(hook_result.get('discount_percentage', 0))) if hook_result.get('discount_percentage') else None
        result.campaign_message = hook_result.get('message')
        result.metadata = hook_result.get('metadata', {})

        return result

    except ImportError as e:
        logger.error(f"Failed to import hook module '{hook.hook_module_path}': {str(e)}")
        return None
    except AttributeError as e:
        logger.error(f"Hook function '{hook.hook_function_name}' not found in module '{hook.hook_module_path}': {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error executing Python hook '{hook.hook_name}': {str(e)}", exc_info=True)
        return None


def _execute_api_hook(
    hook: CampaignHookConfig,
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    context: Dict[str, Any]
) -> Optional[CampaignHookResult]:
    """
    Execute an API endpoint hook.

    Sends POST request to hook_endpoint with:
        {
            'entity_id': str,
            'base_price': float,
            'applicable_date': str (ISO format),
            'hook_config': Dict,
            'context': Dict
        }

    Expected response (if discount applies):
        {
            'adjusted_price': float,
            'discount_amount': float,
            'discount_percentage': float (optional),
            'message': str (optional),
            'metadata': Dict (optional)
        }

    Returns None if no discount applies or on error.
    """
    try:
        # Prepare request payload
        payload = {
            'entity_id': entity_id,
            'base_price': float(base_price),
            'applicable_date': applicable_date.isoformat(),
            'hook_config': hook.hook_config or {},
            'context': context
        }

        # Prepare headers
        headers = {'Content-Type': 'application/json'}

        # Add authentication if configured
        if hook.api_auth_type == 'bearer' and hook.api_auth_credentials:
            headers['Authorization'] = f"Bearer {hook.api_auth_credentials}"
        elif hook.api_auth_type == 'api_key' and hook.api_auth_credentials:
            headers['X-API-Key'] = hook.api_auth_credentials

        # Make HTTP request
        timeout_seconds = (hook.timeout_ms or 5000) / 1000
        response = requests.post(
            hook.hook_endpoint,
            json=payload,
            headers=headers,
            timeout=timeout_seconds
        )

        # Check response
        if response.status_code != 200:
            logger.warning(f"API hook '{hook.hook_name}' returned status {response.status_code}")
            return None

        hook_result = response.json()

        # If no discount, return None
        if not hook_result or not hook_result.get('adjusted_price'):
            return None

        # Build result
        result = CampaignHookResult()
        result.hook_applied = True
        result.hook_name = hook.hook_name
        result.hook_id = str(hook.hook_id)
        result.original_price = base_price
        result.adjusted_price = Decimal(str(hook_result['adjusted_price']))
        result.discount_amount = Decimal(str(hook_result.get('discount_amount', 0)))
        result.discount_percentage = Decimal(str(hook_result.get('discount_percentage', 0))) if hook_result.get('discount_percentage') else None
        result.campaign_message = hook_result.get('message')
        result.metadata = hook_result.get('metadata', {})

        return result

    except requests.Timeout:
        logger.warning(f"API hook '{hook.hook_name}' timed out after {timeout_seconds}s")
        return None
    except requests.RequestException as e:
        logger.error(f"API hook '{hook.hook_name}' request failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error executing API hook '{hook.hook_name}': {str(e)}", exc_info=True)
        return None


def _execute_sql_hook(
    session: Session,
    hook: CampaignHookConfig,
    entity_id: str,
    base_price: Decimal,
    applicable_date: date,
    context: Dict[str, Any]
) -> Optional[CampaignHookResult]:
    """
    Execute a SQL function hook.

    Expected SQL function signature:
        CREATE FUNCTION hook_function(
            entity_id UUID,
            base_price NUMERIC,
            applicable_date DATE,
            hook_config JSONB,
            context JSONB
        ) RETURNS JSONB

    Expected return value (if discount applies):
        {
            "adjusted_price": 450.00,
            "discount_amount": 50.00,
            "discount_percentage": 10.00,
            "message": "Campaign applied",
            "metadata": {}
        }

    Returns NULL if no discount applies.
    """
    try:
        # Build SQL query
        sql = f"SELECT {hook.hook_sql_function}(:entity_id, :base_price, :applicable_date, :hook_config::jsonb, :context::jsonb) as result"

        # Execute query
        result = session.execute(
            sql,
            {
                'entity_id': entity_id,
                'base_price': float(base_price),
                'applicable_date': applicable_date,
                'hook_config': json.dumps(hook.hook_config or {}),
                'context': json.dumps(context)
            }
        ).fetchone()

        # If no result or NULL, no discount
        if not result or not result.result:
            return None

        hook_result = result.result

        # Build result
        campaign_result = CampaignHookResult()
        campaign_result.hook_applied = True
        campaign_result.hook_name = hook.hook_name
        campaign_result.hook_id = str(hook.hook_id)
        campaign_result.original_price = base_price
        campaign_result.adjusted_price = Decimal(str(hook_result['adjusted_price']))
        campaign_result.discount_amount = Decimal(str(hook_result.get('discount_amount', 0)))
        campaign_result.discount_percentage = Decimal(str(hook_result.get('discount_percentage', 0))) if hook_result.get('discount_percentage') else None
        campaign_result.campaign_message = hook_result.get('message')
        campaign_result.metadata = hook_result.get('metadata', {})

        return campaign_result

    except Exception as e:
        logger.error(f"Error executing SQL hook '{hook.hook_name}': {str(e)}", exc_info=True)
        return None


# ============================================================================
# Hook Management Functions
# ============================================================================

def get_active_hooks_for_hospital(
    session: Session,
    hospital_id: str
) -> List[CampaignHookConfig]:
    """Get all active campaign hooks for a hospital"""
    return session.query(CampaignHookConfig).filter(
        CampaignHookConfig.hospital_id == hospital_id,
        CampaignHookConfig.is_active == True,
        CampaignHookConfig.is_deleted == False
    ).order_by(CampaignHookConfig.priority).all()


def create_campaign_hook(
    session: Session,
    hospital_id: str,
    hook_name: str,
    hook_type: str,
    created_by: str,
    **kwargs
) -> CampaignHookConfig:
    """
    Create a new campaign hook.

    Example:
        hook = create_campaign_hook(
            session=session,
            hospital_id='hospital-uuid',
            hook_name='Diwali 2025',
            hook_type='python_module',
            hook_module_path='app.campaigns.diwali',
            hook_function_name='apply_discount',
            applies_to_medicines=True,
            effective_from=date(2025, 11, 1),
            effective_to=date(2025, 11, 15),
            hook_config={'discount_percentage': 20},
            created_by='admin'
        )
    """
    hook = CampaignHookConfig(
        hospital_id=hospital_id,
        hook_name=hook_name,
        hook_type=hook_type,
        created_by=created_by,
        **kwargs
    )

    session.add(hook)
    session.flush()

    logger.info(f"Created campaign hook: {hook.hook_name} (ID: {hook.hook_id})")

    return hook


def deactivate_campaign_hook(
    session: Session,
    hook_id: str,
    deactivated_by: str
) -> bool:
    """Deactivate a campaign hook"""
    hook = session.query(CampaignHookConfig).filter_by(hook_id=hook_id).first()

    if not hook:
        return False

    hook.is_active = False
    hook.updated_by = deactivated_by
    session.flush()

    logger.info(f"Deactivated campaign hook: {hook.hook_name}")

    return True


def delete_campaign_hook(
    session: Session,
    hook_id: str,
    deleted_by: str
) -> bool:
    """Soft delete a campaign hook"""
    hook = session.query(CampaignHookConfig).filter_by(hook_id=hook_id).first()

    if not hook:
        return False

    hook.is_deleted = True
    hook.deleted_at = datetime.now()
    hook.deleted_by = deleted_by
    session.flush()

    logger.info(f"Deleted campaign hook: {hook.hook_name}")

    return True
