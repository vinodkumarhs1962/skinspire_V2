"""
Config to Master Sync Service

This service synchronizes currently effective pricing and GST configurations
from entity_pricing_tax_config table to master tables (medicines, services, packages).

Purpose:
- Keep master tables aligned with current effective configs
- Provide fallback data consistency
- Useful for reporting and queries that use master tables directly

Usage:
- Can be run manually via CLI script
- Can be scheduled (daily/weekly)
- Supports dry-run mode for safety
"""

from decimal import Decimal
from datetime import date
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.config import EntityPricingTaxConfig
from app.models.master import Medicine, Service, Package
import logging

logger = logging.getLogger(__name__)


class ConfigMasterSyncResult:
    """Result object for sync operation"""

    def __init__(self):
        self.medicines_updated = 0
        self.services_updated = 0
        self.packages_updated = 0
        self.medicines_skipped = 0
        self.services_skipped = 0
        self.packages_skipped = 0
        self.errors = []
        self.changes = []

    @property
    def total_updated(self):
        return self.medicines_updated + self.services_updated + self.packages_updated

    @property
    def total_skipped(self):
        return self.medicines_skipped + self.services_skipped + self.packages_skipped

    def add_change(self, entity_type: str, entity_id: str, entity_name: str, field: str, old_value, new_value):
        self.changes.append({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_name': entity_name,
            'field': field,
            'old_value': old_value,
            'new_value': new_value
        })

    def add_error(self, entity_type: str, entity_id: str, error: str):
        self.errors.append({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'error': error
        })

    def __repr__(self):
        return (f"<ConfigMasterSyncResult updated={self.total_updated} "
                f"skipped={self.total_skipped} errors={len(self.errors)}>")


def sync_config_to_masters(
    session: Session,
    hospital_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    dry_run: bool = True,
    update_pricing: bool = True,
    update_gst: bool = True,
    current_user_id: Optional[str] = None
) -> ConfigMasterSyncResult:
    """
    Sync currently effective configs from entity_pricing_tax_config to master tables.

    This function:
    1. Finds all currently effective configs (effective_to = NULL or >= today)
    2. Updates corresponding master table records (medicines/services/packages)
    3. Only updates fields that have changed
    4. Logs all changes

    Args:
        session: Database session
        hospital_id: Optional filter by hospital UUID
        entity_type: Optional filter ('medicine', 'service', 'package')
        dry_run: If True, don't commit changes (default: True for safety)
        update_pricing: Update pricing fields (MRP, selling_price, etc.)
        update_gst: Update GST fields (gst_rate, cgst_rate, etc.)
        current_user_id: User triggering the sync

    Returns:
        ConfigMasterSyncResult with details of what was updated

    Example:
        >>> # Dry run first (preview changes)
        >>> result = sync_config_to_masters(session, dry_run=True)
        >>> print(f"Would update {result.total_updated} records")
        >>>
        >>> # Actual sync
        >>> result = sync_config_to_masters(session, dry_run=False)
        >>> session.commit()
    """

    result = ConfigMasterSyncResult()

    logger.info(f"Starting config to master sync: hospital_id={hospital_id}, "
               f"entity_type={entity_type}, dry_run={dry_run}")

    # Build base query for currently effective configs
    today = date.today()
    query = session.query(EntityPricingTaxConfig).filter(
        and_(
            EntityPricingTaxConfig.effective_from <= today,
            or_(
                EntityPricingTaxConfig.effective_to == None,
                EntityPricingTaxConfig.effective_to >= today
            ),
            EntityPricingTaxConfig.is_deleted == False
        )
    )

    # Apply filters
    if hospital_id:
        query = query.filter(EntityPricingTaxConfig.hospital_id == hospital_id)

    if entity_type:
        entity_id_column = f"{entity_type}_id"
        query = query.filter(getattr(EntityPricingTaxConfig, entity_id_column) != None)

    configs = query.all()

    logger.info(f"Found {len(configs)} currently effective configs to process")

    # Process each config
    for config in configs:
        try:
            if config.medicine_id:
                _sync_medicine(session, config, result, dry_run, update_pricing, update_gst, current_user_id)
            elif config.service_id:
                _sync_service(session, config, result, dry_run, update_pricing, update_gst, current_user_id)
            elif config.package_id:
                _sync_package(session, config, result, dry_run, update_pricing, update_gst, current_user_id)
        except Exception as e:
            logger.error(f"Error syncing config {config.config_id}: {str(e)}", exc_info=True)
            result.add_error(
                config.entity_type,
                str(config.entity_id),
                str(e)
            )

    # Log summary
    logger.info(f"Sync complete: {result.total_updated} updated, "
               f"{result.total_skipped} skipped, {len(result.errors)} errors")

    if dry_run:
        logger.warning("DRY RUN MODE - No changes committed")

    return result


