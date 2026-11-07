"""Append-only evaluation report serialization."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def write_report(report: Any, results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    path = results_dir / f"evaluation-{timestamp}-{secrets.token_hex(4)}.json"
    payload = asdict(report)
    payload["report_path"] = str(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n")
    return path


def list_reports(results_dir: Path) -> list[Path]:
    return sorted(results_dir.glob("evaluation-*.json"))
