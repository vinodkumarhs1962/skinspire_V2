# app/utils/unicode_logging.py

import sys
import logging
import os
import codecs
from logging.handlers import RotatingFileHandler

class UnicodeFormatter(logging.Formatter):
    """
    Custom formatter that handles Unicode characters safely
    """
    def __init__(self, fmt=None, datefmt=None, use_emoji=True):
        super().__init__(fmt, datefmt)
        self.use_emoji = use_emoji
        self.emoji_map = {
            # Emoji symbols
            '🔍': '[INFO]',
            '✅': '[SUCCESS]', 
            '❌': '[ERROR]',
            '⚠️': '[WARNING]',
            '🔄': '[PROCESS]',
            '📊': '[DATA]',
            '💰': '[MONEY]',
            '🏥': '[HOSPITAL]',
            '📝': '[DOC]',
            '🔐': '[SECURITY]',
            
            # Currency symbols
            '₹': 'Rs.',          # Indian Rupee
            '$': 'USD ',         # US Dollar
            '€': 'EUR ',         # Euro
            '£': 'GBP ',         # British Pound
            '¥': 'JPY ',         # Japanese Yen
            '₽': 'RUB ',         # Russian Ruble
            '₦': 'NGN ',         # Nigerian Naira
            '₨': 'Rs.',          # Generic Rupee symbol
            '¢': 'cents',        # Cents
            '₡': 'CRC ',         # Costa Rican Colon
            '₩': 'KRW ',         # South Korean Won
            '₪': 'ILS ',         # Israeli Shekel
            '₫': 'VND ',         # Vietnamese Dong
            '₴': 'UAH ',         # Ukrainian Hryvnia
            '₲': 'PYG ',         # Paraguayan Guarani
            
            # Mathematical and special symbols
            '±': '+/-',          # Plus-minus
            '×': 'x',            # Multiplication
            '÷': '/',            # Division
            '≤': '<=',           # Less than or equal
            '≥': '>=',           # Greater than or equal
            '≠': '!=',           # Not equal
            '≈': '~=',           # Approximately equal
            '∞': 'infinity',     # Infinity
            '°': 'deg',          # Degree symbol
            '™': '(TM)',         # Trademark
            '©': '(C)',          # Copyright
            '®': '(R)',          # Registered trademark
            
            # Business and medical symbols
            '📈': '[GROWTH]',    # Chart increasing
            '📉': '[DECLINE]',   # Chart decreasing
            '💊': '[MEDICINE]',  # Pill
            '🩺': '[MEDICAL]',   # Stethoscope
            '🏥': '[HOSPITAL]',  # Hospital
            '💉': '[INJECTION]', # Syringe
            '🧾': '[RECEIPT]',   # Receipt
            '📋': '[FORM]',      # Clipboard
            '👨‍⚕️': '[DOCTOR]',    # Doctor
            '👩‍⚕️': '[DOCTOR]',    # Doctor (female)
            '🚑': '[AMBULANCE]', # Ambulance
        }
        
    def format(self, record):
        try:
            # Try normal formatting first
            formatted = super().format(record)
            
            # Test if the formatted message can be encoded on Windows
            if sys.platform.startswith('win'):
                formatted.encode('utf-8')
            
            return formatted
            
        except UnicodeEncodeError:
            # Fallback: Replace problematic Unicode characters
            if self.use_emoji:
                safe_message = record.getMessage()
                for emoji, replacement in self.emoji_map.items():
                    safe_message = safe_message.replace(emoji, replacement)
                
                # Update the record with safe message
                record.msg = safe_message
                record.args = ()
            
            # Format again with safe message
            return super().format(record)
        
        except Exception as e:
            # Ultimate fallback
            return f"{record.levelname}: {record.getMessage()} [Unicode Error: {e}]"


class UnicodeConsoleHandler(logging.StreamHandler):
    """
    Console handler that gracefully handles Unicode errors
    """
    def emit(self, record):
        try:
            super().emit(record)
        except UnicodeEncodeError:
            # Fallback: Create safe version of the message
            try:
                safe_record = logging.LogRecord(
                    record.name, record.levelno, record.pathname,
                    record.lineno, record.getMessage().encode('ascii', 'replace').decode('ascii'),
                    (), record.exc_info
                )
                super().emit(safe_record)
            except Exception:
                # Ultimate fallback
                print(f"[LOGGING ERROR] {record.levelname}: Could not log Unicode message")


