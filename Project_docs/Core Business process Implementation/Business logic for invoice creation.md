Business Logic for SkinSpire Clinic Invoice System
Invoice Creation Process

Patient Selection: User selects a patient using the search interface
Line Item Addition:

Items can be services, packages, or medicines
Medicines may be regular items or "included in consultation"


Pharmacy Registration Check:

The system checks if the hospital has a valid pharmacy registration
A registration is valid if it exists and has not expired


Prescription Item Handling:

If hospital has valid pharmacy registration:

Each prescription item is billed individually
Items appear as separate line items on the invoice

If hospital has no valid pharmacy registration:

Prescription items are consolidated into "Doctor's Examination and Treatment"
This appears as a single line item on the invoice
The GST is still tracked for reporting purposes
Inventory updates still occur for each individual medicine

GST Calculation:

For Regular Services/Packages: GST is added to the price
For Medicines/Prescriptions: GST is included in MRP and reverse-calculated
For "Doctor's Examination": Treated like medicines - GST is included in MRP


Invoice Generation:

Different invoice types may be created (GST/non-GST)
Invoice numbers follow specific formats (e.g., GST/2025-2026/00016)
The system automatically assigns the next sequential number



GST Calculation Logic

Service/Package Items:

Taxable Value = Price × Quantity - Discount
GST Amount = Taxable Value × GST Rate


Medicine/Prescription Items:

MRP already includes GST
Base Value = MRP ÷ (1 + GST Rate/100)
GST Amount = MRP - Base Value


Doctor's Examination Items (special case):

Uses the same GST calculation logic as medicines
MRP already includes GST
Base Value = MRP ÷ (1 + GST Rate/100)
GST Amount = MRP - Base Value



Invoice Printing

General Information:

Hospital details including name, address, contact info
GSTIN displayed if GST invoice
Pharmacy registration number and validity displayed if available


Line Item Display:

Each line item shows quantity, price, discount (if any)
For GST invoices, additional columns show taxable value, GST breakdown
For medicines and Doctor's Examination, GST is reverse-calculated from MRP
For services, GST is calculated on top of price


GST Summary:

Groups items by GST rate
Shows taxable value and GST components for each rate
Displays totals for CGST/SGST (intrastate) or IGST (interstate)



Files and Responsibilities

invoice.js:

Handles client-side calculations
Contains specialized function for Doctor's Examination GST calculation
Manages UI interactions and form handling
Performs initial GST calculations during invoice creation


billing_service.py:

Contains the server-side business logic
Checks for valid pharmacy registration
Decides whether to consolidate prescriptions based on registration status
Contains specialized function for Doctor's Examination GST calculation
Handles invoice creation, splitting, and storage


print_invoice.html:

Displays the final invoice for printing
Shows pharmacy registration if available
Includes special formatting and calculations for GST breakdown
Contains special logic to detect Doctor's Examination items
Provides visual feedback for email/WhatsApp functions


billing_views.py:

Connects the frontend and backend
Manages routing and request handling
Prepares data for template rendering
Handles email/WhatsApp sending requests



The system maintains consistency by having the specialized Doctor's Examination handling logic in both the client-side code (invoice.js) and server-side code (billing_service.py), ensuring the same GST calculations are performed in both places. The decision to consolidate prescriptions happens on the server side based on pharmacy registration status, while the client simply displays what the server has provided.RetryClaude can make mistakes. Please double-check responses.