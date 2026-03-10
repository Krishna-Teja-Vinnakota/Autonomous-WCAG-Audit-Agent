#!/usr/bin/env python3
"""
WCAG Accessibility Audit Agent - Full Pipeline
================================================
Steps 1 + 2 + 3 + (4) + 5: Crawl → Collect → Analyze → (RAG Enrich) → Report

Setup:
    1. Fill in .env with GCP + Pinecone credentials
    2. Run build_knowledge_base.py once (for RAG)
    3. python run_step5.py https://www.swiggy.com/instamart --max-pages 3
    # supply --auth or answer "y" at prompt for authenticated sites

RAG is optional — if Pinecone isn't configured, the pipeline runs without it.
"""

import asyncio
import argparse
import sys
import os
import json
import time
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    validate_vertex_ai, print_config,
    PINECONE_API_KEY, PINECONE_INDEX_NAME,
)
from src.pipeline import AuditDataPipeline
from src.models import AuthConfig
from src.agents.orchestrator import AgentOrchestrator
from src.aggregator.deduplicator import ReportAggregator
from src.reports.pdf_generator import PDFReportGenerator
from src.models import Severity


def parse_args():
    parser = argparse.ArgumentParser(description="WCAG Audit - Full Pipeline")
    parser.add_argument("url", help="Target URL to audit")
    parser.add_argument("--auth", "-a", action="store_true", help="Prompt for login credentials before crawling")
    parser.add_argument("--max-pages", "-m", type=int, default=1, help="Max pages to audit (default: 1 — audits only the given URL)")
    parser.add_argument("--wcag-level", "-w", default="wcag2aa", help="WCAG level")
    parser.add_argument("--output-dir", "-o", default="./data", help="Output directory")
    parser.add_argument("--no-rag", action="store_true", help="Disable RAG enrichment")
    return parser.parse_args()


