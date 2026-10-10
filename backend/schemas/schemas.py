"""
Pydantic request/response schemas for the API layer.
"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PolicyVersionOut(BaseModel):
    id: UUID
    version: str
    effective_from: date
    effective_until: date | None
    status: str
    chunk_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class PolicyOut(BaseModel):
    id: UUID
    name: str
    insurer: str
    created_at: datetime
    versions: list[PolicyVersionOut] = []

    class Config:
        from_attributes = True


class PolicyUploadResponse(BaseModel):
    policy_id: UUID
    policy_version_id: UUID
    status: str
    message: str


class EvidenceItem(BaseModel):
    chunk_id: UUID
    content: str
    page: int | None
    section: str | None
    policy_version: str
    relevance_score: float


class ChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    policy_id: UUID | None = None
    as_of_date: date | None = None
    top_k: int = 8


class ChatQueryResponse(BaseModel):
    answer: str
    policy_version: str | None
    evidence: list[EvidenceItem]
    confidence: float
    warnings: list[str] = []
    crag_regime: str | None = None
    retrieval_strategy: str | None = None
    sub_queries: list[str] = []
    factual_precision: float | None = None
    reasoning_paths: list[str] = []
    okf_concepts: list[str] = []
    okf_rules_applied: dict = {}
    calibrated_confidence: float | None = None
    should_abstain: bool = False
    coverage_guarantee: float | None = None
    entropy_level: str | None = None
    speculative_drafts_count: int | None = None
    community_summaries: list[str] = []
    verified_claims: list[dict] = []
    # Patent Inventions (TTH-SDLA & CMPL)
    merkle_root: str | None = None
    certificate_signature: str | None = None
    conformal_interval: list[float] | None = None
    topological_dispersion: float | None = None
    lattice_arbitration_status: str | None = None


class CompareRequest(BaseModel):
    policy_version_id_a: UUID
    policy_version_id_b: UUID


class ClauseDiff(BaseModel):
    type: str  # SAME|UPDATED|CONTRADICTORY|REMOVED|ADDED
    clause_a: str | None
    clause_b: str | None
    explanation: str
    confidence: float


class CompareResponse(BaseModel):
    added: list[ClauseDiff]
    removed: list[ClauseDiff]
    modified: list[ClauseDiff]
    contradictions: list[ClauseDiff]


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    data: dict = {}


class GraphEdge(BaseModel):
    source: str
    target: str
    relation: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    communities: list[dict] = []


class HealthResponse(BaseModel):
    status: str
    env: str
