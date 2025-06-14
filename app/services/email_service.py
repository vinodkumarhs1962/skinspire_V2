"""
Email service for sending email messages
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import current_app

logger = logging.getLogger(__name__)

def send_email(recipient_email, subject, body, html_body=None):
    """
    Send an email to the specified recipient.
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject
        body: Email text body
        html_body: Optional HTML body
        
    Returns:
        Boolean indicating success
    """
    try:
        # Get SMTP settings from config
        smtp_host = current_app.config.get('SMTP_HOST', 'localhost')
        smtp_port = current_app.config.get('SMTP_PORT', 25)
        smtp_user = current_app.config.get('SMTP_USER')
        smtp_pass = current_app.config.get('SMTP_PASS')
        smtp_from = current_app.config.get('SMTP_FROM', 'no-reply@example.com')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = smtp_from
        msg['To'] = recipient_email
        
        # Add text body
        msg.attach(MIMEText(body, 'plain'))
        
        # Add HTML body if provided
        if html_body:
            msg.attach(MIMEText(html_body, 'html'))
        
        # Connect to SMTP server
        if smtp_user and smtp_pass:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            server.login(smtp_user, smtp_pass)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
        
        # Send email
        server.sendmail(smtp_from, recipient_email, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent to {recipient_email}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email: {str(e)}", exc_info=True)
        return False

def send_email_with_attachment(recipient_email, subject, body, attachment_data, attachment_name, attachment_type='application/pdf'):
    """
    Send an email with attachment to the specified recipient.
    
    Args:
        recipient_email: Email address of the recipient
        subject: Email subject
        body: Email text body
        attachment_data: Binary attachment data
        attachment_name: Name of the attachment
        attachment_type: MIME type of the attachment
        
    Returns:
        Boolean indicating success
    """
    try:
        # Get SMTP settings from config
        smtp_host = current_app.config.get('SMTP_HOST', 'localhost')
        smtp_port = current_app.config.get('SMTP_PORT', 25)
        smtp_user = current_app.config.get('SMTP_USER')
        smtp_pass = current_app.config.get('SMTP_PASS')
        smtp_from = current_app.config.get('SMTP_FROM', 'no-reply@example.com')
        
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = smtp_from
        msg['To'] = recipient_email
        
        # Add text body
        msg.attach(MIMEText(body, 'plain'))
        
        # Add attachment
        attachment = MIMEApplication(attachment_data)
        attachment.add_header('Content-Disposition', 'attachment', filename=attachment_name)
        msg.attach(attachment)
        
        # Connect to SMTP server
        if smtp_user and smtp_pass:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            server.login(smtp_user, smtp_pass)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
        
        # Send email
        server.sendmail(smtp_from, recipient_email, msg.as_string())
        server.quit()
        
        logger.info(f"Email with attachment sent to {recipient_email}: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending email with attachment: {str(e)}", exc_info=True)
        return False