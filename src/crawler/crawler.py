"""
STEP 1: Website Crawler
========================
Discovers all pages on a target website using Playwright.
- Opens a real Chromium browser (headless)
- Starts from the target URL
- Follows internal links up to max_pages limit
- Respects same-domain boundary
- Returns list of PageInfo objects

API Keys Needed: NONE (runs locally)
"""

import asyncio
from urllib.parse import urlparse, urljoin, urldefrag
from typing import Set, List, Optional
from datetime import datetime
from loguru import logger

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from src.models import PageInfo, CrawlResult, AuthConfig


class WebsiteCrawler:
    """Crawls a website and discovers all accessible pages."""
    
    def __init__(
        self,
        max_pages: int = 20,
        timeout_ms: int = 30000,
        headless: bool = True,
        max_depth: int = 3,
    ):
        self.max_pages = max_pages
        self.timeout_ms = timeout_ms
        self.headless = headless
        self.max_depth = max_depth
        
        # State
        self._visited: Set[str] = set()
        self._queue: List[tuple] = []  # (url, depth, parent_url)
        self._pages: List[PageInfo] = []
        self._errors: List[str] = []
        self._base_domain: str = ""
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL: remove fragment, trailing slash, lowercase domain."""
        url, _ = urldefrag(url)
        parsed = urlparse(url)
        # Rebuild without fragment, normalize
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized.endswith("/") and len(parsed.path) > 1:
            normalized = normalized[:-1]
        return normalized
    
    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain as target."""
        try:
            parsed = urlparse(url)
            return parsed.netloc == self._base_domain or \
                   parsed.netloc.endswith(f".{self._base_domain}")
        except Exception:
            return False
    
    def _is_valid_page_url(self, url: str) -> bool:
        """Filter out non-page URLs (images, files, etc.)."""
        skip_extensions = {
            '.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',
            '.mp4', '.mp3', '.wav', '.zip', '.tar', '.gz',
            '.css', '.js', '.json', '.xml', '.ico', '.woff', '.woff2', '.ttf'
        }
        parsed = urlparse(url)
        path_lower = parsed.path.lower()
        
        # Skip non-http(s) schemes
        if parsed.scheme not in ('http', 'https'):
            return False
        
        # Skip file extensions that aren't pages
        for ext in skip_extensions:
            if path_lower.endswith(ext):
                return False
        
        # Skip common non-page paths
        skip_paths = ['/wp-json/', '/api/', '/feed', '/rss', '/.well-known/']
        for skip in skip_paths:
            if skip in path_lower:
                return False
        
        return True
    
    async def _extract_links(self, page: Page, current_url: str) -> List[str]:
        """Extract all internal links from a page."""
        links = []
        try:
            # Get all anchor hrefs
            hrefs = await page.eval_on_selector_all(
                "a[href]",
                "elements => elements.map(el => el.href)"
            )
            
            for href in hrefs:
                if not href:
                    continue
                
                # Resolve relative URLs
                absolute_url = urljoin(current_url, href)
                normalized = self._normalize_url(absolute_url)
                
                if (self._is_same_domain(normalized) and 
                    self._is_valid_page_url(normalized) and
                    normalized not in self._visited):
                    links.append(normalized)
                    
        except Exception as e:
            logger.warning(f"Error extracting links from {current_url}: {e}")
        
        return links
    
    async def _visit_page(
        self, 
        context: BrowserContext, 
        url: str, 
        depth: int,
        parent_url: Optional[str]
    ) -> Optional[PageInfo]:
        """Visit a single page and collect basic info."""
        page = await context.new_page()
        
        try:
            logger.info(f"  Visiting [{depth}]: {url}")
            
            response = await page.goto(
                url, 
                wait_until="networkidle",
                timeout=self.timeout_ms
            )
            
            if response is None:
                self._errors.append(f"No response from {url}")
                return None
            
            status_code = response.status
            content_type = response.headers.get("content-type", "text/html")
            
            # Skip non-HTML responses
            if "text/html" not in content_type:
                return None
            
            # Get page title
            title = await page.title() or ""
            
            # Wait a moment for any dynamic content
            await page.wait_for_timeout(1000)
            
            # Create PageInfo
            page_info = PageInfo(
                url=url,
                title=title,
                depth=depth,
                parent_url=parent_url,
                status_code=status_code,
                content_type=content_type,
            )
            
            # Extract links for further crawling (skip when auditing a single page)
            if self.max_pages > 1 and depth < self.max_depth:
                new_links = await self._extract_links(page, url)
                for link in new_links:
                    if link not in self._visited and len(self._visited) + len(self._queue) < self.max_pages * 2:
                        self._queue.append((link, depth + 1, url))
            
            return page_info
            
        except Exception as e:
            error_msg = f"Error visiting {url}: {str(e)}"
            logger.error(error_msg)
            self._errors.append(error_msg)
            return None
            
        finally:
            await page.close()
    
    async def crawl(
        self, 
        target_url: str, 
        audit_id: Optional[str] = None,
        auth: Optional[AuthConfig] = None,
    ) -> CrawlResult:
        """
        Main crawl method: discovers all pages on the target website.
        
        Args:
            target_url: The starting URL to crawl
            audit_id: Optional audit ID for tracking
            auth: Optional authentication configuration; if supplied the crawler
                  will log in once before traversing pages.
        
        Returns:
            CrawlResult with all discovered pages
        """
        # Initialize
        normalized_target = self._normalize_url(target_url)
        self._base_domain = urlparse(normalized_target).netloc
        self._visited = set()
        self._queue = [(normalized_target, 0, None)]
        self._pages = []
        self._errors = []
        
        result = CrawlResult(
            target_url=target_url,
            audit_id=audit_id or CrawlResult.__fields__["audit_id"].default_factory(),
        )
        
        logger.info(f"Starting crawl of {target_url} (max {self.max_pages} pages)")
        
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="WCAG-Audit-Bot/1.0 (Accessibility Audit Tool)",
            )

            # if auth information was provided, perform a login step now so that
            # the session cookies are available to all later pages.
            if auth:
                try:
                    login_url = auth.login_url or target_url
                    logger.info(f"  authenticating at {login_url}")
                    page = await context.new_page()
                    await page.goto(login_url, wait_until="networkidle", timeout=self.timeout_ms)
                    await page.fill(auth.user_selector, auth.username)
                    await page.fill(auth.pass_selector, auth.password)
                    await page.click(auth.submit_selector)
                    await page.wait_for_load_state("networkidle")
                    await page.close()
                    logger.info("  ✅ authentication successful")
                except Exception as e:
                    logger.error(f"Authentication failed during crawl: {e}")

            try:
                while self._queue and len(self._pages) < self.max_pages:
                    url, depth, parent = self._queue.pop(0)
                    
                    # Skip if already visited
                    if url in self._visited:
                        continue
                    
                    self._visited.add(url)
                    
                    # Visit the page
                    page_info = await self._visit_page(context, url, depth, parent)
                    
                    if page_info:
                        self._pages.append(page_info)
                
            finally:
                await browser.close()
        
        # Build result
        result.pages = self._pages
        result.total_pages_found = len(self._visited)
        result.pages_crawled = len(self._pages)
        result.crawl_end = datetime.utcnow()
        result.errors = self._errors
        
        logger.info(
            f"Crawl complete: {result.pages_crawled} pages crawled, "
            f"{result.total_pages_found} URLs discovered, "
            f"{len(result.errors)} errors"
        )
        
        return result


# ─── CLI Usage ───────────────────────────────────────────

async def main():
    """Quick test: crawl a URL from command line."""
    import sys
    
    url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    crawler = WebsiteCrawler(max_pages=max_pages, headless=True)
    result = await crawler.crawl(url)
    
    print(f"\n{'='*60}")
    print(f"CRAWL RESULTS: {result.target_url}")
    print(f"{'='*60}")
    print(f"Pages crawled: {result.pages_crawled}")
    print(f"Total URLs found: {result.total_pages_found}")
    print(f"Errors: {len(result.errors)}")
    print(f"\nPages discovered:")
    for p in result.pages:
        print(f"  [{p.depth}] {p.title or 'No title'}: {p.url}")
    
    if result.errors:
        print(f"\nErrors:")
        for e in result.errors:
            print(f"  ⚠ {e}")


if __name__ == "__main__":
    asyncio.run(main())
