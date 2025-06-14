# app/utils/filters.py

from datetime import datetime
import locale

def currencyformat(value, currency_code=None):
    """
    Format a value as currency with appropriate formatting for the currency
    
    Args:
        value: Numeric value to format
        currency_code: Optional currency code (e.g., 'INR', 'USD', 'EUR')
        
    Returns:
        Formatted currency string
    """
    try:
        # Convert to float if it's not already
        value = float(value)
        
        # Default to INR if no currency code is provided
        if not currency_code:
            currency_code = 'INR'
            
        # Currency-specific formatting
        if currency_code == 'INR':
            # Indian numbering system formatting
            s = "{:,.2f}".format(value)
            
            # For Indian format, we need to adjust the comma positions
            parts = s.split('.')
            whole_part = parts[0].replace(',', '')
            decimal_part = parts[1] if len(parts) > 1 else '00'
            
            # Apply Indian comma placement
            if len(whole_part) > 3:
                # Last 3 digits
                last_three = whole_part[-3:]
                # Remaining digits
                remaining = whole_part[:-3]
                
                # Add commas every 2 digits in the remaining part (Indian system)
                formatted_remaining = ""
                for i, digit in enumerate(reversed(remaining)):
                    if i > 0 and i % 2 == 0:
                        formatted_remaining = "," + formatted_remaining
                    formatted_remaining = digit + formatted_remaining
                    
                whole_part = formatted_remaining + "," + last_three
            
            return " Rs. " + whole_part + "." + decimal_part
            
        elif currency_code == 'USD':
            # US/International formatting
            return "$ {:,.2f}".format(value)
            
        elif currency_code == 'EUR':
            # Euro formatting (typically uses spaces for thousands in many European countries)
            # This is a simplified version - some European countries use different formats
            return "€ {:,.2f}".format(value)
            
        else:
            # For other currencies, use international format with currency code
            return "{} {:,.2f}".format(currency_code, value)
        
    except (ValueError, TypeError):
        # Return appropriate default based on currency code
        if currency_code == 'USD':
            return "$ 0.00"
        elif currency_code == 'EUR':
            return "€ 0.00"
        else:
            return " Rs. 0.00"


def dateformat(value, format_string='%d-%m-%Y'):
    """
    Format a date value
    
    Args:
        value: Date/datetime object to format
        format_string: strftime format string
        
    Returns:
        Formatted date string
    """
    if value is None:
        return ''
    
    try:
        return value.strftime(format_string)
    except AttributeError:
        return str(value)


def datetimeformat(value, format_string='%d-%m-%Y %H:%M'):
    """
    Format a datetime value
    
    Args:
        value: Datetime object to format
        format_string: strftime format string
        
    Returns:
        Formatted datetime string
    """
    if value is None:
        return ''
    
    try:
        return value.strftime(format_string)
    except AttributeError:
        return str(value)


def timeago(value):
    """
    Format a datetime as a human-readable time ago string
    
    Args:
        value: Datetime object
        
    Returns:
        Human-readable time ago string (e.g., "5 minutes ago")
    """
    if value is None:
        return ''
    
    try:
        now = datetime.now()
        if value.tzinfo:
            now = datetime.now(value.tzinfo)
        
        diff = now - value
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:  # Less than 1 hour
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:  # Less than 1 day
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif seconds < 2592000:  # Less than 30 days
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        elif seconds < 31536000:  # Less than 1 year
            months = int(seconds / 2592000)
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = int(seconds / 31536000)
            return f"{years} year{'s' if years != 1 else ''} ago"
    
    except Exception:
        return str(value)


def format_currency(value):
    """
    Alias for currencyformat to maintain backward compatibility
    """
    return currencyformat(value)


def numberformat(value, decimals=2):
    """
    Format a number with specified decimal places
    
    Args:
        value: Numeric value to format
        decimals: Number of decimal places
        
    Returns:
        Formatted number string
    """
    try:
        value = float(value)
        format_string = f"{{:,.{decimals}f}}"
        return format_string.format(value)
    except (ValueError, TypeError):
        return "0.00"


def percentformat(value, decimals=1):
    """
    Format a value as percentage
    
    Args:
        value: Numeric value (0-100 or 0-1)
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    try:
        value = float(value)
        # If value is between 0 and 1, multiply by 100
        if 0 <= value <= 1:
            value = value * 100
        format_string = f"{{:.{decimals}f}}%"
        return format_string.format(value)
    except (ValueError, TypeError):
        return "0.0%"


def statusformat(value):
    """
    Format status values to be more human-readable
    
    Args:
        value: Status string (e.g., "in_progress", "completed")
        
    Returns:
        Formatted status string
    """
    if not value:
        return ''
    
    # Convert snake_case to Title Case
    return value.replace('_', ' ').title()


def boolformat(value, true_text="Yes", false_text="No"):
    """
    Format boolean values to human-readable text
    
    Args:
        value: Boolean value
        true_text: Text to display for True
        false_text: Text to display for False
        
    Returns:
        Human-readable boolean text
    """
    return true_text if value else false_text


def register_filters(app):
    """
    Register custom filters with Flask app
    
    Args:
        app: Flask application instance
    """
    app.jinja_env.filters['currencyformat'] = currencyformat
    app.jinja_env.filters['format_currency'] = format_currency  # Alias
    app.jinja_env.filters['dateformat'] = dateformat
    app.jinja_env.filters['datetimeformat'] = datetimeformat
    app.jinja_env.filters['timeago'] = timeago
    app.jinja_env.filters['numberformat'] = numberformat
    app.jinja_env.filters['percentformat'] = percentformat
    app.jinja_env.filters['statusformat'] = statusformat
    app.jinja_env.filters['boolformat'] = boolformat
    
    # Add global functions that might be useful
    app.jinja_env.globals['now'] = datetime.now