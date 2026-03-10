"""
STEP 4: WCAG 2.2 Data Loader — COMPREHENSIVE
===============================================
All 86 WCAG 2.2 Success Criteria with:
  - Criterion definition
  - Understanding (why it matters)
  - Key techniques (how to fix)
  - Common failures

Organized by Principle → Guideline → Success Criterion.
"""

import json
import os
import hashlib
from typing import List
from dataclasses import dataclass, field, asdict
from loguru import logger


@dataclass
class WCAGChunk:
    """A single chunk of WCAG knowledge ready for embedding."""
    chunk_id: str
    text: str
    criterion_id: str = ""
    criterion_name: str = ""
    wcag_level: str = ""
    principle: str = ""
    chunk_type: str = ""
    technique_id: str = ""
    source_url: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ════════════════════════════════════════════════════════════
# COMPLETE WCAG 2.2 KNOWLEDGE BASE — ALL 86 SUCCESS CRITERIA
# ════════════════════════════════════════════════════════════

WCAG_KNOWLEDGE = [

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PRINCIPLE 1: PERCEIVABLE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── 1.1 Text Alternatives ─────────────────────────────

    {
        "criterion_id": "1.1.1",
        "criterion_name": "Non-text Content",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.1.1 Non-text Content (Level A): All non-text content presented to the user has a text alternative that serves the equivalent purpose. Exceptions: controls/input (name describes purpose), time-based media (descriptive label), tests, sensory, CAPTCHA (alternatives provided), decoration (implemented so AT ignores it)."},
            {"type": "understanding", "text": "Understanding 1.1.1: Text alternatives make non-text content accessible through any modality — visual, auditory, tactile. Screen readers rely on alt text for images. Without it, they announce file names or nothing. Alt text should convey the SAME information as the image. Decorative images get alt=''. Complex images need long descriptions."},
            {"type": "technique", "technique_id": "H37", "text": "Technique H37: Using alt attributes on img elements. Every img must have alt. Informative images: describe the information conveyed. Functional images (links/buttons): describe the function. Decorative: alt=''. Complex (charts/diagrams): brief alt + longer nearby description. Example: <img src='chart.png' alt='Sales grew 25% in Q3 vs Q2'>. Bad: alt='image', alt='photo.jpg', alt='banner'."},
            {"type": "technique", "technique_id": "G94", "text": "Technique G94: Short text alternative for non-text content serving the same purpose. Keep under 150 chars. For informative images describe what info the image conveys. For functional images describe the action. For images of text include the same text."},
            {"type": "technique", "technique_id": "G95", "text": "Technique G95: Short text alternatives providing brief description of complex content. When content is too complex for short alt, provide both short alt identifying the content and a long description with full information via aria-describedby or adjacent text."},
            {"type": "failure", "technique_id": "F65", "text": "Failure F65: Omitting alt attribute on img, area, and input type=image. Missing alt means screen readers announce filename/URL. Fix: add alt='descriptive text' for informative, alt='' for decorative, or role='presentation'."},
            {"type": "failure", "technique_id": "F30", "text": "Failure F30: Using text alternatives that are not alternatives. Alt text like 'image1.jpg', 'photo', 'untitled', 'spacer', 'banner' don't serve the image's purpose. Alt text must describe what the image conveys to users who cannot see it."},
        ]
    },

    # ── 1.2 Time-based Media ──────────────────────────────

    {
        "criterion_id": "1.2.1",
        "criterion_name": "Audio-only and Video-only (Prerecorded)",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.1 Audio-only and Video-only Prerecorded (Level A): For prerecorded audio-only, provide a text transcript. For prerecorded video-only (no audio), provide either a text description or an audio track describing the visual content."},
            {"type": "understanding", "text": "Understanding 1.2.1: Deaf users need transcripts for audio. Blind users need descriptions for silent video. Podcasts need transcripts. Silent animations/demos need text or audio descriptions of what's shown. Transcripts should include all spoken content, speaker identification, and relevant sounds."},
            {"type": "technique", "technique_id": "G158", "text": "Technique G158: Providing an alternative for time-based media for audio-only content. Create a text transcript that includes all dialogue, identifies speakers, and describes relevant non-speech audio (applause, music, sound effects). Link the transcript near the audio player."},
        ]
    },
    {
        "criterion_id": "1.2.2",
        "criterion_name": "Captions (Prerecorded)",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.2 Captions Prerecorded (Level A): Captions are provided for all prerecorded audio content in synchronized media, except when the media is a media alternative for text and clearly labeled as such."},
            {"type": "understanding", "text": "Understanding 1.2.2: Captions enable deaf and hard-of-hearing users to access video content. Captions must be synchronized with audio, include dialogue, identify speakers, and describe meaningful sounds (doorbell, laughter, music). Auto-generated captions often have errors and should be reviewed/corrected."},
            {"type": "technique", "technique_id": "G87", "text": "Technique G87: Providing closed captions. Use WebVTT or SRT format. Include: all dialogue verbatim, speaker identification when not obvious, sound effects in brackets [door slams], music descriptions [upbeat jazz]. Sync within 100ms of audio. Test with sound off."},
        ]
    },
    {
        "criterion_id": "1.2.3",
        "criterion_name": "Audio Description or Media Alternative (Prerecorded)",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.3 Audio Description or Media Alternative Prerecorded (Level A): An alternative for time-based media or audio description of the prerecorded video content is provided for synchronized media, except when the media is clearly labeled as a text alternative."},
            {"type": "understanding", "text": "Understanding 1.2.3: Blind users need audio descriptions of important visual content in videos — actions, scene changes, on-screen text, facial expressions that convey meaning. Audio descriptions are narrated during natural pauses in dialogue. Alternatively, a full text transcript can serve as the media alternative."},
        ]
    },
    {
        "criterion_id": "1.2.4",
        "criterion_name": "Captions (Live)",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.4 Captions Live (Level AA): Captions are provided for all live audio content in synchronized media. This applies to live broadcasts, webinars, live streams, and real-time events."},
            {"type": "understanding", "text": "Understanding 1.2.4: Live captions give deaf users real-time access to live events. Options include CART (Communication Access Realtime Translation), AI-powered live captioning services, or trained captioners. Some delay is acceptable. Quality should be monitored."},
        ]
    },
    {
        "criterion_id": "1.2.5",
        "criterion_name": "Audio Description (Prerecorded)",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.5 Audio Description Prerecorded (Level AA): Audio description is provided for all prerecorded video content in synchronized media. Unlike 1.2.3, a text alternative is not sufficient at this level."},
            {"type": "understanding", "text": "Understanding 1.2.5: Audio descriptions narrate visual information during pauses in dialogue. Describes actions, settings, facial expressions, scene changes, and on-screen text. The description track is mixed with the original audio. Should be professional and concise."},
        ]
    },
    {
        "criterion_id": "1.2.6",
        "criterion_name": "Sign Language (Prerecorded)",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.6 Sign Language Prerecorded (Level AAA): Sign language interpretation is provided for all prerecorded audio content in synchronized media."},
            {"type": "understanding", "text": "Understanding 1.2.6: Some deaf individuals are more fluent in sign language than written language. Sign language provides access through their primary language. The interpreter should be clearly visible and properly lit."},
        ]
    },
    {
        "criterion_id": "1.2.7",
        "criterion_name": "Extended Audio Description (Prerecorded)",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.7 Extended Audio Description Prerecorded (Level AAA): Where pauses in foreground audio are insufficient for audio descriptions, extended audio description is provided by pausing the video."},
        ]
    },
    {
        "criterion_id": "1.2.8",
        "criterion_name": "Media Alternative (Prerecorded)",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.8 Media Alternative Prerecorded (Level AAA): An alternative for time-based media is provided for all prerecorded synchronized media and all prerecorded video-only media. A full text transcript including visual descriptions."},
        ]
    },
    {
        "criterion_id": "1.2.9",
        "criterion_name": "Audio-only (Live)",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.2.9 Audio-only Live (Level AAA): An alternative for time-based media that presents equivalent information for live audio-only content is provided. A text-based real-time alternative like CART."},
        ]
    },

    # ── 1.3 Adaptable ────────────────────────────────────

    {
        "criterion_id": "1.3.1",
        "criterion_name": "Info and Relationships",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.3.1 Info and Relationships (Level A): Information, structure, and relationships conveyed through presentation can be programmatically determined or are available in text. Visual formatting that conveys meaning must be in HTML/ARIA markup."},
            {"type": "understanding", "text": "Understanding 1.3.1: Screen readers rely on semantic HTML to convey structure. If headings are just large bold text without h1-h6 tags, screen readers can't navigate by headings. Lists need ul/ol/li, not line breaks. Forms need label elements. Tables need proper th/td/caption. Data relationships must be in markup, not just visual."},
            {"type": "technique", "technique_id": "H42", "text": "Technique H42: Using h1-h6 to identify headings. Nest logically: h1 for main topic, h2 for sections, h3 for subsections. Don't skip levels. Don't use headings for styling. Every page needs at least one h1."},
            {"type": "technique", "technique_id": "H44", "text": "Technique H44: Using label elements to associate text labels with form controls. Every input needs <label for='id'>. Example: <label for='email'>Email:</label> <input type='email' id='email'>. Use aria-label when visible labels aren't possible."},
            {"type": "technique", "technique_id": "ARIA11", "text": "Technique ARIA11: Using ARIA landmarks to identify page regions. Use <header>, <nav>, <main>, <footer>, <aside>. Or role='banner', 'navigation', 'main', 'contentinfo', 'complementary', 'search'. Helps screen reader users jump between sections."},
            {"type": "technique", "technique_id": "H51", "text": "Technique H51: Using table markup for tabular data. Use <table>, <tr>, <th>, <td>, <caption>, <thead>, <tbody>. th elements identify headers. Use scope='col' or scope='row'. Never use tables for layout."},
        ]
    },
    {
        "criterion_id": "1.3.2",
        "criterion_name": "Meaningful Sequence",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.3.2 Meaningful Sequence (Level A): When the sequence in which content is presented affects its meaning, a correct reading sequence can be programmatically determined."},
            {"type": "understanding", "text": "Understanding 1.3.2: DOM order must match visual order. CSS flexbox order, float, absolute positioning can create visual layouts where reading order differs from code order. Screen readers follow DOM order. Test by linearizing content (disable CSS) and verifying it still makes sense. Multi-column layouts should have proper DOM order."},
            {"type": "technique", "technique_id": "G57", "text": "Technique G57: Ordering the content in a meaningful sequence. Ensure DOM order matches the intended reading order. Avoid CSS that reorders content visually (flex order, grid placement) unless DOM order is also correct. Use CSS to control visual presentation, not document order."},
        ]
    },
    {
        "criterion_id": "1.3.3",
        "criterion_name": "Sensory Characteristics",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.3.3 Sensory Characteristics (Level A): Instructions for understanding and operating content do not rely solely on sensory characteristics of components such as shape, color, size, visual location, orientation, or sound."},
            {"type": "understanding", "text": "Understanding 1.3.3: Don't say 'click the round button' (shape), 'press the button on the right' (location), 'red items are errors' (color only). Instead use text labels: 'click the Submit button', 'errors are marked with an X icon and red text'. Provide redundant cues — color plus text, position plus label."},
        ]
    },
    {
        "criterion_id": "1.3.4",
        "criterion_name": "Orientation",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.3.4 Orientation (Level AA): Content does not restrict its view and operation to a single display orientation, such as portrait or landscape, unless a specific orientation is essential."},
            {"type": "understanding", "text": "Understanding 1.3.4: Users with mounted devices or wheelchair trays may only use one orientation. Don't lock to portrait or landscape via CSS or meta viewport. Essential exceptions: piano app, bank check scan. Test by rotating device and verifying all content and functionality remain available."},
        ]
    },
    {
        "criterion_id": "1.3.5",
        "criterion_name": "Identify Input Purpose",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.3.5 Identify Input Purpose (Level AA): The purpose of each input field collecting information about the user can be programmatically determined when the input field serves a purpose identified in the Input Purposes for User Interface Components section."},
            {"type": "understanding", "text": "Understanding 1.3.5: Use HTML autocomplete attributes to identify field purposes. This allows browsers to autofill and assistive tech to provide icons/labels. Example: autocomplete='given-name', 'family-name', 'email', 'tel', 'street-address', 'postal-code', 'cc-number'. Helps users with cognitive disabilities and motor impairments who struggle with typing."},
            {"type": "technique", "technique_id": "H98", "text": "Technique H98: Using HTML autocomplete attributes. Add autocomplete to all personal data inputs: <input type='text' autocomplete='given-name'>, <input type='email' autocomplete='email'>, <input type='tel' autocomplete='tel'>, <input type='text' autocomplete='street-address'>. Full list in HTML spec section 4.10.18.7.1."},
        ]
    },
    {
        "criterion_id": "1.3.6",
        "criterion_name": "Identify Purpose",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.3.6 Identify Purpose (Level AAA): In content implemented using markup languages, the purpose of UI components, icons, and regions can be programmatically determined. Uses ARIA landmarks, roles, and microdata to enable AT personalization."},
        ]
    },

    # ── 1.4 Distinguishable ──────────────────────────────

    {
        "criterion_id": "1.4.1",
        "criterion_name": "Use of Color",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.1 Use of Color (Level A): Color is not used as the only visual means of conveying information, indicating an action, prompting a response, or distinguishing a visual element."},
            {"type": "understanding", "text": "Understanding 1.4.1: Color blind users (8% of men, 0.5% of women) cannot distinguish some colors. Required fields marked only in red, links distinguished only by color, chart data using only colors — all fail. Add redundant cues: underlines for links, icons for status, patterns in charts, text labels for errors. Color can supplement but not be the sole indicator."},
            {"type": "technique", "technique_id": "G14", "text": "Technique G14: Ensuring information conveyed by color differences is also available in text. Add text labels alongside color coding. Error fields: red border PLUS error icon and text message. Required fields: red label PLUS asterisk. Status: green/red PLUS 'Active'/'Inactive' text."},
        ]
    },
    {
        "criterion_id": "1.4.2",
        "criterion_name": "Audio Control",
        "wcag_level": "A",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.2 Audio Control (Level A): If any audio on a Web page plays automatically for more than 3 seconds, either a mechanism is available to pause or stop the audio, or a mechanism is available to control audio volume independently from the overall system volume."},
            {"type": "understanding", "text": "Understanding 1.4.2: Auto-playing audio interferes with screen readers which use audio output. Users need to be able to stop, pause, or control the volume. Best practice: never autoplay audio. If you must, provide prominent controls at the top of the page. The control must be keyboard accessible."},
        ]
    },
    {
        "criterion_id": "1.4.3",
        "criterion_name": "Contrast (Minimum)",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.3 Contrast Minimum (Level AA): Text and images of text have a contrast ratio of at least 4.5:1. Large text (18pt/24px regular or 14pt/18.67px bold) needs at least 3:1. Exceptions: incidental, logotypes, decoration."},
            {"type": "understanding", "text": "Understanding 1.4.3: Low vision users need sufficient contrast. 4.5:1 compensates for vision loss of ~20/40. Check all text against its background. For text on images/gradients check worst-case. Placeholder text, disabled text, and text on hover states all need checking. Tools: WebAIM Contrast Checker, Chrome DevTools."},
            {"type": "technique", "technique_id": "G18", "text": "Technique G18: Ensuring 4.5:1 contrast ratio between text and background. Fix: darken text, lighten background, increase font size for 'large text' threshold, add semi-opaque background behind text on images. Common failures: #999 on #fff (2.85:1), #767676 on #fff (4.54:1 — barely passes). Safe choices: #595959 on #fff (7:1)."},
            {"type": "technique", "technique_id": "G145", "text": "Technique G145: Ensuring 3:1 contrast for large text. Large = 18pt/24px regular or 14pt/18.67px bold. Applies to headings and hero text. Aim for 4.5:1 even for large text."},
        ]
    },
    {
        "criterion_id": "1.4.4",
        "criterion_name": "Resize Text",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.4 Resize Text (Level AA): Text can be resized without assistive technology up to 200 percent without loss of content or functionality. Except for captions and images of text."},
            {"type": "understanding", "text": "Understanding 1.4.4: Low vision users zoom text to 200%. Content must not be clipped, overlapped, or require horizontal scrolling. Use relative units (em, rem, %) not fixed px for font sizes and container heights. Test with browser zoom at 200%. Avoid overflow:hidden on text containers."},
            {"type": "technique", "technique_id": "G179", "text": "Technique G179: Ensuring no loss of content or functionality when text resizes to 200%. Use relative font sizes (em, rem). Avoid fixed-height containers for text. Let containers grow. Use min-height not height. Test at 200% zoom in multiple browsers."},
        ]
    },
    {
        "criterion_id": "1.4.5",
        "criterion_name": "Images of Text",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.5 Images of Text (Level AA): If the technologies being used can achieve the visual presentation, text is used to convey information rather than images of text. Exceptions: essential (logos) and customizable images of text."},
            {"type": "understanding", "text": "Understanding 1.4.5: Images of text cannot be resized, searched, selected, or adjusted by users. Screen readers may not read them accurately. Use actual HTML text with CSS styling instead. Logos are exempt. If images of text are needed, provide the same text as alt text."},
        ]
    },
    {
        "criterion_id": "1.4.6",
        "criterion_name": "Contrast (Enhanced)",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.6 Contrast Enhanced (Level AAA): Text and images of text have a contrast ratio of at least 7:1. Large text at least 4.5:1. Exceptions: incidental, logotypes."},
            {"type": "understanding", "text": "Understanding 1.4.6: Enhanced contrast (7:1) provides better readability for users with more severe vision loss (~20/80). Achievable with dark text on white: #333 on #fff = 12.63:1."},
        ]
    },
    {
        "criterion_id": "1.4.7",
        "criterion_name": "Low or No Background Audio",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.7 Low or No Background Audio (Level AAA): For prerecorded audio-only content with primarily speech: no background sounds, or background at least 20 dB lower than speech, or a mechanism to turn off background."},
        ]
    },
    {
        "criterion_id": "1.4.8",
        "criterion_name": "Visual Presentation",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.8 Visual Presentation (Level AAA): For blocks of text: user can select foreground/background colors, width is no more than 80 characters, text is not justified, line spacing at least 1.5, paragraph spacing at least 1.5x line spacing, text can be resized to 200% without requiring horizontal scroll."},
        ]
    },
    {
        "criterion_id": "1.4.9",
        "criterion_name": "Images of Text (No Exception)",
        "wcag_level": "AAA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.9 Images of Text No Exception (Level AAA): Images of text are only used for pure decoration or where a particular presentation is essential."},
        ]
    },
    {
        "criterion_id": "1.4.10",
        "criterion_name": "Reflow",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.10 Reflow (Level AA): Content can be presented without loss of information or functionality and without scrolling in two dimensions at 320px width (vertical scrolling content) or 256px height (horizontal scrolling content). Exceptions: images, maps, diagrams, video, games, data tables, toolbars."},
            {"type": "understanding", "text": "Understanding 1.4.10: 400% zoom on 1280px = 320px effective viewport. Content must reflow without horizontal scrolling. Use responsive design, relative units, CSS flexbox/grid, avoid fixed widths. Test at 400% zoom on 1280px window."},
            {"type": "technique", "technique_id": "C31", "text": "Technique C31: Using CSS Flexbox to reflow content. Use display:flex with flex-wrap:wrap. Set flex items with flex-basis in relative units. Media queries for layout changes. Avoid min-width in px on containers."},
        ]
    },
    {
        "criterion_id": "1.4.11",
        "criterion_name": "Non-text Contrast",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.11 Non-text Contrast (Level AA): UI components and graphical objects have a contrast ratio of at least 3:1 against adjacent colors. Applies to form field borders, buttons, icons, chart data, focus indicators, custom controls."},
            {"type": "understanding", "text": "Understanding 1.4.11: Low vision users need to see UI component boundaries and graphical information. Common failures: light gray borders (#ccc on #fff = 1.6:1), icon-only buttons with poor contrast, custom checkboxes blending with background. Focus indicators also need 3:1."},
            {"type": "technique", "technique_id": "G195", "text": "Technique G195: Author-supplied visible focus indicator with 3:1 contrast. CSS: button:focus-visible { outline: 2px solid #005fcc; outline-offset: 2px; }. Never outline:none without replacement. Focus must be visible on both light and dark backgrounds."},
        ]
    },
    {
        "criterion_id": "1.4.12",
        "criterion_name": "Text Spacing",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.12 Text Spacing (Level AA): No loss of content or functionality when overriding: line-height to 1.5x font size, paragraph spacing to 2x font size, letter-spacing to 0.12x font size, word-spacing to 0.16x font size."},
            {"type": "understanding", "text": "Understanding 1.4.12: Dyslexic and low vision users adjust text spacing for readability. Content must not break. Common failures: overflow:hidden clipping text, fixed-height containers, overlapping text. Fix: use flexible containers, min-height not height, test with text spacing bookmarklet."},
        ]
    },
    {
        "criterion_id": "1.4.13",
        "criterion_name": "Content on Hover or Focus",
        "wcag_level": "AA",
        "principle": "Perceivable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 1.4.13 Content on Hover or Focus (Level AA): Where hover or focus triggers additional content to become visible and then hidden, the following are true: Dismissible (can be dismissed without moving hover/focus, e.g., Escape), Hoverable (pointer can move over additional content without it disappearing), Persistent (content remains until hover/focus trigger is removed, user dismisses it, or info is no longer valid)."},
            {"type": "understanding", "text": "Understanding 1.4.13: Tooltips, custom popups, and dropdown menus triggered by hover/focus must be dismissible (Escape key), hoverable (user can mouse into the popup), and persistent (don't disappear on their own). Low vision users with magnification may need to scroll to read tooltips. Keyboard users need focus to trigger the same content."},
            {"type": "technique", "technique_id": "SCR39", "text": "Technique SCR39: Making content on hover/focus dismissible, hoverable, persistent. Add Escape handler to dismiss. Keep content visible while pointer is within trigger or content area. Don't use setTimeout to hide. Use mouseenter/mouseleave not mouseover/mouseout."},
        ]
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PRINCIPLE 2: OPERABLE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── 2.1 Keyboard Accessible ──────────────────────────

    {
        "criterion_id": "2.1.1",
        "criterion_name": "Keyboard",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.1.1 Keyboard (Level A): All functionality is operable through keyboard without requiring specific timings, except where the underlying function requires path-dependent input (like freehand drawing)."},
            {"type": "understanding", "text": "Understanding 2.1.1: Essential for blind users (can't use mouse), motor-impaired users (may use keyboard alternatives), and power users. Common failures: onclick on div/span without keyboard, custom widgets without keyboard support, drag-and-drop without keyboard alternative."},
            {"type": "technique", "technique_id": "G202", "text": "Technique G202: Ensuring keyboard control for all functionality. Use native HTML elements (button, a, input, select) with built-in keyboard support. For custom widgets: tabindex='0' for focus, handle Enter/Space for activation, arrow keys for widget navigation, Escape for close. Follow ARIA Authoring Practices."},
            {"type": "failure", "technique_id": "F54", "text": "Failure F54: Using only pointing-device-specific event handlers (onclick on non-interactive element without keyboard handlers). Fix: use <button> instead of <div onclick>, or add role='button', tabindex='0', and keydown handler for Enter/Space."},
        ]
    },
    {
        "criterion_id": "2.1.2",
        "criterion_name": "No Keyboard Trap",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.1.2 No Keyboard Trap (Level A): If keyboard focus can be moved to a component, focus can be moved away using keyboard. If non-standard keys are needed, the user is advised."},
            {"type": "understanding", "text": "Understanding 2.1.2: Keyboard traps prevent users from navigating away. Causes: modals without proper focus management, embedded iframes/plugins, custom widgets capturing all keystrokes. Fix: Tab should cycle predictably, Escape should close modals and return focus, focus should only be trapped intentionally in modals (with visible close)."},
            {"type": "technique", "technique_id": "G21", "text": "Technique G21: Ensuring users are not trapped in content. Test by tabbing through entire page. For modals: trap focus within modal while open, close on Escape, return focus to trigger element. Never prevent Tab from moving focus. For plugins: ensure Tab exits the plugin."},
        ]
    },
    {
        "criterion_id": "2.1.3",
        "criterion_name": "Keyboard (No Exception)",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.1.3 Keyboard No Exception (Level AAA): All functionality is operable through keyboard without exception (removes the path-dependent input exception from 2.1.1)."},
        ]
    },
    {
        "criterion_id": "2.1.4",
        "criterion_name": "Character Key Shortcuts",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.1.4 Character Key Shortcuts (Level A): If a keyboard shortcut using only letter, punctuation, number, or symbol characters is implemented, at least one of: turn off mechanism, remap mechanism, or shortcut is only active when the component has focus."},
            {"type": "understanding", "text": "Understanding 2.1.4: Single-character shortcuts can be accidentally triggered by speech input users or users with motor impairments. Gmail's 'j/k' for navigation can conflict with speech input. Fix: require modifier key (Ctrl+K), provide remap option, or only activate when component has focus."},
        ]
    },

    # ── 2.2 Enough Time ──────────────────────────────────

    {
        "criterion_id": "2.2.1",
        "criterion_name": "Timing Adjustable",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.2.1 Timing Adjustable (Level A): For time limits set by content, user can: turn off, adjust (at least 10x default), or extend (warned 20+ seconds before, can extend with simple action, allowed to extend at least 10 times). Exceptions: real-time events, essential timing, 20+ hour limit."},
            {"type": "understanding", "text": "Understanding 2.2.1: Users with disabilities often need more time to read, type, or complete tasks. Session timeouts, auto-advancing carousels, and timed forms can exclude them. Best: remove time limits. Next best: warn before timeout and allow extension. Auto-rotating carousels must have pause/stop controls."},
            {"type": "technique", "technique_id": "G198", "text": "Technique G198: Providing a way for users to turn off time limits. Add a setting or checkbox to disable timeouts. For session timeouts: warn 2 minutes before, allow extension. For carousels: provide play/pause controls. For forms: save progress and allow return."},
        ]
    },
    {
        "criterion_id": "2.2.2",
        "criterion_name": "Pause, Stop, Hide",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.2.2 Pause, Stop, Hide (Level A): For moving, blinking, scrolling content that starts automatically and lasts 5+ seconds: a mechanism to pause, stop, or hide. For auto-updating content: a mechanism to pause, stop, hide, or control frequency."},
            {"type": "understanding", "text": "Understanding 2.2.2: Animated content distracts users with cognitive disabilities and attention disorders. Auto-playing carousels, animated banners, scrolling tickers, and live feeds need controls. Animations that last less than 5 seconds are exempt. prefers-reduced-motion CSS media query can help."},
            {"type": "technique", "technique_id": "G4", "text": "Technique G4: Allowing content to be paused and resumed. Add visible pause/play button for carousels, animations, auto-scrolling content. Respect prefers-reduced-motion: @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }"},
        ]
    },
    {
        "criterion_id": "2.2.3",
        "criterion_name": "No Timing",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.2.3 No Timing (Level AAA): Timing is not an essential part of the event or activity, except for real-time events and non-interactive synchronized media."},
        ]
    },
    {
        "criterion_id": "2.2.4",
        "criterion_name": "Interruptions",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.2.4 Interruptions (Level AAA): Interruptions can be postponed or suppressed by the user, except emergencies involving health, property, or safety."},
        ]
    },
    {
        "criterion_id": "2.2.5",
        "criterion_name": "Re-authenticating",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.2.5 Re-authenticating (Level AAA): When an authenticated session expires, the user can continue the activity without loss of data after re-authenticating."},
        ]
    },
    {
        "criterion_id": "2.2.6",
        "criterion_name": "Timeouts",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.2.6 Timeouts (Level AAA): Users are warned of any timeout that could cause data loss, unless data is preserved for more than 20 hours of user inactivity."},
        ]
    },

    # ── 2.3 Seizures and Physical Reactions ──────────────

    {
        "criterion_id": "2.3.1",
        "criterion_name": "Three Flashes or Below Threshold",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.3.1 Three Flashes or Below Threshold (Level A): Web pages do not contain anything that flashes more than three times in any one second period, or the flash is below the general flash and red flash thresholds."},
            {"type": "understanding", "text": "Understanding 2.3.1: Flashing content can cause seizures in people with photosensitive epilepsy. Affects ~1 in 4000 people. Avoid content that flashes more than 3 times per second. If flashing is necessary, ensure the flashing area is small (less than 25% of 10 degrees of visual field) or below the thresholds. This includes videos, animations, GIFs, and CSS animations."},
        ]
    },
    {
        "criterion_id": "2.3.2",
        "criterion_name": "Three Flashes",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.3.2 Three Flashes (Level AAA): Web pages do not contain anything that flashes more than three times in any one second period (no threshold exception)."},
        ]
    },
    {
        "criterion_id": "2.3.3",
        "criterion_name": "Animation from Interactions",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.3.3 Animation from Interactions (Level AAA): Motion animation triggered by interaction can be disabled, unless the animation is essential. Parallax scrolling, zoom animations, and motion transitions should respect prefers-reduced-motion."},
        ]
    },

    # ── 2.4 Navigable ────────────────────────────────────

    {
        "criterion_id": "2.4.1",
        "criterion_name": "Bypass Blocks",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.1 Bypass Blocks (Level A): A mechanism is available to bypass blocks of content repeated on multiple pages."},
            {"type": "understanding", "text": "Understanding 2.4.1: Screen reader and keyboard users must tab through every nav link to reach content. Skip links let them bypass this. ARIA landmarks also help. Without skip links, users may need 20-50+ tab presses."},
            {"type": "technique", "technique_id": "G1", "text": "Technique G1: Adding skip link at top of page to main content. Example: <a href='#main-content' class='skip-link'>Skip to main content</a> ... <main id='main-content'>. CSS: .skip-link { position: absolute; left: -9999px; } .skip-link:focus { position: fixed; top: 0; left: 0; z-index: 9999; padding: 8px 16px; background: #000; color: #fff; }"},
        ]
    },
    {
        "criterion_id": "2.4.2",
        "criterion_name": "Page Titled",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.2 Page Titled (Level A): Web pages have titles that describe topic or purpose."},
            {"type": "technique", "technique_id": "G88", "text": "Technique G88: Providing descriptive page titles. Format: 'Page Name - Site Name' or 'Page Name | Section | Site Name'. Bad: 'Untitled', 'Home', same title on every page. Screen readers announce title first on page load."},
        ]
    },
    {
        "criterion_id": "2.4.3",
        "criterion_name": "Focus Order",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.3 Focus Order (Level A): If a page can be navigated sequentially and the navigation sequences affect meaning or operation, focusable components receive focus in an order that preserves meaning and operability."},
            {"type": "understanding", "text": "Understanding 2.4.3: Tab order should follow visual/logical reading order. Avoid positive tabindex values (tabindex='1','2'). Ensure dynamically inserted content (modals, dropdowns) receives focus correctly. CSS flex order and position:absolute can cause visual/DOM order mismatch."},
            {"type": "technique", "technique_id": "H4", "text": "Technique H4: Creating a logical tab order through links, form controls, and objects. Follow DOM order for tab sequence. Avoid tabindex > 0. For modals: move focus to modal on open, trap focus inside, return focus on close. Test by tabbing through the entire page."},
        ]
    },
    {
        "criterion_id": "2.4.4",
        "criterion_name": "Link Purpose (In Context)",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.4 Link Purpose In Context (Level A): The purpose of each link can be determined from the link text alone or from link text together with programmatically determined context."},
            {"type": "understanding", "text": "Understanding 2.4.4: Screen readers list all links. 'Click here', 'read more', 'learn more' are meaningless out of context. Each link should describe its destination. Use aria-label for repeated patterns."},
            {"type": "technique", "technique_id": "H30", "text": "Technique H30: Providing descriptive link text. Instead of 'Click here to view pricing', use 'View our pricing plans'. For image links, alt text is the link text. For cards: <a href='/article-1' aria-label='Read full article: AI Trends'>Read more</a>."},
        ]
    },
    {
        "criterion_id": "2.4.5",
        "criterion_name": "Multiple Ways",
        "wcag_level": "AA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.5 Multiple Ways (Level AA): More than one way is available to locate a Web page within a set of pages, except where the page is a result of or step in a process."},
            {"type": "understanding", "text": "Understanding 2.4.5: Different users navigate differently. Provide at least two of: navigation menu, site map, search, table of contents, A-Z index, link from every page to all other pages. Helps users with cognitive disabilities who may find one method easier than another."},
        ]
    },
    {
        "criterion_id": "2.4.6",
        "criterion_name": "Headings and Labels",
        "wcag_level": "AA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.6 Headings and Labels (Level AA): Headings and labels describe topic or purpose. This doesn't require headings or labels, but when they are provided they must be descriptive."},
            {"type": "understanding", "text": "Understanding 2.4.6: Generic headings like 'Introduction' or 'More' don't help users understand content structure. Labels like 'Field 1' don't describe input purpose. Write headings that summarize the section content. Labels should clearly indicate what input is expected."},
        ]
    },
    {
        "criterion_id": "2.4.7",
        "criterion_name": "Focus Visible",
        "wcag_level": "AA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.7 Focus Visible (Level AA): Any keyboard operable user interface has a mode of operation where the keyboard focus indicator is visible."},
            {"type": "understanding", "text": "Understanding 2.4.7: Sighted keyboard users MUST see which element has focus. Without visible focus, keyboard navigation is impossible. Common failure: CSS outline:none without replacement. Use :focus-visible for keyboard-only focus rings."},
            {"type": "technique", "technique_id": "C15", "text": "Technique C15: Using CSS to change presentation on focus. CSS: *:focus-visible { outline: 2px solid #005fcc; outline-offset: 2px; } For custom: button:focus-visible { box-shadow: 0 0 0 3px rgba(0,95,204,0.5); } Ensure 3:1 contrast for focus indicator (2.4.11)."},
        ]
    },
    {
        "criterion_id": "2.4.8",
        "criterion_name": "Location",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.8 Location (Level AAA): Information about the user's location within a set of Web pages is available. Breadcrumbs, highlighted current page in navigation, step indicators in processes."},
        ]
    },
    {
        "criterion_id": "2.4.9",
        "criterion_name": "Link Purpose (Link Only)",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.9 Link Purpose Link Only (Level AAA): The purpose of each link can be identified from the link text alone (no surrounding context needed)."},
        ]
    },
    {
        "criterion_id": "2.4.10",
        "criterion_name": "Section Headings",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.10 Section Headings (Level AAA): Section headings are used to organize the content. Headings should be used wherever content can logically be divided into sections."},
        ]
    },
    {
        "criterion_id": "2.4.11",
        "criterion_name": "Focus Not Obscured (Minimum)",
        "wcag_level": "AA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.11 Focus Not Obscured Minimum (Level AA): When a UI component receives keyboard focus, the component is not entirely hidden by author-created content. New in WCAG 2.2. Culprits: sticky headers/footers, cookie banners, chat widgets."},
            {"type": "technique", "technique_id": "C43", "text": "Technique C43: Ensuring focused elements aren't obscured by sticky content. Use scroll-padding-top/bottom for fixed headers/footers. Ensure z-index keeps focused content visible. Test by tabbing through with sticky elements present. CSS: html { scroll-padding-top: 80px; }"},
        ]
    },
    {
        "criterion_id": "2.4.12",
        "criterion_name": "Focus Not Obscured (Enhanced)",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.12 Focus Not Obscured Enhanced (Level AAA): When a UI component receives keyboard focus, no part of the component is hidden by author-created content (stricter than 2.4.11 which only requires 'not entirely hidden')."},
        ]
    },
    {
        "criterion_id": "2.4.13",
        "criterion_name": "Focus Appearance",
        "wcag_level": "AA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.4.13 Focus Appearance (Level AA): When the keyboard focus indicator is visible, the focus indicator area is at least as large as the area of a 2 CSS pixel thick perimeter of the unfocused component, and has a contrast ratio of at least 3:1 between focused and unfocused states. New in WCAG 2.2."},
            {"type": "understanding", "text": "Understanding 2.4.13: Focus indicators must be large enough and high enough contrast to be visible. A 2px outline around the component meets the area requirement. The indicator must have 3:1 contrast against unfocused state. Thin 1px dotted outlines typically fail. Recommended: 2px+ solid outline with good contrast."},
        ]
    },

    # ── 2.5 Input Modalities ─────────────────────────────

    {
        "criterion_id": "2.5.1",
        "criterion_name": "Pointer Gestures",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.1 Pointer Gestures (Level A): All functionality using multipoint or path-based gestures can be operated with a single pointer without a path-based gesture, unless multipoint/path-based is essential."},
            {"type": "understanding", "text": "Understanding 2.5.1: Pinch-to-zoom, multi-finger swipe, and drawing gestures are difficult for users with motor impairments using head pointers, eye tracking, or single switches. Provide single-tap/click alternatives for all gestures. Maps: pinch-to-zoom should have +/- buttons. Carousels: swipe should have next/prev buttons."},
        ]
    },
    {
        "criterion_id": "2.5.2",
        "criterion_name": "Pointer Cancellation",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.2 Pointer Cancellation (Level A): For single-pointer functionality, at least one of: no down-event, abort/undo mechanism, up-event reversal, essential. This prevents accidental activation."},
            {"type": "understanding", "text": "Understanding 2.5.2: Users with motor impairments may accidentally press buttons. Using mouseup/click instead of mousedown allows users to move pointer away to cancel. Native HTML elements already do this. Custom components using mousedown/touchstart for activation fail this criterion. Always prefer click events."},
        ]
    },
    {
        "criterion_id": "2.5.3",
        "criterion_name": "Label in Name",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.3 Label in Name (Level A): For UI components with labels that include text or images of text, the accessible name contains the text that is presented visually."},
            {"type": "understanding", "text": "Understanding 2.5.3: Speech input users activate controls by saying the visible label. If the accessible name (aria-label) doesn't include the visible text, the command fails. Example: button shows 'Search' but aria-label='Find products' — saying 'Click Search' won't work. The accessible name must START WITH or include the visible label text."},
            {"type": "technique", "technique_id": "G211", "text": "Technique G211: Matching the accessible name to the visible label. Ensure aria-label includes visible text. If button shows 'Submit Order', aria-label can be 'Submit Order - proceed to payment' but must include 'Submit Order'. Don't use aria-label that contradicts visible text."},
        ]
    },
    {
        "criterion_id": "2.5.4",
        "criterion_name": "Motion Actuation",
        "wcag_level": "A",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.4 Motion Actuation (Level A): Functionality operated by device motion or user motion can also be operated by UI components, and motion response can be disabled. Exception: essential for accessible interface, or motion is used in a supported accessibility way."},
            {"type": "understanding", "text": "Understanding 2.5.4: Shake-to-undo, tilt-to-scroll, and motion-based games exclude wheelchair-mounted devices and users with tremors. Provide button/UI alternatives for all motion features. Allow disabling motion in settings. Device orientation changes should be handled by 1.3.4."},
        ]
    },
    {
        "criterion_id": "2.5.5",
        "criterion_name": "Target Size (Enhanced)",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.5 Target Size Enhanced (Level AAA): The size of the target for pointer inputs is at least 44 by 44 CSS pixels, except for: inline targets in text, user-agent controlled, essential, or equivalent target available."},
        ]
    },
    {
        "criterion_id": "2.5.6",
        "criterion_name": "Concurrent Input Mechanisms",
        "wcag_level": "AAA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.6 Concurrent Input Mechanisms (Level AAA): Web content does not restrict use of input modalities available on a platform except where the restriction is essential, required for security, or required to respect user settings. Users must be able to switch between input mechanisms (touch, keyboard, mouse, voice) at any point."},
            {"type": "understanding", "text": "Understanding 2.5.6: Users may switch between input methods during a session — start with keyboard, switch to touch, then use voice. Websites must not lock users into one input type. For example, don't disable keyboard input after a touch event is detected. Don't require only mouse for drag operations if touch is available. Allow all platform-supported inputs concurrently."},
        ]
    },
    {
        "criterion_id": "2.5.7",
        "criterion_name": "Dragging Movements",
        "wcag_level": "AA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.7 Dragging Movements (Level AA): All functionality that uses a dragging movement can be achieved by a single pointer without dragging, unless dragging is essential. New in WCAG 2.2."},
            {"type": "understanding", "text": "Understanding 2.5.7: Drag-and-drop for reordering, slider controls, and drawing tools are difficult for users with motor impairments. Provide click-based alternatives: move up/down buttons for reordering, text input for sliders, or click-to-place for drag operations."},
        ]
    },
    {
        "criterion_id": "2.5.8",
        "criterion_name": "Target Size (Minimum)",
        "wcag_level": "AA",
        "principle": "Operable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 2.5.8 Target Size Minimum (Level AA): Target size for pointer inputs is at least 24x24 CSS pixels, except: sufficient spacing (24px to adjacent targets), equivalent control meets size, inline in text, user-agent controlled, essential. New in WCAG 2.2."},
            {"type": "understanding", "text": "Understanding 2.5.8: Small touch targets fail users with motor impairments, tremors, limited dexterity. The 24x24px minimum ensures reliable activation. Fix: increase padding, min-width/min-height: 24px, adequate spacing between targets, pseudo-elements to enlarge touch area beyond visible element."},
        ]
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PRINCIPLE 3: UNDERSTANDABLE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── 3.1 Readable ─────────────────────────────────────

    {
        "criterion_id": "3.1.1",
        "criterion_name": "Language of Page",
        "wcag_level": "A",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.1.1 Language of Page (Level A): The default human language of each Web page can be programmatically determined."},
            {"type": "technique", "technique_id": "H57", "text": "Technique H57: Using lang attribute on html element. <html lang='en'>. Use BCP 47 tags: en, fr, de, ja, zh-Hans, pt-BR. Allows screen readers to use correct pronunciation. Without it, French text may be read with English phonetics."},
        ]
    },
    {
        "criterion_id": "3.1.2",
        "criterion_name": "Language of Parts",
        "wcag_level": "AA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.1.2 Language of Parts (Level AA): The human language of each passage or phrase can be programmatically determined, except for proper names, technical terms, words of indeterminate language, and words that are part of the surrounding text's vernacular."},
            {"type": "technique", "technique_id": "H58", "text": "Technique H58: Using lang attribute to identify changes in language. For multilingual pages: <p lang='fr'>Bonjour le monde</p> within an English page. Screen readers switch pronunciation rules. Common words adopted into the language (like 'rendezvous' in English) don't need marking."},
        ]
    },
    {
        "criterion_id": "3.1.3",
        "criterion_name": "Unusual Words",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.1.3 Unusual Words (Level AAA): A mechanism is available for identifying specific definitions of words or phrases used in an unusual or restricted way, including idioms and jargon."},
        ]
    },
    {
        "criterion_id": "3.1.4",
        "criterion_name": "Abbreviations",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.1.4 Abbreviations (Level AAA): A mechanism for identifying the expanded form or meaning of abbreviations is available. Use <abbr title='World Wide Web'>WWW</abbr> or spell out on first use."},
        ]
    },
    {
        "criterion_id": "3.1.5",
        "criterion_name": "Reading Level",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.1.5 Reading Level (Level AAA): When text requires more than lower secondary education reading level, supplemental content or a simpler version is available."},
        ]
    },
    {
        "criterion_id": "3.1.6",
        "criterion_name": "Pronunciation",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.1.6 Pronunciation (Level AAA): A mechanism for identifying specific pronunciation of words where meaning is ambiguous without knowing the pronunciation."},
        ]
    },

    # ── 3.2 Predictable ──────────────────────────────────

    {
        "criterion_id": "3.2.1",
        "criterion_name": "On Focus",
        "wcag_level": "A",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.2.1 On Focus (Level A): When any UI component receives focus, it does not initiate a change of context. Tabbing to a form field should NOT submit the form, navigate to another page, or significantly change page content."},
            {"type": "understanding", "text": "Understanding 3.2.1: Changes of context on focus are disorienting, especially for screen reader users. Don't: auto-submit forms on focus, open new windows on focus, change active content/panel on focus. Focus should only move the visual focus indicator, nothing else."},
        ]
    },
    {
        "criterion_id": "3.2.2",
        "criterion_name": "On Input",
        "wcag_level": "A",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.2.2 On Input (Level A): Changing the setting of any UI component does not automatically cause a change of context unless the user has been advised beforehand. Selecting a radio button or changing a dropdown should NOT auto-submit or navigate."},
            {"type": "understanding", "text": "Understanding 3.2.2: Unexpected navigation when interacting with form controls is confusing. Don't: auto-submit when dropdown selection changes, navigate when checkbox is checked. Use an explicit submit button. If auto-change is needed, warn users beforehand in adjacent text."},
            {"type": "technique", "technique_id": "G80", "text": "Technique G80: Providing a submit button to initiate a change of context. Always use a Submit/Go/Apply button rather than auto-submitting on dropdown change. If auto-update is needed (like filtering), update content in-place without navigation and announce changes to screen readers."},
        ]
    },
    {
        "criterion_id": "3.2.3",
        "criterion_name": "Consistent Navigation",
        "wcag_level": "AA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.2.3 Consistent Navigation (Level AA): Navigational mechanisms that are repeated on multiple pages occur in the same relative order each time, unless the user initiates a change."},
            {"type": "understanding", "text": "Understanding 3.2.3: Users learn where navigation elements are. Moving the search box, reordering nav links, or changing footer layout between pages causes confusion, especially for screen reader users and users with cognitive disabilities. Keep nav, search, and other repeated elements in the same position and order across all pages."},
        ]
    },
    {
        "criterion_id": "3.2.4",
        "criterion_name": "Consistent Identification",
        "wcag_level": "AA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.2.4 Consistent Identification (Level AA): Components that have the same functionality within a set of pages are identified consistently. Same function = same label, icon, and text alternative across pages."},
            {"type": "understanding", "text": "Understanding 3.2.4: If the search function is labeled 'Search' on one page, 'Find' on another, and 'Look up' on a third, users with cognitive disabilities get confused. Use the same labels, icons, and alt text for identical functionality across all pages. This includes print, search, navigation, and form controls."},
        ]
    },
    {
        "criterion_id": "3.2.5",
        "criterion_name": "Change on Request",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.2.5 Change on Request (Level AAA): Changes of context are initiated only by user request, or a mechanism is available to turn off such changes."},
        ]
    },
    {
        "criterion_id": "3.2.6",
        "criterion_name": "Consistent Help",
        "wcag_level": "A",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.2.6 Consistent Help (Level A): If a web page contains help mechanisms (human contact details, contact mechanism, self-help option, automated contact mechanism) and these are repeated across pages, they occur in the same relative order. New in WCAG 2.2."},
            {"type": "understanding", "text": "Understanding 3.2.6: Users with cognitive disabilities need to find help consistently. If there's a chat widget, phone number, or FAQ link on multiple pages, place them in the same location and order. This helps users develop a reliable mental model for finding help."},
        ]
    },

    # ── 3.3 Input Assistance ─────────────────────────────

    {
        "criterion_id": "3.3.1",
        "criterion_name": "Error Identification",
        "wcag_level": "A",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.1 Error Identification (Level A): If an input error is automatically detected, the item in error is identified and the error is described to the user in text."},
            {"type": "understanding", "text": "Understanding 3.3.1: Error messages must be in text (not just red borders or icons). Identify which field has the error and describe what's wrong. 'Error in form' is insufficient — say 'Email address: please enter a valid email format'. Use aria-invalid='true' and aria-describedby linking to error message. Move focus to first error on submit."},
            {"type": "technique", "technique_id": "G83", "text": "Technique G83: Providing text descriptions of errors. Show error text near the field: 'Email: Please enter a valid email address (e.g., name@example.com)'. Use aria-describedby to link input to error. Set aria-invalid='true'. Show error summary at top with links to each field."},
        ]
    },
    {
        "criterion_id": "3.3.2",
        "criterion_name": "Labels or Instructions",
        "wcag_level": "A",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.2 Labels or Instructions (Level A): Labels or instructions are provided when content requires user input."},
            {"type": "understanding", "text": "Understanding 3.3.2: Every form field needs a visible label or instructions. Placeholder text alone is NOT sufficient — it disappears on typing. Required fields must be clearly marked (not just by color). Groups of related fields use fieldset/legend. Date formats should be specified (MM/DD/YYYY)."},
        ]
    },
    {
        "criterion_id": "3.3.3",
        "criterion_name": "Error Suggestion",
        "wcag_level": "AA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.3 Error Suggestion (Level AA): If an input error is automatically detected and suggestions for correction are known, the suggestions are provided to the user, unless it would jeopardize security or purpose."},
            {"type": "understanding", "text": "Understanding 3.3.3: Go beyond 'invalid input' — suggest corrections. 'Date must be in MM/DD/YYYY format', 'Password needs at least 8 characters and one number', 'Did you mean user@gmail.com?'. Helps users with cognitive disabilities understand what's expected."},
        ]
    },
    {
        "criterion_id": "3.3.4",
        "criterion_name": "Error Prevention (Legal, Financial, Data)",
        "wcag_level": "AA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.4 Error Prevention Legal Financial Data (Level AA): For pages with legal commitments, financial transactions, or user data modification/deletion: submissions are reversible, data is checked and user can correct, or a mechanism to review/confirm/correct before finalizing."},
            {"type": "understanding", "text": "Understanding 3.3.4: Users should be able to review before final submission of orders, payments, legal agreements. Provide confirmation pages, undo mechanisms, or edit capabilities. 'Review your order' page before payment. Ability to cancel within a time period. Delete confirmations."},
        ]
    },
    {
        "criterion_id": "3.3.5",
        "criterion_name": "Help",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.5 Help (Level AAA): Context-sensitive help is available. Help text, tooltips, or links to help documentation are provided for complex inputs or processes."},
        ]
    },
    {
        "criterion_id": "3.3.6",
        "criterion_name": "Error Prevention (All)",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.6 Error Prevention All (Level AAA): For all forms requiring user submission: submissions are reversible, checked with correction opportunity, or reviewed/confirmed before finalizing."},
        ]
    },
    {
        "criterion_id": "3.3.7",
        "criterion_name": "Redundant Entry",
        "wcag_level": "A",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.7 Redundant Entry (Level A): Information previously entered by or provided to the user that is required for the same process is either auto-populated or available for the user to select. New in WCAG 2.2. Exception: re-entering is essential (password confirmation) or security requires it."},
            {"type": "understanding", "text": "Understanding 3.3.7: Don't make users re-enter information already provided in the same process. If billing address was entered, auto-fill shipping address or provide 'same as billing' option. If name was given on step 1, pre-populate on step 3. Reduces cognitive load and errors."},
        ]
    },
    {
        "criterion_id": "3.3.8",
        "criterion_name": "Accessible Authentication (Minimum)",
        "wcag_level": "AA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.8 Accessible Authentication Minimum (Level AA): A cognitive function test (remembering password, solving puzzle) is not required for any step in authentication unless: an alternative method is available, a mechanism assists the user (copy-paste allowed), the test is object recognition, or the test is identification of personal content. New in WCAG 2.2."},
            {"type": "understanding", "text": "Understanding 3.3.8: CAPTCHAs, memory-based puzzles, and password-only auth exclude users with cognitive disabilities. Allow copy-paste in password fields (for password managers). Provide alternatives to CAPTCHAs (email verification, SMS codes). Support passkeys and WebAuthn. Don't disable paste on password fields."},
        ]
    },
    {
        "criterion_id": "3.3.9",
        "criterion_name": "Accessible Authentication (Enhanced)",
        "wcag_level": "AAA",
        "principle": "Understandable",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 3.3.9 Accessible Authentication Enhanced (Level AAA): No cognitive function test required for authentication, with narrower exceptions than 3.3.8 (no object recognition or personal content exceptions)."},
        ]
    },

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PRINCIPLE 4: ROBUST
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    {
        "criterion_id": "4.1.1",
        "criterion_name": "Parsing (Deprecated)",
        "wcag_level": "A",
        "principle": "Robust",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 4.1.1 Parsing (Level A): DEPRECATED in WCAG 2.2. Originally required valid HTML. Modern browsers handle parsing errors well. This criterion exists for backwards compatibility but is always considered satisfied in WCAG 2.2 conformance."},
        ]
    },
    {
        "criterion_id": "4.1.2",
        "criterion_name": "Name, Role, Value",
        "wcag_level": "A",
        "principle": "Robust",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 4.1.2 Name Role Value (Level A): For all UI components: name and role can be programmatically determined, states/properties/values can be programmatically set, and notification of changes is available to assistive technologies."},
            {"type": "understanding", "text": "Understanding 4.1.2: AT needs to know what each component IS (role), what it's CALLED (name), and its STATE (value). Native HTML provides this. Custom widgets need ARIA: role='button', aria-label for name, aria-expanded/aria-selected/aria-checked for states. Common failures: div-as-button without role, custom dropdown without aria-expanded."},
            {"type": "technique", "technique_id": "ARIA16", "text": "Technique ARIA16: Using aria-labelledby for accessible names. Reference visible text: <span id='user-label'>Username</span> <input aria-labelledby='user-label'>. Can reference multiple IDs. Preferred over aria-label when visible text exists (keeps accessible name matching visible text per 2.5.3)."},
            {"type": "technique", "technique_id": "ARIA5", "text": "Technique ARIA5: Using ARIA state and property attributes. Communicate dynamic changes: aria-expanded='true/false' for collapsible sections, aria-selected for tabs, aria-checked for custom checkboxes, aria-disabled='true', aria-hidden='true' for decorative content. Update via JS when states change."},
        ]
    },
    {
        "criterion_id": "4.1.3",
        "criterion_name": "Status Messages",
        "wcag_level": "AA",
        "principle": "Robust",
        "chunks": [
            {"type": "criterion", "text": "WCAG 2.2 SC 4.1.3 Status Messages (Level AA): In content implemented using markup languages, status messages can be programmatically determined through role or properties such that they can be presented to the user by assistive technologies without receiving focus."},
            {"type": "understanding", "text": "Understanding 4.1.3: When content updates dynamically (search results count, form submission success, error messages, cart item count), screen readers must be notified without moving focus. Use ARIA live regions: role='status' for polite updates, role='alert' for urgent messages, aria-live='polite' for search results, aria-live='assertive' for errors."},
            {"type": "technique", "technique_id": "ARIA22", "text": "Technique ARIA22: Using role=status for status messages. For non-urgent updates: <div role='status'>3 results found</div>. For urgent/errors: <div role='alert'>Payment failed. Please try again.</div>. For progress: <div role='status' aria-live='polite'>Uploading... 75%</div>. Ensure the live region exists in DOM before content is added."},
        ]
    },
]


