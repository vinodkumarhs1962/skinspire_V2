-- Test Data Creation for Invoice Testing
DO $$
DECLARE 
    v_hospital_id UUID := '4ef72e18-e65d-4766-b9eb-0308c42485ca';  -- Replace with your actual hospital ID
    
    -- Variables to store IDs for references
    v_antibiotics_cat UUID;
    v_painrelievers_cat UUID;
    v_topical_cat UUID;
    v_vitamins_cat UUID;
    v_otc_cat UUID;
    v_procedure_consumables_cat UUID;
    v_basic_consumables_cat UUID;
    v_skincare_products_cat UUID;
    v_makeup_products_cat UUID;
    
    -- Manufacturer IDs
    v_medpharm_id UUID;
    v_dermacare_id UUID;
    v_vitalife_id UUID;
    v_mediequip_id UUID;
    
    -- Supplier IDs
    v_medisupplies_id UUID;
    v_skincare_products_id UUID;
    v_medequip_suppliers_id UUID;
    
    -- Medicine IDs
    v_amoxicillin_id UUID;
    v_hydrocortisone_id UUID;
    v_paracetamol_id UUID;
    v_multivitamin_id UUID;
    v_gloves_id UUID;
    v_facemask_id UUID;
    v_moisturizer_id UUID;
    v_sunscreen_id UUID;
    
    -- Service IDs
    v_derm_consult_id UUID;
    v_basic_facial_id UUID;
    v_advanced_facial_id UUID;
    v_acne_treatment_id UUID;
    
    -- Package family IDs
    v_skincare_family_id UUID;
    v_acne_family_id UUID;
    
    -- Package IDs
    v_basic_facial_pkg_id UUID;
    v_premium_facial_pkg_id UUID;
    v_acne_care_pkg_id UUID;

