"""
Analysis Prompts for Task 3 (Analysis Phase)

This module contains prompt templates for LLM-based analysis nodes.
Each prompt is designed to replace the current rule-based logic while maintaining
the same state contract and responsibilities.

Current Status: These are string constants only. No API calls.
Future Integration: Import these prompts into analysis_nodes.py when switching to LLM-based analysis.

State Contract Reminder:
✓ Output fields: swot_S, swot_W, swot_O, swot_T, comparative_swot, final_insight
✗ PROHIBITED: resilience_score, validation_result, preliminary_insight, review_feedback,
              warnings, human_review_flags, review_status, any intermediate field
"""

# ============================================================================
# SWOT CATEGORY ANALYSIS PROMPTS
# ============================================================================

STRENGTH_ANALYSIS_PROMPT = """
Analyze STRENGTHS for both LGES and CATL in the EV battery market chasm recovery context.

INPUT DATA:
- company_a_swot: LGES SWOT items (list of dicts with 'point', 'evidence', 'source')
- company_b_swot: CATL SWOT items (list of dicts with 'point', 'evidence', 'source')
- company_a_portfolio: LGES portfolio composition
- company_b_portfolio: CATL portfolio composition
- market_context: EV chasm recovery phase description

YOUR TASK:
1. Extract STRENGTH items for both companies from their respective swot data
2. Enrich each strength with strategic context:
   - why_it_matters: Why this strength matters in chasm recovery
   - impact: "high", "medium", or "low" impact level
3. Compare strengths between companies and identify comparative advantages
4. Generate strategic implications for the STRENGTH category

OUTPUT FORMAT (JSON):
{
  "lges_items": [
    {
      "point": "strength description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "catl_items": [
    {
      "point": "strength description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "comparative_points": [
    {
      "dimension": "comparison aspect",
      "lges_position": "LGES position description",
      "catl_position": "CATL position description",
      "relative_advantage": "LGES_leads|CATL_leads|balanced"
    }
  ],
  "strategic_implications": [
    "implication statement 1",
    "implication statement 2"
  ]
}

CRITICAL CONSTRAINTS:
- ONLY analyze STRENGTHS category (S)
- DO NOT read or modify any other state fields
- DO NOT create intermediate state fields
- Output must be valid JSON matching CategoryAnalysisState structure
"""

WEAKNESS_ANALYSIS_PROMPT = """
Analyze WEAKNESSES for both LGES and CATL in the EV battery market chasm recovery context.

INPUT DATA:
- company_a_swot: LGES SWOT items
- company_b_swot: CATL SWOT items
- company_a_portfolio: LGES portfolio composition
- company_b_portfolio: CATL portfolio composition
- market_context: EV chasm recovery phase description

YOUR TASK:
1. Extract WEAKNESS items for both companies from their respective swot data
2. Enrich each weakness with strategic context:
   - why_it_matters: Why this weakness matters in chasm recovery
   - impact: "high", "medium", or "low" impact level
3. Compare weaknesses between companies and identify vulnerability differences
4. Generate strategic implications for the WEAKNESS category

OUTPUT FORMAT (JSON):
{
  "lges_items": [
    {
      "point": "weakness description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "catl_items": [
    {
      "point": "weakness description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "comparative_points": [
    {
      "dimension": "comparison aspect",
      "lges_position": "LGES position description",
      "catl_position": "CATL position description",
      "relative_advantage": "LGES_leads|CATL_leads|balanced"
    }
  ],
  "strategic_implications": [
    "implication statement 1",
    "implication statement 2"
  ]
}

CRITICAL CONSTRAINTS:
- ONLY analyze WEAKNESSES category (W)
- DO NOT read or modify any other state fields
- DO NOT create intermediate state fields
- Output must be valid JSON matching CategoryAnalysisState structure
"""

