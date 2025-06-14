"""
Utility functions for generating PDF files using ReportLab
"""
import io
import logging
import os
from decimal import Decimal
from datetime import datetime

# ReportLab imports
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

# XHTML2PDF for HTML-to-PDF conversion (ReportLab-based)
from xhtml2pdf import pisa

# Flask imports
from flask import current_app, render_template

logger = logging.getLogger(__name__)

def html_to_pdf(html_content):
    """
    Convert HTML content to PDF using XHTML2PDF (ReportLab-based)
    
    Args:
        html_content: HTML string to convert
        
    Returns:
        PDF data as bytes
    """
    pdf_buffer = io.BytesIO()
    
    # Convert HTML to PDF
    pisa_status = pisa.CreatePDF(
        src=html_content,            # HTML content
        dest=pdf_buffer,             # Output buffer
        encoding='utf-8'             # Encoding
    )
    
    # Check if conversion was successful
    if pisa_status.err:
        logger.error(f"HTML to PDF conversion failed: {pisa_status.err}")
        raise Exception("HTML to PDF conversion failed")
    
    # Get the PDF from the buffer
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()

def generate_invoice_pdf(invoice_id):
    """
    Generate a PDF for the given invoice using ReportLab.
    
    Args:
        invoice_id: UUID of the invoice
        
    Returns:
        BytesIO containing the PDF data
    """
    try:
        from app.services.billing_service import get_invoice_by_id
        from app.models.master import Patient, Hospital
        from app.services.database_service import get_db_session
        from flask import current_user

        # Get invoice details
        with get_db_session() as session:
            # Get invoice
            invoice = get_invoice_by_id(
                hospital_id=current_user.hospital_id, 
                invoice_id=invoice_id
            )
            
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found")
                
            # Get patient details
            patient = session.query(Patient).filter_by(
                patient_id=invoice['patient_id']
            ).first()
            
            if patient:
                patient_data = {
                    'name': patient.full_name,
                    'mrn': patient.mrn,
                    'contact_info': patient.contact_info,
                    'personal_info': patient.personal_info
                }
            else:
                patient_data = {'name': 'Unknown Patient', 'mrn': 'N/A'}
            
            # Get hospital details
            hospital = session.query(Hospital).filter_by(
                hospital_id=invoice['hospital_id']
            ).first()
            
            if hospital:
                hospital_data = {
                    'name': hospital.name,
                    'address': hospital.address.get('full_address', '') if hasattr(hospital, 'address') and hospital.address else '',
                    'phone': hospital.contact_details.get('phone', '') if hasattr(hospital, 'contact_details') and hospital.contact_details else '',
                    'email': hospital.contact_details.get('email', '') if hasattr(hospital, 'contact_details') and hospital.contact_details else '',
                    'gst_registration_number': hospital.gst_registration_number if hasattr(hospital, 'gst_registration_number') else ''
                }
            else:
                hospital_data = {'name': 'Hospital', 'address': '', 'phone': '', 'email': ''}

        # Method 1: Use direct ReportLab generation
        return _generate_invoice_pdf_reportlab(invoice, patient_data, hospital_data)
        
        # Method 2: Alternatively, use XHTML2PDF to convert HTML to PDF
        # Render the invoice template to HTML
        # html_content = render_template(
        #     'billing/print_invoice.html',
        #     invoice=invoice,
        #     patient=patient_data,
        #     hospital=hospital_data,
        #     print_mode=True
        # )
        # return html_to_pdf(html_content)
        
    except Exception as e:
        logger.error(f"Error generating invoice PDF: {str(e)}", exc_info=True)
        return _generate_error_pdf(str(e))

