PYTHON=python3
PIP=pip3
PIPFLAGS=--upgrade
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
	pylint flatdir

.PHONY: check
check: type test lint

.PHONY: deps
deps:
	$(PIP) install $(PIPFLAGS) --requirement requirements.txt

.PHONY: deps-dev
deps-dev:
	$(PIP) install $(PIPFLAGS) --requirement requirements-dev.txt

.PHONY: fonts
fonts:
	$(NPM) $(NPMFLAGS) install
	mkdir -p flatdir/res/fonts/files
	cp node_modules/@fontsource/noto-sans/400.css flatdir/res/fonts/
	cp node_modules/@fontsource/noto-sans/600.css flatdir/res/fonts/
	cp node_modules/@fontsource/noto-sans/files/noto-sans-*-400-normal.woff2 \
	    flatdir/res/fonts/files/
	cp node_modules/@fontsource/noto-sans/files/noto-sans-*-600-normal.woff2 \
	    flatdir/res/fonts/files/
	@#rm flatdir/res/fonts
	@#cp -r node_modules/@fontsource/noto-sans flatdir/res/fonts

.PHONY: clean
clean:
	rm --recursive --force $$(find . -name __pycache__) .mypy_cache
