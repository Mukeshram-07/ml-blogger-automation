"""
content_writer.py
-----------------
Transforms raw topic notes (experience_points, mistakes, lessons)
into a structured, human-style technical blog article.

Two modes:
  1. Groq LLM (default when GROQ_API_KEY is set + USE_LLM=true)
     Uses llama3-8b-8192 via Groq's ultra-fast inference API.
     Falls back to template writer if the API call fails.

  2. Template-based (fallback / offline)
     Pure Python — no external API needed. Works in CI always.
"""

import json
from typing import List

import requests

from app.config import config
from app.logger import logger
from app.models import Article, ArticleSection, Topic


# ── Groq API constants ─────────────────────────────────────────────────────────

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


# ── Template-based writer (always available, offline safe) ────────────────────

def _build_intro(topic: Topic) -> str:
    first_tag = topic.tags[0] if topic.tags else topic.category
    return (
        f"When I started working with {first_tag}, "
        f"I quickly realized there was a gap between theory and what actually happens in practice. "
        f"This post is about {topic.title_seed.lower()}. "
        f"I'll walk you through what I learned, what tripped me up, and the lessons that stuck with me. "
        f"No fluff — just honest notes from someone who went through it."
    )


def _build_experience_sections(topic: Topic) -> List[ArticleSection]:
    sections = []
    for i, point in enumerate(topic.experience_points, start=1):
        content = (
            f"{point}. "
            f"This was one of those things I had to learn by doing — "
            f"reading about it only gets you so far. "
            f"Once I actually ran into this in a real project, it clicked. "
            f"If you're at a similar stage, keep this in mind: it matters more than it looks at first."
        )
        sections.append(
            ArticleSection(
                heading=f"Key Insight #{i}: {point.rstrip('.')}",
                content=content,
            )
        )
    return sections


def _build_tools_section(topic: Topic) -> List[ArticleSection]:
    if not topic.tags:
        return []
    tools_str = ", ".join(topic.tags)
    return [
        ArticleSection(
            heading="Tools and Stack I Used",
            content=(
                f"For this, I worked with: {tools_str}. "
                f"Each tool had its own learning curve. "
                f"I'll point out specifically where each one helped — or caused confusion — as we go."
            ),
        )
    ]


def _build_mistakes_section(topic: Topic) -> str:
    if not topic.mistakes:
        return ""
    lines = "\n".join(f"- {m}" for m in topic.mistakes)
    return (
        f"Here are the mistakes I made that I wish I had known upfront:\n\n"
        f"{lines}\n\n"
        f"These aren't meant to embarrass me — they're here because I've seen others hit the same walls. "
        f"Hopefully reading this saves you some debugging time."
    )


def _build_lessons_section(topic: Topic) -> str:
    if not topic.lessons:
        return ""
    lines = "\n".join(f"- {l}" for l in topic.lessons)
    return (
        f"After going through all of this, here's what I'd tell myself at the start:\n\n"
        f"{lines}\n\n"
        f"These aren't rules — they're patterns I noticed. Your context might be different, "
        f"but the core ideas tend to hold."
    )


def _build_code_mention(topic: Topic) -> List[ArticleSection]:
    if not topic.optional_code_snippet_idea:
        return []
    return [
        ArticleSection(
            heading="A Quick Code Example to Ground This",
            content=(
                f"To make this concrete, imagine you're building: {topic.optional_code_snippet_idea}. "
                f"The logic here is straightforward once you see it in action. "
                f"I'll keep the example minimal so the concept stays front and center — "
                f"real projects will obviously be more complex."
            ),
        )
    ]


def _build_conclusion(topic: Topic) -> str:
    return (
        f"That's my honest take on {topic.title_seed.lower()}. "
        f"{topic.category} has a lot of moving parts, and getting comfortable with it takes time. "
        f"But every mistake you make is context you keep — and it compounds. "
        f"If you found this useful, or if you've hit a different version of the same problem, "
        f"I'd love to hear about it. This is a learning log as much as it is a blog."
    )


def _write_with_template(topic: Topic) -> Article:
    """Pure template-based article construction. No external API needed."""
    logger.info(f"Building article for topic {topic.topic_id} using template writer.")

    sections: List[ArticleSection] = []
    sections.extend(_build_tools_section(topic))
    sections.extend(_build_experience_sections(topic))
    sections.extend(_build_code_mention(topic))

    return Article(
        title=topic.title_seed,
        intro=_build_intro(topic),
        sections=sections,
        mistakes_section=_build_mistakes_section(topic),
        lessons_section=_build_lessons_section(topic),
        conclusion=_build_conclusion(topic),
        tags=topic.tags,
        category=topic.category,
    )


# ── Groq LLM writer ───────────────────────────────────────────────────────────

