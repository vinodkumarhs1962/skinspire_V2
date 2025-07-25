skinspire_v2/
├── .env
├── .flaskenv
├── .flask_env_type
├── activate.bat
├── activate_env.bat
├── app/
│   ├── api/
│   │   ├── desktop.ini
│   │   ├── routes/
│   │   │   ├── admin.py
│   │   │   ├── approval.py
│   │   │   ├── auth.py.bak
│   │   │   ├── desktop.ini
│   │   │   ├── gl.py
│   │   │   ├── inventory.py
│   │   │   ├── patient.py
│   │   │   ├── supplier.py
│   │   │   ├── verification.py
│   │   │   ├── __init__.py
│   │   ├── __init__.py
│   ├── config/
│   │   ├── db_config.py
│   │   ├── desktop.ini
│   │   ├── env_setup.py
│   │   ├── logo_logging.py
│   │   ├── settings.py
│   │   ├── __init__.py
│   ├── core/
│   │   ├── db_operations/
│   │   │   ├── backup.py
│   │   │   ├── copy.py
│   │   │   ├── Database Core Modules README.md
│   │   │   ├── maintenance.py
│   │   │   ├── migration.py
│   │   │   ├── restore.py
│   │   │   ├── schema_sync 08.04.py
│   │   │   ├── schema_sync.py
│   │   │   ├── triggers.py
│   │   │   ├── utils.py
│   │   │   ├── __init__.py
│   │   ├── environment.py
│   │   ├── __init__.py
│   ├── database/
│   │   ├── context.py
│   │   ├── core_trigger_functions copy.sql
│   │   ├── desktop.ini
│   │   ├── functions copy 2.sql
│   │   ├── functions copy latest.sql
│   │   ├── functions copy.sql
│   │   ├── manager.py
│   │   ├── migrations/
│   │   │   ├── helpers.py
│   │   ├── triggers/
│   │   │   ├── core_trigger_functions.sql
│   │   │   ├── functions.sql
│   │   ├── __init__.py
│   ├── desktop.ini
│   ├── forms/
│   │   ├── auth_forms 03.04.py
│   │   ├── auth_forms.py
│   │   ├── billing_forms.py
│   │   ├── gl_forms.py
│   │   ├── inventory_forms.py
│   │   ├── staff_forms.py
│   │   ├── supplier_forms.py
│   │   ├── verification_forms.py
│   │   ├── __init__.py
│   ├── models/
│   │   ├── base.py
│   │   ├── business.py
│   │   ├── config.py
│   │   ├── desktop.ini
│   │   ├── master copy.py
│   │   ├── master.py
│   │   ├── test_migration_model.py
│   │   ├── transaction copy.py
│   │   ├── transaction.py
│   │   ├── __init__.py
│   ├── security/
│   │   ├── audit/
│   │   │   ├── audit_logger.py
│   │   │   ├── desktop.ini
│   │   │   ├── error_tracker.py
│   │   │   ├── __init__.py
│   │   ├── authentication/
│   │   │   ├── auth_manager.py
│   │   │   ├── desktop.ini
│   │   │   ├── password_policy.py
│   │   │   ├── session_manager.py
│   │   │   ├── __init__.py
│   │   ├── authorization/
│   │   │   ├── decorators.py
│   │   │   ├── desktop.ini
│   │   │   ├── permission_validator.py
│   │   │   ├── rbac_manager.py
│   │   │   ├── __init__.py
│   │   ├── bridge.py
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── desktop.ini
│   │   │   ├── functions.sql
│   │   │   ├── migrations/
│   │   │   ├── __init__.py
│   │   ├── desktop.ini
│   │   ├── encryption/
│   │   │   ├── desktop.ini
│   │   │   ├── field_encryption.py
│   │   │   ├── hospital_encryption.py
│   │   │   ├── model_encryption.py
│   │   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── routes/
│   │   │   ├── audit.py
│   │   │   ├── auth copy.py
│   │   │   ├── auth.py
│   │   │   ├── desktop.ini
│   │   │   ├── rbac.py
│   │   │   ├── security_management.py
│   │   │   ├── __init__.py
│   │   ├── utils/
│   │   │   ├── auth_utils.py
│   │   ├── verification_middleware.py
│   │   ├── __init__.py
│   ├── services/
│   │   ├── appointment_service.py
│   │   ├── approval_service.py
│   │   ├── billing_service.py
│   │   ├── database_service.py
│   │   ├── employee_id_service.py
│   │   ├── forgot_password_service.py
│   │   ├── gl_service.py
│   │   ├── hospital_logo_service.py
│   │   ├── hospital_settings_service.py
│   │   ├── inventory_service.py
│   │   ├── menu_service.py
│   │   ├── patient_service.py
│   │   ├── profile_service.py
│   │   ├── supplier_service.py
│   │   ├── user_management.py
│   │   ├── user_service.py
│   │   ├── verification_service.py
│   ├── static/
│   │   ├── css/
│   │   │   ├── components/
│   │   │   │   ├── buttons.css
│   │   │   │   ├── cards.css
│   │   │   │   ├── forms.css
│   │   │   │   ├── navigation.css
│   │   │   │   ├── tables.css
│   │   │   ├── src/
│   │   │   │   ├── tailwind.css
│   │   │   ├── tailwind.css
│   │   ├── images/
│   │   │   ├── icons/
│   │   │   ├── logo.svg
│   │   ├── js/
│   │   │   ├── common/
│   │   │   │   ├── ajax-helpers.js
│   │   │   │   ├── date-helpers.js
│   │   │   │   ├── utils.js
│   │   │   │   ├── validation.js
│   │   │   ├── components/
│   │   │   │   ├── batch_selector.js
│   │   │   │   ├── datepicker.js
│   │   │   │   ├── modal.js
│   │   │   │   ├── notifications.js
│   │   │   │   ├── payment_form.js
│   │   │   │   ├── stock_movement.js
│   │   │   │   ├── tables.js
│   │   │   ├── pages/
│   │   │   │   ├── appointment.js
│   │   │   │   ├── batch_selector.js
│   │   │   │   ├── consultation.js
│   │   │   │   ├── gl.js
│   │   │   │   ├── inventory.js
│   │   │   │   ├── invoice.js
│   │   │   │   ├── notifications.js
│   │   │   │   ├── payment_form.js
│   │   │   │   ├── supplier.js
│   │   ├── uploads/
│   │   │   ├── hospital_logos/
│   │   │   │   ├── 4ef72e18-e65d-4766-b9eb-0308c42485ca/
│   │   │   │   │   ├── icon_3da15aa2-4a2f-4ace-901b-d4d89d1ff66f.jpg
│   │   │   │   │   ├── large_3da15aa2-4a2f-4ace-901b-d4d89d1ff66f.jpg
│   │   │   │   │   ├── medium_3da15aa2-4a2f-4ace-901b-d4d89d1ff66f.jpg
│   │   │   │   │   ├── original_3da15aa2-4a2f-4ace-901b-d4d89d1ff66f.jpg
│   │   │   │   │   ├── small_3da15aa2-4a2f-4ace-901b-d4d89d1ff66f.jpg
│   │   │   │   ├── 98131652-293b-405b-a5e2-a301244efd0a/
│   │   │   │   │   ├── icon_772c1f6e-505e-4033-9b8b-cafe23cbdceb.jpeg
│   │   │   │   │   ├── large_772c1f6e-505e-4033-9b8b-cafe23cbdceb.jpeg
│   │   │   │   │   ├── medium_772c1f6e-505e-4033-9b8b-cafe23cbdceb.jpeg
│   │   │   │   │   ├── original_772c1f6e-505e-4033-9b8b-cafe23cbdceb.jpeg
│   │   │   │   │   ├── small_772c1f6e-505e-4033-9b8b-cafe23cbdceb.jpeg
│   │   │   │   ├── d559f1ea-a1d2-4451-b1af-143d0fe18c82/
│   │   │   │   │   ├── icon_7076cbc3-14d7-46c0-80fb-c7b93c1610d1.png
│   │   │   │   │   ├── large_7076cbc3-14d7-46c0-80fb-c7b93c1610d1.png
│   │   │   │   │   ├── medium_7076cbc3-14d7-46c0-80fb-c7b93c1610d1.png
│   │   │   │   │   ├── original_7076cbc3-14d7-46c0-80fb-c7b93c1610d1.png
│   │   │   │   │   ├── small_7076cbc3-14d7-46c0-80fb-c7b93c1610d1.png
│   │   │   │   ├── {hospital_id}/
│   ├── templates/
│   │   ├── admin/
│   │   │   ├── hospital_admin_dashboard.html
│   │   │   ├── hospital_settings copy.html
│   │   │   ├── hospital_settings.html
│   │   │   ├── system_admin_dashboard.html
│   │   │   ├── users.html
│   │   ├── auth/
│   │   │   ├── employee_id_settings.html
│   │   │   ├── forgot_password.html
│   │   │   ├── login copy.html
│   │   │   ├── login.html
│   │   │   ├── register copy.html
│   │   │   ├── register.html
│   │   │   ├── register_enhanced.html
│   │   │   ├── reset_password.html
│   │   │   ├── settings.html
│   │   │   ├── staff_approval_admin.html
│   │   │   ├── staff_approval_detail.html
│   │   │   ├── staff_approval_request.htm
│   │   │   ├── staff_approval_request.html
│   │   │   ├── staff_approval_status.html
│   │   │   ├── staff_detail.html
│   │   │   ├── staff_management.html
│   │   │   ├── verification_status.html
│   │   │   ├── verify_email.html
│   │   │   ├── verify_phone.html
│   │   ├── base.html
│   │   ├── billing/
│   │   │   ├── create_invoice.html
│   │   │   ├── invoice_list.html
│   │   │   ├── payment_form.html
│   │   │   ├── payment_history.html
│   │   │   ├── print_invoice.html
│   │   │   ├── view_invoice.html
│   │   ├── components/
│   │   │   ├── forms/
│   │   │   ├── modals/
│   │   │   ├── navigation/
│   │   │   │   ├── menu._old.html
│   │   │   ├── navigation.html
│   │   │   ├── sidebar.html
│   │   │   ├── tables/
│   │   ├── dashboard/
│   │   │   ├── index copy.html
│   │   │   ├── index.html
│   │   ├── errors/
│   │   │   ├── 404.html
│   │   │   ├── 500.html
│   │   ├── gl/
│   │   │   ├── account_reconciliation.html
│   │   │   ├── balance_sheet.html
│   │   │   ├── financial_reports.html
│   │   │   ├── gstr1.html
│   │   │   ├── gstr2a.html
│   │   │   ├── gstr3b.html
│   │   │   ├── gst_reports.html
│   │   │   ├── profit_loss.html
│   │   │   ├── transaction_detail.html
│   │   │   ├── transaction_list.html
│   │   │   ├── trial_balance.html
│   │   ├── inventory/
│   │   │   ├── adjustment_form.html
│   │   │   ├── batch_management.html
│   │   │   ├── consumption_report.html
│   │   │   ├── expiring_stock.html
│   │   │   ├── low_stock.html
│   │   │   ├── stock_list.html
│   │   │   ├── stock_movement.html
│   │   ├── layouts/
│   │   │   ├── base.html
│   │   │   ├── dashboard new.html
│   │   │   ├── dashboard.html
│   │   │   ├── full.html
│   │   │   ├── public.html
│   │   ├── pages/
│   │   │   ├── admin/
│   │   │   ├── auth/
│   │   │   │   ├── login.html
│   │   │   ├── doctor/
│   │   │   ├── finance/
│   │   │   ├── patient/
│   │   │   ├── pharmacy/
│   │   ├── supplier/
│   │   │   ├── create_purchase_order.html
│   │   │   ├── create_supplier_invoice.html
│   │   │   ├── payment_form.html
│   │   │   ├── payment_history.html
│   │   │   ├── pending_invoices.html
│   │   │   ├── purchase_order_list.html
│   │   │   ├── supplier_form.html
│   │   │   ├── supplier_invoice_list.html
│   │   │   ├── supplier_list.html
│   │   │   ├── supplier_view.html
│   │   │   ├── view_purchase_order.html
│   │   │   ├── view_supplier_invoice.html
│   │   ├── test/
│   │   │   ├── tailwind_test.html
│   │   ├── user_management/
│   │   │   ├── list.html
│   ├── utils/
│   │   ├── menu_utils 14.04.py
│   │   ├── menu_utils.py
│   │   ├── phone_utils.py
│   │   ├── verification_helpers.py
│   ├── views/
│   │   ├── admin.py
│   │   ├── admin_views.py
│   │   ├── auth_views 13.04.py
│   │   ├── auth_views.py
│   │   ├── billing_views.py
│   │   ├── doctor.py
│   │   ├── finance.py
│   │   ├── gl_views.py
│   │   ├── inventory_views.py
│   │   ├── patient.py
│   │   ├── pharmacy.py
│   │   ├── supplier_views.py
│   │   ├── test.py
│   │   ├── verification_views.py
│   │   ├── __init__.py
│   ├── __init__ 13.04.py
│   ├── __init__.py
├── apptemplatestest/
├── backups/
│   ├── dev_backup_20250408_154357.sql
│   ├── dev_backup_20250408_154413.sql
│   ├── dev_backup_20250410_224738.sql
│   ├── dev_backup_20250411_084713.sql
│   ├── test_20250410_225337_pre_copy.sql
│   ├── test_backup_20250410_225047.sql
├── db_manager
├── desktop.ini
├── Dev Database.session.sql
├── Dict
├── flask_cli.py
├── form_error.png
├── import
├── migrations/
│   ├── 20250411085022_68931bed_add_core_business_process_models.py
│   ├── alembic.ini
│   ├── env.py
│   ├── migration script.py
│   ├── README
│   ├── script.py.mako
│   ├── versions/
│   │   ├── 20250411085022_68931bed_add_core_business_process_models.py
│   │   ├── 20250411193212_289067f4_datetime_datatype_change_in_columns.py
│   │   ├── f46930f30666_merge_migration_heads.py
│   │   ├── __init__.py
├── misc/
│   ├── create_hospital_settings.py
│   ├── skinspire_dev_backup 05.04.sql
│   ├── skinspire_test_backup_before_core_test.sql
│   ├── test database.session.sql
│   ├── test_core_modules.py
│   ├── test_imports.py
│   ├── test_status.json
│   ├── test_tailwind.py
├── package-lock.json
├── package.json
├── path_config.json
├── postcss.config.js
├── Project_docs/
│   ├── Authentication/
│   │   ├── Authentication Docmentation.md
│   │   ├── Authentication system test documentation.md
│   │   ├── CSRF Protection Guide .md
│   │   ├── desktop.ini
│   │   ├── image.png
│   │   ├── Test Authentication validation moved to triggers.md
│   │   ├── test_authentication_lessons_learnt.md
│   ├── Core Business process Implementation/
│   │   ├── Core Business Processes Approach Document.md
│   │   ├── core services functionality implemented.md
│   │   ├── Data model for core Business.md
│   │   ├── Implementation summary and next steps 12.04.md
│   │   ├── Implementation summary and next steps 13.04.md
│   │   ├── Implementation summary and next steps 14.04.md
│   │   ├── Revised Core Business Processes Approach Document.md
│   ├── Database access strategy/
│   │   ├── Complete Implementation Plan for Database Service Integration.md
│   │   ├── Database access methods and roadmap.md
│   │   ├── Database Service Migration Checklist for Test Modules.md
│   │   ├── Database Service Migration Summary.md
│   │   ├── dev and test database strategy.md
│   │   ├── Developer Guide-Using database_service.py V2.md
│   │   ├── Developer Guide-Using database_service.py V3.md
│   │   ├── Developer Guide-Using database_service.py V4.md
│   │   ├── Developer Guide-Using database_service.py V5.md
│   │   ├── Developer Guide-Using database_service.py.md
│   │   ├── get_db_engine usage discovery.md
│   │   ├── migration guide for test framework.md
│   │   ├── new_chat_begin_text.md
│   │   ├── SQLAlchemy - session vs query.py
│   │   ├── SQLAlchemy Detached Entity Quick Reference Guide.md
│   │   ├── Technical Guide - Managing Database Environments in Flask Testing.md
│   ├── Database setup and testing/
│   │   ├── Database Migration Instructions.md
│   │   ├── Database opertions guide.md
│   │   ├── database-documentation.md
│   │   ├── databse trigger commands.md
│   │   ├── desktop.ini
│   │   ├── Implementation Plan for SkinSpire Database Management Enhancements.md
│   │   ├── Schema Management Guidelines for Developers.md
│   │   ├── SkinSpire Clinic HMS Database Management Guide v2.md
│   │   ├── SkinSpire Clinic HMS Database Management Guide.md
│   │   ├── SkinSpire Database Management System - Building Blocks and Connections.md
│   │   ├── Testing Plan for Enhanced Database Management Features.md
│   ├── desktop.ini
│   ├── encryption/
│   │   ├── 01_concept.md
│   │   ├── 02_implementation.md
│   │   ├── 03_models.md
│   │   ├── 04_testing.md
│   │   ├── 05_key_rotation.md
│   │   ├── 06_lessons.md
│   │   ├── desktop.ini
│   │   ├── index.md
│   │   ├── README.md
│   ├── Front end Design and Development/
│   │   ├── Database connection from UI - appoach and guidelines.md
│   │   ├── Front end Approach and Design.md
│   │   ├── Logo guidelines.md
│   │   ├── Role based menu system Developer guide.md
│   │   ├── Understanding the Architecture API vs Views.md
│   ├── Implementation Plan/
│   │   ├── Email SMS Integratipon.md
│   │   ├── Enhanced authentication Implementation.md
│   │   ├── Handwritten Prescription Capture Solution.md
│   │   ├── Phone Verification & Staff Approval Implementation.md
│   │   ├── Project Dependencies and Library Overview.md
│   │   ├── user Management & Authentication Implementation Plan.md
│   ├── index.md
│   ├── Linex_Redis_login.md
│   ├── MAster documents/
│   │   ├── Claude system understanding 13.01.2025.docx
│   │   ├── Consolidated Table strucrture doc.md
│   │   ├── Consolidated Table Structure 16.01.2025.csv
│   │   ├── Database Management Master Document.md
│   │   ├── DBMS - schema and data management strategy.md
│   │   ├── Hospital Management System Master document v 4.0 16.01.2025.docx
│   │   ├── Industry Alignment for Mid-Size Healthcare Facilities.md
│   │   ├── Master_project_structure_proposed.md
│   │   ├── Model-Driven Database Migration Strategy.md
│   │   ├── Project background and collaboration guidelines.md
│   │   ├── SkinSpire Clinic HMS Development Guidelines.md
│   │   ├── SkinSpire Clinic HMS Technical Development Guidelines.md
│   ├── project structure/
│   │   ├── Project structure 03.02.2025.md
│   │   ├── Project Structure 04.04.25.md
│   │   ├── project structure 09.04.25.md
│   │   ├── Project structure 10.04.25.md
│   │   ├── project structure 10.3.25.md
│   │   ├── project structure 13.03.2025.md
│   │   ├── project structure 19.3.25.md
│   │   ├── Project Structure 22.03.2025.md
│   │   ├── Project Structure 24.3.25.md
│   │   ├── Project structure 7.4.25.md
│   │   ├── project structure 8.3.25.md
│   │   ├── project structure consolidated 8.3.25.md
│   │   ├── project_structure 31-01.md
│   │   ├── project_structure_5.3.25.md
│   ├── project_status/
│   │   ├── 10.3.25/
│   │   │   ├── Autheentication enhancements.md
│   │   │   ├── end o end Authentication system tested.md
│   │   │   ├── front end development next steps proposed.md
│   │   ├── 16.3.25/
│   │   │   ├── unresolved session detach issue.md
│   │   ├── 24.3.25/
│   │   │   ├── summary v1.md
│   │   │   ├── summary v2.md
│   │   │   ├── summary v3.md
│   │   ├── 5.3.25/
│   │   │   ├── status_5.3.25.md
│   │   │   ├── user_management_dev_notes.md
│   │   ├── 6.3.25/
│   │   │   ├── Further implementation-plan.md
│   │   │   ├── trigger_issue analysis.md
│   │   ├── 6.4.25/
│   │   │   ├── 06.04.25.md
│   │   ├── 7.3.25/
│   │   │   ├── revised trigger strategy and solution.md
│   │   ├── 8.3.25/
│   │   │   ├── Frontend implementation.md
│   │   ├── 9.3.25/
│   │   │   ├── status 9.3 v 1.md
│   │   │   ├── status 9.3 v2.md
│   │   ├── desktop.ini
│   │   ├── status_1_2_25.md
│   ├── Project_summary_status_5.3.25.md
│   ├── README.md
│   ├── redis_setup_guide.md
│   ├── security/
│   │   ├── auth-testing-docs.md
│   │   ├── authentication/
│   │   │   ├── desktop.ini
│   │   │   ├── handover_notes.md
│   │   │   ├── test_plan.md
│   │   │   ├── test_status.md
│   │   ├── desktop.ini
│   │   ├── security_testing_plan
│   │   ├── sesson_management_token_handling.md
│   ├── testing/
│   │   ├── Comprehensive Testing Strategy and Implementation Guide for SkinSpire Clinic HMS.md
│   │   ├── test report 25.3.25.md
│   ├── User Authorization/
│   │   ├── password hash implementation.md
│   │   ├── SkinSpire CSRF Protection Implementation Documentation.md
│   │   ├── user-auth-documentation.md
│   │   ├── User_management_approach.md
│   ├── virtual_environment_setup/
│   │   ├── desktop.ini
│   │   ├── virtual_environment_manager_documentation.md
├── pyproject.toml
├── pytest.ini
├── python_path_diagnostic.py
├── raise
├── requirements.txt
├── reset_migrations.py
├── run.py
├── scripts/
│   ├── copy_test_to_dev.py
│   ├── create_database.py
│   ├── db/
│   │   ├── backup_manager.py
│   │   ├── copy_db.py
│   │   ├── db_connection_manager.py
│   │   ├── migration_manager.py
│   ├── db_inspector.py
│   ├── desktop.ini
│   ├── direct_migration.py
│   ├── enhanced_trigger_installer.py
│   ├── inspect_password_hash.py
│   ├── install_old.py
│   ├── install_triggers 24.3.py
│   ├── install_triggers copy latest.py
│   ├── install_triggers.py
│   ├── manage_db 08.04.py
│   ├── manage_db.py
│   ├── manage_db_standalone.py
│   ├── modify_app_env.py
│   ├── populate_test_data.py
│   ├── PSQL/
│   │   ├── desktop.ini
│   │   ├── Trigger verification.sql
│   ├── reset_database.py
│   ├── setup_db.bat
│   ├── setup_test_db.py
│   ├── switch_env.py
│   ├── test_db_core.py
│   ├── test_db_features.py
│   ├── test_db_service_with_test.py
│   ├── test_migration_strategy 08.04.py
│   ├── test_migration_strategy.py
│   ├── venv_manager.py
│   ├── verify_db_service.py
│   ├── verify_test_data.py
│   ├── verify_test_db.py
│   ├── verify_triggers.py
├── session_id
├── skinspire_dev_backup.sql
├── tailwind.config.js
├── tests/
│   ├── conftest.py
│   ├── test_api/
│   │   ├── test_auth_api.py
│   ├── test_database_triggers.py
│   ├── test_db_setup.py
│   ├── test_db_utils.py
│   ├── test_environment.py
│   ├── test_frontend/
│   │   ├── test_auth_ui.py
│   │   ├── test_responsive.py
│   ├── test_redis_connection.py
│   ├── test_security/
│   │   ├── test_authentication.py
│   │   ├── test_authorization.py
│   │   ├── test_auth_end_to_end.py
│   │   ├── test_auth_flow.py
│   │   ├── test_auth_system copy.py
│   │   ├── test_auth_system.py
│   │   ├── test_auth_ui.py
│   │   ├── test_auth_views.py
│   │   ├── test_encryption.py
│   │   ├── test_hospital_logo.py
│   │   ├── test_password_policy.py
│   │   ├── test_security_endpoints.py
│   │   ├── test_setup_verification.py
│   │   ├── test_triggers.py
│   │   ├── test_user_management.py
│   │   ├── verify_core.py
│   │   ├── __init__.py
│   ├── test_venv_manager.py
│   ├── __init__.py
├── utils/
│   ├── db_utils.py
├── verification_status.json
├── wsgi.py



