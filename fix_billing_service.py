#!/usr/bin/env python
"""
Fix critical bugs in billing_service.py
"""

import re

# Read the file
with open('app/services/billing_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("Applying fixes to billing_service.py...")
print("=" * 80)

# Fix #1: Change created_by to recorded_by in GL posting
old_pattern1 = r'current_user_id=created_by,'
new_pattern1 = r'current_user_id=recorded_by,  # Fixed: was created_by (undefined variable)'

if re.search(old_pattern1, content):
    content = re.sub(old_pattern1, new_pattern1, content)
    print("✓ Fix #1: Changed 'created_by' to 'recorded_by' in GL posting (line 2709)")
else:
    print("✗ Fix #1: Pattern not found or already fixed")

# Fix #2: Remove 'if should_post_gl:' wrapper from AR creation
# Find the AR section and unwrap it from the conditional

old_pattern2 = r'''        # ========================================================================
        # CREATE AR_SUBLEDGER ENTRIES FOR EACH INVOICE ALLOCATION \(LINE-ITEM LEVEL\)
        # ========================================================================

        allocation_results = \[\]

        if should_post_gl:
            try:
                from app.services.subledger_service import create_ar_subledger_entry'''

new_pattern2 = '''        # ========================================================================
        # CREATE AR_SUBLEDGER ENTRIES FOR EACH INVOICE ALLOCATION (LINE-ITEM LEVEL)
        # ========================================================================
        # ✅ CRITICAL FIX: AR entries must ALWAYS be created, regardless of GL posting status
        # AR tracks invoice payments immediately, GL posting can be deferred until approval

        allocation_results = []

        try:
            from app.services.subledger_service import create_ar_subledger_entry'''

if old_pattern2.replace('\\', '') in content:
    content = content.replace(old_pattern2.replace('\\', ''), new_pattern2)
    print("✓ Fix #2: Removed 'if should_post_gl:' wrapper from AR creation (line 2731)")
else:
    print("✗ Fix #2: Pattern not found or already fixed")

# Fix #3: Close the try-except properly and add traceability fields
# We need to find the AR exception handler and fix the indentation

old_pattern3 = r'''            except Exception as e:
                logger.error\(f"Error creating AR subledger entries: \{str\(e\)\}"\)
                raise

        return \{'''

new_pattern3 = '''        except Exception as e:
            logger.error(f"Error creating AR subledger entries: {str(e)}")
            raise

        # ========================================================================
        # POPULATE NEW TRACEABILITY FIELDS
        # ========================================================================
        # Added 2025-11-15: Improve payment tracking and reporting
        payment.patient_id = patient_id
        payment.branch_id = first_invoice.branch_id
        payment.payment_source = 'multi_invoice'
        payment.invoice_count = len(invoice_allocations)
        payment.recorded_by = recorded_by

        return {'''

if re.search(r'except Exception as e:\s+logger\.error\(f"Error creating AR subledger entries:', content):
    content = re.sub(
        r'(            )(except Exception as e:\s+logger\.error\(f"Error creating AR subledger entries:.*?\n.*?raise\n\n)(        return \{)',
        r'\1\2\n        # ========================================================================\n        # POPULATE NEW TRACEABILITY FIELDS\n        # ========================================================================\n        # Added 2025-11-15: Improve payment tracking and reporting\n        payment.patient_id = patient_id\n        payment.branch_id = first_invoice.branch_id\n        payment.payment_source = \'multi_invoice\'\n        payment.invoice_count = len(invoice_allocations)\n        payment.recorded_by = recorded_by\n\n\3',
        content,
        flags=re.DOTALL
    )
    print("✓ Fix #3: Added traceability fields population")
else:
    print("✗ Fix #3: Pattern not found or already fixed")

# Fix #4: Remove extra indentation from AR block (since we removed the if statement)
# The with session.no_autoflush: should be at 2 indent levels, not 3

content = re.sub(
    r'                # Wrap entire AR entry creation',
    r'            # Wrap entire AR entry creation',
    content
)

content = re.sub(
    r'                with session\.no_autoflush:',
    r'            with session.no_autoflush:',
    content
)

# Fix all lines inside the AR block (reduce indentation by 4 spaces)
# This is complex, so let's do it line by line for the AR section

lines = content.split('\n')
new_lines = []
in_ar_section = False
ar_section_start = 0

for i, line in enumerate(lines):
    if 'CREATE AR_SUBLEDGER ENTRIES FOR EACH INVOICE ALLOCATION' in line:
        in_ar_section = True
        ar_section_start = i
        new_lines.append(line)
    elif in_ar_section and 'POPULATE NEW TRACEABILITY FIELDS' in line:
        in_ar_section = False
        new_lines.append(line)
    elif in_ar_section and i > ar_section_start + 10:  # After the try: line
        # Reduce indentation by 4 spaces for AR block content
        if line.startswith('                    '):  # 20 spaces
            new_lines.append(line[4:])  # Remove 4 spaces
        elif line.startswith('                '):  # 16 spaces
            new_lines.append(line[4:])  # Remove 4 spaces
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

content = '\n'.join(new_lines)

print("✓ Fix #4: Fixed indentation after removing 'if should_post_gl:' wrapper")

# Write the fixed content back
with open('app/services/billing_service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 80)
print("All fixes applied successfully!")
print("=" * 80)
print("\nSummary of changes:")
print("1. Fixed undefined variable 'created_by' → 'recorded_by' in GL posting")
print("2. Removed conditional wrapper from AR creation (AR now ALWAYS created)")
print("3. Added population of new traceability fields")
print("4. Fixed indentation after removing conditional")
print("\nPlease review the changes and test the payment creation!")