def _build_groq_prompt(topic: Topic) -> str:
    """Build the structured prompt from topic notes."""
    exp_points = "\n".join(f"- {p}" for p in topic.experience_points)
    mistakes = "\n".join(f"- {m}" for m in topic.mistakes)
    lessons = "\n".join(f"- {l}" for l in topic.lessons)
    snippet_hint = (
        f"\nCode example idea: {topic.optional_code_snippet_idea}"
        if topic.optional_code_snippet_idea
        else ""
    )

    return f"""Write a technical blog post based on my personal learning notes. You are my writing assistant — expand my raw notes into a polished article. Preserve my voice as a learner and builder.

Title: {topic.title_seed}
Category: {topic.category}
Difficulty: {topic.difficulty}
Tags: {", ".join(topic.tags)}

My experience notes:
{exp_points}

Mistakes I made:
{mistakes}

Lessons I learned:
{lessons}{snippet_hint}

INSTRUCTIONS:
- Write in first person, honest and direct tone
- Structure with clear section headings (use ## for headings)
- Include a "## Mistakes I Made" section
- Include a "## What I'd Do Differently" section
- End with a short human conclusion
- Do NOT use marketing language or buzzwords
- Sound like a developer sharing notes, not writing SEO content
- Keep it under 700 words
- Return only the blog post content, no meta commentary""".strip()


def _parse_groq_response(raw_text: str, topic: Topic) -> Article:
    """
    Parse Groq's free-form markdown output into our Article model.
    Splits on ## headings, first paragraph = intro, last = conclusion.
    """
    lines = raw_text.strip().split("\n")

    intro_lines = []
    sections: List[ArticleSection] = []
    current_heading = None
    current_content_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            # Save previous section
            if current_heading is not None:
                sections.append(ArticleSection(
                    heading=current_heading,
                    content="\n".join(current_content_lines).strip(),
                ))
            current_heading = stripped[3:].strip()
            current_content_lines = []
        elif current_heading is None:
            # Still in intro
            if stripped:
                intro_lines.append(stripped)
        else:
            current_content_lines.append(line)

    # Save last section
    if current_heading is not None and current_content_lines:
        sections.append(ArticleSection(
            heading=current_heading,
            content="\n".join(current_content_lines).strip(),
        ))

    intro = " ".join(intro_lines) if intro_lines else _build_intro(topic)

    # Pull out conclusion from last section if it looks like one
    conclusion = _build_conclusion(topic)
    if sections and any(
        kw in sections[-1].heading.lower()
        for kw in ["conclusion", "wrap", "final", "summary", "closing"]
    ):
        conclusion = sections[-1].content
        sections = sections[:-1]

    if len(sections) == 0:
        logger.warning("Groq response had no parseable sections. Using template fallback.")
        return _write_with_template(topic)

    return Article(
        title=topic.title_seed,
        intro=intro,
        sections=sections,
        mistakes_section=None,   # Groq weaves them into sections
        lessons_section=None,
        conclusion=conclusion,
        tags=topic.tags,
        category=topic.category,
    )


def _write_with_groq(topic: Topic) -> Article:
    """
    Call Groq API (llama3-8b-8192) to generate enriched article prose.
    Falls back to template writer on any failure.
    """
    logger.info(
        f"Calling Groq API (model={config.GROQ_MODEL}) for topic {topic.topic_id}."
    )

    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config.GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a technical writing assistant helping an ML engineer "
                    "write honest, experience-based blog posts. "
                    "Preserve the author's voice — they are a learner and builder, not a marketer. "
                    "Use plain language. Avoid buzzwords. Sound human and direct."
                ),
            },
            {
                "role": "user",
                "content": _build_groq_prompt(topic),
            },
        ],
        "temperature": 0.7,
        "max_tokens": 2048,
    }

    try:
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            logger.warning(
                f"Groq API returned {response.status_code}: {response.text[:300]}. "
                f"Falling back to template writer."
            )
            return _write_with_template(topic)

        data = response.json()
        raw_text = data["choices"][0]["message"]["content"].strip()
        logger.info(
            f"Groq response received. Length: {len(raw_text)} chars. Parsing article."
        )
        return _parse_groq_response(raw_text, topic)

    except requests.exceptions.Timeout:
        logger.warning("Groq API timed out. Falling back to template writer.")
        return _write_with_template(topic)

    except Exception as e:
        logger.warning(f"Groq API call failed: {e}. Falling back to template writer.")
        return _write_with_template(topic)


# ── Public interface ───────────────────────────────────────────────────────────

def write_article(topic: Topic) -> Article:
    """
    Main entry point.
    Routes to Groq LLM writer if USE_LLM=true and GROQ_API_KEY is set.
    Otherwise falls back to template writer.
    """
    if config.USE_LLM and config.GROQ_API_KEY:
        return _write_with_groq(topic)

    logger.info("USE_LLM=false or no GROQ_API_KEY — using template writer.")
    return _write_with_template(topic)
