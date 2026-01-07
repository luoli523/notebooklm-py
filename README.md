# notebooklm-client

**Unofficial Python client for Google NotebookLM API**

A comprehensive Python library and CLI for automating Google NotebookLM. Programmatically manage notebooks, add sources, query content, and generate studio artifacts like podcasts, videos, quizzes, and research reports using reverse-engineered RPC APIs.

[![PyPI version](https://badge.fury.io/py/notebooklm-client.svg)](https://badge.fury.io/py/notebooklm-client)
[![Python Version](https://img.shields.io/pypi/pyversions/notebooklm-client.svg)](https://pypi.org/project/notebooklm-client/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Key Features

- **Notebook Management**: Create, list, rename, delete, and configure notebooks.
- **Source Integration**:
  - Web URLs and YouTube videos (with automatic transcript extraction).
  - Native file uploads (PDF, TXT, MD, DOCX) and Google Drive documents.
  - Raw text content and AI-discovered research findings.
- **AI-Powered Querying**: Full-featured chat with streaming support, conversation history, and customizable personas.
- **Studio Artifacts**:
  - **Audio & Video**: Generate podcasts (Audio Overviews) and explainer videos with multiple styles.
  - **Educational Tools**: Create Quizzes, Flashcards, and comprehensive Study Guides.
  - **Visuals & Data**: Generate Slide Decks, Infographics, Data Tables, and Mind Maps.
- **Agentic Research**: Trigger Fast or Deep research agents to gather information from the web or Google Drive.
- **Local Sync & Export**: Download generated media or export artifacts directly to Google Docs and Sheets.

## Installation

### Basic (CLI + API)
```bash
pip install notebooklm-client
```

### With Browser Login Support (Required for first-time setup)
```bash
pip install "notebooklm-client[browser]"
playwright install chromium
```

### Full Development Setup
```bash
pip install "notebooklm-client[all]"
playwright install chromium
```

## Authentication

NotebookLM uses Google's internal `batchexecute` RPC protocol, which requires valid session cookies and CSRF tokens.

### CLI Login (Recommended)
The easiest way to authenticate is using the built-in login command:
```bash
notebooklm login
```
This will open a Chromium window using a **persistent browser profile** (at `~/.notebooklm/browser_profile/`). Log in to your Google account manually, wait for the NotebookLM homepage to load, and press ENTER in the terminal to save the session state to `~/.notebooklm/storage_state.json`.

## Quick Start

### CLI Usage
```bash
# 1. Login (opens browser for Google authentication)
notebooklm login

# 2. Create a notebook and set it as current context
notebooklm create "AI Research"
notebooklm use <notebook_id>  # Use ID from output above

# 3. Add sources (auto-detects URL/YouTube/file)
notebooklm source add "https://en.wikipedia.org/wiki/Artificial_intelligence"
notebooklm source add "./my-paper.pdf"

# 4. Chat with your sources
notebooklm ask "What are the key themes?"

# 5. Generate a podcast (--wait blocks until complete)
notebooklm generate audio "Focus on the history of AI" --wait

# 6. Download the generated audio
notebooklm download audio ./my-podcast.mp3
```

### Python API
```python
import asyncio
from notebooklm import NotebookLMClient
from notebooklm.services import NotebookService, ArtifactService

async def main():
    # Automatically loads auth from default storage path
    async with await NotebookLMClient.from_storage() as client:
        # High-level service layer
        nb_svc = NotebookService(client)
        art_svc = ArtifactService(client)
        
        # 1. Create/Get notebook
        nb = await nb_svc.create("AI Research")
        
        # 2. Add sources
        await client.add_source_url(nb.id, "https://example.com/ai-basics")
        
        # 3. Chat
        response = await client.query(nb.id, "What are the core concepts?")
        print(f"AI: {response['answer']}")
        
        # 4. Generate and wait for a podcast
        status = await art_svc.generate_audio(nb.id, instructions="Make it professional")
        result = await art_svc.wait_for_completion(nb.id, status.task_id)
        print(f"Audio URL: {result.url}")

asyncio.run(main())
```

## CLI Reference

### Context & Auth
| Command | Description |
|---------|-------------|
| `login` | Authenticate via browser |
| `use <notebook_id>` | Set the current notebook context for subsequent commands |
| `status`| Show current notebook and conversation context |
| `clear` | Clear the current context |
| `list` | List notebooks (shortcut for `notebook list`) |
| `create <title>` | Create notebook (shortcut for `notebook create`) |
| `ask <question>` | Chat with current notebook (shortcut) |

### Notebooks (`notebooklm notebook ...`)
| Command | Description |
|---------|-------------|
| `list` | List all accessible notebooks |
| `create <title>` | Create a new notebook |
| `delete <id>` | Delete a notebook |
| `rename <new_title>` | Rename a notebook |
| `share` | Get sharing info for a notebook |
| `summary` | Get AI-generated summary and suggested topics |
| `analytics` | Get usage analytics for the notebook |
| `history` | View or clear conversation history |
| `ask <question>` | Chat with the notebook |
| `configure` | Set chat persona, response length, and mode |
| `research <query>` | Start a research agent session (Fast/Deep) |
| `featured` | List public/featured notebooks from Google |

### Sources (`notebooklm source ...`)
| Command | Description |
|---------|-------------|
| `list` | List all sources in a notebook |
| `add <content>` | Add URL, YouTube, local file, or text (auto-detected) |
| `add-drive <file_id> <title>` | Add Google Drive documents |
| `get <source_id>` | Get details of a specific source |
| `rename <source_id> <title>` | Rename a source |
| `refresh <source_id>` | Re-sync content for URL or Drive sources |
| `delete <source_id>` | Remove a source |

### Generation (`notebooklm generate ...`)
| Command | Description |
|---------|-------------|
| `audio [description]` | Generate podcast with optional instructions |
| `video [description]` | Generate explainer video |
| `slide-deck [description]` | Generate presentation slides |
| `quiz [description]` | Generate interactive quiz |
| `flashcards [description]` | Generate study flashcards |
| `infographic [description]` | Generate visual infographic |
| `data-table [description]` | Generate structured data table |
| `mind-map` | Generate interactive mind map |
| `report [description]` | Generate briefing doc, study guide, or blog post |

### Artifacts (`notebooklm artifact ...`)
| Command | Description |
|---------|-------------|
| `list` | List all artifacts in a notebook |
| `get <artifact_id>` | Get artifact details |
| `rename <artifact_id> <title>` | Rename an artifact |
| `delete <artifact_id>` | Delete an artifact |
| `export <artifact_id>` | Export to Google Docs/Sheets |
| `suggestions` | Get AI-suggested report topics |
| `poll <task_id>` | Check generation status |

### Downloads (`notebooklm download ...`)
| Command | Description |
|---------|-------------|
| `audio [output_path]` | Download audio overview(s) |
| `video [output_path]` | Download video overview(s) |
| `slide-deck [output_path]` | Download slide deck(s) |
| `infographic [output_path]` | Download infographic(s) |

### Notes (`notebooklm note ...`)
| Command | Description |
|---------|-------------|
| `list` | List all notes in a notebook |
| `create <content>` | Create a new note |
| `get <note_id>` | Get note content |
| `save <note_id>` | Update note content |
| `rename <note_id> <title>` | Rename a note |
| `delete <note_id>` | Delete a note |

## Advanced Usage

### Chat Configuration
Customize how the AI responds by setting a persona or using predefined modes:
```bash
# Use a predefined mode
notebooklm notebook configure --mode learning-guide

# Set a custom persona
notebooklm notebook configure --persona "Act as a critical tech journalist" --response-length longer
```

### Research Agent
Trigger an agent to find information from the web or your Drive:
```bash
notebooklm notebook research "Latest breakthroughs in fusion energy" --mode deep --import-all
```

## Documentation
- [Usage Examples](docs/EXAMPLES.md) - Runnable Python scripts for common tasks.
- [API Reference](docs/API.md) - Detailed Python API documentation.
- [RPC Reference](docs/reference/RpcProtocol.md) - Deep dive into the reverse-engineered protocol.
- [Known Issues](docs/reference/KnownIssues.md) - Limitations and workarounds.
- [Contributing](CONTRIBUTING.md) - Guidelines for contributors and AI agents.

## License

MIT License. See [LICENSE](LICENSE) for details.

---
*Disclaimer: This is an unofficial library and is not affiliated with or endorsed by Google.*

