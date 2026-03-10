"""
STEP 2d: Keyboard Navigation Recorder
=======================================
Simulates keyboard-only navigation through a page:
- Presses Tab through all focusable elements (using Playwright native keyboard)
- Records the tab order, element type, labels
- Detects focus traps (Tab cycling back to an already-seen element)
- Checks for visible focus indicators
- Checks for skip navigation links

This data feeds Agent 3 (Keyboard Agent) in Step 3.

API Keys Needed: NONE
"""

from loguru import logger
from playwright.async_api import Page
from src.models import KeyboardNavData


class KeyboardNavRecorder:
    """Records keyboard navigation behaviour on web pages."""

    def __init__(self, max_tabs: int = 100):
        """
        Args:
            max_tabs: Maximum number of Tab presses before stopping
                      (prevents infinite loops on large pages)
        """
        self.max_tabs = max_tabs

    async def record_tab_order(self, page: Page, url: str) -> KeyboardNavData:
        """
        Simulate Tab key navigation using Playwright's native keyboard API
        and record the resulting focus order.

        Using page.keyboard.press('Tab') is more accurate than calling
        el.focus() via JavaScript because:
          - It follows the browser's real tab order (respects tabindex values)
          - It triggers :focus-visible styles correctly
          - It can detect focus traps (when focus cycles back to an already-seen element)

        Args:
            page: Playwright page (already navigated)
            url: URL for logging

        Returns:
            KeyboardNavData with tab order and issue detection
        """
        try:
            logger.info(f"  [keyboard-nav] recording: {url}")

            # ── Check for a skip-navigation link ──────────────────────────
            skip_link_present: bool = await page.evaluate("""
                () => {
                    const links = document.querySelectorAll('a[href^="#"]');
                    return Array.from(links).some(l => {
                        const t = (l.textContent || '').toLowerCase();
                        return t.includes('skip') || t.includes('main content');
                    });
                }
            """)

            # ── Reset focus to the top of the page ────────────────────────
            await page.evaluate("document.body.focus()")

            tab_order = []
            focus_visible_issues = []
            seen_uids: set = set()
            focus_trap = False

            # ── Tab through the page using Playwright's real keyboard ──────
            for i in range(self.max_tabs):
                await page.keyboard.press("Tab")

                element_info = await page.evaluate("""
                    () => {
                        const el = document.activeElement;
                        if (!el || el === document.body || el === document.documentElement) {
                            return null;
                        }

                        const rect = el.getBoundingClientRect();
                        // Skip zero-size elements (hidden / off-screen)
                        if (rect.width === 0 && rect.height === 0) return null;

                        // Focus-ring detection: check computed outline and box-shadow
                        const style = window.getComputedStyle(el);
                        const outline   = style.outline   || '';
                        const boxShadow = style.boxShadow || '';
                        const hasFocusRing = (
                            (outline   && outline   !== 'none' && !outline.includes('0px')) ||
                            (boxShadow && boxShadow !== 'none')
                        );

                        // Build a unique identifier for this element
                        const uid = [
                            el.tagName,
                            el.id || '',
                            Math.round(rect.top),
                            Math.round(rect.left)
                        ].join(':');

                        // Resolve best accessible label
                        let label = '';
                        if (el.getAttribute('aria-label'))        label = el.getAttribute('aria-label');
                        else if (el.getAttribute('title'))         label = el.getAttribute('title');
                        else if (el.labels && el.labels[0])        label = el.labels[0].textContent.trim();
                        else if (el.getAttribute('placeholder'))   label = el.getAttribute('placeholder');
                        else label = (el.textContent || el.value || '').trim().substring(0, 60);

                        return {
                            tag:                 el.tagName.toLowerCase(),
                            role:                el.getAttribute('role') || '',
                            type:                el.getAttribute('type') || '',
                            id:                  el.id || '',
                            label:               label,
                            href:                el.getAttribute('href') || '',
                            tabindex:            el.getAttribute('tabindex') || '',
                            visible:             rect.width > 0 && rect.height > 0,
                            has_focus_indicator: hasFocusRing,
                            position:            { top: Math.round(rect.top), left: Math.round(rect.left) },
                            uid:                 uid
                        };
                    }
                """)

                if not element_info:
                    # Focus returned to body/html — end of focusable elements
                    break

                uid = element_info.pop("uid")

                # ── Focus trap detection ───────────────────────────────────
                if uid in seen_uids:
                    focus_trap = True
                    logger.warning(
                        f"  Focus trap detected at Tab press {i}: "
                        f"<{element_info.get('tag')}> '{element_info.get('label', '')[:40]}'"
                    )
                    break

                seen_uids.add(uid)
                element_info["index"] = i
                tab_order.append(element_info)

                # Track elements without a visible focus indicator
                if not element_info.get("has_focus_indicator"):
                    tag = element_info.get("tag", "?")
                    el_id = element_info.get("id", "")
                    label = element_info.get("label", "")[:40]
                    selector = f"#{el_id}" if el_id else tag
                    focus_visible_issues.append(f"{tag}: '{label}' ({selector})")

            result = KeyboardNavData(
                tab_order=tab_order,
                total_focusable=len(tab_order),
                focus_trap_detected=focus_trap,
                skip_link_present=skip_link_present,
                focus_visible_issues=focus_visible_issues[:20],
            )

            logger.info(
                f"  ✅ Keyboard nav: {result.total_focusable} focusable elements, "
                f"skip link: {'YES' if result.skip_link_present else 'NO'}, "
                f"focus issues: {len(result.focus_visible_issues)}"
            )
            return result

        except Exception as e:
            logger.error(f"  ❌ Keyboard recording failed for {url}: {e}")
            return KeyboardNavData()