class WCAGDataLoader:
    """
    Loads comprehensive WCAG 2.2 knowledge and produces chunks for embedding.
    
    Usage:
        loader = WCAGDataLoader()
        chunks = loader.load_all()
        loader.save_chunks(chunks, './data/wcag_docs/chunks.json')
    """

    def load_all(self) -> List[WCAGChunk]:
        """Load all WCAG knowledge into chunks."""
        logger.info("📚 Loading WCAG 2.2 comprehensive knowledge base...")
        chunks = []
        criteria_count = 0

        for criterion_data in WCAG_KNOWLEDGE:
            criterion_id = criterion_data["criterion_id"]
            criterion_name = criterion_data["criterion_name"]
            wcag_level = criterion_data["wcag_level"]
            principle = criterion_data["principle"]
            criteria_count += 1

            for chunk_data in criterion_data["chunks"]:
                chunk_type = chunk_data["type"]
                text = chunk_data["text"]
                technique_id = chunk_data.get("technique_id", "")

                id_source = f"{criterion_id}_{chunk_type}_{technique_id}_{text[:50]}"
                chunk_id = hashlib.md5(id_source.encode()).hexdigest()[:12]

                chunk = WCAGChunk(
                    chunk_id=chunk_id,
                    text=text,
                    criterion_id=criterion_id,
                    criterion_name=criterion_name,
                    wcag_level=wcag_level,
                    principle=principle,
                    chunk_type=chunk_type,
                    technique_id=technique_id,
                    source_url=f"https://www.w3.org/WAI/WCAG22/Understanding/{criterion_id.replace('.', '')}/",
                )
                chunks.append(chunk)

        logger.info(f"  ✅ Loaded {len(chunks)} chunks covering {criteria_count} criteria")
        return chunks

    def save_chunks(self, chunks: List[WCAGChunk], filepath: str):
        """Save chunks to JSON for inspection/debugging."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump([c.to_dict() for c in chunks], f, indent=2)
        logger.info(f"  💾 Saved {len(chunks)} chunks to {filepath}")

    def load_chunks_from_file(self, filepath: str) -> List[WCAGChunk]:
        """Load chunks from a saved JSON file."""
        with open(filepath) as f:
            data = json.load(f)
        return [WCAGChunk(**d) for d in data]

    def get_stats(self) -> dict:
        """Get coverage statistics."""
        criteria = set()
        techniques = set()
        chunk_types = {}
        for c in WCAG_KNOWLEDGE:
            criteria.add(c["criterion_id"])
            for chunk in c["chunks"]:
                t = chunk["type"]
                chunk_types[t] = chunk_types.get(t, 0) + 1
                if chunk.get("technique_id"):
                    techniques.add(chunk["technique_id"])

        return {
            "total_criteria": len(criteria),
            "total_chunks": sum(chunk_types.values()),
            "chunk_types": chunk_types,
            "total_techniques": len(techniques),
            "level_a": sum(1 for c in WCAG_KNOWLEDGE if c["wcag_level"] == "A"),
            "level_aa": sum(1 for c in WCAG_KNOWLEDGE if c["wcag_level"] == "AA"),
            "level_aaa": sum(1 for c in WCAG_KNOWLEDGE if c["wcag_level"] == "AAA"),
        }