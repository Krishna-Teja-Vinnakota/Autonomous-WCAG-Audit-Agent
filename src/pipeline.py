"""
STEP 1 + 2 PIPELINE: Crawl & Collect
======================================
Orchestrates the full data collection process:
1. Crawl the website to discover pages
2. For each page, collect:
   - Screenshots (4 viewports)
   - DOM content (full + semantic snapshot)
   - axe-core scan results
   - Keyboard navigation recording

This is the entry point for the first two steps.

API Keys Needed: NONE — everything runs locally.
"""

import asyncio
import time
from typing import List, Optional
from loguru import logger

from playwright.async_api import async_playwright
from src.models import (
    CrawlResult, PageInfo, PageCollectionResult, 
    ScreenshotData, AxeResult, KeyboardNavData, AuthConfig
)
from src.crawler.crawler import WebsiteCrawler
from src.collectors.screenshot_collector import ScreenshotCollector
from src.collectors.dom_collector import DOMCollector
from src.collectors.axe_scanner import AxeCoreScanner
from src.collectors.keyboard_recorder import KeyboardNavRecorder


class AuditDataPipeline:
    """
    Runs the complete data collection pipeline for a website audit.
    
    Usage:
        pipeline = AuditDataPipeline(max_pages=10)
        crawl_result, page_data = await pipeline.run("https://example.com")
    """
    
    def __init__(
        self,
        max_pages: int = 20,
        headless: bool = True,
        screenshot_dir: str = "./data/screenshots",
        wcag_level: str = "wcag2aa",
    ):
        self.crawler = WebsiteCrawler(max_pages=max_pages, headless=headless)
        self.screenshot_collector = ScreenshotCollector(output_dir=screenshot_dir)
        self.dom_collector = DOMCollector()
        self.axe_scanner = AxeCoreScanner(wcag_level=wcag_level)
        self.keyboard_recorder = KeyboardNavRecorder()
        self.headless = headless
    
    async def run(
        self, 
        target_url: str,
        audit_id: Optional[str] = None,
        auth: Optional[AuthConfig] = None,
    ) -> tuple[CrawlResult, List[PageCollectionResult]]:
        """
        Run the complete pipeline.
        
        Args:
            target_url: URL to audit
            audit_id: Optional tracking ID
            auth: Optional authentication configuration.  When provided the
                  pipeline will perform a login step in the browser context
                  before crawling or collecting any pages.
        
        Returns:
            Tuple of (CrawlResult, list of PageCollectionResult)
        """
        overall_start = time.time()
        
        # ─── STEP 1: Crawl (or skip for single-page mode) ───
        logger.info(f"{'='*60}")
        if auth:
            logger.info("STEP 0: AUTHENTICATION REQUESTED")
        if self.crawler.max_pages == 1:
            logger.info(f"STEP 1: SINGLE-PAGE MODE — {target_url}")
            logger.info(f"{'='*60}")
            # Skip the crawler entirely: no need to open a browser just to get a page title.
            # The title will be filled in during data collection below.
            crawl_result = CrawlResult(target_url=target_url)
            if audit_id:
                crawl_result.audit_id = audit_id
            crawl_result.pages = [PageInfo(url=target_url, title="", depth=0)]
            crawl_result.pages_crawled = 1
            crawl_result.total_pages_found = 1
        else:
            logger.info(f"STEP 1: CRAWLING {target_url}")
            logger.info(f"{'='*60}")
            crawl_result = await self.crawler.crawl(
                target_url,
                audit_id=audit_id,
                auth=auth,
            )
        
        if not crawl_result.pages:
            logger.error("No pages found during crawl!")
            return crawl_result, []
        
        # ─── STEP 2: Collect Data Per Page ───
        logger.info(f"\n{'='*60}")
        logger.info(f"STEP 2: COLLECTING DATA ({len(crawl_result.pages)} pages)")
        logger.info(f"{'='*60}")
        
        page_results: List[PageCollectionResult] = []
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="WCAG-Audit-Bot/1.0 (Accessibility Audit Tool)",
            )
            
            # perform login in the collection context as well
            if auth:
                try:
                    logger.info("  🔐 authenticating collection context")
                    await auth.perform_login(context, target_url)
                except Exception as e:
                    logger.error(f"Authentication failed during collection: {e}")

            try:
                for i, page_info in enumerate(crawl_result.pages):
                    page_start = time.time()
                    logger.info(f"\n--- Page {i+1}/{len(crawl_result.pages)}: {page_info.url} ---")
                    
                    result = PageCollectionResult(page=page_info)
                    
                    # Open the page once for DOM + axe + keyboard
                    page = await context.new_page()
                    try:
                        await page.goto(
                            page_info.url,
                            wait_until="networkidle",
                            timeout=30000
                        )
                        await page.wait_for_timeout(1000)

                        # Fill title if the crawler was skipped (single-page mode)
                        if not page_info.title:
                            page_info.title = await page.title() or ""
                        
                        # 2a. Screenshots (uses its own pages for different viewports)
                        result.screenshots = await self.screenshot_collector.capture_page(
                            context, page_info, crawl_result.audit_id
                        )
                        
                        # 2b. DOM content
                        result.dom_content = await self.dom_collector.extract_full_dom(page)
                        result.dom_snapshot = await self.dom_collector.extract_semantic_snapshot(page)
                        
                        # 2c. axe-core scan
                        result.axe_results = await self.axe_scanner.scan_page(page, page_info.url)
                        
                        # 2d. Keyboard navigation
                        result.keyboard_nav = await self.keyboard_recorder.record_tab_order(
                            page, page_info.url
                        )
                        
                    except Exception as e:
                        logger.error(f"  ❌ Error collecting data for {page_info.url}: {e}")
                    finally:
                        await page.close()
                    
                    result.collection_time_seconds = time.time() - page_start
                    page_results.append(result)
                    
                    logger.info(
                        f"  ⏱️  Page collected in {result.collection_time_seconds:.1f}s"
                    )
                    
            finally:
                await browser.close()
        
        total_time = time.time() - overall_start
        
        # ─── Summary ───
        logger.info(f"\n{'='*60}")
        logger.info("PIPELINE SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total pages crawled: {len(crawl_result.pages)}")
        logger.info(f"Total pages collected: {len(page_results)}")
        
        total_violations = sum(r.axe_results.total_violations for r in page_results)
        total_nodes = sum(r.axe_results.total_nodes_affected for r in page_results)
        logger.info(f"Total axe-core violations: {total_violations} ({total_nodes} nodes)")
        
        total_keyboard_issues = sum(len(r.keyboard_nav.focus_visible_issues) for r in page_results)
        logger.info(f"Total keyboard focus issues: {total_keyboard_issues}")
        
        logger.info(f"Total time: {total_time:.1f}s")
        
        return crawl_result, page_results


