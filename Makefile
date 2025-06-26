PYTHON=python3
PYTHONFLAGS=-W error
PIP=pip3
PIPFLAGS=--upgrade
PYLINTFLAGS=
NPM=npm
NPMFLAGS=--no-save

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
	@# Work around npm 7 update modifying package.json (see https://github.com/npm/cli/issues/3044)
	$(NPM) install $(NPMFLAGS)
	# OQ should we delete this before update? to make sure old files get deleted correctly?
	# hhmmmm...
	# TODO this also applies to the update process of the flatdir data/web directory... hm...

.PHONY: clean
clean:
	rm -rf $$(find . -name __pycache__) .mypy_cache node_modules
