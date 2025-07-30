.PHONY: test clean

# Default target
test: setup-venv install-test-deps run-tests

# Check if we're in a virtual environment and create one if not
setup-venv:
	@echo "Checking virtual environment..."
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "No virtual environment detected. Creating one..."; \
		python3 -m venv venv; \
		echo "Virtual environment created. Please activate it with: source venv/bin/activate"; \
		echo "Then run 'make test' again."; \
		exit 1; \
	else \
		echo "Virtual environment detected: $$VIRTUAL_ENV"; \
	fi

# Install test requirements
install-test-deps:
	@echo "Installing test requirements..."
	@pip install -r test_requirements.txt

# Run the tests
run-tests:
	@echo "Running tests..."
	@python run_tests.py

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