.env:

# Environment Configuration
FLASK_ENV=development
DEBUG=True

# Database URLs
DEV_DATABASE_URL=postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_dev
TEST_DATABASE_URL=postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test
PROD_DATABASE_URL=postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_prod

# Redis Configuration
DEV_REDIS_URL=redis://localhost:6379/0
TEST_REDIS_URL=redis://localhost:6379/1

# Security
MASTER_ENCRYPTION_KEY=your-encryption-key-here

# Python Environment
PYTHONPATH=C:\Users\vinod\AppData\Local\Programs\skinspire-env\Scripts
VIRTUAL_ENV=C:\Users\vinod\AppData\Local\Programs\skinspire-env

# Gmail SMTP Settings
GMAIL_EMAIL=skinspireclinics@gmail.com
GMAIL_APP_PASSWORD=jdtz rsdi cwut pgbr

# Twilio WhatsApp Settings
TWILIO_ACCOUNT_SID=AC99d5e1a8757e767dac4695a4fdc538ee
TWILIO_AUTH_TOKEN=2f72d6e3f17650d8d383a211aef18432
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
# Twilio account recovery code 8TENDVVCQ81G9EWU3SSVFB9K

# Hospital Logo Settings
HOSPITAL_LOGO_UPLOAD_PATH=/uploads/hospital_logos/
HOSPITAL_LOGO_MAX_SIZE_MB=5
HOSPITAL_LOGO_ALLOWED_TYPES=png,jpg,jpeg,svg,webp


