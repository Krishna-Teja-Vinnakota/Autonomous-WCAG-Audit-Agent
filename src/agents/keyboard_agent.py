"""
STEP 3 - AGENT 3: Keyboard Navigation Agent
=============================================
Uses Gemini Text to analyze keyboard navigation recordings.

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


KEYBOARD_ANALYSIS_PROMPT = """You are an expert WCAG 2.2 accessibility auditor analyzing keyboard navigation data for a web page.

PAGE URL: {page_url}
PAGE TITLE: {page_title}

KEYBOARD NAVIGATION DATA:
- Total focusable elements: {total_focusable}
- Skip navigation link present: {skip_link}
- Focus trap detected: {focus_trap}

TAB ORDER (elements in the order they receive focus when pressing Tab):
{tab_order_formatted}

FOCUS INDICATOR ISSUES (elements where no visible focus ring was detected):
{focus_issues_formatted}

DOM CONTEXT (semantic structure for reference):
{dom_context}

Analyze this keyboard navigation data for accessibility issues:

1. **Tab Order Logic (WCAG 2.4.3)**: Does tab order follow logical sequence?
2. **Skip Navigation (WCAG 2.4.1)**: Is there a "skip to main content" link?
3. **Focus Visibility (WCAG 2.4.7, 2.4.11, 2.4.12)**: Which elements lack visible focus indicators?
4. **Keyboard Traps (WCAG 2.1.2)**: Can user Tab through entire page without getting stuck?
5. **Keyboard Operability (WCAG 2.1.1)**: Are all interactive elements reachable via keyboard?
6. **Focus Management (WCAG 2.4.3)**: Is focus managed properly after interactions?

For EACH issue, respond in this exact JSON format:
```json
[
  {{
    "title": "Brief issue title",
    "description": "What's wrong and the impact on keyboard users",
    "wcag_criterion": "2.4.7",
    "wcag_criterion_name": "Focus Visible",
    "wcag_level": "AA",
    "severity": "serious",
    "impact_groups": ["motor_impaired_users", "blind_users"],
    "element_selector": "Element description or selector",
    "fix_description": "How to fix this",
    "fix_code_before": "button {{ outline: none; }}",
    "fix_code_after": "button:focus-visible {{ outline: 2px solid #005fcc; outline-offset: 2px; }}",
    "confidence": 0.85
  }}
]
```

SEVERITY: "critical" (blocked), "serious" (major difficulty), "moderate" (inconvenience), "minor" (slight issue)

IMPORTANT:
- If there's no skip link and nav has 10+ links, that's SERIOUS.
- If total focusable is 0, the page likely has JS-only interactions — flag as CRITICAL.
"""


class KeyboardAgent:
    """Analyzes keyboard navigation data for accessibility issues."""

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

    def _format_tab_order(self, tab_order: list) -> str:
        if not tab_order:
            return "  (No focusable elements recorded)"

        lines = []
        for entry in tab_order[:60]:
            tag = entry.get("tag", "?")
            role = entry.get("role", "")
            label = entry.get("label", "")[:50]
            idx = entry.get("index", "?")
            href = entry.get("href", "")
            tabindex = entry.get("tabindex", "")
            visible = entry.get("visible", True)
            has_focus = entry.get("has_focus_indicator", True)

            parts = [f"  [{idx}] <{tag}>"]
            if role: parts.append(f'role="{role}"')
            if label: parts.append(f'"{label}"')
            if href: parts.append(f"→ {href[:60]}")
            if tabindex: parts.append(f"tabindex={tabindex}")
            if not visible: parts.append("[HIDDEN]")
            if not has_focus: parts.append("[NO FOCUS RING]")
            lines.append(" ".join(parts))

        if len(tab_order) > 60:
            lines.append(f"  ... and {len(tab_order) - 60} more elements")
        return "\n".join(lines)

    def _format_focus_issues(self, focus_issues: list) -> str:
        if not focus_issues:
            return "  (No focus visibility issues detected)"
        return "\n".join(f"  - {issue}" for issue in focus_issues[:20])

    async def analyze_page(self, page_data: PageCollectionResult) -> List[AccessibilityIssue]:
        try:
            logger.info(f"  [keyboard] analyzing: {page_data.page.url}")
            client = self._get_client()

            dom_context = page_data.dom_snapshot[:20000] if page_data.dom_snapshot else "(not available)"

            prompt = KEYBOARD_ANALYSIS_PROMPT.format(
                page_url=page_data.page.url,
                page_title=page_data.page.title,
                total_focusable=page_data.keyboard_nav.total_focusable,
                skip_link="YES" if page_data.keyboard_nav.skip_link_present else "NO",
                focus_trap="YES ⚠️" if page_data.keyboard_nav.focus_trap_detected else "No",
                tab_order_formatted=self._format_tab_order(page_data.keyboard_nav.tab_order),
                focus_issues_formatted=self._format_focus_issues(page_data.keyboard_nav.focus_visible_issues),
                dom_context=dom_context,
            )

            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192),
            )

            issues = self._parse_response(response.text, page_data.page.url)
            logger.info(f"  ✅ Keyboard Agent: found {len(issues)} issues")
            return issues

        except Exception as e:
            logger.error(f"  ❌ Keyboard Agent error: {e}")
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

            # Repair truncated JSON arrays (e.g. response hit token limit mid-string)
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
                logger.warning(f"  ⚠️  Keyboard Agent: repaired truncated JSON response")
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
                    source="keyboard_agent",
                    page_url=page_url,
                    title=raw.get("title", "Keyboard issue"),
                    description=raw.get("description", ""),
                    wcag_criterion=raw.get("wcag_criterion", ""),
                    wcag_criterion_name=raw.get("wcag_criterion_name", ""),
                    wcag_level=level_map.get(raw.get("wcag_level", "AA"), WCAGLevel.AA),
                    severity=severity_map.get(raw.get("severity", "moderate"), Severity.MODERATE),
                    impact_groups=[impact_map[g] for g in raw.get("impact_groups", []) if g in impact_map],
                    element_selector=raw.get("element_selector", ""),
                    fix_description=raw.get("fix_description", ""),
                    fix_code_before=raw.get("fix_code_before", ""),
                    fix_code_after=raw.get("fix_code_after", ""),
                    confidence=confidence,
                )
                issues.append(issue)

        except json.JSONDecodeError as e:
            logger.error(f"  Failed to parse Keyboard Agent JSON: {e}")
        except Exception as e:
            logger.error(f"  Error parsing Keyboard Agent response: {e}")

        return issues