def _generate_invoice_pdf_reportlab(invoice, patient_data, hospital_data):
    """
    Generate invoice PDF using direct ReportLab API.
    
    Args:
        invoice: Invoice data
        patient_data: Patient information
        hospital_data: Hospital information
        
    Returns:
        PDF data as bytes
    """
    # Create PDF document
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Center',
        alignment=TA_CENTER,
        fontSize=12
    ))
    styles.add(ParagraphStyle(
        name='Right',
        alignment=TA_RIGHT,
        fontSize=10
    ))
    
    # Initialize elements list
    elements = []
    
    # Add hospital header
    elements.append(Paragraph(hospital_data['name'], styles['Heading1']))
    if hospital_data['address']:
        elements.append(Paragraph(hospital_data['address'], styles['Normal']))
    contact_info = []
    if hospital_data['phone']:
        contact_info.append(f"Phone: {hospital_data['phone']}")
    if hospital_data['email']:
        contact_info.append(f"Email: {hospital_data['email']}")
    if contact_info:
        elements.append(Paragraph(" | ".join(contact_info), styles['Normal']))
    if hospital_data['gst_registration_number']:
        elements.append(Paragraph(f"GST No: {hospital_data['gst_registration_number']}", styles['Normal']))
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Add invoice details
    elements.append(Paragraph(f"Invoice #{invoice['invoice_number']}", styles['Heading2']))
    if 'invoice_date' in invoice and invoice['invoice_date']:
        date_str = invoice['invoice_date'].strftime('%d-%b-%Y') if hasattr(invoice['invoice_date'], 'strftime') else str(invoice['invoice_date'])
        elements.append(Paragraph(f"Date: {date_str}", styles['Normal']))
    
    elements.append(Spacer(1, 0.25*inch))
    
    # Add patient details
    elements.append(Paragraph(f"Patient: {patient_data['name']}", styles['Normal']))
    if 'mrn' in patient_data and patient_data['mrn']:
        elements.append(Paragraph(f"MRN: {patient_data['mrn']}", styles['Normal']))
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Add line items table
    data = [['Description', 'Quantity', 'Unit Price', 'Discount', 'Total']]
    
    total_amount = 0
    for item in invoice.get('line_items', []):
        quantity = float(item.get('quantity', 1))
        unit_price = float(item.get('unit_price', 0))
        discount_percent = float(item.get('discount_percent', 0))
        
        # Calculate item total
        item_total = quantity * unit_price
        discount_amount = item_total * (discount_percent / 100)
        final_total = item_total - discount_amount
        
        # Add to overall total
        total_amount += final_total
        
        # Add row to table
        data.append([
            item.get('item_name', 'Unknown Item'),
            str(quantity),
            f"{invoice.get('currency_code', 'INR')} {unit_price:.2f}",
            f"{discount_percent:.2f}%" if discount_percent > 0 else "-",
            f"{invoice.get('currency_code', 'INR')} {final_total:.2f}"
        ])
    
    # Add totals row
    data.append([
        '',
        '',
        '',
        'Grand Total:',
        f"{invoice.get('currency_code', 'INR')} {invoice.get('grand_total', 0):.2f}"
    ])
    
    # Create and style the table
    table = Table(data, colWidths=[200, 60, 80, 60, 80])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    
    # Add payment info
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph("Payment Information", styles['Heading3']))
    
    # Payment status
    payment_status = "Paid" if invoice.get('balance_due', 0) <= 0 else f"Balance Due: {invoice.get('currency_code', 'INR')} {invoice.get('balance_due', 0):.2f}"
    elements.append(Paragraph(f"Status: {payment_status}", styles['Normal']))
    
    # Payment history if any
    if invoice.get('payments'):
        elements.append(Spacer(1, 0.25*inch))
        elements.append(Paragraph("Payment History:", styles['Normal']))
        
        payment_data = [['Date', 'Method', 'Amount']]
        for payment in invoice.get('payments', []):
            payment_date = payment.get('payment_date', datetime.now()).strftime('%d-%b-%Y') if hasattr(payment.get('payment_date', datetime.now()), 'strftime') else str(payment.get('payment_date', ''))
            payment_method = payment.get('payment_method', 'Unknown')
            amount = float(payment.get('amount', 0))
            
            payment_data.append([
                payment_date,
                payment_method,
                f"{invoice.get('currency_code', 'INR')} {amount:.2f}"
            ])
        
        payment_table = Table(payment_data, colWidths=[100, 100, 100])
        payment_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(payment_table)
    
    # Add footer
    elements.append(Spacer(1, 1*inch))
    elements.append(Paragraph("Thank you for your business!", styles['Center']))
    
    # Build PDF document
    doc.build(elements)
    
    # Return the PDF data
    buffer.seek(0)
    return buffer.getvalue()

def _generate_error_pdf(error_message):
    """
    Generate a simple error PDF.
    
    Args:
        error_message: Error message to include in the PDF
        
    Returns:
        PDF data as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    
    elements = []
    elements.append(Paragraph("Error Generating Invoice PDF", styles['Heading1']))
    elements.append(Paragraph(f"An error occurred: {error_message}", styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def generate_report_pdf(title, content, data_tables=None):
    """
    Generate a generic report PDF.
    
    Args:
        title: Report title
        content: Report content or description
        data_tables: List of dictionaries with table data and headers
        
    Returns:
        PDF data as bytes
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    elements = []
    
    # Add title
    elements.append(Paragraph(title, styles['Heading1']))
    elements.append(Spacer(1, 0.25*inch))
    
    # Add content paragraphs
    if isinstance(content, str):
        elements.append(Paragraph(content, styles['Normal']))
    elif isinstance(content, list):
        for paragraph in content:
            elements.append(Paragraph(paragraph, styles['Normal']))
            elements.append(Spacer(1, 0.1*inch))
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Add data tables if provided
    if data_tables:
        for table_data in data_tables:
            if 'title' in table_data:
                elements.append(Paragraph(table_data['title'], styles['Heading2']))
                elements.append(Spacer(1, 0.2*inch))
            
            if 'headers' in table_data and 'data' in table_data:
                # Create table data with headers
                table_content = [table_data['headers']]
                table_content.extend(table_data['data'])
                
                # Determine column widths
                col_count = len(table_data['headers'])
                col_width = 450 / col_count
                
                # Create table
                table = Table(table_content, colWidths=[col_width] * col_count)
                
                # Style the table
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 0.5*inch))
    
    # Build PDF document
    doc.build(elements)
    
    # Return the PDF data
    buffer.seek(0)
    return buffer.getvalue()