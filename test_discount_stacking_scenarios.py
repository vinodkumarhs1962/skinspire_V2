"""
Comprehensive Test Script for Discount Stacking Scenarios
Tests all combinations of discount stacking configurations

Run with: python test_discount_stacking_scenarios.py
"""

import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from app.services.discount_service import DiscountService


def print_result(scenario_name, result, expected=None):
    """Pretty print test result"""
    print(f"\n{'='*70}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*70}")
    print(f"Total Discount: {result['total_percent']}%")
    print(f"Capped: {result['capped']}")
    if result['capped']:
        print(f"Original (before cap): {result['cap_applied']}%")

    print(f"\nBreakdown:")
    for item in result['breakdown']:
        print(f"  - {item['source']}: {item['percent']}% ({item['mode']})")

    print(f"\nApplied Discounts:")
    for item in result['applied_discounts']:
        print(f"  - {item['source']}: {item['percent']}% ({item.get('name', '')})")

    if result['excluded_discounts']:
        print(f"\nExcluded Discounts:")
        for item in result['excluded_discounts']:
            print(f"  - {item['source']}: {item['reason']}")

    if expected is not None:
        status = "PASS" if result['total_percent'] == expected else "FAIL"
        print(f"\nExpected: {expected}% | Actual: {result['total_percent']}% | {status}")
        return status == "PASS"
    return True


