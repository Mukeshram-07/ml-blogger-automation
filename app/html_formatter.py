"""
html_formatter.py
-----------------
Converts an Article model into clean Blogger-compatible HTML.

Design goals:
- Semantic HTML (h2, h3, p, ul, pre/code)
- Readable in Blogger's post editor
- Mobile-friendly inline styles
- No external CSS dependencies
"""

from app.logger import logger
from app.models import Article


# ── Style constants ────────────────────────────────────────────────────────────

H2_STYLE = 'style="font-size:1.4em; color:#2c3e50; margin-top:2em; margin-bottom:0.4em; border-bottom:2px solid #e0e0e0; padding-bottom:6px;"'
P_STYLE = 'style="font-size:1em; line-height:1.75; color:#333; margin-bottom:1em;"'
UL_STYLE = 'style="line-height:1.9; color:#333; padding-left:1.5em;"'
LI_STYLE = 'style="margin-bottom:0.4em;"'
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
    return f"<p {P_STYLE}>{text}</p>\n"


def _h2(text: str) -> str:
    return f"<h2 {H2_STYLE}>{text}</h2>\n"


def _ul(items: list) -> str:
    if not items:
        return ""
    li_items = "".join(f"<li {LI_STYLE}>{item}</li>\n" for item in items)
    return f"<ul {UL_STYLE}>\n{li_items}</ul>\n"


def _hr() -> str:
    return f"<hr {DIVIDER_STYLE}/>\n"


def _inline_markdown(text: str) -> str:
    """Convert inline markdown (bold, italic, inline code) to HTML."""
    import re
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    text = re.sub(
        r"`(.+?)`",
        r'<code style="background:#f0f0f0; padding:1px 5px; border-radius:3px; font-family:monospace; font-size:0.92em;">\1</code>',
        text,
    )
    return text


def _format_section_content(raw_text: str) -> str:
    """
    Renders section content to HTML.
    Handles: bullet lists, ### subheadings, code fences, bold/italic, paragraphs.
    """
    if not raw_text.strip():
        return ""

    import re as _re
    html = []
    lines = raw_text.split("\n")
    in_code_block = False
    code_lines = []
    bullet_buffer = []

    def flush_bullets():
        if bullet_buffer:
            html.append(_ul(bullet_buffer))
            bullet_buffer.clear()

    for line in lines:
        stripped = line.strip()

        # ── Code fence ────────────────────────────────────────────────────
        if stripped.startswith("```"):
            if not in_code_block:
                flush_bullets()
                in_code_block = True
                code_lines = []
            else:
                in_code_block = False
                code_content = "\n".join(code_lines)
                html.append(f"<pre><code {CODE_BLOCK_STYLE}>{code_content}</code></pre>\n")
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        # ── H3 subheading ─────────────────────────────────────────────────
        if stripped.startswith("### "):
            flush_bullets()
            subheading = stripped[4:].strip()
            html.append(
                f'<h3 style="font-size:1.1em; color:#34495e; margin-top:1.4em; margin-bottom:0.3em;">'
                f'{subheading}</h3>\n'
            )
            continue

        # ── Bullet line ───────────────────────────────────────────────────
        if stripped.startswith("- ") or stripped.startswith("* "):
            bullet_buffer.append(_inline_markdown(stripped[2:].strip()))
            continue

        # ── Numbered list ─────────────────────────────────────────────────
        if _re.match(r"^\d+\.\s", stripped):
            flush_bullets()
            content = _re.sub(r"^\d+\.\s", "", stripped)
            html.append(_p(_inline_markdown(content)))
            continue

        # ── Empty line ────────────────────────────────────────────────────
        if not stripped:
            flush_bullets()
            continue

        # ── Regular paragraph ─────────────────────────────────────────────
        flush_bullets()
        html.append(_p(_inline_markdown(stripped)))

    flush_bullets()
    return "".join(html)


def _tags_html(tags: list) -> str:
    if not tags:
        return ""
    badges = "".join(f'<span {TAG_STYLE}>{tag}</span>' for tag in tags)
    return f'<p style="margin-top:1em;">{badges}</p>\n'


def format_article_to_html(article: Article) -> str:
    """
    Convert a structured Article into clean Blogger-ready HTML.
    Text only — no images.
    """
    logger.info(f"Formatting article '{article.title}' to HTML.")
    html_parts = []

    # ── Intro ──────────────────────────────────────────────────────────────
    html_parts.append(_p(_inline_markdown(article.intro)))
    html_parts.append(_hr())

    # ── Body sections ──────────────────────────────────────────────────────
    for section in article.sections:
        html_parts.append(_h2(section.heading))
        html_parts.append(_format_section_content(section.content))

    # ── Mistakes section ───────────────────────────────────────────────────
    if article.mistakes_section:
        html_parts.append(_hr())
        html_parts.append(_h2("⚠️ Mistakes I Made"))
        html_parts.append(_format_section_content(article.mistakes_section))

    # ── Lessons section ────────────────────────────────────────────────────
    if article.lessons_section:
        html_parts.append(_hr())
        html_parts.append(_h2("✅ What I Learned (The Hard Way)"))
        html_parts.append(_format_section_content(article.lessons_section))

    # ── Conclusion ─────────────────────────────────────────────────────────
    html_parts.append(_hr())
    html_parts.append(_h2("Wrapping Up"))
    html_parts.append(_format_section_content(article.conclusion))

    # ── Tags footer ────────────────────────────────────────────────────────
    html_parts.append(_hr())
    html_parts.append(
        f'<p {FOOTER_STYLE}>Category: <strong>{article.category}</strong></p>\n'
    )
    html_parts.append(_tags_html(article.tags))

    full_html = "".join(html_parts)
    logger.debug(f"HTML generated. Length: {len(full_html)} characters.")
    return full_html
