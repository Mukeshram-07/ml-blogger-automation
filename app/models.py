"""
models.py
---------
Pydantic data models for type-safe data handling across the system.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class TopicStatus(str, Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    SKIPPED = "skipped"


class Topic(BaseModel):
    topic_id: int
    title_seed: str
    category: str
    tags: List[str] = []
    difficulty: str = "Intermediate"
    experience_points: List[str] = []
    mistakes: List[str] = []
    lessons: List[str] = []
    optional_code_snippet_idea: Optional[str] = None
    status: TopicStatus = TopicStatus.PENDING
    posted_at: Optional[str] = None
    blogger_post_id: Optional[str] = None
    blogger_post_url: Optional[str] = None


class ArticleSection(BaseModel):
    heading: str
    content: str


class Article(BaseModel):
    title: str
    intro: str
    sections: List[ArticleSection] = []
    mistakes_section: Optional[str] = None
    lessons_section: Optional[str] = None
    conclusion: str
    tags: List[str] = []
    category: str = ""


class PostResult(BaseModel):
    success: bool
    topic_id: int
    title: str
    dry_run: bool = False
    draft_mode: bool = False
    blogger_post_id: Optional[str] = None
    blogger_post_url: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: Optional[str] = None
