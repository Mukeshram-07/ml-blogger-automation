"""
topic_loader.py
---------------
Responsible for:
- Loading topics from topics.json
- Picking the next pending topic
- Marking a topic as posted or failed
- Saving changes back to file
"""

import json
import os
from typing import List, Optional

from app.config import config
from app.logger import logger
from app.models import Topic, TopicStatus


def load_topics() -> List[Topic]:
    """Load all topics from the JSON file."""
    if not os.path.exists(config.TOPICS_FILE):
        logger.error(f"Topics file not found: {config.TOPICS_FILE}")
        raise FileNotFoundError(f"Topics file not found: {config.TOPICS_FILE}")

    with open(config.TOPICS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)

    topics = [Topic(**item) for item in raw]
    logger.info(f"Loaded {len(topics)} topics from {config.TOPICS_FILE}")
    return topics


def save_topics(topics: List[Topic]) -> None:
    """Persist the updated topics list back to JSON."""
    data = [topic.model_dump() for topic in topics]
    with open(config.TOPICS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    logger.debug("Topics file saved successfully.")


def get_next_pending_topic(topics: List[Topic]) -> Optional[Topic]:
    """
    Return the first topic with status=pending.
    Returns None if all topics are exhausted.
    """
    for topic in topics:
        if topic.status == TopicStatus.PENDING:
            logger.info(
                f"Next pending topic → ID: {topic.topic_id} | '{topic.title_seed}'"
            )
            return topic

    logger.warning("No pending topics found. All topics are posted or skipped.")
    return None


def mark_topic_posted(
    topics: List[Topic],
    topic_id: int,
    blogger_post_id: str,
    blogger_post_url: str,
    posted_at: str,
) -> None:
    """Update a topic's status to 'posted' and save."""
    for topic in topics:
        if topic.topic_id == topic_id:
            topic.status = TopicStatus.POSTED
            topic.blogger_post_id = blogger_post_id
            topic.blogger_post_url = blogger_post_url
            topic.posted_at = posted_at
            logger.info(f"Topic {topic_id} marked as POSTED.")
            break
    save_topics(topics)


def mark_topic_failed(topics: List[Topic], topic_id: int) -> None:
    """Update a topic's status to 'failed' and save."""
    for topic in topics:
        if topic.topic_id == topic_id:
            topic.status = TopicStatus.FAILED
            logger.warning(f"Topic {topic_id} marked as FAILED.")
            break
    save_topics(topics)


def get_stats(topics: List[Topic]) -> dict:
    """Return a summary count of topic statuses."""
    from collections import Counter
    counts = Counter(t.status for t in topics)
    return dict(counts)
