#!/usr/bin/env python3
"""Generic learning-oriented NotebookLM importer.

One command to:
1) create/find a notebook
2) collect URLs from sitemap
3) deduplicate language variants (prefer one canonical version)
4) filter by learning value (keep/skip path prefixes)
5) import with retry + concurrency controls
6) emit JSON report

Examples:
  python scripts/import_openclaw_docs_urls.py \
    --notebook "OpenClaw" \
    --sitemap https://docs.openclaw.ai/sitemap.xml \
    --prefer-lang en \
    --keep-prefix /start,/concepts,/gateway,/tools,/cli,/providers,/channels,/nodes,/platforms,/automation,/install,/help,/web \
    --skip-prefix /reference/templates,/experiments,/plugins \
    --max-import 220
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen

from notebooklm import NotebookLMClient

LANG_SEGMENT_RE = re.compile(r"^[a-z]{2}(?:-[A-Z]{2})?$")
DEFAULT_REPORT = "import_learning_report.json"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept": "application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
}


def parse_csv_prefixes(raw: str | None) -> list[str]:
    if not raw:
        return []
    out = []
    for p in (x.strip() for x in raw.split(",")):
        if not p:
            continue
        if not p.startswith("/"):
            p = "/" + p
        out.append(p.rstrip("/") or "/")
    return sorted(set(out), key=lambda x: (len(x), x))


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Create/import a learning-focused NotebookLM knowledge notebook from sitemap")
    ap.add_argument("--notebook", required=True, help="Notebook title")
    source_group = ap.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--sitemap", help="Sitemap XML URL")
    source_group.add_argument("--seed-url", help="Any doc URL on the target site; tool will auto-discover sitemap")
    ap.add_argument("--prefer-lang", default="en", help="Preferred language prefix (default: en)")
    ap.add_argument("--keep-prefix", default="", help="Comma-separated path prefixes to keep (e.g. /docs,/guides)")
    ap.add_argument("--skip-prefix", default="", help="Comma-separated path prefixes to skip")
    ap.add_argument("--max-import", type=int, default=200, help="Max URLs to import in one run")
    ap.add_argument("--concurrency", type=int, default=4, help="Parallel add_url workers")
    ap.add_argument("--retries", type=int, default=5, help="Retry attempts per URL")
    ap.add_argument("--report", default=DEFAULT_REPORT, help="Output report JSON path")
    ap.add_argument("--dry-run", action="store_true", help="Plan only, do not import")
    return ap.parse_args()


def extract_lang_and_tail(path: str) -> tuple[str | None, str]:
    """/zh-CN/cli/setup -> ('zh-CN', '/cli/setup')."""
    p = path.rstrip("/") or "/"
    if p == "/":
        return None, "/"
    segs = p.split("/")
    if len(segs) > 1 and LANG_SEGMENT_RE.match(segs[1]):
        tail = "/" + "/".join(segs[2:])
        return segs[1], (tail if tail != "" else "/")
    return None, p


def normalize_url(url: str) -> tuple[str, str | None, str]:
    """Return canonical URL, detected language, and path tail."""
    u = urlparse(url)
    lang, tail = extract_lang_and_tail(u.path)
    canonical = urlunparse((u.scheme or "https", u.netloc, tail, "", "", ""))
    return canonical, lang, tail


def prefer_score(lang: str | None, prefer_lang: str) -> int:
    if not lang:
        return 1
    if lang == prefer_lang:
        return 3
    if lang.split("-")[0] == prefer_lang.split("-")[0]:
        return 2
    return 0


def keep_for_learning(path_tail: str, keep_prefixes: list[str], skip_prefixes: list[str]) -> tuple[bool, str]:
    for s in skip_prefixes:
        if path_tail == s or path_tail.startswith(s + "/"):
            return False, f"skip:{s}"

    if not keep_prefixes:
        return True, "keep:all"

    for k in keep_prefixes:
        if path_tail == k or path_tail.startswith(k + "/"):
            return True, f"keep:{k}"
    return False, "skip:outside-keep-prefix"


def load_sitemap_urls(sitemap_url: str) -> list[str]:
    req = Request(sitemap_url, headers=DEFAULT_HEADERS)
    xml = urlopen(req, timeout=60).read()
    root = ET.fromstring(xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    # support both sitemapindex and urlset by collecting all <loc>
    locs = [e.text.strip() for e in root.findall('.//sm:loc', ns) if e.text and e.text.strip()]
    if not locs:
        return []

    # if it's sitemap index, recursively load nested sitemaps
    tag = root.tag.lower()
    if tag.endswith("sitemapindex"):
        out: list[str] = []
        seen = set()
        for sm in locs:
            try:
                for u in load_sitemap_urls(sm):
                    if u not in seen:
                        seen.add(u)
                        out.append(u)
            except Exception:
                continue
        return out

    return locs


def discover_sitemap_from_seed(seed_url: str) -> str:
    p = urlparse(seed_url)
    if not p.scheme or not p.netloc:
        raise ValueError(f"invalid --seed-url: {seed_url}")

    base = f"{p.scheme}://{p.netloc}"

    # 1) robots.txt hints
    robots = urljoin(base, "/robots.txt")
    try:
        txt = urlopen(Request(robots, headers=DEFAULT_HEADERS), timeout=30).read().decode("utf-8", errors="ignore")
        for line in txt.splitlines():
            if line.lower().startswith("sitemap:"):
                sm = line.split(":", 1)[1].strip()
                if sm:
                    # validate reachable
                    _ = load_sitemap_urls(sm)
                    return sm
    except Exception:
        pass

    # 2) conventional locations
    candidates = [
        urljoin(base, "/sitemap.xml"),
        urljoin(base, "/sitemap_index.xml"),
        urljoin(base, "/sitemap-index.xml"),
        urljoin(base, "/wp-sitemap.xml"),
    ]
    for sm in candidates:
        try:
            urls = load_sitemap_urls(sm)
            if urls:
                return sm
        except Exception:
            continue

    raise RuntimeError(
        f"No sitemap found from seed URL {seed_url}. Provide --sitemap explicitly or use a different seed URL."
    )


def curate_urls(urls: list[str], prefer_lang: str, keep_prefixes: list[str], skip_prefixes: list[str], max_import: int) -> tuple[list[str], Counter, dict[str, str]]:
    stats = Counter()
    reasons: dict[str, str] = {}

    # group by canonical path-tail; choose best language per group
    best_by_canonical: dict[str, tuple[int, str]] = {}
    for raw in urls:
        canonical, lang, tail = normalize_url(raw)
        score = prefer_score(lang, prefer_lang)
        prev = best_by_canonical.get(canonical)
        if prev is None or score > prev[0] or (score == prev[0] and raw < prev[1]):
            best_by_canonical[canonical] = (score, raw)

    curated: list[str] = []
    for canonical, (_score, chosen_raw) in best_by_canonical.items():
        _canon2, _lang2, tail = normalize_url(chosen_raw)
        ok, reason = keep_for_learning(tail, keep_prefixes, skip_prefixes)
        reasons[canonical] = reason
        if ok:
            curated.append(canonical)
            stats["kept"] += 1
        else:
            stats[reason] += 1

    stats["total_raw_urls"] = len(urls)
    stats["deduped_unique_canonical"] = len(best_by_canonical)
    stats["dedup_removed"] = len(urls) - len(best_by_canonical)

    curated.sort(key=lambda u: (urlparse(u).path.count("/"), urlparse(u).path))
    if len(curated) > max_import:
        stats["trimmed_for_rate_limit"] = len(curated) - max_import
        curated = curated[:max_import]

    return curated, stats, reasons


async def add_with_retry(client, notebook_id: str, url: str, retries: int):
    last_err = None
    for i in range(retries):
        try:
            await client.sources.add_url(notebook_id, url)
            return True, None
        except Exception as e:
            last_err = e
            await asyncio.sleep(min(12, 1.5 * (2 ** i)))
    return False, str(last_err)


async def run() -> int:
    args = parse_args()
    keep_prefixes = parse_csv_prefixes(args.keep_prefix)
    skip_prefixes = parse_csv_prefixes(args.skip_prefix)
    report_path = Path(args.report).expanduser().resolve()

    sitemap_url = args.sitemap or discover_sitemap_from_seed(args.seed_url)
    if args.seed_url and not args.sitemap:
        print(f"discovered sitemap: {sitemap_url}")

    raw_urls = load_sitemap_urls(sitemap_url)
    curated, stats, reasons = curate_urls(
        raw_urls,
        prefer_lang=args.prefer_lang,
        keep_prefixes=keep_prefixes,
        skip_prefixes=skip_prefixes,
        max_import=args.max_import,
    )

    print(f"raw urls: {len(raw_urls)}")
    print(f"curated urls: {len(curated)}")

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        nb = next((n for n in notebooks if n.title == args.notebook), None)
        if not nb:
            nb = await client.notebooks.create(args.notebook)
            print(f"created notebook: {nb.title} ({nb.id})")
        else:
            print(f"using notebook: {nb.title} ({nb.id})")

        existing_sources = await client.sources.list(nb.id)
        existing_canonical = {
            normalize_url(s.url)[0]
            for s in existing_sources
            if getattr(s, "url", None)
        }

        todo = [u for u in curated if u not in existing_canonical]

        print(f"existing canonical url sources: {len(existing_canonical)}")
        print(f"to import now: {len(todo)}")

        ok = 0
        failed: list[tuple[str, str]] = []

        if not args.dry_run and todo:
            sem = asyncio.Semaphore(max(1, args.concurrency))
            done = 0

            async def worker(u: str):
                nonlocal ok, done
                async with sem:
                    success, err = await add_with_retry(client, nb.id, u, retries=max(1, args.retries))
                done += 1
                if success:
                    ok += 1
                else:
                    failed.append((u, err or "unknown error"))
                if done % 20 == 0 or done == len(todo):
                    print(f"progress {done}/{len(todo)} | success={ok} fail={len(failed)}")

            await asyncio.gather(*(worker(u) for u in todo))

        report = {
            "sitemap": sitemap_url,
            "seed_url": args.seed_url,
            "notebook": args.notebook,
            "notebook_id": nb.id,
            "prefer_lang": args.prefer_lang,
            "keep_prefixes": keep_prefixes,
            "skip_prefixes": skip_prefixes,
            "raw_total": len(raw_urls),
            "curated_total": len(curated),
            "existing_canonical_urls": len(existing_canonical),
            "attempted": len(todo),
            "added_success": ok,
            "failed_count": len(failed),
            "failed": [{"url": u, "error": e} for u, e in failed],
            "filter_stats": dict(stats),
            "sample_reasons": {u: reasons.get(u, "") for u in curated[:100]},
            "dry_run": bool(args.dry_run),
        }

        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("DONE")
    print(f"added_success={ok}")
    print(f"failed={len(failed)}")
    print(f"report={report_path}")
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
