#!/usr/bin/env python3
import asyncio
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.request import urlopen

from notebooklm import NotebookLMClient

SITEMAP_URL = "https://docs.openclaw.ai/sitemap.xml"
TARGET_NOTEBOOK_TITLE = "OpenClaw"
LANG_PREFIXES = {"en", "zh", "ja", "fr", "es", "de", "ko", "pt", "ru", "id", "it", "tr", "vi", "ar", "zh-CN", "ja-JP"}

# Keep pages that are useful for learning OpenClaw concepts + practical operation.
KEEP_PREFIXES = {
    "/",
    "/start",
    "/concepts",
    "/gateway",
    "/tools",
    "/cli",
    "/providers",
    "/channels",
    "/nodes",
    "/platforms",
    "/automation",
    "/install",
    "/help",
    "/web",
}

# Skip low-value / duplicate-like sections for learning-oriented ingest.
SKIP_PREFIXES = {
    "/reference/templates",
    "/reference/test",
    "/reference/credits",
    "/reference/RELEASING",
    "/reference/AGENTS.default",
    "/experiments",
    "/plugins",  # mostly niche/community plugin docs
    "/security/formal-verification",
}

MAX_IMPORT = 220  # avoid quota bursts / rate limit
REPORT_PATH = Path(__file__).resolve().parents[1] / "openclaw_docs_import_report.json"


def canonicalize_to_english(url: str) -> str:
    """Collapse language variants to the canonical English path."""
    p = urlparse(url)
    path = p.path.rstrip("/") or "/"
    segs = path.split("/")

    # /zh-CN/cli/setup -> /cli/setup
    if len(segs) > 1 and segs[1] in LANG_PREFIXES:
        path = "/" + "/".join(segs[2:])
        if path == "/":
            path = "/"

    return urlunparse(("https", "docs.openclaw.ai", path, "", "", ""))


def keep_for_learning(path: str) -> tuple[bool, str]:
    for s in SKIP_PREFIXES:
        if path == s or path.startswith(s + "/"):
            return False, f"skip:{s}"

    if path == "/":
        return True, "keep:root"

    for k in KEEP_PREFIXES:
        if k != "/" and (path == k or path.startswith(k + "/")):
            return True, f"keep:{k}"

    return False, "skip:outside-learning-scope"


def load_curated_urls() -> tuple[list[str], dict[str, str], Counter]:
    xml = urlopen(SITEMAP_URL, timeout=60).read()
    root = ET.fromstring(xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [e.text.strip() for e in root.findall('.//sm:url/sm:loc', ns) if e.text]

    seen = set()
    kept = []
    reasons = {}
    stats = Counter()

    for raw in locs:
        c = canonicalize_to_english(raw)
        if c in seen:
            stats["dedup_language_or_duplicate"] += 1
            continue
        seen.add(c)

        path = urlparse(c).path
        ok, reason = keep_for_learning(path)
        reasons[c] = reason
        if ok:
            kept.append(c)
            stats["kept"] += 1
        else:
            stats[reason] += 1

    # stable order by path depth then lexicographic (prioritize foundational docs)
    kept.sort(key=lambda u: (urlparse(u).path.count("/"), urlparse(u).path))
    if len(kept) > MAX_IMPORT:
        stats["trimmed_for_rate_limit"] = len(kept) - MAX_IMPORT
        kept = kept[:MAX_IMPORT]

    return kept, reasons, stats


async def add_with_retry(client, notebook_id: str, url: str, retries: int = 5):
    last_err = None
    for i in range(retries):
        try:
            await client.sources.add_url(notebook_id, url)
            return True, None
        except Exception as e:
            last_err = e
            await asyncio.sleep(min(12, 1.5 * (2 ** i)))
    return False, str(last_err)


async def main():
    all_urls, reasons, stats = load_curated_urls()
    print(f"curated URLs after dedup/filter: {len(all_urls)}")

    async with await NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        target = next((n for n in notebooks if n.title == TARGET_NOTEBOOK_TITLE), None)
        if not target:
            raise RuntimeError(f"Notebook not found: {TARGET_NOTEBOOK_TITLE}")

        existing_sources = await client.sources.list(target.id)
        existing_urls = {canonicalize_to_english(s.url) for s in existing_sources if getattr(s, 'url', None)}
        todo = [u for u in all_urls if u not in existing_urls]

        print(f"notebook: {target.title} ({target.id})")
        print(f"existing URL sources (canonical): {len(existing_urls)}")
        print(f"to import now: {len(todo)}")

        semaphore = asyncio.Semaphore(4)
        completed = 0
        ok = 0
        failed = []

        async def worker(url: str):
            nonlocal completed, ok
            async with semaphore:
                success, err = await add_with_retry(client, target.id, url)
            completed += 1
            if success:
                ok += 1
            else:
                failed.append((url, err))
            if completed % 20 == 0 or completed == len(todo):
                print(f"progress {completed}/{len(todo)} | success={ok} fail={len(failed)}")

        await asyncio.gather(*(worker(u) for u in todo))

        report = {
            "sitemap": SITEMAP_URL,
            "target_notebook": TARGET_NOTEBOOK_TITLE,
            "curated_total": len(all_urls),
            "existing_canonical_urls": len(existing_urls),
            "attempted": len(todo),
            "added_success": ok,
            "failed_count": len(failed),
            "failed": [{"url": u, "error": e} for u, e in failed],
            "filter_stats": dict(stats),
            "sample_reasons": {u: reasons.get(u, "") for u in all_urls[:80]},
        }
        REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        print("DONE")
        print(f"added_success={ok}")
        print(f"failed={len(failed)}")
        print(f"report={REPORT_PATH}")

        if failed:
            for u, e in failed[:30]:
                print(f"FAILED: {u} :: {e}")


if __name__ == "__main__":
    asyncio.run(main())