def _sync_medicine(
    session: Session,
    config: EntityPricingTaxConfig,
    result: ConfigMasterSyncResult,
    dry_run: bool,
    update_pricing: bool,
    update_gst: bool,
    current_user_id: Optional[str]
):
    """Sync config to medicine master"""

    medicine = session.query(Medicine).filter_by(medicine_id=config.medicine_id).first()

    if not medicine:
        logger.warning(f"Medicine {config.medicine_id} not found in master - skipping")
        result.medicines_skipped += 1
        return

    changes_made = False

    # Update pricing fields
    if update_pricing:
        if config.mrp is not None and medicine.mrp != config.mrp:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'mrp', medicine.mrp, config.mrp)
            if not dry_run:
                medicine.mrp = config.mrp
            changes_made = True

        if config.selling_price is not None and medicine.selling_price != config.selling_price:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'selling_price', medicine.selling_price, config.selling_price)
            if not dry_run:
                medicine.selling_price = config.selling_price
            changes_made = True

        if config.cost_price is not None and medicine.cost_price != config.cost_price:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'cost_price', medicine.cost_price, config.cost_price)
            if not dry_run:
                medicine.cost_price = config.cost_price
            changes_made = True

    # Update GST fields
    if update_gst:
        if config.gst_rate is not None and medicine.gst_rate != config.gst_rate:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'gst_rate', medicine.gst_rate, config.gst_rate)
            if not dry_run:
                medicine.gst_rate = config.gst_rate
            changes_made = True

        if config.cgst_rate is not None and medicine.cgst_rate != config.cgst_rate:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'cgst_rate', medicine.cgst_rate, config.cgst_rate)
            if not dry_run:
                medicine.cgst_rate = config.cgst_rate
            changes_made = True

        if config.sgst_rate is not None and medicine.sgst_rate != config.sgst_rate:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'sgst_rate', medicine.sgst_rate, config.sgst_rate)
            if not dry_run:
                medicine.sgst_rate = config.sgst_rate
            changes_made = True

        if config.igst_rate is not None and medicine.igst_rate != config.igst_rate:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'igst_rate', medicine.igst_rate, config.igst_rate)
            if not dry_run:
                medicine.igst_rate = config.igst_rate
            changes_made = True

        if config.is_gst_exempt is not None and medicine.is_gst_exempt != config.is_gst_exempt:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'is_gst_exempt', medicine.is_gst_exempt, config.is_gst_exempt)
            if not dry_run:
                medicine.is_gst_exempt = config.is_gst_exempt
            changes_made = True

        if config.gst_inclusive is not None and medicine.gst_inclusive != config.gst_inclusive:
            result.add_change('medicine', str(medicine.medicine_id), medicine.medicine_name,
                            'gst_inclusive', medicine.gst_inclusive, config.gst_inclusive)
            if not dry_run:
                medicine.gst_inclusive = config.gst_inclusive
            changes_made = True

    if changes_made:
        result.medicines_updated += 1
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Updated medicine: {medicine.medicine_name}")
    else:
        result.medicines_skipped += 1


