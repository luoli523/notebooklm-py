"""Example: Generate an Audio Overview (podcast) from URL sources.

This example demonstrates a complete podcast generation workflow:
1. Create a notebook
2. Add URL sources
3. Generate an audio podcast
4. Wait for completion with progress updates
5. Download the result

Prerequisites:
    - Authentication configured via `notebooklm auth` CLI command
    - Valid Google account with NotebookLM access
"""

import asyncio
from notebooklm import NotebookLMClient, AudioFormat, AudioLength


async def main():
    """Generate a podcast from web sources."""

    # Connect to NotebookLM using stored authentication
    async with await NotebookLMClient.from_storage() as client:

        # Step 1: Create a new notebook for our content
        print("Creating notebook...")
        notebook = await client.notebooks.create("AI Research Podcast")
        print(f"Created notebook: {notebook.id}")

        # Step 2: Add URL sources to the notebook
        # The AI will use these sources to generate the podcast
        urls = [
            "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "https://en.wikipedia.org/wiki/Machine_learning",
        ]

        print("\nAdding sources...")
        for url in urls:
            source = await client.sources.add_url(notebook.id, url)
            print(f"  Added: {source.title or url}")

        # Step 3: Generate the audio overview (podcast)
        # Options:
        #   audio_format: DEEP_DIVE (default), BRIEF, CRITIQUE, or DEBATE
        #   audio_length: SHORT, DEFAULT, or LONG
        #   instructions: Custom guidance for the AI hosts
        print("\nStarting podcast generation...")
        generation = await client.artifacts.generate_audio(
            notebook.id,
            audio_format=AudioFormat.DEEP_DIVE,
            audio_length=AudioLength.DEFAULT,
            instructions="Focus on practical applications and recent breakthroughs",
        )
        print(f"Generation started with task ID: {generation.task_id}")

        # Step 4: Wait for completion with progress polling
        # This can take 2-5 minutes for a full podcast
        print("\nWaiting for generation to complete...")
        print("(This typically takes 2-5 minutes)")

        try:
            final_status = await client.artifacts.wait_for_completion(
                notebook.id,
                generation.task_id,
                initial_interval=5.0,  # Start checking every 5 seconds
                max_interval=15.0,     # Max 15 seconds between checks
                timeout=600.0,         # 10 minute timeout
            )

            if final_status.is_complete:
                print("Podcast generation complete!")

                # Step 5: Download the audio file
                output_path = "ai_podcast.mp4"  # Audio is in MP4 container
                print(f"\nDownloading to {output_path}...")

                await client.artifacts.download_audio(
                    notebook.id,
                    output_path,
                    artifact_id=generation.task_id,
                )
                print(f"Downloaded successfully: {output_path}")

            elif final_status.is_failed:
                print(f"Generation failed: {final_status.error}")

        except TimeoutError:
            print("Generation timed out - it may still be processing")
            print("Check the NotebookLM web UI for status")

        # Optional: List all audio artifacts in the notebook
        print("\nAll audio artifacts:")
        audios = await client.artifacts.list_audio(notebook.id)
        for audio in audios:
            status = "Ready" if audio.is_completed else "Processing"
            print(f"  - {audio.title} ({status})")

        # Cleanup note: The notebook persists after this script ends.
        # Delete it manually or use: await client.notebooks.delete(notebook.id)


if __name__ == "__main__":
    asyncio.run(main())
