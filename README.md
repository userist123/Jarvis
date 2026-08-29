# JARVIS

Local-first cognitive AI system with WPF desktop, web HUD, cognitive brain, agents, OODA execution, memory, voice, and Forge.

## Architecture

JARVIS is designed local-first. Ollama is the default LLM provider, while the AI Memory Vault is the canonical persistent knowledge and memory source. Cloud providers remain optional extension points and are not required for normal local operation.

```text
User
  -> Desktop / Web HUD
  -> Cognitive Runtime
  -> OODA + Agent Router
  -> Memory Recall
  -> AI_Memory_Vault + SQLite index
  -> Cognitive Gateway
  -> Model Router
  -> Ollama
  -> Capability Policy
  -> Validator / Critic
  -> Response
```

## Memory Contract

JARVIS treats the AI Memory Vault as canonical memory and SQLite as a derived runtime index. Memory writes are proposals first and are governed by deterministic checks for provenance, verification, technology/version scope, duplication, and conflict handling.

The governance layer follows the Vault rules: unknown technology/version scope does not trigger automatic deduplication; unresolved conflicts are preserved instead of silently overwritten; weak or unverified candidates remain in review.

## Components

- `jarvis_desktop` - native WPF command center
- `jarvis_cognitive_brain` - cognitive core, memory, agents and OODA
- `jarvis_web` - web HUD, voice service and browser interface
- `generated_programs` - runtime-generated artifacts (not tracked)

## Local-first configuration

Set `JARVIS_VAULT_PATH` to the local `AI_Memory_Vault_CODEX_READY` directory when you want an explicit vault location. Without it, the cognitive brain attempts to discover the vault next to the project and falls back to `vault_notes` for development.

Ollama defaults to `http://localhost:11434` and model `qwen2.5-coder:7b`.

Vault synchronization is enabled by default. Set `JARVIS_SYNC_VAULT=0` to disable startup synchronization.

## Development

See each component README for local setup and runtime requirements.

For the architecture contract, see `LOCAL_FIRST_ARCHITECTURE.md`.
