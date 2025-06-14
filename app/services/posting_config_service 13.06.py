# app/services/posting_config_service.py
# Enhanced with dynamic account lookup while maintaining backward compatibility
# All existing function names and signatures preserved

import os
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.master import ChartOfAccounts
from app.services.database_service import get_db_session
from app.config import POSTING_CONFIG

from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

# Global cache for dynamic configs
_dynamic_cache = {}
_cache_timeout = 300  # 5 minutes

def get_posting_config(hospital_id: str = None) -> Dict:
    """
    Get posting configuration based on current environment
    FIXED: Enhanced with dynamic account lookup using proper session isolation
    """
    
    # Start with base configuration from app.config
    config = POSTING_CONFIG.copy()
    
    # Apply environment-specific overrides (existing logic)
    env = os.getenv('FLASK_ENV', 'development').lower()
    
    if env == 'development':
        config.update({
            'ENABLE_ENHANCED_POSTING': True,
            'LOG_POSTING_DETAILS': True,
            'CONTINUE_ON_POSTING_ERRORS': True,
        })
    elif env == 'production':
        config.update({
            'ENABLE_ENHANCED_POSTING': config.get('ENABLE_ENHANCED_POSTING', False),
            'VALIDATE_ACCOUNT_EXISTENCE': True,
            'CONTINUE_ON_POSTING_ERRORS': False,
        })
    
    # ✅ ENHANCED: Dynamic account lookup with proper error handling
    if hospital_id:
        try:
            dynamic_config = _get_dynamic_account_mapping(hospital_id)
            if dynamic_config:
                config.update(dynamic_config)
                logger.info(f"✅ Applied dynamic account mapping for hospital {hospital_id}")
            else:
                logger.info(f"📋 No dynamic mappings found for hospital {hospital_id}, using static config")
        except Exception as e:
            logger.warning(f"⚠️ Dynamic account lookup failed for hospital {hospital_id}: {str(e)}")
            logger.info("📋 Using static configuration from .env file")
    
    return config

