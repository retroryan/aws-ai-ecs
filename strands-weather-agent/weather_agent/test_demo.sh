#!/bin/bash

# Test script to run the demo with proper PYTHONPATH
# Run from weather_agent directory

echo "Running Weather Agent Demo..."
echo "============================"

# Set PYTHONPATH to include parent directory
export PYTHONPATH="$(dirname $(pwd)):$PYTHONPATH"

# Run the demo
python main.py --demo