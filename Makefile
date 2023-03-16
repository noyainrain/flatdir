PIP=pip3
PIPFLAGS=--upgrade

.PHONY: deps
deps:
	$(PIP) install $(PIPFLAGS) --requirement requirements.txt

.PHONY: clean
clean:
	rm --recursive --force .mypy_cache