def _get_dynamic_account_mapping(hospital_id: str) -> Dict:
    """
    FIXED: Get dynamic account mapping using primitive value extraction pattern
    Follows established detached entity guidelines - extracts all needed values within session
    """
    
    cache_key = f"dynamic_accounts_{hospital_id}"
    
    # Check cache first
    if cache_key in _dynamic_cache:
        logger.debug(f"🔄 Using cached dynamic config for hospital {hospital_id}")
        return _dynamic_cache[cache_key]
    
    try:
        # ✅ PATTERN #3: Use get_db_session and extract primitives within session
        with get_db_session(read_only=True) as session:
            logger.debug(f"🔍 Attempting dynamic account lookup for hospital {hospital_id}")
            
            dynamic_config = {}
            
            # ✅ Extract ALL needed data as primitives within session context
            # This prevents any detached entity issues
            
            # 1. GST ACCOUNTS - Extract primitive values immediately
            try:
                gst_accounts = session.query(ChartOfAccounts).filter_by(
                    hospital_id=hospital_id,
                    gst_related=True,
                    is_active=True
                ).all()
                
                # Extract primitive values within session
                for account in gst_accounts:
                    gst_component = account.gst_component  # Extract primitive
                    account_group = account.account_group  # Extract primitive
                    gl_account_no = account.gl_account_no  # Extract primitive
                    
                    if gst_component == 'CGST' and account_group == 'Assets':
                        dynamic_config['CGST_RECEIVABLE_ACCOUNT'] = gl_account_no
                    elif gst_component == 'SGST' and account_group == 'Assets':
                        dynamic_config['SGST_RECEIVABLE_ACCOUNT'] = gl_account_no
                    elif gst_component == 'IGST' and account_group == 'Assets':
                        dynamic_config['IGST_RECEIVABLE_ACCOUNT'] = gl_account_no
                        
            except Exception as e:
                logger.warning(f"GST accounts lookup failed: {e}")
            
            # 2. AP ACCOUNT - Extract primitive immediately
            try:
                ap_account = session.query(ChartOfAccounts).filter(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.account_group == 'Liabilities',
                    ChartOfAccounts.account_name.ilike('%payable%'),
                    ChartOfAccounts.is_active == True
                ).first()
                
                if ap_account:
                    # Extract primitive value within session
                    dynamic_config['DEFAULT_AP_ACCOUNT'] = ap_account.gl_account_no
                    
            except Exception as e:
                logger.warning(f"AP account lookup failed: {e}")
            
            # 3. CASH ACCOUNT - Extract primitive immediately
            try:
                cash_account = session.query(ChartOfAccounts).filter(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.account_group == 'Assets',
                    ChartOfAccounts.account_name.ilike('%cash%'),
                    ChartOfAccounts.is_active == True
                ).first()
                
                if cash_account:
                    # Extract primitive value within session
                    cash_account_no = cash_account.gl_account_no
                    dynamic_config['DEFAULT_CASH_ACCOUNT'] = cash_account_no
                else:
                    cash_account_no = None
                    
            except Exception as e:
                logger.warning(f"Cash account lookup failed: {e}")
                cash_account_no = None
            
            # 4. BANK ACCOUNT - Extract primitive immediately
            try:
                bank_account = session.query(ChartOfAccounts).filter(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.account_group == 'Assets',
                    ChartOfAccounts.account_name.ilike('%bank%'),
                    ChartOfAccounts.is_active == True
                ).first()
                
                if bank_account:
                    # Extract primitive value within session
                    bank_account_no = bank_account.gl_account_no
                    dynamic_config['DEFAULT_BANK_ACCOUNT'] = bank_account_no
                else:
                    bank_account_no = None
                    
            except Exception as e:
                logger.warning(f"Bank account lookup failed: {e}")
                bank_account_no = None
            
            # 5. INVENTORY ACCOUNT - Extract primitive immediately
            try:
                inventory_account = session.query(ChartOfAccounts).filter(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.account_group == 'Assets',
                    ChartOfAccounts.account_name.ilike('%inventory%'),
                    ChartOfAccounts.is_active == True
                ).first()
                
                if inventory_account:
                    # Extract primitive value within session
                    dynamic_config['DEFAULT_INVENTORY_ACCOUNT'] = inventory_account.gl_account_no
                    
            except Exception as e:
                logger.warning(f"Inventory account lookup failed: {e}")
            
            # 6. PAYMENT METHOD ACCOUNTS - Extract all primitives within session
            try:
                payment_methods = {}
                
                # Use extracted primitive values
                if cash_account_no:
                    payment_methods['cash'] = cash_account_no
                if bank_account_no:
                    payment_methods['bank_transfer'] = bank_account_no
                    payment_methods['cheque'] = bank_account_no
                
                # Get card accounts and extract primitives
                card_accounts = session.query(ChartOfAccounts).filter(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.account_group == 'Assets',
                    ChartOfAccounts.account_name.ilike('%card%'),
                    ChartOfAccounts.is_active == True
                ).all()
                
                for account in card_accounts:
                    # Extract primitives within session
                    account_name = account.account_name.lower()
                    account_no = account.gl_account_no
                    
                    if 'credit' in account_name:
                        payment_methods['credit_card'] = account_no
                    elif 'debit' in account_name:
                        payment_methods['debit_card'] = account_no
                
                # Get UPI account and extract primitive
                upi_account = session.query(ChartOfAccounts).filter(
                    ChartOfAccounts.hospital_id == hospital_id,
                    ChartOfAccounts.account_group == 'Assets',
                    ChartOfAccounts.account_name.ilike('%upi%'),
                    ChartOfAccounts.is_active == True
                ).first()
                
                if upi_account:
                    # Extract primitive value within session
                    payment_methods['upi'] = upi_account.gl_account_no
                
                if payment_methods:
                    dynamic_config['PAYMENT_METHOD_ACCOUNTS'] = payment_methods
                    
            except Exception as e:
                logger.warning(f"Payment method accounts lookup failed: {e}")
            
            # ✅ All data extracted as primitives - safe to cache and return
            if dynamic_config:
                _dynamic_cache[cache_key] = dynamic_config
                logger.info(f"✅ Cached dynamic config for hospital {hospital_id}: {len(dynamic_config)} mappings")
            else:
                logger.info(f"📋 No dynamic mappings found for hospital {hospital_id}")
            
            return dynamic_config
            
    except Exception as e:
        logger.error(f"❌ Error in dynamic account lookup for hospital {hospital_id}: {str(e)}")
        logger.warning("⚠️ Falling back to static configuration")
        return {}

