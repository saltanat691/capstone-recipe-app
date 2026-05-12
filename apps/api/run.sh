#!/bin/bash

# Run script for Recipe AI System API

echo "Starting Recipe AI System API..."
echo "Server will be available at: http://localhost:4000"
echo "API Documentation: http://localhost:4000/docs"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found."
    echo "Please create one with: python -m venv venv"
    echo "Then activate it and install dependencies."
    exit 1
fi

# Activate virtual environment and run
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload