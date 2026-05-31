"""
Rich TUI dashboard for TaskPilot-CLI.
Provides beautiful terminal output for pipeline execution.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        SpinnerColumn,
        TextColumn,
        TimeElapsedColumn,
    )
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree
    from rich.layout import Layout
    from rich.live import Live
    from rich.status import Status
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from ..core.models import (
    Pipeline,
    PipelineResult,
    StepResult,
    TaskStatus,
)


class Dashboard:
    """Terminal dashboard for pipeline visualization and execution monitoring."""

    # Status icons and colors
    STATUS_ICONS = {
        TaskStatus.PENDING: ("⏳", "dim"),
        TaskStatus.RUNNING: ("🔄", "yellow"),
        TaskStatus.SUCCESS: ("✅", "green"),
        TaskStatus.FAILED: ("❌", "red"),
        TaskStatus.SKIPPED: ("⏭️", "dim"),
        TaskStatus.RETRYING: ("🔁", "yellow"),
        TaskStatus.CANCELLED: ("🚫", "red"),
    }

    def __init__(self, use_rich: bool = True):
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()

    def _print(self, message: str = "", style: str = ""):
        """Print with or without Rich."""
        if self.use_rich:
            self.console.print(message, style=style)
        else:
            print(message)

    def print_banner(self) -> None:
        """Print TaskPilot-CLI banner."""
        banner = r"""
[bold cyan]
 ╔══════════════════════════════════════════════════╗
 ║                                                  ║
 ║   🚀 TaskPilot-CLI                               ║
 ║   Lightweight AI Task Orchestration Engine        ║
 ║   轻量级AI任务智能编排与执行引擎                    ║
 ║                                                  ║
 ╚══════════════════════════════════════════════════╝
