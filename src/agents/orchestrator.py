"""
STEP 3: Agent Orchestrator
===========================
Runs all three AI agents in parallel:
  - Agent 1 (Vision): Screenshot analysis
  - Agent 2 (Semantic): DOM analysis
  - Agent 3 (Keyboard): Navigation analysis
Also converts axe-core findings into unified format.

Credentials: All agents read from .env via config/settings.py
"""

import asyncio
import time
from typing import List, Dict
from loguru import logger

from src.models import (
    AccessibilityIssue, PageCollectionResult,
    Severity, ImpactGroup, WCAGLevel
)
from src.agents.vision_agent import VisionAgent
from src.agents.semantic_agent import SemanticAgent
from src.agents.keyboard_agent import KeyboardAgent


# ─── Axe-Core → AccessibilityIssue Converter ─────────────

class AxeConverter:
    """Converts axe-core violations into unified AccessibilityIssue format."""

    IMPACT_MAP = {
        "critical": Severity.CRITICAL,
        "serious": Severity.SERIOUS,
        "moderate": Severity.MODERATE,
        "minor": Severity.MINOR,
    }

    AXE_TO_WCAG = {
        # ── Perceivable ───────────────────────────────────────────────
        "image-alt": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "input-image-alt": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "object-alt": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "area-alt": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "role-img-alt": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "svg-img-alt": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "image-redundant-alt": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "aria-meter-name": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "aria-progressbar-name": ("1.1.1", "Non-text Content", WCAGLevel.A),
        "audio-caption": ("1.2.1", "Audio-only and Video-only", WCAGLevel.A),
        "video-caption": ("1.2.2", "Captions (Prerecorded)", WCAGLevel.A),
        "video-description": ("1.2.3", "Audio Description", WCAGLevel.A),
        "label": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "label-title-only": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "heading-order": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "page-has-heading-one": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "empty-heading": ("2.4.6", "Headings and Labels", WCAGLevel.AA),
        "region": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-one-main": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-banner-is-top-level": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-complementary-is-top-level": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-contentinfo-is-top-level": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-main-is-top-level": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-no-duplicate-banner": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-no-duplicate-contentinfo": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-no-duplicate-main": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "landmark-unique": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "focus-order-semantics": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "list": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "listitem": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "definition-list": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "dlitem": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "td-headers-attr": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "th-has-data-cells": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "scope-attr-valid": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "p-as-heading": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "form-field-multiple-labels": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "aria-required-children": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "aria-required-parent": ("1.3.1", "Info and Relationships", WCAGLevel.A),
        "css-orientation-lock": ("1.3.4", "Orientation", WCAGLevel.AA),
        "autocomplete-valid": ("1.3.5", "Identify Input Purpose", WCAGLevel.AA),
        "link-in-text-block": ("1.4.1", "Use of Color", WCAGLevel.A),
        "color-contrast": ("1.4.3", "Contrast (Minimum)", WCAGLevel.AA),
        "color-contrast-enhanced": ("1.4.6", "Contrast (Enhanced)", WCAGLevel.AAA),
        "meta-viewport": ("1.4.4", "Resize Text", WCAGLevel.AA),
        "avoid-inline-spacing": ("1.4.12", "Text Spacing", WCAGLevel.AA),
        # ── Operable ──────────────────────────────────────────────────
        "scrollable-region-focusable": ("2.1.1", "Keyboard", WCAGLevel.A),
        "keyboard-scrollable-region-focusable": ("2.1.1", "Keyboard", WCAGLevel.A),
        "focus-trap": ("2.1.2", "No Keyboard Trap", WCAGLevel.A),
        "meta-refresh": ("2.2.1", "Timing Adjustable", WCAGLevel.A),
        "bypass": ("2.4.1", "Bypass Blocks", WCAGLevel.A),
        "frame-title": ("2.4.1", "Bypass Blocks", WCAGLevel.A),
        "document-title": ("2.4.2", "Page Titled", WCAGLevel.A),
        "tabindex": ("2.4.3", "Focus Order", WCAGLevel.A),
        "link-name": ("2.4.4", "Link Purpose (In Context)", WCAGLevel.A),
        "identical-links-same-purpose": ("2.4.9", "Link Purpose (Link Only)", WCAGLevel.AAA),
        "target-size": ("2.5.8", "Target Size (Minimum)", WCAGLevel.AA),
        # ── Understandable ────────────────────────────────────────────
        "html-has-lang": ("3.1.1", "Language of Page", WCAGLevel.A),
        "html-lang-valid": ("3.1.1", "Language of Page", WCAGLevel.A),
        "valid-lang": ("3.1.2", "Language of Parts", WCAGLevel.AA),
        # ── Robust ────────────────────────────────────────────────────
        "duplicate-id": ("4.1.1", "Parsing", WCAGLevel.A),
        "duplicate-id-active": ("4.1.1", "Parsing", WCAGLevel.A),
        "duplicate-id-aria": ("4.1.1", "Parsing", WCAGLevel.A),
        "button-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "select-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "summary-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "frame-title-unique": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-roles": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-valid-attr": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-valid-attr-value": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-required-attr": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-allowed-attr": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-prohibited-attr": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-conditional-attr": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-deprecated-role": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-hidden-focus": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-command-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-input-field-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-toggle-field-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-tooltip-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "aria-treeitem-name": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
        "presentation-role-conflict": ("4.1.2", "Name, Role, Value", WCAGLevel.A),
    }

    AXE_IMPACT_GROUPS = {
        "color-contrast": [ImpactGroup.LOW_VISION],
        "image-alt": [ImpactGroup.BLIND],
        "label": [ImpactGroup.BLIND, ImpactGroup.MOTOR],
        "link-name": [ImpactGroup.BLIND],
        "button-name": [ImpactGroup.BLIND],
        "html-has-lang": [ImpactGroup.BLIND],
        "heading-order": [ImpactGroup.BLIND, ImpactGroup.COGNITIVE],
        "bypass": [ImpactGroup.BLIND, ImpactGroup.MOTOR],
        "aria-roles": [ImpactGroup.BLIND],
    }

    @classmethod
    def _parse_wcag_tags(cls, wcag_tags: list) -> str:
        """
        Extract WCAG criterion from axe-core wcag_tags like ['wcag111', 'wcag412', 'wcag258'].
        Tags use concatenated digits: wcag111 → 1.1.1, wcag412 → 4.1.2, wcag1411 → 1.4.11.
        """
        for tag in wcag_tags:
            if tag.startswith("wcag") and len(tag) > 4 and tag[4:].isdigit():
                digits = tag[4:]
                if len(digits) == 3:
                    return f"{digits[0]}.{digits[1]}.{digits[2]}"
                elif len(digits) == 4:
                    return f"{digits[0]}.{digits[1]}.{digits[2:]}"
        return ""

    @classmethod
    def convert(cls, page_data: PageCollectionResult) -> List[AccessibilityIssue]:
        """
        Convert axe-core violations to AccessibilityIssue objects.
        One issue is created per violation (not per node) to avoid duplicate entries
        for rules with multiple affected elements (e.g. target-size, image-redundant-alt).
        """
        issues = []
        for violation in page_data.axe_results.violations:
            # Look up WCAG info from our map; fall back to parsing axe's wcag_tags
            wcag_info = cls.AXE_TO_WCAG.get(violation.rule_id)
            if not wcag_info:
                criterion = cls._parse_wcag_tags(violation.wcag_tags)
                wcag_info = (criterion, "", WCAGLevel.AA) if criterion else ("", "", WCAGLevel.AA)

            impact_groups = cls.AXE_IMPACT_GROUPS.get(violation.rule_id, [ImpactGroup.ALL])

            # Use the first affected node for element details; note total count in description
            first_node = violation.nodes[0] if violation.nodes else {}
            failure_summary = first_node.get("failure_summary", "")
            if violation.node_count > 1 and failure_summary:
                failure_summary = f"{failure_summary} (and {violation.node_count - 1} more)"

            issue = AccessibilityIssue(
                source="axe-core",
                page_url=page_data.page.url,
                title=f"[axe] {violation.help_text}",
                description=(
                    f"{violation.description}. "
                    f"Found {violation.node_count} instance(s) on this page. "
                    f"Failure: {failure_summary}"
                ),
                wcag_criterion=wcag_info[0],
                wcag_criterion_name=wcag_info[1],
                wcag_level=wcag_info[2],
                severity=cls.IMPACT_MAP.get(violation.impact, Severity.MODERATE),
                impact_groups=impact_groups,
                element_selector=", ".join(first_node.get("target", [])),
                element_html=first_node.get("html", "")[:300],
                fix_description=f"See: {violation.help_url}",
                confidence=1.0,
            )
            issues.append(issue)
        return issues


