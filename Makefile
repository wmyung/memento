.PHONY: install test clean

# Install for development (symlinks into PATH)
install:
	ln -sf $(PWD)/memento ~/.local/bin/memento
	ln -sf $(PWD)/sync ~/.local/bin/memento-sync
	@echo "✅ Installed. Run: memento init"

# Pip install
pip-install:
	pip install -e .

# Test basic functionality
test:
	memento init
	memento remember "test fact" --keywords "test"
	memento recall "test"
	memento status

# Clean up __pycache__
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Package for PyPI
dist:
	python3 -m build
