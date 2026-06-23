"""
publisher.py
------------
Orchestrates the end-to-end publishing pipeline:

  1. Load topics → pick next pending
  2. Write article from notes
  3. Format to HTML
  4. Publish to Blogger (or dry-run/draft)
  5. Mark topic posted / failed
  6. Save post history log
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

from app.blogger_client import publish_post
from app.config import config
from app.content_writer import write_article
from app.html_formatter import format_article_to_html
from app.logger import logger
from app.models import PostResult
from app.topic_loader import (
    get_next_pending_topic,
    load_topics,
    mark_topic_failed,
    mark_topic_posted,
    get_stats,
)


def _save_post_log(result: PostResult) -> None:
    """Append the result of a publish attempt to the post history log."""
    os.makedirs(config.LOG_DIR, exist_ok=True)

    history = []
    if os.path.exists(config.POST_LOG_FILE):
        with open(config.POST_LOG_FILE, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []

    history.append(result.model_dump())

    with open(config.POST_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False, default=str)

    logger.debug(f"Post log saved to {config.POST_LOG_FILE}")


def run_publish_pipeline() -> Optional[PostResult]:
    """
    Execute one full publish cycle.

    Returns:
        PostResult if a topic was processed, None if no pending topics.
    """
    logger.info("=" * 60)
    logger.info("ML Blogger Automation — starting publish pipeline")
    logger.info(
        f"Mode: {'DRY RUN' if config.DRY_RUN else ('DRAFT' if config.DRAFT_MODE else 'LIVE PUBLISH')}"
    )
    logger.info("=" * 60)

    # ── Step 1: Load topics ──────────────────────────────────────────────
    topics = load_topics()
    stats = get_stats(topics)
    logger.info(f"Topic stats: {stats}")

    # ── Step 2: Pick next pending topic ──────────────────────────────────
    topic = get_next_pending_topic(topics)
    if topic is None:
        logger.warning("No pending topics. Nothing to publish.")
        return None

    # ── Step 3: Write article from notes ─────────────────────────────────
    try:
        article = write_article(topic)
        logger.info(f"Article written: '{article.title}'")
    except Exception as e:
        logger.error(f"Content writing failed for topic {topic.topic_id}: {e}")
        mark_topic_failed(topics, topic.topic_id)
        return PostResult(
            success=False,
            topic_id=topic.topic_id,
            title=topic.title_seed,
            error_message=f"Content writing failed: {e}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # ── Step 4: Format to HTML ────────────────────────────────────────────
    try:
        html_content = format_article_to_html(article)
    except Exception as e:
        logger.error(f"HTML formatting failed for topic {topic.topic_id}: {e}")
        mark_topic_failed(topics, topic.topic_id)
        return PostResult(
            success=False,
            topic_id=topic.topic_id,
            title=topic.title_seed,
            error_message=f"HTML formatting failed: {e}",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # ── Step 5: Dry run mode — skip API call ─────────────────────────────
    if config.DRY_RUN:
        logger.info("[DRY RUN] Skipping Blogger API call.")
        logger.info(f"[DRY RUN] Title: {article.title}")
        logger.info(f"[DRY RUN] HTML preview (first 300 chars):\n{html_content[:300]}")

        result = PostResult(
            success=True,
            topic_id=topic.topic_id,
            title=article.title,
            dry_run=True,
            draft_mode=config.DRAFT_MODE,
            blogger_post_id="dry-run-id",
            blogger_post_url="https://dry-run.example.com",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        _save_post_log(result)
        return result

    # ── Step 6: Publish to Blogger ────────────────────────────────────────
    logger.info(f"Publishing to Blogger: '{article.title}'")
    success, post_id, post_url = publish_post(
        title=article.title,
        html_content=html_content,
        labels=article.tags,
        is_draft=config.DRAFT_MODE,
    )

    timestamp = datetime.now(timezone.utc).isoformat()

    if success:
        # ── Step 7a: Mark posted ─────────────────────────────────────────
        mark_topic_posted(
            topics,
            topic_id=topic.topic_id,
            blogger_post_id=post_id or "",
            blogger_post_url=post_url or "",
            posted_at=timestamp,
        )
        result = PostResult(
            success=True,
            topic_id=topic.topic_id,
            title=article.title,
            draft_mode=config.DRAFT_MODE,
            blogger_post_id=post_id,
            blogger_post_url=post_url,
            timestamp=timestamp,
        )
        logger.info(f"Pipeline complete. Post live at: {post_url}")
    else:
        # ── Step 7b: Mark failed — do NOT mark as posted ─────────────────
        mark_topic_failed(topics, topic.topic_id)
        result = PostResult(
            success=False,
            topic_id=topic.topic_id,
            title=article.title,
            error_message="Blogger API publish failed after all retries.",
            timestamp=timestamp,
        )
        logger.error(f"Pipeline failed for topic {topic.topic_id}.")

    # ── Step 8: Save log ──────────────────────────────────────────────────
    _save_post_log(result)

    return result
