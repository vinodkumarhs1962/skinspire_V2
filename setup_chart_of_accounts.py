# setup_chart_of_accounts.py
# Run this script to create the required GL accounts for enhanced posting
# Place this file in your project root and run: python setup_chart_of_accounts.py

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.master import ChartOfAccounts, Hospital
from app.services.database_service import get_db_session

def setup_chart_of_accounts():
    """
    Create the required GL accounts for enhanced posting
    """
    
    # First, get your hospital_id
    with get_db_session() as session:
        hospital = session.query(Hospital).first()
        if not hospital:
            print("❌ No hospital found!")
            return
        
        hospital_id = hospital.hospital_id
        print(f"✅ Found hospital: {hospital.hospital_name} ({hospital_id})")
        
        # Define the required accounts
        required_accounts = [
            # Assets (1000-1999)
            {'no': '1001', 'name': 'Bank Account - Main', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1002', 'name': 'Cash Account', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1301', 'name': 'Inventory - General', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1302', 'name': 'Inventory - Prescription Medicines', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1303', 'name': 'Inventory - Products', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1304', 'name': 'Inventory - Consumables', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1305', 'name': 'Inventory - Miscellaneous', 'type': 'Asset', 'category': 'Current Assets'},
            
            # GST Receivable Accounts
            {'no': '1501', 'name': 'CGST Receivable', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1502', 'name': 'SGST Receivable', 'type': 'Asset', 'category': 'Current Assets'},
            {'no': '1503', 'name': 'IGST Receivable', 'type': 'Asset', 'category': 'Current Assets'},
            
            # Liabilities (2000-2999) - CRITICAL FOR SUPPLIER INVOICES
            {'no': '2001', 'name': 'Accounts Payable - Suppliers', 'type': 'Liability', 'category': 'Current Liabilities'},
            {'no': '2501', 'name': 'CGST Payable', 'type': 'Liability', 'category': 'Current Liabilities'},
            {'no': '2502', 'name': 'SGST Payable', 'type': 'Liability', 'category': 'Current Liabilities'},
            {'no': '2503', 'name': 'IGST Payable', 'type': 'Liability', 'category': 'Current Liabilities'},
            
            # Expenses (5000-5999)
            {'no': '5001', 'name': 'General Expenses', 'type': 'Expense', 'category': 'Operating Expenses'},
            {'no': '5002', 'name': 'Medical Supplies Expense', 'type': 'Expense', 'category': 'Operating Expenses'},
            {'no': '5003', 'name': 'Pharmacy Purchases', 'type': 'Expense', 'category': 'Operating Expenses'},
            
            # Revenue (4000-4999) - Optional
            {'no': '4001', 'name': 'Patient Consultation Revenue', 'type': 'Revenue', 'category': 'Operating Revenue'},
            {'no': '4002', 'name': 'Pharmacy Sales Revenue', 'type': 'Revenue', 'category': 'Operating Revenue'},
        ]
        
        created_count = 0
        exists_count = 0
        
        for account_data in required_accounts:
            # Check if account already exists
            existing = session.query(ChartOfAccounts).filter_by(
                hospital_id=hospital_id,
                gl_account_no=account_data['no']
            ).first()
            
            if existing:
                print(f"⏭️  Account {account_data['no']} already exists: {existing.account_name}")
                exists_count += 1
                continue
            
            # Create new account
            new_account = ChartOfAccounts(
                hospital_id=hospital_id,
                gl_account_no=account_data['no'],
                account_name=account_data['name'],
                account_type=account_data['type'],
                account_category=account_data['category'],
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            session.add(new_account)
            print(f"✅ Created account {account_data['no']}: {account_data['name']}")
            created_count += 1
        
        # Commit all changes
        try:
            session.commit()
            print(f"\n🎉 Setup completed!")
            print(f"   Created: {created_count} new accounts")
            print(f"   Existed: {exists_count} accounts")
            print(f"   Total: {created_count + exists_count} accounts")
            
            # Verify the critical accounts for posting
            verify_critical_accounts(session, hospital_id)
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error creating accounts: {str(e)}")
            raise

def verify_critical_accounts(session: Session, hospital_id: uuid.UUID):
    """
    Verify that the critical accounts for enhanced posting exist
    """
    print(f"\n🔍 Verifying critical accounts for enhanced posting...")
    
    critical_accounts = ['2001', '1501', '1502', '1301', '1001']
    all_good = True
    
    for account_no in critical_accounts:
        account = session.query(ChartOfAccounts).filter_by(
            hospital_id=hospital_id,
            gl_account_no=account_no
        ).first()
        
        if account:
            print(f"✅ {account_no}: {account.account_name}")
        else:
            print(f"❌ {account_no}: MISSING!")
            all_good = False
    
    if all_good:
        print(f"\n🎉 All critical accounts are set up correctly!")
        print(f"   Your enhanced posting should now work without the account not found warnings.")
    else:
        print(f"\n⚠️  Some critical accounts are missing. Please check the setup.")

def list_current_accounts():
    """
    List all current chart of accounts
    """
    with get_db_session() as session:
        hospital = session.query(Hospital).first()
        if not hospital:
            print("❌ No hospital found!")
            return
        
        accounts = session.query(ChartOfAccounts).filter_by(
            hospital_id=hospital.hospital_id,
            is_active=True
        ).order_by(ChartOfAccounts.gl_account_no).all()
        
        print(f"\n📋 Current Chart of Accounts for {hospital.hospital_name}:")
        print("="*80)
        
        for account in accounts:
            print(f"{account.gl_account_no:>6} | {account.account_name:<40} | {account.account_type}")

if __name__ == "__main__":
    print("🏥 Chart of Accounts Setup for Enhanced Posting")
    print("="*60)
    
    try:
        # List current accounts first
        list_current_accounts()
        
        # Ask for confirmation
        response = input(f"\n❓ Do you want to create the missing accounts? (y/N): ")
        
        if response.lower() in ['y', 'yes']:
            setup_chart_of_accounts()
        else:
            print("👋 Setup cancelled.")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()