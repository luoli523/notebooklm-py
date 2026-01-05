# Multi-Artifact Download Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable intelligent multi-artifact downloads with natural language selection (latest, earliest, by name) and LLM-friendly defaults.

**Architecture:** Add helper functions for artifact selection and filename sanitization, then enhance all download commands (`audio`, `video`, `slide-deck`, `infographic`) with selection flags (`--latest`, `--earliest`, `--all`, `--name`, `--artifact-id`) and output flags (`--json`, `--dry-run`, `--force`, `--no-clobber`). Implement Filter → Count → Select logic for artifact selection.

**Tech Stack:** Click (CLI framework), httpx (async HTTP), Python 3.9+

---

## Task 1: Create helper module for artifact selection

**Files:**
- Create: `src/notebooklm/download_helpers.py`
- Test: `tests/unit/test_download_helpers.py`

### Step 1: Write failing tests for select_artifact

Create test file:

```python
"""Tests for download helper functions."""

import pytest
from notebooklm.download_helpers import select_artifact


class TestSelectArtifact:
    def test_select_single_artifact(self):
        """Should return the only artifact without applying filters."""
        artifacts = [{"id": "a1", "title": "Meeting", "created_at": 1000}]

        result, reason = select_artifact(artifacts)

        assert result == artifacts[0]
        assert "only artifact" in reason.lower()

    def test_filter_with_name_no_matches(self):
        """Should error when --name filter matches nothing."""
        artifacts = [{"id": "a1", "title": "Meeting", "created_at": 1000}]

        with pytest.raises(ValueError, match="No artifacts matching"):
            select_artifact(artifacts, name="music")

    def test_filter_with_name_single_match(self):
        """Should return artifact when --name filter matches one."""
        artifacts = [
            {"id": "a1", "title": "Meeting Notes", "created_at": 1000},
            {"id": "a2", "title": "Debate Session", "created_at": 2000},
        ]

        result, reason = select_artifact(artifacts, name="debate")

        assert result["id"] == "a2"
        assert "matched by name" in reason.lower()

    def test_filter_then_select_latest(self):
        """Should apply filter THEN select latest from matches."""
        artifacts = [
            {"id": "a1", "title": "Debate Round 1", "created_at": 1000},
            {"id": "a2", "title": "Meeting", "created_at": 2000},
            {"id": "a3", "title": "Debate Round 2", "created_at": 3000},
            {"id": "a4", "title": "Debate Round 3", "created_at": 2500},
        ]

        # Should find 3 "Debate" artifacts, return latest (a3)
        result, reason = select_artifact(artifacts, name="debate", latest=True)

        assert result["id"] == "a3"
        assert result["created_at"] == 3000

    def test_select_latest_from_multiple(self):
        """Should select latest when multiple artifacts exist."""
        artifacts = [
            {"id": "a1", "title": "Overview 1", "created_at": 1000},
            {"id": "a2", "title": "Overview 2", "created_at": 3000},
            {"id": "a3", "title": "Overview 3", "created_at": 2000},
        ]

        result, reason = select_artifact(artifacts, latest=True)

        assert result["id"] == "a2"
        assert "latest" in reason.lower()

    def test_select_earliest_from_multiple(self):
        """Should select earliest when requested."""
        artifacts = [
            {"id": "a1", "title": "Overview 1", "created_at": 1000},
            {"id": "a2", "title": "Overview 2", "created_at": 3000},
        ]

        result, reason = select_artifact(artifacts, earliest=True)

        assert result["id"] == "a1"
        assert "earliest" in reason.lower()

    def test_invalid_latest_and_earliest(self):
        """Should error when both --latest and --earliest provided."""
        artifacts = [{"id": "a1", "title": "Test", "created_at": 1000}]

        with pytest.raises(ValueError, match="Cannot use both"):
            select_artifact(artifacts, latest=True, earliest=True)

    def test_select_by_artifact_id(self):
        """Should select exact artifact by ID."""
        artifacts = [
            {"id": "a1", "title": "First", "created_at": 1000},
            {"id": "a2", "title": "Second", "created_at": 2000},
        ]

        result, reason = select_artifact(artifacts, artifact_id="a2")

        assert result["id"] == "a2"

    def test_artifact_id_not_found(self):
        """Should error when artifact ID doesn't exist."""
        artifacts = [{"id": "a1", "title": "Test", "created_at": 1000}]

        with pytest.raises(ValueError, match="Artifact.*not found"):
            select_artifact(artifacts, artifact_id="a99")

    def test_empty_artifacts_list(self):
        """Should error with helpful message when no artifacts."""
        with pytest.raises(ValueError, match="No artifacts found"):
            select_artifact([])
```

