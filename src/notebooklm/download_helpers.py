"""Helper functions for download commands."""

from typing import Any, Optional, TypedDict


class ArtifactDict(TypedDict):
    """Artifact structure returned by list_artifacts API."""

    id: str
    title: str
    created_at: int  # Unix timestamp


def select_artifact(
    artifacts: list[ArtifactDict],
    latest: bool = True,
    earliest: bool = False,
    name: Optional[str] = None,
    artifact_id: Optional[str] = None,
) -> tuple[ArtifactDict, str]:
    """
    Select an artifact from a list based on criteria.

    CRITICAL: Implements Filter → Count → Select logic:
    1. Filter artifacts by name/artifact_id if provided
    2. Count matches (0/1/many)
    3. Apply latest/earliest to remaining matches

    Args:
        artifacts: List of artifact dicts with 'id', 'title', 'created_at'
        latest: Select most recent (default: True)
        earliest: Select oldest (overrides latest if True)
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
        raise ValueError("Cannot specify both --latest and --earliest")

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
    else:
        # Default to latest (latest=True by default)
        selected = max(filtered, key=lambda a: a["created_at"])
        return selected, f"latest of {count} artifacts"
