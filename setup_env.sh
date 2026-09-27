#!/bin/bash
echo "Creating Python Virtual Environment (venv)..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Environment setup complete!"
