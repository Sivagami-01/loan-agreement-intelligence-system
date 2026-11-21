from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import fitz
import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
PDF_DIR = ROOT / "data" / "raw" / "08_indian_bank_loans"
SOURCES_FILE = PDF_DIR / "sources.txt"
REPORT_DIR = ROOT / "data" / "processed"
CANDIDATE_REPORT = REPORT_DIR / "official_pdf_candidates.csv"
SCOPE_REPORT = REPORT_DIR / "indian_source_scope.csv"
LOG_PATH = REPORT_DIR / "official_crawl.log"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
)
DOMAINS = [
    ("RBI", "www.rbi.org.in"),
    ("Bajaj Finserv", "www.bajajfinserv.in"),
    ("Bajaj Housing Finance", "www.bajajhousingfinance.in"),
    ("Tata Capital", "www.tatacapital.com"),
    ("Aditya Birla Capital", "www.adityabirlacapital.com"),
    ("Hero FinCorp", "www.herofincorp.com"),
    ("L&T Finance", "www.ltfinance.com"),
    ("IIFL", "www.iifl.com"),
    ("Piramal Finance", "www.piramalfinance.com"),
    ("Muthoot Finance", "www.muthootfinance.com"),
    ("Manappuram", "www.manappuram.com"),
    ("Kogta", "www.kogta.in"),
    ("Canara Bank", "www.canarabank.bank.in"),
    ("Bank of Baroda", "bankofbaroda.bank.in"),
    ("Punjab National Bank", "pnb.bank.in"),
    ("Union Bank", "www.unionbankofindia.co.in"),
    ("IDFC FIRST Bank", "www.idfcfirstbank.com"),
    ("Axis Bank", "www.axis.bank.in"),
    ("Kotak", "www.kotak.bank.in"),
    ("Federal Bank", "www.federal.bank.in"),
]
OFFICIAL_HOSTS = {
    host.casefold()
    for _, root_domain in DOMAINS
    for host in (root_domain, root_domain.removeprefix("www."))
}
OFFICIAL_HOSTS.add("www.idfcfirst.bank.in")
OFFICIAL_HOSTS.add("idfcfirst.bank.in")
OFFICIAL_HOSTS.update({
    "ltfinance.com", "www.ltfinance.com",
    "canarabank.bank.in", "www.canarabank.bank.in",
    "bankofbaroda.bank.in",
    "pnb.bank.in", "www.pnb.bank.in",
    "axis.bank.in", "www.axis.bank.in",
    "kotak.bank.in", "www.kotak.bank.in",
    "federal.bank.in", "www.federal.bank.in",
})
DOC_TERMS = (
    "mitc", "most important terms", "key fact", "key-fact", "key_fact", "kfs",
    "sanction letter", "sanction-letter", "loan agreement", "loan-agreement",
    "loan application", "application form", "personal loan", "personal-loan",
    "home loan", "home-loan", "loan against", "loan-against",
    "terms and conditions",
)
PDF_TERMS = (
    "mitc", "most important terms and conditions", "key fact statement",
    "key facts statement", "kfs", "loan agreement", "sanction letter",
)
MAX_HTML_PAGES_PER_DOMAIN = 12
MAX_SUCCESSFUL_DOWNLOADS = 10
MAX_PDF_BYTES = 50 * 1024 * 1024
PARSED_DIR = ROOT / "data" / "processed" / "parsed" / "indian"
csv.field_size_limit(20_000_000)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})
log_lines: list[str] = []
report_rows: list[dict[str, str]] = []


def allowed_https(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    return parsed.scheme == "https" and any(
        host == official or host.endswith("." + official)
        for official in OFFICIAL_HOSTS
    )


def record(url: str, discovered_from: str, status: str, **values: str) -> None:
    report_rows.append({
        "url": url,
        "discovered_from": discovered_from,
        "status": status,
        "filename": values.get("filename", ""),
        "sha256": values.get("sha256", ""),
        "document_type": values.get("document_type", ""),
        "language": values.get("language", ""),
        "detail": values.get("detail", ""),
    })


def log(message: str) -> None:
    log_lines.append(message)
    print(message, flush=True)


def get(url: str, *, stream: bool = False) -> requests.Response | None:
    if not allowed_https(url):
        log(f"SKIP non-allowlisted URL: {url}")
        return None
    try:
        response = session.get(url, timeout=20, stream=stream, allow_redirects=True)
        if not allowed_https(response.url):
            response.close()
            log(f"SKIP redirect outside official domains: {url} -> {response.url}")
            return None
        response.raise_for_status()
        return response
    except requests.RequestException as exc:
        log(f"REQUEST FAILED {url}: {type(exc).__name__}: {exc}")
        return None


def relevant(value: str, terms: tuple[str, ...] = DOC_TERMS) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in terms)


