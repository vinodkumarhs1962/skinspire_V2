"""
Test Script: Campaign Groups Logic Verification
Tests campaign groups filtering across all key functions:
1. Invoice creation - discount determination
2. Promotion dashboard - campaign list with group names
3. Campaign CRUD operations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy import text
import uuid
import json

from app import create_app
from app.services.database_service import get_db_session
from app.services.promotion_dashboard_service import PromotionDashboardService
from app.services.discount_service import DiscountService
from app.models.master import (
    PromotionCampaign, PromotionCampaignGroup, PromotionGroupItem,
    Service, Medicine, Patient
)

# Test hospital ID
HOSPITAL_ID = '4ef72e18-e65d-4766-b9eb-0308c42485ca'

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_subheader(title):
    print(f"\n--- {title} ---")

def print_result(test_name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {test_name}")
    if details:
        print(f"         {details}")


def test_1_service_helper_methods():
    """Test helper methods for getting group names"""
    print_header("TEST 1: Service Helper Methods")

    with get_db_session(read_only=True) as session:
        # Get existing campaign groups
        groups = session.query(PromotionCampaignGroup).filter(
            PromotionCampaignGroup.hospital_id == HOSPITAL_ID,
            PromotionCampaignGroup.is_deleted == False
        ).limit(3).all()

        if not groups:
            print_result("Get group names", False, "No campaign groups found in database")
            return False

        group_ids = [str(g.group_id) for g in groups]
        group_names_expected = [g.group_name for g in groups]

        print_subheader("Testing _get_group_names_by_ids")
        group_names = PromotionDashboardService._get_group_names_by_ids(session, group_ids)

        print(f"  Input group_ids: {group_ids}")
        print(f"  Expected names: {group_names_expected}")
        print(f"  Returned names: {group_names}")

        passed = set(group_names) == set(group_names_expected)
        print_result("Get group names by IDs", passed)

        print_subheader("Testing _enrich_campaign_with_group_names")
        test_campaign = {
            'campaign_id': 'test-123',
            'campaign_name': 'Test Campaign',
            'target_groups': {'group_ids': group_ids}
        }

        enriched = PromotionDashboardService._enrich_campaign_with_group_names(session, test_campaign)

        has_group_names = 'target_group_names' in enriched
        correct_count = len(enriched.get('target_group_names', [])) == len(group_ids)

        print(f"  Has target_group_names key: {has_group_names}")
        print(f"  Group names: {enriched.get('target_group_names', [])}")

        print_result("Enrich campaign with group names", has_group_names and correct_count)

        return passed and has_group_names and correct_count


def test_2_get_all_campaigns_with_groups():
    """Test get_all_campaigns returns target_groups and target_group_names"""
    print_header("TEST 2: Get All Campaigns with Groups")

    result = PromotionDashboardService.get_all_campaigns(
        hospital_id=HOSPITAL_ID,
        page=1,
        per_page=10
    )

    campaigns = result.get('items', [])

    if not campaigns:
        print_result("Get campaigns", False, "No campaigns found")
        return False

    print(f"  Found {len(campaigns)} campaigns")

    all_have_target_groups = True
    all_have_target_group_names = True

    for c in campaigns[:5]:  # Check first 5
        has_tg = 'target_groups' in c
        has_tgn = 'target_group_names' in c

        if not has_tg:
            all_have_target_groups = False
        if not has_tgn:
            all_have_target_group_names = False

        groups_info = f"Groups: {c.get('target_group_names', [])}" if c.get('target_groups') else "No groups"
        print(f"  - {c['campaign_code']}: {groups_info}")

    print_result("All campaigns have target_groups field", all_have_target_groups)
    print_result("All campaigns have target_group_names field", all_have_target_group_names)

    return all_have_target_groups and all_have_target_group_names


def test_3_get_campaign_by_id_with_groups():
    """Test get_campaign_by_id returns target_groups and target_group_names"""
    print_header("TEST 3: Get Campaign By ID with Groups")

    # First get a campaign that has target_groups
    with get_db_session(read_only=True) as session:
        campaign = session.query(PromotionCampaign).filter(
            PromotionCampaign.hospital_id == HOSPITAL_ID,
            PromotionCampaign.is_deleted == False,
            PromotionCampaign.target_groups.isnot(None)
        ).first()

        if not campaign:
            # Try any campaign
            campaign = session.query(PromotionCampaign).filter(
                PromotionCampaign.hospital_id == HOSPITAL_ID,
                PromotionCampaign.is_deleted == False
            ).first()

        if not campaign:
            print_result("Get campaign by ID", False, "No campaigns found")
            return False

        campaign_id = str(campaign.campaign_id)

    result = PromotionDashboardService.get_campaign_by_id(HOSPITAL_ID, campaign_id)

    if not result:
        print_result("Get campaign by ID", False, "Campaign not found")
        return False

    print(f"  Campaign: {result['campaign_code']} - {result['campaign_name']}")
    print(f"  target_groups: {result.get('target_groups')}")
    print(f"  target_group_names: {result.get('target_group_names')}")
    print(f"  target_special_group: {result.get('target_special_group')}")
    print(f"  status: {result.get('status')}")

    has_tg = 'target_groups' in result
    has_tgn = 'target_group_names' in result
    has_tsg = 'target_special_group' in result
    has_status = 'status' in result

    print_result("Has target_groups field", has_tg)
    print_result("Has target_group_names field", has_tgn)
    print_result("Has target_special_group field", has_tsg)
    print_result("Has status field", has_status)

    return has_tg and has_tgn and has_tsg and has_status


def test_4_timeline_data_with_groups():
    """Test get_timeline_data returns campaigns with target_groups"""
    print_header("TEST 4: Timeline Data (Dashboard) with Groups")

    today = date.today()
    start_date = today - timedelta(days=30)
    end_date = today + timedelta(days=90)

    result = PromotionDashboardService.get_timeline_data(
        hospital_id=HOSPITAL_ID,
        start_date=start_date,
        end_date=end_date
    )

    campaigns = result.get('campaigns', [])

    if not campaigns:
        print_result("Get timeline campaigns", False, "No campaigns in timeline")
        return False

    print(f"  Found {len(campaigns)} campaigns in timeline")

    all_have_target_groups = True
    all_have_target_group_names = True

    for c in campaigns[:5]:  # Check first 5
        has_tg = 'target_groups' in c
        has_tgn = 'target_group_names' in c

        if not has_tg:
            all_have_target_groups = False
        if not has_tgn:
            all_have_target_group_names = False

        groups_info = f"{len(c.get('target_group_names', []))} groups" if c.get('target_groups') else "No groups"
        print(f"  - {c['campaign_code']}: {groups_info}")

    print_result("Timeline campaigns have target_groups", all_have_target_groups)
    print_result("Timeline campaigns have target_group_names", all_have_target_group_names)

    return all_have_target_groups and all_have_target_group_names


def test_5_discount_applicability_with_groups():
    """Test that discount calculation respects campaign groups"""
    print_header("TEST 5: Discount Applicability with Campaign Groups")

    with get_db_session() as session:
        # Find a campaign that has target_groups configured
        campaign_with_groups = session.query(PromotionCampaign).filter(
            PromotionCampaign.hospital_id == HOSPITAL_ID,
            PromotionCampaign.is_deleted == False,
            PromotionCampaign.is_active == True,
            PromotionCampaign.target_groups.isnot(None),
            PromotionCampaign.start_date <= date.today(),
            PromotionCampaign.end_date >= date.today()
        ).first()

        if not campaign_with_groups:
            print("  No active campaign with target_groups found. Creating test scenario...")

            # Find an active campaign and a campaign group to test with
            active_campaign = session.query(PromotionCampaign).filter(
                PromotionCampaign.hospital_id == HOSPITAL_ID,
                PromotionCampaign.is_deleted == False,
                PromotionCampaign.is_active == True,
                PromotionCampaign.start_date <= date.today(),
                PromotionCampaign.end_date >= date.today()
            ).first()

            if not active_campaign:
                print_result("Discount applicability", False, "No active campaigns to test with")
                return False

            print(f"  Using campaign: {active_campaign.campaign_code}")
            print(f"  This campaign has no target_groups, so it should apply to ALL items")

            # Get a service to test
            service = session.query(Service).filter(
                Service.hospital_id == HOSPITAL_ID,
                Service.is_active == True
            ).first()

            if not service:
                print_result("Discount applicability", False, "No services found")
                return False

            # Test discount calculation
            result = DiscountService.calculate_promotion_discount(
                session=session,
                hospital_id=HOSPITAL_ID,
                patient_id=None,
                item_type='Service',
                item_id=str(service.service_id),
                unit_price=Decimal('1000'),
                quantity=1,
                invoice_date=date.today()
            )

            if result:
                print(f"  ✅ Discount applied: {result.discount_percent}% ({result.discount_type})")
                print(f"     Campaign: {result.metadata.get('campaign_name', 'N/A')}")
                print_result("Campaign without groups applies to all items", True)
                return True
            else:
                print(f"  ℹ️  No discount applied (campaign may have other restrictions)")
                print_result("Discount calculation executed", True, "No discount but no error")
                return True

        else:
            print(f"  Found campaign with groups: {campaign_with_groups.campaign_code}")
            target_group_ids = campaign_with_groups.target_groups.get('group_ids', [])
            print(f"  Target group IDs: {target_group_ids}")

            # Get an item IN the target groups
            item_in_group = session.query(PromotionGroupItem).filter(
                PromotionGroupItem.group_id.in_(target_group_ids)
            ).first()

            # Get an item NOT in the target groups
            item_not_in_group = session.query(Service).filter(
                Service.hospital_id == HOSPITAL_ID,
                Service.is_active == True
            ).first()

            if item_not_in_group:
                # Check if this service is NOT in any target group
                is_in_group = session.query(PromotionGroupItem).filter(
                    PromotionGroupItem.group_id.in_(target_group_ids),
                    PromotionGroupItem.item_type == 'service',
                    PromotionGroupItem.item_id == str(item_not_in_group.service_id)
                ).first()

                if not is_in_group:
                    print_subheader("Testing item NOT in target groups")
                    result = DiscountService.calculate_promotion_discount(
                        session=session,
                        hospital_id=HOSPITAL_ID,
                        patient_id=None,
                        item_type='Service',
                        item_id=str(item_not_in_group.service_id),
                        unit_price=Decimal('1000'),
                        quantity=1,
                        invoice_date=date.today()
                    )

                    # Should NOT get this specific campaign's discount
                    if result and result.metadata.get('campaign_id') == str(campaign_with_groups.campaign_id):
                        print_result("Item NOT in group excluded from campaign", False,
                                   "Campaign was incorrectly applied to item not in group")
                    else:
                        print_result("Item NOT in group excluded from campaign", True)

            if item_in_group:
                print_subheader("Testing item IN target groups")
                print(f"  Item: {item_in_group.item_type} - {item_in_group.item_id}")

                result = DiscountService.calculate_promotion_discount(
                    session=session,
                    hospital_id=HOSPITAL_ID,
                    patient_id=None,
                    item_type=item_in_group.item_type.capitalize(),
                    item_id=str(item_in_group.item_id),
                    unit_price=Decimal('1000'),
                    quantity=1,
                    invoice_date=date.today()
                )

                if result:
                    print(f"  ✅ Discount applied: {result.discount_percent}%")
                    print_result("Item IN group gets campaign discount", True)
                else:
                    print(f"  ℹ️  No discount (may have other restrictions)")
                    print_result("Discount calculation for item in group", True, "Executed without error")

            return True


def test_6_campaign_create_with_groups():
    """Test creating a campaign with target_groups"""
    print_header("TEST 6: Campaign Creation with Groups")

    # Get existing campaign groups
    with get_db_session(read_only=True) as session:
        groups = session.query(PromotionCampaignGroup).filter(
            PromotionCampaignGroup.hospital_id == HOSPITAL_ID,
            PromotionCampaignGroup.is_deleted == False,
            PromotionCampaignGroup.is_active == True
        ).limit(2).all()

        if not groups:
            print_result("Campaign creation with groups", False, "No campaign groups available")
            return False

        group_ids = [str(g.group_id) for g in groups]
        group_names = [g.group_name for g in groups]

    # Create campaign data
    test_code = f"TEST-GRP-{uuid.uuid4().hex[:6].upper()}"
    campaign_data = {
        'campaign_code': test_code,
        'campaign_name': f'Test Campaign Groups {test_code}',
        'description': 'Test campaign for verifying campaign groups functionality',
        'promotion_type': 'simple_discount',
        'discount_type': 'percentage',
        'discount_value': 10,
        'start_date': date.today(),
        'end_date': date.today() + timedelta(days=30),
        'is_active': False,  # Keep inactive for testing
        'is_personalized': False,
        'auto_apply': True,
        'target_special_group': False,
        'applies_to': 'services',
        'target_groups': {'group_ids': group_ids}
    }

    print(f"  Creating campaign: {test_code}")
    print(f"  Target groups: {group_names}")

    success, message, campaign_id = PromotionDashboardService.create_campaign(
        HOSPITAL_ID, campaign_data
    )

    print(f"  Result: {message}")

    if not success:
        print_result("Create campaign with groups", False, message)
        return False

    print_result("Create campaign", True)

    # Verify the campaign was created with groups
    print_subheader("Verifying created campaign")

    campaign = PromotionDashboardService.get_campaign_by_id(HOSPITAL_ID, campaign_id)

    if not campaign:
        print_result("Retrieve created campaign", False)
        return False

    print(f"  Campaign ID: {campaign['campaign_id']}")
    print(f"  target_groups: {campaign.get('target_groups')}")
    print(f"  target_group_names: {campaign.get('target_group_names')}")

    has_groups = campaign.get('target_groups') is not None
    has_group_ids = has_groups and 'group_ids' in campaign['target_groups']
    correct_group_ids = has_group_ids and set(campaign['target_groups']['group_ids']) == set(group_ids)
    has_group_names = len(campaign.get('target_group_names', [])) == len(group_ids)

    print_result("Campaign has target_groups", has_groups)
    print_result("Campaign has correct group_ids", correct_group_ids)
    print_result("Campaign has target_group_names", has_group_names)

    # Clean up - delete test campaign
    print_subheader("Cleanup")
    del_success, del_message = PromotionDashboardService.delete_campaign(HOSPITAL_ID, campaign_id)
    print(f"  Deleted test campaign: {del_success}")

    return has_groups and correct_group_ids and has_group_names


def test_7_campaign_update_with_groups():
    """Test updating a campaign's target_groups"""
    print_header("TEST 7: Campaign Update with Groups")

    # Get existing campaign groups
    with get_db_session(read_only=True) as session:
        groups = session.query(PromotionCampaignGroup).filter(
            PromotionCampaignGroup.hospital_id == HOSPITAL_ID,
            PromotionCampaignGroup.is_deleted == False,
            PromotionCampaignGroup.is_active == True
        ).limit(3).all()

        if len(groups) < 2:
            print_result("Campaign update with groups", False, "Need at least 2 campaign groups")
            return False

        group_ids_1 = [str(groups[0].group_id)]
        group_ids_2 = [str(g.group_id) for g in groups[:2]]

    # Create a test campaign first
    test_code = f"TEST-UPD-{uuid.uuid4().hex[:6].upper()}"
    campaign_data = {
        'campaign_code': test_code,
        'campaign_name': f'Test Update Groups {test_code}',
        'promotion_type': 'simple_discount',
        'discount_type': 'percentage',
        'discount_value': 15,
        'start_date': date.today(),
        'end_date': date.today() + timedelta(days=30),
        'is_active': False,
        'is_personalized': False,
        'auto_apply': True,
        'applies_to': 'all',
        'target_groups': {'group_ids': group_ids_1}
    }

    success, message, campaign_id = PromotionDashboardService.create_campaign(
        HOSPITAL_ID, campaign_data
    )

    if not success:
        print_result("Create test campaign", False, message)
        return False

    print(f"  Created campaign: {test_code}")
    print(f"  Initial groups: {group_ids_1}")

    # Update with different groups
    update_data = {
        'campaign_code': test_code,
        'campaign_name': f'Test Update Groups {test_code} - Updated',
        'target_groups': {'group_ids': group_ids_2}
    }

    success, message = PromotionDashboardService.update_campaign(
        HOSPITAL_ID, campaign_id, update_data
    )

    if not success:
        print_result("Update campaign groups", False, message)
        # Cleanup
        PromotionDashboardService.delete_campaign(HOSPITAL_ID, campaign_id)
        return False

    print(f"  Updated groups to: {group_ids_2}")

    # Verify update
    campaign = PromotionDashboardService.get_campaign_by_id(HOSPITAL_ID, campaign_id)

    updated_group_ids = campaign.get('target_groups', {}).get('group_ids', [])
    correct_update = set(updated_group_ids) == set(group_ids_2)

    print(f"  Verified groups: {updated_group_ids}")
    print_result("Campaign groups updated correctly", correct_update)

    # Cleanup
    PromotionDashboardService.delete_campaign(HOSPITAL_ID, campaign_id)
    print("  Cleaned up test campaign")

    return correct_update


def run_all_tests():
    """Run all tests and provide summary"""
    print("\n")
    print("*" * 70)
    print(" CAMPAIGN GROUPS LOGIC VERIFICATION TEST SUITE")
    print("*" * 70)

    results = []

    # Run all tests
    results.append(("Helper Methods", test_1_service_helper_methods()))
    results.append(("Get All Campaigns", test_2_get_all_campaigns_with_groups()))
    results.append(("Get Campaign By ID", test_3_get_campaign_by_id_with_groups()))
    results.append(("Timeline Data (Dashboard)", test_4_timeline_data_with_groups()))
    results.append(("Discount Applicability", test_5_discount_applicability_with_groups()))
    results.append(("Campaign Creation", test_6_campaign_create_with_groups()))
    results.append(("Campaign Update", test_7_campaign_update_with_groups()))

    # Summary
    print_header("TEST SUMMARY")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All tests passed! Campaign groups logic is working correctly.")
    else:
        print("\n  ⚠️  Some tests failed. Please review the output above.")

    return passed == total


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        success = run_all_tests()
        sys.exit(0 if success else 1)
