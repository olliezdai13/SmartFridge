# Simple development helpers.

VENV := .venv
PYTHON := python3

.PHONY: venv install

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	. $(VENV)/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