def relevant_page(url: str, label: str) -> bool:
    lowered = f"{url} {label}".casefold()
    excluded = (
        "customer-care", "customer care", "repayment", "payment",
        "calculator", "calculators", "faq", "blog", "career", "privacy",
        "terms-of-use", "terms_of_use", "whatsapp", "corporate",
        "investor", "annual-report", "grievance",
    )
    return not any(term in lowered for term in excluded) and relevant(lowered)


def relevant_pdf_link(value: str) -> bool:
    lowered = value.casefold()
    return any(term in lowered for term in PDF_TERMS)


def sitemap_entries(url: str) -> tuple[list[str], list[str]]:
    response = get(url)
    if response is None:
        return [], []
    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        log(f"INVALID sitemap XML {url}: {exc}")
        return [], []
    urls: list[str] = []
    child_sitemaps: list[str] = []
    is_index = root.tag.casefold().endswith("sitemapindex")
    for element in root.iter():
        if not element.tag.casefold().endswith("loc") or not element.text:
            continue
        location = element.text.strip()
        if not allowed_https(location):
            continue
        if is_index:
            child_sitemaps.append(location)
        else:
            urls.append(location)
    return urls, child_sitemaps


def page_links(url: str) -> tuple[list[tuple[str, str]], list[str]]:
    response = get(url)
    if response is None:
        return [], []
    content_type = response.headers.get("Content-Type", "").casefold()
    if "html" not in content_type and not response.text.lstrip().startswith("<"):
        return [], []
    soup = BeautifulSoup(response.text, "html.parser")
    pdfs: list[tuple[str, str]] = []
    pages: list[str] = []
    for anchor in soup.find_all("a", href=True):
        target = urljoin(response.url, str(anchor["href"]).strip())
        text = anchor.get_text(" ", strip=True)
        label = f"{text} {anchor.get('title', '')} {anchor.parent.get_text(' ', strip=True)} {target}"
        if not allowed_https(target):
            continue
        if urlparse(target).path.casefold().endswith(".pdf") and relevant_pdf_link(label):
            pdfs.append((target, response.url))
        elif relevant_page(target, label) and not urlparse(target).path.casefold().endswith(
            (".jpg", ".jpeg", ".png", ".svg", ".zip", ".doc", ".docx", ".xlsx")
        ):
            pages.append(target)
    return pdfs, pages


def existing_hashes() -> set[str]:
    hashes = set()
    for path in PDF_DIR.glob("*.pdf"):
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes.add(digest)
        except OSError as exc:
            log(f"HASH FAILED {path.name}: {type(exc).__name__}: {exc}")
    return hashes


def filename_for(lender: str, title: str, index: int) -> str:
    value = f"{lender}_{title}"
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    value = value[:90] or "public_loan_document"
    return f"{index:02d}_{value}.pdf"


