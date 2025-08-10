# File: app/utils/template_filters.py
# ADD this file or add to existing template filters

def safe_get_attr(obj, attr_name, default=None):
    """
    Safely get an attribute from an object or dict.
    Works with both object attributes and dictionary keys.
    
    Usage in template:
    {{ entity_config|safe_attr('title_field', '') }}
    """
    if obj is None:
        return default
    
    # Try object attribute first
    if hasattr(obj, attr_name):
        return getattr(obj, attr_name, default)
    
    # Try dictionary key
    if isinstance(obj, dict):
        return obj.get(attr_name, default)
    
    return default


def register_document_filters(app):
    """Register custom filters for document templates"""
    
    @app.template_filter('safe_attr')
    def safe_attr_filter(obj, attr_name, default=None):
        """Safe attribute access filter for templates"""
        return safe_get_attr(obj, attr_name, default)
    
    @app.template_filter('is_dict')
    def is_dict_filter(obj):
        """Check if object is a dictionary"""
        return isinstance(obj, dict)
    
    @app.template_filter('has_attr')
    def has_attr_filter(obj, attr_name):
        """Check if object has an attribute or key"""
        if obj is None:
            return False
        return hasattr(obj, attr_name) or (isinstance(obj, dict) and attr_name in obj)


# In your app initialization (app/__init__.py or wherever you initialize Flask app):
# from app.utils.template_filters import register_document_filters
# register_document_filters(app)