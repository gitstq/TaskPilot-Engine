"""
DAG (Directed Acyclic Graph) scheduler for pipeline execution.
Handles dependency resolution, parallel execution, and retry logic.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional, Set

from ..core.models import (
    Pipeline,
    PipelineResult,
    Step,
    StepResult,
    TaskStatus,
)


class DAGScheduler:
    """
    Schedules and executes pipeline steps respecting dependency order.
    Supports parallel execution of independent steps and retry logic.
    """

    def __init__(
        self,
        pipeline: Pipeline,
        step_executor: Optional[Callable] = None,
        max_parallel: int = 3,
    ):
        """
        Initialize the DAG scheduler.

        Args:
            pipeline: Pipeline to execute.
            step_executor: Async callable that executes a step.
            max_parallel: Maximum number of parallel step executions.
        """
        self.pipeline = pipeline
        self.step_executor = step_executor
        self.max_parallel = max_parallel or pipeline.max_parallel
        self._semaphore = asyncio.Semaphore(self.max_parallel)
        self._cancel_requested = False

    def _build_graph(self) -> Dict[str, Set[str]]:
        """Build adjacency list: step -> steps that depend on it."""
        graph: Dict[str, Set[str]] = defaultdict(set)
        for step in self.pipeline.steps:
            for dep in step.depends_on:
                graph[dep].add(step.name)
        return dict(graph)

    def _get_execution_order(self) -> List[Set[str]]:
        """
        Compute execution layers (steps that can run in parallel).
        Returns list of sets, where each set contains step names
        that can execute concurrently.
        """
        in_degree: Dict[str, int] = {}
        step_names = {s.name for s in self.pipeline.steps}

        for step in self.pipeline.steps:
            in_degree[step.name] = len(step.depends_on)

        layers: List[Set[str]] = []
        queue = deque(name for name, deg in in_degree.items() if deg == 0)

        while queue:
            layer = set()
            next_queue = deque()

            for name in queue:
                layer.add(name)

            for name in layer:
                graph = self._build_graph()
                for dependent in graph.get(name, set()):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_queue.append(dependent)

            layers.append(layer)
            queue = next_queue

        return layers

    def _evaluate_condition(
        self, condition: Optional[str], context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a step condition expression against current context.
        Supports simple expressions like: {{prev_step.status}} == "success"
        """
        if not condition:
            return True

        try:
            # Replace variable references
            expr = condition
            for key, value in context.items():
                if isinstance(value, str):
                    expr = expr.replace(f"{{{{{key}}}}}", f'"{value}"')
                else:
                    expr = expr.replace(f"{{{{{key}}}}}", str(value))

            # Safe evaluation of simple expressions
            return bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            return True  # Default to running if condition can't be evaluated

    async def _execute_step(
        self, step: Step, context: Dict[str, Any]
    ) -> StepResult:
        """Execute a single step with retry logic."""
        result = StepResult(
            step_name=step.name,
            step_id=step.id,
        )
        result.started_at = time.time()

        # Check condition
        if not self._evaluate_condition(step.condition, context):
            result.status = TaskStatus.SKIPPED
            result.finished_at = time.time()
            result.duration = result.finished_at - result.started_at
            return result

        # Check if any dependency failed
        for dep_name in step.depends_on:
            dep_result = context.get("_results", {}).get(dep_name)
            if dep_result and dep_result.status == TaskStatus.FAILED:
                result.status = TaskStatus.SKIPPED
                result.error = f"Skipped due to failed dependency: {dep_name}"
                result.finished_at = time.time()
                result.duration = result.finished_at - result.started_at
                return result

        attempts = step.retry_count + 1
        last_error: Optional[str] = None

        for attempt in range(attempts):
            if self._cancel_requested:
                result.status = TaskStatus.CANCELLED
                result.finished_at = time.time()
                result.duration = result.finished_at - result.started_at
                return result

            result.status = TaskStatus.RUNNING
            result.retry_count = attempt

            try:
                async with self._semaphore:
                    if self.step_executor:
                        output = await asyncio.wait_for(
                            self.step_executor(step, context),
                            timeout=step.timeout,
                        )
                    else:
                        output = await asyncio.wait_for(
                            self._default_executor(step, context),
                            timeout=step.timeout,
                        )

                result.output = output
                result.status = TaskStatus.SUCCESS
                result.finished_at = time.time()
                result.duration = result.finished_at - result.started_at
                return result

            except asyncio.TimeoutError:
                last_error = f"Step timed out after {step.timeout}s"
                result.status = TaskStatus.RETRYING if attempt < attempts - 1 else TaskStatus.FAILED

            except Exception as e:
                last_error = str(e)
                result.status = TaskStatus.RETRYING if attempt < attempts - 1 else TaskStatus.FAILED

            if attempt < attempts - 1:
                await asyncio.sleep(step.retry_delay)

        result.error = last_error
        result.status = TaskStatus.FAILED
        result.finished_at = time.time()
        result.duration = result.finished_at - result.started_at
        return result

    async def _default_executor(
        self, step: Step, context: Dict[str, Any]
    ) -> Any:
        """Default step executor when no custom executor is provided."""
        from ..core.parser import resolve_variables

        step_type = step.step_type.value

        if step_type == "shell_command":
            command = resolve_variables(
                step.config.get("command", ""), context
            )
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Command failed (exit {proc.returncode}): {stderr.decode()}"
                )
            return stdout.decode().strip()

        elif step_type == "http_request":
            return await self._execute_http_step(step, context)

        elif step_type == "transform":
            return self._execute_transform_step(step, context)

        elif step_type == "llm_call":
            return await self._execute_llm_step(step, context)

        else:
            return {"type": step_type, "config": step.config, "inputs": step.inputs}

    async def _execute_http_step(
        self, step: Step, context: Dict[str, Any]
    ) -> Any:
        """Execute an HTTP request step."""
        try:
            import httpx
        except ImportError:
            raise RuntimeError(
                "httpx is required for HTTP steps. "
                "Install with: pip install httpx"
            )

        from ..core.parser import resolve_variables

        url = resolve_variables(step.config.get("url", ""), context)
        method = step.config.get("method", "GET").upper()
        headers = step.config.get("headers", {})
        body = step.config.get("body")

        async with httpx.AsyncClient(timeout=step.timeout) as client:
            response = await client.request(
                method, url, headers=headers, json=body
            )

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.text,
            }

    async def _execute_llm_step(
        self, step: Step, context: Dict[str, Any]
    ) -> Any:
        """Execute an LLM call step (simulated/demo mode)."""
        from ..core.parser import resolve_variables

        prompt = resolve_variables(
            step.config.get("prompt", ""), context
        )
        system = resolve_variables(
            step.config.get("system", ""), context
        )

        # In demo mode, return a mock response
        return {
            "prompt": prompt[:200] + ("..." if len(prompt) > 200 else ""),
            "system": system[:200] if system else None,
            "response": f"[Demo Response] Processed prompt with {len(prompt)} characters. "
            f"Connect an LLM backend via --llm-config to get real AI responses.",
            "model": self.pipeline.llm_config.model,
            "provider": self.pipeline.llm_config.provider.value,
        }

    def _execute_transform_step(
        self, step: Step, context: Dict[str, Any]
    ) -> Any:
        """Execute a data transform step."""
        transform_type = step.config.get("transform", "identity")

        if transform_type == "identity":
            return step.inputs

        elif transform_type == "extract":
            source_key = step.config.get("source", "")
            field = step.config.get("field", "")
            source = context.get(source_key, {})
            if isinstance(source, dict):
                return source.get(field)
            return source

        elif transform_type == "template":
            from ..core.parser import resolve_variables
            template = step.config.get("template", "")
            return resolve_variables(template, context)

        return step.inputs

    def cancel(self) -> None:
        """Request cancellation of the pipeline execution."""
        self._cancel_requested = True

    async def execute(self) -> PipelineResult:
        """
        Execute the pipeline respecting DAG dependencies.

        Returns:
            PipelineResult with all step results.
        """
        result = PipelineResult(
            pipeline_name=self.pipeline.name,
            pipeline_id=self.pipeline.id,
        )
        result.started_at = time.time()
        result.status = TaskStatus.RUNNING

        # Build execution context
        context: Dict[str, Any] = {
            **self.pipeline.variables,
            **self.pipeline.env,
            "_results": {},
        }

        # Get execution layers
        layers = self._get_execution_order()

        try:
            for layer in layers:
                if self._cancel_requested:
                    result.status = TaskStatus.CANCELLED
                    break

                # Execute all steps in this layer concurrently
                tasks = []
                step_map = {s.name: s for s in self.pipeline.steps}

                for step_name in layer:
                    step = step_map[step_name]
                    tasks.append(self._execute_step(step, context))

                step_results = await asyncio.gather(*tasks, return_exceptions=True)

                for sr in step_results:
                    if isinstance(sr, Exception):
                        error_result = StepResult(
                            step_name="unknown",
                            step_id="error",
                            status=TaskStatus.FAILED,
                            error=str(sr),
                        )
                        result.step_results.append(error_result)
                    else:
                        result.step_results.append(sr)
                        context["_results"][sr.step_name] = sr
                        if sr.output is not None:
                            context[sr.step_name] = sr.output

                # Check if any step in this layer failed
                if any(
                    r.status == TaskStatus.FAILED
                    for r in result.step_results
                    if r.step_name in layer
                ):
                    # Continue to mark remaining steps as skipped
                    pass

        except Exception as e:
            result.error = str(e)
            result.status = TaskStatus.FAILED

        finally:
            result.finished_at = time.time()
            result.total_duration = result.finished_at - result.started_at
            result.total_tokens = sum(r.tokens_used for r in result.step_results)

            if result.status == TaskStatus.RUNNING:
                if any(r.status == TaskStatus.FAILED for r in result.step_results):
                    result.status = TaskStatus.FAILED
                else:
                    result.status = TaskStatus.SUCCESS

        return result
