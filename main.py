"""
main.py
-------
Entry point for the ML Blogger Automation System.

Usage:
  python main.py             → Run the publish pipeline
  python main.py --dry-run   → Test without calling Blogger API
  python main.py --verify    → Check Blogger API credentials only
  python main.py --stats     → Show topic queue stats
"""

import argparse
import sys

from app.config import config
from app.logger import logger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ML Blogger Automation System — auto-publish ML/MLOps blog posts"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run pipeline without publishing (overrides .env DRY_RUN setting)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify Blogger API credentials and blog access only",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show topic queue statistics and exit",
    )
    return parser.parse_args()


def cmd_verify() -> None:
    """Verify Blogger API credentials."""
    from app.blogger_client import verify_blog_access

    logger.info("Running Blogger API credential verification...")
    if verify_blog_access():
        logger.info("✅ Credentials valid. Blog is accessible.")
        print("\n✅ Blogger API credentials are working correctly.\n")
    else:
        logger.error("❌ Credential verification failed.")
        print("\n❌ Blogger API credentials check FAILED. See logs for details.\n")
        sys.exit(1)


def cmd_stats() -> None:
    """Print topic queue statistics."""
    from app.topic_loader import load_topics, get_stats

    topics = load_topics()
    stats = get_stats(topics)
    print("\n── Topic Queue Stats ──────────────────")
    for status, count in stats.items():
        print(f"  {status:<10} : {count}")
    print(f"  {'TOTAL':<10} : {len(topics)}")
    print("───────────────────────────────────────\n")


def cmd_run(dry_run: bool = False) -> None:
    """Run the full publish pipeline."""
    from app.publisher import run_publish_pipeline

    # Allow CLI flag to override env setting
    if dry_run:
        config.DRY_RUN = True
        logger.info("DRY RUN mode activated via CLI flag.")

    result = run_publish_pipeline()

    if result is None:
        print("\nℹ️  No pending topics to publish.\n")
        sys.exit(0)

    print("\n── Publish Result ─────────────────────")
    print(f"  Success    : {result.success}")
    print(f"  Topic ID   : {result.topic_id}")
    print(f"  Title      : {result.title}")
    print(f"  Dry Run    : {result.dry_run}")
    print(f"  Draft Mode : {result.draft_mode}")

    if result.success:
        print(f"  Post URL   : {result.blogger_post_url}")
    else:
        print(f"  Error      : {result.error_message}")

    print(f"  Timestamp  : {result.timestamp}")
    print("───────────────────────────────────────\n")

    if not result.success:
        sys.exit(1)


def main() -> None:
    args = parse_args()

    if args.verify:
        cmd_verify()
    elif args.stats:
        cmd_stats()
    else:
        cmd_run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