BEGIN
    -- =============================================
    -- 1. Medicine Categories
    -- =============================================
    INSERT INTO medicine_categories (
        category_id, 
        hospital_id, 
        name, 
        description, 
        gst_rate, 
        requires_prescription, 
        category_type, 
        procedure_linked, 
        status,
        created_at,
        updated_at
    ) VALUES
    -- Regular Prescription medicines
    (gen_random_uuid(), v_hospital_id, 'Antibiotics', 'Antibiotic medications', 12.0, TRUE, 'Prescription', FALSE, 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'Pain Relievers', 'Pain relief medications', 12.0, TRUE, 'Prescription', FALSE, 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'Topical Creams', 'Skin application creams and ointments', 12.0, TRUE, 'Prescription', FALSE, 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'Vitamins', 'Vitamin supplements', 12.0, FALSE, 'OTC', FALSE, 'active', NOW(), NOW()),
    -- OTC Medicines
    (gen_random_uuid(), v_hospital_id, 'Basic OTC', 'Over-the-counter basic medications', 12.0, FALSE, 'OTC', FALSE, 'active', NOW(), NOW()),
    -- Consumables
    (gen_random_uuid(), v_hospital_id, 'Procedure Consumables', 'Consumables used in procedures', 12.0, FALSE, 'Consumable', TRUE, 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'Basic Consumables', 'General consumables', 12.0, FALSE, 'Consumable', FALSE, 'active', NOW(), NOW()),
    -- Products
    (gen_random_uuid(), v_hospital_id, 'Skincare Products', 'Skincare retail products', 18.0, FALSE, 'Product', FALSE, 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'Makeup Products', 'Makeup retail products', 18.0, FALSE, 'Product', FALSE, 'active', NOW(), NOW());

    -- Get category IDs for reference
    SELECT category_id INTO v_antibiotics_cat FROM medicine_categories WHERE name = 'Antibiotics' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_painrelievers_cat FROM medicine_categories WHERE name = 'Pain Relievers' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_topical_cat FROM medicine_categories WHERE name = 'Topical Creams' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_vitamins_cat FROM medicine_categories WHERE name = 'Vitamins' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_otc_cat FROM medicine_categories WHERE name = 'Basic OTC' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_procedure_consumables_cat FROM medicine_categories WHERE name = 'Procedure Consumables' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_basic_consumables_cat FROM medicine_categories WHERE name = 'Basic Consumables' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_skincare_products_cat FROM medicine_categories WHERE name = 'Skincare Products' AND hospital_id = v_hospital_id;
    SELECT category_id INTO v_makeup_products_cat FROM medicine_categories WHERE name = 'Makeup Products' AND hospital_id = v_hospital_id;

    -- =============================================
    -- 2. Manufacturers
    -- =============================================
    INSERT INTO manufacturers (
        manufacturer_id,
        hospital_id,
        manufacturer_name,
        manufacturer_address,
        specialization,
        gst_registration_number,
        pan_number,
        tax_type,
        state_code,
        remarks,
        status,
        created_at,
        updated_at
    ) VALUES
    (gen_random_uuid(), v_hospital_id, 'MedPharm Ltd', '{"street": "123 Pharma Road", "city": "Mumbai", "state": "Maharashtra", "country": "India", "pincode": "400001"}', 'Generic Pharmaceuticals', '27AABCM1234A1Z5', 'AABCM1234A', 'Regular', '27', 'Major supplier of generic medications', 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'DermaCare', '{"street": "45 Beauty Avenue", "city": "Bengaluru", "state": "Karnataka", "country": "India", "pincode": "560001"}', 'Dermatological Products', '29XXBCD5678B1Z3', 'XXBCD5678B', 'Regular', '29', 'Specialized in skin care products', 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'VitaLife', '{"street": "78 Health Street", "city": "Chennai", "state": "Tamil Nadu", "country": "India", "pincode": "600001"}', 'Nutritional Supplements', '33PQRST8765C1Z9', 'PQRST8765C', 'Regular', '33', 'Vitamins and supplements manufacturer', 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'MediEquip Solutions', '{"street": "90 Equipment Lane", "city": "Delhi", "state": "Delhi", "country": "India", "pincode": "110001"}', 'Medical Equipment', '07LMNOP4321D1Z7', 'LMNOP4321D', 'Regular', '07', 'Supplies medical equipment and consumables', 'active', NOW(), NOW());

    -- Get manufacturer IDs for reference
    SELECT manufacturer_id INTO v_medpharm_id FROM manufacturers WHERE manufacturer_name = 'MedPharm Ltd' AND hospital_id = v_hospital_id;
    SELECT manufacturer_id INTO v_dermacare_id FROM manufacturers WHERE manufacturer_name = 'DermaCare' AND hospital_id = v_hospital_id;
    SELECT manufacturer_id INTO v_vitalife_id FROM manufacturers WHERE manufacturer_name = 'VitaLife' AND hospital_id = v_hospital_id;
    SELECT manufacturer_id INTO v_mediequip_id FROM manufacturers WHERE manufacturer_name = 'MediEquip Solutions' AND hospital_id = v_hospital_id;

    -- =============================================
    -- 3. Suppliers
    -- =============================================
    INSERT INTO suppliers (
        supplier_id,
        hospital_id,
        supplier_name,
        supplier_category,
        supplier_address,
        contact_person_name,
        contact_info,
        manager_name,
        manager_contact_info,
        email,
        black_listed,
        performance_rating,
        payment_terms,
        gst_registration_number,
        pan_number,
        tax_type,
        state_code,
        bank_details,
        remarks,
        status,
        created_at,
        updated_at
    ) VALUES
    (gen_random_uuid(), v_hospital_id, 'MediSupplies Distributors', 'Distributor', 
    '{"street": "123 Supply Street", "city": "Bengaluru", "state": "Karnataka", "country": "India", "pincode": "560001"}',
    'Rajesh Kumar', '{"phone": "9876543210", "mobile": "8765432109"}',
    'Sunita Sharma', '{"phone": "9876543211", "mobile": "8765432108"}',
    'contact@medisupplies.com', FALSE, 5, 'Net 30', 
    '29ABCDE1234F1Z5', 'ABCDE1234F', 'Regular', '29',
    '{"bank_name": "HDFC Bank", "account_no": "12345678901234", "ifsc_code": "HDFC0001234"}',
    'Primary medicine supplier', 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'SkinCare Products', 'Retail Supplier', 
    '{"street": "45 Beauty Road", "city": "Mumbai", "state": "Maharashtra", "country": "India", "pincode": "400001"}',
    'Priya Singh', '{"phone": "9876543212", "mobile": "8765432107"}',
    'Vikram Patel', '{"phone": "9876543213", "mobile": "8765432106"}',
    'orders@skincareproducts.com', FALSE, 4, 'Net 45', 
    '27PQRST5678G1Z8', 'PQRST5678G', 'Regular', '27',
    '{"bank_name": "ICICI Bank", "account_no": "98765432109876", "ifsc_code": "ICIC0005678"}',
    'Specialized in skincare products', 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'MedEquip Suppliers', 'Equipment Supplier', 
    '{"street": "78 Equipment Avenue", "city": "Delhi", "state": "Delhi", "country": "India", "pincode": "110001"}',
    'Anil Gupta', '{"phone": "9876543214", "mobile": "8765432105"}',
    'Meena Verma', '{"phone": "9876543215", "mobile": "8765432104"}',
    'info@medequipsuppliers.com', FALSE, 4, 'Net 30', 
    '07UVWXY9012H1Z3', 'UVWXY9012H', 'Regular', '07',
    '{"bank_name": "State Bank of India", "account_no": "56789012345678", "ifsc_code": "SBIN0012345"}',
    'Medical equipment and consumables', 'active', NOW(), NOW());

    -- Get supplier IDs for reference
    SELECT supplier_id INTO v_medisupplies_id FROM suppliers WHERE supplier_name = 'MediSupplies Distributors' AND hospital_id = v_hospital_id;
    SELECT supplier_id INTO v_skincare_products_id FROM suppliers WHERE supplier_name = 'SkinCare Products' AND hospital_id = v_hospital_id;
    SELECT supplier_id INTO v_medequip_suppliers_id FROM suppliers WHERE supplier_name = 'MedEquip Suppliers' AND hospital_id = v_hospital_id;

    -- =============================================
    -- 4. Medicines 
    -- =============================================
    INSERT INTO medicines (
        medicine_id,
        hospital_id,
        medicine_name,
        manufacturer_id,
        preferred_supplier_id,
        category_id,
        generic_name,
        dosage_form,
        unit_of_measure,
        medicine_type,
        hsn_code,
        gst_rate,
        cgst_rate,
        sgst_rate,
        igst_rate,
        is_gst_exempt,
        gst_inclusive,
        safety_stock,
        priority,
        current_stock,
        prescription_required,
        is_consumable,
        status,
        created_at,
        updated_at
    ) VALUES
    -- Prescription Medicines (Antibiotics)
    (gen_random_uuid(), v_hospital_id, 'Amoxicillin 500mg', v_medpharm_id, v_medisupplies_id, v_antibiotics_cat,
    'Amoxicillin', 'Tablet', 'Strips', 'Prescription', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    50, 'High', 200, TRUE, FALSE, 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Azithromycin 250mg', v_medpharm_id, v_medisupplies_id, v_antibiotics_cat,
    'Azithromycin', 'Tablet', 'Strips', 'Prescription', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    30, 'Medium', 150, TRUE, FALSE, 'active', NOW(), NOW()),

    -- Prescription Medicines (Pain Relievers)
    (gen_random_uuid(), v_hospital_id, 'Ibuprofen 400mg', v_medpharm_id, v_medisupplies_id, v_painrelievers_cat,
    'Ibuprofen', 'Tablet', 'Strips', 'Prescription', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    100, 'Medium', 300, TRUE, FALSE, 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Diclofenac Gel 30g', v_medpharm_id, v_medisupplies_id, v_painrelievers_cat,
    'Diclofenac', 'Gel', 'Tubes', 'Prescription', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    40, 'Medium', 120, TRUE, FALSE, 'active', NOW(), NOW()),

    -- Prescription Medicines (Topical Creams)
    (gen_random_uuid(), v_hospital_id, 'Hydrocortisone Cream 1% 15g', v_dermacare_id, v_skincare_products_id, v_topical_cat,
    'Hydrocortisone', 'Cream', 'Tubes', 'Prescription', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    25, 'Medium', 75, TRUE, FALSE, 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Clotrimazole Cream 1% 20g', v_dermacare_id, v_skincare_products_id, v_topical_cat,
    'Clotrimazole', 'Cream', 'Tubes', 'Prescription', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    20, 'Medium', 60, TRUE, FALSE, 'active', NOW(), NOW()),

    -- OTC Medicines
    (gen_random_uuid(), v_hospital_id, 'Paracetamol 500mg', v_medpharm_id, v_medisupplies_id, v_otc_cat,
    'Paracetamol', 'Tablet', 'Strips', 'OTC', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    200, 'High', 500, FALSE, FALSE, 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Cetirizine 10mg', v_medpharm_id, v_medisupplies_id, v_otc_cat,
    'Cetirizine', 'Tablet', 'Strips', 'OTC', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    100, 'Medium', 250, FALSE, FALSE, 'active', NOW(), NOW()),

    -- Vitamins
    (gen_random_uuid(), v_hospital_id, 'Multivitamin Tablets', v_vitalife_id, v_medisupplies_id, v_vitamins_cat,
    'Multiple Vitamins', 'Tablet', 'Bottles', 'OTC', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    50, 'Low', 100, FALSE, FALSE, 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Vitamin C 500mg', v_vitalife_id, v_medisupplies_id, v_vitamins_cat,
    'Ascorbic Acid', 'Tablet', 'Bottles', 'OTC', '30049099', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    40, 'Low', 80, FALSE, FALSE, 'active', NOW(), NOW()),

    -- Consumables
    (gen_random_uuid(), v_hospital_id, 'Disposable Gloves', v_mediequip_id, v_medequip_suppliers_id, v_basic_consumables_cat,
    'Latex Gloves', 'Box', 'Boxes', 'Consumable', '40151900', 12.0, 6.0, 6.0, 12.0, FALSE, FALSE,
    100, 'High', 200, FALSE, TRUE, 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Facial Sheet Masks', v_dermacare_id, v_skincare_products_id, v_procedure_consumables_cat,
    'Cotton Sheet Masks', 'Pack', 'Packs', 'Consumable', '33049990', 18.0, 9.0, 9.0, 18.0, FALSE, FALSE,
    30, 'Medium', 60, FALSE, TRUE, 'active', NOW(), NOW()),

    -- Skincare Products
    (gen_random_uuid(), v_hospital_id, 'Moisturizing Cream 50g', v_dermacare_id, v_skincare_products_id, v_skincare_products_cat,
    'Moisturizer', 'Jar', 'Jars', 'Product', '33049990', 18.0, 9.0, 9.0, 18.0, FALSE, FALSE,
    20, 'Medium', 40, FALSE, FALSE, 'active', NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Sunscreen SPF 50 100ml', v_dermacare_id, v_skincare_products_id, v_skincare_products_cat,
    'Sunscreen', 'Bottle', 'Bottles', 'Product', '33049990', 18.0, 9.0, 9.0, 18.0, FALSE, FALSE,
    25, 'Medium', 50, FALSE, FALSE, 'active', NOW(), NOW());

    -- Get medicine IDs for reference
    SELECT medicine_id INTO v_amoxicillin_id FROM medicines WHERE medicine_name = 'Amoxicillin 500mg' AND hospital_id = v_hospital_id;
    SELECT medicine_id INTO v_hydrocortisone_id FROM medicines WHERE medicine_name = 'Hydrocortisone Cream 1% 15g' AND hospital_id = v_hospital_id;
    SELECT medicine_id INTO v_paracetamol_id FROM medicines WHERE medicine_name = 'Paracetamol 500mg' AND hospital_id = v_hospital_id;
    SELECT medicine_id INTO v_multivitamin_id FROM medicines WHERE medicine_name = 'Multivitamin Tablets' AND hospital_id = v_hospital_id;
    SELECT medicine_id INTO v_gloves_id FROM medicines WHERE medicine_name = 'Disposable Gloves' AND hospital_id = v_hospital_id;
    SELECT medicine_id INTO v_facemask_id FROM medicines WHERE medicine_name = 'Facial Sheet Masks' AND hospital_id = v_hospital_id;
    SELECT medicine_id INTO v_moisturizer_id FROM medicines WHERE medicine_name = 'Moisturizing Cream 50g' AND hospital_id = v_hospital_id;
    SELECT medicine_id INTO v_sunscreen_id FROM medicines WHERE medicine_name = 'Sunscreen SPF 50 100ml' AND hospital_id = v_hospital_id;

    -- =============================================
    -- 5. Services
    -- =============================================
    INSERT INTO services (
        service_id,
        hospital_id,
        code,
        service_name,
        price,
        currency_code,
        sac_code,
        gst_rate,
        cgst_rate,
        sgst_rate,
        igst_rate,
        is_gst_exempt,
        priority,
        service_owner,
        max_discount,
        created_at,
        updated_at
    ) VALUES
    (gen_random_uuid(), v_hospital_id, 'CONS-GEN', 'General Consultation', 500.00, 'INR', '998321', 18.0, 9.0, 9.0, 18.0, FALSE, 'High', 'General Medicine', 10.0, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'CONS-DERM', 'Dermatology Consultation', 800.00, 'INR', '998321', 18.0, 9.0, 9.0, 18.0, FALSE, 'High', 'Dermatology', 10.0, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'FACIAL-BASIC', 'Basic Facial', 1500.00, 'INR', '998321', 18.0, 9.0, 9.0, 18.0, FALSE, 'Medium', 'Skin Care', 15.0, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'FACIAL-ADVANCE', 'Advanced Facial', 3000.00, 'INR', '998321', 18.0, 9.0, 9.0, 18.0, FALSE, 'Medium', 'Skin Care', 15.0, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'TREAT-ACNE', 'Acne Treatment Session', 2500.00, 'INR', '998321', 18.0, 9.0, 9.0, 18.0, FALSE, 'Medium', 'Dermatology', 10.0, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'LASER-HAIR', 'Laser Hair Removal (Small Area)', 3500.00, 'INR', '998321', 18.0, 9.0, 9.0, 18.0, FALSE, 'Medium', 'Laser Treatment', 5.0, NOW(), NOW());

    -- Get service IDs for reference
    SELECT service_id INTO v_derm_consult_id FROM services WHERE code = 'CONS-DERM' AND hospital_id = v_hospital_id;
    SELECT service_id INTO v_basic_facial_id FROM services WHERE code = 'FACIAL-BASIC' AND hospital_id = v_hospital_id;
    SELECT service_id INTO v_advanced_facial_id FROM services WHERE code = 'FACIAL-ADVANCE' AND hospital_id = v_hospital_id;
    SELECT service_id INTO v_acne_treatment_id FROM services WHERE code = 'TREAT-ACNE' AND hospital_id = v_hospital_id;

    -- =============================================
    -- 6. Package Families
    -- =============================================
    INSERT INTO package_families (
        package_family_id,
        hospital_id,
        package_family,
        description,
        status,
        created_at,
        updated_at
    ) VALUES
    (gen_random_uuid(), v_hospital_id, 'Skin Care Packages', 'Various skin care treatment packages', 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'Acne Treatment Packages', 'Packages for acne treatment and prevention', 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, 'Hair Care Packages', 'Hair care and treatment packages', 'active', NOW(), NOW());

    -- Get package family IDs for reference
    SELECT package_family_id INTO v_skincare_family_id FROM package_families WHERE package_family = 'Skin Care Packages' AND hospital_id = v_hospital_id;
    SELECT package_family_id INTO v_acne_family_id FROM package_families WHERE package_family = 'Acne Treatment Packages' AND hospital_id = v_hospital_id;

    -- =============================================
    -- 7. Packages
    -- =============================================
    INSERT INTO packages (
        package_id,
        hospital_id,
        package_family_id,
        package_name,
        price,
        currency_code,
        gst_rate,
        cgst_rate,
        sgst_rate,
        igst_rate,
        is_gst_exempt,
        service_owner,
        max_discount,
        status,
        created_at,
        updated_at
    ) VALUES
    (gen_random_uuid(), v_hospital_id, v_skincare_family_id, 'Basic Facial Package', 1500.00, 'INR', 18.0, 9.0, 9.0, 18.0, FALSE, 'Skin Care', 10.0, 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_skincare_family_id, 'Premium Facial Package', 3500.00, 'INR', 18.0, 9.0, 9.0, 18.0, FALSE, 'Skin Care', 10.0, 'active', NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_acne_family_id, 'Acne Care Package', 5000.00, 'INR', 18.0, 9.0, 9.0, 18.0, FALSE, 'Dermatology', 5.0, 'active', NOW(), NOW());

    -- Get package IDs for reference
    SELECT package_id INTO v_basic_facial_pkg_id FROM packages WHERE package_name = 'Basic Facial Package' AND hospital_id = v_hospital_id;
    SELECT package_id INTO v_premium_facial_pkg_id FROM packages WHERE package_name = 'Premium Facial Package' AND hospital_id = v_hospital_id;
    SELECT package_id INTO v_acne_care_pkg_id FROM packages WHERE package_name = 'Acne Care Package' AND hospital_id = v_hospital_id;

    -- =============================================
    -- 8. Package Service Mapping
    -- =============================================
    INSERT INTO package_service_mapping (
        mapping_id,
        hospital_id,
        package_id,
        service_id,
        sessions,
        is_optional,
        created_at,
        updated_at
    ) VALUES
    -- Basic Facial Package Services
    (gen_random_uuid(), v_hospital_id, v_basic_facial_pkg_id, v_derm_consult_id, 1, FALSE, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_basic_facial_pkg_id, v_basic_facial_id, 1, FALSE, NOW(), NOW()),

    -- Premium Facial Package Services
    (gen_random_uuid(), v_hospital_id, v_premium_facial_pkg_id, v_derm_consult_id, 1, FALSE, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_premium_facial_pkg_id, v_advanced_facial_id, 1, FALSE, NOW(), NOW()),

    -- Acne Care Package Services
    (gen_random_uuid(), v_hospital_id, v_acne_care_pkg_id, v_derm_consult_id, 1, FALSE, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_acne_care_pkg_id, v_acne_treatment_id, 2, FALSE, NOW(), NOW());

    -- =============================================
    -- 9. Consumable Standards
    -- =============================================
    INSERT INTO consumable_standards (
        standard_id,
        hospital_id,
        service_id,
        medicine_id,
        standard_quantity,
        unit_of_measure,
        is_active,
        created_at,
        updated_at
    ) VALUES
    -- Basic Facial Consumables
    (gen_random_uuid(), v_hospital_id, v_basic_facial_id, v_facemask_id, 1.0, 'Packs', TRUE, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_basic_facial_id, v_moisturizer_id, 0.1, 'Jars', TRUE, NOW(), NOW()),

    -- Advanced Facial Consumables
    (gen_random_uuid(), v_hospital_id, v_advanced_facial_id, v_facemask_id, 2.0, 'Packs', TRUE, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_advanced_facial_id, v_moisturizer_id, 0.15, 'Jars', TRUE, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_advanced_facial_id, v_sunscreen_id, 0.05, 'Bottles', TRUE, NOW(), NOW()),

    -- Acne Treatment Consumables
    (gen_random_uuid(), v_hospital_id, v_acne_treatment_id, v_gloves_id, 0.05, 'Boxes', TRUE, NOW(), NOW()),
    (gen_random_uuid(), v_hospital_id, v_acne_treatment_id, v_hydrocortisone_id, 0.2, 'Tubes', TRUE, NOW(), NOW());

    -- =============================================
    -- 10. Inventory for Batches (for testing)
    -- =============================================
    INSERT INTO inventory (
        stock_id,
        hospital_id,
        stock_type,
        medicine_id,
        distributor_invoice_no,
        medicine_name,
        medicine_category,
        batch,
        expiry,
        pack_purchase_price,
        pack_mrp,
        units_per_pack,
        unit_price,
        sale_price,
        units,
        current_stock,
        location,
        transaction_date,
        created_at,
        updated_at
    ) VALUES
    -- Amoxicillin Batches
    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_amoxicillin_id, 'INIT-001',
    'Amoxicillin 500mg', 'Antibiotics', 'AM23001', '2026-05-31', 150.00, 195.00, 10, 19.50, 25.00,
    100, 100, 'Main Pharmacy', NOW(), NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_amoxicillin_id, 'INIT-002',
    'Amoxicillin 500mg', 'Antibiotics', 'AM23002', '2026-06-30', 155.00, 200.00, 10, 20.00, 26.00,
    100, 100, 'Main Pharmacy', NOW(), NOW(), NOW()),

    -- Hydrocortisone Batches
    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_hydrocortisone_id, 'INIT-003',
    'Hydrocortisone Cream 1% 15g', 'Topical Creams', 'HC23001', '2025-12-31', 120.00, 160.00, 1, 160.00, 180.00,
    50, 50, 'Main Pharmacy', NOW(), NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_hydrocortisone_id, 'INIT-004',
    'Hydrocortisone Cream 1% 15g', 'Topical Creams', 'HC23002', '2026-01-31', 122.00, 165.00, 1, 165.00, 185.00,
    25, 25, 'Main Pharmacy', NOW(), NOW(), NOW()),

    -- Paracetamol Batches
    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_paracetamol_id, 'INIT-005',
    'Paracetamol 500mg', 'Basic OTC', 'PC23001', '2026-07-31', 40.00, 50.00, 10, 5.00, 7.00,
    200, 200, 'Main Pharmacy', NOW(), NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_paracetamol_id, 'INIT-006',
    'Paracetamol 500mg', 'Basic OTC', 'PC23002', '2026-08-31', 42.00, 52.00, 10, 5.20, 7.50,
    300, 300, 'Main Pharmacy', NOW(), NOW(), NOW()),

    -- Facial Sheet Masks Batches
    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_facemask_id, 'INIT-007',
    'Facial Sheet Masks', 'Procedure Consumables', 'FM23001', '2027-01-31', 400.00, 600.00, 10, 60.00, 80.00,
    30, 30, 'Main Pharmacy', NOW(), NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_facemask_id, 'INIT-008',
    'Facial Sheet Masks', 'Procedure Consumables', 'FM23002', '2027-02-28', 410.00, 620.00, 10, 62.00, 85.00,
    30, 30, 'Main Pharmacy', NOW(), NOW(), NOW()),

    -- Moisturizer Batches
    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_moisturizer_id, 'INIT-009',
    'Moisturizing Cream 50g', 'Skincare Products', 'MC23001', '2026-06-30', 250.00, 400.00, 1, 400.00, 500.00,
    20, 20, 'Main Pharmacy', NOW(), NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_moisturizer_id, 'INIT-010',
    'Moisturizing Cream 50g', 'Skincare Products', 'MC23002', '2026-07-31', 260.00, 420.00, 1, 420.00, 525.00,
    20, 20, 'Main Pharmacy', NOW(), NOW(), NOW()),

    -- Sunscreen Batches
    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_sunscreen_id, 'INIT-011',
    'Sunscreen SPF 50 100ml', 'Skincare Products', 'SS23001', '2026-05-31', 300.00, 450.00, 1, 450.00, 550.00,
    15, 15, 'Main Pharmacy', NOW(), NOW(), NOW()),

    (gen_random_uuid(), v_hospital_id, 'Opening Stock', v_sunscreen_id, 'INIT-012',
    'Sunscreen SPF 50 100ml', 'Skincare Products', 'SS23002', '2026-06-30', 310.00, 470.00, 1, 470.00, 575.00,
    10, 10, 'Main Pharmacy', NOW(), NOW(), NOW());

END;
$$;