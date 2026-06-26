.PHONY: install playground run test

install:
	uv sync

playground:
	uv run adk web aquaguard_agent --host 127.0.0.1 --port 18081 --reload_agents

run:
	uv run uvicorn aquaguard_agent.agent_runtime_app:app --host 127.0.0.1 --port 8080

test:
	uv run pytest tests/