# ─── Parallel Orchestrator ────────────────────────────────

class AgentOrchestrator:
    """
    Runs all 3 AI agents + axe-core conversion in parallel for each page.
    All agents read credentials from .env via config/settings.py.

    Usage:
        orchestrator = AgentOrchestrator()
        all_issues = await orchestrator.analyze_all_pages(page_data_list)
    """

    def __init__(self):
        self.vision_agent = VisionAgent()
        self.semantic_agent = SemanticAgent()
        self.keyboard_agent = KeyboardAgent()
        self.axe_converter = AxeConverter()

    async def analyze_page(self, page_data: PageCollectionResult) -> List[AccessibilityIssue]:
        logger.info(f"\n🤖 AI ANALYSIS: {page_data.page.url}")
        start = time.time()

        # 1. Convert axe-core findings (synchronous, fast)
        axe_issues = self.axe_converter.convert(page_data)
        logger.info(f"  📊 axe-core converted: {len(axe_issues)} issues")

        # 2. Run 3 AI agents in parallel
        vision_task = asyncio.create_task(self._safe_run(self.vision_agent.analyze_page, page_data, "Vision"))
        semantic_task = asyncio.create_task(self._safe_run(self.semantic_agent.analyze_page, page_data, "Semantic"))
        keyboard_task = asyncio.create_task(self._safe_run(self.keyboard_agent.analyze_page, page_data, "Keyboard"))

        vision_issues, semantic_issues, keyboard_issues = await asyncio.gather(
            vision_task, semantic_task, keyboard_task
        )

        # 3. Combine all findings
        all_issues = axe_issues + vision_issues + semantic_issues + keyboard_issues

        elapsed = time.time() - start
        logger.info(
            f"  ✅ Page analysis complete in {elapsed:.1f}s: "
            f"{len(axe_issues)} axe + {len(vision_issues)} vision + "
            f"{len(semantic_issues)} semantic + {len(keyboard_issues)} keyboard = "
            f"{len(all_issues)} total"
        )
        return all_issues

    async def analyze_all_pages(
        self, pages_data: List[PageCollectionResult]
    ) -> Dict[str, List[AccessibilityIssue]]:
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP 3: AI ANALYSIS ({len(pages_data)} pages)")
        logger.info(f"{'='*60}")

        results: Dict[str, List[AccessibilityIssue]] = {}
        total_start = time.time()

        for i, page_data in enumerate(pages_data):
            logger.info(f"\n--- Analyzing page {i+1}/{len(pages_data)} ---")
            issues = await self.analyze_page(page_data)
            results[page_data.page.url] = issues

            if i < len(pages_data) - 1:
                await asyncio.sleep(1)

        total_time = time.time() - total_start
        total_issues = sum(len(issues) for issues in results.values())

        logger.info(f"\n{'='*60}")
        logger.info(f"AI ANALYSIS COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total pages analyzed: {len(results)}")
        logger.info(f"Total issues found: {total_issues}")
        logger.info(f"Total time: {total_time:.1f}s")

        source_counts = {"axe-core": 0, "vision_agent": 0, "semantic_agent": 0, "keyboard_agent": 0}
        for issues in results.values():
            for issue in issues:
                source_counts[issue.source] = source_counts.get(issue.source, 0) + 1
        for source, count in source_counts.items():
            logger.info(f"  {source}: {count} issues")

        return results

    async def _safe_run(self, func, page_data, agent_name: str) -> List[AccessibilityIssue]:
        try:
            return await func(page_data)
        except Exception as e:
            logger.error(f"  ❌ {agent_name} Agent failed: {e}")
            return []
