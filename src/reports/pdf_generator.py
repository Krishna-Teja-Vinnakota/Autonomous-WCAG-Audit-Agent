"""
STEP 5b: PDF Report Generator
===============================
Generates a professional WCAG accessibility audit PDF report.
Now includes RAG technique references when available.

API Keys Needed: NONE
pip install: reportlab
"""

import os
from datetime import datetime
from typing import List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from loguru import logger

from src.models import AuditReport, PageReport, AccessibilityIssue, Severity


# ─── Color Palette ────────────────────────────────────────

COLORS = {
    "primary": colors.HexColor("#1a56db"),
    "dark": colors.HexColor("#1e293b"),
    "muted": colors.HexColor("#64748b"),
    "light_bg": colors.HexColor("#f8fafc"),
    "border": colors.HexColor("#e2e8f0"),
    "critical": colors.HexColor("#dc2626"),
    "serious": colors.HexColor("#ea580c"),
    "moderate": colors.HexColor("#ca8a04"),
    "minor": colors.HexColor("#2563eb"),
    "pass": colors.HexColor("#16a34a"),
    "rag": colors.HexColor("#7c3aed"),
    "white": colors.white,
}

SEVERITY_COLORS = {
    Severity.CRITICAL: COLORS["critical"],
    Severity.SERIOUS: COLORS["serious"],
    Severity.MODERATE: COLORS["moderate"],
    Severity.MINOR: COLORS["minor"],
}

SEVERITY_LABELS = {
    Severity.CRITICAL: "CRITICAL",
    Severity.SERIOUS: "SERIOUS",
    Severity.MODERATE: "MODERATE",
    Severity.MINOR: "MINOR",
}


