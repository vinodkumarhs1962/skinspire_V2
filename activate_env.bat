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