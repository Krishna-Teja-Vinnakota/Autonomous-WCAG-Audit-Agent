"""
STEP 5a: Issue Deduplicator, Scorer & RAG Enrichment
======================================================
Takes all raw findings from Step 3 and produces a clean, prioritized report:
  - Deduplicates similar issues across sources
  - Calculates per-page and overall accessibility scores
  - Enriches top issues with WCAG techniques via RAG (Step 4)
  - Builds a prioritized action plan

API Keys Needed: Pinecone (optional — gracefully degrades without it)
"""

from typing import List, Dict, Optional
from collections import defaultdict
from loguru import logger

from src.models import (
    AccessibilityIssue, PageReport, AuditReport,
    Severity, ImpactGroup, WCAGLevel, AuditStatus
)


# Severity weights for scoring
SEVERITY_WEIGHT = {
    Severity.CRITICAL: 10,
    Severity.SERIOUS: 5,
    Severity.MODERATE: 2,
    Severity.MINOR: 1,
}

# WCAG principle mapping
WCAG_PRINCIPLES = {
    "1": "Perceivable",
    "2": "Operable",
    "3": "Understandable",
    "4": "Robust",
}


class IssueDeduplicator:
    """Deduplicates issues found by multiple sources."""

    @staticmethod
    def deduplicate(issues: List[AccessibilityIssue]) -> List[AccessibilityIssue]:
        if not issues:
            return []

        unique: List[AccessibilityIssue] = []
        seen_keys: set = set()

        sorted_issues = sorted(
            issues,
            key=lambda i: (-i.confidence, i.source != "axe-core"),
        )

        for issue in sorted_issues:
            key_parts = []
            if issue.wcag_criterion:
                key_parts.append(issue.wcag_criterion)
            if issue.element_selector:
                selector = issue.element_selector.strip().lower()[:100]
                key_parts.append(selector)
            elif issue.element_html:
                html_sig = issue.element_html.strip().lower()[:80]
                key_parts.append(html_sig)
            if len(key_parts) < 2:
                key_parts.append(issue.title.lower().strip()[:60])

            dedup_key = "|".join(key_parts)

            if dedup_key in seen_keys:
                issue.is_duplicate = True
                continue

            seen_keys.add(dedup_key)
            unique.append(issue)

        deduped_count = len(issues) - len(unique)
        if deduped_count > 0:
            logger.info(f"  🔄 Deduplicated: {len(issues)} → {len(unique)} ({deduped_count} removed)")

        return unique


class AccessibilityScorer:
    """Calculates accessibility scores using a capped, diminishing-returns model.

    Each severity tier contributes a capped penalty so that a site with many issues
    in one category doesn't automatically score 0.  The caps reflect the point at
    which additional issues of that tier add no incremental signal:

        Tier       Weight  Cap  Max-penalty  (cap ÷ weight = issues to hit cap)
        ───────────────────────────────────────────────────────────────────────
        Critical    8 pts   40      40 pts   (5+ criticals)
        Serious     4 pts   24      24 pts   (6+ serious)
        Moderate    2 pts   16      16 pts   (8+ moderate)
        Minor       0.5 pts  4       4 pts   (8+ minor)
        ─────────────────────────────────────────────────────
        Maximum total penalty                84 pts  → floor score ≈ 16

    Real-world calibration:
        Perfect site (0 issues)  → 100
        1 critical               → 92
        4 critical + 10 serious  → ~52  (like a major e-commerce site with real issues)
        Terrible site (maxed out) → ~16
    """

    @staticmethod
    def calculate_page_score(issues: List[AccessibilityIssue]) -> float:
        if not issues:
            return 100.0

        active = [i for i in issues if not i.is_duplicate]

        critical = sum(1 for i in active if i.severity == Severity.CRITICAL)
        serious  = sum(1 for i in active if i.severity == Severity.SERIOUS)
        moderate = sum(1 for i in active if i.severity == Severity.MODERATE)
        minor    = sum(1 for i in active if i.severity == Severity.MINOR)

        penalty = (
            min(critical * 8,   40) +
            min(serious  * 4,   24) +
            min(moderate * 2,   16) +
            min(minor    * 0.5,  4)
        )

        return round(max(0.0, 100.0 - penalty), 1)

    @staticmethod
    def calculate_overall_score(page_scores: List[float]) -> float:
        if not page_scores:
            return 100.0
        return round(sum(page_scores) / len(page_scores), 1)


