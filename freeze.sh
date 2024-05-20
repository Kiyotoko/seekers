#!/bin/bash
echo "Setting up virtual environment ..."
python -m venv 

echo "Install requirements ..."
venv/bin/pip install -r requirements.txt
venv/bin/pip install cx_Freeze

echo "Building binaries ..."
venv/bin/cxfreeze -c run_seekers.py --target-dir dist/seekers --include-files config.ini
venv/bin/cxfreeze -c run_client.py --target-dir dist/client

echo "Compress artifacts ..."
zip client-linux.zip dist/client
zip seekers-linux.zip dist/seekers
echo "Finished!"