"""
Adaptive Query Engine for Policy RAG.
Inspired by Adaptive-RAG (NAACL 2024), HyDE (ACL 2023), Step-Back Prompting (ICLR 2024),
and Query2Doc (EMNLP 2023).

Features:
1. Query Complexity Classification: Identifies Simple, Conditional, Comparative, or Multi-hop intent.
2. Domain-Aware Expansion: Injects insurance-specific synonyms, regulatory terms, and sub-clauses.
3. Sub-Query Decomposition: Splits compound insurance questions into targeted micro-queries.
4. HyDE (Hypothetical Document Embeddings): Synthesizes pseudo-clause wording to bridge vocabulary mismatch.
"""
import enum
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


class QueryComplexity(str, enum.Enum):
    SIMPLE = "simple"            # Direct definition or single-fact question
    CONDITIONAL = "conditional"  # Involves disease, waiting period, or specific eligibility
    COMPARATIVE = "comparative"  # Compares versions, policies, or coverage options
    MULTI_HOP = "multi_hop"      # Multi-part question (e.g. coverage AND sublimit AND copay)


# Domain-specific synonym & term expansion map for Indian & International Health Insurance
INSURANCE_TAXONOMY: dict[str, list[str]] = {
    "cataract": [
        "cataract surgery",
        "eye treatment",
        "intraocular lens",
        "sub-limit for cataract",
        "ophthalmic procedure",
    ],
    "maternity": [
        "maternity expenses",
        "normal delivery",
        "caesarean section",
        "newborn baby coverage",
        "waiting period for maternity",
    ],
    "room rent": [
        "room rent capping",
        "ICU charges",
        "boarding and nursing expenses",
        "proportionate deduction",
        "single private room",
    ],
    "pre-existing": [
        "pre-existing disease",
        "PED waiting period",
        "prior illness",
        "hypertension diabetes",
        "36 months 48 months exclusion",
    ],
    "ped": [
        "pre-existing disease",
        "PED waiting period",
        "declared illness",
        "continuous coverage",
    ],
    "day care": [
        "day care treatment",
        "less than 24 hours hospitalization",
        "dialysis chemotherapy",
        "specified day care procedures",
    ],
    "ayush": [
        "ayurveda unani siddha homeopathy",
        "alternative treatment",
        "government recognized hospital",
    ],
    "organ donor": [
        "inpatient hospitalization of donor",
        "organ transplantation expenses",
        "harvesting organ",
    ],
    "no claim bonus": [
        "cumulative bonus",
        "NCB percentage",
        "bonus increase per claim free year",
    ],
    "restoration": [
        "recharge benefit",
        "refill of sum insured",
        "automatic restoration",
    ],
    "copay": [
        "co-payment",
        "percentage of claim borne by insured",
        "zone co-pay",
        "age-based co-payment",
    ],
    "waiting period": [
        "initial waiting period 30 days",
        "specific illness waiting period 24 months",
        "pre-existing disease waiting period",
    ],
}


@dataclass
class QueryAnalysis:
    original_query: str
    complexity: QueryComplexity
    sub_queries: list[str] = field(default_factory=list)
    expanded_terms: list[str] = field(default_factory=list)
    hyde_prompt: Optional[str] = None
    target_clause_types: list[str] = field(default_factory=list)