class RAGEnricher:
    """
    Enriches accessibility issues with WCAG techniques from RAG knowledge base.
    Gracefully degrades if Pinecone is not configured.
    """

    def __init__(self):
        self._kb = None
        self._available = None

    def _init_kb(self):
        """Lazy-init knowledge base."""
        if self._available is not None:
            return self._available

        try:
            from src.rag.knowledge_base import WCAGKnowledgeBase
            self._kb = WCAGKnowledgeBase()
            self._available = self._kb.is_available()
            if self._available:
                stats = self._kb.get_stats()
                logger.info(f"  📚 RAG knowledge base connected ({stats['total_vectors']} vectors)")
            else:
                logger.info("  ℹ️  RAG knowledge base empty or not configured — skipping enrichment")
        except Exception as e:
            logger.info(f"  ℹ️  RAG not available ({e}) — skipping enrichment")
            self._available = False

        return self._available

    def enrich_issues(self, issues: List[AccessibilityIssue]) -> List[AccessibilityIssue]:
        """
        Enrich issues with WCAG technique references from RAG.
        Only enriches issues that have a WCAG criterion.
        """
        if not self._init_kb():
            return issues

        enriched_count = 0
        for issue in issues:
            if issue.is_duplicate:
                continue
            if not issue.wcag_criterion:
                continue

            try:
                result = self._kb.query_for_issue(
                    title=issue.title,
                    description=issue.description,
                    wcag_criterion=issue.wcag_criterion,
                    top_k=3,
                )

                # Enrich fix_description with technique references
                if result["techniques"]:
                    technique_refs = []
                    for t in result["techniques"]:
                        if t["technique_id"]:
                            technique_refs.append(f"{t['technique_id']}")
                    if technique_refs:
                        issue.rag_techniques = technique_refs
                        # Append technique info to fix description if it's sparse
                        if len(issue.fix_description) < 50 and result["techniques"]:
                            best_technique = result["techniques"][0]
                            # Extract actionable part from technique text
                            tech_text = best_technique["text"]
                            if len(tech_text) > 200:
                                tech_text = tech_text[:200] + "..."
                            issue.fix_description = (
                                f"{issue.fix_description} "
                                f"[{best_technique['technique_id']}] {tech_text}"
                            ).strip()

                # Add understanding context if missing description depth
                if result["understanding"] and len(issue.description) < 100:
                    issue.rag_understanding = result["understanding"][:300]

                # Add fix suggestions from techniques
                if result["fix_suggestions"] and not issue.fix_code_after:
                    for suggestion in result["fix_suggestions"][:1]:
                        if "Example:" in suggestion:
                            example = suggestion[suggestion.index("Example:") + 9:].strip()
                            issue.fix_code_after = example[:300]

                enriched_count += 1

            except Exception as e:
                logger.debug(f"  RAG enrichment failed for {issue.wcag_criterion}: {e}")
                continue

        if enriched_count > 0:
            logger.info(f"  📚 RAG enriched {enriched_count} issues with WCAG techniques")

        return issues