async def run():
    args = parse_args()

    # auth prompt
    auth_conf = None
    if args.auth:
        username = input("Username/email: ")
        password = getpass("Password: ")
        user_sel = input("Username selector [input.form-input[type=\"email\"]]: ").strip() or "input.form-input[type=\"email\"]"
        pass_sel = input("Password selector [input.form-input[type=\"password\"]]: ").strip() or "input.form-input[type=\"password\"]"
        submit_sel = input("Submit selector [button.login-btn[type=\"submit\"]]: ").strip() or "button.login-btn[type=\"submit\"]"
        auth_conf = AuthConfig(username=username, password=password, user_selector=user_sel, pass_selector=pass_sel, submit_selector=submit_sel)
    else:
        ans = input("Does this site require authentication? [y/N] ").strip().lower()
        if ans.startswith('y'):
            username = input("Username/email: ")
            password = getpass("Password: ")
            user_sel = input("Username selector [input.form-input[type=\"email\"]]: ").strip() or "input.form-input[type=\"email\"]"
            pass_sel = input("Password selector [input.form-input[type=\"password\"]]: ").strip() or "input.form-input[type=\"password\"]"
            submit_sel = input("Submit selector [button.login-btn[type=\"submit\"]]: ").strip() or "button.login-btn[type=\"submit\"]"
            auth_conf = AuthConfig(username=username, password=password, user_selector=user_sel, pass_selector=pass_sel, submit_selector=submit_sel)

    validate_vertex_ai()
    total_start = time.time()

    rag_status = "Disabled (--no-rag)" if args.no_rag else (
        f"✅ Enabled (Pinecone: {PINECONE_INDEX_NAME})" if PINECONE_API_KEY
        else "⚠️ Not configured (add PINECONE_API_KEY to .env)"
    )

    print(f"""
╔══════════════════════════════════════════════════╗
║     WCAG Accessibility Audit Agent v1.0          ║
║     Full Pipeline: Crawl → Analyze → Report      ║
╚══════════════════════════════════════════════════╝

  Target URL:   {args.url}
  Mode:         {"Single Page (exact URL only)" if args.max_pages == 1 else f"Multi-Page (up to {args.max_pages} pages)"}
  WCAG Level:   {args.wcag_level}
  Output Dir:   {args.output_dir}
  RAG:          {rag_status}
  Authentication: {'enabled' if auth_conf else 'none'}
""")
    print_config()
    print()

    # ─── Steps 1 + 2: Crawl & Collect ───
    pipeline = AuditDataPipeline(
        max_pages=args.max_pages,
        headless=True,
        wcag_level=args.wcag_level,
    )
    crawl_result, page_data = await pipeline.run(args.url, auth=auth_conf)

    if not page_data:
        print("❌ No pages collected. Exiting.")
        sys.exit(1)

    # ─── Step 3: AI Analysis ───
    orchestrator = AgentOrchestrator()
    analysis_results = await orchestrator.analyze_all_pages(page_data)

    # ─── Step 4+5: Aggregation with RAG Enrichment ───
    total_duration = time.time() - total_start
    enable_rag = not args.no_rag and bool(PINECONE_API_KEY)
    aggregator = ReportAggregator(enable_rag=enable_rag)
    report = aggregator.build_report(
        audit_id=crawl_result.audit_id,
        target_url=crawl_result.target_url,
        analysis_results=analysis_results,
        total_duration=total_duration,
    )

    # Track RAG stats
    rag_enriched = sum(
        1 for pr in report.page_reports
        for i in pr.issues if i.rag_techniques
    )
    report.rag_enabled = enable_rag
    report.rag_enriched_count = rag_enriched

    # ─── Step 5: PDF Report ───
    os.makedirs(args.output_dir, exist_ok=True)
    pdf_generator = PDFReportGenerator(output_dir=args.output_dir)
    pdf_path = pdf_generator.generate(report)
    report.pdf_path = pdf_path

    # ─── Step 5: JSON Report ───
    json_path = os.path.join(
        args.output_dir,
        f"wcag_audit_{crawl_result.audit_id[:8]}_report.json"
    )

    json_output = {
        "audit_id": report.audit_id,
        "target_url": report.target_url,
        "audit_date": report.audit_date.isoformat(),
        "overall_score": report.overall_score,
        "total_issues": report.total_issues,
        "total_pages_audited": report.total_pages_audited,
        "total_duration_seconds": round(report.total_duration_seconds, 1),
        "rag_enabled": report.rag_enabled,
        "rag_enriched_count": rag_enriched,
        "severity_summary": report.issues_by_severity,
        "wcag_principle_summary": report.issues_by_wcag_principle,
        "impact_group_summary": report.issues_by_impact_group,
        "priority_fixes": [
            {
                "rank": idx,
                "title": fix.title,
                "severity": fix.severity.value,
                "wcag_criterion": fix.wcag_criterion,
                "wcag_name": fix.wcag_criterion_name,
                "description": fix.description,
                "fix": fix.fix_description,
                "code_before": fix.fix_code_before,
                "code_after": fix.fix_code_after,
                "source": fix.source,
                "rag_techniques": fix.rag_techniques,
                "rag_understanding": fix.rag_understanding[:200] if fix.rag_understanding else "",
            }
            for idx, fix in enumerate(report.priority_fixes, 1)
        ],
        "pages": [
            {
                "url": pr.page_url,
                "score": pr.score,
                "critical": pr.critical_count,
                "serious": pr.serious_count,
                "moderate": pr.moderate_count,
                "minor": pr.minor_count,
                "issues": [
                    {
                        "issue_id": i.issue_id,
                        "source": i.source,
                        "title": i.title,
                        "description": i.description,
                        "wcag_criterion": i.wcag_criterion,
                        "wcag_criterion_name": i.wcag_criterion_name,
                        "wcag_level": i.wcag_level.value,
                        "severity": i.severity.value,
                        "impact_groups": [g.value for g in i.impact_groups],
                        "element_selector": i.element_selector,
                        "element_html": i.element_html[:200] if i.element_html else "",
                        "fix_description": i.fix_description,
                        "fix_code_before": i.fix_code_before,
                        "fix_code_after": i.fix_code_after,
                        "confidence": i.confidence,
                        "rag_techniques": i.rag_techniques,
                    }
                    for i in pr.issues
                ],
            }
            for pr in report.page_reports
        ],
    }

    with open(json_path, "w") as f:
        json.dump(json_output, f, indent=2)
    report.json_path = json_path

    # ─── Final Summary ───
    total_time = time.time() - total_start

    severity_icons = {
        Severity.CRITICAL: "🔴",
        Severity.SERIOUS: "🟠",
        Severity.MODERATE: "🟡",
        Severity.MINOR: "🔵",
    }

    print(f"\n{'='*60}")
    print(f"✅ AUDIT COMPLETE")
    print(f"{'='*60}")
    print(f"  Score:      {report.overall_score}/100")
    print(f"  Pages:      {report.total_pages_audited}")
    print(f"  Issues:     {report.total_issues}")
    print(f"    {severity_icons[Severity.CRITICAL]} Critical: {report.issues_by_severity.get('critical', 0)}")
    print(f"    {severity_icons[Severity.SERIOUS]} Serious:  {report.issues_by_severity.get('serious', 0)}")
    print(f"    {severity_icons[Severity.MODERATE]} Moderate: {report.issues_by_severity.get('moderate', 0)}")
    print(f"    {severity_icons[Severity.MINOR]} Minor:    {report.issues_by_severity.get('minor', 0)}")
    print(f"  RAG:        {'✅ ' + str(rag_enriched) + ' issues enriched' if rag_enriched else ('⚠️ Not configured' if not enable_rag else '0 enriched')}")
    print(f"  Duration:   {total_time:.1f}s")
    print(f"\n  📄 PDF Report: {pdf_path}")
    print(f"  📋 JSON Report: {json_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run())