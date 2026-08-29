# JARVIS Local-First Architecture

## Principles

- Ollama is the default LLM provider.
- The AI Memory Vault is the canonical knowledge/memory source.
- Cloud LLM providers are optional and must never be required for normal local operation.
- Runtime memory is indexed into local SQLite for fast retrieval; the Vault remains the canonical Markdown source.
- JARVIS must work without internet access unless a user explicitly enables a cloud provider.

## Local data flow

```text
User
  -> JARVIS Desktop / Web HUD
  -> Cognitive Runtime
  -> OODA / Agent Router
  -> Memory Recall
  -> AI_Memory_Vault
  -> SQLite retrieval index
  -> Ollama
  -> Validator / Critic
  -> Response
```

## Vault discovery

Set `JARVIS_VAULT_PATH` to the user's vault directory for an explicit configuration.
When it is not set, JARVIS looks for `AI_Memory_Vault_CODEX_READY` next to the project and falls back to `vault_notes` for development.

Vault synchronization is enabled by default. Set `JARVIS_SYNC_VAULT=0` to disable startup synchronization.

## Model abstraction

Agents use the `BaseLLMProvider` interface. They do not depend directly on Ollama. This keeps the architecture ready for future providers such as OpenAI or Anthropic without coupling cognitive logic to a vendor API.
