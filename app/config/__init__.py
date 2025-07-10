import os
from dotenv import load_dotenv

load_dotenv()  # Make sure you've loaded the environment variables

EMAIL_CONFIG = {
    'SMTP_HOST': os.getenv('SMTP_HOST', 'smtp.example.com'),
    'SMTP_PORT': int(os.getenv('SMTP_PORT', 587)),
    'SMTP_USER': os.getenv('SMTP_USER', ''),
    'SMTP_PASS': os.getenv('SMTP_PASS', ''),
    'SMTP_FROM': os.getenv('SMTP_FROM', 'no-reply@example.com')
}

WHATSAPP_CONFIG = {
    'API_KEY': os.getenv('WHATSAPP_API_KEY', ''),
    'API_URL': os.getenv('WHATSAPP_API_URL', 'https://api.whatsapp.com/send')
}

# OPTIONAL: Only add if you need to change default behavior
DEFAULT_BRANCH_BEHAVIOR = os.environ.get('DEFAULT_BRANCH_BEHAVIOR', 'user_assigned')
SINGLE_BRANCH_AUTO_ASSIGN = os.environ.get('SINGLE_BRANCH_AUTO_ASSIGN', 'true')

# Payment System Configuration
PAYMENT_CONFIG = {
    'APPROVAL_THRESHOLD_L1': float(os.getenv('PAYMENT_APPROVAL_THRESHOLD_L1', '50000.00')),
    'APPROVAL_THRESHOLD_L2': float(os.getenv('PAYMENT_APPROVAL_THRESHOLD_L2', '200000.00')),
    'AUTO_APPROVE_LIMIT': float(os.getenv('PAYMENT_AUTO_APPROVE_LIMIT', '5000.00')),
    'DOCUMENT_STORAGE_PATH': os.getenv('PAYMENT_DOCUMENT_STORAGE_PATH', '/tmp/payment_documents'),
    'MAX_FILE_SIZE': int(os.getenv('PAYMENT_MAX_FILE_SIZE', '10485760')),  # 10MB
    'ALLOWED_FILE_TYPES': os.getenv('PAYMENT_ALLOWED_FILE_TYPES', 'pdf,jpg,jpeg,png').split(','),
    'REQUIRE_DOCUMENTS_ABOVE': float(os.getenv('PAYMENT_REQUIRE_DOCUMENTS_ABOVE', '10000.00'))
}

# Document Management Configuration  
DOCUMENT_CONFIG = {
    'STORAGE_TYPE': os.getenv('DOCUMENT_STORAGE_TYPE', 'filesystem'),  # filesystem, cloud, dms
    'ENCRYPTION_ENABLED': os.getenv('DOCUMENT_ENCRYPTION_ENABLED', 'false').lower() == 'true',
    'RETENTION_YEARS': int(os.getenv('DOCUMENT_RETENTION_YEARS', '7')),
    'AUTO_VERIFY_RECEIPTS': os.getenv('DOCUMENT_AUTO_VERIFY_RECEIPTS', 'false').lower() == 'true'
}

