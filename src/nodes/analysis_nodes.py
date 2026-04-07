"""
Analysis Nodes for SWOT and Strategic Insight Generation.

These nodes keep a strict state contract while supporting two execution modes:
1. Rule-based local analysis (default, always available)
2. Optional LLM-assisted analysis when OPENAI_API_KEY is configured
"""

from typing import Dict, List, Any, Mapping

from ..agents.analysis_prompts import (
    CROSS_VALIDATION_PROMPT,
    HUMAN_REVIEW_PROMPT,
    INSIGHT_PROMPT,
    OPPORTUNITY_ANALYSIS_PROMPT,
    RESILIENCE_EVALUATION_PROMPT,
    STRENGTH_ANALYSIS_PROMPT,
    THREAT_ANALYSIS_PROMPT,
    WEAKNESS_ANALYSIS_PROMPT,
)
from ..core import invoke_json, llm_enabled
from ..state.state import (
    SwotItem,
    AnalysisGraphState,
    CategoryAnalysisState,
    ComparativeSwotState,
    ComparativePoint,
    EnrichedSwotItem,
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _extract_swot_by_category(
    swot_data: Any,
    category: str
) -> List[Dict[str, Any]]:
    """Extract SWOT items for specific category from either dict- or list-based inputs."""
    if isinstance(swot_data, Mapping):
        items = swot_data.get(category, [])
        return [dict(item) for item in items if isinstance(item, Mapping)]

    if isinstance(swot_data, list):
        return [
            dict(item) for item in swot_data
            if isinstance(item, Mapping) and item.get("category") == category
        ]

    return []


def _normalize_swot_item(item: Dict[str, Any]) -> SwotItem:
    """Normalize raw SWOT item to standard format."""
    return SwotItem(
        point=item.get("point", ""),
        evidence=item.get("evidence", ""),
        source=item.get("source", "unknown")
    )


def _enrich_swot_items(
    items: List[Dict[str, Any]],
    portfolio: Mapping[str, Any],
    market_context: Any
) -> List[EnrichedSwotItem]:
    """
    Enrich SWOT items with strategic context.
    
    Adds why_it_matters and impact based on portfolio and market context.
    """
    enriched = []
    for item in items:
        normalized = _normalize_swot_item(item)
        
        # Determine impact based on portfolio relevance
        impact = "medium"
        if portfolio:
            portfolio_keys = set(portfolio.keys())
            item_point = normalized["point"].lower()
            
            # Simple heuristic: if item mentions portfolio categories, increase impact
            if any(key.lower() in item_point for key in portfolio_keys):
                impact = "high"
            elif "critical" in item_point or "strategic" in item_point:
                impact = "high"
        
        why_it_matters = (
            f"In EV chasm recovery context, this {impact}-impact factor shapes "
            "competitive positioning and recovery trajectory"
        )
        
        enriched.append(
            EnrichedSwotItem(
                point=normalized["point"],
                evidence=normalized["evidence"],
                why_it_matters=why_it_matters,
                impact=impact,
            )
        )
    
    return enriched


def _market_context_to_text(market_context: Any) -> str:
    """Flatten MarketContext into a short string for prompt-like reasoning."""
    if isinstance(market_context, str):
        return market_context

    if isinstance(market_context, Mapping):
        parts = [str(value).strip() for value in market_context.values() if value]
        return " | ".join(parts)

    return ""


def _coerce_category_state(value: Any) -> Dict[str, Any]:
    """Normalize a category node output into CategoryAnalysisState-like dict."""
    if isinstance(value, Mapping):
        return dict(value)

    if isinstance(value, list):
        return {
            "lges_items": value,
            "catl_items": [],
            "comparative_points": [],
            "strategic_implications": [],
        }

    return {
        "lges_items": [],
        "catl_items": [],
        "comparative_points": [],
        "strategic_implications": [],
    }


def _coerce_enriched_item(item: Mapping[str, Any]) -> EnrichedSwotItem:
    return EnrichedSwotItem(
        point=str(item.get("point", "")),
        evidence=str(item.get("evidence", "")),
        why_it_matters=str(item.get("why_it_matters", "")),
        impact=str(item.get("impact", "medium")),
    )


def _coerce_comparative_point(item: Mapping[str, Any]) -> ComparativePoint:
    return ComparativePoint(
        dimension=str(item.get("dimension", "")),
        lges_position=str(item.get("lges_position", "")),
        catl_position=str(item.get("catl_position", "")),
        relative_advantage=str(item.get("relative_advantage", "balanced")),
    )


def _coerce_category_analysis_result(payload: Mapping[str, Any]) -> CategoryAnalysisState:
    return {
        "lges_items": [
            _coerce_enriched_item(item) for item in payload.get("lges_items", []) if isinstance(item, Mapping)
        ],
        "catl_items": [
            _coerce_enriched_item(item) for item in payload.get("catl_items", []) if isinstance(item, Mapping)
        ],
        "comparative_points": [
            _coerce_comparative_point(item)
            for item in payload.get("comparative_points", [])
            if isinstance(item, Mapping)
        ],
        "strategic_implications": [str(item) for item in payload.get("strategic_implications", [])],
    }


def _coerce_comparative_swot_result(payload: Mapping[str, Any]) -> ComparativeSwotState:
    def _coerce_matrix(matrix_value: Any) -> Dict[str, List[EnrichedSwotItem]]:
        if not isinstance(matrix_value, Mapping):
            return {"S": [], "W": [], "O": [], "T": []}
        matrix: Dict[str, List[EnrichedSwotItem]] = {}
        for category in ("S", "W", "O", "T"):
            raw_items = matrix_value.get(category, [])
            matrix[category] = [
                _coerce_enriched_item(item) for item in raw_items if isinstance(item, Mapping)
            ]
        return matrix

    return {
        "lges_matrix": _coerce_matrix(payload.get("lges_matrix", {})),
        "catl_matrix": _coerce_matrix(payload.get("catl_matrix", {})),
        "comparative_summary": str(payload.get("comparative_summary", "")),
        "strategic_positioning": str(payload.get("strategic_positioning", "")),
    }


def _build_category_prompt_payload(
    state: AnalysisGraphState,
    category: str,
) -> Dict[str, Any]:
    return {
        "category": category,
        "company_a_swot": _extract_swot_by_category(state.get("company_a_swot", {}), category),
        "company_b_swot": _extract_swot_by_category(state.get("company_b_swot", {}), category),
        "company_a_portfolio": state.get("company_a_portfolio", {}),
        "company_b_portfolio": state.get("company_b_portfolio", {}),
        "market_context": state.get("market_context", {}),
    }


def _invoke_category_llm(prompt: str, state: AnalysisGraphState, category: str) -> CategoryAnalysisState | None:
    payload = _build_category_prompt_payload(state, category)
    response = invoke_json(prompt, payload)
    if not response:
        return None
    return _coerce_category_analysis_result(response)


def _invoke_comparative_swot_llm(state: AnalysisGraphState) -> ComparativeSwotState | None:
    payload = {
        "swot_S": state.get("swot_S", {}),
        "swot_W": state.get("swot_W", {}),
        "swot_O": state.get("swot_O", {}),
        "swot_T": state.get("swot_T", {}),
    }
    response = invoke_json(
        """
Integrate SWOT category analyses into a ComparativeSwotState JSON object.
Return only valid JSON.
""",
        payload,
    )
    if not response:
        return None
    return _coerce_comparative_swot_result(response)


def _invoke_resilience_llm(state: AnalysisGraphState) -> Mapping[str, Any] | None:
    response = invoke_json(
        RESILIENCE_EVALUATION_PROMPT,
        {"comparative_swot": state.get("comparative_swot", {})},
    )
    if not response:
        return None
    return {
        "total_score_lges": float(response.get("total_score_lges", 0.0)),
        "total_score_catl": float(response.get("total_score_catl", 0.0)),
        "winner": str(response.get("winner", "Tie")),
        "evaluation_summary": str(response.get("evaluation_summary", "")),
        "evaluation_factors": [str(item) for item in response.get("evaluation_factors", [])],
    }


def _invoke_insight_llm(state: AnalysisGraphState) -> Mapping[str, Any] | None:
    response = invoke_json(
        INSIGHT_PROMPT,
        {
            "comparative_swot": state.get("comparative_swot", {}),
            "final_insight": state.get("final_insight", {}),
            "raw_findings": state.get("raw_findings", []),
        },
    )
    if not response:
        return None
    return {
        "key_differences": [str(item) for item in response.get("key_differences", [])],
        "strategic_winner": str(response.get("strategic_winner", "Unknown")),
        "final_insights": [str(item) for item in response.get("final_insights", [])],
    }


def _invoke_validation_llm(state: AnalysisGraphState) -> List[str] | None:
    response = invoke_json(
        CROSS_VALIDATION_PROMPT,
        {
            "final_insight": state.get("final_insight", {}),
            "comparative_swot": state.get("comparative_swot", {}),
            "raw_findings": state.get("raw_findings", []),
        },
    )
    if not response:
        return None
    return [str(item) for item in response.get("validation_notes", [])]


def _invoke_human_review_llm(state: AnalysisGraphState) -> str | None:
    response = invoke_json(
        HUMAN_REVIEW_PROMPT,
        {
            "final_insight": state.get("final_insight", {}),
            "comparative_swot": state.get("comparative_swot", {}),
            "consistency_flags": state.get("consistency_flags", []),
        },
    )
    review_status = str(response.get("review_status", "")) if response else ""
    return review_status if review_status in {"approved", "review_required"} else None


def _raw_findings_to_text(raw_findings: Any) -> str:
    """Collect lightweight evidence text from either list- or dict-based raw findings."""
    if isinstance(raw_findings, list):
        chunks = []
        for finding in raw_findings:
            if not isinstance(finding, Mapping):
                continue
            raw_content = str(finding.get("raw_content", "")).strip()
            key_points = " ".join(str(point) for point in finding.get("key_points", []))
            chunks.append(f"{raw_content} {key_points}".strip())
        return " ".join(chunks).strip()

    if isinstance(raw_findings, Mapping):
        chunks = []
        raw_content = raw_findings.get("raw_content")
        if raw_content:
            chunks.append(str(raw_content))
        key_points = raw_findings.get("key_points", [])
        if isinstance(key_points, list):
            chunks.append(" ".join(str(point) for point in key_points))
        for value in raw_findings.values():
            if isinstance(value, Mapping):
                nested_swot = value.get("swot", [])
                if isinstance(nested_swot, list):
                    chunks.extend(str(item.get("point", "")) for item in nested_swot if isinstance(item, Mapping))
        return " ".join(part for part in chunks if part).strip()

    return ""


def _coverage_check_notes(final_insight: Mapping[str, Any], raw_text: str) -> List[str]:
    """Validate whether key report-level criteria are visible in Task 3 outputs."""
    notes: List[str] = []
    final_text = " ".join(
        [*final_insight.get("key_differences", []), *final_insight.get("final_insights", [])]
    ).lower()
    combined = f"{final_text} {raw_text.lower()}".strip()

    keyword_checks = {
        "기술 비교 근거": ["energy density", "charging", "cycle", "technology", "technical"],
        "경제 비교 근거": ["cost", "share", "backlog", "margin", "economic"],
        "중장기 전망": ["2026", "2027", "long-term", "outlook"],
        "국내 산업 시사점": ["korea", "domestic", "industry", "supply chain"],
    }

    for label, keywords in keyword_checks.items():
        if any(keyword in combined for keyword in keywords):
            notes.append(f"✓ {label} 언급 확인")
        else:
            notes.append(f"⚠ {label} 언급이 약함")

    return notes


def _analyze_swot_category(
    category: str,
    company_a_swot: Any,
    company_b_swot: Any,
    company_a_portfolio: Mapping[str, Any],
    company_b_portfolio: Mapping[str, Any],
    market_context: Any
) -> CategoryAnalysisState:
    """
    Unified SWOT category analysis for both companies.
    
    Shared logic for all 4 SWOT nodes (strength_analysis, weakness_analysis, etc.)
    """
    # Extract items for this category
    company_a_items = _extract_swot_by_category(company_a_swot, category)
    company_b_items = _extract_swot_by_category(company_b_swot, category)
    
    # Enrich items with context
    market_context_text = _market_context_to_text(market_context)
    lges_enriched = _enrich_swot_items(company_a_items, company_a_portfolio, market_context_text)
    catl_enriched = _enrich_swot_items(company_b_items, company_b_portfolio, market_context_text)
    
    # Build comparative points (simple rule-based comparison)
    comparative_points: List[ComparativePoint] = []
    
    if len(lges_enriched) > len(catl_enriched):
        comparative_points.append(
            ComparativePoint(
                dimension=f"{category} quantity",
                lges_position=f"{len(lges_enriched)} items",
                catl_position=f"{len(catl_enriched)} items",
                relative_advantage="LGES_leads",
            )
        )
    elif len(catl_enriched) > len(lges_enriched):
        comparative_points.append(
            ComparativePoint(
                dimension=f"{category} quantity",
                lges_position=f"{len(lges_enriched)} items",
                catl_position=f"{len(catl_enriched)} items",
                relative_advantage="CATL_leads",
            )
        )
    
    # Generate strategic implications
    strategic_implications = []
    if category == "S":
        strategic_implications.append(
            "Strengths form the foundation for competitive differentiation in chasm recovery"
        )
    elif category == "W":
        strategic_implications.append(
            "Weaknesses represent vulnerability areas requiring immediate mitigation"
        )
    elif category == "O":
        strategic_implications.append(
            "Opportunities indicate growth vectors and portfolio expansion potential"
        )
    elif category == "T":
        strategic_implications.append(
            "Threats signal external pressures and competitive recovery challenges"
        )
    
    return {
        "lges_items": lges_enriched,
        "catl_items": catl_enriched,
        "comparative_points": comparative_points,
        "strategic_implications": strategic_implications,
    }


def _validate_swot_category(category_analysis: CategoryAnalysisState) -> tuple:
    """
    Validate SWOT category analysis consistency.
    
    Returns: (is_valid, warnings_local)
    """
    warnings_local = []
    
    # Check for empty categories
    if not category_analysis.get("lges_items") and not category_analysis.get("catl_items"):
        warnings_local.append("Both companies lack items in this category")
    
    # Check for extreme imbalance
    lges_count = len(category_analysis.get("lges_items", []))
    catl_count = len(category_analysis.get("catl_items", []))
    
    if lges_count > 0 and catl_count > 0:
        ratio = max(lges_count, catl_count) / min(lges_count, catl_count)
        if ratio > 5:
            warnings_local.append(f"Large imbalance detected (ratio {ratio:.1f}:1)")
    
    is_valid = len(warnings_local) == 0
    return is_valid, warnings_local


def _extract_key_differences(comparative_swot: ComparativeSwotState) -> List[str]:
    """
    Extract 3-5 key behavioral differences from SWOT asymmetry.
    
    LOCAL PROCESSING ONLY - returns list of strings for final_insight.
    """
    lges_matrix = comparative_swot.get("lges_matrix", {})
    catl_matrix = comparative_swot.get("catl_matrix", {})
    
    differences = []
    
    # Analyze SWOT balance
    lges_balance = {
        "strengths": len(lges_matrix.get("S", [])),
        "weaknesses": len(lges_matrix.get("W", [])),
        "opportunities": len(lges_matrix.get("O", [])),
        "threats": len(lges_matrix.get("T", []))
    }
    
    catl_balance = {
        "strengths": len(catl_matrix.get("S", [])),
        "weaknesses": len(catl_matrix.get("W", [])),
        "opportunities": len(catl_matrix.get("O", [])),
        "threats": len(catl_matrix.get("T", []))
    }
    
    # Generate differences (rule-based)
    if lges_balance["strengths"] > catl_balance["strengths"]:
        differences.append(
            f"LGES has superior operational strengths "
            f"({lges_balance['strengths']} vs {catl_balance['strengths']})"
        )
    
    if catl_balance["opportunities"] > lges_balance["opportunities"]:
        differences.append(
            f"CATL identifies more market opportunities "
            f"({catl_balance['opportunities']} vs {lges_balance['opportunities']})"
        )
    
    if lges_balance["weaknesses"] < catl_balance["weaknesses"]:
        differences.append(
            f"LGES has fewer structural weaknesses "
            f"({lges_balance['weaknesses']} vs {catl_balance['weaknesses']})"
        )
    
    if catl_balance["threats"] < lges_balance["threats"]:
        differences.append(
            f"CATL faces fewer external threats "
            f"({catl_balance['threats']} vs {lges_balance['threats']})"
        )
    
    # Ensure we return 3-5 items
    if len(differences) < 3:
        differences.append("Both companies show balanced competitive positioning in EV chasm recovery")
    
    return differences[:5]


def _generate_final_insights(
    comparative_swot: ComparativeSwotState,
    resilience_eval: Mapping[str, Any]
) -> List[str]:
    """
    Generate 4 scenario-based final insights.
    
    LOCAL PROCESSING ONLY - returns list of strings for final_insight.
    """
    winner_local = resilience_eval.get("winner", "Unknown")
    lges_score = resilience_eval.get("total_score_lges", 50)
    catl_score = resilience_eval.get("total_score_catl", 50)
    
    insights = []
    
    # Insight 1: Winner
    if winner_local == "LGES":
        insights.append(
            f"LGES demonstrates superior EV chasm recovery resilience "
            f"({lges_score:.1f} vs {catl_score:.1f}). Recommend accelerating "
            "portfolio diversification while leveraging operational strengths."
        )
    elif winner_local == "CATL":
        insights.append(
            f"CATL shows competitive advantage in resilience metrics "
            f"({catl_score:.1f} vs {lges_score:.1f}). Strategic opportunities in "
            "market positioning require expedited execution."
        )
    else:
        insights.append(
            f"Both companies show comparable resilience ({lges_score:.1f} vs {catl_score:.1f}). "
            "Differentiation will depend on execution speed and portfolio optimization."
        )
    
    # Insight 2: Portfolio strategy
    lges_opportunities = len(comparative_swot.get("lges_matrix", {}).get("O", []))
    catl_opportunities = len(comparative_swot.get("catl_matrix", {}).get("O", []))
    
    if lges_opportunities > catl_opportunities:
        insights.append(
            "LGES should capitalize on identified market opportunities to strengthen "
            "recovery trajectory. Opportunity window in EV chasm phase is time-limited."
        )
    else:
        insights.append(
            "CATL has more identified growth opportunities. Rapid execution of opportunity-based "
            "initiatives critical for competitive differentiation."
        )
    
    # Insight 3: Risk mitigation
    lges_threats = len(comparative_swot.get("lges_matrix", {}).get("T", []))
    catl_threats = len(comparative_swot.get("catl_matrix", {}).get("T", []))
    
    if lges_threats > catl_threats:
        insights.append(
            f"LGES faces elevated external threats ({lges_threats} identified). "
            "Defensive positioning and threat mitigation strategies should be prioritized."
        )
    else:
        insights.append(
            f"CATL faces elevated external threats ({catl_threats} identified). "
            "Proactive threat monitoring and contingency planning essential."
        )
    
    # Insight 4: Long-term trajectory
    insights.append(
        "Success in EV chasm recovery phase depends on balancing aggressive growth "
        "(opportunities) with defensive risk management (threat mitigation). Both "
        "companies must adjust portfolio strategy to changing competitive dynamics."
    )
    
    return insights[:4]


def _check_overconfident_language(insight_text: str) -> List[str]:
    """
    Detect absolute/overconfident language in insights.
    
    LOCAL PROCESSING ONLY - returns warnings for logging only, never added to state.
    """
    warnings_local = []
    
    absolute_phrases = ["definitely", "absolutely", "certainly", "guaranteed", "100%", "must"]
    insight_lower = insight_text.lower()
    
    for phrase in absolute_phrases:
        if phrase in insight_lower:
            warnings_local.append(f"Overconfident language detected: '{phrase}'")
    
    return warnings_local


def _check_evidence_sparsity(insight_text: str, raw_text: str) -> List[str]:
    """
    Check if insights are supported by raw findings.
    
    LOCAL PROCESSING ONLY - returns warnings for logging only.
    """
    warnings_local = []
    
    keywords = ["LGES", "CATL", "EV", "chasm", "battery", "portfolio"]
    found_keywords = [kw for kw in keywords if kw in insight_text or kw in raw_text]
    
    if len(found_keywords) < 2:
        warnings_local.append("Sparse keyword coverage in raw findings")
    
    return warnings_local


def _validate_final_insight_structure(final_insight: Mapping[str, Any]) -> Dict[str, bool]:
    """
    Validate final_insight has required structure.
    
    Required fields:
        - resilience_evaluation (required)
        - key_differences (required)
        - strategic_winner (required)
        - final_insights (required)
        - validation_notes (optional)
    
    Returns: dict with validation flags and is_valid status
    """
    validation_result = {
        "has_resilience_evaluation": "resilience_evaluation" in final_insight,
        "has_key_differences": "key_differences" in final_insight,
        "has_strategic_winner": "strategic_winner" in final_insight,
        "has_final_insights": "final_insights" in final_insight,
        "has_validation_notes": "validation_notes" in final_insight
    }
    
    # All required fields present?
    required_present = all([
        validation_result["has_resilience_evaluation"],
        validation_result["has_key_differences"],
        validation_result["has_strategic_winner"],
        validation_result["has_final_insights"]
    ])
    
    validation_result["is_valid"] = required_present
    return validation_result


def _validate_comparative_swot(comparative_swot: ComparativeSwotState) -> List[str]:
    """
    Validate comparative_swot matrix structure and content.
    
    Returns: List of validation notes/warnings (local processing only).
    """
    validation_notes = []
    
    lges_matrix = comparative_swot.get("lges_matrix", {})
    catl_matrix = comparative_swot.get("catl_matrix", {})
    
    if not lges_matrix or not catl_matrix:
        validation_notes.append("⚠ Missing SWOT matrix data (LGES or CATL)")
        return validation_notes
    
    # Check all categories present
    required_categories = {"S", "W", "O", "T"}
    lges_categories = set(lges_matrix.keys())
    catl_categories = set(catl_matrix.keys())
    
    if not lges_categories.issuperset(required_categories):
        missing = required_categories - lges_categories
        validation_notes.append(f"⚠ LGES missing categories: {', '.join(missing)}")
    
    if not catl_categories.issuperset(required_categories):
        missing = required_categories - catl_categories
        validation_notes.append(f"⚠ CATL missing categories: {', '.join(missing)}")
    
    # Check for empty categories
    for category in required_categories:
        lges_count = len(lges_matrix.get(category, []))
        catl_count = len(catl_matrix.get(category, []))
        
        if lges_count == 0 and catl_count == 0:
            validation_notes.append(f"⚠ Empty category '{category}' in both companies")
        
        # Check for extreme imbalance
        if lges_count > 0 and catl_count > 0:
            ratio = max(lges_count, catl_count) / min(lges_count, catl_count)
            if ratio > 4:
                validation_notes.append(
                    f"⚠ Extreme {category} imbalance: LGES {lges_count} vs CATL {catl_count} (ratio {ratio:.1f})"
                )
    
    # Check enriched item quality (spot check)
    all_items_lges = [item for items in lges_matrix.values() for item in items]
    all_items_catl = [item for items in catl_matrix.values() for item in items]
    
    for company_name, items in [("LGES", all_items_lges), ("CATL", all_items_catl)]:
        required_fields = {"point", "evidence", "why_it_matters", "impact"}
        for idx, item in enumerate(items[:3]):  # Spot check first 3 items
            item_fields = set(item.keys())
            missing_fields = required_fields - item_fields
            if missing_fields:
                validation_notes.append(
                    f"⚠ {company_name} item {idx} missing fields: {', '.join(missing_fields)}"
                )
    
    if not validation_notes:
        validation_notes.append("✓ SWOT matrix validation passed")
    
    return validation_notes


# ============================================================================
# PARALLEL SWOT ANALYSIS NODES
# ============================================================================

def strength_analysis_node(state: AnalysisGraphState) -> Dict[str, CategoryAnalysisState]:
    """
    Analyze and compare STRENGTHS between LGES (company_a) and CATL (company_b).
    
    Thin wrapper around _analyze_swot_category with S category.
    
    Reads:
        - company_a_swot, company_b_swot: SWOT item lists
        - company_a_portfolio, company_b_portfolio: Portfolio composition
        - market_context: EV chasm phase context
    
    Writes:
        - swot_S: Comparative strengths analysis with enriched context
    """
    llm_result = _invoke_category_llm(STRENGTH_ANALYSIS_PROMPT, state, "S") if llm_enabled() else None
    result = llm_result or _analyze_swot_category(
        category="S",
        company_a_swot=state.get("company_a_swot", []),
        company_b_swot=state.get("company_b_swot", []),
        company_a_portfolio=state.get("company_a_portfolio", {}),
        company_b_portfolio=state.get("company_b_portfolio", {}),
        market_context=state.get("market_context", "")
    )
    return {"swot_S": result}


def weakness_analysis_node(state: AnalysisGraphState) -> Dict[str, CategoryAnalysisState]:
    """
    Analyze and compare WEAKNESSES between LGES and CATL.
    
    Thin wrapper around _analyze_swot_category with W category.
    
    Writes:
        - swot_W: Comparative weaknesses analysis
    """
    llm_result = _invoke_category_llm(WEAKNESS_ANALYSIS_PROMPT, state, "W") if llm_enabled() else None
    result = llm_result or _analyze_swot_category(
        category="W",
        company_a_swot=state.get("company_a_swot", []),
        company_b_swot=state.get("company_b_swot", []),
        company_a_portfolio=state.get("company_a_portfolio", {}),
        company_b_portfolio=state.get("company_b_portfolio", {}),
        market_context=state.get("market_context", "")
    )
    return {"swot_W": result}


def opportunity_analysis_node(state: AnalysisGraphState) -> Dict[str, CategoryAnalysisState]:
    """
    Analyze and compare OPPORTUNITIES between LGES and CATL.
    
    Thin wrapper around _analyze_swot_category with O category.
    
    Writes:
        - swot_O: Comparative opportunities analysis
    """
    llm_result = _invoke_category_llm(OPPORTUNITY_ANALYSIS_PROMPT, state, "O") if llm_enabled() else None
    result = llm_result or _analyze_swot_category(
        category="O",
        company_a_swot=state.get("company_a_swot", []),
        company_b_swot=state.get("company_b_swot", []),
        company_a_portfolio=state.get("company_a_portfolio", {}),
        company_b_portfolio=state.get("company_b_portfolio", {}),
        market_context=state.get("market_context", "")
    )
    return {"swot_O": result}


def threat_analysis_node(state: AnalysisGraphState) -> Dict[str, CategoryAnalysisState]:
    """
    Analyze and compare THREATS between LGES and CATL.
    
    Thin wrapper around _analyze_swot_category with T category.
    
    Writes:
        - swot_T: Comparative threats analysis
    """
    llm_result = _invoke_category_llm(THREAT_ANALYSIS_PROMPT, state, "T") if llm_enabled() else None
    result = llm_result or _analyze_swot_category(
        category="T",
        company_a_swot=state.get("company_a_swot", []),
        company_b_swot=state.get("company_b_swot", []),
        company_a_portfolio=state.get("company_a_portfolio", {}),
        company_b_portfolio=state.get("company_b_portfolio", {}),
        market_context=state.get("market_context", "")
    )
    return {"swot_T": result}


# ============================================================================
# SEQUENTIAL INTEGRATION & EVALUATION NODES
# ============================================================================

def context_integration_node(state: AnalysisGraphState) -> Dict[str, ComparativeSwotState]:
    """
    Integrate all 4 SWOT categories into unified comparative matrix.
    
    Reads:
        - swot_S, swot_W, swot_O, swot_T: Individual SWOT analyses (enriched)
        - company_a_portfolio, company_b_portfolio: Portfolio info
    
    Writes:
        - comparative_swot: Unified SWOT matrix with strategic positioning
    """
    swot_s = _coerce_category_state(state.get("swot_S", {}))
    swot_w = _coerce_category_state(state.get("swot_W", {}))
    swot_o = _coerce_category_state(state.get("swot_O", {}))
    swot_t = _coerce_category_state(state.get("swot_T", {}))
    
    llm_result = _invoke_comparative_swot_llm(state) if llm_enabled() else None
    if llm_result:
        return {"comparative_swot": llm_result}

    # Build LGES matrix with enriched items
    lges_matrix = {
        "S": swot_s.get("lges_items", []),
        "W": swot_w.get("lges_items", []),
        "O": swot_o.get("lges_items", []),
        "T": swot_t.get("lges_items", [])
    }
    
    # Build CATL matrix with enriched items
    catl_matrix = {
        "S": swot_s.get("catl_items", []),
        "W": swot_w.get("catl_items", []),
        "O": swot_o.get("catl_items", []),
        "T": swot_t.get("catl_items", [])
    }
    
    # Count items per category
    lges_total = sum(len(items) for items in lges_matrix.values())
    catl_total = sum(len(items) for items in catl_matrix.values())
    
    # Generate strategic positioning summary (local only)
    comparative_summary_local = (
        f"Comparative analysis: LGES ({lges_total} factors) vs CATL ({catl_total} factors). "
        "EV chasm recovery phase requires balanced growth and risk management."
    )
    
    strategic_positioning_local = (
        "LGES and CATL pursue divergent recovery strategies. "
        "Success depends on portfolio optimization and threat mitigation."
    )
    
    return {
        "comparative_swot": {
            "lges_matrix": lges_matrix,
            "catl_matrix": catl_matrix,
            "comparative_summary": comparative_summary_local,
            "strategic_positioning": strategic_positioning_local,
        }
    }


def resilience_evaluation_node(state: AnalysisGraphState) -> Dict[str, Any]:
    """
    Evaluate strategic resilience in EV chasm recovery phase.
    
    CRITICAL STATE CONTRACT:
    - Does NOT create separate "resilience_score" field
    - Returns resilience_evaluation NESTED INSIDE final_insight
    
    Reads:
        - comparative_swot: SWOT matrix
    
    Writes:
        - final_insight: Contains resilience_evaluation (and will be extended by insight_node)
    """
    llm_result = _invoke_resilience_llm(state) if llm_enabled() else None
    comparative_swot = state.get("comparative_swot", {})
    
    # All processing is LOCAL - never stored as separate state field
    lges_matrix = comparative_swot.get("lges_matrix", {})
    catl_matrix = comparative_swot.get("catl_matrix", {})
    
    lges_counts = {
        "S": len(lges_matrix.get("S", [])),
        "W": len(lges_matrix.get("W", [])),
        "O": len(lges_matrix.get("O", [])),
        "T": len(lges_matrix.get("T", []))
    }
    
    catl_counts = {
        "S": len(catl_matrix.get("S", [])),
        "W": len(catl_matrix.get("W", [])),
        "O": len(catl_matrix.get("O", [])),
        "T": len(catl_matrix.get("T", []))
    }
    
    # Calculate local resilience scores (not stored separately)
    lges_positive = lges_counts["S"] + lges_counts["O"]
    lges_negative = lges_counts["W"] + lges_counts["T"]
    lges_score_local = (lges_positive / (lges_negative + 1.0)) * 50 + 50
    lges_score_local = min(100, max(0, lges_score_local))
    
    catl_positive = catl_counts["S"] + catl_counts["O"]
    catl_negative = catl_counts["W"] + catl_counts["T"]
    catl_score_local = (catl_positive / (catl_negative + 1.0)) * 50 + 50
    catl_score_local = min(100, max(0, catl_score_local))
    
    # Determine winner (local logic)
    score_diff = abs(lges_score_local - catl_score_local)
    if score_diff < 5:
        winner_local = "Tie"
    elif lges_score_local > catl_score_local:
        winner_local = "LGES"
    else:
        winner_local = "CATL"
    
    evaluation_factors_local = [
        f"LGES: {lges_positive}:{lges_negative} vs CATL: {catl_positive}:{catl_negative}",
        "Adaptive resilience in EV chasm recovery phase"
    ]
    
    # Build resilience_evaluation (nested in final_insight)
    resilience_eval_nested = llm_result or {
        "total_score_lges": round(lges_score_local, 1),
        "total_score_catl": round(catl_score_local, 1),
        "winner": winner_local,
        "evaluation_summary": (
            f"LGES ({lges_score_local:.1f}) vs CATL ({catl_score_local:.1f}). "
            f"Winner: {winner_local}. Diff: {score_diff:.1f} pts."
        ),
        "evaluation_factors": evaluation_factors_local
    }
    
    # Return ONLY final_insight with resilience_evaluation nested inside
    return {
        "final_insight": {
            **state.get("final_insight", {}),
            "resilience_evaluation": resilience_eval_nested,
        }
    }


def insight_node(state: AnalysisGraphState) -> Dict[str, Any]:
    """
    Generate strategic insights and populate final_insight.
    
    CRITICAL STATE CONTRACT:
    - Updates existing final_insight (preserves resilience_evaluation from prior node)
    - Does NOT create separate "preliminary_insight" field
    - Adds: key_differences, strategic_winner, final_insights
    
    Reads:
        - final_insight: Contains resilience_evaluation from prior node
        - comparative_swot: SWOT matrix data
        - raw_findings: For context (read-only)
    
    Writes:
        - final_insight: Extended with key_differences, strategic_winner, final_insights
    """
    # MERGE STRATEGY: Preserve existing final_insight, add new fields
    existing = state.get("final_insight", {})
    comparative_swot = state.get("comparative_swot", {})
    
    llm_result = _invoke_insight_llm(state) if llm_enabled() else None

    # Local processing: extract differences
    key_differences = _extract_key_differences(comparative_swot)
    
    # Get resilience eval (set by prior node)
    resilience_eval = existing.get("resilience_evaluation", {})
    strategic_winner = resilience_eval.get("winner", "Unknown")
    
    # Local processing: generate insights
    final_insights = _generate_final_insights(comparative_swot, resilience_eval)

    if llm_result:
        key_differences = list(llm_result.get("key_differences", key_differences))[:5]
        strategic_winner = str(llm_result.get("strategic_winner", strategic_winner))
        final_insights = list(llm_result.get("final_insights", final_insights))[:4]
    
    # MERGE: Combine existing data with new fields (NO OVERWRITE)
    return {
        "final_insight": {
            **existing,
            "key_differences": key_differences,
            "strategic_winner": strategic_winner,
            "final_insights": final_insights
        }
    }


def cross_validation_node(state: AnalysisGraphState) -> Dict[str, Any]:
    """
    Cross-validate final_insight and comparative_swot against raw_findings.
    
    CRITICAL STATE CONTRACT (AnalysisGraphState):
    - Does NOT add validation_result field to state
    - Raw findings: read-only (no modification)
    - Comparative SWOT: read-only (no modification)
    - Validation notes stored INSIDE final_insight (merge strategy)
    
    Reads:
        - final_insight: Strategic insights for validation (read-only)
        - comparative_swot: SWOT matrix for validation (read-only)
        - raw_findings: Evidence source (read-only)
    
    Writes:
        - final_insight: Updated with validation_notes field (merge, no overwrite)
    """
    # Get existing data (read-only)
    existing_final_insight = state.get("final_insight", {})
    comparative_swot = state.get("comparative_swot", {})
    raw_findings = state.get("raw_findings", {})
    
    # LOCAL PROCESSING: Validate SWOT matrix structure
    validation_notes = _validate_comparative_swot(comparative_swot)
    
    # LOCAL PROCESSING: Validate insights against raw findings
    raw_text_local = _raw_findings_to_text(raw_findings)
    
    final_insights_local = existing_final_insight.get("final_insights", [])
    for insight in final_insights_local:
        validation_notes.extend(_check_overconfident_language(insight))
        validation_notes.extend(_check_evidence_sparsity(insight, raw_text_local))

    validation_notes.extend(_coverage_check_notes(existing_final_insight, raw_text_local))

    llm_validation_notes = _invoke_validation_llm(state) if llm_enabled() else None
    if llm_validation_notes:
        validation_notes.extend(llm_validation_notes)
    
    # LOCAL PROCESSING: Add summary note
    if validation_notes:
        total_notes = len(validation_notes)
        passed = sum(1 for note in validation_notes if note.startswith("✓"))
        validation_notes.append(
            f"Validation Complete: {passed} checks passed, {total_notes - passed} warnings"
        )
    
    # MERGE STRATEGY: Store validation_notes in final_insight (NO OVERWRITE)
    return {
        "final_insight": {
            **existing_final_insight,  # Preserve all existing fields
            "validation_notes": validation_notes
        }
    }


def human_review_node(state: AnalysisGraphState) -> Dict[str, str]:
    """
    Determine if final_insight requires review before dispatch.
    
    CRITICAL STATE CONTRACT:
    - Returns ONLY review_status field for routing
    - Does NOT add review_feedback or other fields to state
    
    Writes:
        - review_status: "approved" or "review_required"
    """
    llm_review_status = _invoke_human_review_llm(state) if llm_enabled() else None
    if llm_review_status:
        return {"review_status": llm_review_status}

    final_insight = state.get("final_insight", {})
    validation_notes = final_insight.get("validation_notes") or []
    consistency_flags = state.get("consistency_flags", [])

    required_fields = [
        "resilience_evaluation",
        "key_differences",
        "strategic_winner",
        "final_insights",
    ]
    missing_fields = [field for field in required_fields if not final_insight.get(field)]

    has_warning = any(str(note).startswith("⚠") for note in validation_notes)
    review_status_local = "review_required" if has_warning or consistency_flags or missing_fields else "approved"
    
    return {"review_status": review_status_local}


def dispatch_node(state: AnalysisGraphState) -> Dict[str, Any]:
    """
    Package analysis results for next stage (Report generation).
    
    CRITICAL STATE CONTRACT - Returns exactly 6 fields:
        1. swot_S: Strength analysis
        2. swot_W: Weakness analysis
        3. swot_O: Opportunity analysis
        4. swot_T: Threat analysis
        5. comparative_swot: Unified SWOT matrix
        6. final_insight: Complete strategic insight
    
    final_insight structure (guaranteed):
        - resilience_evaluation: Required
        - key_differences: Required
        - strategic_winner: Required
        - final_insights: Required
        - validation_notes: Optional
    
    Returns:
        Dict with exactly 6 fields for next stage
    """
    # Validate final_insight structure before dispatch
    final_insight = state.get("final_insight", {})
    structure_check = _validate_final_insight_structure(final_insight)
    
    if not structure_check["is_valid"]:
        # Identify missing fields
        missing_fields = []
        if not structure_check["has_resilience_evaluation"]:
            missing_fields.append("resilience_evaluation")
        if not structure_check["has_key_differences"]:
            missing_fields.append("key_differences")
        if not structure_check["has_strategic_winner"]:
            missing_fields.append("strategic_winner")
        if not structure_check["has_final_insights"]:
            missing_fields.append("final_insights")
        
        raise ValueError(
            f"final_insight missing required fields for dispatch: {', '.join(missing_fields)}"
        )
    
    # Return EXACTLY 6 fields (state contract)
    dispatch_payload = {
        "swot_S": state.get("swot_S", {}),
        "swot_W": state.get("swot_W", {}),
        "swot_O": state.get("swot_O", {}),
        "swot_T": state.get("swot_T", {}),
        "comparative_swot": state.get("comparative_swot", {}),
        "final_insight": final_insight
    }
    
    # Verify exactly 6 keys
    if len(dispatch_payload) != 6:
        raise ValueError(
            f"dispatch_payload must have exactly 6 fields, got {len(dispatch_payload)}"
        )
    
    return dispatch_payload
