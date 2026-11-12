from __future__ import annotations

import multiprocessing
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any

from ..context import ExecutionContext
from ..pipeline import ExecutionPipeline, ExecutionResult
from ..runner_port import RunnerPort
from ..spec import ExecutionSpecification
from ..stage import Stage


def _run_pipeline_in_process(spec: ExecutionSpecification, queue: multiprocessing.queues.Queue[ExecutionResult]) -> None:
    pipeline = ExecutionPipeline()
    try:
        result = pipeline.run(spec)
    except Exception as exc:  # pragma: no cover - defensive branch
        context = ExecutionContext.from_spec(spec)
        context.set_status("failed")
        context.add_log(f"runner error: {exc}")
        result = ExecutionResult(status="failure", context=context, duration_seconds=0.0, details={"runner": {"strategy": "process"}})
    queue.put(result)


class BaseRunner(RunnerPort):
    """Shared base class for execution strategies."""

    def __init__(self, pipeline: ExecutionPipeline | None = None) -> None:
        self.pipeline = pipeline or ExecutionPipeline()
        self.strategy = "local"
        self.run_count = 0
        self.error_count = 0
        self.last_duration_seconds = 0.0
        self.environment: dict[str, str] = {}

    def run(self, spec: ExecutionSpecification) -> ExecutionResult:
        self._prepare_environment(spec)
        started_at = perf_counter()
        self.run_count += 1

        try:
            result = self._execute(spec)
        except Exception as exc:  # pragma: no cover - defensive branch
            self.error_count += 1
            context = ExecutionContext.from_spec(spec)
            context.set_status("failed")
            context.add_log(f"runner error: {exc}")
            result = ExecutionResult(
                status="failure",
                context=context,
                duration_seconds=perf_counter() - started_at,
                details={"runner": self._runner_details()},
            )

        self.last_duration_seconds = result.duration_seconds
        if result.context.status == "failed" and result.status != "failure":
            self.error_count += 1
        result.details = self._merge_details(result.details, result.duration_seconds)
        result.context.add_metric("runner_strategy", 1.0)
        result.context.add_metric("runner_runs", float(self.run_count))
        result.context.add_metric("runner_errors", float(self.error_count))
        result.context.add_metric("runner_duration_seconds", float(result.duration_seconds))
        return result

    def _prepare_environment(self, spec: ExecutionSpecification) -> None:
        self.environment = dict(spec.environment)

    def _execute(self, spec: ExecutionSpecification) -> ExecutionResult:
        return self.pipeline.run(spec)

    def _merge_details(self, details: dict[str, Any], duration_seconds: float) -> dict[str, Any]:
        merged = dict(details)
        merged["runner"] = self._runner_details(duration_seconds=duration_seconds)
        merged["metrics"] = {
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_duration_seconds": self.last_duration_seconds,
        }
        return merged

    def _runner_details(self, duration_seconds: float | None = None) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "run_count": self.run_count,
            "error_count": self.error_count,
            "last_duration_seconds": duration_seconds if duration_seconds is not None else self.last_duration_seconds,
        }


class LocalRunner(BaseRunner):
    """Simple local execution strategy."""

    def __init__(self, pipeline: ExecutionPipeline | None = None) -> None:
        super().__init__(pipeline=pipeline)
        self.strategy = "local"


class ThreadRunner(BaseRunner):
    """Executes the pipeline in a dedicated thread."""

    def __init__(self, pipeline: ExecutionPipeline | None = None) -> None:
        super().__init__(pipeline=pipeline)
        self.strategy = "thread"

    def _execute(self, spec: ExecutionSpecification) -> ExecutionResult:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.pipeline.run, spec)
            return future.result()


class ProcessRunner(BaseRunner):
    """Executes the pipeline in a child process for better isolation."""

    def __init__(self, pipeline: ExecutionPipeline | None = None) -> None:
        super().__init__(pipeline=pipeline)
        self.strategy = "process"

    def _execute(self, spec: ExecutionSpecification) -> ExecutionResult:
        context = multiprocessing.get_context("spawn")
        queue: multiprocessing.queues.Queue[ExecutionResult] = context.Queue()
        process = context.Process(target=_run_pipeline_in_process, args=(spec, queue))
        process.start()
        process.join()

        if process.exitcode != 0:
            raise RuntimeError(f"process runner exited with code {process.exitcode}")

        return queue.get()
