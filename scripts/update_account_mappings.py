# scripts/update_account_mappings.py
# Utility to scan chart of accounts and update .env file with account mappings

import os
import sys
import argparse
from typing import Dict, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.models.master import ChartOfAccounts
from app.services.database_service import get_database_url

class AccountMappingUtility:
    """
    Utility to scan chart of accounts and generate/update .env file
    """
    
    def __init__(self):
        self.engine = create_engine(get_database_url(), echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def scan_hospital_accounts(self, hospital_id: str) -> Dict[str, Dict]:
        """
        Scan chart of accounts for a hospital and suggest account mappings
        """
        print(f"🔍 Scanning chart of accounts for hospital: {hospital_id}")
        
        with self.SessionLocal() as session:
            accounts = session.query(ChartOfAccounts).filter_by(
                hospital_id=hospital_id,
                is_active=True
            ).all()
            
            if not accounts:
                print(f"❌ No active accounts found for hospital {hospital_id}")
                return {}
            
            print(f"📊 Found {len(accounts)} active accounts")
            
            # Categorize accounts
            suggestions = {
                'ap_accounts': [],
                'inventory_accounts': [],
                'bank_accounts': [],
                'cash_accounts': [],
                'gst_accounts': {'cgst': [], 'sgst': [], 'igst': []},
                'expense_accounts': [],
                'other_accounts': []
            }
            
            for account in accounts:
                account_info = {
                    'account_no': account.gl_account_no,
                    'account_name': account.account_name,
                    'account_group': account.account_group
                }
                
                account_name_lower = account.account_name.lower() if account.account_name else ''
                
                # Categorize accounts based on name patterns
                if account.account_group == 'Liabilities':
                    if any(keyword in account_name_lower for keyword in ['payable', 'supplier', 'creditor', 'ap']):
                        suggestions['ap_accounts'].append(account_info)
                    
                elif account.account_group == 'Assets':
                    if any(keyword in account_name_lower for keyword in ['inventory', 'stock', 'medicine']):
                        suggestions['inventory_accounts'].append(account_info)
                    elif any(keyword in account_name_lower for keyword in ['bank', 'checking', 'savings']):
                        suggestions['bank_accounts'].append(account_info)
                    elif any(keyword in account_name_lower for keyword in ['cash', 'petty']):
                        suggestions['cash_accounts'].append(account_info)
                    elif any(keyword in account_name_lower for keyword in ['expense', 'cost']):
                        suggestions['expense_accounts'].append(account_info)
                    else:
                        suggestions['other_accounts'].append(account_info)
                
                # GST accounts (if you have gst_related and gst_component fields)
                if hasattr(account, 'gst_related') and account.gst_related:
                    gst_component = getattr(account, 'gst_component', None)
                    if gst_component:
                        if gst_component.upper() == 'CGST' and account.account_group == 'Assets':
                            suggestions['gst_accounts']['cgst'].append(account_info)
                        elif gst_component.upper() == 'SGST' and account.account_group == 'Assets':
                            suggestions['gst_accounts']['sgst'].append(account_info)
                        elif gst_component.upper() == 'IGST' and account.account_group == 'Assets':
                            suggestions['gst_accounts']['igst'].append(account_info)
                
                # Pattern matching for GST accounts (if no gst_related field)
                elif account.account_group == 'Assets':
                    if 'cgst' in account_name_lower:
                        suggestions['gst_accounts']['cgst'].append(account_info)
                    elif 'sgst' in account_name_lower:
                        suggestions['gst_accounts']['sgst'].append(account_info)
                    elif 'igst' in account_name_lower:
                        suggestions['gst_accounts']['igst'].append(account_info)
            
            return suggestions
    
    def display_suggestions(self, suggestions: Dict[str, Dict], hospital_id: str):
        """
        Display account mapping suggestions for user review
        """
        print(f"\n🎯 ACCOUNT MAPPING SUGGESTIONS for Hospital: {hospital_id}")
        print("=" * 80)
        
        # AP Accounts
        print("\n📋 ACCOUNTS PAYABLE (AP) ACCOUNTS:")
        if suggestions['ap_accounts']:
            for i, account in enumerate(suggestions['ap_accounts'], 1):
                print(f"  {i}. {account['account_no']} - {account['account_name']} ({account['account_group']})")
        else:
            print("  ❌ No AP accounts found")
        
        # Inventory Accounts
        print("\n📦 INVENTORY ACCOUNTS:")
        if suggestions['inventory_accounts']:
            for i, account in enumerate(suggestions['inventory_accounts'], 1):
                print(f"  {i}. {account['account_no']} - {account['account_name']} ({account['account_group']})")
        else:
            print("  ❌ No inventory accounts found")
        
        # Bank Accounts
        print("\n🏦 BANK ACCOUNTS:")
        if suggestions['bank_accounts']:
            for i, account in enumerate(suggestions['bank_accounts'], 1):
                print(f"  {i}. {account['account_no']} - {account['account_name']} ({account['account_group']})")
        else:
            print("  ❌ No bank accounts found")
        
        # Cash Accounts
        print("\n💰 CASH ACCOUNTS:")
        if suggestions['cash_accounts']:
            for i, account in enumerate(suggestions['cash_accounts'], 1):
                print(f"  {i}. {account['account_no']} - {account['account_name']} ({account['account_group']})")
        else:
            print("  ❌ No cash accounts found")
        
        # GST Accounts
        print("\n📊 GST ACCOUNTS:")
        for gst_type in ['cgst', 'sgst', 'igst']:
            print(f"  {gst_type.upper()}:")
            if suggestions['gst_accounts'][gst_type]:
                for account in suggestions['gst_accounts'][gst_type]:
                    print(f"    • {account['account_no']} - {account['account_name']}")
            else:
                print(f"    ❌ No {gst_type.upper()} accounts found")
        
        # Other accounts
        print(f"\n🔍 OTHER ASSETS ({len(suggestions['other_accounts'])} accounts)")
        if suggestions['other_accounts']:
            print("  (Use these for manual mapping if needed)")
            for account in suggestions['other_accounts'][:5]:  # Show first 5
                print(f"    • {account['account_no']} - {account['account_name']}")
            if len(suggestions['other_accounts']) > 5:
                print(f"    ... and {len(suggestions['other_accounts']) - 5} more")
    
    def generate_env_entries(self, suggestions: Dict[str, Dict], hospital_id: str) -> List[str]:
        """
        Generate .env file entries based on suggestions
        """
        env_entries = []
        env_entries.append(f"# Account mappings for hospital {hospital_id}")
        env_entries.append(f"# Generated on {os.popen('date').read().strip()}")
        env_entries.append("")
        
        # AP Account
        if suggestions['ap_accounts']:
            # Use first AP account as default
            ap_account = suggestions['ap_accounts'][0]['account_no']
            env_entries.append(f"DEFAULT_AP_ACCOUNT={ap_account}")
            env_entries.append(f"# AP Account: {suggestions['ap_accounts'][0]['account_name']}")
        else:
            env_entries.append("DEFAULT_AP_ACCOUNT=2100  # UPDATE THIS - No AP account found")
        
        # Inventory Account
        if suggestions['inventory_accounts']:
            inventory_account = suggestions['inventory_accounts'][0]['account_no']
            env_entries.append(f"DEFAULT_INVENTORY_ACCOUNT={inventory_account}")
            env_entries.append(f"# Inventory Account: {suggestions['inventory_accounts'][0]['account_name']}")
        else:
            env_entries.append("DEFAULT_INVENTORY_ACCOUNT=1410  # UPDATE THIS - No inventory account found")
        
        # Bank Account
        if suggestions['bank_accounts']:
            bank_account = suggestions['bank_accounts'][0]['account_no']
            env_entries.append(f"DEFAULT_BANK_ACCOUNT={bank_account}")
            env_entries.append(f"# Bank Account: {suggestions['bank_accounts'][0]['account_name']}")
        else:
            env_entries.append("DEFAULT_BANK_ACCOUNT=1100  # UPDATE THIS - No bank account found")
        
        # Cash Account
        if suggestions['cash_accounts']:
            cash_account = suggestions['cash_accounts'][0]['account_no']
            env_entries.append(f"DEFAULT_CASH_ACCOUNT={cash_account}")
            env_entries.append(f"# Cash Account: {suggestions['cash_accounts'][0]['account_name']}")
        else:
            env_entries.append("DEFAULT_CASH_ACCOUNT=1101  # UPDATE THIS - No cash account found")
        
        # GST Accounts
        env_entries.append("")
        env_entries.append("# GST Accounts")
        
        for gst_type in ['cgst', 'sgst', 'igst']:
            env_var = f"{gst_type.upper()}_RECEIVABLE_ACCOUNT"
            if suggestions['gst_accounts'][gst_type]:
                gst_account = suggestions['gst_accounts'][gst_type][0]['account_no']
                env_entries.append(f"{env_var}={gst_account}")
                env_entries.append(f"# {gst_type.upper()} Account: {suggestions['gst_accounts'][gst_type][0]['account_name']}")
            else:
                default_val = {'cgst': '1710', 'sgst': '1720', 'igst': '1730'}[gst_type]
                env_entries.append(f"{env_var}={default_val}  # UPDATE THIS - No {gst_type.upper()} account found")
        
        # Enhanced posting settings
        env_entries.append("")
        env_entries.append("# Enhanced Posting Settings")
        env_entries.append("ENABLE_ENHANCED_POSTING=True")
        env_entries.append("POSTING_BATCH_SIZE=100")
        
        return env_entries
    
    def update_env_file(self, env_entries: List[str], backup: bool = True):
        """
        Update .env file with new account mappings
        """
        env_file_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        
        # Create backup if requested
        if backup and os.path.exists(env_file_path):
            backup_path = f"{env_file_path}.backup"
            os.system(f"cp {env_file_path} {backup_path}")
            print(f"✅ Created backup: {backup_path}")
        
        # Read existing .env file
        existing_entries = []
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                existing_entries = f.readlines()
        
        # Remove existing account mapping entries
        account_vars = [
            'DEFAULT_AP_ACCOUNT', 'DEFAULT_INVENTORY_ACCOUNT', 'DEFAULT_BANK_ACCOUNT',
            'DEFAULT_CASH_ACCOUNT', 'CGST_RECEIVABLE_ACCOUNT', 'SGST_RECEIVABLE_ACCOUNT',
            'IGST_RECEIVABLE_ACCOUNT', 'ENABLE_ENHANCED_POSTING', 'POSTING_BATCH_SIZE'
        ]
        
        filtered_entries = []
        for line in existing_entries:
            line = line.strip()
            if not any(line.startswith(f"{var}=") for var in account_vars):
                filtered_entries.append(line)
        
        # Add new entries
        all_entries = filtered_entries + [''] + env_entries
        
        # Write updated .env file
        with open(env_file_path, 'w') as f:
            for entry in all_entries:
                f.write(entry + '\n')
        
        print(f"✅ Updated .env file: {env_file_path}")
        print("📋 New account mappings have been added")

def main():
    parser = argparse.ArgumentParser(description='Update account mappings in .env file')
    parser.add_argument('hospital_id', help='Hospital ID to scan accounts for')
    parser.add_argument('--update-env', action='store_true', help='Update .env file with suggestions')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup of .env file')
    
    args = parser.parse_args()
    
    utility = AccountMappingUtility()
    
    # Scan accounts
    suggestions = utility.scan_hospital_accounts(args.hospital_id)
    
    if not suggestions:
        print("❌ No accounts found. Exiting.")
        return
    
    # Display suggestions
    utility.display_suggestions(suggestions, args.hospital_id)
    
    if args.update_env:
        # Generate and update .env file
        env_entries = utility.generate_env_entries(suggestions, args.hospital_id)
        
        print("\n📝 Generated .env entries:")
        print("-" * 40)
        for entry in env_entries:
            print(entry)
        
        # Confirm before updating
        confirm = input("\n❓ Update .env file with these mappings? (y/N): ")
        if confirm.lower() == 'y':
            utility.update_env_file(env_entries, backup=not args.no_backup)
            print("\n🎉 Account mappings updated successfully!")
            print("🔄 Restart your application to use the new settings.")
        else:
            print("❌ Update cancelled.")
    else:
        print(f"\n💡 To update .env file, run:")
        print(f"   python scripts/update_account_mappings.py {args.hospital_id} --update-env")

if __name__ == '__main__':
    main()