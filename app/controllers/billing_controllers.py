# app/controllers/billing_controllers.py

from app.controllers.form_controller import FormController
from app.forms.billing_forms import AdvancePaymentForm, PaymentForm
from app.services.billing_service import (
    create_advance_payment, 
    record_payment,
    get_invoice_by_id,         
    get_patient_advance_balance  
)
from app.services.database_service import (
    get_db_session,
    get_detached_copy,
    get_entity_dict
)
from app.models.transaction import InvoiceHeader, PaymentDetail
from app.models.master import Patient, Hospital, Branch
from app.utils.menu_utils import get_menu_items

from decimal import Decimal
import uuid
from datetime import datetime, timezone, timedelta
from flask import url_for
from flask_login import current_user
import logging

logger = logging.getLogger(__name__)

class AdvancePaymentController(FormController):
    """Controller for handling advance payment forms"""
    
    def __init__(self):
        super().__init__(
            form_class=AdvancePaymentForm,
            template_path='billing/advance_payment.html',
            success_url=self.get_success_url,
            success_message="Advance payment recorded successfully",
            page_title="Record Advance Payment"
        )
    
    def initialize_form(self, form, *args, **kwargs):
        """Set default values for form fields"""
        form.payment_date.data = datetime.now(timezone.utc).date()
    
    def process_form(self, form, *args, **kwargs):
        """Process advance payment form submission"""
        # Get form data
        patient_id = uuid.UUID(form.patient_id.data)
        payment_date = form.payment_date.data
        cash_amount = form.cash_amount.data or Decimal('0')
        credit_card_amount = form.credit_card_amount.data or Decimal('0')
        debit_card_amount = form.debit_card_amount.data or Decimal('0')
        upi_amount = form.upi_amount.data or Decimal('0')
        total_amount = cash_amount + credit_card_amount + debit_card_amount + upi_amount
        
        # Create advance payment using existing service function
        result = create_advance_payment(
            hospital_id=current_user.hospital_id,
            patient_id=patient_id,
            amount=total_amount,
            payment_date=payment_date,
            cash_amount=cash_amount,
            credit_card_amount=credit_card_amount,
            debit_card_amount=debit_card_amount,
            upi_amount=upi_amount,
            card_number_last4=form.card_number_last4.data,
            card_type=form.card_type.data,
            upi_id=form.upi_id.data,
            reference_number=form.reference_number.data,
            notes=form.notes.data,
            current_user_id=current_user.user_id
        )
        
        # Return the result for success_redirect
        return {
            'patient_id': patient_id,
            'total_amount': total_amount,
            'result': result
        }
    
    def get_success_url(self, result, *args, **kwargs):
        """Generate success URL based on processing result"""
        patient_id = result['patient_id']
        return url_for('billing_views.view_patient_advances', patient_id=patient_id)


