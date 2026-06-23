"""
html_formatter.py
-----------------
Converts an Article model into clean Blogger-compatible HTML.

Design goals:
- Semantic HTML (h2, p, ul, blockquote, pre)
- Readable in Blogger's post editor
- Mobile-friendly inline styles where needed
- No external CSS dependencies
"""

from app.logger import logger
from app.models import Article


# ── Style constants ────────────────────────────────────────────────────────────

H2_STYLE = 'style="font-size:1.4em; color:#2c3e50; margin-top:2em; margin-bottom:0.4em; border-bottom:2px solid #e0e0e0; padding-bottom:6px;"'
P_STYLE = 'style="font-size:1em; line-height:1.75; color:#333; margin-bottom:1em;"'
UL_STYLE = 'style="line-height:1.9; color:#333; padding-left:1.5em;"'
LI_STYLE = 'style="margin-bottom:0.4em;"'
BLOCKQUOTE_STYLE = (
    'style="border-left:4px solid #3498db; padding:0.6em 1em; '
    'background:#f0f7fd; color:#555; font-style:italic; margin:1.5em 0;"'
)
CODE_BLOCK_STYLE = (
    'style="background:#1e1e1e; color:#d4d4d4; padding:1em 1.2em; '
    'border-radius:6px; font-family:monospace; font-size:0.92em; '
    'overflow-x:auto; display:block; margin:1.2em 0;"'
)
TAG_STYLE = (
    'style="display:inline-block; background:#e8f4f8; color:#2980b9; '
    'padding:2px 10px; border-radius:12px; font-size:0.82em; margin:2px;"'
)
DIVIDER_STYLE = 'style="border:none; border-top:1px solid #eee; margin:2em 0;"'
FOOTER_STYLE = 'style="font-size:0.88em; color:#888; margin-top:2.5em; padding-top:1em; border-top:1px solid #eee;"'


def _p(text: str) -> str:
    """Wrap text in a styled paragraph tag."""
    return f"<p {P_STYLE}>{text}</p>\n"


def _h2(text: str) -> str:
    """Wrap text in a styled h2 tag."""
    return f"<h2 {H2_STYLE}>{text}</h2>\n"


def _ul(items: list) -> str:
    """Convert a list of strings to a styled unordered list."""
    if not items:
        return ""
    li_items = "".join(f"<li {LI_STYLE}>{item}</li>\n" for item in items)
    return f"<ul {UL_STYLE}>\n{li_items}</ul>\n"


def _blockquote(text: str) -> str:
    return f"<blockquote {BLOCKQUOTE_STYLE}>{text}</blockquote>\n"


def _hr() -> str:
    return f"<hr {DIVIDER_STYLE}/>\n"


def _newlines_to_paragraphs(text: str) -> str:
    """
    Convert multi-line text into multiple <p> tags.
    Splits on double newlines or single newlines for bullet-like lines.
    """
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    result = []
    for line in lines:
        if line.startswith("- "):
            # Treat as a list item — collect into a ul block handled separately
            result.append(f"<li {LI_STYLE}>{line[2:]}</li>")
        else:
            result.append(_p(line))
    return "".join(result)


def _format_bullet_section(raw_text: str) -> str:
    """
    Detect if the raw_text is a bullet-list format and render accordingly.
    If it has "- " lines, renders as <ul>. Otherwise as paragraphs.
    """
    lines = [l.strip() for l in raw_text.strip().split("\n") if l.strip()]
    bullet_lines = [l[2:] for l in lines if l.startswith("- ")]
    prose_lines = [l for l in lines if not l.startswith("- ")]

    html = ""
    if prose_lines:
        html += _p(" ".join(prose_lines))
    if bullet_lines:
        html += _ul(bullet_lines)
    return html


def _tags_html(tags: list) -> str:
    """Render tags as styled inline badges."""
    if not tags:
        return ""
    badges = "".join(f'<span {TAG_STYLE}>{tag}</span>' for tag in tags)
    return f'<p style="margin-top:1em;">{badges}</p>\n'


def format_article_to_html(article: Article) -> str:
    """
    Convert a structured Article into clean Blogger-ready HTML.
    """
    logger.info(f"Formatting article '{article.title}' to HTML.")
    html_parts = []

    # ── Intro ──────────────────────────────────────────────────────────────
    html_parts.append(_p(article.intro))
    html_parts.append(_hr())

    # ── Body sections ──────────────────────────────────────────────────────
    for section in article.sections:
        html_parts.append(_h2(section.heading))
        html_parts.append(_format_bullet_section(section.content))

    # ── Mistakes section ───────────────────────────────────────────────────
    if article.mistakes_section:
        html_parts.append(_hr())
        html_parts.append(_h2("⚠️ Mistakes I Made"))
        html_parts.append(_format_bullet_section(article.mistakes_section))

    # ── Lessons section ────────────────────────────────────────────────────
    if article.lessons_section:
        html_parts.append(_hr())
        html_parts.append(_h2("✅ What I Learned (The Hard Way)"))
        html_parts.append(_format_bullet_section(article.lessons_section))

    # ── Conclusion ─────────────────────────────────────────────────────────
    html_parts.append(_hr())
    html_parts.append(_h2("Wrapping Up"))
    html_parts.append(_p(article.conclusion))

    # ── Tags footer ────────────────────────────────────────────────────────
    html_parts.append(_hr())
    html_parts.append(
        f'<p {FOOTER_STYLE}>Category: <strong>{article.category}</strong></p>\n'
    )
    html_parts.append(_tags_html(article.tags))

    full_html = "".join(html_parts)
    logger.debug(f"HTML generated. Length: {len(full_html)} characters.")
    return full_html
