# Documentation Organization Design

**Date:** 2026-01-06
**Status:** Approved
**Goal:** Reduce documentation sprawl, establish rules for AI agents to follow

## Problem Statement

AI agents create markdown files without discipline, leading to:
- One-off analysis files accumulating at root level
- Implementation plans never cleaned up after completion
- Duplicate reference docs (e.g., RPC.md vs RPC_REFERENCE.md)
- Clutter that confuses both humans and AI agents

## Design Decisions

### 1. File Organization Structure

**Root level (checked into repo):**
```
README.md          # Project overview for users
CONTRIBUTING.md    # Contributor guidelines + AI agent rules (NEW)
CLAUDE.md          # Claude-specific behavioral instructions only
GEMINI.md          # Gemini-specific behavioral instructions only
AGENTS.md          # Multi-agent/other tools instructions only
CHANGELOG.md       # Release history
```

**docs/ folder:**
```
docs/
├── README.md              # Folder-specific rules for documentation (NEW)
├── API.md                 # User-facing API documentation
├── EXAMPLES.md            # Usage examples
├── reference/             # Long-lived technical reference
│   ├── RpcProtocol.md     # RPC protocol reference (PascalCase)
│   ├── KnownIssues.md     # Known issues (PascalCase)
│   └── internals/         # Reverse engineering notes (optional)
├── designs/               # Approved design docs (permanent)
│   └── <feature-name>.md  # No date prefix, gets updated
└── scratch/               # Temporary agent work (disposable)
    └── YYYY-MM-DD-<context>.md  # Date prefix for auto-cleanup
```

### 2. What to Keep vs Delete

| Category | Action |
|----------|--------|
| Design docs (explain "why") | Keep permanently in `docs/designs/` |
| Implementation plans (step-by-step tasks) | Delete after completion |
| One-off analysis files | Put in `docs/scratch/`, clean up periodically |
| Duplicate reference docs | Consolidate into single file |
| Reverse engineering notes | Move to `docs/reference/internals/` or archive |

### 3. Agent File Strategy

**Common project context** → README.md and CONTRIBUTING.md (all agents read these)

**Agent-specific behavioral instructions** → Separate files (CLAUDE.md, GEMINI.md, AGENTS.md) containing only:
- Tool usage preferences
- Commit/PR style
- Agent-specific quirks

Each agent file must include:
```markdown
**IMPORTANT:** Follow documentation rules in CONTRIBUTING.md
```

## Documentation Rules for AI Agents

These rules go in CONTRIBUTING.md:

### File Creation Rules

1. **No Root Rule** - Never create .md files in the repository root unless explicitly instructed
2. **Modify, Don't Fork** - Edit existing files; never create FILE_v2.md, FILE_REFERENCE.md, or FILE_updated.md duplicates
3. **Scratchpad Protocol** - All analysis, investigation logs, and intermediate work go in `docs/scratch/`
4. **Consolidation First** - Before creating new docs, search for existing related docs and update them instead

### Protected Sections

Some sections within files are critical and must not be modified without explicit approval.

**Inline markers** (source of truth):
```markdown
<!-- PROTECTED: Do not modify without approval -->
## Critical Section Title
Content that should not be changed by agents...
<!-- END PROTECTED -->
```

For code files:
```python
# PROTECTED: Do not modify without approval
class RPCMethod(Enum):
    ...
# END PROTECTED
```

**Rule:** Agents must never modify content between `PROTECTED` and `END PROTECTED` markers unless explicitly instructed by the user.

### Plan/Design Lifecycle

1. **Design docs** (`docs/designs/`) - Document the "why" behind major decisions; kept permanently
2. **Implementation plans** - Tactical step-by-step plans; delete after task completion
3. **Scratch files** (`docs/scratch/`) - Temporary work; periodically cleaned up, not permanent artifacts

### Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Design docs | `<feature-name>.md` (no date, gets updated) | `authentication.md`, `cli-refactoring.md` |
| Reference docs | `PascalCase.md` (acronyms stay caps) | `RpcProtocol.md`, `API.md` |
| Scratch files | `YYYY-MM-DD-<context>.md` (date for auto-cleanup) | `2026-01-06-debug-auth.md` |

### Status Headers

All docs should include status metadata for staleness tracking:

```markdown
**Status:** Active | Deprecated
**Last Updated:** YYYY-MM-DD
```

Agents should ignore files marked `Deprecated`.

### Information Management Principles

1. **Link, Don't Copy** - Agent files should reference README.md sections instead of repeating commands. Prevents drift between docs.

2. **Scoped Instructions** - Put folder-specific rules in that folder's README.md:
   - `docs/README.md` - Rules for documentation structure
   - Root agent files - Only agent-specific behavioral instructions

3. **Minimal Agent Files** - CLAUDE.md, GEMINI.md, AGENTS.md contain only:
   - Tool/commit preferences specific to that agent
   - Link to CONTRIBUTING.md for shared rules
   - NO repeated project context (that's in README.md)

## Migration Plan

1. Create `CONTRIBUTING.md` with human guidelines + agent rules
2. Create `docs/README.md` with folder-specific documentation rules
3. Create `docs/reference/` and `docs/scratch/` directories
4. Consolidate and rename duplicate files (using PascalCase):
   - RPC.md + RPC_REFERENCE.md → `docs/reference/RpcProtocol.md`
   - KNOWN_ISSUES.md + KNOWN_ISSUES_REFERENCE.md → `docs/reference/KnownIssues.md`
5. Move one-off root files to `docs/scratch/` (with date prefix):
   - TEST_FIX_SUMMARY.md → `docs/scratch/2026-01-XX-test-fix-summary.md`
   - EXTRACTION_VERIFICATION.md → `docs/scratch/2026-01-XX-extraction-verification.md`
   - E2E_TEST_ANALYSIS.md → `docs/scratch/2026-01-XX-e2e-test-analysis.md`
6. Move reverse engineering notes to `docs/reference/internals/`
7. Rename `docs/plans/` to `docs/designs/` and remove date prefixes from filenames
8. Add reference to CONTRIBUTING.md in each agent file
9. Trim agent files to behavioral instructions only (use "Link, Don't Copy")