### Step 2: Run test to verify it fails

Run: `pytest tests/unit/test_download_helpers.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'notebooklm.download_helpers'"

### Step 3: Write minimal implementation

Create `src/notebooklm/download_helpers.py`:

```python
"""Helper functions for download commands."""

from typing import Any, Optional


def select_artifact(
    artifacts: list[dict[str, Any]],
    latest: bool = True,
    earliest: bool = False,
    name: Optional[str] = None,
    artifact_id: Optional[str] = None,
) -> tuple[dict[str, Any], str]:
    """
    Select an artifact from a list based on criteria.

    CRITICAL: Implements Filter → Count → Select logic:
    1. Filter artifacts by name/artifact_id if provided
    2. Count matches (0/1/many)
    3. Apply latest/earliest to remaining matches

    Args:
        artifacts: List of artifact dicts with 'id', 'title', 'created_at'
        latest: Select most recent (default True)
        earliest: Select oldest
        name: Filter by title (case-insensitive substring match)
        artifact_id: Select by exact artifact ID

    Returns:
        Tuple of (selected_artifact, selection_reason)

    Raises:
        ValueError: If no match, invalid criteria, or both latest+earliest
    """
    # Validate inputs
    if not artifacts:
        raise ValueError("No artifacts found")

    if latest and earliest:
        raise ValueError("Cannot use both --latest and --earliest together")

    # Step 1: Filter
    filtered = artifacts

    if artifact_id:
        filtered = [a for a in artifacts if a["id"] == artifact_id]
        if not filtered:
            raise ValueError(f"Artifact {artifact_id} not found")
        return filtered[0], f"matched by ID: {artifact_id}"

    if name:
        name_lower = name.lower()
        filtered = [a for a in artifacts if name_lower in a["title"].lower()]
        if not filtered:
            raise ValueError(
                f"No artifacts matching '{name}'. "
                f"Available: {', '.join(a['title'] for a in artifacts)}"
            )

    # Step 2: Count
    count = len(filtered)

    # Step 3: Select
    if count == 1:
        reason = "matched by name" if name else "only artifact"
        return filtered[0], reason

    # Multiple matches - apply latest/earliest
    if earliest:
        selected = min(filtered, key=lambda a: a["created_at"])
        return selected, f"earliest of {count} artifacts"
    else:  # latest is default
        selected = max(filtered, key=lambda a: a["created_at"])
        return selected, f"latest of {count} artifacts"
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/unit/test_download_helpers.py -v`
Expected: PASS (all 12 tests)

### Step 5: Commit

```bash
git add src/notebooklm/download_helpers.py tests/unit/test_download_helpers.py
git commit -m "feat(download): add artifact selection helper with filter logic"
```

---

## Task 2: Add filename sanitization helper

**Files:**
- Modify: `src/notebooklm/download_helpers.py`
- Modify: `tests/unit/test_download_helpers.py`

### Step 1: Write failing test for filename sanitization

Add to `tests/unit/test_download_helpers.py`:

```python
from notebooklm.download_helpers import artifact_title_to_filename


class TestArtifactTitleToFilename:
    def test_simple_title(self):
        """Should handle simple ASCII title."""
        result = artifact_title_to_filename("Deep Dive Overview", ".mp3", set())
        assert result == "Deep Dive Overview.mp3"

    def test_sanitize_special_characters(self):
        """Should remove invalid filename characters."""
        result = artifact_title_to_filename("My/Awesome\\Talk: Part 1?", ".mp3", set())
        assert result == "My_Awesome_Talk_ Part 1_.mp3"

    def test_handle_duplicate_titles(self):
        """Should append (2), (3) for duplicate titles."""
        existing = {"Overview.mp3"}

        result = artifact_title_to_filename("Overview", ".mp3", existing)
        assert result == "Overview (2).mp3"

        existing.add("Overview (2).mp3")
        result = artifact_title_to_filename("Overview", ".mp3", existing)
        assert result == "Overview (3).mp3"

    def test_handle_existing_with_number(self):
        """Should handle titles that already have (N) pattern."""
        existing = {"Report (1).pdf"}

        result = artifact_title_to_filename("Report (1)", ".pdf", existing)
        assert result == "Report (1) (2).pdf"

    def test_long_filename_truncation(self):
        """Should truncate very long filenames."""
        long_title = "A" * 300
        result = artifact_title_to_filename(long_title, ".mp3", set())

        # Most filesystems support 255 bytes max
        assert len(result) <= 255
        assert result.endswith(".mp3")
