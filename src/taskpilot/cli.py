#!/usr/bin/env python3
"""
TaskPilot-CLI - Lightweight Terminal AI Task Orchestration & Execution Engine
轻量级终端AI任务智能编排与执行引擎

Usage:
    taskpilot run <pipeline.yaml>          Run a pipeline
    taskpilot validate <pipeline.yaml>     Validate a pipeline file
    taskpilot show <pipeline.yaml>         Show pipeline info
    taskpilot history                      Show execution history
    taskpilot init                          Create example pipeline
    taskpilot config                        Manage configuration
    taskpilot version                       Show version info
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

# Add src to path for development
src_path = str(Path(__file__).parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from taskpilot.core.models import Pipeline, PipelineResult
from taskpilot.core.parser import (
    parse_pipeline_file,
    validate_pipeline,
    PipelineParseError,
    PipelineValidationError,
)
from taskpilot.engine.scheduler import DAGScheduler
from taskpilot.ui.dashboard import Dashboard
from taskpilot.utils.helpers import (
    save_execution_history,
    list_execution_history,
    load_config,
    save_config,
    print_version,
    get_env_variable,
)


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="taskpilot",
        description="🚀 TaskPilot-CLI - Lightweight AI Task Orchestration Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--no-rich",
        action="store_true",
        help="Disable Rich TUI output (plain text mode)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--save-history",
        action="store_true",
        default=True,
        help="Save execution history (default: True)",
    )
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=None,
        help="Override max parallel step execution",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show pipeline without executing",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run a pipeline")
    run_parser.add_argument("pipeline", help="Path to pipeline YAML file")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate pipeline file")
    validate_parser.add_argument("pipeline", help="Path to pipeline YAML file")

    # Show command
    show_parser = subparsers.add_parser("show", help="Show pipeline information")
    show_parser.add_argument("pipeline", help="Path to pipeline YAML file")
    show_parser.add_argument("--dag", action="store_true", help="Show DAG visualization")

    # History command
    subparsers.add_parser("history", help="Show execution history")

    # Init command
    init_parser = subparsers.add_parser("init", help="Create example pipeline file")
    init_parser.add_argument(
        "--output", "-o",
        default="pipeline.yaml",
        help="Output file path (default: pipeline.yaml)",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument(
        "action",
        choices=["show", "set", "reset"],
        help="Config action",
    )
    config_parser.add_argument("--key", help="Config key to set")
    config_parser.add_argument("--value", help="Config value to set")

    # Version command
    subparsers.add_parser("version", help="Show version info")

    return parser


async def cmd_run(args, dashboard: Dashboard) -> int:
    """Execute the run command."""
    try:
        pipeline = parse_pipeline_file(args.pipeline)
    except PipelineParseError as e:
        dashboard._print(f"❌ Failed to parse pipeline: {e}", style="red")
        return 1

    # Validate
    errors = validate_pipeline(pipeline)
    if errors:
        dashboard._print("❌ Pipeline validation failed:", style="red")
        for err in errors:
            dashboard._print(f"  • {err}", style="red")
        return 1

    # Show pipeline info
    dashboard.print_pipeline_info(pipeline)
    dashboard.print_step_list(pipeline)

    if args.dry_run:
        dashboard._print("\n✅ Dry run complete. Pipeline is valid.", style="green")
        return 0

    dashboard._print("\n🚀 Starting pipeline execution...", style="cyan bold")

    # Override LLM config from environment
    api_key = get_env_variable("OPENAI_API_KEY") or get_env_variable("LLM_API_KEY")
    if api_key:
        pipeline.llm_config.api_key = api_key

    api_base = get_env_variable("OPENAI_API_BASE") or get_env_variable("LLM_API_BASE")
    if api_base:
        pipeline.llm_config.api_base = api_base

    # Create scheduler and execute
    scheduler = DAGScheduler(
        pipeline,
        max_parallel=args.max_parallel,
    )

    result = await scheduler.execute()

    # Print results
    dashboard.print_execution_result(result)

    if args.json:
        dashboard.print_json_result(result)

    # Save history
    if args.save_history:
        history_path = save_execution_history(
            pipeline.name, result.to_dict()
        )
        dashboard._print(f"\n📁 History saved: {history_path}", style="dim")

    return 0 if result.status.value == "success" else 1


def cmd_validate(args, dashboard: Dashboard) -> int:
    """Execute the validate command."""
    try:
        pipeline = parse_pipeline_file(args.pipeline)
    except PipelineParseError as e:
        dashboard._print(f"❌ Parse error: {e}", style="red")
        return 1

    errors = validate_pipeline(pipeline)
    if errors:
        dashboard._print("❌ Validation failed:", style="red")
        for err in errors:
            dashboard._print(f"  • {err}", style="red")
        return 1

    dashboard._print(f"✅ Pipeline '{pipeline.name}' is valid!", style="green")
    dashboard._print(f"  Steps: {len(pipeline.steps)}", style="green")
    return 0


def cmd_show(args, dashboard: Dashboard) -> int:
    """Execute the show command."""
    try:
        pipeline = parse_pipeline_file(args.pipeline)
    except PipelineParseError as e:
        dashboard._print(f"❌ Parse error: {e}", style="red")
        return 1

    dashboard.print_pipeline_info(pipeline)
    dashboard.print_step_list(pipeline)

    if args.dag:
        dashboard.print_dag_visualization(pipeline)

    return 0


def cmd_history(args, dashboard: Dashboard) -> int:
    """Execute the history command."""
    entries = list_execution_history()

    if not entries:
        dashboard._print("📭 No execution history found.", style="dim")
        return 0

    if dashboard.use_rich:
        from rich.table import Table
        table = Table(title="📜 Execution History")
        table.add_column("Pipeline", style="cyan")
        table.add_column("Status", width=10)
        table.add_column("Duration", justify="right", width=10)
        table.add_column("Timestamp", style="dim")

        for entry in entries:
            status = entry["status"]
            icon = "✅" if status == "success" else "❌" if status == "failed" else "⏳"
            table.add_row(
                entry["pipeline"],
                f"{icon} {status}",
                f"{entry['duration']:.2f}s",
                entry["timestamp"],
            )

        dashboard.console.print(table)
    else:
        for entry in entries:
            print(f"  {entry['pipeline']} [{entry['status']}] "
                  f"{entry['duration']:.2f}s @ {entry['timestamp']}")

    return 0


def cmd_init(args, dashboard: Dashboard) -> int:
    """Create an example pipeline file."""
    example_yaml = """# TaskPilot-CLI Pipeline Example
