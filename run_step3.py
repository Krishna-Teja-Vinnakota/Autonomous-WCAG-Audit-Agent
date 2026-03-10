#!/usr/bin/env python3
"""
WCAG Accessibility Audit Agent - Steps 1 + 2 + 3
==================================================
Crawl → Collect → AI Analysis

Setup:
    1. Fill in your .env file (copy from .env.example)
    2. Place service-account.json in project root
    3. Run: python run_step3.py https://www.swiggy.com/instamart --max-pages 2
    # use --auth or answer "y" when prompted if a login is required
"""

import asyncio
import argparse
import sys
import os
import json
from getpass import getpass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# This import loads .env and sets GOOGLE_APPLICATION_CREDENTIALS automatically
from config.settings import (
    GCP_PROJECT_ID, GCP_REGION, GEMINI_MODEL,
    GOOGLE_APPLICATION_CREDENTIALS, validate_vertex_ai, print_config
)
from src.pipeline import AuditDataPipeline
from src.models import AuthConfig
from src.agents.orchestrator import AgentOrchestrator
from src.models import Severity


def parse_args():
    parser = argparse.ArgumentParser(description="WCAG Audit - Steps 1+2+3")
    parser.add_argument("url", help="Target URL to audit")
    parser.add_argument("--auth", "-a", action="store_true", help="Prompt for login credentials before crawling")
    parser.add_argument("--max-pages", "-m", type=int, default=3, help="Max pages (default: 3)")
    parser.add_argument("--wcag-level", "-w", default="wcag2aa", help="WCAG level")
    return parser.parse_args()


async def run():
    args = parse_args()

    # prompt for optional authentication
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

    # Validate credentials from .env
    validate_vertex_ai()

    print(f"""
╔══════════════════════════════════════════════════╗
║     WCAG Accessibility Audit Agent v1.0          ║
║     Steps 1 + 2 + 3: Crawl → Collect → Analyze  ║
╚══════════════════════════════════════════════════╝

  Target URL:   {args.url}
  Max Pages:    {args.max_pages}
  WCAG Level:   {args.wcag_level}
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

    # ─── Summary Report ───
    print(f"\n{'='*60}")
    print("📊 COMPLETE AUDIT RESULTS")
    print(f"{'='*60}")

    severity_icons = {
        Severity.CRITICAL: "🔴 CRITICAL",
        Severity.SERIOUS: "🟠 SERIOUS",
        Severity.MODERATE: "🟡 MODERATE",
        Severity.MINOR: "🔵 MINOR",
    }

    total_issues = 0
    severity_totals = {s: 0 for s in Severity}

    for url, issues in analysis_results.items():
        print(f"\n📄 {url} ({len(issues)} issues)")

        by_severity = {}
        for issue in issues:
            by_severity.setdefault(issue.severity, []).append(issue)

        for sev in [Severity.CRITICAL, Severity.SERIOUS, Severity.MODERATE, Severity.MINOR]:
            sev_issues = by_severity.get(sev, [])
            if sev_issues:
                print(f"\n  {severity_icons[sev]} ({len(sev_issues)})")
                for issue in sev_issues[:5]:
                    print(f"    • [{issue.source}] {issue.title}")
                    if issue.wcag_criterion:
                        print(f"      WCAG {issue.wcag_criterion} {issue.wcag_criterion_name}")
                if len(sev_issues) > 5:
                    print(f"    ... +{len(sev_issues) - 5} more")

            severity_totals[sev] += len(sev_issues)
        total_issues += len(issues)

    print(f"\n{'='*60}")
    print(f"GRAND TOTAL: {total_issues} issues across {len(analysis_results)} pages")
    print(f"  🔴 Critical: {severity_totals[Severity.CRITICAL]}")
    print(f"  🟠 Serious:  {severity_totals[Severity.SERIOUS]}")
    print(f"  🟡 Moderate: {severity_totals[Severity.MODERATE]}")
    print(f"  🔵 Minor:    {severity_totals[Severity.MINOR]}")
    print(f"{'='*60}")

    # ─── Save Full Results ───
    output_path = f"./data/audit_{crawl_result.audit_id[:8]}_full.json"
    output = {
        "audit_id": crawl_result.audit_id,
        "target_url": crawl_result.target_url,
        "pages_audited": len(analysis_results),
        "total_issues": total_issues,
        "severity_summary": {s.value: severity_totals[s] for s in Severity},
        "pages": {}
    }

    for url, issues in analysis_results.items():
        output["pages"][url] = [
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
                "element_html": i.element_html[:200],
                "fix_description": i.fix_description,
                "fix_code_before": i.fix_code_before,
                "fix_code_after": i.fix_code_after,
                "confidence": i.confidence,
            }
            for i in issues
        ]

    os.makedirs("./data", exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n💾 Full results saved to: {output_path}")
    print(f"\n✅ Steps 1+2+3 complete!")
    print(f"   Next: Step 4 (RAG) — needs PINECONE_API_KEY in .env")
    print(f"   Or:   Step 5 (Aggregation + Report)")


if __name__ == "__main__":
    asyncio.run(run())