# ─── CLI Entry Point ─────────────────────────────────────

async def main():
    """Run the pipeline from command line."""
    import sys
    import json
    from getpass import getpass
    from src.models import AuthConfig
    
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    # simple CLI prompt for authentication
    auth_conf = None
    ans = input("Does this site require authentication? [y/N] ").strip().lower()
    if ans.startswith('y'):
        username = input("Username/email: ")
        password = getpass("Password: ")
        user_sel = input("Username selector [input.form-input[type=\"email\"]]: ").strip() or "input.form-input[type=\"email\"]"
        pass_sel = input("Password selector [input.form-input[type=\"password\"]]: ").strip() or "input.form-input[type=\"password\"]"
        submit_sel = input("Submit selector [button.login-btn[type=\"submit\"]]: ").strip() or "button.login-btn[type=\"submit\"]"
        auth_conf = AuthConfig(username=username, password=password, user_selector=user_sel, pass_selector=pass_sel, submit_selector=submit_sel)

    print(f"\n🚀 Starting WCAG Accessibility Audit Pipeline")
    print(f"   Target: {url}")
    print(f"   Max pages: {max_pages}\n")
    
    pipeline = AuditDataPipeline(max_pages=max_pages, headless=True)
    crawl_result, page_data = await pipeline.run(url, auth=auth_conf)
    
    # Print results summary
    print(f"\n{'='*60}")
    print(f"📊 RESULTS SUMMARY")
    print(f"{'='*60}")
    
    for pr in page_data:
        print(f"\n📄 {pr.page.title or pr.page.url}")
        print(f"   URL: {pr.page.url}")
        print(f"   Screenshots: {sum(1 for s in [pr.screenshots.desktop, pr.screenshots.tablet, pr.screenshots.mobile, pr.screenshots.zoomed_200] if s)}/4")
        print(f"   DOM size: {len(pr.dom_content):,} chars")
        print(f"   Semantic snapshot: {len(pr.dom_snapshot):,} chars")
        print(f"   axe-core violations: {pr.axe_results.total_violations}")
        
        if pr.axe_results.violations:
            for v in pr.axe_results.violations[:5]:
                print(f"     ⚠️  [{v.impact}] {v.rule_id}: {v.help_text}")
        
        print(f"   Focusable elements: {pr.keyboard_nav.total_focusable}")
        print(f"   Skip link: {'✅' if pr.keyboard_nav.skip_link_present else '❌'}")
        print(f"   Focus indicator issues: {len(pr.keyboard_nav.focus_visible_issues)}")
        print(f"   Collection time: {pr.collection_time_seconds:.1f}s")
    
    # Save raw data as JSON for inspection
    output = {
        "audit_id": crawl_result.audit_id,
        "target_url": crawl_result.target_url,
        "pages_crawled": crawl_result.pages_crawled,
        "pages": [
            {
                "url": pr.page.url,
                "title": pr.page.title,
                "axe_violations": pr.axe_results.total_violations,
                "axe_details": [
                    {
                        "rule": v.rule_id,
                        "impact": v.impact,
                        "description": v.help_text,
                        "nodes_affected": v.node_count,
                        "wcag_tags": v.wcag_tags,
                    }
                    for v in pr.axe_results.violations
                ],
                "keyboard": {
                    "focusable_elements": pr.keyboard_nav.total_focusable,
                    "skip_link": pr.keyboard_nav.skip_link_present,
                    "focus_issues": pr.keyboard_nav.focus_visible_issues[:5],
                },
                "screenshots": {
                    "desktop": pr.screenshots.desktop,
                    "tablet": pr.screenshots.tablet,
                    "mobile": pr.screenshots.mobile,
                    "zoomed": pr.screenshots.zoomed_200,
                }
            }
            for pr in page_data
        ]
    }
    
    output_path = f"./data/audit_{crawl_result.audit_id[:8]}_raw.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    
    print(f"\n💾 Raw data saved to: {output_path}")
    print(f"\n✅ Step 1 & 2 complete! Ready for Step 3 (AI Analysis).")


if __name__ == "__main__":
    asyncio.run(main())
