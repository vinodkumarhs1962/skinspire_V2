Implementation Plan: Extend Universal Engine to Patients, Medicines, and Packages   │
     │                                                                                     │
     │ Overview                                                                            │
     │                                                                                     │
     │ Extend Universal Engine CRUD operations to three master entities following the      │
     │ supplier master pattern. All configurations will be in separate module files, using │
     │ plural naming convention (patients, medicines, packages).                           │
     │                                                                                     │
     │ ---                                                                                 │
     │ Entity 1: MEDICINES (Implement First - Simplest)                                    │
     │                                                                                     │
     │ Files to CREATE:                                                                    │
     │                                                                                     │
     │ 1. app/config/modules/medicine_config.py                                            │
     │   - Define ~35 fields (medicine_name, generic_name, dosage_form, medicine_type,     │
     │ etc.)                                                                               │
     │   - Map relationship fields: manufacturer_id, preferred_supplier_id, category_id    │
     │   - Configure entity dropdowns for manufacturer, supplier, category                 │
     │   - GST fields: hsn_code, gst_rate, cgst_rate, sgst_rate, igst_rate                 │
     │   - Pricing fields: cost_price, mrp, selling_price, mrp_effective_date              │
     │   - Inventory fields: safety_stock, current_stock, priority                         │
     │   - Filter mapping: medicine_name (SEARCH), manufacturer_id (RELATIONSHIP),         │
     │ medicine_type (SELECTION), mrp (AMOUNT)                                             │
     │   - View layout: Tabbed (Basic Info | Pricing & GST | Inventory | Relationships)    │
     │   - Summary cards: Total Medicines, Low Stock Items, Total Inventory Value          │
     │   - Export: config = MEDICINE_CONFIG                                                │
     │ 2. app/services/medicine_service.py (NEW - doesn't exist yet)                       │
     │   - Inherit from UniversalEntityService                                             │
     │   - Constructor: super().__init__('medicines', Medicine)                            │
     │   - Implement _add_virtual_calculations(): current stock value, reorder status, last│
     │  purchase info                                                                      │
     │   - Optional: Custom renderer for stock history                                     │
     │                                                                                     │
     │ Files to MODIFY:                                                                    │
     │                                                                                     │
     │ 3. app/config/entity_registry.py                                                    │
     │   - Add to ENTITY_REGISTRY:                                                         │
     │ "medicines": EntityRegistration(                                                    │
     │     category=EntityCategory.MASTER,                                                 │
     │     module="app.config.modules.medicine_config",                                    │
     │     service_class="app.services.medicine_service.MedicineService",                  │
     │     model_class="app.models.master.Medicine"                                        │
     │ )                                                                                   │
     │ 4. app/engine/universal_config_cache.py (Line ~465)                                 │
     │   - Add 'medicines' to common_entities list in preload_common_configurations()      │
     │ 5. app/api/routes/universal_api.py                                                  │
     │   - Add search_medicines() function (search by medicine_name, generic_name)         │
     │   - Update entity_search() routing to handle 'medicines'                            │
     │   - Return format: medicine_name as value (NOT medicine_id UUID)                    │
     │                                                                                     │
     │ ---                                                                                 │
     │ Entity 2: PACKAGES (Implement Second - Moderate Complexity)                         │
     │                                                                                     │
     │ Files to CREATE:                                                                    │
     │                                                                                     │
     │ 1. app/config/modules/package_config.py (NEW - replace or merge with existing)      │
     │   - Define ~25 fields (package_name, package_family_id, service_owner, price, etc.) │
     │   - Map relationship: package_family_id (entity dropdown)                           │
     │   - GST fields: gst_rate, cgst_rate, sgst_rate, igst_rate, is_gst_exempt            │
     │   - Pricing: price, currency_code, max_discount                                     │
     │   - Filter mapping: package_name (SEARCH), package_family_id (RELATIONSHIP), price  │
     │ (AMOUNT), status (SELECTION)                                                        │
     │   - View layout: Tabbed (Basic Info | Pricing & GST | Package Services)             │
     │   - Summary cards: Total Packages, Active Packages, Total Package Value             │
     │   - Export: config = PACKAGE_CONFIG                                                 │
     │ 2. app/services/package_service.py (Already EXISTS - extend it)                     │
     │   - Verify inheritance from UniversalEntityService                                  │
     │   - Constructor: super().__init__('packages', Package)                              │
     │   - Implement custom renderer: get_package_services() for services table            │
     │   - Add cache decorator: @cache_service_method('packages', 'service_list')          │
     │                                                                                     │
     │ Files to MODIFY:                                                                    │
     │                                                                                     │
     │ 3. app/config/entity_registry.py                                                    │
     │   - Add to ENTITY_REGISTRY:                                                         │
     │ "packages": EntityRegistration(                                                     │
     │     category=EntityCategory.MASTER,                                                 │
     │     module="app.config.modules.package_config",                                     │
     │     service_class="app.services.package_service.PackageService",                    │
     │     model_class="app.models.master.Package"                                         │
     │ )                                                                                   │
     │ 4. app/engine/universal_config_cache.py (Line ~465)                                 │
     │   - Add 'packages' to common_entities list                                          │
     │ 5. app/api/routes/universal_api.py                                                  │
     │   - Add search_packages() function (search by package_name)                         │
     │   - Update entity_search() routing                                                  │
     │   - Return format: package_name as value, include price in response                 │
     │                                                                                     │
     │ ---                                                                                 │
     │ Entity 3: PATIENTS (Implement Third - Most Complex)                                 │
     │                                                                                     │
     │ Files to CREATE:                                                                    │
     │                                                                                     │
     │ 1. app/config/modules/patient_config.py                                             │
     │   - Define ~40-45 fields total (10-15 virtual JSONB fields)                         │
     │   - System fields: patient_id, hospital_id, branch_id, mrn, is_active               │
     │   - Direct fields: title, first_name, last_name, blood_group                        │
     │   - Essential virtual fields from personal_info: date_of_birth, gender,             │
     │ marital_status, age                                                                 │
     │   - Essential virtual fields from contact_info: phone, email, address_line1, city,  │
     │ state, pincode                                                                      │
     │   - Essential virtual fields from emergency_contact: emergency_name,                │
     │ emergency_phone, emergency_relation                                                 │
     │   - Filter mapping: mrn (SEARCH), first_name/last_name (SEARCH), phone (SEARCH),    │
     │ branch_id (RELATIONSHIP), is_active (SELECTION)                                     │
     │   - View layout: Tabbed (Personal Info | Contact & Address | Medical Info |         │
     │ Emergency Contact | Documents)                                                      │
     │   - Summary cards: Total Patients, Active Patients, Recent Registrations (last 30   │
     │ days)                                                                               │
     │   - Entity dropdown config: search by first_name, last_name, mrn, phone             │
     │   - Export: config = PATIENT_CONFIG                                                 │
     │ 2. app/services/patient_service.py (Already EXISTS - extend it)                     │
     │   - Verify inheritance from UniversalEntityService                                  │
     │   - Constructor: super().__init__('patients', Patient)                              │
     │   - Implement _add_virtual_calculations(): age calculation, total visits,           │
     │ outstanding balance                                                                 │
     │   - Optional custom renderer: get_patient_visit_history() with cache decorator      │
     │                                                                                     │
     │ Files to MODIFY:                                                                    │
     │                                                                                     │
     │ 3. app/config/entity_registry.py                                                    │
     │   - Add to ENTITY_REGISTRY:                                                         │
     │ "patients": EntityRegistration(                                                     │
     │     category=EntityCategory.MASTER,                                                 │
     │     module="app.config.modules.patient_config",                                     │
     │     service_class="app.services.patient_service.PatientService",                    │
     │     model_class="app.models.master.Patient"                                         │
     │ )                                                                                   │
     │ 4. app/engine/universal_config_cache.py (Line ~465)                                 │
     │   - Add 'patients' to common_entities list                                          │
     │ 5. app/api/routes/universal_api.py                                                  │
     │   - Add search_patients() function (search by first_name, last_name, mrn, phone)    │
     │   - Handle JSONB field search: Patient.contact_info['phone'].astext.ilike(pattern)  │
     │   - Update entity_search() routing                                                  │
     │   - Return format: patient_name (computed) as value, include mrn and patient_id     │
     │                                                                                     │
     │ ---                                                                                 │
     │ Engine Modifications Requiring Permission                                           │
     │                                                                                     │
     │ NONE REQUIRED - Universal Engine Already Supports Everything                        │
     │                                                                                     │
     │ The existing Universal Engine components already handle:                            │
     │ - ✅ Virtual JSONB field mapping (virtual_field_transformer.py)                      │
     │ - ✅ Entity dropdown search (universal_entity_search_service.py)                     │
     │ - ✅ Categorized filters (categorized_filter_processor.py)                           │
     │ - ✅ Summary cards with hidden card pattern (universal_entity_service.py)            │
     │ - ✅ Tabbed layouts (data_assembler.py)                                              │
     │ - ✅ Relationship loading (universal_entity_service.py)                              │
     │                                                                                     │
     │ NO engine modifications needed - purely configuration and service implementation.   │
     │                                                                                     │
     │ ---                                                                                 │
     │ Summary of Objects Created/Modified                                                 │
     │                                                                                     │
     │ CREATED (9 files):                                                                  │
     │                                                                                     │
     │ 1. app/config/modules/medicine_config.py ⭐ NEW                                      │
     │ 2. app/services/medicine_service.py ⭐ NEW                                           │
     │ 3. app/config/modules/package_config.py ⭐ NEW (or replace existing)                 │
     │ 4. app/config/modules/patient_config.py ⭐ NEW                                       │
     │                                                                                     │
     │ MODIFIED (5 files):                                                                 │
     │                                                                                     │
     │ 5. app/services/package_service.py - Extend to inherit from UniversalEntityService  │
     │ 6. app/services/patient_service.py - Extend to inherit from UniversalEntityService  │
     │ 7. app/config/entity_registry.py - Add 3 entity registrations                       │
     │ 8. app/engine/universal_config_cache.py - Add 3 entities to preload list            │
     │ 9. app/api/routes/universal_api.py - Add 3 search functions + routing               │
     │                                                                                     │
     │ NOT MODIFIED:                                                                       │
     │                                                                                     │
     │ - ❌ No changes to app/engine/* core components                                      │
     │ - ❌ No changes to universal_views.py (routes auto-register)                         │
     │ - ❌ No changes to data models (already exist)                                       │
     │                                                                                     │
     │ ---                                                                                 │
     │ Implementation Order                                                                │
     │                                                                                     │
     │ 1. Medicines (4-6 hours) - Simplest, no JSONB complexity                            │
     │ 2. Packages (3-4 hours) - Moderate, leverage existing service                       │
     │ 3. Patients (6-8 hours) - Most complex, JSONB virtual fields                        │
     │                                                                                     │
     │ Total Effort: ~13-18 hours for all three entities                                   │
     │                                                                                     │
     │ ---                                                                                 │
     │ Post-Implementation Testing                                                         │
     │                                                                                     │
     │ For each entity, verify:                                                            │
     │ 1. ✅ Startup logs show preload message                                              │
     │ 2. ✅ /universal/{entity}/list loads without 302 redirect                            │
     │ 3. ✅ Filters work (especially entity dropdowns)                                     │
     │ 4. ✅ Create/Edit forms render correctly                                             │
     │ 5. ✅ Detail view shows all fields and custom renderers                              │
     │ 6. ✅ Search API endpoint returns correct format (NAME as value)                     │
     │ 7. ✅ Soft delete works properly  


     > There is 4th entity called package family.  Which is supposed to combine individual packages , services, medicines, products, all together.  There is     
        no billing at package family level but it is an aggregator with bill of material and services.  This is a future feature scope. But if we need to add       
        any element in existing entities of packages and medicines, let us just review and keep the hooks.  Can you analyse this?
