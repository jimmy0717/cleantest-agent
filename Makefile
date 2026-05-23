.PHONY: test lint install dev-install demo clean help build

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

dev-install:  ## Install the cleantest_agent package + dev tools (pytest/flake8/mypy) in editable mode
	pip install -e ".[dev]"

test:  ## Run all tests
	pytest tests/ -v --tb=short --cov=cleantest_agent --cov-report=term-missing

lint:  ## Run linters
	flake8 cleantest_agent/ skills/ tests/ --max-line-length=120
	mypy cleantest_agent/ --ignore-missing-imports

install:  ## Install skills to ~/.codebuddy/skills/ (run `make dev-install` first)
	@command -v python >/dev/null && python -c "import cleantest_agent" 2>/dev/null || \
		(echo "WARNING: cleantest_agent package is not installed in the active Python environment."; \
		 echo "         Run 'make dev-install' (or 'pip install -e .') first, otherwise the skills"; \
		 echo "         will fail with 'ModuleNotFoundError: No module named cleantest_agent'."; )
	@mkdir -p ~/.codebuddy/skills
	@for s in cleantest-pipeline cleantest-syntax-filter cleantest-relevance-filter cleantest-coverage-filter; do \
		cp -R skills/$$s ~/.codebuddy/skills/$$s; \
		echo "Installed $$s"; \
	done
	@echo "All skills installed. Restart CodeBuddy to activate."

demo:  ## Run the pipeline on sample data (no LLM)
	python -m cleantest_agent.pipeline --input_csv tests/fixtures/sample_noisy.csv --output_dir ./output --skip_coverage

build:  ## Build sdist + wheel under dist/
	python -m build

clean:  ## Remove build artifacts and output files
	rm -rf output/ __pycache__ .pytest_cache .mypy_cache *.egg-info build dist .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
