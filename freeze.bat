@echo off
echo Setting up virtual environment ...
python -m venv venv

echo Installing requirements ...
.\venv\Scripts\pip install -r requirements.txt cx_Freeze

echo Building binaries ...
.\venv\Scripts\cxfreeze -c run_seekers.py --target-dir dist/seekers --include-files config.ini
.\venv\Scripts\cxfreeze -c run_client.py --target-dir dist/client

echo Compress artifacts ...
for /d %%a in (dist\*) do (powershell Compress-Archive ".\%%a\*" "%%~na-windows.zip")
echo Finished!