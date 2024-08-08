PYTHON=python3
PIP=pip3
PIPFLAGS=--upgrade
PYLINTFLAGS=
NPM=npm
NPMFLAGS=--no-save

.PHONY: test
test:
	$(PYTHON) -m unittest

.PHONY: type
type:
	mypy flatdir

.PHONY: lint
lint:
	pylint $(PYLINTFLAGS) flatdir

.PHONY: check
check: type test lint

.PHONY: deps
deps:
	$(PIP) install $(PIPFLAGS) --requirement requirements.txt

.PHONY: deps-dev
deps-dev:
	$(PIP) install $(PIPFLAGS) --requirement requirements-dev.txt

FONTSMODULE=node_modules/@fontsource/noto-sans
FONTSRESOURCE=flatdir/res/fonts
.PHONY: fonts
fonts:
	@# Work around npm 7 update modifying package.json (see https://github.com/npm/cli/issues/3044)
	$(NPM) install $(NPMFLAGS)
	mkdir --parents $(FONTSRESOURCE)/files
	cp $(FONTSMODULE)/400.css $(FONTSMODULE)/600.css $(FONTSRESOURCE)/
	cp $(FONTSMODULE)/files/noto-sans-*-400-normal.woff2 \
	    $(FONTSMODULE)/files/noto-sans-all-400-normal.woff \
	    $(FONTSMODULE)/files/noto-sans-*-600-normal.woff2 \
	    $(FONTSMODULE)/files/noto-sans-all-600-normal.woff $(FONTSRESOURCE)/files/

.PHONY: clean
clean:
	rm --recursive --force $$(find . -name __pycache__) .mypy_cache node_modules
