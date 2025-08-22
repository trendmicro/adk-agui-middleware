#!/bin/bash

# ADK AGUI Middleware - Code Quality Check Script
# This script runs all code quality checks in the correct order

set -e  # Exit on any error

echo "🚀 Starting ADK AGUI Middleware code quality checks..."
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print step headers
print_step() {
    echo -e "\n${BLUE}📋 Step $1: $2${NC}"
    echo "----------------------------------------"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Step 1: Format code with ruff
print_step "1" "Code Formatting (ruff format)"
if uv run ruff format src/; then
    print_success "Code formatting completed"
else
    print_error "Code formatting failed"
    exit 1
fi

# Step 2: Lint and auto-fix with ruff
print_step "2" "Linting and Auto-fix (ruff check --fix)"
if uv run ruff check --fix src/; then
    print_success "Linting and auto-fix completed"
else
    print_error "Linting failed"
    exit 1
fi

# Step 3: Type checking with mypy
print_step "3" "Type Checking (mypy)"
if uv run mypy src/ --strict --show-error-codes; then
    print_success "Type checking passed"
else
    print_error "Type checking failed"
    exit 1
fi

# Step 4: Security analysis with bandit
print_step "4" "Security Analysis (bandit)"
if uv run bandit -r src/adk_agui_middleware/ -f json -o bandit-report.json --exclude=*/.venv/*,*/venv/*,*/env/*,*/.env/*; then
    print_success "Security analysis completed"
    echo "📊 Security report saved to: bandit-report.json"
    # Also run bandit with console output for immediate feedback
    echo "🔍 Running bandit with console output..."
    uv run bandit -r src/adk_agui_middleware/ --severity-level medium --exclude=*/.venv/*,*/venv/*,*/env/*,*/.env/* || true
else
    print_warning "Security analysis completed with findings"
    echo "📊 Security report saved to: bandit-report.json"
    # Show console output even if there are findings
    echo "🔍 Running bandit with console output..."
    uv run bandit -r src/adk_agui_middleware/ --severity-level medium --exclude=*/.venv/*,*/venv/*,*/env/*,*/.env/* || true
fi

# Step 5: Run unit tests
print_step "5" "Unit Tests"
export PYTHONPATH=$PWD/src
if uv run python -m unittest discover -s tests -p "test_*.py" -v; then
    print_success "All tests passed"
else
    print_error "Some tests failed"
    exit 1
fi

# Step 6: Test coverage
print_step "6" "Test Coverage"
if uv run coverage run --source=src -m unittest discover -s tests -p "test_*.py" -v; then
    uv run coverage report --show-missing
    uv run coverage html
    print_success "Coverage analysis completed"
    echo "📊 Coverage report saved to: htmlcov/index.html"
else
    print_error "Coverage analysis failed"
    exit 1
fi

# Step 7: Build package
print_step "7" "Package Build Test"
if uv build; then
    print_success "Package build successful"
else
    print_error "Package build failed"
    exit 1
fi

# Step 8: Import test
print_step "8" "Import Test"
if PYTHONPATH=$PWD/src uv run python -c "import adk_agui_middleware; print('✅ Package imports successfully')"; then
    print_success "Package import test passed"
else
    print_error "Package import test failed"
    exit 1
fi

# Final summary
echo -e "\n${GREEN}🎉 All checks completed successfully!${NC}"
echo "=================================================="
echo "📊 Reports generated:"
echo "  • Security: bandit-report.json"
echo "  • Coverage: htmlcov/index.html"
echo "  • Package: dist/"
echo ""
echo "🚀 Your code is ready for commit/release!"