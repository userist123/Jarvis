# JARVIS Agent Execution Policy

## Local-first

Agent routing and council selection are deterministic. The LLM may reason about a task, but it does not grant itself capabilities or decide its own execution authority.

## Routing

1. Classify the requested capabilities.
2. Rank enabled agent profiles by capability and task keywords.
3. Select one primary agent when the task is routine.
4. Escalate to a council when complexity, explicit review, or risky capabilities require it.

## Council

A council may contain one primary agent and up to two reviewers. Reviewers validate the plan or result; they do not automatically inherit execution authority.

## Risk

`execute_code`, `iot_control`, and `network` are treated as risky capabilities and should require explicit policy grants plus validation.

## Memory

Agent selection never bypasses memory governance. Recalled memory is evidence; provenance, confidence, lifecycle, and conflicts remain authoritative constraints.