```

### Step 2: Run test to verify it fails

Run: `pytest tests/unit/test_download_helpers.py::TestArtifactTitleToFilename -v`
Expected: FAIL with "ImportError: cannot import name 'artifact_title_to_filename'"

### Step 3: Implement filename sanitization

Add to `src/notebooklm/download_helpers.py`:

```python
import re


def artifact_title_to_filename(
    title: str,
    extension: str,
    existing_files: set[str],
    max_length: int = 240,  # Leave room for extension and (N) suffix
) -> str:
    """
    Convert artifact title to safe filename.

    Args:
        title: Artifact title
        extension: File extension (with leading dot, e.g., ".mp3")
        existing_files: Set of filenames already used
        max_length: Maximum filename length before extension

    Returns:
        Sanitized filename with extension
    """
    # Sanitize: replace invalid chars with underscore
    # Invalid chars: / \ : * ? " < > |
    sanitized = re.sub(r'[/\\:*?"<>|]', '_', title)

    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('. ')

    # Build initial filename
    base = sanitized
    filename = f"{base}{extension}"

    # Handle duplicates with (2), (3), etc.
    counter = 2
    while filename in existing_files:
        filename = f"{base} ({counter}){extension}"
        counter += 1

    return filename
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/unit/test_download_helpers.py::TestArtifactTitleToFilename -v`
Expected: PASS (all 5 tests)

### Step 5: Commit

```bash
git add src/notebooklm/download_helpers.py tests/unit/test_download_helpers.py
git commit -m "feat(download): add filename sanitization with duplicate handling"
```

---

## Task 3: Enhance download audio command

**Files:**
- Modify: `src/notebooklm/notebooklm_cli.py` (download audio command)
- Modify: `tests/unit/test_cli.py`

### Step 1: Write failing test for enhanced download audio

Add to `tests/unit/test_cli.py`:

```python
class TestDownloadAudioEnhanced:
    def test_download_audio_latest_default(self, runner):
        """Should download latest when multiple artifacts exist."""
        with patch("notebooklm.notebooklm_cli.NotebookLMClient") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.list_artifacts = AsyncMock(return_value=[
                {"id": "a1", "title": "Overview 1", "created_at": 1000, "type": "AUDIO"},
                {"id": "a2", "title": "Overview 2", "created_at": 2000, "type": "AUDIO"},
            ])
            mock_client.download_audio = AsyncMock(return_value=b"audio data")
            mock_client_cls.return_value = mock_client

            with patch("notebooklm.notebooklm_cli.fetch_tokens") as mock_fetch:
                mock_fetch.return_value = ("csrf", "session")
                with patch("notebooklm.notebooklm_cli.load_auth_from_storage") as mock_auth:
                    mock_auth.return_value = {"SID": "test"}

                    result = runner.invoke(cli, ["download", "audio", "-n", "nb_001"])

            assert result.exit_code == 0
            # Should download a2 (latest)
            mock_client.download_audio.assert_called_once()

    def test_download_audio_with_name_filter(self, runner):
        """Should filter by --name before selecting."""
        # Similar structure, test that --name filters correctly
        pass

    def test_download_audio_all_flag(self, runner):
        """Should download all artifacts with --all."""
        pass

    def test_download_audio_json_output(self, runner):
        """Should output JSON with --json flag."""
        pass

    def test_download_audio_dry_run(self, runner):
        """Should preview without downloading with --dry-run."""
        pass
