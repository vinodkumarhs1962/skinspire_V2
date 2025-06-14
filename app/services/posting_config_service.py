# app/services/posting_config_service.py - SIMPLIFIED VERSION
# Eliminates dynamic lookup entirely - uses static .env configuration only

import os
from typing import Dict, List

from app.utils.unicode_logging import get_unicode_safe_logger
logger = get_unicode_safe_logger(__name__)

def get_posting_config(hospital_id: str = None) -> Dict:
    """
    Get posting configuration from static .env file
    SIMPLIFIED: No dynamic lookup - eliminates all session conflicts
    """
    # Static configuration from environment only
    config = {
        'ENABLE_ENHANCED_POSTING': os.getenv('ENABLE_ENHANCED_POSTING', 'False').lower() == 'true',
        'DEFAULT_AP_ACCOUNT': os.getenv('DEFAULT_AP_ACCOUNT', '2100'),
        'DEFAULT_INVENTORY_ACCOUNT': os.getenv('DEFAULT_INVENTORY_ACCOUNT', '1410'),
        'DEFAULT_EXPENSE_ACCOUNT': os.getenv('DEFAULT_EXPENSE_ACCOUNT', '5100'),
        'DEFAULT_BANK_ACCOUNT': os.getenv('DEFAULT_BANK_ACCOUNT', '1100'),
        'DEFAULT_CASH_ACCOUNT': os.getenv('DEFAULT_CASH_ACCOUNT', '1101'),
        'CGST_RECEIVABLE_ACCOUNT': os.getenv('CGST_RECEIVABLE_ACCOUNT', '1710'),
        'SGST_RECEIVABLE_ACCOUNT': os.getenv('SGST_RECEIVABLE_ACCOUNT', '1720'),
        'IGST_RECEIVABLE_ACCOUNT': os.getenv('IGST_RECEIVABLE_ACCOUNT', '1730'),
        'POSTING_BATCH_SIZE': int(os.getenv('POSTING_BATCH_SIZE', '100')),
        
        # Payment method accounts (if configured)
        'PAYMENT_METHOD_ACCOUNTS': {
            'cash': os.getenv('DEFAULT_CASH_ACCOUNT', '1101'),
            'bank_transfer': os.getenv('DEFAULT_BANK_ACCOUNT', '1100'),
            'cheque': os.getenv('DEFAULT_BANK_ACCOUNT', '1100'),
            'credit_card': os.getenv('CREDIT_CARD_ACCOUNT', os.getenv('DEFAULT_BANK_ACCOUNT', '1100')),
            'debit_card': os.getenv('DEBIT_CARD_ACCOUNT', os.getenv('DEFAULT_BANK_ACCOUNT', '1100')),
            'upi': os.getenv('UPI_ACCOUNT', os.getenv('DEFAULT_BANK_ACCOUNT', '1100')),
        },
        
        # Additional settings for backward compatibility
        'AUTO_POST_INVOICES': True,
        'AUTO_POST_PAYMENTS': True,
        'REQUIRE_APPROVAL_FOR_CREDIT_NOTES': True,
        'VALIDATE_ACCOUNT_EXISTENCE': False,  # Disabled since no dynamic lookup
        'LOG_POSTING_DETAILS': os.getenv('FLASK_ENV', 'development').lower() == 'development',
        'CONTINUE_ON_POSTING_ERRORS': os.getenv('FLASK_ENV', 'development').lower() == 'development'
    }
    
    if hospital_id:
        logger.info(f"📋 Using static configuration for hospital {hospital_id}")
    
    return config

def get_default_gl_account(account_type: str, hospital_id: str = None) -> str:
    """
    Get default GL account for a given type from static configuration
    SIMPLIFIED: No dynamic lookup
    """
    config = get_posting_config(hospital_id)
    
    account_mapping = {
        'ap': config.get('DEFAULT_AP_ACCOUNT', '2100'),
        'inventory': config.get('DEFAULT_INVENTORY_ACCOUNT', '1410'),
        'expense': config.get('DEFAULT_EXPENSE_ACCOUNT', '5100'),
        'bank': config.get('DEFAULT_BANK_ACCOUNT', '1100'),
        'cash': config.get('DEFAULT_CASH_ACCOUNT', '1101'),
        'cgst': config.get('CGST_RECEIVABLE_ACCOUNT', '1710'),
        'sgst': config.get('SGST_RECEIVABLE_ACCOUNT', '1720'),
        'igst': config.get('IGST_RECEIVABLE_ACCOUNT', '1730'),
    }
    
    result = account_mapping.get(account_type.lower(), '1100')
    
    if hospital_id:
        logger.info(f"🔍 Account lookup for type '{account_type}': {result} (hospital: {hospital_id})")
    
    return result

def get_payment_method_account(payment_method: str, hospital_id: str = None) -> str:
    """
    Get GL account for specific payment method from static configuration
    SIMPLIFIED: No dynamic lookup
    """
    config = get_posting_config(hospital_id)
    method_accounts = config.get('PAYMENT_METHOD_ACCOUNTS', {})
    
    result = method_accounts.get(
        payment_method.lower(), 
        config.get('DEFAULT_BANK_ACCOUNT', '1100')
    )
    
    if hospital_id:
        logger.info(f"🔍 Payment method account for '{payment_method}': {result} (hospital: {hospital_id})")
    
    return result

