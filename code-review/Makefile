.PHONY: test clean

VENV_ACTIVATE := venv/bin/activate

# Default target
test: setup-venv install-test-deps run-tests

# Check if we're in a virtual environment and create one if not
setup-venv:
	@echo "Checking virtual environment..."
	@if [ ! -e "$(VENV_ACTIVATE)" ]; then \
		echo "No virtual environment detected. Creating one..."; \
		python3 -m venv venv; \
		echo "Virtual environment created"; \
	else \
		echo "Virtual environment detected: "$(VENV_ACTIVATE)""; \
	fi

# Install test requirements
install-test-deps:
	@echo "Installing test requirements..."
	@. "$(VENV_ACTIVATE)" && pip install -r test_requirements.txt

# Run the tests
run-tests:
	@echo "Running tests..."
	@. "$(VENV_ACTIVATE)" && python run_tests.py

# Clean up generated files
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete."

# Help target
help:
	@echo "Available targets:"
	@echo "  test        - Setup virtual environment, install dependencies, and run tests"
	@echo "  setup-venv  - Check/create virtual environment"
	@echo "  install-test-deps - Install test requirements"
	@echo "  run-tests   - Run the test suite"
	@echo "  clean       - Remove Python cache files"
	@echo "  help        - Show this help message"
