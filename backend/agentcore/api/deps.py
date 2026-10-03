"""Dependency providers for the API layer.

Lazy-initializes the Supervisor (with all 9 agents) and the Blackboard
singleton. Uses module-level singletons to avoid re-creating expensive
objects on every request.
"""

from __future__ import annotations

from ..blackboard import Blackboard, InMemoryBlackboard
from ..bus import InProcessMessageBus
from ..llm import AsyncLLMClient
from ..protocol import AgentRole
from ..settings import get_settings
from ..supervisor import Supervisor

_supervisor: Supervisor | None = None
_blackboard: Blackboard | None = None
_llm: AsyncLLMClient | None = None


def get_llm_dep() -> AsyncLLMClient:
    global _llm
    if _llm is None:
        _llm = AsyncLLMClient()
    return _llm


def get_blackboard_dep() -> Blackboard:
    global _blackboard
    if _blackboard is None:
        settings = get_settings()
        # Use InMemoryBlackboard for dev when Redis isn't available;
        # RedisBlackboard for staging/prod.
        if settings.redis_url and settings.environment != "development":
            from ..blackboard import RedisBlackboard
            _blackboard = RedisBlackboard(settings.redis_url)
        else:
            _blackboard = InMemoryBlackboard()
    return _blackboard


def get_supervisor_dep() -> Supervisor:
    global _supervisor
    if _supervisor is None:
        from ..agents.scanner import ScannerAgent
        from ..agents.ocr import OCRAgent
        from ..agents.validator import ValidatorAgent
        from ..agents.medical_expert import MedicalExpertAgent
        from ..agents.policy_expert import PolicyExpertAgent
        from ..agents.fraud_detection import FraudDetectionAgent
        from ..agents.risk_assessment import RiskAssessmentAgent
        from ..agents.communication import CommunicationAgent
        from ..agents.judge import JudgeAgent

        llm = get_llm_dep()
        bus = InProcessMessageBus()

        _supervisor = Supervisor(
            scanner=ScannerAgent(
                role=AgentRole.SCANNER, llm=llm, bus=bus),
            ocr=OCRAgent(
                role=AgentRole.OCR, llm=llm, bus=bus),
            validator=ValidatorAgent(
                role=AgentRole.VALIDATOR, llm=llm, bus=bus),
            medical_expert=MedicalExpertAgent(
                role=AgentRole.MEDICAL_EXPERT, llm=llm, bus=bus),
            policy_expert=PolicyExpertAgent(
                role=AgentRole.POLICY_EXPERT, llm=llm, bus=bus),
            fraud_detection=FraudDetectionAgent(
                role=AgentRole.FRAUD_DETECTION, llm=llm, bus=bus),
            risk_assessment=RiskAssessmentAgent(
                role=AgentRole.RISK_ASSESSMENT, llm=llm, bus=bus),
            communication=CommunicationAgent(
                role=AgentRole.COMMUNICATION, llm=llm, bus=bus),
            judge=JudgeAgent(
                role=AgentRole.JUDGE, llm=llm, bus=bus),
        )
    return _supervisor