# Enhanced Posting Configuration - NEW SECTION
POSTING_CONFIG = {
    # Main feature toggles
    'ENABLE_ENHANCED_POSTING': os.getenv('ENABLE_ENHANCED_POSTING', 'false').lower() == 'true',
    'AUTO_POST_INVOICES': os.getenv('AUTO_POST_INVOICES', 'true').lower() == 'true',
    'AUTO_POST_PAYMENTS': os.getenv('AUTO_POST_PAYMENTS', 'true').lower() == 'true',
    'REQUIRE_APPROVAL_FOR_CREDIT_NOTES': os.getenv('REQUIRE_APPROVAL_FOR_CREDIT_NOTES', 'true').lower() == 'true',
    
    # Batch processing settings
    'POSTING_BATCH_SIZE': int(os.getenv('POSTING_BATCH_SIZE', '100')),
    'MAX_POSTING_RETRIES': 3,
    'POSTING_RETRY_DELAY_SECONDS': 30,
    
    # Default GL Account Mappings
    'DEFAULT_AP_ACCOUNT': os.getenv('DEFAULT_AP_ACCOUNT', '2100'),
    'DEFAULT_INVENTORY_ACCOUNT': os.getenv('DEFAULT_INVENTORY_ACCOUNT', '1410'),
    'DEFAULT_EXPENSE_ACCOUNT': os.getenv('DEFAULT_EXPENSE_ACCOUNT', '5900'),
    'DEFAULT_BANK_ACCOUNT': os.getenv('DEFAULT_BANK_ACCOUNT', '1200'),
    'DEFAULT_CASH_ACCOUNT': os.getenv('DEFAULT_CASH_ACCOUNT', '1100'),
    'CREDIT_NOTE_EXPENSE_ACCOUNT': os.getenv('CREDIT_NOTE_EXPENSE_ACCOUNT', '5999'), 
    
    # GST Account Mappings
    'CGST_RECEIVABLE_ACCOUNT': os.getenv('CGST_RECEIVABLE_ACCOUNT', '1710'),
    'SGST_RECEIVABLE_ACCOUNT': os.getenv('SGST_RECEIVABLE_ACCOUNT', '1720'),
    'IGST_RECEIVABLE_ACCOUNT': os.getenv('IGST_RECEIVABLE_ACCOUNT', '1730'),
    
    # Account mappings by payment method
    'PAYMENT_METHOD_ACCOUNTS': {
        'cash': os.getenv('DEFAULT_CASH_ACCOUNT', '1002'),
        'bank_transfer': os.getenv('DEFAULT_BANK_ACCOUNT', '1001'),
        'cheque': os.getenv('DEFAULT_BANK_ACCOUNT', '1001'),
        'card': os.getenv('DEFAULT_BANK_ACCOUNT', '1001'),
        'upi': os.getenv('DEFAULT_BANK_ACCOUNT', '1001'),
        'neft': os.getenv('DEFAULT_BANK_ACCOUNT', '1001'),
        'rtgs': os.getenv('DEFAULT_BANK_ACCOUNT', '1001'),
    },
    
    # Account mappings by medicine type for better classification
    'MEDICINE_TYPE_ACCOUNTS': {
        'OTC': os.getenv('DEFAULT_INVENTORY_ACCOUNT', '1301'),
        'Prescription': '1302',   # Inventory - Prescription Medicines  
        'Product': '1303',        # Inventory - Products
        'Consumable': '1304',     # Inventory - Consumables
        'Misc': '1305',           # Inventory - Miscellaneous
    },
    
    # Validation settings
    'VALIDATE_ACCOUNT_EXISTENCE': os.getenv('VALIDATE_ACCOUNT_EXISTENCE', 'true').lower() == 'true',
    'VALIDATE_POSTING_BALANCE': True,
    'ALLOW_NEGATIVE_INVENTORY': False,
    
    # Error handling
    'CONTINUE_ON_POSTING_ERRORS': os.getenv('CONTINUE_ON_POSTING_ERRORS', 'false').lower() == 'true',
    'LOG_POSTING_DETAILS': os.getenv('LOG_POSTING_DETAILS', 'true').lower() == 'true',
    'SEND_POSTING_ERROR_ALERTS': False,
    
    # Reconciliation settings
    'ENABLE_AUTO_RECONCILIATION': False,
    'RECONCILIATION_TOLERANCE': 0.01,
    'DAILY_RECONCILIATION_TIME': '23:30',
}

# Credit Note Configuration
CREDIT_NOTE_CONFIG = {
    # Basic settings
    'ENABLED': os.getenv('CREDIT_NOTE_ENABLED', 'true').lower() == 'true',
    'AUTO_GENERATE_CREDIT_NUMBER': True,
    'CREDIT_NUMBER_PREFIX': 'CN',
    
    # Business rules
    'ALLOW_MULTIPLE_CREDITS_PER_PAYMENT': True,
    'MAX_CREDIT_PERCENTAGE': 100,  # Can credit up to 100% of payment
    'REQUIRE_REASON': True,
    'MIN_REASON_LENGTH': 10,
    
    # Line item handling (NO MEDICINE DEPENDENCY)
    'DEFAULT_CREDIT_DESCRIPTION': 'Payment Adjustment - Credit Note',
    'USE_VIRTUAL_LINE_ITEMS': True,  # Don't require medicine_id
    'VIRTUAL_MEDICINE_NAME': 'Credit Note Adjustment',
    
    # Permissions - reuse your existing pattern
    'CREATE_PERMISSION': 'supplier.edit',
    'VIEW_PERMISSION': 'supplier.view',
    
    # UI settings
    'SHOW_IN_PAYMENT_VIEW': True,
    'ENABLE_PARTIAL_CREDITS': True,
}

# Reason codes for credit notes
CREDIT_NOTE_REASONS = [
    ('payment_error', 'Payment Error'),
    ('duplicate_payment', 'Duplicate Payment'), 
    ('overpayment', 'Overpayment'),
    ('invoice_dispute', 'Invoice Dispute'),
    ('quality_issue', 'Quality Issue'),
    ('cancellation', 'Order Cancellation'),
    ('return', 'Goods Return'),
    ('other', 'Other')
]