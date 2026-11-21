from __future__ import annotations

import hashlib
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
TESSDATA = ROOT / "data" / "processed" / "tessdata"
LOG = ROOT / "data" / "processed" / "ocr_setup.log"
LANGUAGES = ("eng", "hin", "ben", "pan", "mal")
BASE_URL = "https://github.com/tesseract-ocr/tessdata/raw/main"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"


def main() -> None:
    TESSDATA.mkdir(parents=True, exist_ok=True)
    lines = []
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    for index, language in enumerate(LANGUAGES, 1):
        destination = TESSDATA / f"{language}.traineddata"
        print(f"[{index}/{len(LANGUAGES)}] Setting up {language}", flush=True)
        try:
            if destination.is_file() and destination.stat().st_size:
                content = destination.read_bytes()
                lines.append(f"{language}: already present; bytes={len(content)}; sha256={hashlib.sha256(content).hexdigest()}")
                print(f"  already present ({len(content):,} bytes)")
                continue
            response = session.get(f"{BASE_URL}/{language}.traineddata", timeout=60)
            response.raise_for_status()
            if len(response.content) < 100_000:
                raise ValueError(f"traineddata response too small: {len(response.content)} bytes")
            destination.write_bytes(response.content)
            digest = hashlib.sha256(response.content).hexdigest()
            lines.append(f"{language}: installed to {destination.relative_to(ROOT)}; bytes={len(response.content)}; sha256={digest}")
            print(f"  installed ({len(response.content):,} bytes; sha256 {digest})")
        except Exception as exc:
            message = f"{language}: FAILED {type(exc).__name__}: {exc}"
            lines.append(message)
            print(f"  {message}", flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")
    failures = sum(line.startswith(language + ": FAILED") for language in LANGUAGES for line in lines)
    print(f"Language packs completed; failures={failures}; log={LOG.relative_to(ROOT)}")
    if failures:
        print("If the approved Tesseract packs cannot be installed, the next fallback is local PaddleOCR; no cloud OCR will be used.")


if __name__ == "__main__":
    main()
