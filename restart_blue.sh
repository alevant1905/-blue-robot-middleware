#!/bin/bash

echo "========================================"
echo "Restarting Blue with Fresh Code"
echo "========================================"
echo ""

echo "Step 1: Clearing Python cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "  ✓ Done!"
echo ""

echo "Step 2: Verifying settings..."
python3 -c "import bluetools; s = bluetools._settings; print('  USE_STRICT_TOOL_FORCING:', s.USE_STRICT_TOOL_FORCING); print('  MAX_ITERATIONS:', s.MAX_ITERATIONS)"
echo ""

echo "Step 3: Starting Blue..."
echo ""
python3 run.py
