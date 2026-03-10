"""
STEP 3 - AGENT 1: Vision Analysis Agent
=========================================
Uses Gemini Vision to analyze page screenshots for visual
accessibility issues that automated tools can't catch.

Credentials: Reads from .env via config/settings.py
"""

import os
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


VISION_ANALYSIS_PROMPT = """You are an expert WCAG 2.2 accessibility auditor analyzing screenshots of a web page.

PAGE URL: {page_url}
PAGE TITLE: {page_title}
VIEWPORT: {viewport_name} ({viewport_desc})

Analyze this screenshot for VISUAL accessibility issues. Focus on:

1. **Color Contrast (WCAG 1.4.3, 1.4.6)**: Text that appears hard to read against its background. Look for:
   - Light gray text on white backgrounds
   - Text overlaid on images or gradients without proper contrast
   - Placeholder text with insufficient contrast
   - Disabled elements that are nearly invisible

2. **Target Size (WCAG 2.5.8, 2.5.5)**: Interactive elements (buttons, links, form controls) that appear smaller than 24x24px (AA) or 44x44px (AAA). Look for:
   - Tiny clickable icons
   - Links too close together (especially in navigation)
   - Small form controls

3. **Text Spacing & Readability (WCAG 1.4.12)**: Content that may break when text spacing is adjusted:
   - Overlapping text
   - Truncated content with "..."
   - Text cut off by containers

4. **Responsive Design Issues (WCAG 1.4.10)**: Content that doesn't work well at this viewport:
   - Horizontal scrolling required
   - Content hidden or cut off
   - Overlapping elements
   - Unreadable text size on mobile

5. **Visual Focus & State Indicators (WCAG 1.4.11)**: UI components that may lack sufficient visual indicators:
   - Buttons that look like plain text
   - Links that aren't visually distinct
   - Form fields without clear boundaries

6. **Content Structure (WCAG 1.3.1)**: Visual structure issues:
   - Information conveyed only through color
   - Missing visual grouping of related content
   - Layout that doesn't follow logical reading order

For EACH issue found, respond in this exact JSON format:
```json
[
  {{
    "title": "Brief issue title",
    "description": "Detailed description of what's wrong and where on the page",
    "wcag_criterion": "1.4.3",
    "wcag_criterion_name": "Contrast (Minimum)",
    "wcag_level": "AA",
    "severity": "serious",
    "impact_groups": ["low_vision_users"],
    "element_description": "Description of the specific element",
    "fix_description": "How to fix this issue",
    "confidence": 0.85
  }}
]
```

SEVERITY LEVELS: "critical", "serious", "moderate", "minor"
IMPACT GROUPS: "blind_users", "low_vision_users", "deaf_users", "motor_impaired_users", "cognitive_disability_users", "all_users"
WCAG LEVELS: "A", "AA", "AAA"

If no issues are found, return an empty array: []
Be specific about WHERE on the page you see each issue. Only report issues with confidence > 0.6.
Do NOT report issues that axe-core would already catch — focus on VISUAL issues only.
"""


class VisionAgent:
    """Analyzes page screenshots using Gemini Vision for visual accessibility issues."""

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

    def _load_image_as_part(self, image_path: str):
        if not os.path.exists(image_path):
            logger.warning(f"Screenshot not found: {image_path}")
            return None

        with open(image_path, "rb") as f:
            image_bytes = f.read()

        return types.Part.from_bytes(data=image_bytes, mime_type="image/png")

    async def analyze_page(self, page_data: PageCollectionResult) -> List[AccessibilityIssue]:
        all_issues: List[AccessibilityIssue] = []

        viewport_configs = [
            ("desktop", page_data.screenshots.desktop, "Desktop 1920x1080",
             "Full desktop view — check for contrast, target sizes, visual hierarchy"),
            ("mobile", page_data.screenshots.mobile, "Mobile 375x812",
             "Mobile view — check for touch targets, text readability, content reflow"),
            ("zoomed_200", page_data.screenshots.zoomed_200, "Desktop at 200% zoom",
             "200% zoom — check for content overlap, truncation, reflow at increased text size"),
        ]

        client = self._get_client()

        for viewport_name, screenshot_path, viewport_desc, analysis_focus in viewport_configs:
            if not screenshot_path or not os.path.exists(screenshot_path):
                logger.warning(f"  Skipping {viewport_name} — no screenshot available")
                continue

            try:
                logger.info(f"  [vision] analyzing {viewport_name}: {page_data.page.url}")

                image_part = self._load_image_as_part(screenshot_path)
                if image_part is None:
                    continue

                prompt = VISION_ANALYSIS_PROMPT.format(
                    page_url=page_data.page.url,
                    page_title=page_data.page.title,
                    viewport_name=viewport_name,
                    viewport_desc=f"{viewport_desc} — {analysis_focus}",
                )

                response = await client.aio.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=[image_part, prompt],
                    config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=8192),
                )

                issues = self._parse_response(response.text, page_data.page.url, viewport_name, screenshot_path)
                all_issues.extend(issues)
                logger.info(f"  ✅ Vision Agent ({viewport_name}): found {len(issues)} issues")

            except Exception as e:
                logger.error(f"  ❌ Vision Agent error on {viewport_name}: {e}")

        return all_issues

    def _parse_response(self, response_text: str, page_url: str, viewport: str, screenshot_path: str) -> List[AccessibilityIssue]:
        import json
        issues = []

        try:
            text = response_text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            # Model returned prose (e.g. "no issues found") instead of JSON
            if not text.startswith("[") and not text.startswith("{"):
                return []

            raw_issues = json.loads(text)
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
                    source="vision_agent",
                    page_url=page_url,
                    title=raw.get("title", "Visual issue"),
                    description=f"[{viewport}] {raw.get('description', '')}",
                    wcag_criterion=raw.get("wcag_criterion", ""),
                    wcag_criterion_name=raw.get("wcag_criterion_name", ""),
                    wcag_level=level_map.get(raw.get("wcag_level", "AA"), WCAGLevel.AA),
                    severity=severity_map.get(raw.get("severity", "moderate"), Severity.MODERATE),
                    impact_groups=[impact_map[g] for g in raw.get("impact_groups", []) if g in impact_map],
                    element_selector=raw.get("element_description", ""),
                    screenshot_region=screenshot_path,
                    fix_description=raw.get("fix_description", ""),
                    confidence=confidence,
                )
                issues.append(issue)

        except json.JSONDecodeError as e:
            logger.error(f"  Failed to parse Vision Agent JSON response: {e}")
            logger.debug(f"  Raw response: {response_text[:500]}")
        except Exception as e:
            logger.error(f"  Error parsing Vision Agent response: {e}")

        return issues
