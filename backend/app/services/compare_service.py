"""Contract comparison service - diffs two review results."""
from typing import Dict, Any, List, Optional


def compare_reviews(review_a: Dict[str, Any], review_b: Dict[str, Any]) -> Dict[str, Any]:
    """Compare two review results field by field."""
    result: Dict[str, Any] = {
        "file_a": {"id": review_a.get("file_id", ""), "filename": review_a.get("filename", "")},
        "file_b": {"id": review_b.get("file_id", ""), "filename": review_b.get("filename", "")},
        "score_comparison": {
            "a": review_a.get("risk_score", 0),
            "b": review_b.get("risk_score", 0),
            "diff": (review_b.get("risk_score", 0) or 0) - (review_a.get("risk_score", 0) or 0),
        },
        "risk_level_comparison": {
            "a": review_a.get("risk_level", ""),
            "b": review_b.get("risk_level", ""),
        },
        "field_diffs": [],
        "issue_comparison": _compare_issues(review_a, review_b),
        "dimension_comparison": _compare_dimensions(review_a, review_b),
    }

    # Compare structured info fields
    sa = review_a.get("structured_info") or {}
    sb = review_b.get("structured_info") or {}
    fields = ["contract_type", "parties", "contract_period", "payment_terms",
              "breach_liability", "dispute_resolution", "confidentiality",
              "intellectual_property", "termination"]

    for field in fields:
        va = sa.get(field)
        vb = sb.get(field)
        if va != vb:
            result["field_diffs"].append({
                "field": field,
                "value_a": _truncate(va),
                "value_b": _truncate(vb),
                "status": "different" if (va and vb) else ("only_a" if va else "only_b"),
            })

    return result


def _compare_issues(a: Dict, b: Dict) -> Dict[str, Any]:
    ia = a.get("issues", [])
    ib = b.get("issues", [])
    return {
        "a_count": len(ia),
        "b_count": len(ib),
        "a_high": sum(1 for i in ia if i.get("severity") == "high"),
        "b_high": sum(1 for i in ib if i.get("severity") == "high"),
        "a_medium": sum(1 for i in ia if i.get("severity") == "medium"),
        "b_medium": sum(1 for i in ib if i.get("severity") == "medium"),
        "common_titles": _find_common(ia, ib),
    }


def _compare_dimensions(a: Dict, b: Dict) -> List[Dict[str, Any]]:
    da = {d.get("name", ""): d for d in (a.get("scoring_dimensions") or [])}
    db = {d.get("name", ""): d for d in (b.get("scoring_dimensions") or [])}
    all_dims = sorted(set(list(da.keys()) + list(db.keys())))
    result = []
    for name in all_dims:
        a_score = da.get(name, {}).get("score", 0)
        b_score = db.get(name, {}).get("score", 0)
        result.append({
            "dimension": name,
            "score_a": a_score,
            "score_b": b_score,
            "diff": b_score - a_score,
        })
    return result


def _find_common(ia: List[Dict], ib: List[Dict]) -> List[str]:
    titles_a = {i.get("title", "") for i in ia if i.get("title")}
    titles_b = {i.get("title", "") for i in ib if i.get("title")}
    return sorted(titles_a & titles_b)


def _truncate(val: Any, max_len: int = 200) -> Any:
    if isinstance(val, str) and len(val) > max_len:
        return val[:max_len] + "..."
    if isinstance(val, list):
        return [_truncate(v, max_len) for v in val[:5]]
    return val