def test_scenarios():
    """Run all test scenarios"""

    results = []

    # =========================================================================
    # SCENARIO 1: Exclusive Campaign - Only campaign applies
    # =========================================================================
    config_1 = {
        'campaign': {'mode': 'exclusive', 'buy_x_get_y_exclusive': True},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': True},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_1 = {
        'campaign': {'percent': 15, 'type': 'percentage', 'name': 'Summer Sale'},
        'bulk': {'percent': 5},
        'loyalty': {'percent': 3, 'card_type': 'Gold'},
        'vip': {'percent': 10}
    }

    result_1 = DiscountService.calculate_stacked_discount(discounts_1, config_1)
    results.append(print_result(
        "1. Exclusive Campaign Mode",
        result_1,
        expected=15.0
    ))

    # =========================================================================
    # SCENARIO 2: Incremental Campaign + All Incremental
    # =========================================================================
    config_2 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'incremental'},
        'max_total_discount': None
    }

    discounts_2 = {
        'campaign': {'percent': 10, 'type': 'percentage', 'name': 'Monsoon Offer'},
        'bulk': {'percent': 5},
        'loyalty': {'percent': 3, 'card_type': 'Silver'},
        'vip': {'percent': 8}
    }

    result_2 = DiscountService.calculate_stacked_discount(discounts_2, config_2)
    results.append(print_result(
        "2. All Incremental (Campaign 10 + Bulk 5 + Loyalty 3 + VIP 8)",
        result_2,
        expected=26.0  # 10 + 5 + 3 + 8 = 26
    ))

    # =========================================================================
    # SCENARIO 3: Incremental Campaign + Bulk Excluded with Campaign
    # =========================================================================
    config_3 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': True},
        'vip': {'mode': 'incremental'},
        'max_total_discount': None
    }

    discounts_3 = {
        'campaign': {'percent': 10, 'type': 'percentage', 'name': 'Festival Sale'},
        'bulk': {'percent': 5},
        'loyalty': {'percent': 3, 'card_type': 'Gold'},
        'vip': {'percent': 8}
    }

    result_3 = DiscountService.calculate_stacked_discount(discounts_3, config_3)
    results.append(print_result(
        "3. Incremental Campaign + Bulk Excluded (Campaign 10 + Loyalty 3 + VIP 8, no Bulk)",
        result_3,
        expected=21.0  # 10 + 3 + 8 = 21 (bulk excluded)
    ))

    # =========================================================================
    # SCENARIO 4: VIP in Absolute Mode (competing with others)
    # =========================================================================
    config_4 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': True},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_4 = {
        'campaign': {'percent': 10, 'type': 'percentage', 'name': 'Weekend Deal'},
        'bulk': {'percent': 5},
        'loyalty': {'percent': 3, 'card_type': 'Bronze'},
        'vip': {'percent': 20}
    }

    result_4 = DiscountService.calculate_stacked_discount(discounts_4, config_4)
    results.append(print_result(
        "4. VIP Absolute Mode (Campaign 10 incremental + Loyalty 3 incremental + VIP 20 absolute)",
        result_4,
        expected=33.0  # 10 + 3 + 20 = 33
    ))

    # =========================================================================
    # SCENARIO 5: Multiple Absolute Candidates (VIP vs Loyalty)
    # =========================================================================
    config_5 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'absolute'},
        'bulk': {'mode': 'absolute', 'exclude_with_campaign': True},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_5 = {
        'campaign': {'percent': 10, 'type': 'percentage', 'name': 'Flash Sale'},
        'bulk': {'percent': 5},  # excluded due to campaign
        'loyalty': {'percent': 8, 'card_type': 'Platinum'},
        'vip': {'percent': 15}
    }

    result_5 = DiscountService.calculate_stacked_discount(discounts_5, config_5)
    results.append(print_result(
        "5. Multiple Absolute (Campaign 10 + best of VIP 15 vs Loyalty 8)",
        result_5,
        expected=25.0  # 10 + 15 = 25 (VIP wins)
    ))

    # =========================================================================
    # SCENARIO 6: Max Discount Cap Applied
    # =========================================================================
    config_6 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'incremental'},
        'max_total_discount': 25
    }

    discounts_6 = {
        'campaign': {'percent': 15, 'type': 'percentage', 'name': 'Mega Sale'},
        'bulk': {'percent': 5},
        'loyalty': {'percent': 5, 'card_type': 'Gold'},
        'vip': {'percent': 10}
    }

    result_6 = DiscountService.calculate_stacked_discount(discounts_6, config_6)
    results.append(print_result(
        "6. Max Cap 25% (Total would be 35%, capped to 25%)",
        result_6,
        expected=25.0  # 15 + 5 + 5 + 10 = 35, capped to 25
    ))

    # =========================================================================
    # SCENARIO 7: Fixed Amount Campaign
    # =========================================================================
    config_7 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': True},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_7 = {
        'campaign': {'percent': 0, 'amount': 500, 'type': 'fixed', 'name': 'Rs.500 Off', 'applicable': True},
        'bulk': {'percent': 5},
        'loyalty': {'percent': 3, 'card_type': 'Silver'},
        'vip': {'percent': 10}
    }

    result_7 = DiscountService.calculate_stacked_discount(
        discounts_7,
        config_7,
        item_price=Decimal('2500')  # Rs 500 on Rs 2500 = 20%
    )
    results.append(print_result(
        "7. Fixed Amount Campaign (Rs.500 on Rs.2500 = 20% + Loyalty 3% + VIP 10%)",
        result_7,
        expected=33.0  # 20 + 3 + 10 = 33
    ))

    # =========================================================================
    # SCENARIO 8: No Campaign - Fallback to Standard
    # =========================================================================
    config_8 = {
        'campaign': {'mode': 'exclusive'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_8 = {
        'campaign': {'percent': 0},
        'bulk': {'percent': 0},
        'loyalty': {'percent': 0},
        'vip': {'percent': 0},
        'standard': {'percent': 5}
    }

    result_8 = DiscountService.calculate_stacked_discount(discounts_8, config_8)
    results.append(print_result(
        "8. No Discounts - Standard Fallback (5%)",
        result_8,
        expected=5.0
    ))

    # =========================================================================
    # SCENARIO 9: No Discount at All
    # =========================================================================
    config_9 = {
        'campaign': {'mode': 'exclusive'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_9 = {
        'campaign': {'percent': 0},
        'bulk': {'percent': 0},
        'loyalty': {'percent': 0},
        'vip': {'percent': 0}
    }

    result_9 = DiscountService.calculate_stacked_discount(discounts_9, config_9)
    results.append(print_result(
        "9. No Discounts Available",
        result_9,
        expected=0.0
    ))

    # =========================================================================
    # SCENARIO 10: Buy X Get Y Campaign
    # =========================================================================
    config_10 = {
        'campaign': {'mode': 'incremental', 'buy_x_get_y_exclusive': True},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': True},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_10 = {
        'campaign': {
            'percent': 0,
            'type': 'buy_x_get_y',
            'effective_percent': 33.33,  # Buy 2 Get 1 = ~33% effective
            'name': 'Buy 2 Get 1 Free',
            'applicable': True
        },
        'bulk': {'percent': 5},
        'loyalty': {'percent': 3, 'card_type': 'Gold'},
        'vip': {'percent': 10}
    }

    result_10 = DiscountService.calculate_stacked_discount(discounts_10, config_10)
    results.append(print_result(
        "10. Buy X Get Y Campaign (33.33% effective + Loyalty 3% + VIP 10%)",
        result_10,
        expected=46.33  # 33.33 + 3 + 10 = 46.33
    ))

    # =========================================================================
    # SCENARIO 11: Loyalty in Absolute Mode (loses to VIP)
    # =========================================================================
    config_11 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'absolute'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_11 = {
        'campaign': {'percent': 10, 'type': 'percentage', 'name': 'Regular Promo'},
        'bulk': {'percent': 5},
        'loyalty': {'percent': 8, 'card_type': 'Platinum'},
        'vip': {'percent': 12}
    }

    result_11 = DiscountService.calculate_stacked_discount(discounts_11, config_11)
    results.append(print_result(
        "11. Loyalty Absolute loses to VIP (Campaign 10 + Bulk 5 + VIP 12)",
        result_11,
        expected=27.0  # 10 + 5 + 12 = 27 (VIP wins, loyalty excluded)
    ))

    # =========================================================================
    # SCENARIO 12: Only Loyalty Card (No Campaign, No VIP)
    # =========================================================================
    config_12 = {
        'campaign': {'mode': 'exclusive'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_12 = {
        'campaign': {'percent': 0},
        'bulk': {'percent': 7},
        'loyalty': {'percent': 5, 'card_type': 'Gold'},
        'vip': {'percent': 0}
    }

    result_12 = DiscountService.calculate_stacked_discount(discounts_12, config_12)
    results.append(print_result(
        "12. Only Bulk and Loyalty (Bulk 7 + Loyalty 5)",
        result_12,
        expected=12.0  # 7 + 5 = 12
    ))

    # =========================================================================
    # SCENARIO 13: Edge Case - Very High Discounts with Cap
    # =========================================================================
    config_13 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'incremental'},
        'max_total_discount': 50
    }

    discounts_13 = {
        'campaign': {'percent': 30, 'type': 'percentage', 'name': 'Massive Sale'},
        'bulk': {'percent': 15},
        'loyalty': {'percent': 10, 'card_type': 'Platinum'},
        'vip': {'percent': 20}
    }

    result_13 = DiscountService.calculate_stacked_discount(discounts_13, config_13)
    results.append(print_result(
        "13. High Discounts with 50% Cap (30+15+10+20=75% capped to 50%)",
        result_13,
        expected=50.0
    ))

    # =========================================================================
    # SCENARIO 14: All Absolute Mode
    # =========================================================================
    config_14 = {
        'campaign': {'mode': 'incremental'},  # Campaign still incremental
        'loyalty': {'mode': 'absolute'},
        'bulk': {'mode': 'absolute', 'exclude_with_campaign': False},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_14 = {
        'campaign': {'percent': 10, 'type': 'percentage', 'name': 'Base Promo'},
        'bulk': {'percent': 8},
        'loyalty': {'percent': 6, 'card_type': 'Silver'},
        'vip': {'percent': 15}
    }

    result_14 = DiscountService.calculate_stacked_discount(discounts_14, config_14)
    results.append(print_result(
        "14. All Absolute (Campaign 10 + best of Bulk 8, Loyalty 6, VIP 15)",
        result_14,
        expected=25.0  # 10 + 15 = 25 (VIP wins among absolute)
    ))

    # =========================================================================
    # SCENARIO 15: Campaign Only (no other discounts)
    # =========================================================================
    config_15 = {
        'campaign': {'mode': 'incremental'},
        'loyalty': {'mode': 'incremental'},
        'bulk': {'mode': 'incremental', 'exclude_with_campaign': False},
        'vip': {'mode': 'absolute'},
        'max_total_discount': None
    }

    discounts_15 = {
        'campaign': {'percent': 20, 'type': 'percentage', 'name': 'Solo Campaign'},
        'bulk': {'percent': 0},
        'loyalty': {'percent': 0},
        'vip': {'percent': 0}
    }

    result_15 = DiscountService.calculate_stacked_discount(discounts_15, config_15)
    results.append(print_result(
        "15. Campaign Only (20%)",
        result_15,
        expected=20.0
    ))

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for r in results if r)
    total = len(results)

    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"\nSuccess Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        print("\nALL TESTS PASSED!")
    else:
        print("\nSome tests failed - please review the results above.")

    return passed == total


if __name__ == "__main__":
    print("="*70)
    print("DISCOUNT STACKING COMPREHENSIVE TEST SUITE")
    print("="*70)

    success = test_scenarios()
    sys.exit(0 if success else 1)