[/bold cyan]
"""
        if self.use_rich:
            self.console.print(banner)
        else:
            print("=" * 50)
            print("  TaskPilot-CLI - AI Task Orchestration Engine")
            print("=" * 50)

    def print_pipeline_info(self, pipeline: Pipeline) -> None:
        """Print pipeline overview information."""
        if self.use_rich:
            table = Table(title="📋 Pipeline Overview", show_header=False)
            table.add_column("Property", style="cyan bold", width=16)
            table.add_column("Value")

            table.add_row("Name", pipeline.name)
            table.add_row("Description", pipeline.description or "N/A")
            table.add_row("Version", pipeline.version)
            table.add_row("Steps", str(len(pipeline.steps)))
            table.add_row("Max Parallel", str(pipeline.max_parallel))
            table.add_row("LLM Provider", pipeline.llm_config.provider.value)
            table.add_row("LLM Model", pipeline.llm_config.model)

            self.console.print(table)
        else:
            print(f"\n--- Pipeline: {pipeline.name} ---")
            print(f"  Description: {pipeline.description or 'N/A'}")
            print(f"  Version: {pipeline.version}")
            print(f"  Steps: {len(pipeline.steps)}")
            print(f"  Max Parallel: {pipeline.max_parallel}")
            print(f"  LLM: {pipeline.llm_config.provider.value}/{pipeline.llm_config.model}")

    def print_step_list(self, pipeline: Pipeline) -> None:
        """Print all steps in the pipeline."""
        if self.use_rich:
            tree = Tree("📦 Pipeline Steps")
            for i, step in enumerate(pipeline.steps, 1):
                deps = f" (after: {', '.join(step.depends_on)})" if step.depends_on else ""
                icon = self.STATUS_ICONS[TaskStatus.PENDING][0]
                branch = tree.add(
                    f"{icon} [{i}] {step.name}{deps}"
                )
                branch.add(Text(f"Type: {step.step_type.value}", style="dim"))
                if step.description:
                    branch.add(Text(step.description, style="dim"))
                if step.retry_count > 0:
                    branch.add(
                        Text(f"Retries: {step.retry_count}", style="yellow dim")
                    )
            self.console.print(tree)
        else:
            print(f"\nSteps ({len(pipeline.steps)}):")
            for i, step in enumerate(pipeline.steps, 1):
                deps = f" -> {', '.join(step.depends_on)}" if step.depends_on else ""
                print(f"  {i}. [{step.step_type.value}] {step.name}{deps}")

    def print_step_start(self, step_name: str) -> None:
        """Print when a step starts executing."""
        icon, color = self.STATUS_ICONS[TaskStatus.RUNNING]
        self._print(f"  {icon} Running: {step_name}", style=color)

    def print_step_success(self, step_name: str, duration: float) -> None:
        """Print when a step succeeds."""
        icon, color = self.STATUS_ICONS[TaskStatus.SUCCESS]
        self._print(f"  {icon} {step_name} completed ({duration:.2f}s)", style=color)

    def print_step_failed(self, step_name: str, error: str) -> None:
        """Print when a step fails."""
        icon, color = self.STATUS_ICONS[TaskStatus.FAILED]
        self._print(f"  {icon} {step_name} failed: {error}", style=color)

    def print_step_skipped(self, step_name: str, reason: str = "") -> None:
        """Print when a step is skipped."""
        icon, color = self.STATUS_ICONS[TaskStatus.SKIPPED]
        msg = f"  {icon} {step_name} skipped"
        if reason:
            msg += f": {reason}"
        self._print(msg, style=color)

    def print_execution_result(self, result: PipelineResult) -> None:
        """Print the final execution result."""
        if self.use_rich:
            # Summary panel
            status_icon, status_color = self.STATUS_ICONS.get(
                result.status, ("❓", "white")
            )

            summary_text = (
                f"[{status_color}]{status_icon} Pipeline: {result.pipeline_name}\n"
                f"Status: {result.status.value.upper()} | "
                f"Duration: {result.total_duration:.2f}s | "
                f"Tokens: {result.total_tokens}\n"
                f"Steps: {result.success_count}✅ "
                f"{result.failed_count}❌ "
                f"{result.skipped_count}⏭️"
            )

            panel = Panel(summary_text, title="📊 Execution Summary", border_style=status_color)
            self.console.print(panel)

            # Step results table
            if result.step_results:
                table = Table(title="📝 Step Results")
                table.add_column("#", style="dim", width=3)
                table.add_column("Step", style="cyan")
                table.add_column("Status", width=10)
                table.add_column("Duration", justify="right", width=8)
                table.add_column("Tokens", justify="right", width=7)
                table.add_column("Error", style="red", max_width=40)

                for i, sr in enumerate(result.step_results, 1):
                    icon, color = self.STATUS_ICONS.get(sr.status, ("❓", "white"))
                    table.add_row(
                        str(i),
                        sr.step_name,
                        f"{icon} {sr.status.value}",
                        f"{sr.duration:.2f}s",
                        str(sr.tokens_used),
                        sr.error or "",
                    )

                self.console.print(table)
        else:
            print(f"\n{'='*50}")
            print(f"Pipeline: {result.pipeline_name}")
            print(f"Status: {result.status.value}")
            print(f"Duration: {result.total_duration:.2f}s")
            print(f"Results: {result.success_count} success, "
                  f"{result.failed_count} failed, "
                  f"{result.skipped_count} skipped")
            print(f"{'='*50}")

            for i, sr in enumerate(result.step_results, 1):
                status_str = f"[{sr.status.value}]"
                print(f"  {i}. {sr.step_name} {status_str} ({sr.duration:.2f}s)")
                if sr.error:
                    print(f"     Error: {sr.error}")

    def print_dag_visualization(self, pipeline: Pipeline) -> None:
        """Print a simple DAG visualization of the pipeline."""
        if not pipeline.steps:
            return

        if self.use_rich:
            tree = Tree("🔀 Execution DAG")
            step_map = {s.name: s for s in pipeline.steps}

            # Find root steps (no dependencies)
            roots = [s for s in pipeline.steps if not s.depends_on]

            def add_children(parent_branch, step_name: str, visited: set):
                if step_name in visited:
                    return
                visited.add(step_name)
                step = step_map.get(step_name)
                if not step:
                    return

                children = [s for s in pipeline.steps if step_name in s.depends_on]
                for child in children:
                    child_branch = parent_branch.add(f"→ {child.name}")
                    add_children(child_branch, child.name, visited)

            visited = set()
            for root in roots:
                root_branch = tree.add(f"🚀 {root.name}")
                add_children(root_branch, root.name, visited)

            self.console.print(tree)
        else:
            print("\nExecution DAG:")
            for step in pipeline.steps:
                deps = " → " + ", ".join(step.depends_on) if step.depends_on else " (root)"
                print(f"  {step.name}{deps}")

    def print_json_result(self, result: PipelineResult) -> None:
        """Print result as formatted JSON."""
        json_str = json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
        if self.use_rich:
            from rich.syntax import Syntax
            syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
            self.console.print(syntax)
        else:
            print(json_str)

    def print_variables(self, variables: Dict[str, Any]) -> None:
        """Print pipeline variables."""
        if not variables:
            return
        if self.use_rich:
            table = Table(title="🔧 Variables", show_header=False)
            table.add_column("Name", style="cyan")
            table.add_column("Value")
            for k, v in variables.items():
                table.add_row(k, str(v))
            self.console.print(table)
        else:
            print("\nVariables:")
            for k, v in variables.items():
                print(f"  {k}: {v}")