class SafeUnicodeLogger:
    """
    Wrapper for logging that automatically handles Unicode issues
    """
    
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.emoji_map = {
            # Emoji symbols
            '🔍': '[INFO]',
            '✅': '[SUCCESS]', 
            '❌': '[ERROR]',
            '⚠️': '[WARNING]',
            '🔄': '[PROCESS]',
            '📊': '[DATA]',
            '💰': '[MONEY]',
            '🏥': '[HOSPITAL]',
            '📝': '[DOC]',
            '🔐': '[SECURITY]',
            '🎯': '[TOTAL]',
            '🔧': '[SETTINGS]',
            
            # Currency symbols
            '₹': 'Rs.',          # Indian Rupee
            '$': 'USD ',         # US Dollar
            '€': 'EUR ',         # Euro
            '£': 'GBP ',         # British Pound
            '¥': 'JPY ',         # Japanese Yen
            '₽': 'RUB ',         # Russian Ruble
            '₦': 'NGN ',         # Nigerian Naira
            '₨': 'Rs.',          # Generic Rupee symbol
            '¢': 'cents',        # Cents
            '₡': 'CRC ',         # Costa Rican Colon
            '₩': 'KRW ',         # South Korean Won
            '₪': 'ILS ',         # Israeli Shekel
            '₫': 'VND ',         # Vietnamese Dong
            '₴': 'UAH ',         # Ukrainian Hryvnia
            '₲': 'PYG ',         # Paraguayan Guarani
            
            # Mathematical and special symbols
            '±': '+/-',          # Plus-minus
            '×': 'x',            # Multiplication
            '÷': '/',            # Division
            '≤': '<=',           # Less than or equal
            '≥': '>=',           # Greater than or equal
            '≠': '!=',           # Not equal
            '≈': '~=',           # Approximately equal
            '∞': 'infinity',     # Infinity
            '°': 'deg',          # Degree symbol
            '™': '(TM)',         # Trademark
            '©': '(C)',          # Copyright
            '®': '(R)',          # Registered trademark
            
            # Business and medical symbols
            '📈': '[GROWTH]',    # Chart increasing
            '📉': '[DECLINE]',   # Chart decreasing
            '💊': '[MEDICINE]',  # Pill
            '🩺': '[MEDICAL]',   # Stethoscope
            '🏥': '[HOSPITAL]',  # Hospital
            '💉': '[INJECTION]', # Syringe
            '🧾': '[RECEIPT]',   # Receipt
            '📋': '[FORM]',      # Clipboard
            '👨‍⚕️': '[DOCTOR]',    # Doctor
            '👩‍⚕️': '[DOCTOR]',    # Doctor (female)
            '🚑': '[AMBULANCE]', # Ambulance
        }
    
    def _safe_message(self, message):
        """Convert Unicode message to safe version if needed"""
        if not isinstance(message, str):
            message = str(message)
            
        # On Windows, check if message can be safely encoded
        if sys.platform.startswith('win'):
            try:
                message.encode('cp1252')
                return message  # Message is safe
            except UnicodeEncodeError:
                # Replace emojis with ASCII equivalents
                for emoji, replacement in self.emoji_map.items():
                    message = message.replace(emoji, replacement)
                return message
        
        return message
    
    def info(self, message, *args, **kwargs):
        safe_msg = self._safe_message(message)
        self.logger.info(safe_msg, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        safe_msg = self._safe_message(message)
        self.logger.warning(safe_msg, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        safe_msg = self._safe_message(message)
        self.logger.error(safe_msg, *args, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        safe_msg = self._safe_message(message)
        self.logger.debug(safe_msg, *args, **kwargs)
    
    def exception(self, message, *args, **kwargs):
        safe_msg = self._safe_message(message)
        self.logger.exception(safe_msg, *args, **kwargs)


def configure_windows_console_utf8():
    """Configure Windows console for UTF-8 support"""
    if not sys.platform.startswith('win'):
        return True
        
    try:
        # Method 1: Set console code page to UTF-8 (Windows 10+)
        os.system('chcp 65001 > nul 2>&1')
        
        # Method 2: Set environment variables for UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # Method 3: Reconfigure stdout/stderr for UTF-8
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        elif hasattr(sys.stdout, 'buffer'):
            # Fallback for older Python versions
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
        
        return True
        
    except Exception:
        return False


def setup_unicode_logging(logs_dir='logs'):
    """
    MAIN FUNCTION: Set up comprehensive Unicode logging support
    
    Args:
        logs_dir: Directory for log files (default: 'logs')
    
    Returns:
        bool: True if setup successful, False otherwise
    """
    try:
        # Step 1: Configure Windows console for UTF-8
        configure_windows_console_utf8()
        
        # Step 2: Configure root logger with Unicode support
        root_logger = logging.getLogger()
        
        # Clear existing handlers to avoid conflicts
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Step 3: Create Unicode-safe console handler
        console_handler = UnicodeConsoleHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = UnicodeFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            use_emoji=True
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Step 4: Create Unicode-safe file handler
        try:
            os.makedirs(logs_dir, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                os.path.join(logs_dir, 'app.log'),
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'  # Explicitly set UTF-8 encoding for files
            )
            file_handler.setLevel(logging.INFO)
            file_formatter = UnicodeFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                use_emoji=True
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
            
        except Exception:
            # Continue without file logging if it fails
            pass
        
        # Set root logger level
        root_logger.setLevel(logging.INFO)
        
        # Step 5: Test Unicode logging
        test_logger = logging.getLogger('unicode_setup')
        test_logger.info("✅ Unicode logging initialized successfully")
        
        return True
        
    except Exception:
        # Fallback to basic logging if Unicode setup fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return False


def get_unicode_safe_logger(name):
    """
    CONVENIENCE FUNCTION: Get a Unicode-safe logger instance
    
    Args:
        name: Logger name
        
    Returns:
        SafeUnicodeLogger: Unicode-safe logger wrapper
    """
    return SafeUnicodeLogger(name)


def format_indian_currency(amount, include_symbol=True):
    """
    UTILITY: Format amount in Indian currency format with Unicode-safe rupee symbol
    
    Args:
        amount: Numeric amount
        include_symbol: Whether to include ₹ symbol (default: True)
    
    Returns:
        str: Formatted currency string (e.g., "₹2,47,800.00" or "Rs.2,47,800.00")
    
    Examples:
        format_indian_currency(247800) -> "₹2,47,800.00" or "Rs.2,47,800.00"
        format_indian_currency(1234.56) -> "₹1,234.56" or "Rs.1,234.56"
    """
    try:
        amount_float = float(amount)
        
        # Format with Indian numbering system (lakhs, crores)
        if amount_float >= 10000000:  # 1 crore
            crores = amount_float / 10000000
            formatted = f"{crores:,.2f} Cr"
        elif amount_float >= 100000:  # 1 lakh
            lakhs = amount_float / 100000
            formatted = f"{lakhs:,.2f} L"
        else:
            formatted = f"{amount_float:,.2f}"
        
        if include_symbol:
            # Try Unicode rupee symbol first
            import sys
            if sys.platform.startswith('win'):
                try:
                    # Test if rupee symbol can be encoded
                    test_str = f"₹{formatted}"
                    test_str.encode('cp1252')
                    return test_str
                except UnicodeEncodeError:
                    # Fallback to ASCII
                    return f"Rs.{formatted}"
            else:
                return f"₹{formatted}"
        
        return formatted
        
    except (ValueError, TypeError):
        return "₹0.00" if include_symbol else "0.00"


def format_medical_amount(amount, currency='₹', context=''):
    """
    UTILITY: Format medical/hospital amounts with context
    
    Args:
        amount: Numeric amount
        currency: Currency symbol (default: ₹)
        context: Medical context (e.g., 'consultation', 'medicine', 'procedure')
    
    Returns:
        str: Formatted medical amount with safe Unicode
    """
    formatted_amount = format_indian_currency(amount, include_symbol=True)
    
    context_map = {
        'consultation': '👨‍⚕️',
        'medicine': '💊',
        'procedure': '🩺',
        'injection': '💉',
        'surgery': '🏥',
        'lab': '📊',
        'payment': '💰',
        'invoice': '🧾'
    }
    
    context_emoji = context_map.get(context.lower(), '💰')
    
    # Use safe logger to handle Unicode conversion
    temp_logger = SafeUnicodeLogger('medical_format')
    safe_context = temp_logger._safe_message(context_emoji)
    
    return f"{safe_context} {formatted_amount}"