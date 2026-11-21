"""scripts/run_all_offline_tests.py

Runs all offline verification test suites in sequential order:
  1. scripts/test_5a_numbers.py
  2. scripts/test_5b_translate.py
  3. scripts/test_7b1_web.py
  4. scripts/test_7b2_web.py
  5. scripts/test_7b3_web.py
  6. scripts/test_7b4_web.py

Makes ZERO Gemini API calls. Never prints environment variables or API keys.
T3 build checks inside the sandbox are reported as INCONCLUSIVE.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLM_LOG_PATH = ROOT / "data" / "processed" / "llm_log.csv"

TEST_SCRIPTS = [
    "test_5a_numbers.py",
    "test_5b_translate.py",
    "test_7b1_web.py",
    "test_7b2_web.py",
    "test_7b3_web.py",
    "test_7b4_web.py",
]


def _count_llm_log_rows() -> int:
    if not LLM_LOG_PATH.is_file():
        return 0
    with LLM_LOG_PATH.open("r", encoding="utf-8", errors="ignore") as fh:
        return sum(1 for _ in fh)


def main() -> int:
    print("=" * 80)
    print("OFFLINE VERIFICATION TEST SUITE RUNNER")
    print("=" * 80)

    rows_before = _count_llm_log_rows()

    overall_success = True
    results: list[tuple[str, str, str]] = []

    sub_env = dict(os.environ)
    sub_env["PYTHONIOENCODING"] = "utf-8"

    for script_name in TEST_SCRIPTS:
        script_path = ROOT / "scripts" / script_name
        if not script_path.is_file():
            results.append((script_name, "FAIL", f"File missing at {script_path}"))
            overall_success = False
            continue

        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            env=sub_env,
        )

        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        combined = stdout + "\n" + stderr

        # Extract sub-test statuses if present (e.g. T1 PASS, T2 PASS, T3 INCONCLUSIVE)
        sub_tags: list[str] = []
        for line in stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("T1 ") or line_str.startswith("T2 ") or line_str.startswith("T3 "):
                tag = line_str.split("|")[0].strip()
                sub_tags.append(tag)

        if proc.returncode != 0:
            status = "FAIL"
            detail = f"exit_code={proc.returncode}"
            overall_success = False
        elif "INCONCLUSIVE" in combined:
            status = "INCONCLUSIVE"
            detail = ", ".join(sub_tags) if sub_tags else "contains inconclusive sub-test (sandbox build)"
        else:
            status = "PASS"
            detail = ", ".join(sub_tags) if sub_tags else "all checks passed"

        results.append((script_name, status, detail))

    print("\nTest Results:")
    for name, status, detail in results:
        print(f"  {name}: {status} ({detail})")

    rows_after = _count_llm_log_rows()
    delta = rows_after - rows_before

    print("-" * 80)
    print(f"llm_log.csv rows: {rows_before} -> {rows_after} (delta = {delta})")
    zero_api_pass = (delta == 0)

    if not zero_api_pass:
        print(f"[FAIL] Zero Gemini calls assertion failed: delta={delta} != 0")
        overall_success = False
    else:
        print("[PASS] Zero Gemini calls assertion passed: delta == 0")

    print("=" * 80)
    if overall_success:
        print("ALL OFFLINE SUITES COMPLETED (0 live Gemini calls)")
        return 0
    else:
        print("ONE OR MORE OFFLINE SUITES FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
