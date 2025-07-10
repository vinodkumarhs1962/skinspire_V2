# =============================================================================
# DATA ASSEMBLER SAFETY CHECK SCRIPT
# File: scripts/check_data_assembler_safety.py
# =============================================================================

"""
Safety check script to verify if data_assembler.py can be safely replaced
Checks for external dependencies on methods that will be removed

RUN THIS BEFORE replacing data_assembler.py
"""

import os
import re
import sys
from typing import List, Dict, Set

class DataAssemblerSafetyChecker:
    """Check if data_assembler.py can be safely replaced"""
    
    def __init__(self):
        self.project_root = self._find_project_root()
        self.methods_to_remove = [
            '_assemble_enhanced_filter_form',
            '_assemble_enhanced_filter_data', 
            '_build_filter_field_data',
            '_get_filter_backend_data',
            '_detect_active_date_preset',
            '_get_enhanced_filter_type',
            'get_filter_backend_data'  # If it exists as standalone function
        ]
        
        self.methods_to_keep = [
            'assemble_complex_list_data',  # Main method - MUST keep
            '_assemble_table_columns',
            '_assemble_table_data',
            '_format_field_value',
            '_format_status_badge', 
            '_assemble_summary_data',
            '_assemble_pagination_data',
            '_build_row_actions',
            '_check_action_conditions',
            '_build_action_url',
            '_get_field_type_safe',
            '_get_error_fallback_data'
        ]
        
        self.scan_results = {
            'safe_to_replace': True,
            'external_calls': {},
            'warnings': [],
            'errors': []
        }
    
    def run_safety_check(self) -> Dict:
        """Run complete safety check"""
        print("🔍 Running Data Assembler Safety Check...")
        print("=" * 50)
        
        # Check external method calls
        self._check_external_method_calls()
        
        # Check import patterns
        self._check_import_patterns()
        
        # Check current data_assembler.py structure
        self._analyze_current_data_assembler()
        
        # Generate recommendations
        self._generate_recommendations()
        
        return self.scan_results
    
    def _check_external_method_calls(self):
        """Check if removed methods are called from other files"""
        print("\n📋 Checking external method calls...")
        
        python_files = self._find_python_files()
        
        for method_name in self.methods_to_remove:
            external_calls = self._find_method_calls(method_name, python_files)
            
            if external_calls:
                print(f"  ⚠️  {method_name} called externally:")
                for file_path, lines in external_calls.items():
                    print(f"     📄 {file_path}")
                    for line_num, line_content in lines:
                        print(f"        Line {line_num}: {line_content.strip()}")
                
                self.scan_results['external_calls'][method_name] = external_calls
                self.scan_results['safe_to_replace'] = False
            else:
                print(f"  ✅ {method_name} - no external calls found")
    
    def _check_import_patterns(self):
        """Check how data_assembler is imported"""
        print("\n📦 Checking import patterns...")
        
        python_files = self._find_python_files()
        import_patterns = []
        
        for file_path in python_files:
            if 'data_assembler.py' in file_path:
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check various import patterns
                patterns = [
                    r'from.*data_assembler.*import.*',
                    r'import.*data_assembler',
                    r'data_assembler\.',
                    r'EnhancedUniversalDataAssembler',
                    r'assemble_complex_list_data'
                ]
                
                for pattern in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1]
                        
                        import_patterns.append({
                            'file': file_path,
                            'line': line_num,
                            'content': line_content.strip(),
                            'pattern': pattern
                        })
                        
            except Exception as e:
                self.scan_results['warnings'].append(f"Could not read {file_path}: {str(e)}")
        
        if import_patterns:
            print(f"  📋 Found {len(import_patterns)} import/usage patterns:")
            for pattern in import_patterns:
                print(f"     📄 {pattern['file']}:{pattern['line']}")
                print(f"        {pattern['content']}")
        else:
            print("  ✅ No import patterns found")
    
    def _analyze_current_data_assembler(self):
        """Analyze current data_assembler.py structure"""
        print("\n🔧 Analyzing current data_assembler.py...")
        
        data_assembler_path = os.path.join(self.project_root, 'app', 'engine', 'data_assembler.py')
        
        if not os.path.exists(data_assembler_path):
            self.scan_results['errors'].append("data_assembler.py not found!")
            return
        
        try:
            with open(data_assembler_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for each method
            methods_found = []
            methods_missing = []
            
            all_methods = self.methods_to_remove + self.methods_to_keep
            
            for method in all_methods:
                if f"def {method}" in content:
                    methods_found.append(method)
                else:
                    methods_missing.append(method)
            
            print(f"  📋 Current data_assembler.py analysis:")
            print(f"     ✅ Methods found: {len(methods_found)}")
            print(f"     ❓ Methods missing: {len(methods_missing)}")
            
            if methods_missing:
                print(f"     Missing methods: {', '.join(methods_missing)}")
            
            # Check for unknown methods
            method_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            all_methods_in_file = re.findall(method_pattern, content)
            known_methods = set(all_methods + ['__init__'])
            unknown_methods = [m for m in all_methods_in_file if m not in known_methods]
            
            if unknown_methods:
                print(f"     ⚠️  Unknown methods found: {', '.join(unknown_methods)}")
                self.scan_results['warnings'].append(f"Unknown methods in data_assembler.py: {', '.join(unknown_methods)}")
                
        except Exception as e:
            self.scan_results['errors'].append(f"Could not analyze data_assembler.py: {str(e)}")
    
    def _generate_recommendations(self):
        """Generate safety recommendations"""
        print("\n🎯 Safety Recommendations:")
        
        if self.scan_results['safe_to_replace']:
            print("  ✅ SAFE TO REPLACE data_assembler.py")
            print("     No external dependencies on methods that will be removed")
        else:
            print("  ⚠️  NOT SAFE TO REPLACE YET")
            print("     External calls found to methods that will be removed")
            print("     Options:")
            print("     1. Update calling code to use new methods")
            print("     2. Keep old methods as compatibility wrappers")
            print("     3. Implement gradual migration")
        
        if self.scan_results['external_calls']:
            print("\n  🔧 Required actions before replacement:")
            for method, calls in self.scan_results['external_calls'].items():
                print(f"     📋 {method}:")
                for file_path, lines in calls.items():
                    print(f"        - Update calls in {file_path}")
        
        if self.scan_results['warnings']:
            print("\n  ⚠️  Warnings:")
            for warning in self.scan_results['warnings']:
                print(f"     - {warning}")
        
        if self.scan_results['errors']:
            print("\n  ❌ Errors:")
            for error in self.scan_results['errors']:
                print(f"     - {error}")
    
    def _find_python_files(self) -> List[str]:
        """Find all Python files in project"""
        python_files = []
        
        exclude_dirs = {'.git', '__pycache__', '.pytest_cache', 'node_modules', 'venv', 'env'}
        exclude_files = {'test_universal_filter_backend.py'}  # Exclude our test files
        
        for root, dirs, files in os.walk(self.project_root):
            # Remove excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file.endswith('.py') and file not in exclude_files:
                    python_files.append(os.path.join(root, file))
        
        return python_files
    
    def _find_method_calls(self, method_name: str, files: List[str]) -> Dict[str, List]:
        """Find calls to a specific method"""
        calls = {}
        
        patterns = [
            rf'\.{method_name}\s*\(',  # .method_name(
            rf'assembler\.{method_name}\s*\(',  # assembler.method_name(
            rf'self\.{method_name}\s*\(',  # self.method_name(
        ]
        
        for file_path in files:
            if 'data_assembler.py' in file_path:
                continue  # Skip the data_assembler.py itself
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_calls = []
                
                for pattern in patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = content.split('\n')[line_num - 1]
                        file_calls.append((line_num, line_content))
                
                if file_calls:
                    calls[file_path] = file_calls
                    
            except Exception as e:
                continue  # Skip files we can't read
        
        return calls
    
    def _find_project_root(self) -> str:
        """Find project root directory"""
        current_dir = os.getcwd()
        
        # Look for common project indicators
        indicators = ['app', 'requirements.txt', 'manage.py', '.git']
        
        while current_dir != '/':
            if any(os.path.exists(os.path.join(current_dir, indicator)) for indicator in indicators):
                return current_dir
            current_dir = os.path.dirname(current_dir)
        
        return os.getcwd()  # Fallback to current directory

def main():
    """Main function"""
    checker = DataAssemblerSafetyChecker()
    results = checker.run_safety_check()
    
    print("\n" + "=" * 50)
    print("🏁 SAFETY CHECK COMPLETE")
    print("=" * 50)
    
    if results['safe_to_replace']:
        print("✅ VERDICT: SAFE TO REPLACE data_assembler.py")
        print("\n🚀 Next steps:")
        print("   1. Backup current data_assembler.py")
        print("   2. Replace with cleaned version")
        print("   3. Test functionality")
    else:
        print("⚠️  VERDICT: NOT SAFE TO REPLACE YET")
        print("\n🔧 Required actions:")
        print("   1. Fix external method calls listed above")
        print("   2. Re-run this safety check")
        print("   3. Then proceed with replacement")
    
    print("\n📊 Summary:")
    print(f"   External calls found: {len(results['external_calls'])}")
    print(f"   Warnings: {len(results['warnings'])}")
    print(f"   Errors: {len(results['errors'])}")
    
    return 0 if results['safe_to_replace'] else 1

if __name__ == '__main__':
    sys.exit(main())