OPPORTUNITY_ANALYSIS_PROMPT = """
Analyze OPPORTUNITIES for both LGES and CATL in the EV battery market chasm recovery context.

INPUT DATA:
- company_a_swot: LGES SWOT items
- company_b_swot: CATL SWOT items
- company_a_portfolio: LGES portfolio composition
- company_b_portfolio: CATL portfolio composition
- market_context: EV chasm recovery phase description

YOUR TASK:
1. Extract OPPORTUNITY items for both companies from their respective swot data
2. Enrich each opportunity with strategic context:
   - why_it_matters: Why this opportunity matters in chasm recovery
   - impact: "high", "medium", or "low" impact level
3. Compare opportunities between companies and identify growth potential differences
4. Generate strategic implications for the OPPORTUNITY category

OUTPUT FORMAT (JSON):
{
  "lges_items": [
    {
      "point": "opportunity description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "catl_items": [
    {
      "point": "opportunity description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "comparative_points": [
    {
      "dimension": "comparison aspect",
      "lges_position": "LGES position description",
      "catl_position": "CATL position description",
      "relative_advantage": "LGES_leads|CATL_leads|balanced"
    }
  ],
  "strategic_implications": [
    "implication statement 1",
    "implication statement 2"
  ]
}

CRITICAL CONSTRAINTS:
- ONLY analyze OPPORTUNITIES category (O)
- DO NOT read or modify any other state fields
- DO NOT create intermediate state fields
- Output must be valid JSON matching CategoryAnalysisState structure
"""

THREAT_ANALYSIS_PROMPT = """
Analyze THREATS for both LGES and CATL in the EV battery market chasm recovery context.

INPUT DATA:
- company_a_swot: LGES SWOT items
- company_b_swot: CATL SWOT items
- company_a_portfolio: LGES portfolio composition
- company_b_portfolio: CATL portfolio composition
- market_context: EV chasm recovery phase description

YOUR TASK:
1. Extract THREAT items for both companies from their respective swot data
2. Enrich each threat with strategic context:
   - why_it_matters: Why this threat matters in chasm recovery
   - impact: "high", "medium", or "low" impact level
3. Compare threats between companies and identify risk exposure differences
4. Generate strategic implications for the THREAT category

OUTPUT FORMAT (JSON):
{
  "lges_items": [
    {
      "point": "threat description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "catl_items": [
    {
      "point": "threat description",
      "evidence": "supporting evidence",
      "why_it_matters": "strategic importance explanation",
      "impact": "high|medium|low"
    }
  ],
  "comparative_points": [
    {
      "dimension": "comparison aspect",
      "lges_position": "LGES position description",
      "catl_position": "CATL position description",
      "relative_advantage": "LGES_leads|CATL_leads|balanced"
    }
  ],
  "strategic_implications": [
    "implication statement 1",
    "implication statement 2"
  ]
}

CRITICAL CONSTRAINTS:
- ONLY analyze THREATS category (T)
- DO NOT read or modify any other state fields
- DO NOT create intermediate state fields
- Output must be valid JSON matching CategoryAnalysisState structure
"""

# ============================================================================
# INTEGRATION & SYNTHESIS PROMPTS
# ============================================================================

CONTEXT_INTEGRATION_PROMPT = """
Integrate all 4 SWOT category analyses into a unified comparative matrix.

INPUT DATA:
- swot_S: Strength analysis results (CategoryAnalysisState)
- swot_W: Weakness analysis results (CategoryAnalysisState)
- swot_O: Opportunity analysis results (CategoryAnalysisState)
- swot_T: Threat analysis results (CategoryAnalysisState)

YOUR TASK:
1. Combine all 4 category analyses into structured matrices:
   - lges_matrix: {"S": [...], "W": [...], "O": [...], "T": [...]}
   - catl_matrix: {"S": [...], "W": [...], "O": [...], "T": [...]}
2. Generate comparative summary highlighting key patterns
3. Assess strategic positioning based on SWOT balance

OUTPUT FORMAT (JSON):
{
  "lges_matrix": {
    "S": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}],
    "W": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}],
    "O": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}],
    "T": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}]
  },
  "catl_matrix": {
    "S": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}],
    "W": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}],
    "O": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}],
    "T": [{"point": "...", "evidence": "...", "why_it_matters": "...", "impact": "..."}]
  },
  "comparative_summary": "Overall comparison summary text",
  "strategic_positioning": "Strategic positioning assessment"
}

CRITICAL CONSTRAINTS:
- ONLY read swot_S, swot_W, swot_O, swot_T fields
- DO NOT modify any existing state fields
- DO NOT create intermediate state fields
- Output must be valid JSON matching ComparativeSwotState structure
"""

