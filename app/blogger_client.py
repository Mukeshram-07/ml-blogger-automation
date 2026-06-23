"""
blogger_client.py
-----------------
Handles all communication with the Blogger API v3.

Authentication: OAuth2 using a refresh token (long-lived, no browser needed).
This is the right approach for server-side / CI automation.

How to get credentials:
  See README.md → "Setting Up Blogger API Credentials"
"""

import time
from typing import Optional, Tuple

import requests

from app.config import config
from app.logger import logger


# ── OAuth2 token management ────────────────────────────────────────────────────

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
BLOGGER_API_BASE = "https://www.googleapis.com/blogger/v3"


def _get_access_token() -> str:
    """
    Exchange the refresh token for a short-lived access token.
    This runs before each API call so we never deal with token expiry.
    """
    payload = {
        "client_id": config.GOOGLE_CLIENT_ID,
        "client_secret": config.GOOGLE_CLIENT_SECRET,
        "refresh_token": config.GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }

    response = requests.post(GOOGLE_TOKEN_URL, data=payload, timeout=15)

    if response.status_code != 200:
        logger.error(
            f"Failed to get access token. Status: {response.status_code} | {response.text}"
        )
        raise ValueError(
            f"OAuth2 token refresh failed: {response.status_code} — {response.text}"
        )

    token_data = response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise ValueError("access_token missing from OAuth2 response.")

    logger.debug("Access token refreshed successfully.")
    return access_token


# ── Post creation ──────────────────────────────────────────────────────────────

def publish_post(
    title: str,
    html_content: str,
    labels: list,
    is_draft: bool = False,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Publish a post to Blogger.

    Args:
        title:        Post title
        html_content: Blogger-compatible HTML body
        labels:       List of tag strings (Blogger labels)
        is_draft:     If True, saves as draft instead of publishing live

    Returns:
        Tuple of (success: bool, post_id: str | None, post_url: str | None)
    """
    access_token = _get_access_token()

    url = f"{BLOGGER_API_BASE}/blogs/{config.BLOGGER_BLOG_ID}/posts/"
    if is_draft:
        url += "?isDraft=true"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    body = {
        "kind": "blogger#post",
        "title": title,
        "content": html_content,
        "labels": labels,
    }

    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            logger.info(
                f"Blogger API call — attempt {attempt}/{config.MAX_RETRIES} "
                f"| draft={is_draft} | title='{title}'"
            )
            response = requests.post(url, headers=headers, json=body, timeout=30)

            if response.status_code in (200, 201):
                data = response.json()
                post_id = data.get("id")
                post_url = data.get("url")
                logger.info(f"Post published successfully. ID: {post_id} | URL: {post_url}")
                return True, post_id, post_url

            elif response.status_code == 429:
                # Rate limited — wait longer before retry
                wait = config.RETRY_DELAY_SECONDS * attempt * 2
                logger.warning(f"Rate limited by Blogger API. Waiting {wait}s before retry.")
                time.sleep(wait)

            elif response.status_code in (401, 403):
                logger.error(
                    f"Auth error from Blogger API: {response.status_code} | {response.text}"
                )
                return False, None, None

            else:
                logger.warning(
                    f"Blogger API returned {response.status_code}: {response.text}"
                )
                time.sleep(config.RETRY_DELAY_SECONDS)

        except requests.exceptions.Timeout:
            logger.warning(f"Request timed out on attempt {attempt}. Retrying...")
            time.sleep(config.RETRY_DELAY_SECONDS)

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            time.sleep(config.RETRY_DELAY_SECONDS)

    logger.error(f"All {config.MAX_RETRIES} attempts failed for post '{title}'.")
    return False, None, None


def verify_blog_access() -> bool:
    """
    Quick connectivity check — verifies credentials are valid
    and the blog ID exists. Useful for local testing.
    """
    try:
        access_token = _get_access_token()
        url = f"{BLOGGER_API_BASE}/blogs/{config.BLOGGER_BLOG_ID}"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            blog_name = response.json().get("name", "unknown")
            logger.info(f"Blog access verified. Blog name: '{blog_name}'")
            return True
        else:
            logger.error(
                f"Blog access check failed: {response.status_code} | {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"Blog access verification error: {e}")
        return False
