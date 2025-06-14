# app/controllers/form_controller.py

from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user
from app.utils.menu_utils import get_menu_items
import logging

logger = logging.getLogger(__name__)

class FormController:
    """
    Base class for form handling controllers
    
    This class provides common functionality for handling forms:
    - Form initialization
    - GET/POST handling
    - Success/error messages
    - Redirection
    """
    
    def __init__(
        self, 
        form_class, 
        template_path, 
        success_url=None,
        success_message="Form submitted successfully",
        page_title=None,
        additional_context=None
    ):
        """
        Initialize the form controller
        
        Args:
            form_class: The WTForms form class to use
            template_path: Path to the template to render
            success_url: URL to redirect to on success (can be a function or string)
            success_message: Message to flash on success
            page_title: Page title to display
            additional_context: Additional template context
        """
        self.form_class = form_class
        self.template_path = template_path
        self.success_url = success_url
        self.success_message = success_message
        self.page_title = page_title
        self.additional_context = additional_context or {}
        
    def handle_request(self, *args, **kwargs):
        """
        Handle GET/POST request
        
        Override this method to customize behavior
        
        Returns:
            Flask response object
        """
        form = self.get_form(*args, **kwargs)
        
        if request.method == 'POST':
            return self.handle_post(form, *args, **kwargs)
        else:
            return self.handle_get(form, *args, **kwargs)
    
    def get_form(self, *args, **kwargs):
        """
        Get the form instance
        
        Override this method to customize form initialization
        
        Returns:
            Form instance
        """
        return self.form_class()
    
    def handle_get(self, form, *args, **kwargs):
        """
        Handle GET request
        
        Override this method to customize GET behavior
        
        Args:
            form: Form instance
            
        Returns:
            Flask response object
        """
        self.initialize_form(form, *args, **kwargs)
        return self.render_form(form, *args, **kwargs)
    
    def initialize_form(self, form, *args, **kwargs):
        """
        Initialize form values for GET request
        
        Override this method to set default values
        
        Args:
            form: Form instance
        """
        pass
    
    def handle_post(self, form, *args, **kwargs):
        """
        Handle POST request - process the form submission
        
        This enhanced method provides robust form validation handling that works with
        both standard WTForms validation and custom validation methods.
        """
        form_valid = False
        
        # Attempt validation with appropriate error handling
        try:
            # Try standard Flask-WTF validation
            form_valid = form.validate_on_submit()
        except TypeError as e:
            # Handle the case where form.validate() doesn't accept extra_validators
            if "extra_validators" in str(e):
                logger.info("Falling back to basic form validation without extra_validators")
                # Check if the form is submitted first
                if request.method == 'POST' and form.is_submitted():
                    # Try basic validation without extra_validators
                    form_valid = form.validate()
            else:
                # For other TypeError exceptions, log and continue to error handling
                logger.error(f"Form validation TypeError: {str(e)}", exc_info=True)
        except Exception as e:
            # Log any other validation exceptions
            logger.error(f"Form validation exception: {str(e)}", exc_info=True)
        
        # Process form based on validation result
        if form_valid:
            try:
                # Process validated form data - same as original implementation
                result = self.process_form(form, *args, **kwargs)
                
                # Flash success message - preserves original behavior
                if isinstance(self.success_message, str) and self.success_message:
                    flash(self.success_message, "success")
                
                # Redirect to success URL - preserves original behavior
                return self.success_redirect(result, *args, **kwargs)
            except Exception as e:
                # Error handling - same as original implementation
                logger.error(f"Error processing form: {str(e)}", exc_info=True)
                flash(f"Error: {str(e)}", "error")
        else:
            # Validation failure handling - same as original implementation
            if hasattr(form, 'errors') and form.errors:
                logger.error(f"Form validation failed: {form.errors}")
                flash("Please correct the errors in the form", "error")
        
        # If we reached here, either validation failed or processing failed
        # Re-render the form - same as original implementation
        return self.render_form(form, *args, **kwargs)
    
    def process_form(self, form, *args, **kwargs):
        """
        Process the form data after validation
        
        This method should be overridden by subclasses
        
        Args:
            form: Validated form instance
            
        Returns:
            Result object used for redirection
        """
        raise NotImplementedError("Subclasses must implement process_form")
    
    def success_redirect(self, result, *args, **kwargs):
        """
        Redirect after successful form processing
        
        Args:
            result: Result from process_form
            
        Returns:
            Flask redirect response
        """
        if callable(self.success_url):
            url = self.success_url(result, *args, **kwargs)
        else:
            url = self.success_url
        
        return redirect(url)
    
    def render_form(self, form, *args, **kwargs):
        """
        Render the form template
        
        Args:
            form: Form instance
            
        Returns:
            Flask render_template response
        """
        import logging
        logger = logging.getLogger(__name__)

        context = {
            'form': form,
            'payment_form': form,
            'menu_items': get_menu_items(current_user),
            'page_title': self.page_title or "Form"
        }
        
        # Add additional context if provided
        if self.additional_context:
            if callable(self.additional_context):
                logger.info(f"FormController.render_form - Calling additional_context method")
                additional = self.additional_context(*args, **kwargs)
                logger.info(f"FormController.render_form - additional_context returned keys: {additional.keys() if additional else 'None'}")
            else:
                additional = self.additional_context
                
            if additional:
                context.update(additional)
        
        logger.info(f"FormController.render_form - Final context keys: {context.keys()}")
        return render_template(self.template_path, **context)