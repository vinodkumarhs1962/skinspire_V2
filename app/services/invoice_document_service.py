# File: app/services/invoice_document_service.py
# Invoice-specific document service for generating and storing invoice PDFs
# Extends existing UniversalDocumentService with invoice-specific functionality

import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from pathlib import Path

from flask import current_app, render_template
from flask_login import current_user

from app.models.transaction import InvoiceHeader, InvoiceDocument
from app.services.database_service import get_db_session
from app.engine.document_service import get_document_service

logger = logging.getLogger(__name__)

class InvoiceDocumentService:
    """
    Service for generating and storing invoice PDFs
    Uses existing UniversalDocumentService for PDF generation
    Adds invoice-specific metadata tracking and storage
    """

    def __init__(self):
        self.document_service = get_document_service()
        self.storage_base_path = self._get_storage_path()

    def _get_storage_path(self) -> Path:
        """Get the base storage path for invoice documents"""
        # Default to app/static/invoice_documents/
        base_path = Path(current_app.root_path) / 'static' / 'invoice_documents'

        # Create directory if it doesn't exist
        base_path.mkdir(parents=True, exist_ok=True)

        return base_path

    def generate_and_store_invoice_pdf(
        self,
        invoice_id: uuid.UUID,
        hospital_id: uuid.UUID,
        user_id: Optional[str] = None,
        trigger: str = 'on_creation'
    ) -> Optional[InvoiceDocument]:
        """
        Generate invoice PDF and store in database with metadata

        Args:
            invoice_id: Invoice UUID
            hospital_id: Hospital UUID
            user_id: User ID who triggered generation
            trigger: What triggered generation (on_creation, manual_regenerate, revision)

        Returns:
            InvoiceDocument record or None if failed
        """
        try:
            with get_db_session() as session:
                # Get invoice header with line items
                invoice = session.query(InvoiceHeader).filter(
                    InvoiceHeader.invoice_id == invoice_id,
                    InvoiceHeader.hospital_id == hospital_id
                ).first()

                if not invoice:
                    logger.error(f"Invoice not found: {invoice_id}")
                    return None

                # Get hospital to check drug license status
                from app.models.master import Hospital
                hospital = session.query(Hospital).filter_by(
                    hospital_id=hospital_id
                ).first()

                if not hospital:
                    logger.error(f"Hospital not found: {hospital_id}")
                    return None

                # Check drug license status (snapshot for this document)
                has_drug_license = self._check_drug_license(hospital)

                # Count prescription items and check if consolidated
                prescription_count = 0
                is_consolidated = False

                for line_item in invoice.line_items:
                    if line_item.is_prescription_item:
                        prescription_count += 1
                        if line_item.print_as_consolidated:
                            is_consolidated = True

                # Generate PDF using existing print template
                pdf_content = self._render_invoice_pdf(invoice_id, hospital_id, session)

                if not pdf_content:
                    logger.error(f"Failed to generate PDF for invoice {invoice_id}")
                    return None

                # Prepare file storage
                file_info = self._prepare_file_storage(
                    invoice=invoice,
                    hospital_id=hospital_id,
                    pdf_content=pdf_content
                )

                # Create InvoiceDocument record
                invoice_doc = InvoiceDocument(
                    hospital_id=hospital_id,
                    branch_id=invoice.branch_id,
                    invoice_id=invoice_id,
                    document_type='invoice_pdf',
                    document_category='billing',
                    document_status='generated',
                    original_filename=file_info['original_filename'],
                    stored_filename=file_info['stored_filename'],
                    file_path=file_info['file_path'],
                    file_size=file_info['file_size'],
                    mime_type='application/pdf',
                    file_extension='pdf',
                    is_original=True,
                    version_number=1,
                    # Snapshot metadata
                    hospital_had_drug_license=has_drug_license,
                    prescription_items_count=prescription_count,
                    consolidated_prescription=is_consolidated,
                    description=f"Invoice {invoice.invoice_number} generated on {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M')}",
                    generation_trigger=trigger,
                    tags=[]
                )

                if user_id:
                    invoice_doc.created_by = user_id

                session.add(invoice_doc)
                session.commit()

                logger.info(f"✅ Generated and stored invoice PDF: {invoice.invoice_number} (document_id: {invoice_doc.document_id})")
                logger.info(f"   Drug License: {has_drug_license}, Rx Items: {prescription_count}, Consolidated: {is_consolidated}")

                return invoice_doc

        except Exception as e:
            logger.error(f"Error generating invoice PDF: {str(e)}", exc_info=True)
            return None

    def _check_drug_license(self, hospital) -> bool:
        """Check if hospital has valid pharmacy registration"""
        if not hospital.pharmacy_registration_number:
            return False

        # Check expiry date if exists
        expiry_field = None
        if hasattr(hospital, 'pharmacy_registration_valid_until'):
            expiry_field = hospital.pharmacy_registration_valid_until
        elif hasattr(hospital, 'pharmacy_reg_valid_until'):
            expiry_field = hospital.pharmacy_reg_valid_until

        if expiry_field:
            from datetime import date
            if expiry_field < date.today():
                return False

        return True

    def _render_invoice_pdf(
        self,
        invoice_id: uuid.UUID,
        hospital_id: uuid.UUID,
        session
    ) -> Optional[bytes]:
        """
        Render invoice as PDF using existing print template

        Returns:
            PDF bytes or None if failed
        """
        try:
            from weasyprint import HTML, CSS
            from app.models.master import Hospital, Branch

            # Get invoice with all relationships
            invoice = session.query(InvoiceHeader).filter(
                InvoiceHeader.invoice_id == invoice_id,
                InvoiceHeader.hospital_id == hospital_id
            ).first()

            if not invoice:
                logger.error(f"Invoice not found: {invoice_id}")
                return None

            # Get hospital information
            hospital = session.query(Hospital).filter_by(
                hospital_id=hospital_id
            ).first()

            if not hospital:
                logger.error(f"Hospital not found: {hospital_id}")
                return None

            # Get branch information
            branch = None
            if invoice.branch_id:
                branch = session.query(Branch).filter_by(
                    branch_id=invoice.branch_id
                ).first()

            # Get hospital logo URL (if exists)
            logo_url = None
            if hasattr(hospital, 'logo_url') and hospital.logo_url:
                logo_url = hospital.logo_url
            elif hasattr(hospital, 'logo_path') and hospital.logo_path:
                # Convert file path to URL if needed
                logo_url = f"/static/logos/{Path(hospital.logo_path).name}"

            # Prepare context for template
            context = {
                'invoice': invoice,
                'hospital': hospital,
                'branch': branch,
                'logo_url': logo_url,
                'current_date': datetime.now(timezone.utc)
            }

            # Render HTML template
            html_string = render_template('billing/print_invoice.html', **context)

            # Convert HTML to PDF using WeasyPrint
            logger.info(f"Converting invoice {invoice.invoice_number} HTML to PDF...")
            pdf_bytes = HTML(string=html_string, base_url=current_app.config.get('BASE_URL', '/')).write_pdf()

            logger.info(f"✅ Successfully generated PDF for invoice {invoice.invoice_number} ({len(pdf_bytes)} bytes)")
            return pdf_bytes

        except ImportError as e:
            logger.error(f"WeasyPrint not available: {str(e)}", exc_info=True)
            logger.error("Install with: pip install WeasyPrint")
            return None
        except Exception as e:
            logger.error(f"Error rendering invoice PDF: {str(e)}", exc_info=True)
            return None

    def _prepare_file_storage(
        self,
        invoice,
        hospital_id: uuid.UUID,
        pdf_content: bytes
    ) -> Dict:
        """
        Prepare file storage location and save PDF

        Returns:
            Dict with file info (original_filename, stored_filename, file_path, file_size)
        """
        # Create directory structure: YYYY/MM/hospital_id/
        now = datetime.now(timezone.utc)
        year_month_path = self.storage_base_path / str(now.year) / f"{now.month:02d}" / str(hospital_id)
        year_month_path.mkdir(parents=True, exist_ok=True)

        # Generate filenames
        invoice_number_safe = invoice.invoice_number.replace('/', '-').replace('\\', '-')
        timestamp = now.strftime('%Y%m%d_%H%M%S')

        original_filename = f"INV-{invoice_number_safe}.pdf"
        stored_filename = f"INV-{invoice_number_safe}_{timestamp}_{uuid.uuid4().hex[:8]}.pdf"

        # Full file path
        file_path = year_month_path / stored_filename

        # Save PDF content
        with open(file_path, 'wb') as f:
            f.write(pdf_content)

        file_size = len(pdf_content)

        # Return relative path for database storage
        relative_path = str(file_path.relative_to(self.storage_base_path))

        return {
            'original_filename': original_filename,
            'stored_filename': stored_filename,
            'file_path': relative_path,
            'file_size': file_size
        }

    def get_latest_invoice_document(
        self,
        invoice_id: uuid.UUID,
        hospital_id: uuid.UUID
    ) -> Optional[InvoiceDocument]:
        """
        Get the latest (most recent) invoice document

        Returns:
            InvoiceDocument or None
        """
        try:
            with get_db_session() as session:
                doc = session.query(InvoiceDocument).filter(
                    InvoiceDocument.invoice_id == invoice_id,
                    InvoiceDocument.hospital_id == hospital_id,
                    InvoiceDocument.is_original == True,
                    InvoiceDocument.document_status != 'superseded'
                ).order_by(InvoiceDocument.created_at.desc()).first()

                return doc

        except Exception as e:
            logger.error(f"Error getting latest invoice document: {str(e)}")
            return None

    def regenerate_invoice_pdf(
        self,
        invoice_id: uuid.UUID,
        hospital_id: uuid.UUID,
        user_id: Optional[str] = None,
        reason: str = 'Manual regeneration'
    ) -> Optional[InvoiceDocument]:
        """
        Regenerate invoice PDF and mark previous version as superseded

        Returns:
            New InvoiceDocument or None
        """
        try:
            with get_db_session() as session:
                # Mark existing document as superseded
                existing_doc = self.get_latest_invoice_document(invoice_id, hospital_id)

                if existing_doc:
                    existing_doc.document_status = 'superseded'
                    session.add(existing_doc)
                    session.commit()

                # Generate new document
                new_doc = self.generate_and_store_invoice_pdf(
                    invoice_id=invoice_id,
                    hospital_id=hospital_id,
                    user_id=user_id,
                    trigger='manual_regenerate'
                )

                if new_doc:
                    new_doc.description = f"{reason} - Previous version superseded"
                    new_doc.parent_document_id = existing_doc.document_id if existing_doc else None
                    new_doc.version_number = (existing_doc.version_number + 1) if existing_doc else 1
                    session.add(new_doc)
                    session.commit()

                return new_doc

        except Exception as e:
            logger.error(f"Error regenerating invoice PDF: {str(e)}", exc_info=True)
            return None


# Singleton instance
_invoice_document_service = None

def get_invoice_document_service() -> InvoiceDocumentService:
    """Get singleton instance of invoice document service"""
    global _invoice_document_service
    if _invoice_document_service is None:
        _invoice_document_service = InvoiceDocumentService()
    return _invoice_document_service
