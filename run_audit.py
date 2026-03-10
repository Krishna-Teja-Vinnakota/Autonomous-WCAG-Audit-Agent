#!/usr/bin/env python3
"""
WCAG Accessibility Audit Agent - Quick Start
=============================================
Run Steps 1 & 2: Crawl a website and collect accessibility data.

Usage:
    python run_audit.py https://example.com
    python run_audit.py https://example.com --max-pages 10
    python run_audit.py https://example.com --max-pages 5 --wcag-level wcag2aaa
    # if the site requires login the tool will prompt or you can pass --auth
    python run_audit.py https://secure.example.com --auth
"""

import asyncio
import argparse
from getpass import getpass
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pipeline import AuditDataPipeline
from src.models import AuthConfig


def parse_args():
    parser = argparse.ArgumentParser(
        description="WCAG Accessibility Audit Agent"
    )
    parser.add_argument(
        "url",
        help="Target URL to audit"
    )
    parser.add_argument(
        "--auth", "-a",
        action="store_true",
        help="Prompt for login credentials before crawling"
    )
    parser.add_argument(
        "--max-pages", "-m",
        type=int,
        default=5,
        help="Maximum number of pages to crawl (default: 5)"
    )
    parser.add_argument(
        "--wcag-level", "-w",
        choices=["wcag2a", "wcag2aa", "wcag2aaa"],
        default="wcag2aa",
        help="WCAG conformance level (default: wcag2aa)"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible window)"
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="./data",
        help="Output directory for screenshots and data (default: ./data)"
    )
    return parser.parse_args()


async def run():
    args = parse_args()
    
    # global authentication prompt
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

    print(f"""
╔══════════════════════════════════════════════════╗
║     WCAG Accessibility Audit Agent v1.0          ║
║     Steps 1 & 2: Crawl + Collect                 ║
╚══════════════════════════════════════════════════╝

  Target URL:  {args.url}
  Max Pages:   {args.max_pages}
  WCAG Level:  {args.wcag_level}
  Browser:     {'Headed' if args.headed else 'Headless'}
  Output:      {args.output_dir}
  Authentication: {'enabled' if auth_conf else 'none'}
""")
    
    pipeline = AuditDataPipeline(
        max_pages=args.max_pages,
        headless=not args.headed,
        screenshot_dir=f"{args.output_dir}/screenshots",
        wcag_level=args.wcag_level,
    )
    
    crawl_result, page_data = await pipeline.run(args.url, auth=auth_conf)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 STEP 1 & 2 COMPLETE")
    print(f"{'='*60}")
    print(f"  Audit ID:       {crawl_result.audit_id}")
    print(f"  Pages crawled:  {crawl_result.pages_crawled}")
    print(f"  Total axe violations: {sum(r.axe_results.total_violations for r in page_data)}")
    print(f"  Total focus issues:   {sum(len(r.keyboard_nav.focus_visible_issues) for r in page_data)}")
    
    print(f"\n✅ Data collection complete!")
    print(f"   Next: Run Step 3 (AI Analysis) — requires Vertex AI credentials")
    
    return crawl_result, page_data


if __name__ == "__main__":
    asyncio.run(run())
