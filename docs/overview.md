# System overview

Oche Agents is intended to help one person organize work by project and topic, route tasks to approved model/agent integrations, and carry forward selected context between related sessions. This page describes the public-facing target architecture and separates it from the prototype that exists today.

## Current prototype

```text
CLI request
    │
    ▼
Local Ollama classifier
    │  task type + confidence + reason codes
    ▼
Policy validation and route planning
    │
    ▼
Route plan printed to the terminal
```

The CLI currently supports `poa doctor` and `poa route`. The model classifies a task; the Core validates the output and applies the configured provider allowlist. `route` does not invoke a provider, persist a session, or start an agent.

## Intended architecture

```text
CLI / future UI or IDE client
              │
              ▼
     Local orchestration core
       ├── Project and topic manager
       ├── Parent-session orchestrator
       │     └── Scoped child-agent sessions
       ├── Local task classifier
       ├── Policy router → execution profile
       ├── Provider connection + model catalog
       ├── Model-bound inference profiles
       └── Session/context ledger
```

The Core is intended to be the single place where routing policy, session relationships, provider state, and context permissions are enforced. Clients should not hold provider credentials or independently decide which agents may run.

### Provider, model, and inference selection

The target design separates a provider connection (service/account), a provider-scoped model ID, and an **execution profile** that binds a model to validated inference settings. One connection may expose multiple models, and one model may have multiple profiles such as low- and high-effort settings. The router selects an allowed profile rather than selecting only a provider.

Inference controls are model-specific. The adapter validates support and maps a limited normalized effort preference to the provider's native API. Unsupported controls are rejected rather than silently ignored; fallback to another model or effort profile is visible in the result. These are design goals, not current CLI features: the existing prototype only creates a provider-level route plan.

### Project, topic, and session model

- A **Project** groups durable work material and policy; it is optional.
- A **Topic** represents an ongoing subject and may exist independently of a project.
- A user-facing **parent session** owns a conversation turn and its orchestration plan.
- A **child-agent session** handles a scoped invocation requested by the parent.

The parent plan is intended to identify the allowed agents, their input context, provider/tool limits, dependencies, and expected outputs. A child should not gain authority to activate arbitrary agents or modify a project's approved state.

### Context sharing

Related sessions are intended to share selected context entries, not silently copy entire transcripts. Shared entries should retain their source session/run, revision, scope, and draft/approved state. A parent reviews child results before they become shared drafts; explicit user approval is required before a draft becomes a confirmed project decision. Sharing context between sessions does not itself authorize sending that context to an external provider.

## Routing and integration boundaries

The local classifier is a recommendation input, not an authorization mechanism. Policy determines which providers and agents are eligible. Provider adapters are intended to use supported integrations; fallback to another provider should be visible and subject to the same data checks.

In the current prototype, Ollama is used only for local classification and the route plan is not executed. The API server, persistent project/session ledger, provider execution, UI integrations, and parent/child session orchestration remain future work.

## Repository map

| Path | Purpose |
|---|---|
| `src/poa_core/` | Classifier, policy loading, routing, and CLI |
| `examples/policy.yaml` | Example allowlisted provider policy |
| `tests/` | Unit tests for classification and route planning |
| `docs/` | Public system overview |

## Privacy notes

- The default classifier endpoint is `http://127.0.0.1:11434`.
- The current CLI does not send prompts to external providers.
- If provider execution is added, each destination will need explicit policy and privacy checks.
- Provider credentials must be stored outside project policy files and source control.
