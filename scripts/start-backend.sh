#!/bin/bash

BACKEND_DIR="$(cd "$(dirname "$0")" && pwd)/backend"

cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Starting backend server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
