import pytest
from .conftest import requires_auth
from notebooklm.services import NotebookService, Notebook


@requires_auth
@pytest.mark.e2e
class TestNotebookOperations:
    @pytest.mark.asyncio
    async def test_list_notebooks(self, client):
        service = NotebookService(client)
        notebooks = await service.list()
        assert isinstance(notebooks, list)
        assert all(isinstance(nb, Notebook) for nb in notebooks)

    @pytest.mark.asyncio
    async def test_get_notebook(self, client, test_notebook_id):
        service = NotebookService(client)
        notebook = await service.get(test_notebook_id)
        assert notebook is not None
        assert isinstance(notebook, Notebook)
        assert notebook.id == test_notebook_id

    @pytest.mark.asyncio
    async def test_create_rename_delete_notebook(
        self, client, created_notebooks, cleanup_notebooks
    ):
        service = NotebookService(client)

        # Create
        notebook = await service.create("E2E Test Notebook")
        assert isinstance(notebook, Notebook)
        assert notebook.title == "E2E Test Notebook"
        created_notebooks.append(notebook.id)

        # Rename
        renamed = await service.rename(notebook.id, "E2E Test Renamed")
        assert isinstance(renamed, Notebook)
        assert renamed.title == "E2E Test Renamed"

        # Delete
        deleted = await service.delete(notebook.id)
        assert deleted is True
        created_notebooks.remove(notebook.id)

    @pytest.mark.asyncio
    async def test_get_summary(self, client, test_notebook_id):
        summary = await client.get_summary(test_notebook_id)
        assert summary is not None

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, client, test_notebook_id):
        history = await client.get_conversation_history(test_notebook_id)
        assert history is not None


@requires_auth
@pytest.mark.e2e
class TestNotebookAsk:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_ask_notebook(self, client, test_notebook_id):
        result = await client.ask(test_notebook_id, "What is this notebook about?")
        assert "answer" in result
        assert "conversation_id" in result


@requires_auth
@pytest.mark.e2e
class TestNotebookDescription:
    @pytest.mark.asyncio
    async def test_get_description(self, client, test_notebook_id):
        from notebooklm.services import NotebookService
        from notebooklm.services.notebooks import NotebookDescription

        service = NotebookService(client)
        description = await service.get_description(test_notebook_id)

        assert isinstance(description, NotebookDescription)
        assert description.summary is not None
        assert isinstance(description.suggested_topics, list)


@requires_auth
@pytest.mark.e2e
class TestNotebookConfigure:
    @pytest.mark.asyncio
    async def test_configure_learning_mode(self, client, test_notebook_id):
        from notebooklm.services import ConversationService
        from notebooklm.services.conversation import ChatMode

        service = ConversationService(client)
        await service.set_mode(test_notebook_id, ChatMode.LEARNING_GUIDE)

    @pytest.mark.asyncio
    async def test_configure_custom_persona(self, client, test_notebook_id):
        from notebooklm.services import ConversationService
        from notebooklm.rpc import ChatGoal

        service = ConversationService(client)
        await service.configure(
            test_notebook_id,
            goal=ChatGoal.CUSTOM,
            custom_prompt="You are a helpful science tutor",
        )

    @pytest.mark.asyncio
    async def test_reset_to_default(self, client, test_notebook_id):
        from notebooklm.services import ConversationService
        from notebooklm.services.conversation import ChatMode

        service = ConversationService(client)
        await service.set_mode(test_notebook_id, ChatMode.DEFAULT)
