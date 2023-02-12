.DEFAULT_GOAL := help


.PHONY: help
help: ## Show this message
	@echo "Usage: make COMMAND\n\nCommands:"
	@grep '\s##\s' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' | cat


.PHONY: install
install: ## Install via poetry
	curl -sSL https://install.python-poetry.org | python3 -
	poetry install
	@echo "Virtual environment created in $(poetry env list --full-path)"


.PHONY: docs
docs: ## Build documentation
	@echo "--> Building docs"
	@cd docs && SPHINXOPTS="-W" make html
