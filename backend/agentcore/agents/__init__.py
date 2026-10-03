"""Concrete specialized agents for the ClaimBlitz multi-agent system.

Each module here defines one ``agentcore.base.Agent`` subclass — its own
persona (``system_prompt``), its own domain reasoning (``analyze``), and
whatever tools/memory usage make sense for that specialty. None of these
classes talk to each other directly; they only communicate through the
``MessageBus`` primitives (`ask_peer`, `object_to`) inherited from ``Agent``.

Roster (9 of the 10 roles from ``agentcore.protocol.AgentRole`` — the tenth,
SUPERVISOR, is the orchestration engine built in task #5, not "just another
agent" in the same sense as these):

- ``scanner``            — ScannerAgent: document intake/triage
- ``ocr``                 — OCRAgent: structured field extraction
- ``validator``           — ValidatorAgent: structural/consistency checks
- ``medical_expert``      — MedicalExpertAgent: clinical plausibility
- ``policy_expert``       — PolicyExpertAgent: coverage/policy rules
- ``fraud_detection``     — FraudDetectionAgent: duplicate/pattern detection
- ``risk_assessment``     — RiskAssessmentAgent: numeric risk scoring
- ``communication``       — CommunicationAgent: drafts outbound messages
- ``judge``               — JudgeAgent: consensus ruling over analyst findings

Scanner, OCR, and Communication don't naturally produce an approve/reject
opinion the way the four parallel analysts and the Judge do — each still
implements ``analyze()`` (to satisfy the base ``Agent`` contract and remain
addressable over the bus like any other agent), but also exposes a richer,
role-specific method (``scan()``, ``extract()``, ``draft()``) that is what
the Supervisor (task #5) actually calls for its real work product.
"""
