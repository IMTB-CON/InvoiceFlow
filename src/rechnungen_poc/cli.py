from __future__ import annotations

import argparse
import logging

from rechnungen_poc.config import AppConfig
from rechnungen_poc.logging import configure_logging


logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Process invoice emails from Gmail.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform all read/extraction steps without writing to Gmail, Drive, or Sheets.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    from rechnungen_poc.pipeline import run_pipeline

    config = AppConfig.load(dry_run=args.dry_run)
    configure_logging(config.log_level)

    logger.info("Application configuration loaded", extra={"dry_run": config.dry_run})
    return run_pipeline(config)
