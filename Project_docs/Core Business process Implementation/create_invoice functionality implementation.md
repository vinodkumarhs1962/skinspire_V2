Understanding of Requirements and Proposed Changes
Requirements Summary

Fix Invoice UI Issues

Line items display vertically instead of horizontally and aren't aligned with headers
Item search functionality isn't working properly
Missing save button for line items (only delete is visible)
Need to maintain consistent UI with centralized CSS management


Implement Business Logic for Invoicing

Invoice line items should capture all billable items regardless of type and GST applicability
On saving, different invoice types should be processed according to business rules:

For Product/Service/Misc types: Create separate invoices for GST and non-GST items
For Prescription type: Check pharmacy registration and either create a drug rules compliant bill or consolidate under "Doctor's Examination and Treatment"


Each invoice should have its own running serial number
Invoice type in line items (not header) determines processing logic
GST applicability should be determined from product/medicine master records


Follow Project Guidelines

Use API routes for dynamic item search (similar to patient search)
Maintain component-based architecture consistent with GL, inventory modules
Follow centralized development approach per guidelines
Ensure backward compatibility



Proposed Changes
Based on the project structure and centralized development guidelines, I propose the following changes:
Files to be Added or Modified
Phase 1: Fix UI & Frontend Architecture

Template Modifications

app/templates/billing/create_invoice.html: Fix table structure and alignment issues


CSS Reorganization

app/static/css/components/invoice.css: New file for centralized invoice styling
app/static/css/components/forms.css: Enhance form component styles


JavaScript Refactoring

app/static/js/components/invoice_item.js: New component for invoice line items
app/static/js/pages/invoice.js: Page-specific logic for invoice creation



Phase 2: Backend Integration & Business Logic

Service Layer Modifications

app/services/billing_service.py: Enhance to support complex invoice generation rules


API Enhancements

app/api/routes/billing.py: Ensure proper item search functionality


Form Handling

app/forms/billing_forms.py: Potential modifications to support new business logic



Phase 3: Testing & Integration

Testing

tests/services/test_billing_service.py: Test business logic implementation
tests/views/test_billing_views.py: Test frontend integration


Documentation

Update relevant documentation files to reflect changes



Implementation Approach
Phase 1: Fix UI & Frontend Architecture
Step 1: Restructure Invoice Template

Fix table layout to ensure proper horizontal alignment
Add necessary CSS classes for consistent display
Ensure proper mobile responsiveness

Step 2: Centralize CSS Management

Create dedicated CSS file for invoice components
Apply consistent styling for all invoice elements
Ensure dark mode compatibility

Step 3: Refactor JavaScript Logic

Extract JavaScript from HTML into separate files
Create reusable component for line items
Implement proper event delegation

Phase 2: Backend Integration & Business Logic
Step 1: Enhance Billing Service

Modify service functions to support complex invoice generation
Implement item grouping by type and GST applicability
Add support for different invoice types and rules

Step 2: Update API Integration

Ensure proper item search functionality through API
Support dynamic changes based on item type selection
Handle medicine-specific fields and batch selection

Step 3: Modify Form Processing

Update form processing to handle new business logic
Ensure proper validation for all required fields
Maintain backward compatibility

Phase 3: Testing & Integration
Step 1: Develop Tests

Create comprehensive tests for new business logic
Verify frontend-backend integration
Ensure backward compatibility

Step 2: Final Integration

Ensure all components work together seamlessly
Verify performance and responsiveness
Document any required configuration changes

This phased approach allows for manageable implementation while maintaining the project's architecture and guidelines. Each phase builds upon the previous one, ensuring a cohesive final solution.