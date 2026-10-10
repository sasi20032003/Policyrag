"""
Selects the policy version(s) valid for a given as-of date, so the pipeline
never silently mixes outdated and current clauses.
"""
import logging
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.orm_models import PolicyVersion

logger = logging.getLogger(__name__)


async def get_valid_versions(
    db: AsyncSession, policy_id: UUID | None, as_of_date: date | None
) -> list[PolicyVersion]:
    """Return the policy version(s) valid on as_of_date (defaults to today).

    If policy_id is None, considers all policies (multi-policy question).
    Only versions with status='ready' are eligible for retrieval.
    """
    as_of_date = as_of_date or date.today()

    stmt = select(PolicyVersion).where(PolicyVersion.status == "ready")
    if policy_id is not None:
        stmt = stmt.where(PolicyVersion.policy_id == policy_id)

    all_versions = (await db.execute(stmt)).scalars().all()

    valid = [
        v
        for v in all_versions
        if v.effective_from <= as_of_date and (v.effective_until is None or v.effective_until >= as_of_date)
    ]

    if not valid:
        logger.warning("No policy version valid for as_of_date=%s (policy_id=%s)", as_of_date, policy_id)
        return []

    # If multiple policies map to the same insurer/name, prefer the most
    # recently effective version per policy_id.
    latest_per_policy: dict[UUID, PolicyVersion] = {}
    for v in valid:
        current = latest_per_policy.get(v.policy_id)
        if current is None or v.effective_from > current.effective_from:
            latest_per_policy[v.policy_id] = v

    return list(latest_per_policy.values())
