#!/bin/bash

FRONTEND_DIR="$(cd "$(dirname "$0")" && pwd)/frontend"

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo "Starting frontend dev server on port 4321..."
exec npm run dev
