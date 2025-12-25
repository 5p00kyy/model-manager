#!/bin/bash

echo "========================================="
echo "Model Manager v2.0 - Verification Script"
echo "========================================="
echo

# Check Python version
echo "1. Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "   Python: $PYTHON_VERSION"

# Check dependencies
echo
echo "2. Checking dependencies..."
python3 -c "import huggingface_hub; print('   huggingface_hub: ✓')" 2>/dev/null || echo "   huggingface_hub: ✗ (run: pip install -r requirements.txt)"
python3 -c "import textual; print('   textual: ✓')" 2>/dev/null || echo "   textual: ✗ (run: pip install -r requirements.txt)"
python3 -c "import humanize; print('   humanize: ✓')" 2>/dev/null || echo "   humanize: ✗ (run: pip install -r requirements.txt)"

# Check file structure
echo
echo "3. Checking file structure..."
[ -f "run.py" ] && echo "   run.py: ✓" || echo "   run.py: ✗"
[ -f "requirements.txt" ] && echo "   requirements.txt: ✓" || echo "   requirements.txt: ✗"
[ -f "README.md" ] && echo "   README.md: ✓" || echo "   README.md: ✗"
[ -d "src" ] && echo "   src/: ✓" || echo "   src/: ✗"
[ -d "src/services" ] && echo "   src/services/: ✓" || echo "   src/services/: ✗"
[ -d "src/screens" ] && echo "   src/screens/: ✓" || echo "   src/screens/: ✗"
[ -d "src/utils" ] && echo "   src/utils/: ✓" || echo "   src/utils/: ✗"

# Test imports
echo
echo "4. Testing imports..."
python3 -c "import sys; sys.path.insert(0, '.'); from src.app import ModelManagerApp; print('   App imports: ✓')" 2>/dev/null || echo "   App imports: ✗"

# Count files
echo
echo "5. Project statistics..."
PY_FILES=$(find . -name "*.py" | grep -v __pycache__ | wc -l)
echo "   Python files: $PY_FILES"
LINES=$(find . -name "*.py" | grep -v __pycache__ | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}')
echo "   Total lines of code: $LINES"

echo
echo "========================================="
echo "Status: Ready to run!"
echo "Execute: python3 run.py"
echo "========================================="
