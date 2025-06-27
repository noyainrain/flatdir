PYTHON=python3
PYTHONFLAGS=-W error
PIP=pip3
PIPFLAGS=--upgrade
PYLINTFLAGS=
NPM=npm
NPMFLAGS=--no-package-lock

.PHONY: test
test:
	$(PYTHON) $(PYTHONFLAGS) -m unittest

.PHONY: type
type:
	mypy

.PHONY: lint
lint:
	pylint $(PYLINTFLAGS) flatdir

.PHONY: check
check: type test lint

.PHONY: dependencies
dependencies:
	$(PIP) install $(PIPFLAGS) --requirement=requirements.txt

.PHONY: dependencies-dev
dependencies-dev:
	$(PIP) install $(PIPFLAGS) --requirement=requirements-dev.txt

.PHONY: fonts
fonts:
	@# Node.js >= 18.19 is required
	$(NPM) update $(NPMFLAGS)

.PHONY: clean
clean:
	rm -rf $$(find . -name __pycache__) .mypy_cache node_modules
