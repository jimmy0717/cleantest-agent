.PHONY: test lint install clean help

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

test:  ## Run all tests
	pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

lint:  ## Run linters
	flake8 src/ skills/ tests/ --max-line-length=120
	mypy src/ --ignore-missing-imports

install:  ## Install skills to ~/.codebuddy/skills/
	@mkdir -p ~/.codebuddy/skills
	@for s in cleantest-pipeline cleantest-syntax-filter cleantest-relevance-filter cleantest-coverage-filter; do \
		cp -R skills/$$s ~/.codebuddy/skills/$$s; \
		echo "Installed $$s"; \
	done
	@echo "All skills installed. Restart CodeBuddy to activate."

clean:  ## Run the full pipeline on sample data
	python -m src.pipeline --input_csv tests/fixtures/sample_noisy.csv --output_dir ./output --llm_enhance