def is_enhanced_posting_enabled() -> bool:
    """Check if enhanced posting is enabled - UNCHANGED"""
    config = get_posting_config()
    return config.get('ENABLE_ENHANCED_POSTING', False)

def get_default_gl_account(account_type: str, hospital_id: str = None) -> str:
    """
    Get default GL account for a given type
    ENHANCED with dynamic lookup capability
    """
    config = get_posting_config(hospital_id)  # Now passes hospital_id for dynamic lookup
    
    account_mapping = {
        'ap': config.get('DEFAULT_AP_ACCOUNT', '2001'),
        'inventory': config.get('DEFAULT_INVENTORY_ACCOUNT', '1301'),
        'expense': config.get('DEFAULT_EXPENSE_ACCOUNT', '5001'),
        'bank': config.get('DEFAULT_BANK_ACCOUNT', '1001'),
        'cash': config.get('DEFAULT_CASH_ACCOUNT', '1002'),
        'cgst': config.get('CGST_RECEIVABLE_ACCOUNT', '1501'),
        'sgst': config.get('SGST_RECEIVABLE_ACCOUNT', '1502'),
        'igst': config.get('IGST_RECEIVABLE_ACCOUNT', '1503'),
    }
    
    result = account_mapping.get(account_type.lower(), '1001')
    
    if hospital_id:
        logger.info(f"🔍 Account lookup for type '{account_type}': {result} (hospital: {hospital_id})")
    
    return result

def get_payment_method_account(payment_method: str, hospital_id: str = None) -> str:
    """
    Get GL account for specific payment method
    ENHANCED with dynamic lookup capability
    """
    config = get_posting_config(hospital_id)  # Now passes hospital_id for dynamic lookup
    method_accounts = config.get('PAYMENT_METHOD_ACCOUNTS', {})
    
    result = method_accounts.get(
        payment_method.lower(), 
        config.get('DEFAULT_BANK_ACCOUNT', '1001')
    )
    
    if hospital_id:
        logger.info(f"🔍 Payment method account for '{payment_method}': {result} (hospital: {hospital_id})")
    
    return result

def get_medicine_type_account(medicine_type: str, hospital_id: str = None) -> str:
    """
    Get GL account for specific medicine type
    ENHANCED with dynamic lookup capability
    """
    config = get_posting_config(hospital_id)  # Now passes hospital_id for dynamic lookup
    
    # Default medicine type accounts
    type_accounts = {
        'OTC': config.get('DEFAULT_INVENTORY_ACCOUNT', '1301'),
        'Prescription': '1302',   # Inventory - Prescription Medicines  
        'Product': '1303',        # Inventory - Products
        'Consumable': '1304',     # Inventory - Consumables
        'Misc': '1305',           # Inventory - Miscellaneous
    }
    
    result = type_accounts.get(medicine_type, config.get('DEFAULT_INVENTORY_ACCOUNT', '1301'))
    
    if hospital_id:
        logger.info(f"🔍 Medicine type account for '{medicine_type}': {result} (hospital: {hospital_id})")
    
    return result

def validate_posting_configuration(hospital_id: str = None) -> List[str]:
    """
    Validate that posting configuration is properly set up
    ENHANCED to validate dynamic accounts if hospital_id provided
    Returns list of validation errors
    """
    errors = []
    config = get_posting_config(hospital_id)  # Now uses dynamic config if hospital_id provided
    
    # Check required account mappings
    required_accounts = [
        'DEFAULT_AP_ACCOUNT',
        'DEFAULT_INVENTORY_ACCOUNT', 
        'DEFAULT_BANK_ACCOUNT'
    ]
    
    for account_key in required_accounts:
        if not config.get(account_key):
            errors.append(f"Missing required account mapping: {account_key}")
    
    # ✅ NEW: Validate that accounts actually exist in chart of accounts
    if hospital_id:
        errors.extend(_validate_account_existence(config, hospital_id))
    
    # Validate account format (should be strings)
    for key, value in config.items():
        if key.endswith('_ACCOUNT') and not isinstance(value, str):
            errors.append(f"Account {key} should be a string, got {type(value)}")
    
    # Check batch size is reasonable
    batch_size = config.get('POSTING_BATCH_SIZE', 100)
    if not isinstance(batch_size, int) or batch_size <= 0 or batch_size > 10000:
        errors.append(f"POSTING_BATCH_SIZE should be between 1 and 10000, got {batch_size}")
    
    return errors

