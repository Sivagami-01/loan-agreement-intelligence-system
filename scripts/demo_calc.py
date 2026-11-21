from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.calc.extract_inputs import calculate, extract_inputs
from src.llm.gemini_client import GeminiClient


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Calculate a loan estimate using deterministic formulas.")
    parser.add_argument("question", help="Calculation request in plain language")
    parser.add_argument("doc_id", nargs="?", help="Optional ingested document ID")
    args = parser.parse_args()

    client = GeminiClient()
    extracted = extract_inputs(args.question, doc_id=args.doc_id, client=client)
    print(f"Calculation: {extracted['calculation']}")
    print(f"Inputs: {_jsonable(extracted['inputs'])}")
    if extracted["missing"]:
        print(f"Needs inputs: {', '.join(extracted['missing'])}")
        return 0
    result = calculate(extracted)
    print(f"Formula: {result['formula_name']}")
    print(f"Result: {_jsonable(result['result'])} {result.get('currency') or ''}".strip())
    print(f"Steps: {result['steps']}")
    print(f"Assumptions: {result['assumptions']}")
    print("Estimate only: your lender's schedule may differ because of rounding, day-count, fees and taxes. Not financial advice.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
