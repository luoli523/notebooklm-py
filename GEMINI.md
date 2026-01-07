# GEMINI.md

**IMPORTANT:** Follow documentation rules in [CONTRIBUTING.md](CONTRIBUTING.md) - especially the file creation and naming conventions.

Guidelines for Gemini when working on `notebooklm-client`.

## Quick Reference

See [CLAUDE.md](CLAUDE.md) for full project context including:
- Architecture overview (three-layer design)
- Key files and their purposes
- Testing strategy and E2E test status
- Common pitfalls

## Essential Commands

```bash
# Activate virtual environment FIRST
source .venv/bin/activate

# Run tests
pytest                           # All tests (excludes e2e)
pytest tests/e2e -m e2e          # E2E tests (requires auth)

# Install in dev mode
pip install -e ".[all]"
playwright install chromium
```

## Critical Notes

1. **RPC method IDs** in `src/notebooklm/rpc/types.py` are reverse-engineered and can change
2. **Always use async context managers** for the client
3. **Check CONTRIBUTING.md** before creating any documentation files
