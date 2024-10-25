.DEFAULT_GOAL := tests

package = tombot.py
tests = test_tombot.py

.PHONY: tests
tests:
	@python3.12 -m unittest $(tests)

.PHONY: format
format:
	ruff format $(package) $(tests)

.PHONY: lint
lint:
	ruff check --output-format pylint $(package) $(tests)
	pyright $(package)
