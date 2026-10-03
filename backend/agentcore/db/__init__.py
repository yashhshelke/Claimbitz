"""Database layer for the agentcore multi-agent system.

Uses MongoDB (via motor async driver) for document storage. Collections:
- claims, findings, workflows, escalations, audit_log.

MongoDB is a natural fit for this system because claim data, agent findings,
debate rounds, and decision paths are all nested JSON documents — no
ORM/schema mismatch, no migration headaches.
"""