def pdf_metadata(content: bytes, url: str) -> tuple[str, str, bool]:
    document_type = "out of scope"
    language = "unknown"
    eligible = False
    try:
        import io

        with fitz.open(stream=io.BytesIO(content), filetype="pdf") as document:
            metadata = document.metadata or {}
            first_page = document[0].get_text() if document.page_count else ""
        title = str(metadata.get("title", "") or "")
        filename = Path(urlparse(url).path).stem
        title_terms = f"{title} {filename}".casefold()
        opening = first_page[:1800].casefold()
        if (
            "mitc" in title_terms
            or "most important terms and conditions" in title_terms
            or "most important terms and conditions" in opening
            or re.search(r"\bmitc\b", opening)
        ):
            document_type = "MITC"
            eligible = True
        elif (
            "key fact statement" in title_terms
            or "key facts statement" in title_terms
            or "key fact statement" in opening
            or "key facts statement" in opening
        ):
            document_type = "Key Fact Statement"
            eligible = True
        elif "sanction letter" in title_terms:
            document_type = "sanction-letter format"
            eligible = True
        elif (
            "loan agreement" in title_terms
            or "loan agreement" in opening[:1200]
        ):
            document_type = "loan agreement"
            eligible = True
        if (
            eligible
            and ("credit card" in title_terms or "credit card" in opening[:1800])
            and "loan" not in title_terms
            and "loan" not in opening[:1800]
        ):
            document_type = "credit-card MITC (not a loan document)"
            eligible = False
        scripts = {
            "Devanagari": sum(0x0900 <= ord(ch) <= 0x097F for ch in first_page),
            "Bengali": sum(0x0980 <= ord(ch) <= 0x09FF for ch in first_page),
            "Gurmukhi": sum(0x0A00 <= ord(ch) <= 0x0A7F for ch in first_page),
            "Malayalam": sum(0x0D00 <= ord(ch) <= 0x0D7F for ch in first_page),
            "Latin": sum("LATIN" in unicodedata.name(ch, "") for ch in first_page),
        }
        nonzero = [name for name, count in scripts.items() if count]
        language = "English" if nonzero == ["Latin"] else (
            " / ".join(name for name in nonzero if name != "Latin") or "unknown"
        )
    except Exception as exc:
        log(f"PDF metadata/text extraction failed: {type(exc).__name__}: {exc}")
    return document_type, language, eligible


def parse_new_pdf(path: Path) -> None:
    output_name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem)[:80] + ".json"
    output = PARSED_DIR / output_name
    if output.exists():
        log(f"KEEP existing parsed JSON (not overwritten): {output.name}")
        return
    pages = []
    with fitz.open(path) as document:
        for page_number, page in enumerate(document, 1):
            text = page.get_text()
            letters = sum(char.isalpha() for char in text)
            needs_ocr = (
                len(text.strip()) < 50
                or letters / max(1, len(text)) < 0.5
                or text.count("(cid:") > 5
            )
            pages.append({
                "page": page_number,
                "text": text,
                "needs_ocr": needs_ocr,
            })
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "source": str(path.relative_to(ROOT)),
        "pages": pages,
    }, ensure_ascii=False), encoding="utf-8")
    log(f"PARSED newly downloaded PDF only: {output.name} ({len(pages)} pages)")


def download_candidate(
    url: str,
    discovered_from: str,
    lender: str,
    hashes: set[str],
    next_number: int,
) -> bool:
    response = get(url, stream=True)
    if response is None:
        record(url, discovered_from, "REQUEST_FAILED")
        return False
    try:
        length = response.headers.get("Content-Length")
        if length and int(length) > MAX_PDF_BYTES:
            record(url, discovered_from, "SKIPPED_TOO_LARGE", detail=length)
            log(f"SKIP oversized PDF ({length} bytes): {url}")
            return False
        content = bytearray()
        for chunk in response.iter_content(chunk_size=1024 * 256):
            if chunk:
                content.extend(chunk)
                if len(content) > MAX_PDF_BYTES:
                    record(url, discovered_from, "SKIPPED_TOO_LARGE", detail=str(len(content)))
                    log(f"SKIP oversized PDF (> {MAX_PDF_BYTES} bytes): {url}")
                    return False
        if not bytes(content).startswith(b"%PDF"):
            record(url, discovered_from, "NOT_PDF")
            log(f"NOT A PDF: {url}")
            return False
        digest = hashlib.sha256(content).hexdigest()
        if digest in hashes:
            record(url, discovered_from, "DUPLICATE_SHA256", sha256=digest)
            log(f"SKIP duplicate SHA-256: {url}")
            return False
        document_type, language, eligible = pdf_metadata(bytes(content), url)
        if not eligible:
            record(
                url, discovered_from, "OUT_OF_SCOPE",
                document_type=document_type, language=language,
                detail="PDF content/title is not an MITC, KFS, loan agreement, or sanction-letter format",
            )
            log(f"OUT OF SCOPE ({document_type}): {url}")
            return False
        title = Path(urlparse(url).path).stem or document_type
        filename = filename_for(lender, title, next_number)
        destination = PDF_DIR / filename
        while destination.exists():
            next_number += 1
            filename = filename_for(lender, title, next_number)
            destination = PDF_DIR / filename
        destination.write_bytes(content)
        hashes.add(digest)
        with SOURCES_FILE.open("a", encoding="utf-8") as stream:
            stream.write(
                f"{filename}\t{url}\t{date.today().isoformat()}\t"
                f"{document_type}\t{language}\n"
            )
        try:
            parse_new_pdf(destination)
        except Exception as exc:
            log(f"PARSE FAILED {filename}: {type(exc).__name__}: {exc}")
        record(
            url, discovered_from, "DOWNLOADED", filename=filename, sha256=digest,
            document_type=document_type, language=language, detail=str(len(content)),
        )
        log(f"DOWNLOADED {filename} ({len(content):,} bytes; {document_type}; {language})")
        return True
    except (OSError, requests.RequestException, ValueError) as exc:
        record(url, discovered_from, "DOWNLOAD_FAILED", detail=f"{type(exc).__name__}: {exc}")
        log(f"DOWNLOAD FAILED {url}: {type(exc).__name__}: {exc}")
        return False
    finally:
        response.close()


