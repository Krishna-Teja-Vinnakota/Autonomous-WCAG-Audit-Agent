"""
STEP 3 - AGENT 2: Semantic Analysis Agent
===========================================
Uses Gemini Text to analyze DOM structure for semantic accessibility issues.

Credentials: Reads from .env via config/settings.py
"""

import json
from typing import List
from loguru import logger

from google import genai
from google.genai import types
from google.genai.types import HttpOptions

from config.settings import GEMINI_MODEL, GEMINI_API_KEY, GCP_PROJECT_ID, GCP_REGION
from src.models import (
    AccessibilityIssue, PageCollectionResult,
    Severity, ImpactGroup, WCAGLevel
)


SEMANTIC_ANALYSIS_PROMPT = """You are an expert WCAG 2.2 accessibility auditor performing a SEMANTIC analysis of a web page's DOM structure.

PAGE URL: {page_url}
PAGE TITLE: {page_title}

Here is the semantic structure of the page:

```
{dom_snapshot}
```

{axe_context}

Analyze the DOM structure for SEMANTIC accessibility issues. Focus on:

1. **Alt Text Quality (WCAG 1.1.1)**: Images with missing, empty, or generic alt text
2. **Heading Hierarchy (WCAG 1.3.1, 2.4.6)**: Skipped levels, multiple H1s, missing H1
3. **Link Text Quality (WCAG 2.4.4, 2.4.9)**: Ambiguous "click here", "read more" links
4. **Form Accessibility (WCAG 1.3.1, 3.3.2)**: Inputs without labels, missing fieldset/legend
5. **ARIA Usage (WCAG 4.1.2)**: Incorrect roles, missing required properties, redundant ARIA
6. **Document Structure (WCAG 1.3.1, 2.4.1)**: Missing landmarks, language, skip nav
7. **Content & Readability (WCAG 2.4.2, 3.1.1)**: Unclear title, missing language

For EACH issue found, respond in this exact JSON format:
```json
[
  {{
    "title": "Brief issue title",
    "description": "What's wrong and why it matters for accessibility",
    "wcag_criterion": "1.1.1",
    "wcag_criterion_name": "Non-text Content",
    "wcag_level": "A",
    "severity": "serious",
    "impact_groups": ["blind_users"],
    "element_selector": "CSS selector or description of the element",
    "element_html": "<img src='logo.png' alt=''>",
    "fix_description": "Specific fix recommendation",
    "fix_code_before": "<img src='logo.png' alt=''>",
    "fix_code_after": "<img src='logo.png' alt='Company logo - Acme Corp'>",
    "confidence": 0.9
  }}
]
```

SEVERITY: "critical", "serious", "moderate", "minor"
IMPACT GROUPS: "blind_users", "low_vision_users", "deaf_users", "motor_impaired_users", "cognitive_disability_users", "all_users"

IMPORTANT: Do NOT report issues that axe-core already found (listed above). Focus on issues needing HUMAN/AI judgment.
Include fix_code_before and fix_code_after when possible. Only report confidence >= 0.6.
"""


