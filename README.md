# Oche Agents

A local-first personal AI orchestration prototype. The current implementation classifies a request with a local Ollama model and produces a policy-based route plan. It does **not** call external providers or start agent sessions.

## What works today

- Classifies a request as research, writing, coding, analysis, or general using Ollama.
- Validates the model output and selects only a provider allowed by the local YAML policy.
- Prints a route plan without sending the request to that provider.

The planned project/topic session orchestration and cross-session context sharing are summarized in the [system overview](docs/overview.md); they are not implemented yet.

## Quick start

Requirements: Python 3.9+, [uv](https://docs.astral.sh/uv/), and [Ollama](https://ollama.com/download).

```bash
uv sync
ollama pull gemma3:1b
uv run poa doctor
uv run poa route --policy examples/policy.yaml
```

Enter a request when prompted, or pipe it through standard input. The output is a plan only; provider execution is not implemented.

Run tests:

```bash
uv run python -m unittest discover -s tests -v
```

## Security and scope

- The classifier connects only to the loopback Ollama endpoint by default.
- The current route command does not transmit prompts to external providers.
- Do not put credentials in policy files.
- Gemma 3 uses its own terms; review the model license and local hardware requirements before use.

## License

No license has been selected yet. Public availability does not by itself grant permission to reuse or redistribute this project.