def write_reports() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "url", "discovered_from", "status", "filename", "sha256",
        "document_type", "language", "detail",
    ]
    with CANDIDATE_REPORT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report_rows)
    LOG_PATH.write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def write_scope_manifest() -> None:
    source_urls: dict[str, str] = {}
    if SOURCES_FILE.is_file():
        for line in SOURCES_FILE.read_text(encoding="utf-8-sig").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and not parts[1].casefold().startswith("unknown"):
                source_urls[parts[0]] = parts[1]
    fields = [
        "filename", "sha256", "source_url", "official_url",
        "in_scope_for_loan_corpus", "document_type", "language", "reason",
    ]
    rows = []
    for path in sorted(PDF_DIR.glob("*.pdf")):
        try:
            content = path.read_bytes()
            source_url = source_urls.get(path.name, "")
            document_type, language, eligible = pdf_metadata(
                content, source_url or path.name
            )
            official = not source_url or allowed_https(source_url)
            in_scope = eligible and official
            if source_url and not official:
                reason = "source URL is not on an allowlisted HTTPS lender/RBI domain"
            elif in_scope:
                reason = "document title/opening text matches a requested loan document type"
            elif source_url:
                reason = (
                    "downloaded during initial broad crawl; document does not match "
                    "MITC/KFS/loan-agreement/sanction-letter format"
                )
            else:
                reason = (
                    "pre-existing file; type could not be verified from its title/opening text"
                )
            rows.append({
                "filename": path.name,
                "sha256": hashlib.sha256(content).hexdigest(),
                "source_url": source_url,
                "official_url": official,
                "in_scope_for_loan_corpus": in_scope,
                "document_type": document_type,
                "language": language,
                "reason": reason,
            })
        except Exception as exc:
            rows.append({
                "filename": path.name,
                "source_url": source_urls.get(path.name, ""),
                "official_url": "",
                "in_scope_for_loan_corpus": False,
                "document_type": "",
                "language": "",
                "reason": f"scope check failed: {type(exc).__name__}: {exc}",
            })
            log(f"SCOPE CHECK FAILED {path.name}: {type(exc).__name__}: {exc}")
    with SCOPE_REPORT.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    log(
        f"Scope manifest: in-scope="
        f"{sum(bool(row.get('in_scope_for_loan_corpus')) for row in rows)}/{len(rows)}; "
        f"report={SCOPE_REPORT.relative_to(ROOT)}"
    )


