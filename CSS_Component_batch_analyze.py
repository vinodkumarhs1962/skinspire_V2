# CSS_Component_batch_analyze.py
# python CSS_Component_batch_analyze.py
# FIXED VERSION - Windows encoding compatible
# Batch analysis script for Skinspire supplier templates

import os
import sys

# Add the scripts directory to path if component_analyzer is in a subdirectory
if os.path.exists('scripts'):
    sys.path.append('scripts')

try:
    from scripts.component_analyzer import ComponentAnalyzer
except ImportError:
    print("❌ Error: component_analyzer.py not found!")
    print("📁 Current directory:", os.getcwd())
    print("📁 Available Python files:", [f for f in os.listdir('.') if f.endswith('.py')])
    print("\n💡 Make sure component_analyzer.py is in the same directory or in a 'scripts' folder")
    input("Press Enter to exit...")
    sys.exit(1)

def analyze_all_supplier_templates():
    analyzer = ComponentAnalyzer()
    
    # List of your templates with full paths
    templates = [
        "app/templates/supplier/supplier_invoice_list.html",
        "app/templates/supplier/view_supplier_invoice.html", 
        "app/templates/supplier/purchase_order_list.html",
        "app/templates/supplier/view_purchase_order.html"
    ]
    
    print("🔍 ANALYZING ALL SUPPLIER TEMPLATES")
    print("=" * 50)
    
    # Check which templates exist
    existing_templates = []
    missing_templates = []
    
    for template in templates:
        if os.path.exists(template):
            existing_templates.append(template)
        else:
            missing_templates.append(template)
    
    if missing_templates:
        print("⚠️ MISSING TEMPLATES:")
        for template in missing_templates:
            print(f"   ❌ {template}")
        print()
    
    if not existing_templates:
        print("❌ No template files found!")
        print(f"📁 Current directory: {os.getcwd()}")
        print("📁 Looking for templates in:")
        for template in templates:
            print(f"   • {template}")
        
        # Try to find HTML files
        print("\n🔍 HTML files found in current structure:")
        for root, dirs, files in os.walk('.'):
            for file in files:
                if file.endswith('.html'):
                    print(f"   📄 {os.path.join(root, file)}")
        
        input("Press Enter to exit...")
        return
    
    # Analyze existing templates
    all_results = {}
    
    for template in existing_templates:
        print(f"\n📄 Analyzing: {template}")
        try:
            results = analyzer.analyze_template(template)
            
            if 'error' in results:
                print(f"   ❌ Error: {results['error']}")
                continue
            
            all_results[template] = results
            
            # Quick summary
            stats = results['statistics']
            print(f"   📊 Coverage: {stats['coverage_percentage']}%")
            print(f"   🔧 Issues: {stats['conversion_candidates_count']} conversion candidates")
            
            # Top recommendation
            if results['recommendations']:
                print(f"   💡 Priority: {results['recommendations'][0]}")
                
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            continue
    
    # Generate detailed reports
    if all_results:
        print(f"\n{'='*80}")
        print("📋 DETAILED ANALYSIS REPORTS")
        print(f"{'='*80}")
        
        for template_path, results in all_results.items():
            analyzer.print_analysis(results)
        
        # Generate summary
        analyzer.generate_summary_report(all_results)
        
        # Save report to file
        try:
            save_report_to_file(all_results)
        except Exception as e:
            print(f"⚠️ Could not save report file: {e}")
    
    print(f"\n{'='*50}")
    print("✅ Analysis complete!")
    input("Press Enter to exit...")

def save_report_to_file(results_dict):
    """Save the analysis results to a text file"""
    report_filename = "component_analysis_report.txt"
    
    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write("SKINSPIRE COMPONENT ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            # Summary table
            f.write("SUMMARY OVERVIEW:\n")
            f.write("-" * 50 + "\n")
            f.write(f"{'Template':<40} {'Coverage':<10} {'Issues'}\n")
            f.write("-" * 50 + "\n")
            
            for template_path, results in results_dict.items():
                if 'error' not in results:
                    template_name = os.path.basename(template_path)
                    coverage = results['statistics']['coverage_percentage']
                    issues = results['statistics']['conversion_candidates_count']
                    f.write(f"{template_name:<40} {coverage:<9}% {issues}\n")
            
            f.write("\n" + "=" * 80 + "\n\n")
            
            # Detailed results
            for template_path, results in results_dict.items():
                if 'error' not in results:
                    f.write(f"TEMPLATE: {os.path.basename(template_path)}\n")
                    f.write("-" * 60 + "\n")
                    
                    stats = results['statistics']
                    f.write(f"Coverage: {stats['coverage_percentage']}%\n")
                    f.write(f"Components Found: {stats['total_components_found']}\n")
                    f.write(f"Conversion Candidates: {stats['conversion_candidates_count']}\n\n")
                    
                    # Components found
                    f.write("COMPONENTS FOUND:\n")
                    for category, components in results['components_found'].items():
                        if components:
                            f.write(f"  {category.upper()}: {', '.join(components)}\n")
                    
                    # Conversion candidates
                    if results['conversion_candidates']:
                        f.write("\nCONVERSION CANDIDATES:\n")
                        for candidate_type, count in results['conversion_candidates'].items():
                            f.write(f"  {candidate_type.replace('_', ' ').title()}: {count}\n")
                    
                    # Recommendations
                    f.write("\nRECOMMENDATIONS:\n")
                    for rec in results['recommendations']:
                        f.write(f"  {rec}\n")
                    
                    f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"📄 Detailed report saved to: {report_filename}")
        
    except Exception as e:
        print(f"❌ Error saving report: {e}")

if __name__ == "__main__":
    try:
        analyze_all_supplier_templates()
    except KeyboardInterrupt:
        print("\n👋 Analysis interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("📧 Please check your file paths and try again")
        input("Press Enter to exit...")