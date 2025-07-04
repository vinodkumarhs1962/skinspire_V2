USER MASTER					
Sr. No.	Field Name	Data Type (Arrow)	Field Type	Attribute	Field Properties
1	User id    (Phone number)	int 32	Numeric	Validate Phone no. with SMS.     Check, fPhone no. is aregistered as staff or Patient,  populate ID and name fields	Key field
2	Password	string	Text	Masked	Mandatory
3	Role	string	List	reference from separate role table.  Possible values are Doctor, Consultant, Therapispt, Staff Nurse, Clinic Manager, Assistant Manager, visiting expert, Patient, Administrator, Accountant, Pharmacy manager	Mandatory
4	Prefix	string	List	Mr. Mrs. Ms. Dr. Prof. Sir. Col.	Reference Field
5	First Name	string	Text		Reference Field
6	Last Name	string	Text		Reference Field
    Status 			Active / Inactie	
7	Staff  ID 	string	Text	Populated based on Phone no.  Can be edited	Conditional  reference
8	Patient  ID 	string	Text	Populated based on Phone no.  Can be edited	Conditional  reference
STAFF MASTER					
Sr. No.	Field Name	Data Type (Arrow)	Field Type	Attribute	Field Properties
1	Staff ID	int 32	Numeric	4 digit running serial number. This is automatically updated based on current record. This is not a user entered field 	Key Field
2	Role	string	List	reference from separate role table.  Possible values are Doctor, Consultant, Therapispt, Staff Nurse, Clinic Manager, Assistant Manager, visiting expert,  Administrator, Accountant, Pharmacy manager	Reference Field
3	Phone Number	int 32	Numeric	validate phone no. with SMS.  If phone number is registered as user,  populate all relevant fields from user table. 	Mandatory
4	Whether Empoyee?	bool	Radio Button	Yes, No	Mandatory
5	Prefix	string	List	Mr. Mrs. Ms. Dr. Prof. Sir. Col.	Mandatory
6	First Name	string	Text		Mandatory
7	Last Name	string	Text		Mandatory
8	E Mail ID	string	Text	Validate Email id	Mandatory
9	Gender	string	Radio Button	Male Female Trans gender, Not disclosed	Mandatory
10	Age	int 32	Numeric	Validation between 0 to 100. derived from date of birth	Derived
11	D.O.B.	date	Date	not more then current date and age not more than 110 years	Mandatory
12	Preferred Language	string	List	English, Hindi, Kannada, Tamil	Mandatory
13	City	string	List	All major cities of India.  Also provide user to enter if it is not in the list.	Mandatory
14	Address	Dictionary	Dictionary	3 lines for user entry	Mandatory
15	PIN CODE	int 32	Numeric	validation for six digits	Mandatory
16	Blood Group	string	List	O+ve, AB+ve, O-ve, AB-ve, A+ve, A-ve, B+ve, B-ve	Optional
17	Marital Status	string	Radio Button	Married, Single, Not disclosed, 	Mandatory
18	Date of Joining	date	Date	not more then current date	Mandatory
20	User ID	string	Text	E Mail id	Conditional Reference
21	Profile Picture	Picture	Picture		Optional
22	Documents			Moe then one document regarding address proof, ID proof education, etc  Datewise storage	Optional
23	Note	string	Text		Optional
PATIENT MASTER					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Patient id    (Phone number)	int 32	Numeric	10 digit no. preceded by country code. To validate with SMS in case of self registration.  In user based entry SMS based validation is bypassed	Key field
2	Prefix	string	List	Mr. Mrs. Ms. Dr. Prof. Sir. Col.	Mandatory
3	First Name	string	Text		Mandatory
4	Last Name	string	Text		Mandatory
5	Alternate Phone Number	int 32	Numeric	fixed length of 10 digits	Mandatory
6	Attender name 	string	Text		Optional
7	Relationship with Patient	string	Text		Optional
8	E Mail ID	string	Text		Optional
9	Gender	string	Radio Button	Male Female Trans gender, Not disclosed	Mandatory
10	Age	int 32	Numeric	Validation between 0 to 100	Mandatory
11	D.O.B.	date	Date		Optional
12	Preferred Language	string	List	English, Hindi, Kannada, Tamil	Mandatory
13	City	string	List	All major cities	Mandatory
14	Address	Dictionary	Dictionary	Multi line entry	Mandatory
15	PIN CODE	int 32	Numeric	vcalidation for six digits	Mandatory
16	Blood Group	string	List	O+ve, AB+ve, O-ve, AB-ve, A+ve, A-ve, B+ve, B-ve	Optional
17	Marital Status	string	Radio Button	Married, Single, Not disclosed, 	Mandatory
18	How did you know about us?	string	Radio Button	Walk In, Google serarch, Reference, Social media, others 	Mandatory
19	Any Kinown alergires 	Dictionary	Dictionary		Optional
20	Referred By	string	Text		Optional
21	Password	string	Text	Masked. Only in case of self registration	Mandatory
22	Profile Picture	Picture	Picture		Optional
23	Documents	Multi media 	Multi media 	Moe then one document regarding lab records, reports  or other information date wise storage	
24	Notes	Dictionary	Dictionary		optional
25	User ID	string	Text	E Mail id if record exists in user table based on phone number	Conditional Reference
APPOIONTMENT					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Appointment ID	int 32	Numeric	Running Sr. No.	Key Field
2	Patient ID	int 32	Numeric		Reference Field
3	Patient Prefix	string	List	Mr. Mrs. Ms. Dr. Prof. Sir. Col.	Mandatory
4	Patient First Name	string	Text	copied from master	Mandatory
5	Patient Last Name	string	Text	copied from master	Mandatory
6	Appointment Date	date	Date		Mandatory
7	Appointment Time	time64	Time		Mandatory
8	Doctor ID	int 32	Numeric		Reference Field
9	Doctor Name	string	Text	copied from master	Optional
    Department	string	Text	copied from master	Mandatory
