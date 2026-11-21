from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
URLS = ROOT / "data" / "raw" / "urls_extra.txt"
PDF_DIR = ROOT / "data" / "raw" / "08_indian_bank_loans"
PARSED_DIR = ROOT / "data" / "processed" / "parsed" / "indian"
LOG = ROOT / "data" / "processed" / "extra_download.log"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
OFFICIAL_DOMAINS = {
    "rbi.org.in",
    "bajajfinserv.in",
    "bajajhousingfinance.in",
    "tatacapital.com",
    "adityabirlacapital.com",
    "herofincorp.com",
    "ltfs.com",
    "iifl.com",
    "piramalfinance.com",
    "ltfinance.com",
    "muthootfinance.com",
    "manappuram.com",
    "kogta.in",
    "canarabank.com",
    "canarabank.bank.in",
    "bankofbaroda.in",
    "bankofbaroda.bank.in",
    "pnbindia.in",
    "pnb.bank.in",
    "unionbankofindia.co.in",
    "idfcfirstbank.com",
    "idfcfirst.bank.in",
    "axisbank.com",
    "axis.bank.in",
    "kotak.com",
    "kotak.bank.in",
    "federalbank.co.in",
    "federal.bank.in",
}


def log(message: str) -> None:
    print(message, flush=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(message + "\n")


def safe_name(url: str, index: int) -> str:
    basename = Path(unquote(urlparse(url).path)).name
    stem = Path(basename).stem or f"public_loan_document_{index:02d}"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")[:100]
    return f"{stem or f'public_loan_document_{index:02d}'}.pdf"


def is_official_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    return parsed.scheme == "https" and any(
        host == domain or host.endswith("." + domain)
        for domain in OFFICIAL_DOMAINS
    )


def parse_new_pdf(pdf_path: Path) -> None:
    import fitz

    name = re.sub(r"[^A-Za-z0-9._-]+", "_", pdf_path.stem)[:80] + ".json"
    output = PARSED_DIR / name
    if output.exists():
        log(f"Parsed output already exists; keeping it: {output.name}")
        return
    pages = []
    with fitz.open(pdf_path) as document:
        for page_number, page in enumerate(document, 1):
            text = page.get_text()
            letters = sum(char.isalpha() for char in text)
            needs_ocr = len(text.strip()) < 50 or letters / max(1, len(text)) < 0.5 or text.count("(cid:") > 5
            pages.append({"page": page_number, "text": text, "needs_ocr": needs_ocr})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        __import__("json").dumps({"source": str(pdf_path.relative_to(ROOT)), "pages": pages}, ensure_ascii=False),
        encoding="utf-8",
    )
    log(f"Parsed new PDF only: {output.name} ({len(pages)} pages)")


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    if not URLS.exists():
        log(f"URL list not found: {URLS}. Create it with one official PDF URL per line.")
        return
    urls = [
        line.strip()
        for line in URLS.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not urls:
        log(f"No URLs supplied yet. Add official PDF URLs to {URLS.relative_to(ROOT)} and rerun.")
        return
    existing_hashes = set()
    for path in PDF_DIR.glob("*.pdf"):
        try:
            existing_hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
        except OSError as exc:
            log(f"Could not hash {path.name}: {exc}")
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    log(f"Starting extra PDF download run: {len(urls)} URL(s).")
    for index, url in enumerate(urls, 1):
        log(f"[{index}/{len(urls)}] Downloading {url}")
        try:
            if not is_official_url(url):
                log(f"FAILED (URL is not HTTPS on an allowlisted lender/RBI domain): {url}")
                continue
            response = session.get(url, timeout=45)
            response.raise_for_status()
            content = response.content
            if not content.startswith(b"%PDF"):
                log(f"FAILED (not a PDF): {url}")
                continue
            digest = hashlib.sha256(content).hexdigest()
            if digest in existing_hashes:
                log(f"Skipped duplicate SHA-256: {url}")
                continue
            destination = PDF_DIR / safe_name(url, index)
            if destination.exists():
                destination = PDF_DIR / f"{destination.stem}_{digest[:8]}.pdf"
            destination.write_bytes(content)
            existing_hashes.add(digest)
            sources = PDF_DIR / "sources.txt"
            with sources.open("a", encoding="utf-8") as stream:
                stream.write(
                    f"{destination.name}\t{url}\t{date.today().isoformat()}\t"
                    "public loan document\tunknown\n"
                )
            log(f"Saved {destination.name} ({len(content):,} bytes)")
            try:
                parse_new_pdf(destination)
            except Exception as exc:
                log(f"PARSE FAILED for {destination.name}: {type(exc).__name__}: {exc}")
        except Exception as exc:
            log(f"FAILED: {url} ({type(exc).__name__}: {exc})")


if __name__ == "__main__":
    main()
