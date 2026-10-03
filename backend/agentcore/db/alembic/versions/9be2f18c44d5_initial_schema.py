"""initial_schema

Revision ID: 9be2f18c44d5
Create Date: 2026-07-30

Creates all tables for the agentcore multi-agent claim processing system.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "9be2f18c44d5"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "claims",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("patient_name", sa.String(256)),
        sa.Column("provider_name", sa.String(256)),
        sa.Column("diagnosis", sa.Text),
        sa.Column("diagnosis_codes", postgresql.JSONB),
        sa.Column("procedure_codes", postgresql.JSONB),
        sa.Column("billed_amount", sa.Float),
        sa.Column("service_date", sa.String(10)),
        sa.Column("raw_text", sa.Text),
        sa.Column("file_meta", postgresql.JSONB),
        sa.Column("extracted_data", postgresql.JSONB),
        sa.Column("source_filename", sa.String(512)),
        sa.Column("stage", sa.String(32), nullable=False, server_default="ingested"),
        sa.Column("final_verdict", sa.String(16)),
        sa.Column("risk_score", sa.Float),
        sa.Column("risk_label", sa.String(16)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_claims_stage_created", "claims", ["stage", "created_at"])

    op.create_table(
        "claim_findings",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("claim_id", sa.String(32), nullable=False),
        sa.Column("agent_role", sa.String(32), nullable=False),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("reasoning", sa.Text, server_default=""),
        sa.Column("evidence", postgresql.JSONB),
        sa.Column("referenced_fields", postgresql.JSONB),
        sa.Column("tags", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_findings_claim_agent", "claim_findings", ["claim_id", "agent_role"])

    op.create_table(
        "claim_workflows",
        sa.Column("claim_id", sa.String(32), primary_key=True),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("is_paused", sa.Boolean, server_default="false"),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("decision_path", postgresql.JSONB),
        sa.Column("debate_rounds", postgresql.JSONB),
        sa.Column("ruling", postgresql.JSONB),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "escalations",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("claim_id", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("triggered_by", sa.String(32), nullable=False),
        sa.Column("confidence_value", sa.Float),
        sa.Column("status", sa.String(16), server_default="pending"),
        sa.Column("assigned_to", sa.String(256)),
        sa.Column("resolution_notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_escalations_claim_id", "escalations", ["claim_id"])
    op.create_index("ix_escalations_status", "escalations", ["status"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("claim_id", sa.String(32), nullable=False),
        sa.Column("agent_role", sa.String(32), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("summary", sa.Text, server_default=""),
        sa.Column("confidence", sa.Float),
        sa.Column("payload", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_log_claim_id", "audit_log", ["claim_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("escalations")
    op.drop_table("claim_workflows")
    op.drop_table("claim_findings")
    op.drop_table("claims")