class PaymentFormController(FormController):
    """Controller for handling invoice payment forms"""
    
    def __init__(self):
        super().__init__(
            form_class=PaymentForm,
            template_path='billing/payment_form_page.html',
            success_url=self.get_success_url,
            success_message="Payment recorded successfully",
            page_title="Record Payment",
            additional_context=lambda *args, **kwargs: self.get_additional_context(*args, **kwargs)
        )
    
    def initialize_form(self, form, *args, **kwargs):
        """Set default values for form fields"""
        form.payment_date.data = datetime.now().date()
        
        # Get invoice_id from kwargs
        invoice_id = kwargs.get('invoice_id')
        if invoice_id:
            form.invoice_id.data = str(invoice_id)
    
    def get_additional_context(self, *args, **kwargs):
        """Provide additional context for the template"""      

        logging.info(f"get_additional_context called with args: {args}, kwargs: {kwargs}")

        invoice_id = kwargs.get('invoice_id')
        pay_all = kwargs.get('pay_all', False)
        
        logger.info(f"PaymentFormController.get_additional_context - invoice_id: {invoice_id}, pay_all: {pay_all}")

        if not invoice_id:
            raise ValueError("Invoice ID is required")
            
        # Get invoice details
        invoice = get_invoice_by_id(
            hospital_id=current_user.hospital_id,
            invoice_id=invoice_id
        )
        logger.info(f"PaymentFormController - Retrieved invoice: {invoice.get('invoice_number')}")

        # Ensure we have fresh balance data from the database
        with get_db_session() as session:
            fresh_invoice = session.query(InvoiceHeader).filter_by(
                hospital_id=current_user.hospital_id,
                invoice_id=invoice_id
            ).first()
            
            if fresh_invoice:
                # Update the invoice with fresh balance data
                invoice['balance_due'] = float(fresh_invoice.balance_due)
                invoice['paid_amount'] = float(fresh_invoice.paid_amount)
                logger.info(f"Using fresh balance due: {invoice['balance_due']} for payment form")

        # Get patient details
        patient = None
        with get_db_session() as session:
            patient_record = session.query(Patient).filter_by(
                hospital_id=current_user.hospital_id,
                patient_id=invoice['patient_id']
            ).first()
            
            if patient_record:
                # Create detached copy before accessing properties
                patient_detached = get_detached_copy(patient_record)
                patient = {
                    'patient_id': str(patient_detached.patient_id),
                    'mrn': patient_detached.mrn,
                    'name': patient_detached.full_name,
                    'personal_info': patient_detached.personal_info,
                    'contact_info': patient_detached.contact_info
                }
        
        # Get related invoices if pay_all is true
        related_invoices = []
        total_balance_due = float(invoice['balance_due'])
        total_amount = float(invoice['grand_total'])
        total_paid_amount = float(invoice['paid_amount'])
        
        # Always get related invoices regardless of pay_all flag - this is the key change
        if invoice.get('created_at'):
            # Get invoices created around the same time for the same patient
            created_time = invoice.get('created_at')
            patient_id = invoice.get('patient_id')
            
            # Define a time window (e.g., 5 minutes)
            time_window = timedelta(minutes=5)
            
            with get_db_session() as session:
                related_records = session.query(InvoiceHeader).filter(
                    InvoiceHeader.hospital_id == current_user.hospital_id,
                    InvoiceHeader.patient_id == patient_id,
                    InvoiceHeader.created_at >= created_time - time_window,
                    InvoiceHeader.created_at <= created_time + time_window,
                    InvoiceHeader.invoice_id != invoice_id,
                    InvoiceHeader.is_cancelled == False,  # Exclude cancelled invoices
                    InvoiceHeader.balance_due > 0  # Only include those with balance due
                ).all()
                
                # Calculate total balance due including related invoices
                for related in related_records:
                    related_dict = get_entity_dict(related)
                    related_invoices.append(related_dict)
                    # Only include in totals if pay_all is true
                    if pay_all:
                        total_balance_due += float(related_dict['balance_due'])
                        total_amount += float(related_dict['grand_total'])
                        total_paid_amount += float(related_dict['paid_amount'])
        
        # Get available advance balance
        advance_balance = get_patient_advance_balance(
            hospital_id=current_user.hospital_id,
            patient_id=invoice['patient_id']
        )
        
        # Check if there's available advance and related invoices
        has_advance = advance_balance > 0
        has_related_invoices = len(related_invoices) > 0
        
        # Show multi-invoice UI if pay_all is true OR there's advance available AND related invoices
        show_multi_invoice = pay_all or (has_advance and has_related_invoices)

        # Get approval threshold from config
        from flask import current_app
        approval_threshold = float(current_app.config.get('APPROVAL_THRESHOLD_L1', '100000.00'))

        context = {
            'invoice': invoice,
            'patient': patient,
            'related_invoices': related_invoices if has_related_invoices else None,
            'total_balance_due': total_balance_due,
            'total_amount': total_amount,
            'total_paid_amount': total_paid_amount,
            'pay_all': pay_all,
            'show_multi_invoice': show_multi_invoice,  # New flag for UI
            'has_advance': has_advance,
            'advance_balance': advance_balance,
            'approval_threshold': approval_threshold,  # Add approval threshold for UI
            'menu_items': get_menu_items(current_user)
        }
        
        logger.info(f"PaymentFormController - Returning context with keys: {context.keys()}")
        return context
    
    def process_form(self, form, *args, **kwargs):
        """Process payment form submission"""
        from flask import request  # Add this import
        
        invoice_id = kwargs.get('invoice_id')
        pay_all = kwargs.get('pay_all', False)
        
        if not invoice_id:
            raise ValueError("Invoice ID is required")

        # Fix the type conversion issue - check if invoice_id is already a UUID
        if not isinstance(invoice_id, uuid.UUID):
            invoice_id = uuid.UUID(invoice_id)

        # Get form data
        payment_date = form.payment_date.data
        cash_amount = form.cash_amount.data or Decimal('0')
        credit_card_amount = form.credit_card_amount.data or Decimal('0')
        debit_card_amount = form.debit_card_amount.data or Decimal('0')
        upi_amount = form.upi_amount.data or Decimal('0')
        card_number_last4 = form.card_number_last4.data
        card_type = form.card_type.data
        upi_id = form.upi_id.data
        reference_number = form.reference_number.data
        
        # Calculate total
        total_amount = cash_amount + credit_card_amount + debit_card_amount + upi_amount
        
        # If pay_all is true, distribute payment across invoices
        if pay_all:
            # Get selected invoice IDs from the request object
            from flask import request
            selected_invoice_ids = request.form.getlist('invoice_ids')
            
            if not selected_invoice_ids:
                logger.warning("No invoices selected for payment, using current invoice")
                selected_invoice_ids = [str(invoice_id)]
            
            # Return a dictionary with the result
            return {
                'invoice_id': invoice_id,
                'multi_invoice': True,
                'selected_invoice_ids': selected_invoice_ids
            }
        else:
            # Regular single invoice payment
            # Get approval threshold from config (default: ₹100,000)
            from flask import current_app
            approval_threshold = Decimal(str(current_app.config.get('APPROVAL_THRESHOLD_L1', '100000.00')))

            # Check if user requested to save as draft
            save_as_draft = request.form.get('save_as_draft') == 'true'

            result = record_payment(
                hospital_id=current_user.hospital_id,
                invoice_id=invoice_id,
                payment_date=payment_date,
                cash_amount=cash_amount,
                credit_card_amount=credit_card_amount,
                debit_card_amount=debit_card_amount,
                upi_amount=upi_amount,
                card_number_last4=card_number_last4,
                card_type=card_type,
                upi_id=upi_id,
                reference_number=reference_number,
                handle_excess=True,
                recorded_by=current_user.user_id,
                save_as_draft=save_as_draft,
                approval_threshold=approval_threshold
            )
            
            return {
                'invoice_id': invoice_id,
                'result': result
            }
    
    def get_success_url(self, result, *args, **kwargs):
        """Generate success URL based on processing result"""
        invoice_id = result.get('invoice_id')
        return url_for('billing_views.view_invoice', invoice_id=invoice_id)