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
├── API.md                 # User-facing API documentation
├── EXAMPLES.md            # Usage examples
├── reference/             # Long-lived technical reference
│   ├── RPC.md             # RPC protocol reference (consolidate duplicates)
│   ├── KNOWN_ISSUES.md    # Known issues (consolidate duplicates)
│   └── internals/         # Reverse engineering notes (optional)
├── designs/               # Approved design docs (permanent)
│   └── YYYY-MM-DD-<feature>-design.md
└── scratch/               # Temporary agent work (disposable)
    └── <any-analysis-files>.md
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

### Plan/Design Lifecycle

1. **Design docs** (`docs/designs/`) - Document the "why" behind major decisions; kept permanently
2. **Implementation plans** - Tactical step-by-step plans; delete after task completion
3. **Scratch files** (`docs/scratch/`) - Temporary work; periodically cleaned up, not permanent artifacts

### Naming Conventions

- Design docs: `YYYY-MM-DD-<feature>-design.md`
- Scratch files: Any descriptive name, no date prefix required
- Reference docs: Simple descriptive names (e.g., `RPC.md`, not `RPC_REFERENCE.md`)

## Migration Plan

1. Create `CONTRIBUTING.md` with human guidelines + agent rules
2. Create `docs/reference/` and `docs/scratch/` directories
3. Consolidate duplicate files:
   - RPC.md + RPC_REFERENCE.md → `docs/reference/RPC.md`
   - KNOWN_ISSUES.md + KNOWN_ISSUES_REFERENCE.md → `docs/reference/KNOWN_ISSUES.md`
4. Move one-off root files to `docs/scratch/`:
   - TEST_FIX_SUMMARY.md
   - EXTRACTION_VERIFICATION.md
   - E2E_TEST_ANALYSIS.md
5. Move reverse engineering notes to `docs/reference/internals/`
6. Rename `docs/plans/` to `docs/designs/`
7. Add reference to CONTRIBUTING.md in each agent file
8. Trim agent files to behavioral instructions only (move shared context to README.md)
