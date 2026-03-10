"""
STEP 2b: DOM Content Collector
===============================
Extracts and cleans the HTML DOM for semantic AI analysis:
- Full rendered HTML (post-JavaScript)
- Cleaned semantic structure (headings, landmarks, forms, links, images)
- Strips scripts, styles, and noise

The semantic snapshot is what Agent 2 analyzes in Step 3.

API Keys Needed: NONE
"""

from bs4 import BeautifulSoup, Comment
from loguru import logger
from playwright.async_api import Page


class DOMCollector:
    """Extracts and processes DOM content from rendered web pages."""
    
    # Elements to completely remove
    REMOVE_TAGS = {'script', 'style', 'noscript', 'svg', 'path', 'meta', 'link'}
    
    # Semantic elements we care about for accessibility analysis
    SEMANTIC_TAGS = {
        'header', 'nav', 'main', 'aside', 'footer', 'section', 'article',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'form', 'input', 'select', 'textarea', 'button', 'label', 'fieldset', 'legend',
        'a', 'img', 'video', 'audio', 'iframe', 'canvas',
        'table', 'th', 'td', 'caption',
        'ul', 'ol', 'li', 'dl', 'dt', 'dd',
        'figure', 'figcaption', 'dialog',
    }
    
    # ARIA attributes we want to preserve
    ARIA_ATTRS = {
        'role', 'aria-label', 'aria-labelledby', 'aria-describedby',
        'aria-hidden', 'aria-live', 'aria-expanded', 'aria-controls',
        'aria-required', 'aria-invalid', 'aria-current', 'aria-selected',
        'aria-pressed', 'aria-haspopup', 'tabindex',
    }
    
    async def extract_full_dom(self, page: Page) -> str:
        """
        Extract the full rendered HTML content from the page.
        Removes scripts and styles but keeps structure intact.
        """
        try:
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script, style, and other non-content elements
            for tag in soup.find_all(self.REMOVE_TAGS):
                tag.decompose()
            
            # Remove HTML comments
            for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
                comment.extract()
            
            # Clean up excessive whitespace
            cleaned = str(soup)
            
            # Truncate if extremely large (> 500KB)
            if len(cleaned) > 500_000:
                logger.warning(f"DOM content truncated from {len(cleaned)} to 500KB")
                cleaned = cleaned[:500_000]
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error extracting DOM: {e}")
            return ""
    
    async def extract_semantic_snapshot(self, page: Page) -> str:
        """
        Extract a simplified semantic structure of the page.
        This is an LLM-friendly representation focusing on accessibility-relevant elements.
        
        Output format:
        ```
        PAGE STRUCTURE:
        ├── <header role="banner">
        │   ├── <nav role="navigation" aria-label="Main">
        │   │   ├── <a href="/"> Home </a>
        │   │   ├── <a href="/about"> About </a>
        │   ├── <h1> Welcome to Example </h1>
        ├── <main role="main">
        │   ├── <h2> Our Services </h2>
        │   ├── <img src="..." alt="Team photo">
        │   ├── <form>
        │   │   ├── <label for="email"> Email </label>
        │   │   ├── <input type="email" id="email">
        ```
        """
        try:
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove non-content tags
            for tag in soup.find_all(self.REMOVE_TAGS):
                tag.decompose()
            
            # Build semantic tree
            body = soup.find('body')
            if not body:
                return "ERROR: No <body> element found"
            
            lines = ["PAGE SEMANTIC STRUCTURE:", ""]
            self._build_semantic_tree(body, lines, depth=0, max_depth=8)
            
            # Also extract key accessibility metadata
            lines.append("")
            lines.append("ACCESSIBILITY METADATA:")
            lines.extend(self._extract_a11y_metadata(soup))
            
            snapshot = "\n".join(lines)
            
            # Truncate if too large for LLM context
            if len(snapshot) > 100_000:
                snapshot = snapshot[:100_000] + "\n... [TRUNCATED]"
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error extracting semantic snapshot: {e}")
            return ""
    
    def _build_semantic_tree(self, element, lines: list, depth: int, max_depth: int):
        """Recursively build a semantic tree representation."""
        if depth > max_depth:
            return
        
        indent = "│   " * depth + "├── "
        
        for child in element.children:
            if child.name is None:
                # Text node
                text = child.strip()
                if text and len(text) > 2:
                    truncated = text[:100] + "..." if len(text) > 100 else text
                    lines.append(f"{indent}\"{truncated}\"")
                continue
            
            if child.name not in self.SEMANTIC_TAGS and not self._has_aria(child):
                # Skip non-semantic elements but recurse into children
                self._build_semantic_tree(child, lines, depth, max_depth)
                continue
            
            # Build tag representation with accessibility-relevant attributes
            tag_repr = self._format_tag(child)
            
            # Get direct text content
            direct_text = child.string or ""
            if direct_text:
                direct_text = direct_text.strip()[:80]
            
            if direct_text:
                lines.append(f"{indent}{tag_repr} \"{direct_text}\"")
            else:
                lines.append(f"{indent}{tag_repr}")
            
            # Recurse into children
            self._build_semantic_tree(child, lines, depth + 1, max_depth)
    
    def _format_tag(self, element) -> str:
        """Format a tag with its accessibility-relevant attributes."""
        tag = f"<{element.name}"
        
        # Add key attributes
        attrs_to_show = []
        
        # Always show these if present
        for attr in ['id', 'class', 'href', 'src', 'alt', 'type', 'name', 'for', 'action']:
            val = element.get(attr)
            if val:
                if attr == 'class':
                    val = ' '.join(val) if isinstance(val, list) else val
                    val = val[:60]  # truncate long class lists
                elif attr in ('href', 'src'):
                    val = val[:80]  # truncate long URLs
                attrs_to_show.append(f'{attr}="{val}"')
        
        # Always show ARIA attributes
        for attr in self.ARIA_ATTRS:
            val = element.get(attr)
            if val is not None:
                attrs_to_show.append(f'{attr}="{val}"')
        
        if attrs_to_show:
            tag += " " + " ".join(attrs_to_show)
        
        tag += ">"
        return tag
    
    def _has_aria(self, element) -> bool:
        """Check if element has any ARIA attributes."""
        if not element.attrs:
            return False
        return any(attr in self.ARIA_ATTRS for attr in element.attrs)
    
    def _extract_a11y_metadata(self, soup: BeautifulSoup) -> list:
        """Extract key accessibility metadata from the page."""
        meta = []
        
        # Language attribute
        html_tag = soup.find('html')
        lang = html_tag.get('lang', 'NOT SET') if html_tag else 'NOT SET'
        meta.append(f"  Language: {lang}")
        
        # Title
        title = soup.find('title')
        meta.append(f"  Title: {title.string.strip() if title and title.string else 'NOT SET'}")
        
        # Heading hierarchy
        headings = []
        for level in range(1, 7):
            tags = soup.find_all(f'h{level}')
            for h in tags:
                text = h.get_text(strip=True)[:60]
                headings.append(f"    H{level}: {text}")
        meta.append(f"  Heading count: {len(headings)}")
        meta.extend(headings[:30])  # limit output
        
        # Images without alt
        all_imgs = soup.find_all('img')
        imgs_no_alt = [img for img in all_imgs if not img.get('alt') and img.get('alt') != '']
        meta.append(f"  Images total: {len(all_imgs)}")
        meta.append(f"  Images missing alt: {len(imgs_no_alt)}")
        
        # Forms
        forms = soup.find_all('form')
        inputs_no_label = 0
        for form in forms:
            inputs = form.find_all(['input', 'select', 'textarea'])
            for inp in inputs:
                if inp.get('type') in ('hidden', 'submit', 'button'):
                    continue
                inp_id = inp.get('id', '')
                has_label = bool(soup.find('label', {'for': inp_id})) if inp_id else False
                has_aria = bool(inp.get('aria-label') or inp.get('aria-labelledby'))
                if not has_label and not has_aria:
                    inputs_no_label += 1
        meta.append(f"  Forms: {len(forms)}")
        meta.append(f"  Inputs without labels: {inputs_no_label}")
        
        # Landmarks
        landmarks = soup.find_all(attrs={'role': True})
        landmark_roles = [l.get('role') for l in landmarks]
        meta.append(f"  ARIA landmarks: {', '.join(set(landmark_roles)) or 'NONE'}")
        
        # Skip links
        skip_links = soup.find_all('a', href=lambda h: h and h.startswith('#'))
        has_skip = any('skip' in (l.get_text() or '').lower() for l in skip_links)
        meta.append(f"  Skip navigation link: {'YES' if has_skip else 'NOT FOUND'}")
        
        return meta
