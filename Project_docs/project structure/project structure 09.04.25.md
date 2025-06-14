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
│   │   │   ├── patient.py
│   │   │   ├── verification.py
│   │   │   ├── __init__.py
│   │   ├── __init__.py
│   ├── config/
│   │   ├── db_config.py
│   │   ├── desktop.ini
│   │   ├── env_setup.py
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
│   │   ├── verification_forms.py
│   │   ├── __init__.py
│   ├── models/
│   │   ├── base.py
│   │   ├── config.py
│   │   ├── desktop.ini
│   │   ├── master.py
│   │   ├── test_migration_model.py
│   │   ├── transaction - Copy latest.py
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
│   │   ├── approval_service 08.04.py
│   │   ├── approval_service.py
│   │   ├── database_service.py
│   │   ├── forgot_password_service.py
│   │   ├── hospital_settings_service.py
│   │   ├── inventory_service.py
│   │   ├── menu_service.py
│   │   ├── patient_service.py
│   │   ├── profile_service.py
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
│   │   │   │   ├── datepicker.js
│   │   │   │   ├── modal.js
│   │   │   │   ├── notifications.js
│   │   │   │   ├── tables.js
│   │   │   ├── pages/
│   │   │   │   ├── appointment.js
│   │   │   │   ├── consultation.js
│   │   │   │   ├── notifications.js
│   ├── templates/
│   │   ├── admin/
│   │   │   ├── hospital_admin_dashboard.html
│   │   │   ├── hospital_settings.html
│   │   │   ├── system_admin_dashboard.html
│   │   │   ├── users.html
│   │   ├── auth/
│   │   │   ├── forgot_password.html
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   ├── register_enhanced.html
│   │   │   ├── reset_password.html
│   │   │   ├── settings.html
│   │   │   ├── staff_approval_admin.html
│   │   │   ├── staff_approval_detail.html
│   │   │   ├── staff_approval_request.htm
│   │   │   ├── staff_approval_status.html
│   │   │   ├── verification_status.html
│   │   │   ├── verify_email.html
│   │   │   ├── verify_phone.html
│   │   ├── base.html
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
│   │   ├── layouts/
│   │   │   ├── base.html
│   │   │   ├── dashboard  07.04 step 3 working.html
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
│   │   ├── test/
│   │   │   ├── tailwind_test.html
│   │   ├── user_management/
│   │   │   ├── list.html
│   ├── utils/
│   │   ├── menu_utils.py
│   ├── views/
│   │   ├── admin.py
│   │   ├── admin_views.py
│   │   ├── auth_views 03.04.py
│   │   ├── auth_views 08.04.py
│   │   ├── auth_views.py
│   │   ├── doctor.py
│   │   ├── finance.py
│   │   ├── patient.py
│   │   ├── pharmacy.py
│   │   ├── test.py
│   │   ├── verification_views.py
│   │   ├── __init__.py
│   ├── __init__.py
├── apptemplatestest/
├── backups/
│   ├── dev_20250324_072719_pre_copy.sql
│   ├── dev_20250324_073000_pre_copy.sql
│   ├── dev_backup_20250325_111513.sql
│   ├── dev_backup_20250325_132642.sql
│   ├── dev_backup_20250325_134223.sql
│   ├── dev_backup_20250325_153143.sql
│   ├── dev_backup_20250325_153201.sql
│   ├── dev_backup_20250325_153204.sql
│   ├── dev_backup_20250325_154138.sql
│   ├── dev_backup_20250325_154155.sql
│   ├── dev_backup_20250325_181121.sql
│   ├── dev_backup_20250325_181137.sql
│   ├── dev_backup_20250325_181140.sql
│   ├── dev_backup_20250325_181142.sql
│   ├── dev_backup_20250325_184523.sql
│   ├── dev_backup_20250325_184539.sql
│   ├── dev_backup_20250325_184542.sql
│   ├── dev_backup_20250325_184544.sql
│   ├── dev_backup_20250404_104811.sql
│   ├── dev_backup_20250404_104827.sql
│   ├── dev_backup_20250404_104830.sql
│   ├── dev_backup_20250404_104831.sql
│   ├── dev_backup_20250404_190244.sql
│   ├── dev_backup_20250404_190312.sql
│   ├── dev_backup_20250404_190317.sql
│   ├── dev_backup_20250404_190319.sql
│   ├── dev_backup_20250404_193013.sql
│   ├── dev_backup_20250404_193041.sql
│   ├── dev_backup_20250404_193046.sql
│   ├── dev_backup_20250405_195102.sql
│   ├── dev_backup_20250405_202828.sql
│   ├── dev_backup_20250406_123045.sql
│   ├── dev_backup_20250406_125804.sql
│   ├── dev_backup_20250406_130856.sql
│   ├── dev_backup_20250408_100811.sql
│   ├── dev_backup_20250408_113041.sql
│   ├── dev_backup_20250408_115701.sql
│   ├── dev_backup_20250408_115710.sql
│   ├── dev_backup_20250408_124245.sql
│   ├── dev_backup_20250408_124249.sql
│   ├── dev_backup_20250408_141134.sql
│   ├── dev_backup_20250408_141149.sql
│   ├── dev_backup_20250408_142658.sql
│   ├── dev_backup_20250408_142726.sql
│   ├── dev_backup_20250408_154357.sql
│   ├── dev_backup_20250408_154413.sql
│   ├── dev_pre_restore_20250325_111519.sql
│   ├── dev_pre_restore_20250325_132647.sql
│   ├── dev_pre_restore_20250325_134229.sql
│   ├── dev_pre_restore_20250325_153149.sql
│   ├── dev_pre_restore_20250325_153208.sql
│   ├── dev_pre_restore_20250325_154144.sql
│   ├── dev_pre_restore_20250325_154157.sql
│   ├── dev_pre_restore_20250325_181126.sql
│   ├── dev_pre_restore_20250325_181144.sql
│   ├── dev_pre_restore_20250325_184529.sql
│   ├── dev_pre_restore_20250325_184545.sql
│   ├── dev_pre_restore_20250404_104816.sql
│   ├── dev_pre_restore_20250404_104833.sql
│   ├── dev_pre_restore_20250404_190254.sql
│   ├── dev_pre_restore_20250404_190322.sql
│   ├── dev_pre_restore_20250404_193023.sql
│   ├── dev_pre_restore_20250404_193048.sql
│   ├── dev_pre_restore_20250405_195155.sql
│   ├── dev_pre_restore_20250405_221237.sql
│   ├── test_20250325_132644_pre_copy.sql
│   ├── test_20250325_132646_pre_copy.sql
│   ├── test_20250325_134225_pre_copy.sql
│   ├── test_20250325_134227_pre_copy.sql
│   ├── test_20250325_153145_pre_copy.sql
│   ├── test_20250325_153147_pre_copy.sql
│   ├── test_20250325_154141_pre_copy.sql
│   ├── test_20250325_154143_pre_copy.sql
│   ├── test_20250325_181123_pre_copy.sql
│   ├── test_20250325_181124_pre_copy.sql
│   ├── test_20250325_184525_pre_copy.sql
│   ├── test_20250325_184527_pre_copy.sql
│   ├── test_20250404_104813_pre_copy.sql
│   ├── test_20250404_104815_pre_copy.sql
│   ├── test_20250404_190248_pre_copy.sql
│   ├── test_20250404_190251_pre_copy.sql
│   ├── test_20250404_193017_pre_copy.sql
│   ├── test_20250404_193020_pre_copy.sql
│   ├── test_backup_20250325_132639.sql
│   ├── test_backup_20250325_132642.sql
│   ├── test_backup_20250325_132650.sql
│   ├── test_backup_20250325_134221.sql
│   ├── test_backup_20250325_134224.sql
│   ├── test_backup_20250325_134231.sql
│   ├── test_backup_20250325_153140.sql
│   ├── test_backup_20250325_153144.sql
│   ├── test_backup_20250325_153152.sql
│   ├── test_backup_20250325_154136.sql
│   ├── test_backup_20250325_154139.sql
│   ├── test_backup_20250325_154147.sql
│   ├── test_backup_20250325_181118.sql
│   ├── test_backup_20250325_181121.sql
│   ├── test_backup_20250325_181129.sql
│   ├── test_backup_20250325_184521.sql
│   ├── test_backup_20250325_184524.sql
│   ├── test_backup_20250325_184531.sql
│   ├── test_backup_20250404_104808.sql
│   ├── test_backup_20250404_104812.sql
│   ├── test_backup_20250404_104819.sql
│   ├── test_backup_20250404_190239.sql
│   ├── test_backup_20250404_190246.sql
│   ├── test_backup_20250404_190258.sql
│   ├── test_backup_20250404_193004.sql
│   ├── test_backup_20250404_193015.sql
│   ├── test_backup_20250404_193027.sql
│   ├── test_backup_20250405_084805.sql
│   ├── test_pre_restore_20250325_132641.sql
│   ├── test_pre_restore_20250325_132649.sql
│   ├── test_pre_restore_20250325_132651.sql
│   ├── test_pre_restore_20250325_134222.sql
│   ├── test_pre_restore_20250325_134230.sql
│   ├── test_pre_restore_20250325_134233.sql
│   ├── test_pre_restore_20250325_153142.sql
│   ├── test_pre_restore_20250325_153150.sql
│   ├── test_pre_restore_20250325_153153.sql
│   ├── test_pre_restore_20250325_154137.sql
│   ├── test_pre_restore_20250325_154146.sql
│   ├── test_pre_restore_20250325_154148.sql
│   ├── test_pre_restore_20250325_181119.sql
│   ├── test_pre_restore_20250325_181128.sql
│   ├── test_pre_restore_20250325_181131.sql
│   ├── test_pre_restore_20250325_184522.sql
│   ├── test_pre_restore_20250325_184530.sql
│   ├── test_pre_restore_20250325_184533.sql
│   ├── test_pre_restore_20250404_104809.sql
│   ├── test_pre_restore_20250404_104818.sql
│   ├── test_pre_restore_20250404_104821.sql
│   ├── test_pre_restore_20250404_190242.sql
│   ├── test_pre_restore_20250404_190256.sql
│   ├── test_pre_restore_20250404_190301.sql
│   ├── test_pre_restore_20250404_193009.sql
│   ├── test_pre_restore_20250404_193026.sql
│   ├── test_pre_restore_20250404_193030.sql
│   ├── test_pre_restore_20250405_084810.sql
├── create_hospital_settings.py
├── db_manager
├── db_test_20250325_111510.log
├── db_test_20250325_132639.log
├── db_test_20250325_134220.log
├── db_test_20250325_152204.log
├── db_test_20250325_153140.log
├── db_test_20250325_154135.log
├── db_test_20250325_181117.log
├── db_test_20250325_184520.log
├── db_test_20250404_104807.log
├── db_test_20250404_190238.log
├── db_test_20250404_193001.log
├── db_test_20250405_084802.log
├── db_test_results_20250325_132658.json
├── db_test_results_20250325_134239.json
├── db_test_results_20250325_152216.json
├── db_test_results_20250325_153209.json
├── db_test_results_20250325_154158.json
├── db_test_results_20250325_181145.json
├── db_test_results_20250325_184547.json
├── db_test_results_20250404_104834.json
├── db_test_results_20250404_190324.json
├── db_test_results_20250404_193050.json
├── desktop.ini
├── Dev Database.session.sql
├── Dict
├── error_screenshot.png
├── flask_cli copy.py
├── flask_cli.py
├── form_error.png
├── import
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   ├── versions/
│   │   ├── 09618f531e9d_merge_migration_heads.py
│   │   ├── 20250407232451_718bd846_add_test_migration_table.py
│   │   ├── 20250407233316_c952d8cf_add_test_migration_table.py
│   │   ├── 20250408052941_1dceb176_add_test_migration_table.py
│   │   ├── 20250408054113_53d3152b_add_test_migration_table.py
│   │   ├── 20250408113043_92f2bf30_add_test_migration_table.py
│   │   ├── 20250408115704_8980b041_add_test_migration_table.py
│   │   ├── 20250408141137_6a84ea4e_add_test_migration_table.py
│   │   ├── 20250408142701_5ff7232a_add_test_migration_table.py
│   │   ├── 20250408154359_138838be_add_test_migration_table.py
│   │   ├── 303a0814650e_resolving_multiple_migration_branches.py
│   │   ├── d9027dae6a39_add_hospital_settings_table.py
│   │   ├── f799a5b76e41_merge_migration_heads.py
│   │   ├── __init__.py
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
│   │   ├── Understanding the Architecture API vs Views.md
│   ├── Implementation Plan/
│   │   ├── Email SMS Integratipon.md
│   │   ├── Enhanced authentication Implementation.md
│   │   ├── Phone Verification & Staff Approval Implementation.md
│   │   ├── user Management & Authentication Implementation Plan.md
│   ├── index.md
│   ├── Linex_Redis_login.md
│   ├── MAster documents/
│   │   ├── Claude system understanding 13.01.2025.docx
│   │   ├── Consolidated Table Structure 16.01.2025.csv
│   │   ├── Database Management Master Document.md
│   │   ├── DBMS - schema and data management strategy.md
│   │   ├── Hospital Management System Master document v 4.0 16.01.2025.docx
│   │   ├── Master_project_structure_proposed.md
│   │   ├── Model-Driven Database Migration Strategy.md
│   │   ├── Project background and collaboration guidelines.md
│   │   ├── SkinSpire Clinic HMS Development Guidelines.md
│   ├── project structure/
│   │   ├── Project structure 03.02.2025.md
│   │   ├── Project Structure 04.04.25.md
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
├── skinspire_dev_backup 05.04.sql
├── skinspire_dev_backup.sql
├── skinspire_test_backup_before_core_test.sql
├── tailwind.config.js
├── test database.session.sql
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
│   │   ├── test_password_policy.py
│   │   ├── test_security_endpoints.py
│   │   ├── test_setup_verification.py
│   │   ├── test_triggers.py
│   │   ├── test_user_management.py
│   │   ├── verify_core.py
│   │   ├── __init__.py
│   ├── test_venv_manager.py
│   ├── __init__.py
├── test_core_modules.py
├── test_imports.py
├── test_status.json
├── test_tailwind.py
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

<!-- # Twilio WhatsApp Settings
TWILIO_ACCOUNT_SID=AC99d5e1a8757e767dac4695a4fdc538ee
TWILIO_AUTH_TOKEN=2f72d6e3f17650d8d383a211aef18432
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
# Twilio account recovery code 8TENDVVCQ81G9EWU3SSVFB9K -->


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