.flaskenv:

# skinspire_v2/.flaskenv
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=1
TEMPLATES_AUTO_RELOAD=True  


.flask_env_type:

dev


activate.bat:

@echo off

rem This file is UTF-8 encoded, so we need to update the current code page while executing it
for /f "tokens=2 delims=:." %%a in ('"%SystemRoot%\System32\chcp.com"') do (
    set _OLD_CODEPAGE=%%a
)
if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" 65001 > nul
)

set "VIRTUAL_ENV=C:\Users\vinod\AppData\Local\Programs\Skinspire Repository\skinspire_v2\skinspire_v2_env"

if not defined PROMPT set PROMPT=$P$G

if defined _OLD_VIRTUAL_PROMPT set PROMPT=%_OLD_VIRTUAL_PROMPT%
if defined _OLD_VIRTUAL_PYTHONHOME set PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%

set "_OLD_VIRTUAL_PROMPT=%PROMPT%"
set "PROMPT=(skinspire_v2_env) %PROMPT%"

if defined PYTHONHOME set _OLD_VIRTUAL_PYTHONHOME=%PYTHONHOME%
set PYTHONHOME=

if defined _OLD_VIRTUAL_PATH set PATH=%_OLD_VIRTUAL_PATH%
if not defined _OLD_VIRTUAL_PATH set _OLD_VIRTUAL_PATH=%PATH%

set "PATH=%VIRTUAL_ENV%\Scripts;%PATH%"
set "VIRTUAL_ENV_PROMPT=skinspire_v2_env"

:END
if defined _OLD_CODEPAGE (
    "%SystemRoot%\System32\chcp.com" %_OLD_CODEPAGE% > nul
    set _OLD_CODEPAGE=
)



activate_env.bat:

@echo off
SET VIRTUAL_ENV=C:\Users\vinod\AppData\Local\Programs\skinspire-env
SET PYTHON_HOME=%VIRTUAL_ENV%
SET PATH=%VIRTUAL_ENV%\Scripts;%PATH%
SET PYTHONPATH=%VIRTUAL_ENV%\Scripts

echo Virtual environment activated at %VIRTUAL_ENV%
echo Python path set to %VIRTUAL_ENV%\Scripts\python.exe

REM Verify Python location
where python

REM Display Python version
python -V


db_manager:




desktop.ini:

[