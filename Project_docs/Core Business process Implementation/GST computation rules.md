GST Computation Logic for Different Item Types
The system handles GST calculations differently based on item type. Here's a detailed explanation with examples:
1. Service/Package Items (Forward GST Calculation)
For services and packages, GST is added on top of the base price.
Formula:

Taxable Value = Rate / MRP * Qty 
GST Amount = Taxable Value × GST Rate
Discount =  Taxable Value * Discount %age
Total = Taxable Value - Discount + GST Amount

Example:

Service: Facial Treatment
Price (Rate / MRP):  Rs.1,000
Quantity: 2
Discount: 10% 
GST Rate: 18%

Calculation:

Taxable Value =  Rs.1,000 × 2 -  Rs.2,000
CGST (9%) =  Rs.2000 × 9% =  Rs.180
SGST (9%) =  Rs.2000 × 9% =  Rs.180
GST Amount =  Rs.180 +  Rs.180 =  Rs.360
Discount =  2000 * 10% =  Rs.200
Total =  Rs.2000 - 200 +  Rs.360 =  Rs.2160

2. Medicine/Prescription Items (MRP based items  :  Reverse GST Calculation)
For medicines and prescriptions, GST is already included in the MRP, so we need to extract it.
Formula:

Taxable Value = MRP * Qty / (1 + GST %age / 100)
Discount =  Taxable Value * Discount %age 
Total = MRP - Discount
GST Amount = Taxable Value × GST Rate


Example:

Medicine: Amoxicillin 500mg
MRP:  Rs.150
Quantity: 2
Discount: 10
GST Rate: 12%

Calculation:

Taxable Value =  Rs.150 × 2 / (1 + 12/100 ) = 268  
Discount =   Rs.268 * 10% =  Rs.27
Total =  Rs.300 -  Rs.27 =  Rs.273
GST Amount =  Rs.268 × 12% =  Rs.32

CGST (6%) =  Rs.268 × 6% =  Rs.16
SGST (6%) =  Rs.268 × 6% =  Rs.16


3. Doctor's Examination and Treatment (Special Case) It is a consolidated prescription
For Doctor's Examination (consolidated prescriptions), It will be a nil GST

Prescription medicine  1   =  Total Amount  1  (Computed as per MRP based item)
Prescription medicine  2   =  Total Amount  2  (Computed as per MRP based item)
Prescription medicine  3   =  Total Amount  3  (Computed as per MRP based item)
Many other items as invoiced under Priscription medicine    
Doctor's Examination       =  Service Fees  (determined at the time of Invoice creation)


Doctor's Examination and Treatment Rate = Prescription medicine  1 + Prescription medicine  2 + Prescription medicine  3 + ...+  Doctor's Examination

Taxable Value = Doctor's Examionation & Treatment Rate
GST Amount = nil
Discount = 0 (Always)
Qty = 1

Example:

Medicine: Amoxicillin 500mg
MRP:  Rs.150
Quantity: 2
Discount: 10
GST Rate: 12%

After calculation as MRP based items logic  
TOtal amount =  Rs.273

Medicine: Paracetamol 500mg
MRP:  Rs.150
Quantity: 2
Discount: 10
GST Rate: 12%

After calculation as MRP based items logic  
TOtal amount =  Rs.273

Doctor's Examination Service
Rate : defailt 600   Editable field 
Quantity: 1
Discount: 10
GST Rate: Nil

Doctor's Examination and Treatment (consolidated prescriptions)

Calculation:

Doctor's Examination and Treatment Rate = Prescription medicine  1 + Prescription medicine  2 +  Doctor's Examination  =   Rs.273 +  Rs.273 +  Rs.600 =  Rs.1146

Qty  = 1
Discount : Nil
This will be a non-GST invoice with a seperate running serial number