# 轻量级AI任务编排流水线示例

name: example-pipeline
description: A demo pipeline showcasing TaskPilot features
version: "1.0.0"
max_parallel: 3

# LLM Configuration
llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.7
  max_tokens: 4096

# Environment Variables
env:
  PROJECT_DIR: "./workspace"
  OUTPUT_FORMAT: "json"

# Pipeline Variables
variables:
  target_url: "https://httpbin.org/get"
  max_retries: 3

# Pipeline Steps
steps:
  # Step 1: Fetch data (no dependencies, runs first)
  - name: fetch-data
    type: http_request
    description: Fetch data from target URL
    config:
      url: "{{target_url}}"
      method: GET
      headers:
        Accept: "application/json"
    retry_count: 2
    retry_delay: 1.0
    timeout: 30.0

  # Step 2: Process with LLM (depends on fetch-data)
  - name: analyze-data
    type: llm_call
    description: Analyze fetched data with AI
    depends_on:
      - fetch-data
    config:
      system: "You are a data analysis assistant. Provide concise insights."
      prompt: "Analyze the following data and provide key insights:\\n{{fetch-data}}"

  # Step 3: Run shell command (parallel with analyze-data, depends on fetch-data)
  - name: prepare-output
    type: shell_command
    description: Prepare output directory
    depends_on:
      - fetch-data
    config:
      command: "mkdir -p {{PROJECT_DIR}}/output && echo 'Output dir ready'"

  # Step 4: Transform results (depends on analyze-data)
  - name: format-results
    type: transform
    description: Format analysis results
    depends_on:
      - analyze-data
    config:
      transform: template
      template: "Analysis complete. Status: {{analyze-data.status}}"

  # Step 5: Final summary (depends on all previous steps)
  - name: final-report
    type: transform
    description: Generate final report
    depends_on:
      - analyze-data
      - prepare-output
      - format-results
    config:
      transform: identity
"""

    output_path = Path(args.output)
    output_path.write_text(example_yaml, encoding="utf-8")
    dashboard._print(f"✅ Example pipeline created: {output_path}", style="green")
    return 0


def cmd_config(args, dashboard: Dashboard) -> int:
    """Manage configuration."""
    if args.action == "show":
        config = load_config()
        if not config:
            dashboard._print("📭 No configuration set.", style="dim")
            dashboard._print("Use: taskpilot config set --key <key> --value <value>", style="dim")
            return 0

        if dashboard.use_rich:
            from rich.table import Table
            table = Table(title="⚙️ Configuration")
            table.add_column("Key", style="cyan")
            table.add_column("Value")
            for k, v in config.items():
                # Mask sensitive values
                if "key" in k.lower() or "token" in k.lower() or "secret" in k.lower():
                    v = "***masked***"
                table.add_row(k, str(v))
            dashboard.console.print(table)
        else:
            for k, v in config.items():
                print(f"  {k}: {v}")

    elif args.action == "set":
        if not args.key or not args.value:
            dashboard._print("❌ --key and --value are required for 'set' action.", style="red")
            return 1
        config = load_config()
        config[args.key] = args.value
        save_config(config)
        dashboard._print(f"✅ Set {args.key} = {args.value}", style="green")

    elif args.action == "reset":
        from taskpilot.utils.helpers import CONFIG_FILE
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
            dashboard._print("✅ Configuration reset.", style="green")
        else:
            dashboard._print("📭 No configuration to reset.", style="dim")

    return 0


def main(argv: Optional[list] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    dashboard = Dashboard(use_rich=not args.no_rich)

    if args.command == "version":
        print_version()
        return 0

    if args.command == "run":
        return asyncio.run(cmd_run(args, dashboard))
    elif args.command == "validate":
        return cmd_validate(args, dashboard)
    elif args.command == "show":
        return cmd_show(args, dashboard)
    elif args.command == "history":
        return cmd_history(args, dashboard)
    elif args.command == "init":
        return cmd_init(args, dashboard)
    elif args.command == "config":
        return cmd_config(args, dashboard)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