class SemanticAgent:
    """Analyzes page DOM structure for semantic accessibility issues using Gemini."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if GCP_PROJECT_ID:
                self._client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_REGION)
            elif GEMINI_API_KEY:
                self._client = genai.Client(api_key=GEMINI_API_KEY)
            else:
                self._client = genai.Client(http_options=HttpOptions(api_version="v1"))
        return self._client

    def _build_axe_context(self, page_data: PageCollectionResult) -> str:
        if not page_data.axe_results.violations:
            return "AXE-CORE FINDINGS: No violations found by automated scan."

        lines = ["AXE-CORE FINDINGS (already detected — do NOT report these again):"]
        for v in page_data.axe_results.violations:
            lines.append(f"  - [{v.impact}] {v.rule_id}: {v.help_text} ({v.node_count} nodes)")
        return "\n".join(lines)

    async def analyze_page(self, page_data: PageCollectionResult) -> List[AccessibilityIssue]:
        if not page_data.dom_snapshot:
            logger.warning(f"  No DOM snapshot available for {page_data.page.url}")
            return []

        try:
            logger.info(f"  📝 Semantic Agent analyzing: {page_data.page.url}")
            client = self._get_client()

            dom_snapshot = page_data.dom_snapshot
            if len(dom_snapshot) > 80000:
                dom_snapshot = dom_snapshot[:80000] + "\n... [TRUNCATED]"

            prompt = SEMANTIC_ANALYSIS_PROMPT.format(
                page_url=page_data.page.url,
                page_title=page_data.page.title,
                dom_snapshot=dom_snapshot,
                axe_context=self._build_axe_context(page_data),
            )

            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=16384),
            )

            issues = self._parse_response(response.text, page_data.page.url)
            logger.info(f"  ✅ Semantic Agent: found {len(issues)} issues")
            return issues

        except Exception as e:
            logger.error(f"  ❌ Semantic Agent error: {e}")
            return []

    def _parse_response(self, response_text: str, page_url: str) -> List[AccessibilityIssue]:
        issues = []

        try:
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            if not text.startswith("[") and not text.startswith("{"):
                return []

            # Repair truncated JSON arrays (response hit token limit mid-string)
            try:
                raw_issues = json.loads(text)
            except json.JSONDecodeError:
                text = text.rstrip().rstrip(",")
                last_obj = text.rfind("},")
                if last_obj != -1:
                    text = text[:last_obj + 1] + "]"
                elif text.rfind("}") != -1:
                    text = text[:text.rfind("}") + 1] + "]"
                else:
                    raise
                raw_issues = json.loads(text)
                logger.warning("  ⚠️  Semantic Agent: repaired truncated JSON response")
            if not isinstance(raw_issues, list):
                raw_issues = [raw_issues]

            severity_map = {"critical": Severity.CRITICAL, "serious": Severity.SERIOUS, "moderate": Severity.MODERATE, "minor": Severity.MINOR}
            impact_map = {"blind_users": ImpactGroup.BLIND, "low_vision_users": ImpactGroup.LOW_VISION, "deaf_users": ImpactGroup.DEAF, "motor_impaired_users": ImpactGroup.MOTOR, "cognitive_disability_users": ImpactGroup.COGNITIVE, "all_users": ImpactGroup.ALL}
            level_map = {"A": WCAGLevel.A, "AA": WCAGLevel.AA, "AAA": WCAGLevel.AAA}

            for raw in raw_issues:
                confidence = raw.get("confidence", 0.7)
                if confidence < 0.6:
                    continue

                issue = AccessibilityIssue(
                    source="semantic_agent",
                    page_url=page_url,
                    title=raw.get("title", "Semantic issue"),
                    description=raw.get("description", ""),
                    wcag_criterion=raw.get("wcag_criterion", ""),
                    wcag_criterion_name=raw.get("wcag_criterion_name", ""),
                    wcag_level=level_map.get(raw.get("wcag_level", "AA"), WCAGLevel.AA),
                    severity=severity_map.get(raw.get("severity", "moderate"), Severity.MODERATE),
                    impact_groups=[impact_map[g] for g in raw.get("impact_groups", []) if g in impact_map],
                    element_selector=raw.get("element_selector", ""),
                    element_html=raw.get("element_html", ""),
                    fix_description=raw.get("fix_description", ""),
                    fix_code_before=raw.get("fix_code_before", ""),
                    fix_code_after=raw.get("fix_code_after", ""),
                    confidence=confidence,
                )
                issues.append(issue)

        except json.JSONDecodeError as e:
            logger.error(f"  Failed to parse Semantic Agent JSON: {e}")
        except Exception as e:
            logger.error(f"  Error parsing Semantic Agent response: {e}")

        return issues