10	Package	string	Text		Reference Field
11	Service	string	Text		Reference Field
12	Staff ID	int 32	Numeric		Reference Field
13	Staff Name	string	Text		Optional
14	Booking Status	string	List	Booked, Cancelled, Visited	Mandatory
15	Type	string	Text	In Person , Video Call, walk-in	Mandatory
16	Skip Billing	bool	Check Box	Skip Billing check box	Optional
17	Price 	int 32	Numeric		Optional
18	Bill No.	int 32	Numeric		Reference Field
19	Time Stamp	timestamp	Date	Automatic system entry	Mandatory
                    
DOCTOR CONSULTATION					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
CONSULTATION					
1	Appointment ID	int 32			Key Field
2	Patient ID	int 32			Reference Field
3	Patient Prefix	string	List	Mr. Mrs. Ms. Dr. Prof. Sir. Col.	Reference Field
4	Patient First Name	string			Reference Field
5	Patient Last Name	string			Reference Field
6	Consultation Date	date			Mandatory
7	Consultation Time	time64			Mandatory
    Consultation type			online,  In person	Reference Field
8	Doctor Name	string			Reference Field
9	BP	int 32			Optional
10	Pulse	int 32			Optional
11	Height	int 32			Optional
12	Weight	int 32			Optional
13	Temperature	int 32			Optional
14	BMI	int 32			Optional
15	Waist / hip	int 32			Optional
16	SPO2	int 32			Optional
17	Complaints	string			Optional
18	Diagnosis	string			Optional
19	Treatment Advise	string			Optional
20	Tests Requested	string			Optional
21	Next visit days	int 32			Optional
22	Date	date			Optional
23	Investigations	string			Optional
24	Referred to: Doctor	string			Optional
25	Speciality	string			Optional
26	Phone No.	int 32			Optional
27	follow up 	directory		history	Optional
                    
                    
Medicines Prescribed					
1	Appointment ID	int 32			Reference Field
2	Patient ID	int 32			Reference Field
3	Medicine Name	string			Reference Field
4	Frequency	string			Optional
5	Dosage	int 32			Optional
6	Morning	bool			Optional
7	Afternoon	bool			Optional
8	Evening	bool			Optional
9	Every 	string			Optional
10	Duration	int 32			Optional
11	Insturction	string			Optional
                    
BILLING					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
Invoice Header					
1	InvoiceType	string		Service, Cosmatic Products, Prescription / Emergency Drugs, Misc Bill	Mandatory
2	Invoice Date	date			Mandatory
3	Invoice ID	int 32			Key Field
4	Patient ID	int 32			Mandatory
5	Patient Prefix	string	List	Mr. Mrs. Ms. Dr. Prof. Sir. Col.	Reference Field
6	Patient First Name	string			Reference Field
7	Patient Last Name	string			Reference Field
8	Appointment ID	int 32			Mandatory
9	Appointment Date	date			Reference Field
10	Doctor Name	string			Reference Field
                    
