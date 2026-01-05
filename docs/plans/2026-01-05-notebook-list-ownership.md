# Notebook List Ownership Display

**Date:** 2026-01-05
**Status:** Design Approved

## Overview

Add ownership status indicator to the notebook list command to show whether each notebook is owned by the user or shared by someone else. This is important because shared notebooks are read-only (cannot add sources or generate artifacts).

## Current State

The `notebooklm list` command currently shows:
- ID
- Title
- Created

## Design

### 1. Ownership Detection

Ownership is determined by checking `data[5][1]` in the notebook API response:
- `False` → User is the owner (👤 Owner)
- `True` → Notebook is shared (👥 Shared)

**Detection function:**
```python
def detect_ownership(nb_data: list) -> str:
    """Detect if notebook is owned or shared.

    Detection logic:
    - Check nb_data[5][1] - False indicates owned, True indicates shared

    Returns:
        Display string: "👤 Owner" or "👥 Shared"
    """
    if len(nb_data) > 5 and isinstance(nb_data[5], list) and len(nb_data[5]) > 1:
        is_shared = nb_data[5][1]
        if is_shared is False:
            return "👤 Owner"
        elif is_shared is True:
            return "👥 Shared"

    # Default to Owner if we can't determine
    return "👤 Owner"
```

### 2. Notebook Dataclass Update

Add `is_owner` field to the Notebook dataclass in `services/notebooks.py`:

```python
@dataclass
class Notebook:
    """Represents a NotebookLM notebook."""

    id: str
    title: str
    created_at: Optional[datetime] = None
    sources_count: int = 0
    is_owner: bool = True  # New field - True if user owns, False if shared

    @classmethod
    def from_api_response(cls, data: list[Any]) -> "Notebook":
        raw_title = data[0] if len(data) > 0 and isinstance(data[0], str) else ""
        title = raw_title.replace("thought\n", "").strip()
        notebook_id = data[2] if len(data) > 2 and isinstance(data[2], str) else ""

        created_at = None
        if len(data) > 5 and isinstance(data[5], list) and len(data[5]) > 5:
            ts_data = data[5][5]
            if isinstance(ts_data, list) and len(ts_data) > 0:
                try:
                    created_at = datetime.fromtimestamp(ts_data[0])
                except (TypeError, ValueError):
                    pass

        # Extract ownership - data[5][1] = False means owner, True means shared
        is_owner = True
        if len(data) > 5 and isinstance(data[5], list) and len(data[5]) > 1:
            is_owner = data[5][1] is False

        return cls(
            id=notebook_id,
            title=title,
            created_at=created_at,
            is_owner=is_owner
        )
```

### 3. Table Structure

**New Column Order:**
- ID (existing)
- Title (existing)
- **Owner** (new)
- Created (existing)

**Implementation:**
```python
table = Table(title="Notebooks")
table.add_column("ID", style="cyan")
table.add_column("Title", style="green")
table.add_column("Owner")
table.add_column("Created", style="dim")

for nb in notebooks:
    created = nb.created_at.strftime("%Y-%m-%d") if nb.created_at else "-"
    owner_status = "👤 Owner" if nb.is_owner else "👥 Shared"
    table.add_row(nb.id, nb.title, owner_status, created)
```

### 4. Example Output

```
Notebooks
┌──────────────┬─────────────────────────────┬──────────┬────────────┐
│ ID           │ Title                       │ Owner    │ Created    │
├──────────────┼─────────────────────────────┼──────────┼────────────┤
│ nb_abc123    │ My Research Project         │ 👤 Owner │ 2026-01-05 │
│ nb_def456    │ Team Collaboration          │ 👥 Shared│ 2026-01-04 │
│ nb_ghi789    │ Personal Notes              │ 👤 Owner │ 2026-01-03 │
└──────────────┴─────────────────────────────┴──────────┴────────────┘
```

### 5. Permissions Context

**Owner (👤 Owner):**
- Can add sources
- Can generate artifacts (audio, video, reports, etc.)
- Can rename/delete notebook
- Full edit permissions

**Shared (👥 Shared):**
- Read-only access
- Cannot add sources
- Cannot generate artifacts
- Can query and view existing content

## Implementation Notes

- **Location 1**: `src/notebooklm/services/notebooks.py`
  - Add `is_owner: bool = True` field to Notebook dataclass (line 18)
  - Update `from_api_response()` to extract ownership from `data[5][1]` (lines 21-35)

- **Location 2**: `src/notebooklm/notebooklm_cli.py`
  - Update `list_notebooks_shortcut()` function (lines 348-378)
  - Add "Owner" column to table
  - Display ownership status based on `nb.is_owner`

## Benefits

1. **Visibility**: Users can immediately see which notebooks they own vs. which are shared
2. **Permissions clarity**: Clear indication of edit permissions before attempting operations
3. **Error prevention**: Users won't try to add sources/artifacts to shared notebooks
4. **Consistency**: Matches the emoji pattern from artifact and source list improvements
