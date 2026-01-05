# Unified Report Command Design

## Overview

Consolidate three separate CLI commands (`briefing-doc`, `study-guide`, `blog-post`) into a single `generate report` command with format options.

## Motivation

All report types use the same underlying `generate_report()` API method with different `ReportFormat` values. Having separate CLI commands creates redundancy and makes it harder to add new report types.

## CLI Interface

```bash
# Basic usage - defaults to briefing-doc
notebooklm generate report

# Specify format
notebooklm generate report --format study-guide
notebooklm generate report --format blog-post
notebooklm generate report --format briefing-doc

# Custom report (positional arg without --format)
notebooklm generate report "Create a white paper analyzing the technical architecture"

# Add instructions to predefined format
notebooklm generate report --format study-guide "Focus on vocabulary terms"

# Standard options
notebooklm generate report --format blog-post --wait
notebooklm generate report -n <notebook-id>
```

## Argument Logic

1. `--format` defaults to `briefing-doc`
2. If positional `DESCRIPTION` provided without explicit `--format` → treat as custom format
3. If positional `DESCRIPTION` provided with `--format` → use as instructions for that format

## Available Formats

- `briefing-doc` (default)
- `study-guide`
- `blog-post`
- `custom` (explicit, same as bare string)

## Implementation

### Files to Modify

1. **`src/notebooklm/notebooklm_cli.py`**
   - Remove: `generate_briefing_doc()`, `generate_study_guide()`, `generate_blog_post()` commands
   - Add: Single `generate_report()` command with smart argument detection
   - Update generate group docstring

2. **`src/notebooklm/rpc/types.py`**
   - No changes needed

3. **`src/notebooklm/api_client.py`**
   - No changes needed
   - Keep convenience wrappers for programmatic use

### Command Implementation

```python
@generate.command("report")
@click.argument("description", default="", required=False)
@click.option("--format", "report_format",
              type=click.Choice(["briefing-doc", "study-guide", "blog-post", "custom"]),
              default="briefing-doc")
@click.option("--wait/--no-wait", default=False)
@click.option("-n", "--notebook", "notebook_id")
def generate_report_cmd(ctx, description, report_format, wait, notebook_id):
    # If description provided but format is default → custom
    if description and report_format == "briefing-doc":
        report_format = "custom"
    # ... rest of implementation
```

## Edge Cases

1. **Empty custom prompt**: `notebooklm generate report ""`
   - Treat as briefing-doc (default), not custom with empty prompt

2. **Explicit custom without prompt**: `notebooklm generate report --format custom`
   - Use default prompt: "Create a report based on the provided sources."

3. **Explicit format with description**: `notebooklm generate report --format blog-post "Make it funny"`
   - Pass description as `custom_prompt` parameter to enhance that format

## Changes Summary

**Remove (3 commands):**
- `notebooklm generate briefing-doc`
- `notebooklm generate study-guide`
- `notebooklm generate blog-post`

**Add (1 command):**
- `notebooklm generate report [DESCRIPTION] --format <type> --wait -n`

**Net result:** 2 fewer commands, cleaner interface, same functionality.

## Migration

No deprecation period - clean break since this is pre-1.0.