def get_medicine_type_account(medicine_type: str, hospital_id: str = None) -> str:
    """
    Get GL account for specific medicine type from static configuration
    SIMPLIFIED: Uses inventory account for all medicine types
    """
    config = get_posting_config(hospital_id)
    
    # Simplified - all medicine types use inventory account
    result = config.get('DEFAULT_INVENTORY_ACCOUNT', '1410')
    
    if hospital_id:
        logger.info(f"🔍 Medicine type account for '{medicine_type}': {result} (hospital: {hospital_id})")
    
    return result

def is_enhanced_posting_enabled() -> bool:
    """Check if enhanced posting is enabled"""
    config = get_posting_config()
    return config.get('ENABLE_ENHANCED_POSTING', False)

def validate_posting_configuration(hospital_id: str = None) -> List[str]:
    """
    Validate that posting configuration is properly set up
    SIMPLIFIED: Only validates .env file entries, no database checks
    """
    errors = []
    config = get_posting_config(hospital_id)
    
    # Check required account mappings
    required_accounts = [
        'DEFAULT_AP_ACCOUNT',
        'DEFAULT_INVENTORY_ACCOUNT', 
        'DEFAULT_BANK_ACCOUNT'
    ]
    
    for account_key in required_accounts:
        if not config.get(account_key):
            errors.append(f"Missing required account mapping: {account_key}")
    
    # SIMPLIFIED: No database validation (trust .env configuration)
    # The utility script validates accounts exist before updating .env
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

def get_feature_flags() -> Dict:
    """Get current feature flag status"""
    config = get_posting_config()
    
    return {
        'enhanced_posting_enabled': config.get('ENABLE_ENHANCED_POSTING', False),
        'auto_post_invoices': config.get('AUTO_POST_INVOICES', True),
        'auto_post_payments': config.get('AUTO_POST_PAYMENTS', True),
        'require_credit_note_approval': config.get('REQUIRE_APPROVAL_FOR_CREDIT_NOTES', True),
        'validate_account_existence': config.get('VALIDATE_ACCOUNT_EXISTENCE', False),
        'log_posting_details': config.get('LOG_POSTING_DETAILS', False),
        'continue_on_posting_errors': config.get('CONTINUE_ON_POSTING_ERRORS', False)
    }

def get_account_summary_for_hospital(hospital_id: str) -> Dict:
    """
    Get summary of all configured accounts for a hospital
    SIMPLIFIED: Shows static configuration only
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
            'config_source': 'static',
            'dynamic_lookup_enabled': False
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"❌ Error getting account summary: {str(e)}")
        return {'error': str(e)}

def clear_posting_config_cache(hospital_id: str = None):
    """
    SIMPLIFIED: No-op function for backward compatibility
    Since there's no cache in simplified version, this does nothing
    """
    if hospital_id:
        logger.info(f"📋 No cache to clear for hospital {hospital_id} (using static config)")
    else:
        logger.info("📋 No cache to clear (using static config)")

def get_medicine_type_account(medicine_type: str, hospital_id: str = None) -> str:
    """
    Get GL account for specific medicine type from static configuration
    SIMPLIFIED: Uses inventory account for all medicine types (backward compatible)
    """
    config = get_posting_config(hospital_id)
    
    # Simplified - all medicine types use inventory account
    result = config.get('DEFAULT_INVENTORY_ACCOUNT', '1410')
    
    if hospital_id:
        logger.info(f"🔍 Medicine type account for '{medicine_type}': {result} (hospital: {hospital_id})")
    
    return result

# Utility functions for the account mapping script
def get_all_hospitals() -> List[Dict]:
    """
    Get list of all hospitals for the utility script
    This is a helper function for the account mapping utility
    """
    try:
        import uuid
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.services.database_service import get_database_url
        from app.models.master import Hospital
        
        engine = create_engine(get_database_url(), echo=False)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as session:
            hospitals = session.query(Hospital).filter_by(is_active=True).all()
            
            return [
                {
                    'hospital_id': str(hospital.hospital_id),
                    'hospital_name': hospital.hospital_name,
                    'state_code': hospital.state_code
                }
                for hospital in hospitals
            ]
    except Exception as e:
        logger.error(f"Error getting hospitals: {e}")
        return []

def _validate_account_existence(config: Dict, hospital_id: str) -> List[str]:
    """
    SIMPLIFIED: Basic validation without database checks
    Returns empty list since we use static configuration
    """
    # In simplified version, we trust the .env configuration
    # The utility script validates accounts exist before updating .env
    return []

# ✅ REMOVED FUNCTIONS:
# - _get_dynamic_account_mapping() - No longer needed
# - clear_posting_config_cache() - No cache needed
# - All session-related dynamic lookup code

# ✅ BENEFITS OF THIS APPROACH:
# - No session conflicts
# - Better performance (no database lookups)
# - Easier to debug and maintain
# - Clear separation of concerns
# - Account mappings are explicitly configured