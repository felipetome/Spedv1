.PHONY: setup run test clean lint check-venv install-editable

VENV := venv
PY := $(VENV)/bin/python3
PIP := $(VENV)/bin/pip

setup:  ## Cria venv e instala o pacote em modo editable com deps de dev
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	@echo "✅ Venv pronto. Use '$(PY)' ou ative com 'source $(VENV)/bin/activate'"

install-editable: check-venv  ## Reinstala pacote editable (após mudança de pyproject.toml)
	$(PIP) install -e ".[dev]"

test: check-venv  ## Roda pytest
	$(VENV)/bin/pytest

lint: check-venv
	$(PY) -m ruff check . 2>/dev/null || $(PIP) install ruff && $(PY) -m ruff check .

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache *.egg-info build dist

check-venv:
	@test -d $(VENV) || (echo "❌ Venv não existe. Rode 'make setup'" && exit 1)

help:
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