def classify_query_complexity(query: str) -> QueryComplexity:
    """
    Classify query complexity to route retrieval through optimal RAG channels
    (Adaptive-RAG methodology).
    """
    q_lower = query.lower()

    # Check for comparative queries
    if any(k in q_lower for k in ["compare", "difference between", "v1 vs v2", "updated", "changed", "better than"]):
        return QueryComplexity.COMPARATIVE

    # Check for multi-hop / multi-part queries
    multi_part_indicators = [
        " and ",
        " as well as ",
        " also ",
        "along with",
        "what about",
        "both",
    ]
    has_conjunction = any(ind in q_lower for ind in multi_part_indicators)
    question_marks = q_lower.count("?")

    if question_marks > 1 or (has_conjunction and len(query.split()) > 10):
        return QueryComplexity.MULTI_HOP

    # Check for conditional queries (waiting periods, exclusions, limits for specific treatments)
    conditional_keywords = [
        "if",
        "when",
        "eligible",
        "waiting period",
        "cover",
        "covered",
        "exclusion",
        "limit",
        "sub-limit",
        "copay",
        "deductible",
        "after how long",
    ]
    if any(k in q_lower for k in conditional_keywords):
        return QueryComplexity.CONDITIONAL

    return QueryComplexity.SIMPLE


def decompose_query(query: str) -> list[str]:
    """
    Decomposes multi-part queries into focused sub-queries for precision retrieval.
    """
    sub_queries = [query]

    # Split by conjunctions or question marks
    parts = re.split(r"\?|\band\b|\balso\b", query, flags=re.IGNORECASE)
    cleaned_parts = [p.strip() for p in parts if len(p.strip().split()) >= 3]

    if len(cleaned_parts) > 1:
        for p in cleaned_parts:
            if not p.endswith("?"):
                p = p + "?"
            if p not in sub_queries:
                sub_queries.append(p)

    return sub_queries


def generate_domain_expansions(query: str) -> list[str]:
    """
    Extracts key insurance taxonomy concepts from query and returns related terms.
    """
    q_lower = query.lower()
    expansions: list[str] = []

    for term, related_terms in INSURANCE_TAXONOMY.items():
        if re.search(r"\b" + re.escape(term) + r"\b", q_lower):
            expansions.extend(related_terms)

    return list(dict.fromkeys(expansions))[:6]


def generate_hyde_document(query: str, expansions: list[str]) -> str:
    """
    Synthesizes a hypothetical policy wording clause (HyDE) to bridge
    the semantic gap between casual query and formal legal/policy text.
    """
    exp_context = ", ".join(expansions) if expansions else "terms, conditions, limits and exclusions"
    return (
        f"Under the terms of this Health Insurance Policy, coverage for {query} is subject to the following provisions: "
        f"The Company agrees to pay or reimburse medical expenses incurred for {query}, including {exp_context}. "
        f"Subject to waiting periods, room rent capping, sub-limits, and co-payment specified in the Policy Schedule."
    )


def analyze_query(query: str) -> QueryAnalysis:
    """
    Master entrypoint for adaptive query analysis.
    Returns structured analysis with complexity, sub-queries, domain expansions, and HyDE representation.
    """
    complexity = classify_query_complexity(query)
    sub_queries = decompose_query(query) if complexity in (QueryComplexity.MULTI_HOP, QueryComplexity.CONDITIONAL) else [query]
    expansions = generate_domain_expansions(query)
    hyde_doc = generate_hyde_document(query, expansions)

    # Determine likely target clause types
    target_clause_types = []
    q_lower = query.lower()
    if any(k in q_lower for k in ["waiting", "ped", "prior", "pre-existing", "months", "years"]):
        target_clause_types.append("waiting_period")
    if any(k in q_lower for k in ["limit", "sub-limit", "rent", "copay", "deductible", "maximum", "cap"]):
        target_clause_types.append("limit")
    if any(k in q_lower for k in ["exclu", "not cover", "denied", "reject"]):
        target_clause_types.append("exclusion")
    if any(k in q_lower for k in ["cover", "eligible", "benefit", "inpatient", "daycare"]):
        target_clause_types.append("coverage")

    if not target_clause_types:
        target_clause_types = ["general", "coverage"]

    return QueryAnalysis(
        original_query=query,
        complexity=complexity,
        sub_queries=sub_queries,
        expanded_terms=expansions,
        hyde_prompt=hyde_doc,
        target_clause_types=target_clause_types,
    )
