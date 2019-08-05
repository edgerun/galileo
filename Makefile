.PHONY: all foo docker-build docker-prune start stop

VENV_BIN = virtualenv -p python3.7

all:
	@echo "select a build target"

venv: .venv/bin/activate

.venv/bin/activate: requirements.txt
	test -d .venv || $(VENV_BIN) .venv
	. .venv/bin/activate; pip install -Ur requirements.txt
	touch .venv/bin/activate

test: venv
	. .venv/bin/activate; python -m unittest discover -s tests/ -v

dist: venv
	. .venv/bin/activate; python setup.py sdist

install: venv
	. .venv/bin/activate; python setup.py install

dist-clean:
	rm -rf dist/
	rm -rf mc2_symmetry.egg-info/

