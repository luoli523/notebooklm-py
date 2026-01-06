"""Integration tests for domain services."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from notebooklm.services import (
    NotebookService,
    SourceService,
    ArtifactService,
    Notebook,
    Source,
    ArtifactStatus,
)
from notebooklm.auth import AuthTokens


@pytest.fixture
def auth_tokens():
    return AuthTokens(
        cookies={
            "SID": "test_sid",
            "HSID": "test_hsid",
            "SSID": "test_ssid",
            "APISID": "test_apisid",
            "SAPISID": "test_sapisid",
        },
        csrf_token="test_csrf",
        session_id="test_session",
    )


class TestNotebookService:
    @pytest.mark.asyncio
    async def test_list_notebooks(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.list_notebooks.return_value = [
            [
                "First Notebook",
                [],
                "nb_001",
                "📘",
                None,
                [None, None, None, None, None, [1704067200, 0]],
            ],
            [
                "Second Notebook",
                [],
                "nb_002",
                "📚",
                None,
                [None, None, None, None, None, [1704153600, 0]],
            ],
        ]

        service = NotebookService(mock_client)
        notebooks = await service.list()

        assert len(notebooks) == 2
        assert notebooks[0].id == "nb_001"
        assert notebooks[0].title == "First Notebook"

    @pytest.mark.asyncio
    async def test_create_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.create_notebook.return_value = [
            "My Research",
            [],
            "nb_new",
            "📓",
            None,
            [None, None, None, None, None, [1704067200, 0]],
        ]

        service = NotebookService(mock_client)
        notebook = await service.create("My Research")

        assert notebook.id == "nb_new"
        assert notebook.title == "My Research"
        mock_client.create_notebook.assert_called_once_with("My Research")

    @pytest.mark.asyncio
    async def test_get_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        # get_notebook returns [nb_info, ...] where nb_info is the notebook data
        mock_client.get_notebook.return_value = [
            [
                "Test Notebook",
                [["src_001", "Source 1"], ["src_002", "Source 2"]],
                "nb_001",
            ]
        ]

        service = NotebookService(mock_client)
        notebook = await service.get("nb_001")

        assert notebook.id == "nb_001"
        assert notebook.title == "Test Notebook"

    @pytest.mark.asyncio
    async def test_delete_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.delete_notebook.return_value = [True]

        service = NotebookService(mock_client)
        result = await service.delete("nb_001")

        assert result is True
        mock_client.delete_notebook.assert_called_once_with("nb_001")

    @pytest.mark.asyncio
    async def test_rename_notebook(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.rename_notebook.return_value = [
            "Renamed Notebook",
            [],
            "nb_001",
            "📘",
            None,
            [None, None, None, None, None, [1704067200, 0]],
        ]

        service = NotebookService(mock_client)
        notebook = await service.rename("nb_001", "Renamed Notebook")

        assert notebook.id == "nb_001"
        assert notebook.title == "Renamed Notebook"
        mock_client.rename_notebook.assert_called_once_with(
            "nb_001", "Renamed Notebook"
        )


class TestSourceService:
    @pytest.mark.asyncio
    async def test_add_url(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.add_source_url.return_value = [
            [
                [
                    ["src_001"],
                    "Example Site",
                    [None, 11, None, None, 5, None, 1, ["https://example.com"]],
                    [None, 2],
                ]
            ]
        ]

        service = SourceService(mock_client)
        source = await service.add_url("nb_001", "https://example.com")

        assert source.id == "src_001"
        assert source.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_add_text(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.add_source_text.return_value = [
            [[["src_002"], "My Notes", [None, 11], [None, 2]]]
        ]

        service = SourceService(mock_client)
        source = await service.add_text("nb_001", "My Notes", "Content here")

        assert source.id == "src_002"
        assert source.title == "My Notes"

    @pytest.mark.asyncio
    async def test_get_source(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.get_source.return_value = [
            [[["src_001"], "Source Title", [None, 11], [None, 2]]]
        ]

        service = SourceService(mock_client)
        source = await service.get("nb_001", "src_001")

        assert source.id == "src_001"
        assert source.title == "Source Title"
        mock_client.get_source.assert_called_once_with("nb_001", "src_001")

    @pytest.mark.asyncio
    async def test_delete_source(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.delete_source.return_value = [True]

        service = SourceService(mock_client)
        result = await service.delete("nb_001", "src_001")

        assert result is True
        mock_client.delete_source.assert_called_once_with("nb_001", "src_001")


class TestArtifactService:
    @pytest.mark.asyncio
    async def test_generate_audio(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.generate_audio.return_value = {
            "artifact_id": "task_001",
            "status": "in_progress",
            "title": "Audio Overview",
            "create_time": "2024-01-05",
        }

        service = ArtifactService(mock_client)
        status = await service.generate_audio("nb_001")

        assert status.task_id == "task_001"
        assert status.status == "in_progress"

    @pytest.mark.asyncio
    async def test_generate_audio_with_instructions(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.generate_audio.return_value = {
            "artifact_id": "task_002",
            "status": "in_progress",
            "title": "Audio Overview",
            "create_time": "2024-01-05",
        }

        service = ArtifactService(mock_client)
        await service.generate_audio("nb_001", instructions="Be casual")

        mock_client.generate_audio.assert_called_once_with(
            "nb_001", instructions="Be casual"
        )

    @pytest.mark.asyncio
    async def test_generate_slide_deck(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.generate_slide_deck.return_value = {
            "artifact_id": "task_003",
            "status": "in_progress",
            "title": "Slide Deck",
            "create_time": "2024-01-05",
        }

        service = ArtifactService(mock_client)
        status = await service.generate_slide_deck("nb_001")

        assert status.task_id == "task_003"
        assert status.status == "in_progress"

    @pytest.mark.asyncio
    async def test_poll_status(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.poll_studio_status.return_value = [
            "task_001",
            "completed",
            "https://storage.googleapis.com/audio.mp3",
        ]

        service = ArtifactService(mock_client)
        status = await service.poll_status("nb_001", "task_001")

        assert status.status == "completed"
        assert status.url == "https://storage.googleapis.com/audio.mp3"

    @pytest.mark.asyncio
    async def test_wait_for_completion(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.poll_studio_status.side_effect = [
            ["task_001", "pending", None],
            ["task_001", "processing", None],
            ["task_001", "completed", "https://result.mp3"],
        ]

        service = ArtifactService(mock_client)
        status = await service.wait_for_completion(
            "nb_001", "task_001", poll_interval=0.01
        )

        assert status.status == "completed"
        assert mock_client.poll_studio_status.call_count == 3

    @pytest.mark.asyncio
    async def test_suggest_reports(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.get_suggested_report_formats.return_value = [
            {
                "title": "Research Summary",
                "description": "A comprehensive summary",
                "prompt": "Create a research summary",
            },
            {
                "title": "Executive Brief",
                "description": "Key findings overview",
                "prompt": "Create an executive brief",
            },
        ]

        service = ArtifactService(mock_client)
        suggestions = await service.suggest_reports("nb_001")

        assert len(suggestions) == 2
        assert suggestions[0].title == "Research Summary"
        assert suggestions[0].description == "A comprehensive summary"
        assert suggestions[1].title == "Executive Brief"
        mock_client.get_suggested_report_formats.assert_called_once_with("nb_001", None)

    @pytest.mark.asyncio
    async def test_suggest_reports_with_source_ids(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.get_suggested_report_formats.return_value = [
            {
                "title": "Focused Report",
                "description": "Based on selected sources",
                "prompt": "Create focused report",
            },
        ]

        service = ArtifactService(mock_client)
        suggestions = await service.suggest_reports("nb_001", ["src_001", "src_002"])

        assert len(suggestions) == 1
        mock_client.get_suggested_report_formats.assert_called_once_with(
            "nb_001", ["src_001", "src_002"]
        )


class TestConversationService:
    @pytest.mark.asyncio
    async def test_configure_with_mode(self, auth_tokens):
        from notebooklm.services import ConversationService
        from notebooklm.services.conversation import ChatMode

        mock_client = AsyncMock()
        mock_client.configure_chat.return_value = None

        service = ConversationService(mock_client)
        await service.set_mode("nb_001", ChatMode.LEARNING_GUIDE)

        mock_client.configure_chat.assert_called_once()
        args = mock_client.configure_chat.call_args
        assert args[0][0] == "nb_001"

    @pytest.mark.asyncio
    async def test_configure_with_custom_persona(self, auth_tokens):
        from notebooklm.services import ConversationService
        from notebooklm.rpc import ChatGoal, ChatResponseLength

        mock_client = AsyncMock()
        mock_client.configure_chat.return_value = None

        service = ConversationService(mock_client)
        await service.configure(
            "nb_001",
            goal=ChatGoal.CUSTOM,
            response_length=ChatResponseLength.LONGER,
            custom_prompt="Act as a physics tutor",
        )

        mock_client.configure_chat.assert_called_once_with(
            "nb_001",
            ChatGoal.CUSTOM,
            ChatResponseLength.LONGER,
            "Act as a physics tutor",
        )


class TestNotebookServiceExtended:
    @pytest.mark.asyncio
    async def test_get_description(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.get_notebook_description.return_value = {
            "summary": "This notebook covers machine learning basics.",
            "suggested_topics": [
                {
                    "question": "What is supervised learning?",
                    "prompt": "Explain supervised learning",
                },
                {
                    "question": "How does backpropagation work?",
                    "prompt": "Explain backpropagation",
                },
            ],
        }

        service = NotebookService(mock_client)
        description = await service.get_description("nb_001")

        assert description.summary == "This notebook covers machine learning basics."
        assert len(description.suggested_topics) == 2
        assert (
            description.suggested_topics[0].question == "What is supervised learning?"
        )
        mock_client.get_notebook_description.assert_called_once_with("nb_001")

    @pytest.mark.asyncio
    async def test_get_description_empty_topics(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.get_notebook_description.return_value = {
            "summary": "A notebook with no suggestions yet.",
            "suggested_topics": [],
        }

        service = NotebookService(mock_client)
        description = await service.get_description("nb_001")

        assert description.summary == "A notebook with no suggestions yet."
        assert len(description.suggested_topics) == 0


class TestSourceServiceExtended:
    @pytest.mark.asyncio
    async def test_add_drive_file(self, auth_tokens):
        mock_client = AsyncMock()
        mock_client.add_source_drive.return_value = [
            [[["src_drive_001"], "My Google Doc", [None, 0], [None, 2]]]
        ]

        service = SourceService(mock_client)
        source = await service.add_drive_file(
            "nb_001",
            file_id="1abc123xyz",
            title="My Google Doc",
            mime_type="application/vnd.google-apps.document",
        )

        assert source.id == "src_drive_001"
        assert source.title == "My Google Doc"
        mock_client.add_source_drive.assert_called_once_with(
            "nb_001",
            "1abc123xyz",
            "My Google Doc",
            "application/vnd.google-apps.document",
        )
