#!/usr/bin/env python3
"""Functional test runner for the MAS learning prototype.

This script executes the core API workflow step-by-step, prints progress,
and saves a JSON report listing each checked stage and its outcome.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib import error, request


class TestFailure(RuntimeError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def http_request(url: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            content_type = resp.headers.get_content_type()
            if raw and content_type == "application/json":
                try:
                    return resp.status, json.loads(raw)
                except json.JSONDecodeError:
                    return resp.status, raw
            if raw and raw.lstrip().startswith(("{", "[")):
                try:
                    return resp.status, json.loads(raw)
                except json.JSONDecodeError:
                    return resp.status, raw
            return resp.status, raw
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise TestFailure(f"HTTP {exc.code} for {url}: {body}") from exc
    except Exception as exc:
        raise TestFailure(f"Request failed for {url}: {exc}") from exc


def ensure_mapping(value: Any, name: str) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise TestFailure(f"{name} should return a JSON object.")
    return value


def ensure_non_empty(value: Any, name: str) -> str:
    if not value or not str(value).strip():
        raise TestFailure(f"{name} is empty or missing.")
    return str(value)


class FunctionalTestRunner:
    def __init__(self, base_url: str, report_file: Optional[str]) -> None:
        self.base_url = base_url.rstrip("/")
        self.report_file = Path(report_file) if report_file else None
        self.events: List[Dict[str, Any]] = []

    def _record(self, name: str, status: str, detail: str, started_at: str, elapsed_ms: int) -> None:
        self.events.append({
            "name": name,
            "status": status,
            "detail": detail,
            "started_at": started_at,
            "finished_at": now_iso(),
            "elapsed_ms": elapsed_ms,
        })

    def _step(self, name: str, action: Callable[[], None]) -> None:
        started_at = now_iso()
        started_ms = time.perf_counter()
        try:
            action()
            self._record(name, "pass", "OK", started_at, int((time.perf_counter() - started_ms) * 1000))
            print(f"[PASS] {name} ({self.events[-1]['elapsed_ms']} ms)")
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started_ms) * 1000)
            detail = f"{type(exc).__name__}: {exc}"
            self._record(name, "fail", detail, started_at, elapsed_ms)
            print(f"[FAIL] {name} ({elapsed_ms} ms) - {detail}")
            raise

    def run(self) -> Dict[str, Any]:
        payload = {
            "turn1": "I think traveling is important because it help you to know different culture.",
            "turn2": "Yesterday I go to the museum with my friend, it was very fun.",
        }

        result = {"base_url": self.base_url, "status": "passed", "steps": []}

        def health_check() -> None:
            status, body = http_request(f"{self.base_url}/health", method="GET")
            if status != 200:
                raise TestFailure(f"Expected status 200 from /health, got {status}.")
            data = ensure_mapping(body, "/health")
            if data.get("status") != "ok":
                raise TestFailure(f"Unexpected health payload: {data}")

        def root_check() -> None:
            status, _ = http_request(f"{self.base_url}/", method="GET")
            if status != 200:
                raise TestFailure(f"Expected status 200 from /, got {status}.")

        def run_pipeline() -> Dict[str, Any]:
            status, body = http_request(f"{self.base_url}/api/run-pipeline", method="POST", payload=payload)
            if status != 200:
                raise TestFailure(f"Expected status 200 from /api/run-pipeline, got {status}.")
            data = ensure_mapping(body, "/api/run-pipeline")
            ensure_mapping(data.get("student_context"), "student_context")
            diagnosis = ensure_mapping(data.get("diagnosis"), "diagnosis")
            plan = ensure_mapping(data.get("plan"), "plan")
            teacher = ensure_mapping(data.get("teacher"), "teacher")

            if diagnosis.get("level") is None:
                raise TestFailure("diagnosis.level is missing.")
            ensure_non_empty(plan.get("suggestion"), "plan.suggestion")
            ensure_non_empty(teacher.get("status"), "teacher.status")
            return data

        def plan_update(diagnosis: Dict[str, Any]) -> Dict[str, Any]:
            follow_up_payload = {
                "diagnosis": diagnosis,
                "teacher_input": "加強過去式動詞與連接詞練習。",
            }
            status, body = http_request(f"{self.base_url}/api/plan", method="POST", payload=follow_up_payload)
            if status != 200:
                raise TestFailure(f"Expected status 200 from /api/plan, got {status}.")
            data = ensure_mapping(body, "/api/plan")
            ensure_non_empty(data.get("suggestion"), "plan.suggestion")
            return data

        self._step("Health check", health_check)
        self._step("Root page check", root_check)
        pipeline_data = self._step_with_return("Run MAS pipeline", run_pipeline)
        self._step("Teacher advisory update", lambda: plan_update(pipeline_data["diagnosis"]))

        result["steps"] = self.events
        if self.report_file:
            self.report_file.parent.mkdir(parents=True, exist_ok=True)
            self.report_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def _step_with_return(self, name: str, action: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        started_at = now_iso()
        started_ms = time.perf_counter()
        try:
            output = action()
            elapsed_ms = int((time.perf_counter() - started_ms) * 1000)
            self._record(name, "pass", "OK", started_at, elapsed_ms)
            print(f"[PASS] {name} ({elapsed_ms} ms)")
            return output
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started_ms) * 1000)
            detail = f"{type(exc).__name__}: {exc}"
            self._record(name, "fail", detail, started_at, elapsed_ms)
            print(f"[FAIL] {name} ({elapsed_ms} ms) - {detail}")
            raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run functional tests against the MAS backend.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL for the running MAS backend.")
    parser.add_argument("--report", default="mas_functional_test_report.json", help="Path to save the JSON test report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runner = FunctionalTestRunner(base_url=args.base_url, report_file=args.report)
    print(f"=== MAS functional test started ===")
    print(f"Target: {args.base_url}")
    try:
        runner.run()
    except Exception as exc:
        print(f"Functional test failed: {exc}")
        return 1
    print("=== MAS functional test passed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