RESILIENCE_EVALUATION_PROMPT = """
Evaluate strategic resilience of LGES and CATL in EV chasm recovery phase.

INPUT DATA:
- comparative_swot: Unified SWOT matrix (ComparativeSwotState)

YOUR TASK:
1. Analyze SWOT balance and strategic positioning
2. Calculate resilience scores (0-100) for both companies
3. Determine winner based on comprehensive evaluation
4. Identify key evaluation factors and provide summary

OUTPUT FORMAT (JSON):
{
  "total_score_lges": 85.5,
  "total_score_catl": 79.2,
  "winner": "LGES",
  "evaluation_summary": "LGES shows stronger resilience with balanced portfolio...",
  "evaluation_factors": [
    "Portfolio diversification advantage",
    "Technology leadership in key segments",
    "Market position stability"
  ]
}

CRITICAL CONSTRAINTS:
- ONLY read comparative_swot field
- DO NOT modify any existing state fields
- DO NOT create intermediate state fields
- Output must be valid JSON matching ResilienceEvaluation structure
- This evaluation will be NESTED inside final_insight, not stored separately
"""

INSIGHT_PROMPT = """
Generate final strategic insights comparing LGES and CATL in EV chasm recovery.

INPUT DATA:
- comparative_swot: Unified SWOT matrix (ComparativeSwotState)
- final_insight (partial): May contain resilience_evaluation from previous step

YOUR TASK:
1. Extract 3-5 key behavioral differences from SWOT asymmetry
2. Determine strategic winner based on comprehensive analysis
3. Generate exactly 4 final strategic insights
4. If resilience_evaluation exists, incorporate it into analysis

OUTPUT FORMAT (JSON):
{
  "key_differences": [
    "LGES focuses on technology leadership while CATL emphasizes scale",
    "LGES shows stronger portfolio diversification",
    "CATL has advantages in cost optimization"
  ],
  "strategic_winner": "LGES",
  "final_insights": [
    "Insight statement 1",
    "Insight statement 2",
    "Insight statement 3",
    "Insight statement 4"
  ]
}

CRITICAL CONSTRAINTS:
- Read comparative_swot and existing final_insight (if any)
- DO NOT modify comparative_swot or other state fields
- DO NOT create intermediate state fields
- Output must be valid JSON that MERGES with existing final_insight
- Exactly 4 final_insights required
"""

CROSS_VALIDATION_PROMPT = """
Cross-validate final strategic insights against original research findings.

INPUT DATA:
- final_insight: Complete strategic insights (FinalInsight)
- comparative_swot: SWOT matrix for reference (read-only)
- raw_findings: Original research data for validation

YOUR TASK:
1. Check for overconfident language in final_insights
2. Verify evidence sparsity against raw_findings
3. Validate SWOT matrix structure consistency
4. Generate validation notes with warnings (⚠) and confirmations (✓)

OUTPUT FORMAT (JSON):
{
  "validation_notes": [
    "✓ SWOT matrix structure validated",
    "⚠ Overconfident language detected in insight 3",
    "✓ Evidence support verified for key claims",
    "⚠ Potential evidence sparsity in market timing analysis"
  ]
}

CRITICAL CONSTRAINTS:
- Read final_insight, comparative_swot, raw_findings (all read-only)
- DO NOT modify any existing state fields
- Output validation_notes will be MERGED into final_insight (merge strategy)
- Use ⚠ for warnings, ✓ for confirmations
- Focus on content validation, not structural validation
"""

HUMAN_REVIEW_PROMPT = """
Review final Task 3 analysis quality before report handoff.

INPUT DATA:
- final_insight: strategic insight package
- comparative_swot: comparative SWOT matrix
- consistency_flags: any validation flags

YOUR TASK:
1. Decide whether the analysis is safe to dispatch
2. Require review if validation warnings, consistency issues, or missing strategic components exist
3. Return a single review status

OUTPUT FORMAT (JSON):
{
  "review_status": "approved"
}

CRITICAL CONSTRAINTS:
- Return only "approved" or "review_required"
- Require review when evidence quality or logic quality is questionable
- Do not create any extra fields
"""
