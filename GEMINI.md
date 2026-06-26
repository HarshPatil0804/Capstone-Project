# Coding Agent Guide for AquaGuard Agent

## Development Commands

| Command | Purpose |
|---------|---------|
| `make install` | Sync and install Python dependencies |
| `make playground` | Launch the ADK web playground (http://localhost:18081) |
| `make run` | Run local web server |
| `make test` | Run unit tests |

## Operational Guidelines

- **Code preservation**: Only modify code directly targeted by the user's request. Preserve all surrounding code, config values, comments, and formatting.
- **Model selection**: Use `gemini-2.5-flash` or `gemini-2.5-flash-lite` dynamically loaded from the env.
- **Windows Hot-Reload Warning**: After any code edit to `agent.py`, `mcp_server.py`, or `config.py`, you must fully stop the running server/playground (via `Get-Process -Id (Get-NetTCPConnection -LocalPort 18081, 8090).OwningProcess | Stop-Process -Force` in PowerShell) and restart it.