class PDFReportGenerator:
    """Generates a professional PDF accessibility audit report."""

    def __init__(self, output_dir: str = "./data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._setup_styles()

    def _setup_styles(self):
        self.styles = getSampleStyleSheet()

        self.styles.add(ParagraphStyle(
            name="CoverTitle", fontName="Helvetica-Bold", fontSize=28,
            textColor=COLORS["dark"], alignment=TA_CENTER, spaceAfter=12,
        ))
        self.styles.add(ParagraphStyle(
            name="CoverSubtitle", fontName="Helvetica", fontSize=14,
            textColor=COLORS["muted"], alignment=TA_CENTER, spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name="SectionTitle", fontName="Helvetica-Bold", fontSize=18,
            textColor=COLORS["primary"], spaceBefore=20, spaceAfter=10,
        ))
        self.styles.add(ParagraphStyle(
            name="SubSection", fontName="Helvetica-Bold", fontSize=13,
            textColor=COLORS["dark"], spaceBefore=14, spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            name="BodyText2", fontName="Helvetica", fontSize=10,
            textColor=COLORS["dark"], spaceBefore=2, spaceAfter=4, leading=14,
        ))
        self.styles.add(ParagraphStyle(
            name="SmallMuted", fontName="Helvetica", fontSize=9,
            textColor=COLORS["muted"], spaceBefore=2, spaceAfter=2,
        ))
        self.styles.add(ParagraphStyle(
            name="IssueTitle", fontName="Helvetica-Bold", fontSize=11,
            textColor=COLORS["dark"], spaceBefore=8, spaceAfter=2,
        ))
        self.styles.add(ParagraphStyle(
            name="CodeBlock", fontName="Courier", fontSize=8,
            textColor=COLORS["dark"], backColor=COLORS["light_bg"],
            spaceBefore=4, spaceAfter=4, leftIndent=12, rightIndent=12, leading=12,
        ))
        self.styles.add(ParagraphStyle(
            name="RAGRef", fontName="Helvetica", fontSize=9,
            textColor=COLORS["rag"], spaceBefore=2, spaceAfter=2,
        ))

    def generate(self, report: AuditReport) -> str:
        filename = f"wcag_audit_{report.audit_id[:8]}_{datetime.now().strftime('%Y%m%d')}.pdf"
        filepath = os.path.join(self.output_dir, filename)

        logger.info(f"  📄 Generating PDF report: {filepath}")

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            topMargin=25*mm, bottomMargin=20*mm, leftMargin=20*mm, rightMargin=20*mm,
        )

        story = []

        # 1. Cover Page
        story.extend(self._build_cover(report))
        story.append(PageBreak())

        # 2. Executive Summary
        story.extend(self._build_executive_summary(report))
        story.append(PageBreak())

        # 3. Severity Breakdown
        story.extend(self._build_severity_breakdown(report))

        # 4. WCAG Principle Breakdown
        story.extend(self._build_principle_breakdown(report))

        # 5. Priority Action Plan
        story.append(PageBreak())
        story.extend(self._build_priority_fixes(report))

        # 6. Per-Page Findings
        for page_report in report.page_reports:
            story.append(PageBreak())
            story.extend(self._build_page_section(page_report))

        doc.build(story)
        logger.info(f"  ✅ PDF generated: {filepath}")
        return filepath

    # ─── Cover Page ───

    def _build_cover(self, report: AuditReport) -> list:
        elements = []
        elements.append(Spacer(1, 80))
        elements.append(Paragraph("WCAG Accessibility", self.styles["CoverTitle"]))
        elements.append(Paragraph("Audit Report", self.styles["CoverTitle"]))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(report.target_url, self.styles["CoverSubtitle"]))
        elements.append(Paragraph(report.audit_date.strftime("%B %d, %Y"), self.styles["CoverSubtitle"]))
        elements.append(Spacer(1, 40))

        score = report.overall_score
        score_color = self._score_color(score)
        score_text = f'<font color="{score_color}" size="48"><b>{score}</b></font><font color="{COLORS["muted"].hexval()}" size="16">/100</font>'
        elements.append(Paragraph(score_text, ParagraphStyle(
            name="ScoreDisplay", alignment=TA_CENTER, spaceBefore=0, spaceAfter=8
        )))

        score_label = self._score_label(score)
        elements.append(Paragraph(
            f'<font color="{score_color}">{score_label}</font>',
            ParagraphStyle(name="ScoreLabel", alignment=TA_CENTER, fontSize=14,
                           fontName="Helvetica-Bold", spaceAfter=30)
        ))

        stats_data = [
            ["Pages Audited", "Total Issues", "Critical", "Serious"],
            [
                str(report.total_pages_audited),
                str(report.total_issues),
                str(report.issues_by_severity.get("critical", 0)),
                str(report.issues_by_severity.get("serious", 0)),
            ],
        ]
        stats_table = Table(stats_data, colWidths=[110, 110, 110, 110])
        stats_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["muted"]),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 20),
            ("TEXTCOLOR", (0, 1), (1, 1), COLORS["dark"]),
            ("TEXTCOLOR", (2, 1), (2, 1), COLORS["critical"]),
            ("TEXTCOLOR", (3, 1), (3, 1), COLORS["serious"]),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(stats_table)

        elements.append(Spacer(1, 60))

        # RAG status on cover
        rag_text = ""
        if report.rag_enabled and report.rag_enriched_count > 0:
            rag_text = f" | RAG: {report.rag_enriched_count} issues enriched with WCAG techniques"
        elif report.rag_enabled:
            rag_text = " | RAG: Enabled"

        elements.append(Paragraph(
            f"Audit ID: {report.audit_id}", self.styles["SmallMuted"]
        ))
        elements.append(Paragraph(
            f"WCAG 2.2 Level {report.wcag_level_targeted.value} | "
            f"Duration: {report.total_duration_seconds:.0f}s{rag_text} | "
            f"Generated by WCAG Audit Agent",
            self.styles["SmallMuted"]
        ))
        return elements

    # ─── Executive Summary ───

    def _build_executive_summary(self, report: AuditReport) -> list:
        elements = []
        elements.append(Paragraph("Executive Summary", self.styles["SectionTitle"]))
        elements.append(HRFlowable(width="100%", color=COLORS["border"], thickness=1))
        elements.append(Spacer(1, 10))

        critical = report.issues_by_severity.get("critical", 0)
        serious = report.issues_by_severity.get("serious", 0)
        moderate = report.issues_by_severity.get("moderate", 0)
        minor = report.issues_by_severity.get("minor", 0)

        summary = (
            f"An automated WCAG 2.2 accessibility audit was performed on "
            f"<b>{report.target_url}</b>, analyzing <b>{report.total_pages_audited}</b> page(s). "
            f"The audit identified <b>{report.total_issues}</b> accessibility issues: "
            f"<font color='{COLORS['critical'].hexval()}'><b>{critical} critical</b></font>, "
            f"<font color='{COLORS['serious'].hexval()}'><b>{serious} serious</b></font>, "
            f"<font color='{COLORS['moderate'].hexval()}'><b>{moderate} moderate</b></font>, and "
            f"<font color='{COLORS['minor'].hexval()}'><b>{minor} minor</b></font>. "
            f"The overall accessibility score is <b>{report.overall_score}/100</b>."
        )

        if report.rag_enabled and report.rag_enriched_count > 0:
            summary += (
                f" Fix suggestions for <b>{report.rag_enriched_count}</b> issues were enriched "
                f"with specific WCAG 2.2 techniques from the knowledge base."
            )

        elements.append(Paragraph(summary, self.styles["BodyText2"]))
        elements.append(Spacer(1, 12))

        # Impact summary
        if report.issues_by_impact_group:
            elements.append(Paragraph("Who is affected:", self.styles["SubSection"]))
            impact_labels = {
                "blind_users": "Blind users (screen reader)",
                "low_vision_users": "Low vision users",
                "motor_impaired_users": "Motor impaired users (keyboard)",
                "cognitive_disability_users": "Cognitive disability users",
                "deaf_users": "Deaf/hard of hearing users",
                "all_users": "All users",
            }
            for group, count in sorted(report.issues_by_impact_group.items(), key=lambda x: -x[1]):
                label = impact_labels.get(group, group)
                elements.append(Paragraph(
                    f"&bull; <b>{label}</b>: {count} issue(s)", self.styles["BodyText2"]
                ))

        # Page scores
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Page Scores:", self.styles["SubSection"]))

        page_data = [["Page URL", "Score", "Critical", "Serious", "Total"]]
        for pr in report.page_reports:
            url_display = pr.page_url if len(pr.page_url) < 50 else pr.page_url[:47] + "..."
            page_data.append([url_display, f"{pr.score}/100", str(pr.critical_count),
                              str(pr.serious_count), str(len(pr.issues))])

        page_table = Table(page_data, colWidths=[220, 60, 55, 55, 50])
        page_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["white"]),
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary"]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["white"], COLORS["light_bg"]]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(page_table)
        return elements

    # ─── Severity Breakdown ───

    def _build_severity_breakdown(self, report: AuditReport) -> list:
        elements = []
        elements.append(Spacer(1, 16))
        elements.append(Paragraph("Issues by Severity", self.styles["SectionTitle"]))
        elements.append(HRFlowable(width="100%", color=COLORS["border"], thickness=1))
        elements.append(Spacer(1, 10))

        data = [["Severity", "Count", "Description"]]
        severity_info = [
            (Severity.CRITICAL, "Blocks access for some users entirely"),
            (Severity.SERIOUS, "Significantly impedes usability for some users"),
            (Severity.MODERATE, "Causes some difficulty but workarounds exist"),
            (Severity.MINOR, "Minor inconvenience, best practice improvement"),
        ]
        for sev, desc in severity_info:
            count = report.issues_by_severity.get(sev.value, 0)
            data.append([SEVERITY_LABELS[sev], str(count), desc])

        table = Table(data, colWidths=[80, 50, 330])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["white"]),
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["dark"]),
            ("TEXTCOLOR", (0, 1), (0, 1), COLORS["critical"]),
            ("TEXTCOLOR", (0, 2), (0, 2), COLORS["serious"]),
            ("TEXTCOLOR", (0, 3), (0, 3), COLORS["moderate"]),
            ("TEXTCOLOR", (0, 4), (0, 4), COLORS["minor"]),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["white"], COLORS["light_bg"]]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.append(table)
        return elements

    # ─── WCAG Principle Breakdown ───

    def _build_principle_breakdown(self, report: AuditReport) -> list:
        elements = []
        elements.append(Spacer(1, 16))
        elements.append(Paragraph("Issues by WCAG Principle", self.styles["SectionTitle"]))
        elements.append(HRFlowable(width="100%", color=COLORS["border"], thickness=1))
        elements.append(Spacer(1, 10))

        principle_desc = {
            "Perceivable": "Content presentable in ways users can perceive",
            "Operable": "UI operable by all users (keyboard, timing, navigation)",
            "Understandable": "Content readable, predictable, input assistance",
            "Robust": "Content robust enough for assistive technologies",
        }

        data = [["Principle", "Issues", "Description"]]
        for principle, count in sorted(report.issues_by_wcag_principle.items(), key=lambda x: -x[1]):
            data.append([principle, str(count), principle_desc.get(principle, "")])

        if len(data) > 1:
            table = Table(data, colWidths=[90, 50, 320])
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["white"]),
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary"]),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border"]),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["white"], COLORS["light_bg"]]),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            elements.append(table)
        return elements

    # ─── Priority Action Plan ───

    def _build_priority_fixes(self, report: AuditReport) -> list:
        elements = []
        elements.append(Paragraph("Priority Action Plan", self.styles["SectionTitle"]))
        elements.append(HRFlowable(width="100%", color=COLORS["border"], thickness=1))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            "Fix these issues first for maximum accessibility improvement:",
            self.styles["BodyText2"]
        ))
        elements.append(Spacer(1, 8))

        for idx, issue in enumerate(report.priority_fixes, 1):
            sev_color = SEVERITY_COLORS.get(issue.severity, COLORS["muted"])
            sev_label = SEVERITY_LABELS.get(issue.severity, "?")

            card = [
                Paragraph(
                    f'<font color="{sev_color.hexval()}"><b>[{sev_label}]</b></font> '
                    f'<b>#{idx}. {self._safe(issue.title)}</b>',
                    self.styles["IssueTitle"]
                ),
                Paragraph(
                    f'WCAG {issue.wcag_criterion} {self._safe(issue.wcag_criterion_name)} | '
                    f'Source: {issue.source}',
                    self.styles["SmallMuted"]
                ),
                Paragraph(self._safe(issue.description[:200]), self.styles["BodyText2"]),
            ]

            if issue.fix_description:
                card.append(Paragraph(
                    f'<b>Fix:</b> {self._safe(issue.fix_description[:250])}',
                    self.styles["BodyText2"]
                ))

            # RAG technique references
            if issue.rag_techniques:
                tech_text = ", ".join(issue.rag_techniques)
                card.append(Paragraph(
                    f'<font color="{COLORS["rag"].hexval()}">📚 WCAG Techniques: {tech_text}</font>',
                    self.styles["RAGRef"]
                ))

            card.extend([
                Spacer(1, 6),
                HRFlowable(width="100%", color=COLORS["border"], thickness=0.5),
            ])
            elements.append(KeepTogether(card))

        return elements

    # ─── Per-Page Findings ───

    def _build_page_section(self, page_report: PageReport) -> list:
        elements = []
        url_display = page_report.page_url
        if len(url_display) > 70:
            url_display = url_display[:67] + "..."

        elements.append(Paragraph(f'Page: {self._safe(url_display)}', self.styles["SectionTitle"]))
        elements.append(HRFlowable(width="100%", color=COLORS["border"], thickness=1))

        score = page_report.score
        score_color = self._score_color(score)
        elements.append(Paragraph(
            f'<font color="{score_color}" size="16"><b>{score}/100</b></font> '
            f'&nbsp;&nbsp; '
            f'<font color="{COLORS["critical"].hexval()}">Critical: {page_report.critical_count}</font> | '
            f'<font color="{COLORS["serious"].hexval()}">Serious: {page_report.serious_count}</font> | '
            f'<font color="{COLORS["moderate"].hexval()}">Moderate: {page_report.moderate_count}</font> | '
            f'<font color="{COLORS["minor"].hexval()}">Minor: {page_report.minor_count}</font>',
            self.styles["BodyText2"]
        ))
        elements.append(Spacer(1, 10))

        # Issues table
        if page_report.issues:
            data = [["#", "Severity", "Issue", "WCAG", "Source"]]
            for idx, issue in enumerate(page_report.issues[:30], 1):
                title = issue.title[:50] + "..." if len(issue.title) > 50 else issue.title
                wcag = issue.wcag_criterion or "-"
                data.append([str(idx), SEVERITY_LABELS.get(issue.severity, "?"),
                             self._safe(title), wcag, issue.source])

            table = Table(data, colWidths=[25, 65, 240, 50, 80])
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLORS["white"]),
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["dark"]),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border"]),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["white"], COLORS["light_bg"]]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            elements.append(table)

            if len(page_report.issues) > 30:
                elements.append(Paragraph(
                    f"... and {len(page_report.issues) - 30} more issues (see JSON)",
                    self.styles["SmallMuted"]
                ))

        # Detailed issue cards
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Issue Details:", self.styles["SubSection"]))

        for issue in page_report.issues[:10]:
            elements.extend(self._build_issue_card(issue))

        return elements

    def _build_issue_card(self, issue: AccessibilityIssue) -> list:
        elements = []
        sev_color = SEVERITY_COLORS.get(issue.severity, COLORS["muted"])
        sev_label = SEVERITY_LABELS.get(issue.severity, "?")

        card = [
            Paragraph(
                f'<font color="{sev_color.hexval()}"><b>[{sev_label}]</b></font> '
                f'<b>{self._safe(issue.title)}</b>',
                self.styles["IssueTitle"]
            ),
            Paragraph(
                f'WCAG {issue.wcag_criterion} {self._safe(issue.wcag_criterion_name)} '
                f'(Level {issue.wcag_level.value}) | Source: {issue.source} | '
                f'Confidence: {issue.confidence:.0%}',
                self.styles["SmallMuted"]
            ),
            Paragraph(self._safe(issue.description[:300]), self.styles["BodyText2"]),
        ]
        elements.append(KeepTogether(card))

        if issue.element_selector:
            elements.append(Paragraph(
                f'<b>Element:</b> <font face="Courier" size="8">{self._safe(issue.element_selector[:120])}</font>',
                self.styles["BodyText2"]
            ))

        if issue.fix_description:
            elements.append(Paragraph(
                f'<b>Fix:</b> {self._safe(issue.fix_description[:300])}',
                self.styles["BodyText2"]
            ))

        if issue.fix_code_before and issue.fix_code_after:
            elements.append(Paragraph(
                f'Before: {self._safe(issue.fix_code_before[:150])}',
                self.styles["CodeBlock"]
            ))
            elements.append(Paragraph(
                f'After:  {self._safe(issue.fix_code_after[:150])}',
                self.styles["CodeBlock"]
            ))

        # RAG technique references
        if issue.rag_techniques:
            tech_text = ", ".join(issue.rag_techniques)
            elements.append(Paragraph(
                f'<font color="{COLORS["rag"].hexval()}">📚 WCAG Techniques: {tech_text}</font>',
                self.styles["RAGRef"]
            ))

        if issue.rag_understanding:
            elements.append(Paragraph(
                f'<i>{self._safe(issue.rag_understanding[:200])}</i>',
                self.styles["SmallMuted"]
            ))

        elements.append(Spacer(1, 4))
        elements.append(HRFlowable(width="100%", color=COLORS["border"], thickness=0.5))

        return elements

    # ─── Helpers ───

    def _safe(self, text: str) -> str:
        if not text:
            return ""
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    def _score_color(self, score: float) -> str:
        if score >= 80: return COLORS["pass"].hexval()
        elif score >= 60: return COLORS["moderate"].hexval()
        elif score >= 40: return COLORS["serious"].hexval()
        else: return COLORS["critical"].hexval()

    def _score_label(self, score: float) -> str:
        if score >= 90: return "Excellent"
        elif score >= 80: return "Good"
        elif score >= 60: return "Needs Improvement"
        elif score >= 40: return "Poor"
        else: return "Critical Issues Found"