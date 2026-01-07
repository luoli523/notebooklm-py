"""Example: Use the Research API to discover and import sources.

This example demonstrates the research workflow:
1. Start a research session (fast or deep mode)
2. Poll for completion
3. Review discovered sources
4. Import selected sources into the notebook

The Research API searches the web or Google Drive for relevant sources
based on your query, providing AI-curated results.

Prerequisites:
    - Authentication configured via `notebooklm auth` CLI command
    - Valid Google account with NotebookLM access
"""

import asyncio
from notebooklm import NotebookLMClient


async def main():
    """Demonstrate web research and source import."""

    async with await NotebookLMClient.from_storage() as client:

        # Create a notebook for the research
        print("Creating notebook...")
        notebook = await client.notebooks.create("Climate Research")
        print(f"Created notebook: {notebook.id}")

        # =====================================================================
        # Fast Research Mode
        # =====================================================================
        # Fast research returns results quickly (10-30 seconds)
        # Best for getting a quick overview of available sources

        print("\n--- Fast Research Mode ---")
        print("Starting fast web research...")

        task = await client.research.start(
            notebook.id,
            query="climate change mitigation strategies",
            source="web",   # "web" or "drive"
            mode="fast",    # "fast" or "deep"
        )

        if not task:
            print("Failed to start research")
            return

        print(f"Research task started: {task['task_id']}")

        # Poll for results
        print("Polling for results...")
        max_attempts = 30
        for attempt in range(max_attempts):
            result = await client.research.poll(notebook.id)

            if result["status"] == "completed":
                print(f"\nResearch complete! Found {len(result.get('sources', []))} sources")
                break
            elif result["status"] == "in_progress":
                print(f"  Still searching... (attempt {attempt + 1})")
                await asyncio.sleep(2)
            else:
                print(f"  Status: {result['status']}")
                await asyncio.sleep(2)
        else:
            print("Research timed out")
            return

        # Display discovered sources
        sources = result.get("sources", [])
        print("\nDiscovered sources:")
        for i, src in enumerate(sources[:10], 1):  # Show first 10
            title = src.get("title", "Untitled")
            url = src.get("url", "")
            print(f"  {i}. {title}")
            if url:
                print(f"     {url[:60]}...")

        # Display AI summary if available
        summary = result.get("summary", "")
        if summary:
            print(f"\nAI Summary:\n{summary[:500]}...")

        # Import selected sources (first 3 for this example)
        sources_to_import = sources[:3]
        if sources_to_import:
            print(f"\nImporting {len(sources_to_import)} sources...")
            imported = await client.research.import_sources(
                notebook.id,
                task["task_id"],
                sources_to_import,
            )

            print("Imported sources:")
            for src in imported:
                print(f"  - {src['title']} (ID: {src['id']})")

        # =====================================================================
        # Deep Research Mode (Web only)
        # =====================================================================
        # Deep research takes longer (1-3 minutes) but provides:
        # - More comprehensive source discovery
        # - Detailed analysis and synthesis
        # - Higher quality source recommendations

        print("\n--- Deep Research Mode ---")
        print("Starting deep web research...")

        deep_task = await client.research.start(
            notebook.id,
            query="renewable energy policy effectiveness",
            source="web",
            mode="deep",  # Deep mode for thorough research
        )

        if not deep_task:
            print("Failed to start deep research")
            return

        print(f"Deep research task started: {deep_task['task_id']}")
        print("Deep research takes 1-3 minutes...")

        # Poll with longer intervals for deep research
        max_attempts = 60
        for attempt in range(max_attempts):
            result = await client.research.poll(notebook.id)

            if result["status"] == "completed":
                print(f"\nDeep research complete!")
                sources = result.get("sources", [])
                print(f"Found {len(sources)} sources")

                # Deep research often includes more detailed summaries
                if result.get("summary"):
                    print(f"\nResearch synthesis:\n{result['summary'][:800]}...")
                break
            elif result["status"] == "in_progress":
                if attempt % 5 == 0:  # Log every 5 attempts
                    print(f"  Deep analysis in progress... ({attempt * 3}s)")
                await asyncio.sleep(3)
        else:
            print("Deep research timed out")

        # Verify final notebook contents
        print("\n--- Final Notebook Sources ---")
        all_sources = await client.sources.list(notebook.id)
        for src in all_sources:
            print(f"  - {src.title} ({src.source_type})")

        print(f"\nTotal sources in notebook: {len(all_sources)}")


if __name__ == "__main__":
    asyncio.run(main())