class ReportAggregator:
    """
    Aggregates all findings into a structured AuditReport.
    Includes optional RAG enrichment.
    """

    def __init__(self, enable_rag: bool = True):
        self.deduplicator = IssueDeduplicator()
        self.scorer = AccessibilityScorer()
        self.rag_enricher = RAGEnricher() if enable_rag else None

    def build_report(
        self,
        audit_id: str,
        target_url: str,
        analysis_results: Dict[str, List[AccessibilityIssue]],
        total_duration: float = 0.0,
    ) -> AuditReport:
        logger.info(f"\n{'='*60}")
        logger.info("STEP 5: AGGREGATION & REPORT BUILDING")
        logger.info(f"{'='*60}")

        page_reports: List[PageReport] = []
        all_issues: List[AccessibilityIssue] = []
        page_scores: List[float] = []

        for page_url, raw_issues in analysis_results.items():
            logger.info(f"\n  Processing: {page_url}")

            # 1. Deduplicate
            unique_issues = self.deduplicator.deduplicate(raw_issues)

            # 2. RAG Enrichment (if available)
            if self.rag_enricher:
                unique_issues = self.rag_enricher.enrich_issues(unique_issues)

            # 3. Score
            score = self.scorer.calculate_page_score(unique_issues)

            # 4. Count by severity
            severity_counts = self._count_by_severity(unique_issues)

            # 5. Build page report
            page_report = PageReport(
                page_url=page_url,
                page_title=self._extract_title(page_url, unique_issues),
                issues=unique_issues,
                score=score,
                critical_count=severity_counts.get(Severity.CRITICAL, 0),
                serious_count=severity_counts.get(Severity.SERIOUS, 0),
                moderate_count=severity_counts.get(Severity.MODERATE, 0),
                minor_count=severity_counts.get(Severity.MINOR, 0),
            )

            page_reports.append(page_report)
            all_issues.extend(unique_issues)
            page_scores.append(score)

            logger.info(
                f"    Score: {score}/100 | "
                f"Issues: {len(unique_issues)} "
                f"(🔴{severity_counts.get(Severity.CRITICAL, 0)} "
                f"🟠{severity_counts.get(Severity.SERIOUS, 0)} "
                f"🟡{severity_counts.get(Severity.MODERATE, 0)} "
                f"🔵{severity_counts.get(Severity.MINOR, 0)})"
            )

        # Overall score
        overall_score = self.scorer.calculate_overall_score(page_scores)

        # Breakdowns
        issues_by_severity = {
            s.value: sum(1 for i in all_issues if i.severity == s and not i.is_duplicate)
            for s in Severity
        }
        issues_by_principle = self._group_by_principle(all_issues)
        issues_by_impact = self._group_by_impact(all_issues)

        # Priority fixes
        priority_fixes = self._get_priority_fixes(all_issues, limit=10)

        # Build report
        report = AuditReport(
            audit_id=audit_id,
            target_url=target_url,
            status=AuditStatus.COMPLETED,
            overall_score=overall_score,
            total_issues=len(all_issues),
            total_pages_audited=len(page_reports),
            issues_by_severity=issues_by_severity,
            issues_by_wcag_principle=issues_by_principle,
            issues_by_impact_group=issues_by_impact,
            page_reports=page_reports,
            priority_fixes=priority_fixes,
            total_duration_seconds=total_duration,
        )

        logger.info(f"\n  📊 OVERALL SCORE: {overall_score}/100")
        logger.info(f"  📋 Total unique issues: {len(all_issues)}")
        logger.info(f"  🎯 Priority fixes: {len(priority_fixes)}")

        return report

    def _count_by_severity(self, issues: List[AccessibilityIssue]) -> Dict[Severity, int]:
        counts: Dict[Severity, int] = {}
        for issue in issues:
            if not issue.is_duplicate:
                counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return counts

    def _extract_title(self, url: str, issues: List[AccessibilityIssue]) -> str:
        path = url.rstrip("/").split("/")[-1] or "Home"
        return path.replace("-", " ").replace("_", " ").title()

    def _group_by_principle(self, issues: List[AccessibilityIssue]) -> Dict[str, int]:
        groups: Dict[str, int] = {v: 0 for v in WCAG_PRINCIPLES.values()}
        groups["Uncategorized"] = 0
        for issue in issues:
            if issue.is_duplicate:
                continue
            if issue.wcag_criterion and issue.wcag_criterion[0] in WCAG_PRINCIPLES:
                principle = WCAG_PRINCIPLES[issue.wcag_criterion[0]]
                groups[principle] += 1
            else:
                groups["Uncategorized"] += 1
        return {k: v for k, v in groups.items() if v > 0}

    def _group_by_impact(self, issues: List[AccessibilityIssue]) -> Dict[str, int]:
        groups: Dict[str, int] = defaultdict(int)
        for issue in issues:
            if issue.is_duplicate:
                continue
            for group in issue.impact_groups:
                groups[group.value] += 1
        return dict(groups)

    def _get_priority_fixes(
        self, issues: List[AccessibilityIssue], limit: int = 10
    ) -> List[AccessibilityIssue]:
        active_issues = [i for i in issues if not i.is_duplicate]
        ranked = sorted(
            active_issues,
            key=lambda i: (
                -SEVERITY_WEIGHT.get(i.severity, 0),
                -len(i.impact_groups),
                -i.confidence,
            ),
        )
        return ranked[:limit]