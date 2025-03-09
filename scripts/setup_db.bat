REM working test 3.3.25
@echo off
setlocal enabledelayedexpansion

echo Starting SkinSpire test database setup...

REM Set environment variables
set FLASK_APP=wsgi.py
set FLASK_ENV=testing
set PYTHONPATH=%~dp0\..
set TEST_DATABASE_URL=postgresql://skinspire_admin:Skinspire123$@localhost:5432/skinspire_test

REM Activate virtual environment
call %USERPROFILE%\AppData\Local\Programs\skinspire-env\Scripts\activate.bat

REM Change to project root directory
cd %~dp0\..

echo.
echo Current Configuration:
echo -------------------
echo Environment: %FLASK_ENV%
echo Database: skinspire_test
echo.

REM Run the standalone database reset script
echo Resetting and initializing test database...
python scripts\reset_database.py
if %ERRORLEVEL% neq 0 goto error

echo.
echo Test database setup completed successfully!
echo You can now run scripts\populate_test_data.py to add test data.
goto end

:error
echo.
echo Error occurred during test database setup!
echo Please check the error messages above.
pause
exit /b 1

:end
echo.
echo Press any key to exit...
pause >nul
exit /b 0