def _sync_service(
    session: Session,
    config: EntityPricingTaxConfig,
    result: ConfigMasterSyncResult,
    dry_run: bool,
    update_pricing: bool,
    update_gst: bool,
    current_user_id: Optional[str]
):
    """Sync config to service master"""

    service = session.query(Service).filter_by(service_id=config.service_id).first()

    if not service:
        logger.warning(f"Service {config.service_id} not found in master - skipping")
        result.services_skipped += 1
        return

    changes_made = False

    # Update pricing
    if update_pricing and config.service_price is not None:
        if service.price != config.service_price:
            result.add_change('service', str(service.service_id), service.service_name,
                            'price', service.price, config.service_price)
            if not dry_run:
                service.price = config.service_price
            changes_made = True

    # Update GST fields
    if update_gst:
        if config.gst_rate is not None and service.gst_rate != config.gst_rate:
            result.add_change('service', str(service.service_id), service.service_name,
                            'gst_rate', service.gst_rate, config.gst_rate)
            if not dry_run:
                service.gst_rate = config.gst_rate
            changes_made = True

        if config.cgst_rate is not None and service.cgst_rate != config.cgst_rate:
            result.add_change('service', str(service.service_id), service.service_name,
                            'cgst_rate', service.cgst_rate, config.cgst_rate)
            if not dry_run:
                service.cgst_rate = config.cgst_rate
            changes_made = True

        if config.sgst_rate is not None and service.sgst_rate != config.sgst_rate:
            result.add_change('service', str(service.service_id), service.service_name,
                            'sgst_rate', service.sgst_rate, config.sgst_rate)
            if not dry_run:
                service.sgst_rate = config.sgst_rate
            changes_made = True

        if config.igst_rate is not None and service.igst_rate != config.igst_rate:
            result.add_change('service', str(service.service_id), service.service_name,
                            'igst_rate', service.igst_rate, config.igst_rate)
            if not dry_run:
                service.igst_rate = config.igst_rate
            changes_made = True

        if config.is_gst_exempt is not None and service.is_gst_exempt != config.is_gst_exempt:
            result.add_change('service', str(service.service_id), service.service_name,
                            'is_gst_exempt', service.is_gst_exempt, config.is_gst_exempt)
            if not dry_run:
                service.is_gst_exempt = config.is_gst_exempt
            changes_made = True

    if changes_made:
        result.services_updated += 1
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Updated service: {service.service_name}")
    else:
        result.services_skipped += 1


def _sync_package(
    session: Session,
    config: EntityPricingTaxConfig,
    result: ConfigMasterSyncResult,
    dry_run: bool,
    update_pricing: bool,
    update_gst: bool,
    current_user_id: Optional[str]
):
    """Sync config to package master"""

    package = session.query(Package).filter_by(package_id=config.package_id).first()

    if not package:
        logger.warning(f"Package {config.package_id} not found in master - skipping")
        result.packages_skipped += 1
        return

    changes_made = False

    # Update pricing
    if update_pricing and config.package_price is not None:
        if package.price != config.package_price:
            result.add_change('package', str(package.package_id), package.package_name,
                            'price', package.price, config.package_price)
            if not dry_run:
                package.price = config.package_price
            changes_made = True

    # Update GST fields
    if update_gst:
        if config.gst_rate is not None and package.gst_rate != config.gst_rate:
            result.add_change('package', str(package.package_id), package.package_name,
                            'gst_rate', package.gst_rate, config.gst_rate)
            if not dry_run:
                package.gst_rate = config.gst_rate
            changes_made = True

        if config.cgst_rate is not None and package.cgst_rate != config.cgst_rate:
            result.add_change('package', str(package.package_id), package.package_name,
                            'cgst_rate', package.cgst_rate, config.cgst_rate)
            if not dry_run:
                package.cgst_rate = config.cgst_rate
            changes_made = True

        if config.sgst_rate is not None and package.sgst_rate != config.sgst_rate:
            result.add_change('package', str(package.package_id), package.package_name,
                            'sgst_rate', package.sgst_rate, config.sgst_rate)
            if not dry_run:
                package.sgst_rate = config.sgst_rate
            changes_made = True

        if config.igst_rate is not None and package.igst_rate != config.igst_rate:
            result.add_change('package', str(package.package_id), package.package_name,
                            'igst_rate', package.igst_rate, config.igst_rate)
            if not dry_run:
                package.igst_rate = config.igst_rate
            changes_made = True

        if config.is_gst_exempt is not None and package.is_gst_exempt != config.is_gst_exempt:
            result.add_change('package', str(package.package_id), package.package_name,
                            'is_gst_exempt', package.is_gst_exempt, config.is_gst_exempt)
            if not dry_run:
                package.is_gst_exempt = config.is_gst_exempt
            changes_made = True

    if changes_made:
        result.packages_updated += 1
        logger.info(f"{'[DRY RUN] ' if dry_run else ''}Updated package: {package.package_name}")
    else:
        result.packages_skipped += 1


