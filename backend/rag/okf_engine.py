"""
Open Knowledge Format (OKF) Engine for PolicyGraph-RAG.
======================================================
Manages deterministic, version-controlled canonical policy ontologies
stored as Markdown files with YAML frontmatter.

Capabilities:
1. Dynamic Discovery & Ingestion of OKF bundles in `knowledge_base/okf/`.
2. Bidirectional Concept Graph Traversal across explicit hyperlinks/relations.
3. Fast Keyword & Semantic Entity Resolution against incoming user queries.
4. Deterministic Rule Extraction for LLM Prompt Conditioning.
5. Post-Generation Rule Compliance & Contradiction Guardrails.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Search paths for OKF knowledge base
DEFAULT_OKF_DIRS = [
    Path(__file__).resolve().parent.parent.parent / "knowledge_base" / "okf",
    Path(__file__).resolve().parent.parent / "knowledge_base" / "okf",
    Path("knowledge_base/okf"),
]


@dataclass
class OKFRelation:
    target: str
    relation_type: str
    description: str = ""


@dataclass
class OKFConcept:
    id: str
    title: str
    domain: str
    version: str
    status: str
    category: str
    rules: dict[str, Any] = field(default_factory=dict)
    relations: dict[str, list[dict[str, str]]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    markdown_body: str = ""
    filepath: str = ""


class OKFEngine:
    """Singleton Engine to index and query OKF canonical knowledge."""

    def __init__(self, okf_dir: Optional[Path] = None):
        self.okf_dir = okf_dir or self._discover_okf_dir()
        self.concepts: dict[str, OKFConcept] = {}
        self.tag_index: dict[str, set[str]] = {}
        self.keyword_index: dict[str, set[str]] = {}
        self.load_okf_repository()

    def _discover_okf_dir(self) -> Path:
        for p in DEFAULT_OKF_DIRS:
            if p.exists() and p.is_dir():
                return p
        return DEFAULT_OKF_DIRS[0]

    def load_okf_repository(self) -> None:
        """Parses all OKF Markdown files with YAML frontmatter."""
        self.concepts.clear()
        self.tag_index.clear()
        self.keyword_index.clear()

        if not self.okf_dir.exists():
            logger.warning("OKF directory not found at: %s", self.okf_dir)
            return

        md_files = list(self.okf_dir.glob("*.md"))
        for file_path in md_files:
            if file_path.name.lower() == "readme.md":
                continue
            concept = self._parse_file(file_path)
            if concept:
                self.concepts[concept.id] = concept
                self._index_concept(concept)

        logger.info("OKFEngine initialized with %d canonical concepts from %s", len(self.concepts), self.okf_dir)

    def _parse_file(self, file_path: Path) -> Optional[OKFConcept]:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error("Failed to read OKF file %s: %s", file_path, e)
            return None

        # Regex split for YAML frontmatter between --- markers
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return None

        raw_yaml, body = match.groups()
        meta = self._parse_yaml_lines(raw_yaml)

        concept_id = meta.get("id", file_path.stem)
        return OKFConcept(
            id=concept_id,
            title=meta.get("title", file_path.stem.replace("_", " ").title()),
            domain=meta.get("domain", "healthcare_insurance"),
            version=str(meta.get("version", "1.0")),
            status=meta.get("status", "canonical"),
            category=meta.get("category", "General"),
            rules=meta.get("rules", {}),
            relations=meta.get("relations", {}),
            tags=[t.lower() for t in meta.get("tags", [])],
            markdown_body=body.strip(),
            filepath=str(file_path),
        )

    def _parse_yaml_lines(self, yaml_text: str) -> dict[str, Any]:
        """Lightweight robust YAML parser without external C-bindings."""
        result: dict[str, Any] = {"rules": {}, "relations": {}, "tags": []}
        current_section: Optional[str] = None
        current_rel_key: Optional[str] = None

        for line in yaml_text.splitlines():
            line_str = line.rstrip()
            if not line_str.strip() or line_str.strip().startswith("#"):
                continue

            indent = len(line_str) - len(line_str.lstrip())
            stripped = line_str.strip()

            if indent == 0 and ":" in stripped:
                key, val = stripped.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                current_section = key
                current_rel_key = None

                if val:
                    result[key] = self._cast_val(val)
                elif key not in result:
                    result[key] = {}
            elif indent > 0 and current_section == "rules" and ":" in stripped:
                r_key, r_val = stripped.split(":", 1)
                result["rules"][r_key.strip()] = self._cast_val(r_val.strip().strip('"').strip("'"))
            elif indent > 0 and current_section == "tags" and stripped.startswith("-"):
                tag = stripped.lstrip("-").strip().strip('"').strip("'")
                result["tags"].append(tag)
            elif indent > 0 and current_section == "relations":
                if stripped.endswith(":") and not stripped.startswith("-"):
                    current_rel_key = stripped.rstrip(":")
                    if current_rel_key not in result["relations"]:
                        result["relations"][current_rel_key] = []
                elif stripped.startswith("- target:") and current_rel_key:
                    target_val = stripped.replace("- target:", "").strip().strip('"').strip("'")
                    result["relations"][current_rel_key].append({"target": target_val})
                elif stripped.startswith("type:") and current_rel_key and result["relations"][current_rel_key]:
                    result["relations"][current_rel_key][-1]["type"] = stripped.replace("type:", "").strip()
                elif stripped.startswith("description:") and current_rel_key and result["relations"][current_rel_key]:
                    result["relations"][current_rel_key][-1]["description"] = stripped.replace("description:", "").strip().strip('"').strip("'")

        return result

    @staticmethod
    def _cast_val(val: str) -> Any:
        if val.isdigit():
            return int(val)
        try:
            return float(val)
        except ValueError:
            pass
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
        return val

    def _index_concept(self, concept: OKFConcept) -> None:
        # Index tags
        for t in concept.tags:
            self.tag_index.setdefault(t, set()).add(concept.id)

        # Index title terms
        for word in re.findall(r"\w+", concept.title.lower()):
            if len(word) > 2:
                self.keyword_index.setdefault(word, set()).add(concept.id)

    def resolve_concepts(self, query: str, top_k: int = 3) -> list[OKFConcept]:
        """Resolves user query to matching canonical OKF concepts."""
        query_lower = query.lower()
        query_words = set(re.findall(r"\w+", query_lower))

        scored_matches: dict[str, float] = {}

        # 1. Direct tag matches (weight: 3.0)
        for tag, c_ids in self.tag_index.items():
            if tag in query_lower or any(w in tag for w in query_words if len(w) > 3):
                for cid in c_ids:
                    scored_matches[cid] = scored_matches.get(cid, 0.0) + 3.0

        # 2. Keyword matches in title/rules (weight: 1.5)
        for word in query_words:
            if word in self.keyword_index:
                for cid in self.keyword_index[word]:
                    scored_matches[cid] = scored_matches.get(cid, 0.0) + 1.5

        # 3. Direct ID substring match
        for cid in self.concepts:
            short_id = cid.split(".")[-1]
            if short_id in query_lower:
                scored_matches[cid] = scored_matches.get(cid, 0.0) + 5.0

        sorted_cids = sorted(scored_matches.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [self.concepts[cid] for cid, _ in sorted_cids if cid in self.concepts]

    def traverse_linked_concepts(self, concept: OKFConcept) -> list[OKFConcept]:
        """Follows OKF relations/hyperlinks to fetch parent/related concept files."""
        linked: list[OKFConcept] = []
        for rel_group, links in concept.relations.items():
            for link in links:
                target_str = link.get("target", "")
                target_name = Path(target_str).stem
                for cid, c_obj in self.concepts.items():
                    if cid.endswith(target_name) or target_name in cid:
                        linked.append(c_obj)
        return linked

    def format_okf_context_for_prompt(self, concepts: list[OKFConcept]) -> str:
        """Serializes OKF canonical knowledge for injection into LLM prompt."""
        if not concepts:
            return ""

        blocks = ["[OKF CANONICAL KNOWLEDGE (Deterministic Authoritative Ground Truth)]:"]
        for c in concepts:
            rules_formatted = ", ".join(f"{k}: {v}" for k, v in c.rules.items()) if c.rules else "None specified"
            block = (
                f"• Concept: {c.title} [ID: {c.id} | Status: {c.status}]\n"
                f"  Rules: {rules_formatted}\n"
                f"  Overview: {c.markdown_body[:400]}..."
            )
            blocks.append(block)

        return "\n\n".join(blocks)

    def validate_answer_against_rules(
        self,
        answer: str,
        policy_tenure_months: Optional[int],
        concepts: list[OKFConcept],
    ) -> list[str]:
        """
        Guardrail: checks if LLM answer contradicts strict OKF canonical rules.
        """
        warnings = []
        ans_lower = answer.lower()

        for c in concepts:
            rules = c.rules
            waiting_months = rules.get("standard_waiting_period_months")

            # Check waiting period violation
            if waiting_months and policy_tenure_months is not None:
                if policy_tenure_months < waiting_months:
                    # The claim MUST be declared inadmissible or pending
                    if any(pos in ans_lower for pos in ["claim is approved", "is fully covered", "eligible for immediate"]):
                        warnings.append(
                            f"OKF Rule Violation: Query policy age ({policy_tenure_months}m) < "
                            f"canonical waiting period ({waiting_months}m for {c.title}). Answer falsely claimed immediate coverage!"
                        )

            # Check sub-limit violation
            sublimit = rules.get("default_sub_limit_inr")
            if sublimit:
                # If answer promises unlimited without citing a waiver
                if "no sub-limit" in ans_lower and "waiver" not in ans_lower:
                    warnings.append(
                        f"OKF Advisory: {c.title} has a canonical sub-limit of ₹{sublimit:,}. "
                        "Verify policy rider before approving unlimited reimbursement."
                    )

        return warnings


# Global singleton instance
okf_engine = OKFEngine()
