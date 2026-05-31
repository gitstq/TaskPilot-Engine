"""
Tests for TaskPilot-CLI DAG scheduler.
"""

import asyncio
import unittest

from taskpilot.core.models import (
    Pipeline,
    Step,
    StepType,
    TaskStatus,
)
from taskpilot.engine.scheduler import DAGScheduler


def create_test_pipeline() -> Pipeline:
    """Create a simple test pipeline."""
    return Pipeline(
        name="test-pipeline",
        steps=[
            Step(
                name="step-1",
                step_type=StepType.SHELL_COMMAND,
                config={"command": "echo 'step 1 done'"},
            ),
            Step(
                name="step-2",
                step_type=StepType.SHELL_COMMAND,
                depends_on=["step-1"],
                config={"command": "echo 'step 2 done'"},
            ),
            Step(
                name="step-3",
                step_type=StepType.SHELL_COMMAND,
                depends_on=["step-1"],
                config={"command": "echo 'step 3 done'"},
            ),
            Step(
                name="step-4",
                step_type=StepType.TRANSFORM,
                depends_on=["step-2", "step-3"],
                config={"transform": "identity"},
            ),
        ],
    )


class TestDAGScheduler(unittest.TestCase):
    """Test DAG scheduler."""

    def test_execution_order(self):
        """Test that steps execute in correct dependency order."""
        pipeline = create_test_pipeline()
        scheduler = DAGScheduler(pipeline, max_parallel=1)
        layers = scheduler._get_execution_order()

        # Layer 0: step-1 (no deps)
        # Layer 1: step-2, step-3 (depend on step-1)
        # Layer 2: step-4 (depends on step-2, step-3)
        self.assertEqual(len(layers), 3)
        self.assertIn("step-1", layers[0])
        self.assertIn("step-2", layers[1])
        self.assertIn("step-3", layers[1])
        self.assertIn("step-4", layers[2])

    def test_parallel_execution(self):
        """Test parallel step execution."""
        pipeline = create_test_pipeline()
        scheduler = DAGScheduler(pipeline, max_parallel=4)

        async def run():
            result = await scheduler.execute()
            return result

        result = asyncio.run(run())
        self.assertEqual(result.status, TaskStatus.SUCCESS)
        self.assertEqual(len(result.step_results), 4)
        self.assertEqual(result.success_count, 4)

    def test_failed_step_skips_dependents(self):
        """Test that failed steps cause dependents to be skipped."""
        pipeline = Pipeline(
            name="fail-test",
            steps=[
                Step(
                    name="fail-step",
                    step_type=StepType.SHELL_COMMAND,
                    config={"command": "exit 1"},
                ),
                Step(
                    name="dependent-step",
                    step_type=StepType.SHELL_COMMAND,
                    depends_on=["fail-step"],
                    config={"command": "echo 'should not run'"},
                ),
            ],
        )

        scheduler = DAGScheduler(pipeline, max_parallel=1)

        async def run():
            return await scheduler.execute()

        result = asyncio.run(run())
        self.assertEqual(result.status, TaskStatus.FAILED)
        # The dependent step should be skipped
        dependent = next(
            (r for r in result.step_results if r.step_name == "dependent-step"),
            None,
        )
        self.assertIsNotNone(dependent)
        self.assertEqual(dependent.status, TaskStatus.SKIPPED)

    def test_retry_logic(self):
        """Test step retry on failure."""
        pipeline = Pipeline(
            name="retry-test",
            steps=[
                Step(
                    name="retry-step",
                    step_type=StepType.SHELL_COMMAND,
                    config={"command": "exit 1"},
                    retry_count=2,
                    retry_delay=0.1,
                ),
            ],
        )

        scheduler = DAGScheduler(pipeline, max_parallel=1)

        async def run():
            return await scheduler.execute()

        result = asyncio.run(run())
        retry_result = result.step_results[0]
        self.assertEqual(retry_result.status, TaskStatus.FAILED)
        self.assertEqual(retry_result.retry_count, 2)

    def test_cancel_execution(self):
        """Test pipeline cancellation."""
        pipeline = Pipeline(
            name="cancel-test",
            steps=[
                Step(
                    name="slow-step",
                    step_type=StepType.SHELL_COMMAND,
                    config={"command": "sleep 10"},
                    timeout=0.5,
                ),
            ],
        )

        scheduler = DAGScheduler(pipeline, max_parallel=1)

        async def run():
            scheduler.cancel()
            return await scheduler.execute()

        result = asyncio.run(run())
        self.assertEqual(result.status, TaskStatus.CANCELLED)

    def test_empty_pipeline(self):
        """Test execution of empty pipeline."""
        pipeline = Pipeline(name="empty")
        scheduler = DAGScheduler(pipeline)

        async def run():
            return await scheduler.execute()

        result = asyncio.run(run())
        self.assertEqual(result.status, TaskStatus.SUCCESS)
        self.assertEqual(len(result.step_results), 0)

    def test_transform_step(self):
        """Test transform step execution."""
        pipeline = Pipeline(
            name="transform-test",
            steps=[
                Step(
                    name="identity-transform",
                    step_type=StepType.TRANSFORM,
                    config={"transform": "identity"},
                    inputs={"key": "value"},
                ),
            ],
        )

        scheduler = DAGScheduler(pipeline)

        async def run():
            return await scheduler.execute()

        result = asyncio.run(run())
        self.assertEqual(result.status, TaskStatus.SUCCESS)
        self.assertEqual(result.step_results[0].output, {"key": "value"})


if __name__ == "__main__":
    unittest.main()
