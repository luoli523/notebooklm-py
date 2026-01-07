# Documentation Folder

**Status:** Active
**Last Updated:** 2026-01-06

This folder contains all project documentation. AI agents must follow the rules in `/CONTRIBUTING.md`.

## Folder Structure

| Folder | Purpose | File Format |
|--------|---------|-------------|
| `reference/` | Long-lived technical docs | `PascalCase.md` |
| `reference/internals/` | Reverse engineering notes | Any |
| `designs/` | Approved design decisions | `<feature-name>.md` |
| `scratch/` | Temporary agent work | `YYYY-MM-DD-<context>.md` |

## Rules for This Folder

1. **Do not create files in `docs/` root** - Use the appropriate subfolder.

2. **Reference docs are stable** - Only update `reference/` files when fixing errors or adding significant new information.

3. **Designs are permanent** - Files in `designs/` document architectural decisions and should not be deleted.

4. **Scratch is temporary** - Files in `scratch/` can be deleted after 30 days. Always use date prefix.

## Top-Level Files

- `API.md` - User-facing API documentation
- `EXAMPLES.md` - Usage examples for the library
- `FILE_UPLOAD_IMPLEMENTATION.md` - Implementation notes (consider moving to reference/)
