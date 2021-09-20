.PHONY: usage clean clean-dist docker upload

VENV_BIN = python3 -m venv
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

deploy: venv clean-dist pytest dist
	$(VENV_ACTIVATE); pip install --upgrade twine; twine upload dist/*

upload: venv
	$(VENV_ACTIVATE); pip install --upgrade twine; twine upload dist/*

docker-arm:
	docker run --rm --privileged multiarch/qemu-user-static:register --reset; \
	docker build -f docker/galileo/Dockerfile.arm32v7 -t galileo/galileo-arm32v7 .

clean-dist: clean
	rm -rf dist/
	rm -rf *.egg-info/
