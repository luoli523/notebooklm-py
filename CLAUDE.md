# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**IMPORTANT:** Follow documentation rules in [CONTRIBUTING.md](CONTRIBUTING.md) - especially the file creation and naming conventions.

## Project Overview

`notebooklm-client` is an unofficial Python client for Google NotebookLM that uses reverse-engineered RPC APIs. The library enables programmatic automation of NotebookLM features including notebook management, source integration, AI querying, and studio artifact generation (podcasts, videos, quizzes, etc.).

**Critical constraint**: This uses Google's internal `batchexecute` RPC protocol with obfuscated method IDs that Google can change at any time. All RPC method IDs in `src/notebooklm/rpc/types.py` are reverse-engineered and subject to breakage.

## Development Commands

### Testing
```bash
# Run all tests (excluding e2e by default)
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/unit/test_decoder.py

# Run e2e tests (requires authentication)
pytest tests/e2e -m e2e

# Run slow tests (audio/video generation)
pytest -m slow
```

### Build and Install
```bash
# Install in development mode with all extras
pip install -e ".[all]"
playwright install chromium

# Install only browser support
pip install -e ".[browser]"
```

### CLI Testing
```bash
# The CLI entry point is defined in pyproject.toml
notebooklm --help
notebooklm login
notebooklm list
```

## Architecture

### Three-Layer Design

1. **RPC Layer** (`src/notebooklm/rpc/`):
   - `types.py`: Defines all RPC method IDs (e.g., `RPCMethod.CREATE_NOTEBOOK = "CCqFvf"`) and enum types for API parameters
   - `encoder.py`: Converts Python objects to batchexecute request format
   - `decoder.py`: Parses chunked responses (strips `)]}'` prefix, extracts JSON)
   - **Key pattern**: All requests go through `encode_rpc_request(method_id, params) -> str` which generates nested list structures like `[[["CCqFvf", "[...]", null, "generic"]]]`

2. **Client Layer** (`src/notebooklm/api_client.py`):
   - `NotebookLMClient`: Main async API client
   - Uses `_rpc_call(method, params)` for all batchexecute operations
   - Uses `_query_stream()` for the streaming query endpoint (different protocol)
   - Handles auth tokens, request counters (`_reqid_counter`), and conversation caching
   - **Authentication**: Requires `AuthTokens(cookies, csrf_token, session_id)` from browser login

3. **Service Layer** (`src/notebooklm/services/`):
   - `NotebookService`, `SourceService`, `ArtifactService`, `QueryService`
   - Wraps raw RPC responses in typed Python objects (e.g., `Notebook`, `Source`, `GenerationStatus`)
   - Provides high-level operations like `wait_for_completion()` for polling

### Authentication Flow

NotebookLM requires valid Google session cookies. The library uses Playwright to:
1. Launch a persistent browser profile at `~/.notebooklm/browser_profile/` (avoids bot detection)
2. Let user manually log in to Google
3. Extract cookies and CSRF token
4. Save to `~/.notebooklm/storage_state.json`

**Why persistent profile?** Google blocks automated logins. A persistent profile makes the browser look like a regular user installation.

### RPC Protocol Details

**Endpoint**: `https://notebooklm.google.com/_/LabsTailwindUi/data/batchexecute`

**Request format**:
```
f.req=[[[method_id, params_json, null, "generic"]]]&at=CSRF_TOKEN
```

**Response format**:
- Chunked, prefixed with `)]}'`
- Contains nested lists matching the request's RPC method ID
- `decoder.py` handles parsing and extraction

**Adding new RPC methods**:
1. Capture network traffic in DevTools (filter by `batchexecute`)
2. Find the `rpcids` parameter to identify the method ID
3. Analyze the `f.req` payload structure
4. Add the method ID to `RPCMethod` enum in `types.py`
5. Implement the client method using `self._rpc_call(RPCMethod.NEW_METHOD, params)`

## Key Files

- `src/notebooklm/api_client.py`: Core async client with all RPC methods
- `src/notebooklm/rpc/types.py`: All RPC method IDs and parameter enums (THE source of truth for API constants)
- `src/notebooklm/auth.py`: Authentication token management and browser login
- `src/notebooklm/notebooklm_cli.py`: Click-based CLI implementation

## Testing Strategy

- **Unit tests** (`tests/unit/`): Test RPC encoding/decoding, auth logic, CLI commands (mocked)
- **Integration tests** (`tests/integration/`): Test client methods with mocked HTTP responses
- **E2E tests** (`tests/e2e/`): Require real authentication, marked with `@pytest.mark.e2e`, excluded by default
- **Fixtures**: `tests/conftest.py` provides `mock_client`, `mock_auth`, `mock_httpx` fixtures

### E2E Test Status

**Current Results:** 30/58 passing (51.7%)

**Known Issue:** 27 tests fail with `RPCError: No result found for RPC ID: R7cb6c` when generating artifacts (audio, video, quiz, slides, infographics). This is:
- **Not a bug in the code** - Same issue exists in the original project
- **Likely rate limiting or API restrictions** from Google
- **Documented limitation** - See `docs/scratch/2026-01-05-e2e-test-analysis.md` for full details

**What works in E2E:**
- ✅ All notebook operations (list, create, rename, delete, query)
- ✅ All source operations (add URL/text/YouTube, rename)
- ✅ All download operations (audio, video, infographic, slides)
- ✅ Some artifact operations (mind map, study guide, FAQ, data table)

**What's unreliable in E2E:**
- ❌ Artifact generation (audio, video, quiz, flashcards, infographics, slides)
- ⚠️ File upload (text/markdown files returning None)

## Common Pitfalls

1. **RPC method IDs change**: If Google updates their UI, obfuscated IDs may break. Check network traffic and update `types.py`.
2. **Nested list structures**: RPC params are highly nested. Example: `[title, None, None, None, None]` for notebook creation. Position matters.
3. **Streaming responses**: The query endpoint uses a different protocol (gRPC-like) with chunked SSE-style responses. See `_query_stream()`.
4. **CSRF tokens**: Must be extracted from initial page load or storage state. Tokens expire.
5. **File upload**: `add_source_file()` uses native upload (no local text extraction). For PDF text extraction, use services layer's `add_pdf()` instead.

## Repository Structure

```
src/notebooklm/
  ├── __init__.py          # Exports NotebookLMClient
  ├── api_client.py        # Main client implementation
  ├── auth.py              # Browser login and token management
  ├── notebooklm_cli.py    # CLI commands
  ├── rpc/                 # RPC protocol layer
  │   ├── types.py         # Method IDs and enums
  │   ├── encoder.py       # Request encoding
  │   └── decoder.py       # Response parsing
  └── services/            # High-level service abstractions
      ├── notebooks.py
      ├── sources.py
      ├── artifacts.py
      └── query.py
```

## Package Configuration

- **Entry point**: `notebooklm` CLI defined in `[project.scripts]`
- **Dependencies**: `httpx` (async HTTP), `click` (CLI), `rich` (terminal output)
- **Optional deps**: `playwright` (browser login), PDF backends (not in current pyproject.toml)
- **Python support**: 3.9+
- **Build system**: Hatchling
- **Package path**: `src/notebooklm/` (using `hatch.build.targets.wheel.packages`)

## In order to run any python script, you must first activate the virtual environment
source .venv/bin/activate 