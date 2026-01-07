# Known Issues Reference

**Status:** Active
**Last Updated:** 2026-01-06

This document provides a comprehensive reference of known issues, limitations, and edge cases for the `notebooklm-client` library. As this library uses reverse-engineered private APIs, these issues are often inherent to the Google NotebookLM platform and its undocumented endpoints.

---

## Resolved Issues

### Async Artifact Generation (Fixed in v0.1.0)

**Previously:** Artifact generation methods returned `None` instead of task/artifact metadata.

**Resolution:** The issue was a parameter order bug in our implementation, not an API limitation. We had swapped `format_code` and `length_code` positions in the audio_options array.

**Current Behavior:** All artifact generation methods now return a dictionary with metadata:
```python
{
    "artifact_id": str,       # Unique identifier
    "status": str,            # "in_progress" or "completed"
    "title": Optional[str],   # Artifact title
    "create_time": Optional[str]  # ISO timestamp
}
```

---

## 1. API Limitations

### Rate Limiting Behavior
Google NotebookLM enforces strict rate limiting on its `batchexecute` RPC endpoints.
- **Symptom:** RPC calls return `None` or raise `RPCError` with ID `R7cb6c`.
- **Trigger:** Rapidly creating multiple notebooks, sources, or artifacts in a short duration (e.g., during E2E test execution).
- **Error Code:** `UserDisplayableError` with code `[3]` often indicates rate limiting or temporary blocking.

### Quota Restrictions
Certain features, particularly high-compute artifact generation, have daily or hourly quotas.
- **Audio/Video Overviews:** There are strict limits on how many podcasts or videos can be generated per account per day.
- **Research Agents:** Deep Research tasks consume significant backend resources and may be restricted after a few runs.

### Session Expiration
Authentication sessions are tied to Google's internal cookie expiration.
- Sessions typically last from a few days to a few weeks depending on Google's security policies.
- If the `SID` cookie or other critical auth cookies expire, all API calls will fail with `401 Unauthorized` or redirect to the login page.

---

## 2. RPC-Specific Issues

### Non-Functional Methods
Some discovered RPC IDs do not work as expected when called directly:
- **`GET_ARTIFACT` (`BnLyuf`):** Returns a `400 Bad Request` or empty result. **Fix:** The library filters the `LIST_ARTIFACTS` result to find specific artifact details.
- **`GET_SOURCE` (`hizoJc`):** Does not reliably return source content. **Fix:** Source information is extracted from the parent notebook's metadata.

### Unexpected Null Returns
Google's API often returns `null` instead of an error message when a request fails or is rate-limited.
- Methods in `api_client.py` frequently use `allow_null=True` to handle these cases without crashing.
- **Affected Methods:** `generate_audio`, `generate_video`, `create_artifact`, `poll_studio_status`.

### Payload Structure Sensitivities
The RPC parameters are position-sensitive and brittle.
- **Audio Options:** Swapping the position of `format_code` and `length_code` in the `AHyHrd` call causes the API to return `null`.
- **List Artifacts:** The alternative listing method (`LfTXoe`) sometimes returns empty results or inconsistent structures compared to the primary `gArtLc` method.

---

## 3. Authentication Issues

### Cookie Requirements
The library requires at least the `SID` cookie for basic authentication. However, full functionality (especially downloads) requires a complete set of Google auth cookies (`HSID`, `SSID`, `APISID`, `SAPISID`, etc.).

### CSRF and Session ID Handling
All RPC calls require a CSRF token (`SNlM0e`) and a Session ID (`FdrFJe`).
- These are extracted from the `notebooklm.google.com` homepage HTML.
- If these patterns change in Google's frontend code, token extraction will fail, effectively breaking the client.

### Automated Login Blocks
Google often blocks login attempts from automated browser environments (like standard Playwright/Selenium).
- **Solution:** The CLI uses a **persistent browser profile** (`~/.notebooklm/browser_profile/`) which makes the browser appear as a regular user installation.

---

## 4. Content Generation Issues

### Reliability of Visual Artifacts
Generation of complex artifacts is less reliable than standard text queries:
- **Infographics & Slide Decks:** High failure rate under heavy load. The API may return success but the artifact never appears in the list.
- **Data Tables:** Often fails if the sources do not contain structured numerical data.

### Status Polling Edge Cases
Polling for artifact status (`gArtLc`) can be tricky:
- If a generation task fails immediately, the polling method might never see the "failed" status and simply never show the artifact.
- The API does **not return a Task ID** for tracking; the library must poll the entire artifact list and look for the new entry.

---

## 5. Download Issues

### Browser-Based Authentication
Artifact URLs (e.g., `https://lh3.googleusercontent.com/...`) require cross-domain authentication.
- **Issue:** Standard HTTP clients like `httpx` cannot handle the complex cookie redirection required to authenticate these content domains.
- **Requirement:** Playwright (Chromium) is required to download these files using the persistent browser profile.

### Google Content URL Expiry
Download URLs for audio and video files are temporary.
- If you save a URL and try to download it hours later, it will likely return a `403 Forbidden` or `404 Not Found`.
- **Workaround:** Always refresh the artifact list to get a fresh URL before attempting a download.

---

## 6. File Upload Issues

### Native Upload Support
Native file uploads (via `UPLOAD_URL`) are partially implemented but inconsistent:
- **Supported:** `.pdf`, `.txt`, `.md`, `.docx`.
- **Issues:** Text (`.txt`) and Markdown (`.md`) uploads via the native `add-file` command often return `None` or fail to register as sources.
- **Size Limits:** While not explicitly documented, files over 20MB or documents with more than 500,000 words may fail to process.

### Resumable Uploads
The current implementation uses simple POST uploads. Large files that require resumable multi-part uploads are not yet supported and may time out.

---

## 7. Workarounds

| Issue | Recommended Workaround |
|-------|------------------------|
| **Rate Limiting** | Add `asyncio.sleep(5)` between intensive operations; use exponential backoff. |
| **`GET_ARTIFACT` Failure** | Use `list_artifacts()` and filter by ID or title. |
| **File Upload Failures** | For text/markdown, use `add_source_text()` which sends the content directly in the RPC payload. |
| **Auth Expiration** | Run `notebooklm login` to refresh the `storage_state.json`. |
| **Download Failures** | Ensure Playwright is installed: `pip install "notebooklm-client[browser]"`. |
| **Artifact Not Appearing** | Poll `list_artifacts()` for up to 60 seconds after a generation call. |
| **PDF Structure Issues** | Use `add-pdf` (extraction-based) instead of `add-file` (native) for better control over text layout. |
