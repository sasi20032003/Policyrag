"""
OKF (Open Knowledge Format) API endpoints.
Provides discovery, inspection, and ontology graph visualization of canonical OKF concepts.
"""
from fastapi import APIRouter, HTTPException
from rag.okf_engine import okf_engine

router = APIRouter(prefix="/api/okf", tags=["okf"])


@router.get("/concepts")
async def list_okf_concepts():
    """List all registered OKF canonical concepts."""
    return [
        {
            "id": c.id,
            "title": c.title,
            "category": c.category,
            "status": c.status,
            "version": c.version,
            "tags": c.tags,
            "rules_count": len(c.rules),
            "relations_count": sum(len(v) for v in c.relations.values()),
        }
        for c in okf_engine.concepts.values()
    ]


@router.get("/concepts/{concept_id}")
async def get_okf_concept(concept_id: str):
    """Retrieve detailed OKF concept including rules, relations, and markdown body."""
    concept = okf_engine.concepts.get(concept_id)
    if not concept:
        # Try suffix match
        for cid, c in okf_engine.concepts.items():
            if cid.endswith(concept_id):
                concept = c
                break
    if not concept:
        raise HTTPException(status_code=404, detail="OKF concept not found")

    return {
        "id": concept.id,
        "title": concept.title,
        "category": concept.category,
        "status": concept.status,
        "version": concept.version,
        "rules": concept.rules,
        "relations": concept.relations,
        "tags": concept.tags,
        "markdown_body": concept.markdown_body,
        "filepath": concept.filepath,
    }


@router.get("/graph")
async def get_okf_graph():
    """Returns nodes and edges representing the OKF ontology graph."""
    nodes = []
    edges = []
    seen_nodes = set()

    for cid, c in okf_engine.concepts.items():
        if cid not in seen_nodes:
            nodes.append({
                "id": cid,
                "label": c.title,
                "type": "okf_concept",
                "category": c.category,
                "rules": c.rules,
            })
            seen_nodes.add(cid)

        for rel_type, targets in c.relations.items():
            for t in targets:
                target_str = t.get("target", "")
                target_name = target_str.replace("./", "").replace(".md", "")
                # Find matching target cid
                target_cid = next((k for k in okf_engine.concepts if target_name in k), target_name)
                edges.append({
                    "source": cid,
                    "target": target_cid,
                    "relation": t.get("type", rel_type),
                    "description": t.get("description", ""),
                })

    return {"nodes": nodes, "edges": edges}
