"""
WCAG Audit Agent - Core Data Models
Shared data structures used across all pipeline steps.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


# ─── Enums ───────────────────────────────────────────────

class AuditStatus(str, Enum):
    PENDING = "pending"
    CRAWLING = "crawling"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class Severity(str, Enum):
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"


class ImpactGroup(str, Enum):
    BLIND = "blind_users"
    LOW_VISION = "low_vision_users"
    DEAF = "deaf_users"
    MOTOR = "motor_impaired_users"
    COGNITIVE = "cognitive_disability_users"
    ALL = "all_users"


class WCAGLevel(str, Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"


# ─── Authentication Configuration ─────────────────────

class AuthConfig(BaseModel):
    """
    Credentials and selectors used to authenticate a browser context before any
    crawling or data–collection occurs.  The pipeline supports a *global* login
    step that is executed once and then the same context (with session cookies)
    is reused for every page visit.

    Only a simple username/password form is handled by default.  The caller may
    override the `login_url` or CSS selectors if the site uses non‑standard
    field names.
    """

    username: str
    password: str

    # Optional URL to visit for the login form.  If not provided the tool will
    # navigate to the target URL and let any redirects take it to the login page.
    login_url: Optional[str] = None

    # CSS selectors for the login form elements.  These defaults cover most
    # standard HTML patterns (input[name=...], input[type=email], etc.).
    user_selector: str = "input[name='username'], input[type='email'], input[name='email']"
    pass_selector: str = "input[name='password']"
    submit_selector: str = "button[type='submit'], input[type='submit']"

    async def perform_login(self, context, initial_url: str):
        """Open a page, navigate to the login URL and submit credentials.

        Args:
            context: Playwright BrowserContext that will be used for subsequent
                navigation.
            initial_url: the original target URL; used when ``login_url`` is
                not supplied so the page is opened and allowed to redirect.
        """
        page = await context.new_page()
        url = self.login_url or initial_url
        if url:
            await page.goto(url, wait_until="networkidle")
        await page.fill(self.user_selector, self.username)
        await page.fill(self.pass_selector, self.password)
        await page.click(self.submit_selector)
        await page.wait_for_load_state("networkidle")
        await page.close()


# ─── Step 1: Crawl Results ──────────────────────────────

class PageInfo(BaseModel):
    """Represents a discovered page on the target website."""
    url: str
    title: str = ""
    depth: int = 0
    parent_url: Optional[str] = None
    status_code: int = 200
    content_type: str = "text/html"
    discovered_at: datetime = Field(default_factory=datetime.utcnow)


class CrawlResult(BaseModel):
    """Output of Step 1: All discovered pages."""
    audit_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_url: str
    pages: List[PageInfo] = []
    total_pages_found: int = 0
    pages_crawled: int = 0
    crawl_start: datetime = Field(default_factory=datetime.utcnow)
    crawl_end: Optional[datetime] = None
    errors: List[str] = []


# ─── Step 2: Data Collection Per Page ───────────────────

class ScreenshotData(BaseModel):
    """Screenshots captured for a single page."""
    desktop: Optional[str] = None
    tablet: Optional[str] = None
    mobile: Optional[str] = None
    zoomed_200: Optional[str] = None


class AxeViolation(BaseModel):
    """Single axe-core violation."""
    rule_id: str
    description: str
    help_text: str
    help_url: str
    impact: str
    wcag_tags: List[str] = []
    nodes: List[Dict[str, Any]] = []
    node_count: int = 0


class AxeResult(BaseModel):
    """Axe-core scan results for a page."""
    violations: List[AxeViolation] = []
    passes: int = 0
    inapplicable: int = 0
    incomplete: List[Dict[str, Any]] = []
    total_violations: int = 0
    total_nodes_affected: int = 0


class KeyboardNavData(BaseModel):
    """Keyboard navigation recording for a page."""
    tab_order: List[Dict[str, Any]] = []
    total_focusable: int = 0
    focus_trap_detected: bool = False
    skip_link_present: bool = False
    focus_visible_issues: List[str] = []


class PageCollectionResult(BaseModel):
    """All collected data for a single page (Step 2 output)."""
    page: PageInfo
    dom_content: str = ""
    dom_snapshot: str = ""
    screenshots: ScreenshotData = ScreenshotData()
    axe_results: AxeResult = AxeResult()
    keyboard_nav: KeyboardNavData = KeyboardNavData()
    collection_time_seconds: float = 0.0


# ─── Step 3+4: AI Agent Findings + RAG ──────────────────

class AccessibilityIssue(BaseModel):
    """A single accessibility issue found by any agent."""
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    source: str  # "axe-core", "vision_agent", "semantic_agent", "keyboard_agent"
    page_url: str

    # WCAG mapping
    wcag_criterion: str = ""
    wcag_criterion_name: str = ""
    wcag_level: WCAGLevel = WCAGLevel.AA

    # Issue details
    title: str
    description: str
    severity: Severity = Severity.MODERATE
    impact_groups: List[ImpactGroup] = []

    # Evidence
    element_selector: str = ""
    element_html: str = ""
    screenshot_region: Optional[str] = None

    # Fix suggestion
    fix_description: str = ""
    fix_code_before: str = ""
    fix_code_after: str = ""
    wcag_technique_ref: str = ""

    # RAG enrichment (Step 4 — populated by RAGEnricher)
    rag_techniques: List[str] = []           # e.g., ["H37", "G94", "F65"]
    rag_understanding: str = ""              # Understanding text from WCAG docs
    rag_enriched: bool = False               # Whether RAG enrichment was applied

    # Metadata
    confidence: float = 0.0
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None


# ─── Step 5: Aggregated Report ──────────────────────────

class PageReport(BaseModel):
    """Aggregated findings for a single page."""
    page_url: str
    page_title: str
    issues: List[AccessibilityIssue] = []
    score: float = 0.0
    critical_count: int = 0
    serious_count: int = 0
    moderate_count: int = 0
    minor_count: int = 0


class AuditReport(BaseModel):
    """Final aggregated audit report."""
    audit_id: str
    target_url: str
    audit_date: datetime = Field(default_factory=datetime.utcnow)
    status: AuditStatus = AuditStatus.PENDING

    # Summary
    overall_score: float = 0.0
    total_issues: int = 0
    total_pages_audited: int = 0
    wcag_level_targeted: WCAGLevel = WCAGLevel.AA

    # Breakdown
    issues_by_severity: Dict[str, int] = {}
    issues_by_wcag_principle: Dict[str, int] = {}
    issues_by_impact_group: Dict[str, int] = {}

    # Per-page results
    page_reports: List[PageReport] = []

    # Top priority fixes
    priority_fixes: List[AccessibilityIssue] = []

    # RAG stats
    rag_enabled: bool = False
    rag_enriched_count: int = 0

    # Output paths
    pdf_path: Optional[str] = None
    json_path: Optional[str] = None

    # Timing
    total_duration_seconds: float = 0.0