Invoice Line Item					
1	Package ID	int 32			Reference Field
2	Package Name	string			Reference Field
3	Package Family	string			Reference Field
4	Service ID	int 32			Conditional Reference
5	Service Name	string			Reference Field
6	Medicine ID	int 32			Conditional Reference
7	Medicine Name	string			Reference Field
8	Batch	string			Reference Field
9	Expiry Date	date			Reference Field
10	Qty	int 32			Mandatory
11	Item Price	int 32			Reference Field
12	Item Discount	int 32			Reference Field
13	Gst(%)	int 32			Reference Field
14	Gst(Amt)	int 32			Reference Field
15	Disc Amt	int 32			Reference Field
16	Bill Value	int 32			Reference Field
17	Currency	string			Reference Field
18	Paid Amount CASH	int 32			Optional
19	Paid Amount Credit Card	int 32			Optional
20	Paid Amount Debit Card	int 32			Optional
21	Paid Amount UPI 	int 32			Optional
22	Total Amount Paid	int 32			Derived
23	Amount Due	int 32			Derived
24	Refunded Amount	int 32			Optional
                    
Package Family					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Package Family ID	string			Key Field
2	Package Family	string			Mandatory
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
Packages					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Package ID	int 32			Key Field
2	Package Name	string			Mandatory
3	Package Family	string			Reference Field
4	Price	int 32			Mandatory
5	CGST	int 32			Mandatory
6	IGST	int 32			Mandatory
7	Total GST	int 32			Derived
8	Active discontinued	string			Mandatory
9	Service Owner	string			Mandatory
10	Max Discount 	int 32			Optional
                    
                    
                    
                    
                    
Services					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Mandatory / Optional
1	CODE	int 32			
2	Service ID	int 32			
3	Service Name	string			
4	Package Name	string			
5	No. of Sessions for Package	int 32			
6	Price per Session excluding GST	int 32			
7	CGST	int 32			
8	IGST	int 32			
9	Total GST	int 32			
10	Total Price	int 32			
11	Priority	string			
12	Max Discount	int 32			
                    
PURCHASE ORDER					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
Header					
1	P.O. No. 	int 32			Key Field
2	P.O. Date	date			Mandatory
3	Manufacturer Name	string			Reference Field
4	Quotation ID	int 32			Optional
5	Quotation Date	date			Optional
    Deleted Flag	bool			Optional
Line Items					
6	Medicine Name	string			Mandatory
7	Medicine ID	int 32			Reference Field
8	Pack(Purchase Price)	int 32			Reference Field
9	Pack(MRP)	int 32			Reference Field
10	Units(Per Pack)	int 32			Reference Field
11	Units(Price) 	int 32			Reference Field
12	CGST	int 32			Reference Field
13	IGST	int 32			Reference Field
14	Total GST	int 32			Derived
15	Units	int 32			Mandatory
                    
SUPPLIER INVOICE					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
Header					
1	P.O. No. 	int 32			Key Field
2	P.O. Date	date			Mandatory
3	Manufacturer Name	string			Reference Field
4	Invoice ID	int 32			Reference Field
5	Invoice Date	date			Reference Field
Line Items					
6	Medicine Name	string			Mandatory
7	Medicine ID	int 32			Reference Field
8	Pack(Purchase Price)	int 32			Mandatory
9	Pack / Strip (MRP)	int 32			Mandatory
10	Units(Per Pack / Strip)	int 32			Mandatory
11	Units(Price) 	int 32			Mandatory
12	CGST 	int 32			Mandatory
13	IGST	int 32			Mandatory
14	Total GST	int 32			Derived
15	Units	int 32			Mandatory
                    
SUPPLIER MASTER					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Supplier ID	int 32			Key Field
2	Supplier Name	string			Mandatory
3	Supplier  Address	Dictionary			Optional
4	Supplier Category	string		Retail supplier, Distributor,  equitment dealer, trader	Reference Field
5	Black Listed?	bool			Optional
6	Performance Rating	int 32			Optional
7	Payment terms	string			Optional
8	Remarks	string			Optional
9	Contact Person Name	string			Optional
10	Contact No. 	int 32			Optional
11	Manager Name	string			Optional
12	Manager Contact no. 	int 32			Optional
                    
MANUFACTURER					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Manufacturer id	int 32			Key Field
2	Manufacturer Name	string			Mandatory
3	Manufacturer  Address	Dictionary			Optional
4	Specialization	string			Optional
5	Active / Inactive	bool			Optional
6	Remarks	string			Optional
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
MEDICINES					
Sr. No.	Field Name	Data Type	Field type	Attribute	Field Properties
1	Medicine ID	int 32			Key Field
2	Medicine  Name	string			Mandatory
3	Manufacturer Name	string			Optional
    Preferred Distributor name	string			Optional
