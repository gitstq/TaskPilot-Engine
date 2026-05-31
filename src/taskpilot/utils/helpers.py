"""
Utility functions for TaskPilot-CLI.
Includes logging, config management, and helper functions.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


# Default config directory
CONFIG_DIR = Path.home() / ".taskpilot"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"


def ensure_config_dir() -> Path:
    """Ensure config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> Dict[str, Any]:
    """Load user configuration from file."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save user configuration to file."""
    ensure_config_dir()
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def save_execution_history(
    pipeline_name: str, result_data: Dict[str, Any]
) -> str:
    """
    Save execution result to history file.

    Args:
        pipeline_name: Name of the pipeline.
        result_data: Serialized result data.

    Returns:
        Path to the saved history file.
    """
    ensure_config_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{pipeline_name}_{timestamp}.json"
    filepath = HISTORY_DIR / filename
    filepath.write_text(
        json.dumps(result_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return str(filepath)


def list_execution_history(limit: int = 20) -> list:
    """List recent execution history entries."""
    if not HISTORY_DIR.exists():
        return []

    files = sorted(HISTORY_DIR.glob("*.json"), reverse=True)[:limit]
    entries = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            entries.append({
                "file": f.name,
                "pipeline": data.get("pipeline_name", "unknown"),
                "status": data.get("status", "unknown"),
                "duration": data.get("total_duration", 0),
                "timestamp": f.stem.split("_")[-1] if "_" in f.stem else "",
            })
        except (json.JSONDecodeError, IOError):
            continue
    return entries


def get_env_variable(name: str, default: str = "") -> str:
    """Get environment variable with TASKPILOT_ prefix support."""
    # Check TASKPILOT_ prefixed version first
    prefixed = os.environ.get(f"TASKPILOT_{name.upper()}")
    if prefixed is not None:
        return prefixed
    return os.environ.get(name, default)


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def detect_shell() -> str:
    """Detect the current shell environment."""
    shell = os.environ.get("SHELL", "")
    if "bash" in shell:
        return "bash"
    elif "zsh" in shell:
        return "zsh"
    elif "fish" in shell:
        return "fish"
    return "unknown"


def is_ci_environment() -> bool:
    """Check if running in a CI/CD environment."""
    ci_vars = [
        "CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL",
        "TRAVIS", "CIRCLECI", "BUILDKITE",
    ]
    return any(os.environ.get(v) for v in ci_vars)


def print_version() -> None:
    """Print version information."""
    from .. import __version__
    print(f"TaskPilot-CLI v{__version__}")
    print(f"Python {sys.version.split()[0]}")
    print(f"Platform: {sys.platform}")
