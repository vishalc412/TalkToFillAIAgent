#!/bin/bash

# Test runner script for AI Voice Form Filling Agent

echo "=================================="
echo "Running Tests"
echo "=================================="

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
fi

# Run tests with coverage
echo "\n📊 Running tests with coverage...\n"
pytest tests/ \
    --cov=src \
    --cov-report=html \
    --cov-report=term-missing \
    -v

# Check exit code
if [ $? -eq 0 ]; then
    echo "\n✅ All tests passed!"
    echo "\n📄 Coverage report generated in htmlcov/index.html"
else
    echo "\n❌ Some tests failed!"
    exit 1
fi

# Run specific test categories (optional)
echo "\n=================================="
echo "Test Categories Available:"
echo "=================================="
echo "• pytest -m unit        - Unit tests only"
echo "• pytest -m integration - Integration tests only"
echo "• pytest -m api         - API tests only"
echo "• pytest tests/test_models.py -v - Specific test file"