def _validate_account_existence(config: Dict, hospital_id: str) -> List[str]:
    """
    NEW: Validate that configured accounts actually exist in chart of accounts
    """
    errors = []
    
    try:
        with get_db_session(read_only=True) as session:
            # Get all account numbers from config
            account_fields = [key for key in config.keys() if key.endswith('_ACCOUNT')]
            
            for field in account_fields:
                account_no = config.get(field)
                if account_no:
                    # Check if account exists
                    account = session.query(ChartOfAccounts).filter_by(
                        hospital_id=hospital_id,
                        gl_account_no=account_no,
                        is_active=True
                    ).first()
                    
                    if not account:
                        errors.append(f"Account {account_no} configured for {field} does not exist in chart of accounts")
            
            # Validate payment method accounts
            payment_methods = config.get('PAYMENT_METHOD_ACCOUNTS', {})
            for method, account_no in payment_methods.items():
                account = session.query(ChartOfAccounts).filter_by(
                    hospital_id=hospital_id,
                    gl_account_no=account_no,
                    is_active=True
                ).first()
                
                if not account:
                    errors.append(f"Payment method account {account_no} for {method} does not exist in chart of accounts")
                    
    except Exception as e:
        errors.append(f"Error validating account existence: {str(e)}")
    
    return errors

def get_feature_flags() -> Dict:
    """Get current feature flag status - UNCHANGED"""
    config = get_posting_config()
    
    return {
        'enhanced_posting_enabled': config.get('ENABLE_ENHANCED_POSTING', False),
        'auto_post_invoices': config.get('AUTO_POST_INVOICES', True),
        'auto_post_payments': config.get('AUTO_POST_PAYMENTS', True),
        'require_credit_note_approval': config.get('REQUIRE_APPROVAL_FOR_CREDIT_NOTES', True),
        'validate_accounts': config.get('VALIDATE_ACCOUNT_EXISTENCE', True),
    }

def clear_posting_config_cache(hospital_id: str = None):
    """
    NEW: Clear posting configuration cache
    Useful when chart of accounts is updated
    """
    global _dynamic_cache
    
    if hospital_id:
        cache_key = f"dynamic_accounts_{hospital_id}"
        _dynamic_cache.pop(cache_key, None)
        logger.info(f"✅ Cleared posting config cache for hospital {hospital_id}")
    else:
        _dynamic_cache.clear()
        logger.info("✅ Cleared all posting config cache")

def get_account_summary_for_hospital(hospital_id: str) -> Dict:
    """
    NEW: Get summary of all configured accounts for a hospital
    Useful for debugging and verification
    """
    try:
        config = get_posting_config(hospital_id)
        
        summary = {
            'hospital_id': hospital_id,
            'core_accounts': {
                'ap_account': config.get('DEFAULT_AP_ACCOUNT'),
                'bank_account': config.get('DEFAULT_BANK_ACCOUNT'),
                'cash_account': config.get('DEFAULT_CASH_ACCOUNT'),
                'inventory_account': config.get('DEFAULT_INVENTORY_ACCOUNT'),
            },
            'gst_accounts': {
                'cgst_receivable': config.get('CGST_RECEIVABLE_ACCOUNT'),
                'sgst_receivable': config.get('SGST_RECEIVABLE_ACCOUNT'),
                'igst_receivable': config.get('IGST_RECEIVABLE_ACCOUNT'),
            },
            'payment_methods': config.get('PAYMENT_METHOD_ACCOUNTS', {}),
            'config_source': 'dynamic' if hospital_id in _dynamic_cache else 'static'
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error getting account summary: {str(e)}")
        return {'error': str(e)}

# ✅ BACKWARD COMPATIBILITY: All existing function signatures preserved
# ✅ ENHANCEMENT: Dynamic lookup when hospital_id is provided  
# ✅ FALLBACK: Static config when dynamic lookup fails
# ✅ CACHING: Performance optimization for repeated calls
# ✅ LOGGING: Full visibility into account resolution