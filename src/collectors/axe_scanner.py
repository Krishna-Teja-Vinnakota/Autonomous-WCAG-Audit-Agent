"""
STEP 2c: axe-core Accessibility Scanner
=========================================
Runs axe-core automated accessibility checks in the browser.
- Checks 80+ WCAG rules automatically
- Finds violations, passes, and incomplete results
- Maps each violation to WCAG criteria

This catches the "low-hanging fruit" — issues that can be detected
programmatically (missing alt text, color contrast, ARIA errors, etc.)

API Keys Needed: NONE
"""

import json
import urllib.request
from typing import Optional
from loguru import logger
from playwright.async_api import Page
from src.models import AxeResult, AxeViolation


# axe-core CDN URL (inject into page at runtime)
AXE_CORE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.2/axe.min.js"

# Module-level cache so script is fetched only once per process
_AXE_SCRIPT_CACHE: Optional[str] = None


def _fetch_axe_script() -> Optional[str]:
    """Download axe-core source for CSP-bypass injection. Cached after first call."""
    global _AXE_SCRIPT_CACHE
    if _AXE_SCRIPT_CACHE is not None:
        return _AXE_SCRIPT_CACHE
    try:
        with urllib.request.urlopen(AXE_CORE_CDN, timeout=15) as resp:
            _AXE_SCRIPT_CACHE = resp.read().decode("utf-8")
            return _AXE_SCRIPT_CACHE
    except Exception as e:
        logger.warning(f"  Could not fetch axe-core script for CSP bypass: {e}")
        return None


class AxeCoreScanner:
    """Runs axe-core accessibility scans inside Playwright pages."""

    def __init__(self, wcag_level: str = "wcag2aa"):
        """
        Args:
            wcag_level: WCAG conformance level to check. 
                        Options: 'wcag2a', 'wcag2aa', 'wcag2aaa', 'wcag21aa', 'wcag22aa'
        """
        self.wcag_level = wcag_level
        # Tags to include in the scan based on level
        self.run_tags = self._get_tags_for_level(wcag_level)
    
    def _get_tags_for_level(self, level: str) -> list:
        """Map WCAG level to axe-core tags."""
        tag_map = {
            "wcag2a": ["wcag2a", "wcag21a", "wcag22a", "best-practice"],
            "wcag2aa": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"],
            "wcag2aaa": ["wcag2a", "wcag2aa", "wcag2aaa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"],
        }
        return tag_map.get(level, tag_map["wcag2aa"])
    
    async def scan_page(self, page: Page, url: str) -> AxeResult:
        """
        Run axe-core on a page and return structured results.
        
        Args:
            page: Playwright page (already navigated to the URL)
            url: Page URL for logging
            
        Returns:
            AxeResult with all violations and stats
        """
        try:
            logger.info(f"  🔍 Running axe-core scan: {url}")
            
            # Inject axe-core — try CDN first, fall back to evaluate() to bypass CSP
            try:
                await page.add_script_tag(url=AXE_CORE_CDN)
            except Exception:
                axe_script = _fetch_axe_script()
                if axe_script is None:
                    logger.error(f"  ❌ axe-core unavailable (CSP blocked + fetch failed): {url}")
                    return AxeResult()
                logger.info(f"  ℹ️  axe-core CSP blocked — injecting via evaluate() for: {url}")
                await page.evaluate(axe_script)
            await page.wait_for_timeout(500)  # let axe initialise
            
            # Run the scan with configured tags
            run_config = json.dumps({
                "runOnly": {
                    "type": "tag",
                    "values": self.run_tags
                },
                "resultTypes": ["violations", "passes", "incomplete", "inapplicable"]
            })
            
            axe_results_raw = await page.evaluate(f"""
                async () => {{
                    try {{
                        const results = await axe.run(document, {run_config});
                        return JSON.stringify({{
                            violations: results.violations,
                            passes: results.passes.length,
                            incomplete: results.incomplete,
                            inapplicable: results.inapplicable.length,
                        }});
                    }} catch (err) {{
                        return JSON.stringify({{ error: err.message }});
                    }}
                }}
            """)
            
            raw = json.loads(axe_results_raw)
            
            if "error" in raw:
                logger.error(f"  ❌ axe-core error: {raw['error']}")
                return AxeResult()
            
            # Parse violations into our model
            violations = []
            total_nodes = 0
            
            for v in raw.get("violations", []):
                # Extract WCAG tags
                wcag_tags = [t for t in v.get("tags", []) if t.startswith("wcag")]
                
                # Simplify nodes data
                nodes = []
                for node in v.get("nodes", []):
                    nodes.append({
                        "target": node.get("target", []),
                        "html": node.get("html", "")[:500],  # truncate long HTML
                        "failure_summary": node.get("failureSummary", ""),
                        "impact": node.get("impact", ""),
                    })
                
                total_nodes += len(nodes)
                
                violation = AxeViolation(
                    rule_id=v.get("id", "unknown"),
                    description=v.get("description", ""),
                    help_text=v.get("help", ""),
                    help_url=v.get("helpUrl", ""),
                    impact=v.get("impact", "moderate"),
                    wcag_tags=wcag_tags,
                    nodes=nodes,
                    node_count=len(nodes),
                )
                violations.append(violation)
            
            result = AxeResult(
                violations=violations,
                passes=raw.get("passes", 0),
                inapplicable=raw.get("inapplicable", 0),
                incomplete=raw.get("incomplete", [])[:10],  # limit
                total_violations=len(violations),
                total_nodes_affected=total_nodes,
            )
            
            logger.info(
                f"  ✅ axe-core: {result.total_violations} violations "
                f"({result.total_nodes_affected} nodes), "
                f"{result.passes} passes"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"  ❌ axe-core scan failed for {url}: {e}")
            return AxeResult()
