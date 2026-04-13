#!/bin/bash

set -e

VENV_DIR="venv"

echo "Installing system dependencies..."
sudo apt update
sudo apt install -y libcap-dev

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $VENV_DIR
else
    echo "Virtual environment already exists"
fi

echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
else
    echo "No requirements.txt found, skipping install"
fi

echo "Setup complete."
echo "Note: venv is active only if you ran: source venv.sh"