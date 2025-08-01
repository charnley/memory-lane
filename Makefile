.PHONY: help init test

help:
	@echo "Commands:"
	@echo "  init  - Creates a virtual environment and installs dependencies."
	@echo "  test  - Runs the test suite."

init:
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	@echo "Installing dependencies..."
	@uv pip install -e ".[test]"

test:
	@echo "Running tests..."
	@.venv/bin/pytest

