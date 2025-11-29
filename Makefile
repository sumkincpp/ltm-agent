hello:
	@echo "Hello, Little Thinking Model Agent!"

test:
	uv run pytest tests/ -v -n 6

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} +
	rm -rf .mypy_cache .venv .pytest_cache

fibonacci:
	uv run ltm-agent run planning_full "calculate the 10th fibonacci number and show result as FIB:<NUMBER>" --verbose

factorial:
	uv run ltm-agent run planning_full "use code execution to calculate the factorial of 10 and show result as FACT:<NUMBER>" --verbose

nvidia:
	uv run ltm-agent run planning_full "use code execution to fetch the current stock price of NVIDIA (NVDA) using yfinance and show result as PRICE:<NUMBER>" --verbose