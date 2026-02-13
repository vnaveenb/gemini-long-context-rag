"""LangChain prompt templates for DQC evaluation."""

from langchain_core.prompts import ChatPromptTemplate

# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a Learning Content Quality Compliance Analyst. You evaluate educational
materials against a Data Quality Checklist (DQC). You must:

1. Base your evaluation ONLY on the provided document content.
2. Return structured JSON matching the exact schema.
3. Provide specific evidence from the content for your findings.
4. Never fabricate or assume content not present in the provided context.
5. If the content is insufficient to make a determination, set status to "Partial"
   and explain what is missing.
"""

# ── Single-Item Evaluation Prompt ────────────────────────────────────────────

EVALUATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        (
            "human",
            """\
## DQC Item
- ID: {dqc_item_id}
- Category: {category}
- Requirement: {requirement}
- Evaluation Criteria: {criteria}

## Document Content (Retrieved Sections)
{retrieved_context}

## Instructions
Evaluate whether the document content satisfies the above DQC requirement.

{format_instructions}
""",
        ),
    ]
)

# ── Executive Summary Prompt ─────────────────────────────────────────────────

SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a technical writer summarising compliance findings."),
        (
            "human",
            """\
Below are the compliance evaluation results for a learning document.

Document: {filename}
Overall Score: {score}%
Passed: {passed} | Failed: {failed} | Partial: {partial}

Findings:
{findings_text}

Write a concise executive summary (3-5 sentences) describing the overall
compliance status, key risks, and the most important recommendations.
Respond with only the summary text, no JSON or formatting.
""",
        ),
    ]
)

# ── Batch (Long-Context) Evaluation Prompt ───────────────────────────────────

BATCH_EVALUATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
You are a Learning Content Quality Compliance Analyst. You evaluate educational
materials against a Data Quality Checklist (DQC). You must:

1. Base your evaluation ONLY on the provided document content.
2. Return a JSON object matching the exact schema below.
3. Provide specific evidence from the content for your findings.
4. Never fabricate or assume content not present in the provided context.
5. If the content is insufficient to make a determination, set status to "Partial"
   and explain what is missing.
6. Evaluate EVERY item in the checklist — do not skip any.
""",
        ),
        (
            "human",
            """\
## Full Document Content
{document_text}

## DQC Checklist Items
{checklist_items}

## Instructions
Evaluate whether the document content satisfies EACH of the DQC requirements above.

Return a JSON object with exactly this structure:
{{
  "evaluations": [
    {{
      "dqc_item_id": "<item ID>",
      "status": "Pass" | "Fail" | "Partial",
      "justification": "<2-4 sentences explaining your reasoning with evidence>",
      "evidence_quotes": ["<direct quote from document>"],
      "risk_level": "Critical" | "High" | "Medium" | "Low",
      "recommendation": "<action to fix, or null if Pass>",
      "confidence_score": <float 0.0-1.0>,
      "sections_reviewed": ["<section names>"]
    }}
  ],
  "executive_summary": "<3-5 sentence summary of overall compliance status, key risks, and recommendations>"
}}

CRITICAL RULES:
- You MUST return one evaluation object per DQC item.
- Return ONLY valid JSON. Do NOT wrap in markdown code fences.
- All double quotes inside string values MUST be escaped as \".
- Do NOT use trailing commas after the last element in arrays or objects.
- Do NOT include any text outside the JSON object.
""",
        ),
    ]
)
