#!/usr/bin/env python3
# scripts/component_analyzer
# python CSS_Component_batch_analyze.py
"""
Enhanced Component Analyzer for Skinspire Healthcare CSS Component Library
Recognizes all financial and healthcare components including new enhancements
"""

import os
import re
from pathlib import Path
from collections import defaultdict

class ComponentAnalyzer:
    def __init__(self):
        # Enhanced component definitions with new financial components
        self.component_definitions = {
            'buttons': {
                'btn-primary', 'btn-secondary', 'btn-outline', 'btn-warning', 
                'btn-danger', 'btn-success', 'btn-sm', 'btn-lg', 'btn-icon-only',
                'btn-loading', 'action-buttons', 'action-link'
            },
            'cards': {
                # Financial Cards (NEW)
                'financial-data-card', 'financial-data-header', 'financial-data-title',
                'financial-data-summary', 'financial-data-summary-primary', 'financial-data-content',
                'financial-data-footer', 'financial-comparison-card', 'financial-comparison-header',
                'financial-comparison-title', 'financial-comparison-grid', 'financial-comparison-item',
                'financial-comparison-label', 'financial-comparison-value', 'numeric-summary-card',
                'numeric-summary-icon', 'numeric-summary-value', 'numeric-summary-label',
                'payment-method-card', 'payment-method-icon', 'payment-method-label',
                'payment-method-value', 'card-grid',
                # Standard Cards
                'info-card', 'info-card-header', 'info-card-title', 'info-card-content',
                'stat-card', 'stat-value', 'stat-label', 'status-card'
            },
            'tables': {
                # Financial Tables (NEW)
                'financial-table', 'payment-history-table', 'gst-summary-table', 
                'invoice-items-table', 'supplier-invoice-table', 'financial-cell-primary',
                'financial-cell-secondary', 'currency-value', 'percentage-value',
                'text-header', 'number-header', 'action-header', 'text-column', 
                'number-column', 'action-column', 'total-row',
                # Standard Tables
                'data-table', 'compact-table', 'table-container', 'sortable-header',
                'table-pagination', 'pagination-buttons', 'table-filters', 'table-search',
                'table-empty', 'selection-column', 'table-checkbox', 'table-empty-state'
            },
            'forms': {
                'form-input', 'form-select', 'form-textarea', 'form-label',
                'form-group', 'form-error', 'form-help', 'form-checkbox',
                'form-radio', 'form-switch', 'autocomplete-container', 'autocomplete-results',
                'autocomplete-item', 'file-input', 'file-preview', 'signature-pad',
                'multi-step-form', 'form-step', 'step-indicator', 'step-nav',
                'form-section', 'form-subsection', 'input-group', 'input-addon'
            },
            'status': {
                'status-badge', 'status-active', 'status-inactive', 'status-pending',
                'status-approved', 'status-rejected', 'status-success', 'status-error',
                'status-warning', 'status-info', 'status-completed', 'status-processing',
                'status-review', 'alert', 'alert-icon', 'alert-content', 'alert-success',
                'alert-error', 'alert-warning', 'alert-info', 'alert-title', 'alert-message',
                'priority-indicator', 'priority-critical', 'priority-high', 'medical-status',
                'notification-badge', 'notification-count'
            },
            'filters': {
                'filter-card', 'filter-header', 'filter-content', 'filter-group',
                'filter-row', 'quick-filters', 'quick-filter', 'active-filters',
                'filter-chip', 'filter-chip-remove', 'filter-actions', 'filter-reset',
                'filter-apply', 'date-range-picker', 'preset-filters', 'filter-preset'
            },
            'layout': {
                'filter-actions', 'footer-actions', 'page-header', 'page-title',
                'page-subtitle', 'breadcrumb', 'sidebar', 'main-content',
                'dashboard-grid', 'responsive-grid', 'hidden-mobile', 'hidden-tablet'
            },
            'healthcare': {
                'patient-status', 'patient-status-dot', 'medical-table', 'patient-info',
                'patient-search-results', 'medicine-fields', 'gst-element', 'gst-field',
                'invoice-container', 'invoice-header', 'invoice-meta', 'meta-section',
                'line-items-section', 'invoice-table-wrapper', 'invoice-table',
                'line-item-row', 'item-search-results', 'invoice-total-summary',
                'total-section', 'amount-in-words', 'totals', 'grand-total'
            },
            'supplier': {
                'supplier-invoice-totals', 'supplier-totals-grid', 'po-line-item',
                'supplier-search-results', 'supplier-search-item', 'payment-allocation-table',
                'supplier-invoice-status', 'supplier-name-cell'
            },
            'interactive': {
                'loading-spinner', 'loading-text', 'skeleton', 'progress-bar',
                'progress-fill', 'progress-labeled', 'modal', 'modal-overlay',
                'modal-content', 'modal-header', 'modal-body', 'modal-footer',
                'dropdown', 'dropdown-toggle', 'dropdown-menu', 'dropdown-item'
            }
        }
        
        # Enhanced conversion candidates - old patterns to migrate
        self.conversion_patterns = {
            'old_cards': [
                r'class="bg-white.*?rounded-lg.*?shadow',
                r'class="info-card(?!\s+mb-6\s*">)',  # Old info-card not using new pattern
                r'class="bg-white.*?border.*?rounded'
            ],
            'old_tables': [
                r'class="data-table"(?!.*financial-table)',  # data-table without financial-table
                r'<table[^>]*>(?!.*financial-table)',  # Tables without component classes
                r'class="table-container"(?!.*financial-data-content)'  # Old table containers
            ],
            'old_buttons': [
                r'class="btn\s+btn-',  # Old Bootstrap-style buttons
                r'class=".*?bg-blue-.*?px-.*?py-',  # Custom styled buttons
                r'class=".*?bg-green-.*?hover:'  # Custom hover buttons
            ],
            'old_status': [
                r'class=".*?bg-green-100.*?text-green-800',  # Custom status styling
                r'class=".*?bg-red-100.*?text-red-800',
                r'class=".*?bg-yellow-100.*?text-yellow-800'
            ],
            'financial_upgrade_candidates': [
                r'class=".*?payment.*?table"(?!.*financial-table)',  # Payment tables not using financial components
                r'class=".*?gst.*?table"(?!.*financial-table)',  # GST tables
                r'class=".*?invoice.*?table"(?!.*financial-table)',  # Invoice tables
                r'class=".*?summary.*?card"(?!.*numeric-summary-card)',  # Summary cards
                r'class=".*?total.*?amount"(?!.*currency-value)',  # Currency values not using component
                r'₹[0-9.,]+(?!</.*?>.*?currency-value)'  # Currency display without component class
            ]
        }

    def analyze_template(self, template_path):
        """Analyze a single template for component usage"""
        try:
            with open(template_path, 'r', encoding='utf-8') as file:
                content = file.read()
        except Exception as e:
            return {'error': f"Could not read file: {str(e)}"}

        # Find all components
        components_found = defaultdict(set)
        components_missing = defaultdict(set)
        conversion_candidates = defaultdict(int)

        # Check for each component category
        for category, component_list in self.component_definitions.items():
            for component in component_list:
                # Look for component usage in class attributes
                pattern = rf'class="[^"]*\b{re.escape(component)}\b[^"]*"'
                if re.search(pattern, content):
                    components_found[category].add(component)
                else:
                    components_missing[category].add(component)

        # Check for conversion candidates
        for candidate_type, patterns in self.conversion_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                conversion_candidates[candidate_type] += len(matches)

        # Calculate statistics
        total_defined = sum(len(components) for components in self.component_definitions.values())
        total_found = sum(len(components) for components in components_found.values())
        coverage_percentage = (total_found / total_defined) * 100 if total_defined > 0 else 0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            components_found, components_missing, conversion_candidates, coverage_percentage
        )

        return {
            'template': template_path,
            'components_found': dict(components_found),
            'components_missing': dict(components_missing),
            'conversion_candidates': dict(conversion_candidates),
            'statistics': {
                'total_components_found': total_found,
                'total_components_defined': total_defined,
                'coverage_percentage': round(coverage_percentage, 1),
                'conversion_candidates_count': sum(conversion_candidates.values())
            },
            'recommendations': recommendations
        }

    def _generate_recommendations(self, found, missing, candidates, coverage):
        """Generate specific recommendations based on analysis"""
        recommendations = []

        # Coverage-based recommendations
        if coverage < 30:
            recommendations.append("🚨 URGENT: Very low component usage. Consider major refactoring.")
        elif coverage < 50:
            recommendations.append("⚠️ MEDIUM: Moderate component usage. Focus on key areas.")
        elif coverage < 70:
            recommendations.append("✅ GOOD: Good component usage. Minor improvements needed.")
        else:
            recommendations.append("🎉 EXCELLENT: Great component usage!")

        # Financial component specific recommendations
        if 'cards' in missing and 'financial-data-card' in missing['cards']:
            if candidates.get('old_cards', 0) > 0:
                recommendations.append("💳 Replace old card patterns with financial-data-card components")
        
        if 'tables' in missing and 'financial-table' in missing['tables']:
            if candidates.get('old_tables', 0) > 0:
                recommendations.append("📊 Upgrade tables to use financial-table components")

        # Currency formatting recommendations
        if candidates.get('financial_upgrade_candidates', 0) > 0:
            recommendations.append("💰 Add currency-value classes to financial displays")

        # Button recommendations
        if candidates.get('old_buttons', 0) > 0:
            recommendations.append("🔘 Replace custom buttons with standardized btn- components")

        # Status badge recommendations  
        if candidates.get('old_status', 0) > 0:
            recommendations.append("🏷️ Replace custom status styling with status-badge components")

        # Specific component recommendations
        if 'forms' in found and 'buttons' not in found:
            recommendations.append("📝 Add button components to complement your forms")

        if 'tables' in found and 'filters' not in found:
            recommendations.append("🔍 Consider adding filter components for better table UX")

        return recommendations

    def analyze_directory(self, directory_path, file_pattern="*.html"):
        """Analyze all HTML templates in a directory"""
        results = {}
        
        path = Path(directory_path)
        html_files = list(path.glob(file_pattern))
        
        if not html_files:
            print(f"No HTML files found in {directory_path}")
            return results
        
        for file_path in html_files:
            results[str(file_path)] = self.analyze_template(str(file_path))
        
        return results

    def print_analysis(self, results):
        """Print formatted analysis results"""
        if isinstance(results, dict) and 'error' in results:
            print(f"❌ Error: {results['error']}")
            return
        
        template_name = os.path.basename(results['template'])
        stats = results['statistics']
        
        print(f"\n{'='*60}")
        print(f"📊 COMPONENT ANALYSIS: {template_name}")
        print(f"{'='*60}")
        
        print(f"\n📈 STATISTICS:")
        print(f"   • Components Found: {stats['total_components_found']}")
        print(f"   • Coverage: {stats['coverage_percentage']}%")
        print(f"   • Conversion Candidates: {stats['conversion_candidates_count']}")
        
        # Print found components by category
        print(f"\n✅ COMPONENTS FOUND:")
        for category, components in results['components_found'].items():
            if components:
                print(f"   {category.upper()}:")
                for comp in sorted(components):
                    print(f"      ✓ {comp}")
        
        # Print high-priority missing components
        print(f"\n⚠️ HIGH-PRIORITY MISSING COMPONENTS:")
        priority_missing = {
            'financial-data-card', 'financial-table', 'currency-value', 
            'numeric-summary-card', 'financial-comparison-card'
        }
        for category, missing in results['components_missing'].items():
            high_priority = missing.intersection(priority_missing)
            if high_priority:
                print(f"   {category.upper()}:")
                for comp in sorted(high_priority):
                    print(f"      - {comp}")
        
        # Print conversion candidates
        if results['conversion_candidates']:
            print(f"\n🔧 CONVERSION CANDIDATES:")
            for candidate_type, count in results['conversion_candidates'].items():
                if count > 0:
                    print(f"   • {candidate_type.replace('_', ' ').title()}: {count} instances")
        
        # Print recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in results['recommendations']:
            print(f"   {rec}")

    def generate_summary_report(self, directory_results):
        """Generate a summary report for multiple templates"""
        print(f"\n{'='*80}")
        print(f"📋 COMPONENT USAGE SUMMARY REPORT")
        print(f"{'='*80}")
        
        # Calculate overall statistics
        total_templates = len(directory_results)
        coverage_scores = []
        
        print(f"\n📊 TEMPLATE OVERVIEW:")
        print(f"{'Template':<35} {'Coverage':<10} {'Status':<15} {'Priority'}")
        print("-" * 75)
        
        for template_path, results in directory_results.items():
            if 'error' in results:
                print(f"{os.path.basename(template_path):<35} {'ERROR':<9}  {'❌ Failed':<15} {'Check File'}")
                continue
                
            template_name = os.path.basename(template_path)
            coverage = results['statistics']['coverage_percentage']
            coverage_scores.append(coverage)
            
            # Determine status and priority based on financial component usage
            financial_score = self._calculate_financial_score(results)
            
            if coverage >= 70 and financial_score >= 70:
                status = "✅ Excellent"
                priority = "Low"
            elif coverage >= 50 and financial_score >= 50:
                status = "🌟 Good"
                priority = "Low"
            elif coverage >= 30 or financial_score >= 30:
                status = "⚠️ Needs Work"
                priority = "Medium"
            else:
                status = "❌ Poor"
                priority = "High"
            
            print(f"{template_name:<35} {coverage:<9}% {status:<15} {priority}")
        
        if coverage_scores:
            avg_coverage = sum(coverage_scores) / len(coverage_scores)
            print(f"\n📈 OVERALL STATISTICS:")
            print(f"   • Average Coverage: {avg_coverage:.1f}%")
            print(f"   • Templates Analyzed: {total_templates}")
            print(f"   • Templates Needing Work: {sum(1 for score in coverage_scores if score < 70)}")
            
        # Generate migration priorities
        self._generate_migration_priorities(directory_results)

    def _calculate_financial_score(self, results):
        """Calculate score based on financial component usage"""
        financial_components = {
            'financial-data-card', 'financial-table', 'currency-value',
            'numeric-summary-card', 'financial-comparison-card', 'payment-history-table'
        }
        
        found_financial = set()
        for category_components in results['components_found'].values():
            found_financial.update(category_components.intersection(financial_components))
        
        return (len(found_financial) / len(financial_components)) * 100

    def _generate_migration_priorities(self, directory_results):
        """Generate specific migration priorities"""
        print(f"\n🎯 MIGRATION PRIORITIES:")
        
        high_priority = []
        medium_priority = []
        low_priority = []
        
        for template_path, results in directory_results.items():
            if 'error' in results:
                continue
                
            template_name = os.path.basename(template_path)
            coverage = results['statistics']['coverage_percentage']
            candidates = results['conversion_candidates']
            
            total_candidates = sum(candidates.values())
            
            if coverage < 40 or total_candidates > 10:
                high_priority.append((template_name, coverage, total_candidates))
            elif coverage < 70 or total_candidates > 5:
                medium_priority.append((template_name, coverage, total_candidates))
            else:
                low_priority.append((template_name, coverage, total_candidates))
        
        for priority_level, templates in [("HIGH", high_priority), ("MEDIUM", medium_priority), ("LOW", low_priority)]:
            if templates:
                print(f"\n   {priority_level} PRIORITY:")
                for template_name, coverage, candidates in sorted(templates, key=lambda x: x[1]):
                    print(f"      • {template_name} (Coverage: {coverage}%, Candidates: {candidates})")


def main():
    """Main function - analyze payment templates"""
    analyzer = ComponentAnalyzer()
    
    print("🔍 ENHANCED COMPONENT ANALYZER - PAYMENT TEMPLATES FOCUS")
    print("=" * 60)
    
    # Payment templates to analyze
    payment_templates = [
        "app/templates/supplier/payment_list.html",
        "app/templates/supplier/payment_view.html", 
        "app/templates/supplier/payment_form.html"
    ]
    
    # Analyze individual payment templates
    for template_file in payment_templates:
        if os.path.exists(template_file):
            print(f"\n🔍 ANALYZING: {os.path.basename(template_file)}")
            results = analyzer.analyze_template(template_file)
            analyzer.print_analysis(results)
        else:
            print(f"❌ Template file '{template_file}' not found")
    
    # Analyze all supplier templates for comparison
    print(f"\n{'='*80}")
    print("🔍 ANALYZING ALL SUPPLIER TEMPLATES:")
    
    directory_results = analyzer.analyze_directory("app/templates/supplier", "*.html")
    
    if directory_results:
        analyzer.generate_summary_report(directory_results)
    else:
        print("❌ No HTML templates found in supplier directory")

if __name__ == "__main__":
    main()