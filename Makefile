.PHONY: usage clean clean-dist

VENV_BIN = virtualenv -p python3.7
VENV_DIR ?= .venv

VENV_ACTIVATE = . $(VENV_DIR)/bin/activate

usage:
	@echo "select a build target"

venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate: requirements.txt requirements-dev.txt
	test -d .venv || $(VENV_BIN) .venv
	$(VENV_ACTIVATE); pip install -Ur requirements.txt
	$(VENV_ACTIVATE); pip install -Ur requirements-dev.txt
	touch $(VENV_DIR)/bin/activate

clean:
	rm -rf build/
	rm -rf .eggs/
	rm -rf *.egg-info/

test: venv
	. .venv/bin/activate; python setup.py test

dist: venv
	. .venv/bin/activate; python setup.py sdist

install: venv
	. .venv/bin/activate; python setup.py install

clean-dist: clean
	rm -rf dist/
	rm -rf *.egg-info/
