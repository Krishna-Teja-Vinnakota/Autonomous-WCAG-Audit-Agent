"""
STEP 2a: Screenshot Collector
==============================
Captures multi-viewport screenshots for each page:
- Desktop (1920x1080)
- Tablet (768x1024)
- Mobile (375x812)
- Zoomed 200% (desktop with 2x zoom)

These screenshots are later sent to the Vision AI agent (Step 3).

API Keys Needed: NONE
"""

import os
import asyncio
from pathlib import Path
from loguru import logger

from playwright.async_api import async_playwright, Page, BrowserContext
from src.models import PageInfo, ScreenshotData


VIEWPORTS = {
    "desktop": {"width": 1920, "height": 1080},
    "tablet": {"width": 768, "height": 1024},
    "mobile": {"width": 375, "height": 812},
}


class ScreenshotCollector:
    """Captures accessibility-focused screenshots of web pages."""
    
    def __init__(self, output_dir: str = "./data/screenshots", quality: int = 80):
        self.output_dir = Path(output_dir)
        self.quality = quality
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, audit_id: str, page_url: str, viewport_name: str) -> str:
        """Generate a screenshot file path."""
        # Create safe filename from URL
        safe_name = page_url.replace("https://", "").replace("http://", "")
        safe_name = safe_name.replace("/", "_").replace("?", "_").replace("&", "_")
        safe_name = safe_name[:80]  # truncate long URLs
        
        page_dir = self.output_dir / audit_id
        page_dir.mkdir(parents=True, exist_ok=True)
        
        return str(page_dir / f"{safe_name}_{viewport_name}.png")
    
    async def _goto(self, page, url: str) -> None:
        """
        Navigate to a URL reliably.

        Strategy:
          1. Try wait_until="load" (60 s) — fires once HTML + blocking resources are ready,
             ignores never-ending XHR/analytics calls (e.g. Amazon, Flipkart).
          2. If that times out, fall back to wait_until="domcontentloaded" (30 s) — fires as
             soon as the DOM is parsed; JS may still be running but the page is visible.
          3. Either way, wait an extra 2 s for client-side rendering to settle.

        This replaces the old wait_until="networkidle" which would time out on any site
        with continuous background network activity.
        """
        try:
            await page.goto(url, wait_until="load", timeout=60000)
        except Exception:
            # Page likely has continuous network activity — use domcontentloaded instead
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

    async def capture_page(
        self,
        context: BrowserContext,
        page_info: PageInfo,
        audit_id: str,
    ) -> ScreenshotData:
        """
        Capture screenshots of a page at multiple viewports.
        
        Args:
            context: Playwright browser context
            page_info: Page to screenshot
            audit_id: Audit ID for file organization
            
        Returns:
            ScreenshotData with file paths to all screenshots
        """
        screenshots = ScreenshotData()
        
        # --- Desktop screenshot ---
        try:
            page = await context.new_page()
            await page.set_viewport_size(VIEWPORTS["desktop"])
            await self._goto(page, page_info.url)
            path = self._get_path(audit_id, page_info.url, "desktop")
            await page.screenshot(path=path, full_page=True)
            screenshots.desktop = path
            logger.info(f"  📸 Desktop screenshot: {page_info.url}")
            await page.close()
        except Exception as e:
            logger.error(f"  ❌ Desktop screenshot failed for {page_info.url}: {e}")

        # --- Tablet screenshot ---
        try:
            page = await context.new_page()
            await page.set_viewport_size(VIEWPORTS["tablet"])
            await self._goto(page, page_info.url)
            path = self._get_path(audit_id, page_info.url, "tablet")
            await page.screenshot(path=path, full_page=True)
            screenshots.tablet = path
            logger.info(f"  📸 Tablet screenshot: {page_info.url}")
            await page.close()
        except Exception as e:
            logger.error(f"  ❌ Tablet screenshot failed: {e}")

        # --- Mobile screenshot ---
        try:
            page = await context.new_page()
            await page.set_viewport_size(VIEWPORTS["mobile"])
            await self._goto(page, page_info.url)
            path = self._get_path(audit_id, page_info.url, "mobile")
            await page.screenshot(path=path, full_page=True)
            screenshots.mobile = path
            logger.info(f"  📸 Mobile screenshot: {page_info.url}")
            await page.close()
        except Exception as e:
            logger.error(f"  ❌ Mobile screenshot failed: {e}")

        # --- 200% Zoom screenshot ---
        try:
            page = await context.new_page()
            await page.set_viewport_size(VIEWPORTS["desktop"])
            await self._goto(page, page_info.url)
            # Apply 200% zoom via CSS transform
            await page.evaluate("""
                document.body.style.transform = 'scale(2)';
                document.body.style.transformOrigin = 'top left';
                document.body.style.width = '50%';
            """)
            await page.wait_for_timeout(500)
            path = self._get_path(audit_id, page_info.url, "zoomed_200")
            await page.screenshot(path=path, full_page=True)
            screenshots.zoomed_200 = path
            logger.info(f"  📸 200% Zoom screenshot: {page_info.url}")
            await page.close()
        except Exception as e:
            logger.error(f"  ❌ Zoom screenshot failed: {e}")
        
        return screenshots