def main() -> None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    hashes = existing_hashes()
    numeric_prefixes = []
    for path in PDF_DIR.glob("*.pdf"):
        match = re.match(r"(\d+)_", path.name)
        if match:
            numeric_prefixes.append(int(match.group(1)))
    next_number = max(numeric_prefixes, default=0) + 1
    source_urls: dict[str, str] = {}
    if SOURCES_FILE.is_file():
        for line in SOURCES_FILE.read_text(encoding="utf-8-sig").splitlines():
            fields = line.split("\t")
            if len(fields) >= 2 and not fields[1].casefold().startswith("unknown"):
                source_urls[fields[0]] = fields[1]
    already_eligible = 0
    for path in PDF_DIR.glob("*.pdf"):
        source_url = source_urls.get(path.name, "")
        if not source_url:
            continue
        try:
            _, _, eligible = pdf_metadata(path.read_bytes(), source_url)
            if eligible and allowed_https(source_url):
                already_eligible += 1
        except OSError as exc:
            log(f"COUNT SCOPE FAILED {path.name}: {type(exc).__name__}: {exc}")
    remaining_target = max(0, MAX_SUCCESSFUL_DOWNLOADS - already_eligible)
    log(
        f"Previously downloaded official in-scope PDFs={already_eligible}; "
        f"remaining target={remaining_target}."
    )
    downloaded = 0

    for domain_index, (lender, host) in enumerate(DOMAINS, 1):
        if downloaded >= remaining_target:
            break
        root = f"https://{host}/"
        print(f"[Domain {domain_index}/{len(DOMAINS)}] {lender}: {root}", flush=True)
        sitemap_urls = []
        robots = get(urljoin(root, "robots.txt"))
        if robots is not None:
            for line in robots.text.splitlines():
                if line.strip().casefold().startswith("sitemap:"):
                    sitemap_urls.append(line.split(":", 1)[1].strip())
        if not sitemap_urls:
            sitemap_urls = [urljoin(root, "sitemap.xml")]

        sitemap_pages: list[str] = []
        direct_pdfs: list[str] = []
        for sitemap_url in sitemap_urls[:3]:
            entries, child_maps = sitemap_entries(sitemap_url)
            if child_maps:
                for child in child_maps[:3]:
                    nested_entries, _ = sitemap_entries(child)
                    for entry in nested_entries:
                        if urlparse(entry).path.casefold().endswith(".pdf"):
                            direct_pdfs.append(entry)
                        elif relevant(entry):
                            sitemap_pages.append(entry)
            else:
                for entry in entries:
                    if urlparse(entry).path.casefold().endswith(".pdf"):
                        direct_pdfs.append(entry)
                    elif relevant(entry):
                        sitemap_pages.append(entry)

        home_pdfs, home_pages = page_links(root)
        pdf_links: list[tuple[str, str]] = home_pdfs + [
            (url, "official sitemap") for url in direct_pdfs if relevant(url, PDF_TERMS)
        ]
        page_queue = list(dict.fromkeys(home_pages + sitemap_pages))
        page_queue = [
            page for page in page_queue if relevant_page(page, "")
        ]
        page_queue.sort(
            key=lambda page: (
                0 if any(term in page.casefold() for term in (
                    "mitc", "key-fact", "key_fact", "kfs", "sanction",
                    "loan-agreement", "application-form",
                )) else 1,
                page,
            )
        )
        page_queue = page_queue[:MAX_HTML_PAGES_PER_DOMAIN]
        for page_index, page_url in enumerate(page_queue, 1):
            print(f"  [Page {page_index}/{len(page_queue)}] {page_url}", flush=True)
            page_pdfs, discovered_pages = page_links(page_url)
            pdf_links.extend(page_pdfs)
            for child_page in discovered_pages:
                if (
                    len(page_queue) < MAX_HTML_PAGES_PER_DOMAIN
                    and child_page not in page_queue
                    and relevant_page(child_page, "")
                ):
                    page_queue.append(child_page)
        seen_urls = set()
        for pdf_url, source_page in pdf_links:
            if pdf_url in seen_urls:
                continue
            seen_urls.add(pdf_url)
            if not allowed_https(pdf_url):
                record(pdf_url, source_page, "SKIPPED_NONOFFICIAL_HOST")
                continue
            log(f"CANDIDATE PDF linked from official page: {pdf_url}")
            if download_candidate(pdf_url, source_page, lender, hashes, next_number):
                downloaded += 1
                next_number += 1
                if downloaded >= remaining_target:
                    break

    write_scope_manifest()
    write_reports()
    log(
        f"Finished official crawl: new PDFs={downloaded}; "
        f"candidate/failure rows={len(report_rows)}."
    )
    write_reports()


if __name__ == "__main__":
    main()