def generate_sync_report(result: ConfigMasterSyncResult, format: str = 'text') -> str:
    """
    Generate a human-readable report of sync results.

    Args:
        result: ConfigMasterSyncResult object
        format: 'text' or 'html'

    Returns:
        Formatted report string
    """

    if format == 'html':
        return _generate_html_report(result)
    else:
        return _generate_text_report(result)


def _generate_text_report(result: ConfigMasterSyncResult) -> str:
    """Generate text report"""

    lines = []
    lines.append("=" * 70)
    lines.append("CONFIG TO MASTER SYNC REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Summary
    lines.append("SUMMARY:")
    lines.append(f"  Medicines Updated: {result.medicines_updated}")
    lines.append(f"  Services Updated:  {result.services_updated}")
    lines.append(f"  Packages Updated:  {result.packages_updated}")
    lines.append(f"  Total Updated:     {result.total_updated}")
    lines.append("")
    lines.append(f"  Medicines Skipped: {result.medicines_skipped}")
    lines.append(f"  Services Skipped:  {result.services_skipped}")
    lines.append(f"  Packages Skipped:  {result.packages_skipped}")
    lines.append(f"  Total Skipped:     {result.total_skipped}")
    lines.append("")
    lines.append(f"  Errors:            {len(result.errors)}")
    lines.append("")

    # Changes
    if result.changes:
        lines.append("CHANGES:")
        lines.append("-" * 70)
        for change in result.changes:
            lines.append(f"  {change['entity_type'].upper()}: {change['entity_name']}")
            lines.append(f"    Field: {change['field']}")
            lines.append(f"    Old:   {change['old_value']}")
            lines.append(f"    New:   {change['new_value']}")
            lines.append("")

    # Errors
    if result.errors:
        lines.append("ERRORS:")
        lines.append("-" * 70)
        for error in result.errors:
            lines.append(f"  {error['entity_type'].upper()} {error['entity_id']}: {error['error']}")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def _generate_html_report(result: ConfigMasterSyncResult) -> str:
    """Generate HTML report"""

    html = f"""
    <html>
    <head>
        <title>Config to Master Sync Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            .summary {{ background-color: #f9f9f9; padding: 15px; margin: 20px 0; }}
            .error {{ color: red; }}
        </style>
    </head>
    <body>
        <h1>Config to Master Sync Report</h1>

        <div class="summary">
            <h2>Summary</h2>
            <p><strong>Total Updated:</strong> {result.total_updated}</p>
            <ul>
                <li>Medicines: {result.medicines_updated}</li>
                <li>Services: {result.services_updated}</li>
                <li>Packages: {result.packages_updated}</li>
            </ul>
            <p><strong>Total Skipped:</strong> {result.total_skipped}</p>
            <p><strong>Errors:</strong> {len(result.errors)}</p>
        </div>

        <h2>Changes</h2>
        <table>
            <tr>
                <th>Entity Type</th>
                <th>Entity Name</th>
                <th>Field</th>
                <th>Old Value</th>
                <th>New Value</th>
            </tr>
    """

    for change in result.changes:
        html += f"""
            <tr>
                <td>{change['entity_type']}</td>
                <td>{change['entity_name']}</td>
                <td>{change['field']}</td>
                <td>{change['old_value']}</td>
                <td>{change['new_value']}</td>
            </tr>
        """

    html += """
        </table>
    </body>
    </html>
    """

    return html
