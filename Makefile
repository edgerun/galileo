.PHONY: usage clean clean-dist docker

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
	find -iname "*.pyc" -delete

test: venv
	$(VENV_ACTIVATE); python setup.py test

pytest: venv
	$(VENV_ACTIVATE); pytest tests/ --cov galileo/

dist: venv
	$(VENV_ACTIVATE); python setup.py sdist

install: venv
	$(VENV_ACTIVATE); python setup.py install

docker:
	docker build -f docker/galileo/Dockerfile.amd64 -t galileo/galileo .

docker-arm:
	docker build -f docker/galileo/Dockerfile.arm -t galileo/galileo-arm32v7 .

clean-dist: clean
	rm -rf dist/
	rm -rf *.egg-info/