4	Medicine Category	string		Emergency Drug, Priscription Drug, Cosmetic Drug, Consumable, Utility Stock, Low cost consumable, Misc	Reference Field
5	Safety Stock	int 32			Optional
6	CGST	int 32			Mandatory
7	IGST	int 32			Mandatory
8	Total GST	int 32			Derived
9	Current Stock Unit	int 32			Derived
10					
                    
INVENTORY					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Stock type	string	List	Opening Stock, Stock Adjustment, Purchase, Purchase Return, Sale, Sale Return, Free items	Mandatory
2	Distributor Invoice No.	int 32	Numeric	Automatic copy from transaction	Optional
3	Date of purchase	date	Date	Automatic copy from transaction	Optional
4	Distributor Name	string	Text	Automatic copy from transaction	Optional
5	P.O. No.	int 32	Numeric	Automatic copy from transaction	Optional
6	Bill ID	int 32	Numeric	Automatic copy from transaction	Optional
7	Bill Date	date	Date	Automatic copy from transaction	Optional
8	Patient ID 	int 32	Numeric	Automatic copy from transaction	Optional
9	Medicine ID	int 32	Numeric	Automatic copy from transaction	Mandatory
10	Medicine  Name	string	Text	Automatic copy from transaction	Mandatory
12	Medicine Category	string	List	Emergency Drug, Priscription Drug, Cosmetic Drug, Consumable, Utility Stock, Low cost consumable, Misc	Mandatory
13	Batch	string	Text	Automatic copy from transaction	Mandatory
14	Expiry	date	Date	Automatic copy from transaction	Mandatory
15	Pack(Purchase Price)	int 32	Numeric	Automatic copy from transaction	Mandatory
16	Pack(MRP)	int 32	Numeric	Automatic copy from transaction	Mandatory
17	Units(Per Pack)	int 32	Numeric	Automatic copy from transaction	Mandatory
18	Units(Price) - derived field	int 32	Numeric	Automatic copy from transaction	Mandatory
19	Sale Price	int 32	Numeric	Automatic copy from transaction	Mandatory
20	Units (Purchased / Sold)	int 32	Numeric	Automatic copy from transaction	Mandatory
21	%(Discount) 	int 32	Numeric	Automatic copy from transaction	Mandatory
22	CGST	int 32	Numeric	Automatic copy from transaction	Mandatory
23	IGST	int 32	Numeric	Automatic copy from transaction	Mandatory
24	Total GST	int 32	Numeric	Automatic copy from transaction	Mandatory
25	Reason 	string	Text		Optional
                    
                    
                    
Chart of Accounts 					
Sr. No.	Field Name	Data Type	Field Type	Attribute	Field Properties
1	Group	string	List	Assets, Liabilities, Income, Expense	Mandatory
2	GL Account No.	int 32	Numeric		Mandatory
3	Account Name	string	Date		Mandatory
4	Opening Balance 	int 32	Text		Optional
5	Opening Balance Date	date	Numeric		Optional
6	De-Activate 	bool	Check Box		Optional
                    
                    
Sr.No.	TABLE NAME				Details
1	  HOSPITAL Details  (Highest level of partition)				
2	  BRANCH DETAILS (FOR SAME HOSPITAL)				
3	AUTHORIZATION				
4	ROLE MASTER				
5	MEDICINE TYPES				
6	PREFIX				
7	BLOOD GROUP				
8	PREFERED LANGUAGE				
9	GENDER				
10	MARITAL STATUS				
11	CITY				
12	FIELD PARAMETERS SETTING (OPTIONAL, MANDATORY, VALIDATION DISABLED / ENABLED, CONDITIONAL VALIDATION)				
13	 BOOKING STATUS (APPOINTMENT)				
14	SERIAL NUMBER GENERATION (CURRENT SR. NO.)				
15	SPECIALITY (FOR DOCTORS)				
16	CONSULTATION TYPE				
17	 INVOICE TYPE				
18	MEDICINE CATEGORY				
19	 ASSET MASTER				
20	FACILITY MASTER				
21	STOCK TYPE				
22	Safety stock level (%age stock)				
23	SUPPLIER CATEGORY				
24	PERFORMANCE RATING				
25	 CHART OF ACCOUNTS				
26	ACCOUNT HEADS GROUPED BY Assets, Liabilities, Income, Expense				
27	PAYMENT GATEWAY SETTINGS				
28	 REPORT CONFIGURATION (TO BE ANALYSED)				