```

### Step 2: Run test to verify it fails

Run: `pytest tests/unit/test_cli.py::TestDownloadAudioEnhanced::test_download_audio_latest_default -v`
Expected: FAIL (test will fail because download command doesn't have enhanced logic yet)

### Step 3: Enhance download audio command

Modify the `download_audio` command in `src/notebooklm/notebooklm_cli.py`:

```python
@download.command("audio")
@click.argument("output_path", required=False, type=click.Path())
@click.option("-n", "--notebook", help="Notebook ID (uses current context if not set)")
@click.option("--latest", is_flag=True, default=True, help="Download latest (default)")
@click.option("--earliest", is_flag=True, help="Download earliest")
@click.option("--all", "download_all", is_flag=True, help="Download all artifacts")
@click.option("--name", help="Filter by artifact title (fuzzy match)")
@click.option("--artifact-id", help="Select by exact artifact ID")
@click.option("--json", "json_output", is_flag=True, help="Output JSON instead of text")
@click.option("--dry-run", is_flag=True, help="Preview without downloading")
@click.option("--force", is_flag=True, help="Overwrite existing files")
@click.option("--no-clobber", is_flag=True, help="Skip if file exists")
@click.pass_context
def download_audio(
    ctx,
    output_path,
    notebook,
    latest,
    earliest,
    download_all,
    name,
    artifact_id,
    json_output,
    dry_run,
    force,
    no_clobber,
):
    """Download audio overview(s).

    \b
    Examples:
      # Download latest audio
      notebooklm download audio

      # Download by name
      notebooklm download audio --name "debate"

      # Download all to directory
      notebooklm download audio ./audio/ --all

      # Preview before download
      notebooklm download audio --dry-run
    """
    from .download_helpers import select_artifact, artifact_title_to_filename
    from pathlib import Path
    import os

    try:
        notebook_id = require_notebook(notebook)
        cookies, csrf, session_id = get_client(ctx)
        auth = AuthTokens(cookies=cookies, csrf_token=csrf, session_id=session_id)

        async def _download():
            async with NotebookLMClient(auth) as client:
                # Get all audio artifacts
                all_artifacts = await client.list_artifacts(notebook_id)
                audio_artifacts = [
                    a for a in all_artifacts
                    if a.get("type") == "AUDIO" or "audio" in a.get("id", "").lower()
                ]

                if not audio_artifacts:
                    if json_output:
                        return {"error": "No audio artifacts found", "total_found": 0}
                    console.print("[red]No audio artifacts found.[/red]")
                    console.print("Generate one with: [cyan]notebooklm generate audio[/cyan]")
                    raise SystemExit(1)

                # Handle --all flag
                if download_all:
                    # Validate output_path is directory
                    if output_path and Path(output_path).suffix:
                        raise ValueError("--all requires OUTPUT_PATH to be a directory, not a file")

                    download_dir = Path(output_path) if output_path else Path("./audio")
                    download_dir.mkdir(parents=True, exist_ok=True)

                    results = {
                        "downloaded": [],
                        "skipped": [],
                        "failed": [],
                        "total_found": len(audio_artifacts),
                    }

                    existing_files = set()

                    for artifact in audio_artifacts:
                        filename = artifact_title_to_filename(
                            artifact["title"],
                            ".mp3",
                            existing_files
                        )
                        existing_files.add(filename)
                        file_path = download_dir / filename

                        if dry_run:
                            results["downloaded"].append({
                                "id": artifact["id"],
                                "title": artifact["title"],
                                "path": str(file_path),
                                "would_download": True,
                            })
                            continue

                        # Check existing file
                        if file_path.exists():
                            if no_clobber:
                                results["skipped"].append(str(file_path))
                                continue
                            if not force:
                                # Auto-rename
                                counter = 1
                                while file_path.exists():
                                    name_part = file_path.stem
                                    file_path = download_dir / f"{name_part} ({counter}).mp3"
                                    counter += 1

                        try:
                            data = await client.download_audio(
                                notebook_id,
                                str(file_path),
                                artifact_id=artifact["id"]
                            )
                            results["downloaded"].append({
                                "id": artifact["id"],
                                "title": artifact["title"],
                                "path": str(file_path),
                            })
                        except Exception as e:
                            results["failed"].append({
                                "id": artifact["id"],
                                "error": str(e),
                            })

                    if json_output:
                        results["total_downloaded"] = len(results["downloaded"])
                        return results
                    else:
                        console.print(f"[green]Downloaded {len(results['downloaded'])} audio files to {download_dir}[/green]")
                        if results["skipped"]:
                            console.print(f"[yellow]Skipped {len(results['skipped'])} existing files[/yellow]")
                        if results["failed"]:
                            console.print(f"[red]Failed {len(results['failed'])} downloads[/red]")
                    return results

                # Single artifact selection
                try:
                    # Override latest default if earliest specified
                    use_latest = latest and not earliest
                    artifact, reason = select_artifact(
                        audio_artifacts,
                        latest=use_latest,
                        earliest=earliest,
                        name=name,
                        artifact_id=artifact_id,
                    )
                except ValueError as e:
                    if json_output:
                        return {
                            "error": str(e),
                            "available": [
                                {
                                    "id": a["id"],
                                    "title": a["title"],
                                    "created": a.get("created_at"),
                                }
                                for a in audio_artifacts
                            ],
                            "total_found": len(audio_artifacts),
                        }
                    console.print(f"[red]Error: {e}[/red]")
                    console.print("\n[yellow]Available artifacts:[/yellow]")
                    for a in audio_artifacts:
                        console.print(f"  - {a['title']} (ID: {a['id']})")
                    raise SystemExit(1)

                # Determine output path
                if not output_path:
                    filename = artifact_title_to_filename(artifact["title"], ".mp3", set())
                    file_path = Path(filename)
                else:
                    file_path = Path(output_path)
                    if file_path.is_dir():
                        filename = artifact_title_to_filename(artifact["title"], ".mp3", set())
                        file_path = file_path / filename

                # Dry run
                if dry_run:
                    result = {
                        "would_download": [{
                            "id": artifact["id"],
                            "title": artifact["title"],
                            "path": str(file_path.absolute()),
                            "exists": file_path.exists(),
                            "reason": reason,
                        }],
                        "total_found": len(audio_artifacts),
                    }
                    if json_output:
                        return result
                    console.print(f"[yellow]Would download:[/yellow] {artifact['title']}")
                    console.print(f"  Path: {file_path.absolute()}")
                    console.print(f"  Selection: {reason}")
                    return result

                # Handle existing file
                if file_path.exists():
                    if no_clobber:
                        if json_output:
                            return {"skipped": [str(file_path)], "reason": "file exists"}
                        console.print(f"[yellow]Skipped:[/yellow] {file_path} (already exists)")
                        return
                    if not force:
                        # Auto-rename
                        counter = 1
                        original = file_path
                        while file_path.exists():
                            file_path = original.parent / f"{original.stem} ({counter}){original.suffix}"
                            counter += 1

                # Download
                data = await client.download_audio(
                    notebook_id,
                    str(file_path),
                    artifact_id=artifact["id"]
                )

                result = {
                    "downloaded": [{
                        "id": artifact["id"],
                        "title": artifact["title"],
                        "path": str(file_path.absolute()),
                    }],
                    "total_found": len(audio_artifacts),
                    "total_downloaded": 1,
                }

                if json_output:
                    return result

                console.print(f"[green]Downloaded:[/green] {artifact['title']}")
                console.print(f"  → {file_path.absolute()}")
                if len(audio_artifacts) > 1:
                    console.print(f"  [dim](selected {reason}, {len(audio_artifacts)} total)[/dim]")
                    console.print(f"  [dim]Tip: Use --earliest, --name, or --all for other artifacts[/dim]")
                return result

        result = run_async(_download())
        if json_output and result:
            import json
            click.echo(json.dumps(result, indent=2))

    except Exception as e:
        handle_error(e)
