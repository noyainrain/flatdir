PYTHON=python3
PIP=pip3
PIPFLAGS=--upgrade

.PHONY: test
test:
	$(PYTHON) -m unittest

.PHONY: type
type:
	mypy flatdir

.PHONY: lint
lint:
	pylint flatdir

.PHONY: check
check: type test lint

.PHONY: deps
deps:
	$(PIP) install $(PIPFLAGS) --requirement requirements.txt

.PHONY: deps-dev
deps-dev:
	$(PIP) install $(PIPFLAGS) --requirement requirements-dev.txt

.PHONY: clean
clean:
	rm --recursive --force $$(find . -name __pycache__) .mypy_cache
