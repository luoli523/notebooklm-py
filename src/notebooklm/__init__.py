"""NotebookLM Automation - RPC-based automation for Google NotebookLM.

This package provides two client implementations:
- NotebookLMClient (from .client): Modern namespaced API client (recommended)
- LegacyNotebookLMClient (from .api_client): Original monolithic client

Example usage with the new client:
    from notebooklm import NotebookLMClient

    async with NotebookLMClient.from_storage() as client:
        notebooks = await client.notebooks.list()
        await client.sources.add_url(notebook_id, "https://example.com")
        result = await client.chat.ask(notebook_id, "What is this about?")
"""

__version__ = "0.1.0"

from .rpc import (
    RPCMethod,
    StudioContentType,
    BATCHEXECUTE_URL,
    QUERY_URL,
    encode_rpc_request,
    build_request_body,
    decode_response,
    RPCError,
)
from .auth import (
    AuthTokens,
    extract_cookies_from_storage,
    extract_csrf_from_html,
    extract_session_id_from_html,
    load_auth_from_storage,
    MINIMUM_REQUIRED_COOKIES,
    ALLOWED_COOKIE_DOMAINS,
    DEFAULT_STORAGE_PATH,
)

# New namespaced client (recommended)
from .client import NotebookLMClient

# Legacy client (for backwards compatibility during migration)
from .api_client import NotebookLMClient as LegacyNotebookLMClient

# Type exports
from .types import (
    Notebook,
    NotebookDescription,
    SuggestedTopic,
    Source,
    Artifact,
    ArtifactStatus,
    GenerationStatus,
    ReportSuggestion,
    Note,
    ConversationTurn,
    AskResult,
    ChatMode,
    # Re-exported enums
    AudioFormat,
    AudioLength,
    VideoFormat,
    VideoStyle,
    QuizQuantity,
    QuizDifficulty,
    InfographicOrientation,
    InfographicDetail,
    SlideDeckFormat,
    SlideDeckLength,
    ReportFormat,
    ChatGoal,
    ChatResponseLength,
    DriveMimeType,
)

__all__ = [
    "__version__",
    # RPC layer
    "RPCMethod",
    "StudioContentType",
    "BATCHEXECUTE_URL",
    "QUERY_URL",
    "encode_rpc_request",
    "build_request_body",
    "decode_response",
    "RPCError",
    # Auth
    "AuthTokens",
    "extract_cookies_from_storage",
    "extract_csrf_from_html",
    "extract_session_id_from_html",
    "load_auth_from_storage",
    "MINIMUM_REQUIRED_COOKIES",
    "ALLOWED_COOKIE_DOMAINS",
    "DEFAULT_STORAGE_PATH",
    # Clients
    "NotebookLMClient",
    "LegacyNotebookLMClient",
    # Types
    "Notebook",
    "NotebookDescription",
    "SuggestedTopic",
    "Source",
    "Artifact",
    "ArtifactStatus",
    "GenerationStatus",
    "ReportSuggestion",
    "Note",
    "ConversationTurn",
    "AskResult",
    "ChatMode",
    # Enums
    "AudioFormat",
    "AudioLength",
    "VideoFormat",
    "VideoStyle",
    "QuizQuantity",
    "QuizDifficulty",
    "InfographicOrientation",
    "InfographicDetail",
    "SlideDeckFormat",
    "SlideDeckLength",
    "ReportFormat",
    "ChatGoal",
    "ChatResponseLength",
    "DriveMimeType",
]