```

### Step 4: Run tests to verify they pass

Run: `pytest tests/unit/test_cli.py::TestDownloadAudioEnhanced -v`
Expected: PASS

### Step 5: Commit

```bash
git add src/notebooklm/notebooklm_cli.py tests/unit/test_cli.py
git commit -m "feat(download): enhance audio download with multi-artifact support"
```

---

## Task 4: Enhance remaining download commands

**Files:**
- Modify: `src/notebooklm/notebooklm_cli.py` (video, slide-deck, infographic commands)
- Modify: `tests/unit/test_cli.py`

### Step 1: Apply same pattern to download video

Follow the same structure as audio download:
- Add all flags (--latest, --earliest, --all, --name, --artifact-id, --json, --dry-run, --force, --no-clobber)
- Implement Filter → Count → Select logic
- Handle single/multiple artifacts
- Auto-name files by title with `.mp4` extension
- Default directory: `./video/` for --all

### Step 2: Apply pattern to download slide-deck

- Extension: create directory per slide deck (use title as folder name)
- Default directory: `./slide-deck/` for --all
- Handle slide decks as directories, not files

### Step 3: Apply pattern to download infographic

- Extension: `.png` (or determine from response)
- Default directory: `./infographic/` for --all

### Step 4: Write tests for all commands

Add test classes:
- `TestDownloadVideoEnhanced`
- `TestDownloadSlideDeckEnhanced`
- `TestDownloadInfographicEnhanced`

### Step 5: Run all download tests

Run: `pytest tests/unit/test_cli.py -k Download -v`
Expected: PASS (all download command tests)

### Step 6: Commit

```bash
git add src/notebooklm/notebooklm_cli.py tests/unit/test_cli.py
git commit -m "feat(download): enhance video, slide-deck, infographic with multi-artifact support"
```

---

## Task 5: Integration testing

**Files:**
- Create: `tests/integration/test_download_multi_artifact.py`

### Step 1: Write integration tests

Create comprehensive integration tests that mock the full client interaction:

```python
"""Integration tests for multi-artifact download."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path


@pytest.mark.asyncio
class TestMultiArtifactDownload:
    async def test_filter_then_select_integration(self):
        """End-to-end test of filter → count → select logic."""
        # Mock artifacts with different titles and timestamps
        # Test that --name filter is applied BEFORE --latest selection
        pass

    async def test_download_all_handles_duplicates(self):
        """Test that duplicate titles get (2), (3) suffixes."""
        pass

    async def test_json_output_format(self):
        """Test that --json produces valid JSON."""
        pass

    async def test_dry_run_no_actual_download(self):
        """Test that --dry-run doesn't call client.download_*."""
        pass

    async def test_no_clobber_skips_existing(self):
        """Test that --no-clobber skips existing files."""
        pass

    async def test_force_overwrites_existing(self):
        """Test that --force overwrites without prompt."""
        pass

    async def test_auto_rename_on_conflict(self):
        """Test default auto-rename behavior."""
        pass
