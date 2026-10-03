"""agentcore — the collaborative multi-agent runtime for ClaimBlitz.

This package replaces the legacy sequential pipeline in ``backend/agents/*``
and ``backend/main.py`` with a true multi-agent system: independent agents
with their own memory/tools/confidence, communicating over an event bus,
capable of debating and escalating to humans.

Sub-modules (built incrementally across the rebuild task list):

- ``protocol``  — shared wire format: messages, evidence, confidence,
                  decision paths, debate/vote models. No I/O, no deps on
                  any broker/db. Every other module imports from here.
                  [done - task #1]
- ``settings``  — centralized config (pydantic-settings), reads the same
                  backend/.env used by the legacy pipeline. [done - task #2]
- ``llm``       — async Gemini-primary/Ollama-fallback LLM client with
                  per-provider retry/backoff. [done - task #2]
- ``memory``    — ``AgentMemory`` interface + in-process fallback impl.
                  Pinecone-backed implementation lands in task #3, behind
                  the same interface. [interface done - task #2]
- ``tools``     — ``Tool``/``ToolRegistry`` interface for agent-invocable
                  capabilities (policy lookups, rule checks, etc).
                  [done - task #2]
- ``bus``       — ``MessageBus`` interface + a real in-process asyncio
                  implementation (used by tests / single-process dev mode).
                  RabbitMQ-backed implementation lands in task #7/#9, behind
                  the same interface. [interface + in-process impl done -
                  task #2]
- ``base``      — abstract ``Agent`` base class: owns its persona, memory,
                  tools, and LLM client; exposes analyze/answer_question/
                  respond_to_objection/cast_vote and the ask_peer/object_to
                  peer-communication primitives. [done - task #2]

- ``pinecone_memory`` — real vector-backed ``AgentMemory``, one Pinecone
                  namespace per agent. Supports Pinecone Local (docker
                  emulator, dev/test, no API key needed) and real
                  serverless Pinecone (prod) via
                  ``AgentCoreSettings.pinecone_use_local``. Embeds text via
                  Gemini (``AsyncLLMClient.embed_batch``) since Pinecone
                  Local doesn't support Pinecone's own hosted Inference API.
                  [done - task #3]

Not yet built:
- The 10 concrete agents (task #4).
- ``supervisor`` — orchestration engine: workflow state machine, fan-out/
  fan-in of analyst agents, Debate Mode round-tracking, escalation policy
  (task #5).
- ``blackboard`` — Redis-backed shared working memory for an in-flight claim
  (task #7).
- RabbitMQ-backed ``MessageBus`` implementation (task #7/#9).

The legacy ``backend/agents`` package and ``backend/app`` deterministic
pipeline are left untouched on disk; nothing in ``agentcore`` imports from
either.
"""
