"""
Promotion Dashboard Service
Handles all business logic for the Promotions Dashboard including:
- Timeline data aggregation
- Campaign CRUD operations
- Bulk/Loyalty configuration management
- Promotion simulation
- Analytics and reporting
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, text, case
import logging
import uuid

logger = logging.getLogger(__name__)

from app.models.master import (
    Hospital, Service, Medicine, Package, LoyaltyCardType,
    PromotionCampaign, PromotionUsageLog, DiscountApplicationLog, Patient,
    PromotionCampaignGroup, PromotionGroupItem
)
from app.models.transaction import PatientLoyaltyWallet
from app.services.database_service import get_db_session
from app.services.discount_service import DiscountService, DiscountCalculationResult


class PromotionDashboardService:
    """Service class for Promotions Dashboard operations"""

    # ==========================================================================
    # DASHBOARD SUMMARY
    # ==========================================================================

    @staticmethod
    def get_dashboard_summary(hospital_id: str) -> Dict[str, Any]:
        """
        Get summary cards data for dashboard

        Returns:
            Dictionary with summary metrics
        """
        try:
            with get_db_session(read_only=True) as session:
                today = date.today()
                month_start = today.replace(day=1)
                week_ahead = today + timedelta(days=7)

                # Active campaigns count (approved, active, and valid - not expired)
                # Includes both currently running AND starting soon campaigns
                active_campaigns = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.status == 'approved',
                    PromotionCampaign.end_date >= today  # Not expired
                ).scalar() or 0

                # Draft campaigns count (not yet submitted for approval)
                draft_campaigns = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.status == 'draft'
                ).scalar() or 0

                # Pending approval count
                pending_approval = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.status == 'pending_approval'
                ).scalar() or 0

                # Total discount given this month
                total_discount_mtd = session.query(func.coalesce(func.sum(PromotionUsageLog.discount_amount), 0)).filter(
                    PromotionUsageLog.hospital_id == hospital_id,
                    PromotionUsageLog.usage_date >= month_start
                ).scalar() or Decimal('0')

                # Most used campaign this month
                most_used_subq = session.query(
                    PromotionUsageLog.campaign_id,
                    func.count(PromotionUsageLog.usage_id).label('usage_count')
                ).filter(
                    PromotionUsageLog.hospital_id == hospital_id,
                    PromotionUsageLog.usage_date >= month_start
                ).group_by(PromotionUsageLog.campaign_id).order_by(
                    func.count(PromotionUsageLog.usage_id).desc()
                ).first()

                most_used = {'name': 'N/A', 'uses': 0}
                if most_used_subq:
                    campaign = session.query(PromotionCampaign).filter_by(
                        campaign_id=most_used_subq[0]
                    ).first()
                    if campaign:
                        most_used = {
                            'name': campaign.campaign_code or campaign.campaign_name,
                            'uses': most_used_subq[1]
                        }

                # Fallback: if no usage data, show first active approved campaign
                if most_used['name'] == 'N/A':
                    first_active = session.query(PromotionCampaign).filter(
                        PromotionCampaign.hospital_id == hospital_id,
                        PromotionCampaign.is_active == True,
                        PromotionCampaign.is_deleted.is_(False),
                        PromotionCampaign.status == 'approved',
                        PromotionCampaign.start_date <= today,
                        PromotionCampaign.end_date >= today
                    ).order_by(PromotionCampaign.start_date.desc()).first()
                    if first_active:
                        most_used = {
                            'name': first_active.campaign_code or first_active.campaign_name,
                            'uses': first_active.current_uses or 0
                        }

                # Upcoming campaigns (starting in next 7 days, only approved)
                upcoming = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.status == 'approved',
                    PromotionCampaign.start_date > today,
                    PromotionCampaign.start_date <= week_ahead
                ).scalar() or 0

                # Expiring soon (ending in next 7 days, only approved)
                expiring_soon = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.status == 'approved',
                    PromotionCampaign.end_date >= today,
                    PromotionCampaign.end_date <= week_ahead
                ).scalar() or 0

                # Get bulk discount status
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                bulk_enabled = hospital.bulk_discount_enabled if hospital else False
                loyalty_mode = hospital.loyalty_discount_mode if hospital else 'absolute'

                # Count active loyalty card types
                active_card_types = session.query(func.count(LoyaltyCardType.card_type_id)).filter(
                    LoyaltyCardType.hospital_id == hospital_id,
                    LoyaltyCardType.is_active == True,
                    LoyaltyCardType.is_deleted == False
                ).scalar() or 0

                return {
                    'active_campaigns': active_campaigns,
                    'draft_campaigns': draft_campaigns,
                    'pending_approval': pending_approval,
                    'total_discount_mtd': float(total_discount_mtd),
                    'most_used': most_used,
                    'upcoming': upcoming,
                    'expiring_soon': expiring_soon,
                    'bulk_enabled': bulk_enabled,
                    'loyalty_mode': loyalty_mode,
                    'active_card_types': active_card_types
                }

        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}")
            return {
                'active_campaigns': 0,
                'draft_campaigns': 0,
                'pending_approval': 0,
                'total_discount_mtd': 0,
                'most_used': {'name': 'N/A', 'uses': 0},
                'upcoming': 0,
                'expiring_soon': 0,
                'bulk_enabled': False,
                'loyalty_mode': 'absolute',
                'active_card_types': 0
            }

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    @staticmethod
    def deactivate_expired_campaigns(hospital_id: str) -> int:
        """
        Deactivate campaigns that have passed their end_date.

        This should be called periodically (e.g., on dashboard load) to ensure
        expired campaigns are automatically marked as inactive.

        Args:
            hospital_id: Hospital ID

        Returns:
            Number of campaigns deactivated
        """
        try:
            with get_db_session() as session:
                today = date.today()

                # Find active campaigns that have expired
                expired_campaigns = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.end_date < today
                ).all()

                count = 0
                for campaign in expired_campaigns:
                    campaign.is_active = False
                    logger.info(f"Auto-deactivated expired campaign: {campaign.campaign_code} (ended {campaign.end_date})")
                    count += 1

                if count > 0:
                    session.commit()
                    logger.info(f"Deactivated {count} expired campaign(s) for hospital {hospital_id}")

                return count

        except Exception as e:
            logger.error(f"Error deactivating expired campaigns: {e}")
            return 0

    @staticmethod
    def _get_group_names_by_ids(session: Session, group_ids: List[str]) -> List[str]:
        """
        Get campaign group names from group IDs

        Args:
            session: Database session
            group_ids: List of group IDs

        Returns:
            List of group names
        """
        if not group_ids:
            return []
        try:
            groups = session.query(PromotionCampaignGroup.group_name).filter(
                PromotionCampaignGroup.group_id.in_(group_ids)
            ).all()
            return [g.group_name for g in groups]
        except Exception as e:
            logger.error(f"Error getting group names: {e}")
            return []

    @staticmethod
    def _get_group_details_by_ids(session: Session, group_ids: List[str]) -> List[Dict]:
        """
        Get campaign group details (id, code, name) from group IDs

        Args:
            session: Database session
            group_ids: List of group IDs

        Returns:
            List of group dictionaries with id, code, name
        """
        if not group_ids:
            return []
        try:
            groups = session.query(
                PromotionCampaignGroup.group_id,
                PromotionCampaignGroup.group_code,
                PromotionCampaignGroup.group_name
            ).filter(
                PromotionCampaignGroup.group_id.in_(group_ids)
            ).all()
            return [
                {'group_id': str(g.group_id), 'group_code': g.group_code, 'group_name': g.group_name}
                for g in groups
            ]
        except Exception as e:
            logger.error(f"Error getting group details: {e}")
            return []

    @staticmethod
    def _enrich_campaign_with_group_names(session: Session, campaign_dict: Dict) -> Dict:
        """
        Enrich campaign dictionary with target_group_names and target_group_details

        Args:
            session: Database session
            campaign_dict: Campaign dictionary

        Returns:
            Enriched campaign dictionary
        """
        target_groups = campaign_dict.get('target_groups')
        if target_groups and target_groups.get('group_ids'):
            group_ids = target_groups['group_ids']
            group_details = PromotionDashboardService._get_group_details_by_ids(session, group_ids)
            campaign_dict['target_group_names'] = [g['group_name'] for g in group_details]
            campaign_dict['target_group_details'] = group_details
        else:
            campaign_dict['target_group_names'] = []
            campaign_dict['target_group_details'] = []
        return campaign_dict

    # ==========================================================================
    # TIMELINE DATA
    # ==========================================================================

    @staticmethod
    def get_timeline_data(
        hospital_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get all promotion data for timeline visualization

        Args:
            hospital_id: Hospital ID
            start_date: Timeline start date
            end_date: Timeline end date

        Returns:
            Dictionary with campaigns, bulk config, loyalty periods, and overlaps
        """
        try:
            with get_db_session(read_only=True) as session:
                # Get campaigns in range
                campaigns = PromotionDashboardService._get_campaign_timeline(
                    session, hospital_id, start_date, end_date
                )

                # Get bulk discount configuration
                bulk_config = PromotionDashboardService._get_bulk_timeline(
                    session, hospital_id
                )

                # Get loyalty card types
                loyalty_periods = PromotionDashboardService._get_loyalty_timeline(
                    session, hospital_id
                )

                # Detect overlapping campaigns
                overlaps = PromotionDashboardService._detect_overlaps(
                    campaigns
                )

                return {
                    'campaigns': campaigns,
                    'bulk_config': bulk_config,
                    'loyalty_periods': loyalty_periods,
                    'overlaps': overlaps,
                    'timeline_start': start_date.isoformat(),
                    'timeline_end': end_date.isoformat()
                }

        except Exception as e:
            logger.error(f"Error getting timeline data: {e}")
            return {
                'campaigns': [],
                'bulk_config': None,
                'loyalty_periods': [],
                'overlaps': [],
                'error': str(e)
            }

    @staticmethod
    def _get_campaign_timeline(
        session: Session,
        hospital_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get campaigns that fall within the timeline range"""
        campaigns = session.query(PromotionCampaign).filter(
            PromotionCampaign.hospital_id == hospital_id,
            PromotionCampaign.is_deleted.is_(False),
            # Campaigns that overlap with the date range
            or_(
                and_(PromotionCampaign.start_date >= start_date, PromotionCampaign.start_date <= end_date),
                and_(PromotionCampaign.end_date >= start_date, PromotionCampaign.end_date <= end_date),
                and_(PromotionCampaign.start_date <= start_date, PromotionCampaign.end_date >= end_date)
            )
        ).order_by(PromotionCampaign.start_date).all()

        items = []
        for c in campaigns:
            campaign_dict = {
                'campaign_id': str(c.campaign_id),
                'campaign_code': c.campaign_code,
                'campaign_name': c.campaign_name,
                'promotion_type': c.promotion_type,
                'discount_type': c.discount_type,
                'discount_value': float(c.discount_value) if c.discount_value else 0,
                'start_date': c.start_date.isoformat() if c.start_date else None,
                'end_date': c.end_date.isoformat() if c.end_date else None,
                'is_active': c.is_active,
                'is_personalized': c.is_personalized,
                'target_special_group': getattr(c, 'target_special_group', False) or False,
                'target_groups': c.target_groups,
                'applies_to': c.applies_to,
                'status': getattr(c, 'status', 'approved'),  # Approval status for drag restriction
                'current_uses': c.current_uses or 0,
                'max_total_uses': c.max_total_uses
            }
            # Enrich with group names
            PromotionDashboardService._enrich_campaign_with_group_names(session, campaign_dict)
            items.append(campaign_dict)

        return items

    @staticmethod
    def _get_bulk_timeline(session: Session, hospital_id: str) -> Optional[Dict]:
        """Get bulk discount configuration for timeline"""
        hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

        if not hospital:
            return None

        return {
            'enabled': hospital.bulk_discount_enabled,
            'min_count': hospital.bulk_discount_min_service_count,
            'min_service_count': hospital.bulk_discount_min_service_count,  # Alias for JS compatibility
            'effective_from': hospital.bulk_discount_effective_from.isoformat() if hospital.bulk_discount_effective_from else None,
            'stacking_mode': hospital.loyalty_discount_mode or 'absolute'
        }

    @staticmethod
    def _get_loyalty_timeline(session: Session, hospital_id: str) -> List[Dict]:
        """Get loyalty card types for timeline"""
        card_types = session.query(LoyaltyCardType).filter(
            LoyaltyCardType.hospital_id == hospital_id,
            LoyaltyCardType.is_active == True,
            LoyaltyCardType.is_deleted == False
        ).order_by(LoyaltyCardType.discount_percent.desc()).all()

        return [
            {
                'card_type_id': str(ct.card_type_id),
                'card_type_name': ct.card_type_name,
                'discount_percent': float(ct.discount_percent) if ct.discount_percent else 0,
                'is_active': ct.is_active
            }
            for ct in card_types
        ]

    @staticmethod
    def _detect_overlaps(campaigns: List[Dict]) -> List[Dict]:
        """
        Detect overlapping campaigns that target the same items

        Returns list of overlap warnings
        """
        overlaps = []

        for i, c1 in enumerate(campaigns):
            for c2 in campaigns[i + 1:]:
                # Check if they overlap in time
                c1_start = date.fromisoformat(c1['start_date']) if c1['start_date'] else None
                c1_end = date.fromisoformat(c1['end_date']) if c1['end_date'] else None
                c2_start = date.fromisoformat(c2['start_date']) if c2['start_date'] else None
                c2_end = date.fromisoformat(c2['end_date']) if c2['end_date'] else None

                if not all([c1_start, c1_end, c2_start, c2_end]):
                    continue

                # Check temporal overlap
                if c1_start <= c2_end and c2_start <= c1_end:
                    # Check target overlap
                    targets_overlap = (
                        c1['applies_to'] == 'all' or
                        c2['applies_to'] == 'all' or
                        c1['applies_to'] == c2['applies_to']
                    )

                    if targets_overlap:
                        overlap_start = max(c1_start, c2_start)
                        overlap_end = min(c1_end, c2_end)

                        overlaps.append({
                            'campaign_1': {
                                'id': c1['campaign_id'],
                                'code': c1['campaign_code'],
                                'name': c1['campaign_name']
                            },
                            'campaign_2': {
                                'id': c2['campaign_id'],
                                'code': c2['campaign_code'],
                                'name': c2['campaign_name']
                            },
                            'overlap_start': overlap_start.isoformat(),
                            'overlap_end': overlap_end.isoformat(),
                            'severity': 'warning' if c1['applies_to'] != c2['applies_to'] else 'high',
                            'message': f"'{c1['campaign_code']}' and '{c2['campaign_code']}' overlap from {overlap_start} to {overlap_end}"
                        })

        return overlaps

    # ==========================================================================
    # APPLICABLE CAMPAIGNS FILTER
    # ==========================================================================

    @staticmethod
    def get_applicable_campaigns(
        hospital_id: str,
        patient_id: Optional[str] = None,
        service_id: Optional[str] = None,
        medicine_id: Optional[str] = None,
        package_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get applicable campaigns and discounts for a specific patient/service/medicine selection.

        Filtering rules:
        - Patient selected: Show only applicable loyalty cards, filter VIP campaigns by patient status
        - Service/Medicine selected: Show only campaigns applicable to that item type
        - Both selected: Apply all filters

        Args:
            hospital_id: Hospital ID
            patient_id: Optional patient UUID to check loyalty discounts and VIP status
            service_id: Optional service UUID to filter campaigns
            medicine_id: Optional medicine UUID to filter campaigns

        Returns:
            Dictionary with:
                - campaigns: List of applicable campaign dicts
                - applicable_discounts: Dict with bulk, loyalty, and campaign discount details
                - patient_context: Patient's VIP status and loyalty info
        """
        try:
            with get_db_session(read_only=True) as session:
                today = date.today()

                # =============================================================
                # PATIENT CONTEXT - Get VIP status and loyalty card info
                # =============================================================
                patient_context = {
                    'patient_id': patient_id,
                    'is_special_group': False,
                    'has_loyalty_card': False,
                    'loyalty_card_valid': False
                }

                patient = None
                if patient_id:
                    patient = session.query(Patient).filter_by(patient_id=patient_id).first()
                    if patient:
                        patient_context['is_special_group'] = getattr(patient, 'is_special_group', False) or False
                        patient_context['patient_name'] = patient.full_name or f"{patient.first_name} {patient.last_name}"

                # =============================================================
                # CAMPAIGN FILTERING
                # =============================================================
                # Base campaign query - active AND approved campaigns within date range
                query = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.status == 'approved',
                    PromotionCampaign.start_date <= today,
                    PromotionCampaign.end_date >= today
                )

                # Determine item type and id for filtering
                item_type = None
                item_id = None
                item_name = None

                # Track bulk eligibility info for item context
                item_bulk_eligible = False
                item_bulk_percent = 0
                item_standard_percent = 0

                if service_id:
                    item_type = 'services'
                    item_id = service_id
                    service = session.query(Service).filter_by(service_id=service_id).first()
                    if service:
                        item_name = service.service_name
                        item_bulk_eligible = getattr(service, 'bulk_discount_eligible', False) or False
                        item_bulk_percent = float(service.bulk_discount_percent) if service.bulk_discount_percent else 0
                        item_standard_percent = float(service.standard_discount_percent) if service.standard_discount_percent else 0
                elif medicine_id:
                    item_type = 'medicines'
                    item_id = medicine_id
                    medicine = session.query(Medicine).filter_by(medicine_id=medicine_id).first()
                    if medicine:
                        item_name = medicine.medicine_name
                        item_bulk_eligible = getattr(medicine, 'bulk_discount_eligible', False) or False
                        item_bulk_percent = float(medicine.bulk_discount_percent) if medicine.bulk_discount_percent else 0
                        item_standard_percent = 0  # Medicines may not have standard discount
                elif package_id:
                    item_type = 'packages'
                    item_id = package_id
                    package = session.query(Package).filter_by(package_id=package_id).first()
                    if package:
                        item_name = package.package_name
                        item_bulk_eligible = False  # Packages don't have bulk discount
                        item_bulk_percent = 0
                        item_standard_percent = 0

                # Filter campaigns by item applicability
                if item_type:
                    campaigns = query.filter(
                        or_(
                            PromotionCampaign.applies_to == 'all',
                            PromotionCampaign.applies_to == item_type
                        )
                    ).all()

                    # Further filter by specific_items if present
                    filtered_campaigns = []
                    for c in campaigns:
                        if c.specific_items and isinstance(c.specific_items, list):
                            if item_id and str(item_id) in [str(i) for i in c.specific_items]:
                                filtered_campaigns.append(c)
                        else:
                            filtered_campaigns.append(c)
                    campaigns = filtered_campaigns

                    # Further filter by target_groups (item groups) if present
                    # Campaigns with target_groups should only apply if item is in one of those groups
                    group_filtered_campaigns = []
                    for c in campaigns:
                        target_groups = c.target_groups
                        if target_groups and target_groups.get('group_ids'):
                            # Campaign targets specific item groups - check if item is in any group
                            group_ids = target_groups['group_ids']
                            item_in_group = session.query(PromotionGroupItem).filter(
                                PromotionGroupItem.group_id.in_(group_ids),
                                PromotionGroupItem.item_type == item_type.rstrip('s'),  # 'services' -> 'service'
                                PromotionGroupItem.item_id == item_id
                            ).first() is not None
                            if item_in_group:
                                group_filtered_campaigns.append(c)
                            # If item not in target group, skip this campaign
                        else:
                            # No target groups - campaign applies to all items
                            group_filtered_campaigns.append(c)
                    campaigns = group_filtered_campaigns
                else:
                    campaigns = query.all()

                # Filter campaigns by VIP targeting (if patient selected)
                # Also filter personalized campaigns (they require manual code entry)
                final_filtered_campaigns = []
                for c in campaigns:
                    # Check VIP targeting
                    target_special = getattr(c, 'target_special_group', False) or False
                    if target_special:
                        # VIP-only campaign - only include if patient is VIP
                        if patient_id and not patient_context['is_special_group']:
                            continue  # Skip - patient is not VIP
                        elif not patient_id:
                            # No patient selected - include VIP campaigns (general view)
                            pass

                    # Check personalized campaigns
                    is_personalized = getattr(c, 'is_personalized', False) or False
                    if is_personalized:
                        # Personalized campaigns require manual code entry
                        # In filter view, we show them but mark them clearly
                        # They won't auto-apply but patient can enter code
                        pass  # Include but with is_personalized flag

                    final_filtered_campaigns.append(c)
                campaigns = final_filtered_campaigns

                # Build campaign list
                campaign_list = [
                    {
                        'campaign_id': str(c.campaign_id),
                        'campaign_code': c.campaign_code,
                        'campaign_name': c.campaign_name,
                        'promotion_type': c.promotion_type,
                        'discount_type': c.discount_type,
                        'discount_value': float(c.discount_value) if c.discount_value else 0,
                        'start_date': c.start_date.isoformat() if c.start_date else None,
                        'end_date': c.end_date.isoformat() if c.end_date else None,
                        'is_active': c.is_active,
                        'is_personalized': c.is_personalized,
                        'target_special_group': getattr(c, 'target_special_group', False) or False,
                        'target_groups': c.target_groups,
                        'applies_to': c.applies_to,
                        'auto_apply': c.auto_apply
                    }
                    for c in campaigns
                ]

                # =============================================================
                # BULK DISCOUNT - Check eligibility and percentage
                # =============================================================
                bulk_discount = {'applicable': False, 'percent': 0, 'eligible': False}
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                bulk_enabled = hospital.bulk_discount_enabled if hospital else False

                if service_id and bulk_enabled:
                    service = session.query(Service).filter_by(service_id=service_id).first()
                    if service:
                        # Check bulk_discount_eligible flag first
                        eligible = getattr(service, 'bulk_discount_eligible', False) or False
                        percent = float(service.bulk_discount_percent) if service.bulk_discount_percent else 0
                        if eligible and percent > 0:
                            bulk_discount = {
                                'applicable': True,
                                'eligible': True,
                                'percent': percent,
                                'item_name': service.service_name,
                                'min_count': hospital.bulk_discount_min_service_count if hospital else 5
                            }
                elif medicine_id and bulk_enabled:
                    medicine = session.query(Medicine).filter_by(medicine_id=medicine_id).first()
                    if medicine:
                        eligible = getattr(medicine, 'bulk_discount_eligible', False) or False
                        percent = float(medicine.bulk_discount_percent) if medicine.bulk_discount_percent else 0
                        if eligible and percent > 0:
                            bulk_discount = {
                                'applicable': True,
                                'eligible': True,
                                'percent': percent,
                                'item_name': medicine.medicine_name,
                                'min_count': hospital.bulk_discount_min_service_count if hospital else 5
                            }

                # =============================================================
                # LOYALTY DISCOUNT - Check patient's card and validity
                # =============================================================
                loyalty_discount = {
                    'applicable': False,
                    'percent': 0,
                    'card_type': None,
                    'valid_from': None,
                    'valid_to': None,
                    'is_valid_today': False
                }

                if patient_id:
                    # Check PatientLoyaltyWallet for patient's loyalty card
                    loyalty_wallet = session.query(PatientLoyaltyWallet).filter(
                        PatientLoyaltyWallet.patient_id == patient_id,
                        PatientLoyaltyWallet.is_active == True
                    ).first()

                    if loyalty_wallet:
                        patient_context['has_loyalty_card'] = True
                        card_type = session.query(LoyaltyCardType).filter_by(
                            card_type_id=loyalty_wallet.card_type_id,
                            is_active=True
                        ).first()

                        if card_type:
                            # Check validity dates
                            valid_from = getattr(loyalty_wallet, 'valid_from', None)
                            valid_to = getattr(loyalty_wallet, 'valid_to', None)

                            is_valid_today = True
                            if valid_from and today < valid_from:
                                is_valid_today = False
                            if valid_to and today > valid_to:
                                is_valid_today = False

                            patient_context['loyalty_card_valid'] = is_valid_today

                            loyalty_discount = {
                                'applicable': True,
                                'percent': float(card_type.discount_percent) if card_type.discount_percent else 0,
                                'card_type': card_type.card_type_name,
                                'card_type_id': str(card_type.card_type_id),
                                'valid_from': valid_from.isoformat() if valid_from else None,
                                'valid_to': valid_to.isoformat() if valid_to else None,
                                'is_valid_today': is_valid_today
                            }

                # =============================================================
                # STANDARD DISCOUNT - Fallback discount on service/medicine
                # =============================================================
                standard_discount = {'applicable': False, 'percent': 0}
                if service_id:
                    service = session.query(Service).filter_by(service_id=service_id).first()
                    if service and service.standard_discount_percent and float(service.standard_discount_percent) > 0:
                        standard_discount = {
                            'applicable': True,
                            'percent': float(service.standard_discount_percent),
                            'item_name': service.service_name
                        }

                # =============================================================
                # CALCULATE MAX DISCOUNT (Using centralized DiscountService)
                # =============================================================
                # Use centralized stacking logic for consistent calculation
                # across dashboard, simulation, and invoicing

                # Get stacking configuration
                stacking_config = DiscountService.get_stacking_config(session, hospital_id)

                # Prepare discount data for centralized calculation
                # Find best auto-apply campaign
                best_campaign = None
                best_campaign_value = 0
                for c in campaign_list:
                    if c['auto_apply'] and c['discount_type'] == 'percentage' and not c.get('is_personalized', False):
                        if c['discount_value'] > best_campaign_value:
                            best_campaign_value = c['discount_value']
                            best_campaign = c

                discount_data = {
                    'campaign': {
                        'percent': best_campaign_value if best_campaign else 0,
                        'applicable': best_campaign is not None,
                        'type': best_campaign['discount_type'] if best_campaign else 'percentage',
                        'name': best_campaign['campaign_name'] if best_campaign else None,
                        'promotion_type': best_campaign.get('promotion_type', 'simple_discount') if best_campaign else None
                    },
                    'bulk': {
                        'percent': bulk_discount.get('percent', 0),
                        'applicable': bulk_discount.get('applicable', False)
                    },
                    'loyalty': {
                        'percent': loyalty_discount.get('percent', 0),
                        'applicable': loyalty_discount.get('applicable', False),
                        'is_valid_today': loyalty_discount.get('is_valid_today', False),
                        'card_type': loyalty_discount.get('card_type')
                    },
                    'vip': {
                        'percent': 0,  # VIP discount percentage - to be implemented
                        'applicable': patient_context.get('is_special_group', False)
                    },
                    'standard': {
                        'percent': standard_discount.get('percent', 0),
                        'applicable': standard_discount.get('applicable', False)
                    }
                }

                # Calculate using centralized stacking logic
                stacked_result = DiscountService.calculate_stacked_discount(
                    discount_data, stacking_config
                )

                max_discount = stacked_result['total_percent']
                discount_breakdown = stacked_result['applied_discounts']

                return {
                    'success': True,
                    'campaigns': campaign_list,
                    'patient_context': patient_context,
                    'item_context': {
                        'item_type': item_type,
                        'item_id': str(item_id) if item_id else None,
                        'item_name': item_name,
                        'bulk_eligible': item_bulk_eligible,
                        'bulk_percent': item_bulk_percent,
                        'standard_percent': item_standard_percent
                    },
                    'applicable_discounts': {
                        'campaigns': [c for c in campaign_list if c['auto_apply']],
                        'bulk': bulk_discount,
                        'loyalty': loyalty_discount,
                        'standard': standard_discount,
                        'stacking_config': stacking_config,  # Full stacking configuration
                        'max_discount_percent': max_discount,
                        'discount_breakdown': discount_breakdown,
                        'excluded_discounts': stacked_result.get('excluded_discounts', []),
                        'capped': stacked_result.get('capped', False)
                    }
                }

        except Exception as e:
            logger.error(f"Error getting applicable campaigns: {e}")
            return {
                'success': False,
                'campaigns': [],
                'patient_context': {'is_special_group': False, 'has_loyalty_card': False},
                'item_context': {},
                'applicable_discounts': {
                    'campaigns': [],
                    'bulk': {'applicable': False, 'percent': 0},
                    'loyalty': {'applicable': False, 'percent': 0, 'card_type': None},
                    'standard': {'applicable': False, 'percent': 0},
                    'stacking_config': {},  # Empty config on error
                    'max_discount_percent': 0,
                    'discount_breakdown': [],
                    'excluded_discounts': [],
                    'capped': False
                },
                'error': str(e)
            }

    # ==========================================================================
    # SUMMARY CARD DETAILS
    # ==========================================================================

    @staticmethod
    def get_card_details(hospital_id: str, card_type: str) -> Dict[str, Any]:
        """
        Get detailed data for summary card popups.

        Args:
            hospital_id: Hospital ID
            card_type: Type of card (active_campaigns, discount_mtd, top_campaign, etc.)

        Returns:
            Dict with success flag and relevant data
        """
        try:
            with get_db_session(read_only=True) as session:
                today = date.today()
                month_start = today.replace(day=1)

                if card_type == 'active-campaigns':
                    # Get all active AND approved campaigns (not expired)
                    # Includes both currently running AND starting soon
                    campaigns = session.query(PromotionCampaign).filter(
                        PromotionCampaign.hospital_id == hospital_id,
                        PromotionCampaign.is_active == True,
                        PromotionCampaign.is_deleted.is_(False),
                        PromotionCampaign.status == 'approved',
                        PromotionCampaign.end_date >= today  # Not expired
                    ).order_by(PromotionCampaign.start_date).all()

                    return {
                        'success': True,
                        'campaigns': [{
                            'campaign_code': c.campaign_code,
                            'campaign_name': c.campaign_name,
                            'discount_type': c.discount_type,
                            'discount_value': float(c.discount_value) if c.discount_value else 0,
                            'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else '',
                            'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else ''
                        } for c in campaigns]
                    }

                elif card_type == 'draft-campaigns':
                    # Get all draft campaigns (need approval)
                    campaigns = session.query(PromotionCampaign).filter(
                        PromotionCampaign.hospital_id == hospital_id,
                        PromotionCampaign.is_deleted.is_(False),
                        PromotionCampaign.status == 'draft'
                    ).order_by(PromotionCampaign.created_at.desc()).all()

                    return {
                        'success': True,
                        'campaigns': [{
                            'campaign_id': str(c.campaign_id),
                            'campaign_code': c.campaign_code,
                            'campaign_name': c.campaign_name,
                            'discount_type': c.discount_type,
                            'discount_value': float(c.discount_value) if c.discount_value else 0,
                            'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else '',
                            'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else '',
                            'is_active': c.is_active
                        } for c in campaigns]
                    }

                elif card_type == 'pending-approval':
                    # Get all campaigns pending approval
                    campaigns = session.query(PromotionCampaign).filter(
                        PromotionCampaign.hospital_id == hospital_id,
                        PromotionCampaign.is_deleted.is_(False),
                        PromotionCampaign.status == 'pending_approval'
                    ).order_by(PromotionCampaign.created_at.desc()).all()

                    return {
                        'success': True,
                        'campaigns': [{
                            'campaign_id': str(c.campaign_id),
                            'campaign_code': c.campaign_code,
                            'campaign_name': c.campaign_name,
                            'discount_type': c.discount_type,
                            'discount_value': float(c.discount_value) if c.discount_value else 0,
                            'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else '',
                            'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else '',
                            'is_active': c.is_active
                        } for c in campaigns]
                    }

                elif card_type == 'upcoming':
                    # Get upcoming approved campaigns (starting in next 7 days)
                    seven_days = today + timedelta(days=7)
                    campaigns = session.query(PromotionCampaign).filter(
                        PromotionCampaign.hospital_id == hospital_id,
                        PromotionCampaign.is_active == True,
                        PromotionCampaign.is_deleted.is_(False),
                        PromotionCampaign.status == 'approved',
                        PromotionCampaign.start_date > today,
                        PromotionCampaign.start_date <= seven_days
                    ).order_by(PromotionCampaign.start_date).all()

                    return {
                        'success': True,
                        'campaigns': [{
                            'campaign_code': c.campaign_code,
                            'campaign_name': c.campaign_name,
                            'discount_type': c.discount_type,
                            'discount_value': float(c.discount_value) if c.discount_value else 0,
                            'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else '',
                            'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else ''
                        } for c in campaigns]
                    }

                elif card_type == 'expiring':
                    # Get expiring approved campaigns (ending in next 7 days)
                    seven_days = today + timedelta(days=7)
                    campaigns = session.query(PromotionCampaign).filter(
                        PromotionCampaign.hospital_id == hospital_id,
                        PromotionCampaign.is_active == True,
                        PromotionCampaign.is_deleted.is_(False),
                        PromotionCampaign.status == 'approved',
                        PromotionCampaign.end_date >= today,
                        PromotionCampaign.end_date <= seven_days
                    ).order_by(PromotionCampaign.end_date).all()

                    return {
                        'success': True,
                        'campaigns': [{
                            'campaign_code': c.campaign_code,
                            'campaign_name': c.campaign_name,
                            'discount_type': c.discount_type,
                            'discount_value': float(c.discount_value) if c.discount_value else 0,
                            'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else '',
                            'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else ''
                        } for c in campaigns]
                    }

                elif card_type == 'discount-mtd':
                    # Get discount breakdown for this month
                    # This would require invoice_discount table data
                    return {
                        'success': True,
                        'total': 0,
                        'breakdown': [
                            {'type': 'Campaign Discounts', 'amount': 0, 'count': 0},
                            {'type': 'Bulk Discounts', 'amount': 0, 'count': 0},
                            {'type': 'Loyalty Discounts', 'amount': 0, 'count': 0}
                        ]
                    }

                elif card_type == 'top-campaign':
                    # Get top performing approved campaign
                    # Would need usage tracking
                    campaigns = session.query(PromotionCampaign).filter(
                        PromotionCampaign.hospital_id == hospital_id,
                        PromotionCampaign.is_active == True,
                        PromotionCampaign.is_deleted.is_(False),
                        PromotionCampaign.status == 'approved'
                    ).order_by(PromotionCampaign.current_uses.desc()).first()

                    if campaigns:
                        return {
                            'success': True,
                            'campaign': {
                                'campaign_code': campaigns.campaign_code,
                                'campaign_name': campaigns.campaign_name,
                                'discount_type': campaigns.discount_type,
                                'discount_value': float(campaigns.discount_value) if campaigns.discount_value else 0,
                                'total_uses': campaigns.current_uses or 0,
                                'total_discount': 0,
                                'end_date': campaigns.end_date.strftime('%Y-%m-%d') if campaigns.end_date else ''
                            }
                        }
                    return {'success': True, 'campaign': None}

                elif card_type == 'bulk':
                    # Get bulk discount configuration
                    hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                    return {
                        'success': True,
                        'enabled': hospital.bulk_discount_enabled if hospital else False,
                        'min_count': hospital.bulk_discount_min_service_count if hospital else 5,
                        'effective_from': hospital.bulk_discount_effective_from.strftime('%Y-%m-%d') if hospital and hospital.bulk_discount_effective_from else None
                    }

                elif card_type == 'loyalty':
                    # Get loyalty card types
                    card_types = session.query(LoyaltyCardType).filter(
                        LoyaltyCardType.hospital_id == hospital_id,
                        LoyaltyCardType.is_deleted == False
                    ).order_by(LoyaltyCardType.discount_percent.desc()).all()

                    return {
                        'success': True,
                        'card_types': [{
                            'card_type_name': ct.card_type_name,
                            'card_type_code': ct.card_type_code,
                            'description': ct.description,
                            'discount_percent': float(ct.discount_percent) if ct.discount_percent else 0,
                            'card_color': ct.card_color,
                            'is_active': ct.is_active
                        } for ct in card_types]
                    }

                elif card_type == 'customers':
                    # Get customer usage data
                    # Would need to query invoice discount usage
                    return {
                        'success': True,
                        'total_customers': 0,
                        'top_customers': []
                    }

                else:
                    return {'success': False, 'error': f'Unknown card type: {card_type}'}

        except Exception as e:
            logger.error(f"Error getting card details for {card_type}: {e}")
            return {'success': False, 'error': str(e)}

    # ==========================================================================
    # CAMPAIGN CRUD
    # ==========================================================================

    @staticmethod
    def get_all_campaigns(
        hospital_id: str,
        filters: Optional[Dict] = None,
        page: int = 1,
        per_page: int = 20,
        sort_by: str = 'start_date',
        sort_dir: str = 'desc'
    ) -> Dict[str, Any]:
        """
        Get campaigns with filtering, sorting, and pagination

        Args:
            hospital_id: Hospital ID
            filters: Filter dictionary
            page: Page number
            per_page: Items per page
            sort_by: Sort field
            sort_dir: Sort direction ('asc' or 'desc')

        Returns:
            Dictionary with items, total, pages
        """
        try:
            with get_db_session(read_only=True) as session:
                query = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False)
                )

                # Apply filters
                if filters:
                    if filters.get('is_active') is not None:
                        query = query.filter(PromotionCampaign.is_active == filters['is_active'])
                    if filters.get('promotion_type'):
                        query = query.filter(PromotionCampaign.promotion_type == filters['promotion_type'])
                    if filters.get('applies_to'):
                        query = query.filter(PromotionCampaign.applies_to == filters['applies_to'])
                    if filters.get('is_personalized') is not None:
                        query = query.filter(PromotionCampaign.is_personalized == filters['is_personalized'])
                    if filters.get('search'):
                        search_term = f"%{filters['search']}%"
                        query = query.filter(or_(
                            PromotionCampaign.campaign_name.ilike(search_term),
                            PromotionCampaign.campaign_code.ilike(search_term),
                            PromotionCampaign.description.ilike(search_term)
                        ))
                    # Date range filters - filter by campaign period overlapping with date range
                    if filters.get('start_date'):
                        filter_start = date.fromisoformat(filters['start_date'])
                        # Campaigns that end on or after the filter start date (or have no end date)
                        query = query.filter(or_(
                            PromotionCampaign.end_date >= filter_start,
                            PromotionCampaign.end_date.is_(None)
                        ))
                    if filters.get('end_date'):
                        filter_end = date.fromisoformat(filters['end_date'])
                        # Campaigns that start on or before the filter end date (or have no start date)
                        query = query.filter(or_(
                            PromotionCampaign.start_date <= filter_end,
                            PromotionCampaign.start_date.is_(None)
                        ))

                # Get total count
                total = query.count()

                # Apply sorting
                sort_column = getattr(PromotionCampaign, sort_by, PromotionCampaign.start_date)
                if sort_dir == 'desc':
                    query = query.order_by(sort_column.desc())
                else:
                    query = query.order_by(sort_column.asc())

                # Apply pagination
                offset = (page - 1) * per_page
                campaigns = query.offset(offset).limit(per_page).all()

                items = []
                for c in campaigns:
                    campaign_dict = {
                        'campaign_id': str(c.campaign_id),
                        'campaign_code': c.campaign_code,
                        'campaign_name': c.campaign_name,
                        'description': c.description,
                        'promotion_type': c.promotion_type,
                        'discount_type': c.discount_type,
                        'discount_value': float(c.discount_value) if c.discount_value else 0,
                        'start_date': c.start_date.strftime('%d %b %Y') if c.start_date else None,
                        'end_date': c.end_date.strftime('%d %b %Y') if c.end_date else None,
                        'is_active': c.is_active,
                        'is_personalized': c.is_personalized,
                        'auto_apply': c.auto_apply,
                        'applies_to': c.applies_to,
                        'specific_items': c.specific_items,
                        'target_special_group': getattr(c, 'target_special_group', False) or False,
                        'target_groups': c.target_groups,
                        'status': getattr(c, 'status', 'approved'),  # Approval status
                        'min_purchase_amount': float(c.min_purchase_amount) if c.min_purchase_amount else None,
                        'max_discount_amount': float(c.max_discount_amount) if c.max_discount_amount else None,
                        'max_uses_per_patient': c.max_uses_per_patient,
                        'max_total_uses': c.max_total_uses,
                        'current_uses': c.current_uses or 0,
                        'terms_and_conditions': c.terms_and_conditions,
                        'promotion_rules': c.promotion_rules,
                        'created_at': c.created_at.isoformat() if c.created_at else None,
                        'updated_at': c.updated_at.isoformat() if c.updated_at else None
                    }
                    # Enrich with group names
                    PromotionDashboardService._enrich_campaign_with_group_names(session, campaign_dict)
                    items.append(campaign_dict)

                return {
                    'items': items,
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'pages': (total + per_page - 1) // per_page
                }

        except Exception as e:
            logger.error(f"Error getting campaigns: {e}")
            return {'items': [], 'total': 0, 'page': 1, 'per_page': per_page, 'pages': 0, 'error': str(e)}

    @staticmethod
    def get_campaign_summary(hospital_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for campaigns (for summary cards)

        Returns:
            Dictionary with active_count, inactive_count, expiring_soon, uses_this_month
        """
        try:
            with get_db_session(read_only=True) as session:
                today = date.today()
                week_ahead = today + timedelta(days=7)
                month_start = today.replace(day=1)

                # Active campaigns (only approved)
                active_count = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.status == 'approved',
                    PromotionCampaign.start_date <= today,
                    PromotionCampaign.end_date >= today
                ).scalar() or 0

                # Inactive campaigns
                inactive_count = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    or_(
                        PromotionCampaign.is_active == False,
                        PromotionCampaign.end_date < today
                    )
                ).scalar() or 0

                # Expiring soon (within 7 days, only approved)
                expiring_soon = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.status == 'approved',
                    PromotionCampaign.end_date >= today,
                    PromotionCampaign.end_date <= week_ahead
                ).scalar() or 0

                # Uses this month (sum of current_uses for campaigns used this month)
                # Note: This is a simplified count - ideally would query usage logs
                uses_this_month = session.query(func.sum(PromotionCampaign.current_uses)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.is_active == True
                ).scalar() or 0

                return {
                    'active_count': active_count,
                    'inactive_count': inactive_count,
                    'expiring_soon': expiring_soon,
                    'uses_this_month': uses_this_month
                }

        except Exception as e:
            logger.error(f"Error getting campaign summary: {e}")
            return {
                'active_count': 0,
                'inactive_count': 0,
                'expiring_soon': 0,
                'uses_this_month': 0
            }

    @staticmethod
    def get_campaign_by_id(hospital_id: str, campaign_id: str) -> Optional[Dict]:
        """Get a single campaign by ID"""
        try:
            with get_db_session(read_only=True) as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return None

                campaign_dict = {
                    'campaign_id': str(campaign.campaign_id),
                    'campaign_code': campaign.campaign_code,
                    'campaign_name': campaign.campaign_name,
                    'description': campaign.description,
                    'promotion_type': campaign.promotion_type,
                    'discount_type': campaign.discount_type,
                    'discount_value': float(campaign.discount_value) if campaign.discount_value else 0,
                    'start_date': campaign.start_date,
                    'end_date': campaign.end_date,
                    'is_active': campaign.is_active,
                    'is_personalized': campaign.is_personalized,
                    'auto_apply': campaign.auto_apply,
                    'applies_to': campaign.applies_to,
                    'specific_items': campaign.specific_items,
                    'target_special_group': getattr(campaign, 'target_special_group', False) or False,
                    'target_groups': campaign.target_groups,
                    'min_purchase_amount': float(campaign.min_purchase_amount) if campaign.min_purchase_amount else None,
                    'max_discount_amount': float(campaign.max_discount_amount) if campaign.max_discount_amount else None,
                    'max_uses_per_patient': campaign.max_uses_per_patient,
                    'max_total_uses': campaign.max_total_uses,
                    'current_uses': campaign.current_uses or 0,
                    'terms_and_conditions': campaign.terms_and_conditions,
                    'promotion_rules': campaign.promotion_rules,
                    'status': getattr(campaign, 'status', 'approved'),
                    'approval_notes': getattr(campaign, 'approval_notes', None),
                    'approved_by': getattr(campaign, 'approved_by', None),
                    'approved_at': getattr(campaign, 'approved_at', None),
                    'created_at': campaign.created_at,
                    'updated_at': campaign.updated_at
                }

                # Enrich with group names
                PromotionDashboardService._enrich_campaign_with_group_names(session, campaign_dict)

                return campaign_dict

        except Exception as e:
            logger.error(f"Error getting campaign: {e}")
            return None

    @staticmethod
    def create_campaign(hospital_id: str, data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new campaign

        Args:
            hospital_id: Hospital ID
            data: Campaign data dictionary

        Returns:
            Tuple of (success, message, campaign_id)
        """
        try:
            with get_db_session() as session:
                # Check for duplicate code
                existing = session.query(PromotionCampaign).filter(
                    PromotionCampaign.campaign_code == data.get('campaign_code'),
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if existing:
                    return False, f"Campaign code '{data.get('campaign_code')}' already exists", None

                campaign = PromotionCampaign(
                    hospital_id=hospital_id,
                    campaign_code=data.get('campaign_code'),
                    campaign_name=data.get('campaign_name'),
                    description=data.get('description'),
                    promotion_type=data.get('promotion_type', 'simple_discount'),
                    discount_type=data.get('discount_type'),
                    discount_value=Decimal(str(data.get('discount_value', 0))),
                    start_date=data.get('start_date'),
                    end_date=data.get('end_date'),
                    is_active=data.get('is_active', True),
                    is_personalized=data.get('is_personalized', False),
                    auto_apply=data.get('auto_apply', False),
                    target_special_group=data.get('target_special_group', False),  # VIP patient targeting
                    applies_to=data.get('applies_to', 'all'),
                    specific_items=data.get('specific_items'),
                    target_groups=data.get('target_groups'),  # Campaign group targeting
                    min_purchase_amount=Decimal(str(data['min_purchase_amount'])) if data.get('min_purchase_amount') else None,
                    max_discount_amount=Decimal(str(data['max_discount_amount'])) if data.get('max_discount_amount') else None,
                    max_uses_per_patient=data.get('max_uses_per_patient'),
                    max_total_uses=data.get('max_total_uses'),
                    terms_and_conditions=data.get('terms_and_conditions'),
                    promotion_rules=data.get('promotion_rules'),
                    current_uses=0,
                    status='draft'  # New campaigns start as draft, need approval
                )

                session.add(campaign)
                session.flush()
                campaign_id = str(campaign.campaign_id)
                session.commit()

                logger.info(f"Created campaign: {campaign_id}")
                return True, "Campaign created successfully", campaign_id

        except Exception as e:
            logger.error(f"Error creating campaign: {e}")
            return False, str(e), None

    @staticmethod
    def update_campaign(hospital_id: str, campaign_id: str, data: Dict) -> Tuple[bool, str]:
        """
        Update an existing campaign

        Args:
            hospital_id: Hospital ID
            campaign_id: Campaign ID
            data: Updated campaign data

        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found"

                # Check for duplicate code (if code is being changed)
                if data.get('campaign_code') and data['campaign_code'] != campaign.campaign_code:
                    existing = session.query(PromotionCampaign).filter(
                        PromotionCampaign.campaign_code == data['campaign_code'],
                        PromotionCampaign.campaign_id != campaign_id,
                        PromotionCampaign.is_deleted.is_(False)
                    ).first()

                    if existing:
                        return False, f"Campaign code '{data['campaign_code']}' already exists"

                # Update fields
                updatable_fields = [
                    'campaign_code', 'campaign_name', 'description', 'promotion_type',
                    'discount_type', 'discount_value', 'start_date', 'end_date',
                    'is_active', 'is_personalized', 'auto_apply', 'target_special_group',
                    'applies_to', 'specific_items', 'target_groups',
                    'min_purchase_amount', 'max_discount_amount',
                    'max_uses_per_patient', 'max_total_uses', 'terms_and_conditions',
                    'promotion_rules'
                ]

                for field in updatable_fields:
                    if field in data:
                        value = data[field]
                        if field in ['discount_value', 'min_purchase_amount', 'max_discount_amount']:
                            value = Decimal(str(value)) if value is not None else None
                        setattr(campaign, field, value)

                session.commit()
                logger.info(f"Updated campaign: {campaign_id}")
                return True, "Campaign updated successfully"

        except Exception as e:
            logger.error(f"Error updating campaign: {e}")
            return False, str(e)

    @staticmethod
    def toggle_campaign_status(hospital_id: str, campaign_id: str) -> Tuple[bool, str]:
        """
        Toggle campaign active status

        Business rules:
        - Draft/Not-launched campaigns: can toggle freely
        - Launched campaigns (approved + start_date <= today): can only deactivate, not re-activate
        """
        try:
            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found"

                today = date.today()
                campaign_status = getattr(campaign, 'status', 'approved')
                is_launched = (
                    campaign_status == 'approved' and
                    campaign.start_date and
                    campaign.start_date <= today
                )

                # For launched campaigns, only allow deactivation
                if is_launched and not campaign.is_active:
                    return False, "Launched campaigns cannot be re-activated. Create a new campaign instead."

                campaign.is_active = not campaign.is_active
                new_status = 'active' if campaign.is_active else 'inactive'
                session.commit()

                logger.info(f"Toggled campaign {campaign_id} to {new_status}")
                return True, f"Campaign is now {new_status}"

        except Exception as e:
            logger.error(f"Error toggling campaign status: {e}")
            return False, str(e)

    @staticmethod
    def duplicate_campaign(hospital_id: str, campaign_id: str) -> Tuple[bool, str, Optional[str]]:
        """
        Create a copy of an existing campaign

        Returns:
            Tuple of (success, message, new_campaign_id)
        """
        try:
            with get_db_session() as session:
                original = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not original:
                    return False, "Campaign not found", None

                # Generate new code
                base_code = f"{original.campaign_code}_COPY"
                new_code = base_code
                counter = 1
                while session.query(PromotionCampaign).filter(
                    PromotionCampaign.campaign_code == new_code,
                    PromotionCampaign.is_deleted.is_(False)
                ).first():
                    new_code = f"{base_code}_{counter}"
                    counter += 1

                new_campaign = PromotionCampaign(
                    hospital_id=hospital_id,
                    campaign_code=new_code,
                    campaign_name=f"{original.campaign_name} (Copy)",
                    description=original.description,
                    promotion_type=original.promotion_type,
                    discount_type=original.discount_type,
                    discount_value=original.discount_value,
                    start_date=original.start_date,
                    end_date=original.end_date,
                    is_active=False,  # Start inactive
                    is_personalized=original.is_personalized,
                    auto_apply=original.auto_apply,
                    applies_to=original.applies_to,
                    specific_items=original.specific_items,
                    min_purchase_amount=original.min_purchase_amount,
                    max_discount_amount=original.max_discount_amount,
                    max_uses_per_patient=original.max_uses_per_patient,
                    max_total_uses=original.max_total_uses,
                    terms_and_conditions=original.terms_and_conditions,
                    promotion_rules=original.promotion_rules,
                    current_uses=0
                )

                session.add(new_campaign)
                session.flush()
                new_id = str(new_campaign.campaign_id)
                session.commit()

                logger.info(f"Duplicated campaign {campaign_id} to {new_id}")
                return True, f"Campaign duplicated as '{new_code}'", new_id

        except Exception as e:
            logger.error(f"Error duplicating campaign: {e}")
            return False, str(e), None

    @staticmethod
    def delete_campaign(hospital_id: str, campaign_id: str) -> Tuple[bool, str]:
        """Soft delete a campaign"""
        try:
            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found"

                campaign.is_deleted = True
                campaign.is_active = False
                session.commit()

                logger.info(f"Deleted campaign: {campaign_id}")
                return True, "Campaign deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting campaign: {e}")
            return False, str(e)

    # =========================================================================
    # Campaign Approval Workflow Methods
    # =========================================================================

    @staticmethod
    def submit_campaign_for_approval(hospital_id: str, campaign_id: str) -> Tuple[bool, str]:
        """
        Submit a campaign for approval (changes status from 'draft' to 'pending_approval')

        Args:
            hospital_id: Hospital ID
            campaign_id: Campaign ID

        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found"

                if campaign.status != 'draft':
                    return False, f"Campaign cannot be submitted. Current status: {campaign.status}"

                # Capture name before commit
                campaign_name = campaign.campaign_name
                campaign.status = 'pending_approval'
                campaign.approval_notes = None  # Clear any previous notes
                session.commit()

                logger.info(f"Campaign {campaign_id} submitted for approval")
                return True, f"Campaign '{campaign_name}' submitted for approval"

        except Exception as e:
            logger.error(f"Error submitting campaign for approval: {e}")
            return False, str(e)

    @staticmethod
    def approve_campaign(hospital_id: str, campaign_id: str, approver_id: str, notes: str = None) -> Tuple[bool, str]:
        """
        Approve a campaign (changes status from 'pending_approval' to 'approved')

        Args:
            hospital_id: Hospital ID
            campaign_id: Campaign ID
            approver_id: User ID of the approver
            notes: Optional approval notes

        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found"

                if campaign.status != 'pending_approval':
                    return False, f"Campaign cannot be approved. Current status: {campaign.status}"

                # Capture name before commit
                campaign_name = campaign.campaign_name

                # Use ApprovalMixin's approve method
                campaign.approve(approver_id, notes)
                session.commit()

                logger.info(f"Campaign {campaign_id} approved by {approver_id}")
                return True, f"Campaign '{campaign_name}' approved successfully"

        except Exception as e:
            logger.error(f"Error approving campaign: {e}")
            return False, str(e)

    @staticmethod
    def reject_campaign(hospital_id: str, campaign_id: str, rejector_id: str, reason: str) -> Tuple[bool, str]:
        """
        Reject a campaign (changes status from 'pending_approval' to 'rejected')

        Args:
            hospital_id: Hospital ID
            campaign_id: Campaign ID
            rejector_id: User ID of the rejector
            reason: Rejection reason (required)

        Returns:
            Tuple of (success, message)
        """
        try:
            if not reason or not reason.strip():
                return False, "Rejection reason is required"

            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found"

                if campaign.status != 'pending_approval':
                    return False, f"Campaign cannot be rejected. Current status: {campaign.status}"

                # Capture name before commit
                campaign_name = campaign.campaign_name
                campaign.status = 'rejected'
                campaign.approval_notes = f"Rejected by {rejector_id}: {reason}"
                session.commit()

                logger.info(f"Campaign {campaign_id} rejected by {rejector_id}")
                return True, f"Campaign '{campaign_name}' rejected"

        except Exception as e:
            logger.error(f"Error rejecting campaign: {e}")
            return False, str(e)

    @staticmethod
    def resubmit_campaign(hospital_id: str, campaign_id: str) -> Tuple[bool, str]:
        """
        Resubmit a rejected campaign for approval (changes status from 'rejected' to 'pending_approval')

        Args:
            hospital_id: Hospital ID
            campaign_id: Campaign ID

        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found"

                if campaign.status not in ['rejected', 'draft']:
                    return False, f"Campaign cannot be resubmitted. Current status: {campaign.status}"

                # Capture name before commit
                campaign_name = campaign.campaign_name
                campaign.status = 'pending_approval'
                campaign.approval_notes = None  # Clear rejection notes
                campaign.approved_by = None
                campaign.approved_at = None
                session.commit()

                logger.info(f"Campaign {campaign_id} resubmitted for approval")
                return True, f"Campaign '{campaign_name}' resubmitted for approval"

        except Exception as e:
            logger.error(f"Error resubmitting campaign: {e}")
            return False, str(e)

    @staticmethod
    def get_campaigns_pending_approval(hospital_id: str) -> List[Dict]:
        """
        Get all campaigns pending approval

        Args:
            hospital_id: Hospital ID

        Returns:
            List of campaigns with pending_approval status
        """
        try:
            with get_db_session(read_only=True) as session:
                campaigns = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.status == 'pending_approval',
                    PromotionCampaign.is_deleted.is_(False)
                ).order_by(PromotionCampaign.created_at.desc()).all()

                return [
                    {
                        'campaign_id': str(c.campaign_id),
                        'campaign_code': c.campaign_code,
                        'campaign_name': c.campaign_name,
                        'description': c.description,
                        'promotion_type': c.promotion_type,
                        'discount_type': c.discount_type,
                        'discount_value': float(c.discount_value) if c.discount_value else 0,
                        'start_date': c.start_date.isoformat() if c.start_date else None,
                        'end_date': c.end_date.isoformat() if c.end_date else None,
                        'created_at': c.created_at.strftime('%d %b %Y %H:%M') if c.created_at else None,
                        'status': c.status
                    }
                    for c in campaigns
                ]

        except Exception as e:
            logger.error(f"Error getting campaigns pending approval: {e}")
            return []

    @staticmethod
    def update_campaign_dates(
        hospital_id: str,
        campaign_id: str,
        start_date: date,
        end_date: date
    ) -> Tuple[bool, str, bool]:
        """
        Update campaign dates (for timeline drag-resize)

        Business rules:
        - Draft campaigns: can be edited freely (start and end dates)
        - Approved but not started (start_date > today): can edit both dates, resets to draft
        - Approved and started (start_date <= today): can ONLY edit end date, resets to draft
        - Pending approval or rejected: cannot edit via drag

        Args:
            hospital_id: Hospital ID
            campaign_id: Campaign ID
            start_date: New start date
            end_date: New end date

        Returns:
            Tuple of (success, message, status_changed)
        """
        try:
            # Validate dates
            if end_date < start_date:
                return False, "End date cannot be before start date", False

            with get_db_session() as session:
                campaign = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.campaign_id == campaign_id,
                    PromotionCampaign.is_deleted.is_(False)
                ).first()

                if not campaign:
                    return False, "Campaign not found", False

                campaign_status = getattr(campaign, 'status', 'approved')
                today = date.today()
                original_start = campaign.start_date
                original_end = campaign.end_date
                has_started = original_start and original_start <= today
                status_changed = False

                # Check if start date is being changed
                start_date_changed = start_date != original_start

                # Check edit permissions based on status and launch state
                if campaign_status == 'draft':
                    # Draft campaigns can always be edited fully
                    pass
                elif campaign_status == 'approved':
                    if has_started:
                        # Campaign has started - can only modify end date
                        if start_date_changed:
                            return False, "Campaign has started. Start date cannot be modified.", False
                        # End date change is allowed - stays approved (immediate effect)
                        # No status change needed for running campaigns
                        logger.info(f"Campaign {campaign_id} end date modified while running (stays approved)")
                    else:
                        # Not yet started - can edit both dates, reset to draft for re-approval
                        campaign.status = 'draft'
                        status_changed = True
                        logger.info(f"Campaign {campaign_id} status reset to draft due to date edit")
                else:
                    # Pending approval or rejected - cannot edit via drag
                    return False, f"Cannot modify dates for {campaign_status} campaigns.", False

                campaign.start_date = start_date
                campaign.end_date = end_date
                session.commit()

                msg = "Campaign dates updated"
                if status_changed:
                    msg += " (status reset to draft - requires re-approval)"

                logger.info(f"Updated campaign {campaign_id} dates: {start_date} to {end_date}")
                return True, msg, status_changed

        except Exception as e:
            logger.error(f"Error updating campaign dates: {e}")
            return False, str(e), False

    # ==========================================================================
    # SIMULATION
    # ==========================================================================

    @staticmethod
    def simulate_promotions(
        hospital_id: str,
        item_id: str,
        item_type: str,  # 'service', 'medicine', 'package'
        quantity: int = 1,
        patient_id: Optional[str] = None,
        simulation_date: Optional[date] = None,
        include_draft: bool = False
    ) -> Dict[str, Any]:
        """
        Simulate which promotions would apply to an item

        Args:
            hospital_id: Hospital ID
            item_id: Item ID (service_id, medicine_id, or package_id)
            item_type: Type of item
            quantity: Quantity
            patient_id: Optional patient ID for loyalty discount
            simulation_date: Date to simulate (defaults to today)
            include_draft: If True, include draft campaigns in simulation

        Returns:
            Dictionary with simulation results
        """
        try:
            simulation_date = simulation_date or date.today()

            with get_db_session(read_only=True) as session:
                # Get item details
                item = None
                item_name = "Unknown"
                unit_price = Decimal('0')

                if item_type.lower() == 'service':
                    item = session.query(Service).filter_by(service_id=item_id).first()
                    if item:
                        item_name = item.service_name
                        unit_price = item.price or Decimal('0')
                elif item_type.lower() == 'medicine':
                    item = session.query(Medicine).filter_by(medicine_id=item_id).first()
                    if item:
                        item_name = item.medicine_name
                        unit_price = item.mrp or Decimal('0')
                elif item_type.lower() == 'package':
                    item = session.query(Package).filter_by(package_id=item_id).first()
                    if item:
                        item_name = item.package_name
                        unit_price = item.selling_price or Decimal('0')

                if not item:
                    return {
                        'error': f'{item_type.title()} not found',
                        'applicable_promotions': [],
                        'final_discount': None
                    }

                original_price = unit_price * quantity
                applicable_promotions = []

                # Get hospital's stacking configuration early (needed for VIP percent)
                stacking_config = DiscountService.get_stacking_config(session, hospital_id)

                # 1. Check Campaign Promotions (approved, or include draft if requested)
                status_filter = PromotionCampaign.status.in_(['approved', 'draft']) if include_draft else PromotionCampaign.status == 'approved'
                campaigns = session.query(PromotionCampaign).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_active == True,
                    PromotionCampaign.is_deleted.is_(False),
                    status_filter,
                    PromotionCampaign.start_date <= simulation_date,
                    PromotionCampaign.end_date >= simulation_date,
                    or_(
                        PromotionCampaign.applies_to == 'all',
                        PromotionCampaign.applies_to == item_type.lower() + 's'  # services, medicines, packages
                    )
                ).all()

                # Get patient VIP status for filtering VIP-targeted campaigns
                patient_is_vip = False
                if patient_id:
                    patient = session.query(Patient).filter_by(patient_id=patient_id).first()
                    if patient:
                        patient_is_vip = getattr(patient, 'is_special_group', False) or getattr(patient, 'is_vip', False)

                for campaign in campaigns:
                    # Check if specific items restriction applies
                    if campaign.specific_items and item_id not in campaign.specific_items:
                        continue

                    # Check usage limits
                    if campaign.max_total_uses and campaign.current_uses >= campaign.max_total_uses:
                        continue

                    # Check VIP/Special Group targeting (Fixed 2025-11-30)
                    # If campaign targets special group, only apply to VIP patients
                    if getattr(campaign, 'target_special_group', False):
                        if not patient_is_vip:
                            continue  # Skip - this campaign is only for VIP patients

                    # Calculate discount
                    if campaign.discount_type == 'percentage':
                        discount_amount = (original_price * Decimal(str(campaign.discount_value))) / 100
                        if campaign.max_discount_amount and discount_amount > campaign.max_discount_amount:
                            discount_amount = campaign.max_discount_amount
                    else:
                        discount_amount = Decimal(str(campaign.discount_value))

                    # Get campaign stacking mode from config
                    campaign_mode = stacking_config.get('campaign', {}).get('mode', 'absolute')
                    applicable_promotions.append({
                        'type': 'campaign',
                        'name': campaign.campaign_name,
                        'code': campaign.campaign_code,
                        'discount_type': campaign.discount_type,
                        'discount_value': float(campaign.discount_value),
                        'discount_percent': float(campaign.discount_value) if campaign.discount_type == 'percentage' else 0,
                        'discount_amount': float(discount_amount),
                        'priority': 1,
                        'would_apply': False,  # Will be set later
                        'reason': '',
                        'is_personalized': campaign.is_personalized,
                        'is_draft': campaign.status == 'draft',
                        'stacking_mode': campaign_mode
                    })

                # 2. Check Bulk Discount - Using CENTRALIZED method
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()
                bulk_discount = DiscountService.calculate_bulk_discount_simulation(
                    session, hospital_id, item_type, item_id, unit_price, quantity
                )
                if bulk_discount:
                    min_count = hospital.bulk_discount_min_service_count if hospital else 5
                    bulk_mode = stacking_config.get('bulk', {}).get('mode', 'incremental')
                    applicable_promotions.append({
                        'type': 'bulk',
                        'name': 'Bulk Discount',
                        'discount_type': 'percentage',
                        'discount_value': float(bulk_discount.discount_percent),
                        'discount_percent': float(bulk_discount.discount_percent),
                        'discount_amount': float(bulk_discount.discount_amount),
                        'priority': 2,
                        'would_apply': False,
                        'reason': f'Applicable when {min_count}+ services/medicines in single invoice',
                        'min_items': min_count,
                        'eligibility_note': f'This discount applies only when {min_count} or more services/medicines are ordered in a single invoice',
                        'stacking_mode': bulk_mode
                    })

                # 3. Check Loyalty Discount - Using CENTRALIZED method
                if patient_id:
                    logger.info(f"[SIMULATE] Checking loyalty for patient_id={patient_id}, hospital_id={hospital_id}")
                    loyalty_discount = DiscountService.calculate_loyalty_percentage_discount(
                        session, hospital_id, patient_id, item_type, item_id, unit_price, quantity
                    )
                    if loyalty_discount:
                        card_type_name = loyalty_discount.metadata.get('card_type_name', 'Loyalty Card')
                        loyalty_mode = stacking_config.get('loyalty', {}).get('mode', 'incremental')
                        logger.info(f"[SIMULATE] Loyalty discount: {loyalty_discount.discount_percent}% from {card_type_name}")
                        applicable_promotions.append({
                            'type': 'loyalty',
                            'name': f'{card_type_name} Card',
                            'discount_type': 'percentage',
                            'discount_value': float(loyalty_discount.discount_percent),
                            'discount_percent': float(loyalty_discount.discount_percent),
                            'discount_amount': float(loyalty_discount.discount_amount),
                            'priority': 2,
                            'would_apply': False,
                            'reason': f'{card_type_name} member discount',
                            'stacking_mode': loyalty_mode
                        })

                # 4. VIP Discount - Handled via Campaigns (Updated 2025-11-29)
                # VIP discounts are now created as campaigns with target_special_group=True
                # These campaigns are already included in step 1 (Campaign Promotions) above
                # The stacking mode (exclusive/incremental/absolute) is configured in hospital settings
                # No separate VIP logic needed here - campaigns handle validity dates, discount %, etc.

                # 5. Check Standard Discount - Using CENTRALIZED method
                standard_discount = DiscountService.calculate_standard_discount(
                    session, item_type, item_id, unit_price, quantity
                )
                if standard_discount:
                    applicable_promotions.append({
                        'type': 'standard',
                        'name': 'Standard Discount',
                        'discount_type': 'percentage',
                        'discount_value': float(standard_discount.discount_percent),
                        'discount_percent': float(standard_discount.discount_percent),
                        'discount_amount': float(standard_discount.discount_amount),
                        'priority': 4,
                        'would_apply': False,
                        'reason': 'Fallback when no other discount applies',
                        'stacking_mode': 'fallback'  # Standard is fallback - only applies if nothing else does
                    })

                # =============================================================
                # DISCOUNT SELECTION LOGIC - USING CENTRALIZED STACKING CONFIG
                # Uses hospital's discount_stacking_config from DiscountService
                # =============================================================
                logger.info(f"[SIMULATE] Using stacking config: {stacking_config}")

                # Build discount data for centralized calculator
                discount_data = {}

                # Find best campaign discount
                campaign_promos = [p for p in applicable_promotions if p['type'] == 'campaign']
                if campaign_promos:
                    best_campaign = max(campaign_promos, key=lambda x: x['discount_percent'])
                    discount_data['campaign'] = {
                        'percent': best_campaign['discount_percent'],
                        'type': best_campaign['discount_type'],
                        'name': best_campaign['name'],
                        'applicable': True
                    }

                # Find bulk discount
                bulk_promos = [p for p in applicable_promotions if p['type'] == 'bulk']
                if bulk_promos:
                    discount_data['bulk'] = {
                        'percent': bulk_promos[0]['discount_percent'],
                        'name': bulk_promos[0]['name']
                    }

                # Find loyalty discount
                loyalty_promos = [p for p in applicable_promotions if p['type'] == 'loyalty']
                if loyalty_promos:
                    discount_data['loyalty'] = {
                        'percent': loyalty_promos[0]['discount_percent'],
                        'card_type': loyalty_promos[0]['name'],
                        'is_valid_today': True
                    }

                # Find standard discount
                standard_promos = [p for p in applicable_promotions if p['type'] == 'standard']
                if standard_promos:
                    discount_data['standard'] = {
                        'percent': standard_promos[0]['discount_percent']
                    }

                # Note: VIP discounts are now handled as campaigns with target_special_group=True
                # They are included in campaign_promos above and use the VIP stacking mode from config

                logger.info(f"[SIMULATE] Discount data for calculation: {discount_data}")

                # Call centralized stacking calculator
                stacked_result = DiscountService.calculate_stacked_discount(
                    discount_data, stacking_config, item_price=float(original_price)
                )
                logger.info(f"[SIMULATE] Stacked result: {stacked_result}")

                # Update applicable_promotions with would_apply status
                applied_sources = [d['source'] for d in stacked_result.get('applied_discounts', [])]
                applied_names = {d['source']: d.get('name', '') for d in stacked_result.get('applied_discounts', [])}
                excluded_info = {d['source']: d['reason'] for d in stacked_result.get('excluded_discounts', [])}

                for promo in applicable_promotions:
                    promo_type = promo['type']
                    if promo_type in applied_sources:
                        # For campaigns, check if this specific campaign was applied (by name match)
                        if promo_type == 'campaign':
                            applied_campaign_name = applied_names.get('campaign', '')
                            if promo['name'] == applied_campaign_name:
                                promo['would_apply'] = True
                                promo['reason'] = 'Applied per stacking config'
                            else:
                                promo['would_apply'] = False
                                promo['reason'] = f"Lower priority than {applied_campaign_name}" if applied_campaign_name else 'Not best campaign'
                        else:
                            promo['would_apply'] = True
                            promo['reason'] = 'Applied per stacking config'
                    else:
                        promo['would_apply'] = False
                        promo['reason'] = excluded_info.get(promo_type, 'Not applied per stacking config')

                # Calculate final amounts
                total_discount_percent = stacked_result.get('total_percent', 0)
                total_discount_amount = (original_price * Decimal(str(total_discount_percent))) / 100

                # Build final discount info
                final_discount = None
                if total_discount_percent > 0:
                    breakdown_parts = []
                    for item in stacked_result.get('breakdown', []):
                        if item['source'] != 'cap':
                            breakdown_parts.append(f"{item['source'].title()} {item['percent']}%")

                    final_discount = {
                        'type': 'stacked',
                        'name': ' + '.join(breakdown_parts),
                        'breakdown': stacked_result.get('breakdown', []),
                        'applied_discounts': stacked_result.get('applied_discounts', []),
                        'excluded_discounts': stacked_result.get('excluded_discounts', []),
                        'total_percent': total_discount_percent,
                        'amount': float(total_discount_amount),
                        'capped': stacked_result.get('capped', False),
                        'stacking_config': stacking_config
                    }

                # All promotions for display
                all_promotions = applicable_promotions

                return {
                    'item': {
                        'id': str(item_id),
                        'type': item_type,
                        'name': item_name,
                        'unit_price': float(unit_price)
                    },
                    'quantity': quantity,
                    'simulation_date': simulation_date.isoformat(),
                    'applicable_promotions': all_promotions,
                    'final_discount': final_discount,
                    'original_price': float(original_price),
                    'final_price': float(original_price - total_discount_amount),
                    'stacking_config': stacking_config  # Include config for frontend display
                }

        except Exception as e:
            logger.error(f"Error in promotion simulation: {e}")
            return {
                'error': str(e),
                'applicable_promotions': [],
                'final_discount': None
            }

    # ==========================================================================
    # BULK CONFIGURATION
    # ==========================================================================

    @staticmethod
    def get_bulk_config(hospital_id: str) -> Dict[str, Any]:
        """Get bulk discount configuration"""
        try:
            with get_db_session(read_only=True) as session:
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

                if not hospital:
                    return {'error': 'Hospital not found'}

                return {
                    'enabled': hospital.bulk_discount_enabled,
                    'min_service_count': hospital.bulk_discount_min_service_count,
                    'effective_from': hospital.bulk_discount_effective_from.isoformat() if hospital.bulk_discount_effective_from else None
                }

        except Exception as e:
            logger.error(f"Error getting bulk config: {e}")
            return {'error': str(e)}

    @staticmethod
    def update_bulk_config(hospital_id: str, data: Dict) -> Tuple[bool, str]:
        """Update bulk discount configuration"""
        try:
            with get_db_session() as session:
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

                if not hospital:
                    return False, "Hospital not found"

                if 'enabled' in data:
                    hospital.bulk_discount_enabled = data['enabled']
                if 'min_service_count' in data:
                    hospital.bulk_discount_min_service_count = data['min_service_count']
                if 'effective_from' in data:
                    hospital.bulk_discount_effective_from = data['effective_from']

                session.commit()
                logger.info(f"Updated bulk config for hospital {hospital_id}")
                return True, "Bulk discount configuration updated"

        except Exception as e:
            logger.error(f"Error updating bulk config: {e}")
            return False, str(e)

    @staticmethod
    def get_bulk_eligible_items(
        hospital_id: str,
        item_type: str = 'service',
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """Get items with bulk discount configured"""
        try:
            with get_db_session(read_only=True) as session:
                if item_type == 'service':
                    query = session.query(Service).filter(
                        Service.hospital_id == hospital_id,
                        Service.is_deleted == False,
                        Service.bulk_discount_percent > 0
                    )
                    total = query.count()
                    items = query.offset((page - 1) * per_page).limit(per_page).all()

                    return {
                        'items': [
                            {
                                'item_id': str(s.service_id),
                                'item_name': s.service_name,
                                'code': s.code,
                                'price': float(s.price) if s.price else 0,
                                'bulk_discount_percent': float(s.bulk_discount_percent) if s.bulk_discount_percent else 0
                            }
                            for s in items
                        ],
                        'total': total,
                        'page': page,
                        'per_page': per_page
                    }

                elif item_type == 'medicine':
                    query = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        Medicine.is_deleted == False,
                        Medicine.bulk_discount_percent > 0
                    )
                    total = query.count()
                    items = query.offset((page - 1) * per_page).limit(per_page).all()

                    return {
                        'items': [
                            {
                                'item_id': str(m.medicine_id),
                                'item_name': m.medicine_name,
                                'code': m.generic_name or '',  # Medicine has no code field, use generic_name
                                'price': float(m.mrp) if m.mrp else 0,
                                'bulk_discount_percent': float(m.bulk_discount_percent) if m.bulk_discount_percent else 0
                            }
                            for m in items
                        ],
                        'total': total,
                        'page': page,
                        'per_page': per_page
                    }

                return {'items': [], 'total': 0, 'error': f'Invalid item type: {item_type}'}

        except Exception as e:
            logger.error(f"Error getting bulk eligible items: {e}")
            return {'items': [], 'total': 0, 'error': str(e)}

    # ==========================================================================
    # LOYALTY CONFIGURATION
    # ==========================================================================

    @staticmethod
    def get_loyalty_config(hospital_id: str) -> Dict[str, Any]:
        """Get loyalty discount configuration"""
        try:
            with get_db_session(read_only=True) as session:
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

                if not hospital:
                    return {'error': 'Hospital not found'}

                return {
                    'loyalty_discount_mode': hospital.loyalty_discount_mode or 'absolute'
                }

        except Exception as e:
            logger.error(f"Error getting loyalty config: {e}")
            return {'error': str(e)}

    @staticmethod
    def update_loyalty_mode(hospital_id: str, mode: str) -> Tuple[bool, str]:
        """Update loyalty discount mode"""
        try:
            if mode not in ['absolute', 'additional']:
                return False, "Mode must be 'absolute' or 'additional'"

            with get_db_session() as session:
                hospital = session.query(Hospital).filter_by(hospital_id=hospital_id).first()

                if not hospital:
                    return False, "Hospital not found"

                hospital.loyalty_discount_mode = mode
                session.commit()

                logger.info(f"Updated loyalty mode for hospital {hospital_id} to {mode}")
                return True, f"Loyalty discount mode updated to '{mode}'"

        except Exception as e:
            logger.error(f"Error updating loyalty mode: {e}")
            return False, str(e)

    @staticmethod
    def get_card_types(hospital_id: str) -> List[Dict]:
        """Get all loyalty card types"""
        try:
            with get_db_session(read_only=True) as session:
                card_types = session.query(LoyaltyCardType).filter(
                    LoyaltyCardType.hospital_id == hospital_id,
                    LoyaltyCardType.is_deleted == False
                ).order_by(LoyaltyCardType.discount_percent.desc()).all()

                return [
                    {
                        'card_type_id': str(ct.card_type_id),
                        'card_type_name': ct.card_type_name,
                        'card_type_code': ct.card_type_code,
                        'description': ct.description,
                        'discount_percent': float(ct.discount_percent) if ct.discount_percent else 0,
                        'min_lifetime_spend': float(ct.min_lifetime_spend) if ct.min_lifetime_spend else 0,
                        'min_visits': ct.min_visits or 0,
                        'card_color': ct.card_color,
                        'is_active': ct.is_active
                    }
                    for ct in card_types
                ]

        except Exception as e:
            logger.error(f"Error getting card types: {e}")
            return []

    # ==========================================================================
    # ANALYTICS
    # ==========================================================================

    @staticmethod
    def get_discount_breakdown(
        hospital_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Get discount breakdown by type for charts"""
        try:
            with get_db_session(read_only=True) as session:
                # Get from discount application log
                breakdown = session.query(
                    DiscountApplicationLog.applied_discount_type,
                    func.count(DiscountApplicationLog.log_id).label('count'),
                    func.sum(DiscountApplicationLog.discount_amount).label('total_amount')
                ).filter(
                    DiscountApplicationLog.hospital_id == hospital_id,
                    DiscountApplicationLog.applied_at >= start_date,
                    DiscountApplicationLog.applied_at <= end_date
                ).group_by(DiscountApplicationLog.applied_discount_type).all()

                return {
                    'labels': [b[0] or 'unknown' for b in breakdown],
                    'counts': [b[1] for b in breakdown],
                    'amounts': [float(b[2] or 0) for b in breakdown]
                }

        except Exception as e:
            logger.error(f"Error getting discount breakdown: {e}")
            return {'labels': [], 'counts': [], 'amounts': []}

    @staticmethod
    def get_usage_trends(
        hospital_id: str,
        start_date: date,
        end_date: date,
        campaign_id: Optional[str] = None,
        granularity: str = 'daily'
    ) -> Dict[str, Any]:
        """Get usage trends over time"""
        try:
            with get_db_session(read_only=True) as session:
                query = session.query(
                    func.date(PromotionUsageLog.usage_date).label('date'),
                    func.count(PromotionUsageLog.usage_id).label('count'),
                    func.sum(PromotionUsageLog.discount_amount).label('amount')
                ).filter(
                    PromotionUsageLog.hospital_id == hospital_id,
                    PromotionUsageLog.usage_date >= start_date,
                    PromotionUsageLog.usage_date <= end_date
                )

                if campaign_id:
                    query = query.filter(PromotionUsageLog.campaign_id == campaign_id)

                query = query.group_by(func.date(PromotionUsageLog.usage_date)).order_by(
                    func.date(PromotionUsageLog.usage_date)
                )

                results = query.all()

                return {
                    'dates': [r[0].isoformat() if r[0] else '' for r in results],
                    'counts': [r[1] for r in results],
                    'amounts': [float(r[2] or 0) for r in results]
                }

        except Exception as e:
            logger.error(f"Error getting usage trends: {e}")
            return {'dates': [], 'counts': [], 'amounts': []}

    @staticmethod
    def get_top_campaigns(
        hospital_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10
    ) -> List[Dict]:
        """Get top performing campaigns by usage"""
        try:
            with get_db_session(read_only=True) as session:
                results = session.query(
                    PromotionCampaign.campaign_id,
                    PromotionCampaign.campaign_code,
                    PromotionCampaign.campaign_name,
                    func.count(PromotionUsageLog.usage_id).label('usage_count'),
                    func.sum(PromotionUsageLog.discount_amount).label('total_discount'),
                    func.sum(PromotionUsageLog.invoice_amount).label('total_revenue')
                ).join(
                    PromotionUsageLog,
                    PromotionCampaign.campaign_id == PromotionUsageLog.campaign_id
                ).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionUsageLog.usage_date >= start_date,
                    PromotionUsageLog.usage_date <= end_date
                ).group_by(
                    PromotionCampaign.campaign_id,
                    PromotionCampaign.campaign_code,
                    PromotionCampaign.campaign_name
                ).order_by(
                    func.count(PromotionUsageLog.usage_id).desc()
                ).limit(limit).all()

                return [
                    {
                        'campaign_id': str(r[0]),
                        'campaign_code': r[1],
                        'campaign_name': r[2],
                        'usage_count': r[3],
                        'total_discount': float(r[4] or 0),
                        'total_revenue': float(r[5] or 0)
                    }
                    for r in results
                ]

        except Exception as e:
            logger.error(f"Error getting top campaigns: {e}")
            return []

    # ==========================================================================
    # CAMPAIGN GROUPS
    # ==========================================================================

    @staticmethod
    def get_campaign_groups(
        hospital_id: str,
        include_inactive: bool = False,
        include_item_counts: bool = True,
        include_deleted: bool = True
    ) -> List[Dict]:
        """
        Get all campaign groups for a hospital

        Args:
            hospital_id: Hospital UUID
            include_inactive: Include inactive groups
            include_item_counts: Include count of items in each group
            include_deleted: Include soft-deleted groups (shown differently in UI)

        Returns:
            List of campaign groups with details
        """
        try:
            with get_db_session(read_only=True) as session:
                query = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id
                )

                # Filter deleted unless include_deleted is True
                if not include_deleted:
                    query = query.filter(PromotionCampaignGroup.is_deleted.is_(False))

                if not include_inactive:
                    query = query.filter(PromotionCampaignGroup.is_active == True)

                # Order: active non-deleted first, then inactive, then deleted
                groups = query.order_by(
                    PromotionCampaignGroup.is_deleted,
                    PromotionCampaignGroup.is_active.desc(),
                    PromotionCampaignGroup.group_name
                ).all()

                result = []
                for group in groups:
                    group_dict = {
                        'group_id': str(group.group_id),
                        'group_code': group.group_code,
                        'group_name': group.group_name,
                        'description': group.description,
                        'is_active': group.is_active,
                        'is_deleted': group.is_deleted,
                        'deleted_at': group.deleted_at.strftime('%d %b %Y %H:%M') if group.deleted_at else None,
                        'deleted_by': group.deleted_by,
                        'created_at': group.created_at.strftime('%d %b %Y') if group.created_at else None,
                        'updated_at': group.updated_at.strftime('%d %b %Y') if group.updated_at else None
                    }

                    if include_item_counts:
                        # Get item counts by type
                        item_counts = session.query(
                            PromotionGroupItem.item_type,
                            func.count(PromotionGroupItem.group_item_id)
                        ).filter(
                            PromotionGroupItem.group_id == group.group_id
                        ).group_by(PromotionGroupItem.item_type).all()

                        counts = {'service': 0, 'medicine': 0, 'package': 0}
                        for item_type, count in item_counts:
                            counts[item_type] = count

                        group_dict['item_counts'] = counts
                        group_dict['total_items'] = sum(counts.values())

                    result.append(group_dict)

                return result

        except Exception as e:
            logger.error(f"Error getting campaign groups: {e}")
            return []

    @staticmethod
    def get_campaign_group_by_id(hospital_id: str, group_id: str) -> Optional[Dict]:
        """
        Get a single campaign group with all its items (including deleted groups for viewing)

        Args:
            hospital_id: Hospital UUID
            group_id: Group UUID

        Returns:
            Campaign group with items, or None if not found
        """
        try:
            with get_db_session(read_only=True) as session:
                # Allow viewing deleted groups (for detail page with deleted badge)
                group = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_id == group_id
                ).first()

                if not group:
                    return None

                # Get all items in this group with their details
                items = session.query(PromotionGroupItem).filter(
                    PromotionGroupItem.group_id == group_id
                ).all()

                # Fetch item details
                services = []
                medicines = []
                packages = []

                for item in items:
                    if item.item_type == 'service':
                        service = session.query(Service).filter_by(service_id=item.item_id).first()
                        if service:
                            services.append({
                                'group_item_id': str(item.group_item_id),
                                'item_id': str(item.item_id),
                                'item_name': service.service_name,
                                'price': float(service.price) if service.price else 0,
                                'is_active': service.is_active
                            })
                    elif item.item_type == 'medicine':
                        medicine = session.query(Medicine).filter_by(medicine_id=item.item_id).first()
                        if medicine:
                            medicines.append({
                                'group_item_id': str(item.group_item_id),
                                'item_id': str(item.item_id),
                                'item_name': medicine.medicine_name,
                                'price': float(medicine.selling_price) if medicine.selling_price else 0,
                                'is_active': medicine.status == 'active' if hasattr(medicine, 'status') else True
                            })
                    elif item.item_type == 'package':
                        package = session.query(Package).filter_by(package_id=item.item_id).first()
                        if package:
                            packages.append({
                                'group_item_id': str(item.group_item_id),
                                'item_id': str(item.item_id),
                                'item_name': package.package_name,
                                'price': float(package.price) if package.price else 0,
                                'is_active': package.status == 'active' if hasattr(package, 'status') else True
                            })

                # Count campaigns targeting this group (using raw SQL to avoid JSONB issues)
                campaigns_using_query = text("""
                    SELECT COUNT(*) FROM promotion_campaigns
                    WHERE hospital_id = :hospital_id
                    AND is_deleted = FALSE
                    AND target_groups->'group_ids' @> :group_id_json
                """)
                campaigns_using = session.execute(
                    campaigns_using_query,
                    {'hospital_id': hospital_id, 'group_id_json': f'["{group_id}"]'}
                ).scalar() or 0

                return {
                    'group_id': str(group.group_id),
                    'group_code': group.group_code,
                    'group_name': group.group_name,
                    'description': group.description,
                    'is_active': group.is_active,
                    'is_deleted': group.is_deleted,
                    'deleted_at': group.deleted_at.strftime('%d %b %Y %H:%M') if group.deleted_at else None,
                    'deleted_by': group.deleted_by,
                    'created_at': group.created_at.strftime('%d %b %Y %H:%M') if group.created_at else None,
                    'updated_at': group.updated_at.strftime('%d %b %Y %H:%M') if group.updated_at else None,
                    'services': services,
                    'medicines': medicines,
                    'packages': packages,
                    'total_items': len(services) + len(medicines) + len(packages),
                    'campaigns_using': campaigns_using
                }

        except Exception as e:
            logger.error(f"Error getting campaign group: {e}")
            return None

    @staticmethod
    def create_campaign_group(hospital_id: str, data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new campaign group

        Args:
            hospital_id: Hospital UUID
            data: Group data (group_code, group_name, description)

        Returns:
            Tuple of (success, message, group_id)
        """
        try:
            with get_db_session() as session:
                # Check for duplicate code (only among non-deleted groups)
                existing = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_code == data['group_code'],
                    PromotionCampaignGroup.is_deleted.is_(False)
                ).first()

                if existing:
                    return False, f"Group code '{data['group_code']}' already exists", None

                group = PromotionCampaignGroup(
                    hospital_id=hospital_id,
                    group_code=data['group_code'].upper(),
                    group_name=data['group_name'],
                    description=data.get('description', ''),
                    is_active=data.get('is_active', True)
                )

                session.add(group)
                session.flush()  # Flush to get the group_id before commit

                # Capture values before commit
                group_id = str(group.group_id)
                group_name = data['group_name']
                group_code = data['group_code']

                session.commit()

                logger.info(f"Created campaign group '{group_code}' for hospital {hospital_id}")
                return True, f"Campaign group '{group_name}' created successfully", group_id

        except Exception as e:
            logger.error(f"Error creating campaign group: {e}")
            return False, str(e), None

    @staticmethod
    def update_campaign_group(hospital_id: str, group_id: str, data: Dict) -> Tuple[bool, str]:
        """
        Update an existing campaign group

        Args:
            hospital_id: Hospital UUID
            group_id: Group UUID
            data: Updated group data

        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                group = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_id == group_id,
                    PromotionCampaignGroup.is_deleted.is_(False)
                ).first()

                if not group:
                    return False, "Campaign group not found"

                # Check for duplicate code if changing
                if 'group_code' in data and data['group_code'] != group.group_code:
                    existing = session.query(PromotionCampaignGroup).filter(
                        PromotionCampaignGroup.hospital_id == hospital_id,
                        PromotionCampaignGroup.group_code == data['group_code'],
                        PromotionCampaignGroup.group_id != group_id,
                        PromotionCampaignGroup.is_deleted.is_(False)
                    ).first()

                    if existing:
                        return False, f"Group code '{data['group_code']}' already exists"

                    group.group_code = data['group_code'].upper()

                if 'group_name' in data:
                    group.group_name = data['group_name']
                if 'description' in data:
                    group.description = data['description']
                if 'is_active' in data:
                    group.is_active = data['is_active']

                # Capture name before commit
                group_name = group.group_name
                session.commit()

                logger.info(f"Updated campaign group {group_id}")
                return True, f"Campaign group '{group_name}' updated successfully"

        except Exception as e:
            logger.error(f"Error updating campaign group: {e}")
            return False, str(e)

    @staticmethod
    def delete_campaign_group(hospital_id: str, group_id: str) -> Tuple[bool, str]:
        """
        Delete a campaign group (and its item associations)

        Args:
            hospital_id: Hospital UUID
            group_id: Group UUID

        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                group = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_id == group_id,
                    PromotionCampaignGroup.is_deleted.is_(False)
                ).first()

                if not group:
                    return False, "Campaign group not found"

                # Check if any campaigns are using this group
                # Use text-based JSONB query to avoid SQLAlchemy boolean evaluation issues
                campaigns_using_query = text("""
                    SELECT COUNT(*) FROM promotion_campaigns
                    WHERE hospital_id = :hospital_id
                    AND is_deleted = FALSE
                    AND target_groups->'group_ids' @> :group_id_json
                """)
                campaigns_using = session.execute(
                    campaigns_using_query,
                    {'hospital_id': hospital_id, 'group_id_json': f'["{group_id}"]'}
                ).scalar() or 0

                if campaigns_using > 0:
                    return False, f"Cannot delete: {campaigns_using} campaign(s) are using this group"

                group_name = group.group_name

                # Soft delete - set is_deleted flag instead of hard delete
                group.is_deleted = True
                group.deleted_at = datetime.now()
                # Note: deleted_by would need current_user passed in
                session.commit()

                logger.info(f"Soft deleted campaign group {group_id}")
                return True, f"Campaign group '{group_name}' deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting campaign group: {e}")
            return False, str(e)

    @staticmethod
    def undelete_campaign_group(hospital_id: str, group_id: str) -> Tuple[bool, str]:
        """
        Restore a soft-deleted campaign group

        Args:
            hospital_id: Hospital UUID
            group_id: Group UUID

        Returns:
            Tuple of (success, message)
        """
        try:
            with get_db_session() as session:
                group = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_id == group_id,
                    PromotionCampaignGroup.is_deleted.is_(True)
                ).first()

                if not group:
                    return False, "Deleted campaign group not found"

                group_name = group.group_name

                # Restore the group
                group.is_deleted = False
                group.deleted_at = None
                group.deleted_by = None
                session.commit()

                logger.info(f"Restored campaign group {group_id}")
                return True, f"Campaign group '{group_name}' restored successfully"

        except Exception as e:
            logger.error(f"Error restoring campaign group: {e}")
            return False, str(e)

    @staticmethod
    def toggle_campaign_group_status(hospital_id: str, group_id: str) -> Tuple[bool, str]:
        """Toggle campaign group active status"""
        try:
            with get_db_session() as session:
                group = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_id == group_id,
                    PromotionCampaignGroup.is_deleted.is_(False)
                ).first()

                if not group:
                    return False, "Campaign group not found"

                # Toggle and capture values before commit
                new_status = not group.is_active
                group_name = group.group_name
                group.is_active = new_status
                session.commit()

                status = 'activated' if new_status else 'deactivated'
                logger.info(f"Toggled campaign group {group_id} to {status}")
                return True, f"Campaign group '{group_name}' {status}"

        except Exception as e:
            logger.error(f"Error toggling campaign group status: {e}")
            return False, str(e)

    @staticmethod
    def add_items_to_group(
        hospital_id: str,
        group_id: str,
        items: List[Dict]
    ) -> Tuple[bool, str, int]:
        """
        Add items to a campaign group

        Args:
            hospital_id: Hospital UUID
            group_id: Group UUID
            items: List of {item_type, item_id} dicts

        Returns:
            Tuple of (success, message, items_added_count)
        """
        try:
            with get_db_session() as session:
                # Verify group exists and is not deleted
                group = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_id == group_id,
                    PromotionCampaignGroup.is_deleted.is_(False)
                ).first()

                if not group:
                    return False, "Campaign group not found", 0

                added_count = 0
                skipped_count = 0

                for item in items:
                    item_type = item.get('item_type', '').lower()
                    item_id = item.get('item_id')

                    if not item_type or not item_id:
                        continue

                    if item_type not in ['service', 'medicine', 'package']:
                        continue

                    # Check if already exists
                    existing = session.query(PromotionGroupItem).filter(
                        PromotionGroupItem.group_id == group_id,
                        PromotionGroupItem.item_type == item_type,
                        PromotionGroupItem.item_id == item_id
                    ).first()

                    if existing:
                        skipped_count += 1
                        continue

                    # Add new item
                    group_item = PromotionGroupItem(
                        group_id=group_id,
                        item_type=item_type,
                        item_id=item_id
                    )
                    session.add(group_item)
                    added_count += 1

                session.commit()

                message = f"Added {added_count} item(s) to group"
                if skipped_count > 0:
                    message += f" ({skipped_count} already existed)"

                logger.info(f"Added {added_count} items to group {group_id}")
                return True, message, added_count

        except Exception as e:
            logger.error(f"Error adding items to group: {e}")
            return False, str(e), 0

    @staticmethod
    def remove_items_from_group(
        hospital_id: str,
        group_id: str,
        group_item_ids: List[str]
    ) -> Tuple[bool, str, int]:
        """
        Remove items from a campaign group

        Args:
            hospital_id: Hospital UUID
            group_id: Group UUID
            group_item_ids: List of group_item_id UUIDs to remove

        Returns:
            Tuple of (success, message, items_removed_count)
        """
        try:
            with get_db_session() as session:
                # Verify group exists and is not deleted
                group = session.query(PromotionCampaignGroup).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.group_id == group_id,
                    PromotionCampaignGroup.is_deleted.is_(False)
                ).first()

                if not group:
                    return False, "Campaign group not found", 0

                removed_count = session.query(PromotionGroupItem).filter(
                    PromotionGroupItem.group_id == group_id,
                    PromotionGroupItem.group_item_id.in_(group_item_ids)
                ).delete(synchronize_session=False)

                session.commit()

                logger.info(f"Removed {removed_count} items from group {group_id}")
                return True, f"Removed {removed_count} item(s) from group", removed_count

        except Exception as e:
            logger.error(f"Error removing items from group: {e}")
            return False, str(e), 0

    @staticmethod
    def get_item_groups(hospital_id: str, item_type: str, item_id: str) -> List[Dict]:
        """
        Get all campaign groups an item belongs to

        Args:
            hospital_id: Hospital UUID
            item_type: 'service', 'medicine', or 'package'
            item_id: Item UUID

        Returns:
            List of groups the item belongs to
        """
        try:
            with get_db_session(read_only=True) as session:
                groups = session.query(PromotionCampaignGroup).join(
                    PromotionGroupItem,
                    PromotionCampaignGroup.group_id == PromotionGroupItem.group_id
                ).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.is_active == True,
                    PromotionCampaignGroup.is_deleted.is_(False),
                    PromotionGroupItem.item_type == item_type.lower(),
                    PromotionGroupItem.item_id == item_id
                ).all()

                return [
                    {
                        'group_id': str(g.group_id),
                        'group_code': g.group_code,
                        'group_name': g.group_name
                    }
                    for g in groups
                ]

        except Exception as e:
            logger.error(f"Error getting item groups: {e}")
            return []

    @staticmethod
    def get_available_items_for_group(
        hospital_id: str,
        group_id: str,
        item_type: str,
        search: str = ''
    ) -> List[Dict]:
        """
        Get items available to add to a group (not already in group)

        Args:
            hospital_id: Hospital UUID
            group_id: Group UUID
            item_type: 'service', 'medicine', or 'package'
            search: Optional search term

        Returns:
            List of available items
        """
        try:
            with get_db_session(read_only=True) as session:
                # Get items already in group
                existing_ids = session.query(PromotionGroupItem.item_id).filter(
                    PromotionGroupItem.group_id == group_id,
                    PromotionGroupItem.item_type == item_type.lower()
                ).all()
                existing_ids = [str(e[0]) for e in existing_ids]

                results = []

                if item_type.lower() == 'service':
                    query = session.query(Service).filter(
                        Service.hospital_id == hospital_id,
                        Service.is_active == True,
                        Service.is_deleted == False
                    )
                    if existing_ids:
                        query = query.filter(~Service.service_id.in_(existing_ids))
                    if search:
                        query = query.filter(Service.service_name.ilike(f'%{search}%'))

                    items = query.order_by(Service.service_name).limit(50).all()
                    results = [
                        {
                            'item_id': str(s.service_id),
                            'item_name': s.service_name,
                            'price': float(s.price) if s.price else 0
                        }
                        for s in items
                    ]

                elif item_type.lower() == 'medicine':
                    query = session.query(Medicine).filter(
                        Medicine.hospital_id == hospital_id,
                        Medicine.status == 'active',
                        Medicine.is_deleted == False
                    )
                    if existing_ids:
                        query = query.filter(~Medicine.medicine_id.in_(existing_ids))
                    if search:
                        query = query.filter(Medicine.medicine_name.ilike(f'%{search}%'))

                    items = query.order_by(Medicine.medicine_name).limit(50).all()
                    results = [
                        {
                            'item_id': str(m.medicine_id),
                            'item_name': m.medicine_name,
                            'price': float(m.selling_price) if m.selling_price else 0
                        }
                        for m in items
                    ]

                elif item_type.lower() == 'package':
                    query = session.query(Package).filter(
                        Package.hospital_id == hospital_id,
                        Package.status == 'active',
                        Package.is_deleted == False
                    )
                    if existing_ids:
                        query = query.filter(~Package.package_id.in_(existing_ids))
                    if search:
                        query = query.filter(Package.package_name.ilike(f'%{search}%'))

                    items = query.order_by(Package.package_name).limit(50).all()
                    results = [
                        {
                            'item_id': str(p.package_id),
                            'item_name': p.package_name,
                            'price': float(p.price) if p.price else 0
                        }
                        for p in items
                    ]

                return results

        except Exception as e:
            logger.error(f"Error getting available items: {e}")
            return []

    @staticmethod
    def get_groups_summary(hospital_id: str) -> Dict[str, Any]:
        """Get summary statistics for campaign groups"""
        try:
            with get_db_session(read_only=True) as session:
                # Total groups
                total_groups = session.query(func.count(PromotionCampaignGroup.group_id)).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id
                ).scalar() or 0

                # Active groups
                active_groups = session.query(func.count(PromotionCampaignGroup.group_id)).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id,
                    PromotionCampaignGroup.is_active == True
                ).scalar() or 0

                # Total items across all groups
                total_items = session.query(func.count(PromotionGroupItem.group_item_id)).join(
                    PromotionCampaignGroup,
                    PromotionGroupItem.group_id == PromotionCampaignGroup.group_id
                ).filter(
                    PromotionCampaignGroup.hospital_id == hospital_id
                ).scalar() or 0

                # Campaigns using groups
                campaigns_with_groups = session.query(func.count(PromotionCampaign.campaign_id)).filter(
                    PromotionCampaign.hospital_id == hospital_id,
                    PromotionCampaign.is_deleted.is_(False),
                    PromotionCampaign.target_groups.isnot(None)
                ).scalar() or 0

                return {
                    'total_groups': total_groups,
                    'active_groups': active_groups,
                    'inactive_groups': total_groups - active_groups,
                    'total_items': total_items,
                    'campaigns_with_groups': campaigns_with_groups
                }

        except Exception as e:
            logger.error(f"Error getting groups summary: {e}")
            return {
                'total_groups': 0,
                'active_groups': 0,
                'inactive_groups': 0,
                'total_items': 0,
                'campaigns_with_groups': 0
            }