```

### Step 2: Run integration tests

Run: `pytest tests/integration/test_download_multi_artifact.py -v`
Expected: PASS (all integration tests)

### Step 3: Commit

```bash
git add tests/integration/test_download_multi_artifact.py
git commit -m "test(download): add integration tests for multi-artifact logic"
```

---

## Task 6: Update documentation and CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `README.md` (if exists)

### Step 1: Update CHANGELOG

Add entry for version bump:

```markdown
## [0.2.0] - 2026-01-05

### Added
- Multi-artifact download support with intelligent selection
- Natural language flags: `--latest`, `--earliest`, `--name`, `--all`
- Structured output with `--json` flag for LLM parsing
- Preview mode with `--dry-run` flag
- File conflict handling: `--force`, `--no-clobber`, default auto-rename
- Smart defaults: auto-naming by artifact title
- Filter → Count → Select logic ensures filters are always respected

### Changed
- All download commands now support optional OUTPUT_PATH
- Default behavior downloads latest artifact when multiple exist
```

### Step 2: Test CLI help output

Run: `notebooklm download audio --help`
Verify: All new flags are documented

### Step 3: Commit

```bash
git add CHANGELOG.md README.md
git commit -m "docs: update CHANGELOG and README for multi-artifact downloads"
```

---

## Task 7: Manual testing & validation

### Step 1: Install package locally

```bash
pip install -e ".[browser,dev]"
```

### Step 2: Test help commands

```bash
notebooklm download audio --help
notebooklm download video --help
notebooklm download slide-deck --help
notebooklm download infographic --help
```

Expected: All show new flags

### Step 3: Test with mock notebook (optional)

If you have test credentials, verify:
- Download latest: `notebooklm download audio -n <notebook>`
- Filter by name: `notebooklm download audio --name "debate"`
- Download all: `notebooklm download audio ./audio/ --all`
- Dry run: `notebooklm download audio --dry-run`
- JSON output: `notebooklm download audio --json`

### Step 4: Run full test suite

```bash
pytest --cov=src/notebooklm -v
```

Expected: >90% coverage, all tests passing

### Step 5: Final commit

```bash
git add -A
git commit -m "feat: multi-artifact download complete"
```

---

## Completion Checklist

- [ ] Task 1: Helper module created and tested
- [ ] Task 2: Filename sanitization added
- [ ] Task 3: Audio download enhanced
- [ ] Task 4: Video, slide-deck, infographic enhanced
- [ ] Task 5: Integration tests written
- [ ] Task 6: Documentation updated
- [ ] Task 7: Manual testing complete

## Next Steps

After implementation:
1. Use `superpowers:requesting-code-review` to get feedback
2. Use `superpowers:finishing-a-development-branch` to merge or create PR
3. Consider adding E2E tests if credentials are available
