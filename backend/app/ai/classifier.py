"""
AI-assisted classifier — Layer 2 of the scanner.
Uses Claude to read main entry files and detect characteristics that
pure dependency parsing can't catch (retry loops, streaming patterns, etc.).
"""
import json
import anthropic
from app.config import settings
from app.models import ProjectType

CHARACTERISTICS_PROMPT = """\
You are analyzing a {project_type} codebase for deployment characteristics.

Files:
{files}

Identify which of the following are present (return only what you actually see evidence of):
- agent_retry_loops: Agent has retry/tool-call loops
- streaming_responses: Uses streaming SSE or WebSocket responses
- model_loaded_at_request: Model is loaded inside request handlers (not at startup)
- long_running_tasks: Tasks that run longer than 30 seconds
- sync_io_in_async: Synchronous file/HTTP I/O inside async handlers
- no_connection_pooling: Database/Redis connections opened per request without pooling
- background_workers: Uses Celery/RQ/background workers
- gpu_required: Explicitly uses CUDA/GPU
- persistent_memory: Requires persistent vector store or database for memory

Return a JSON object: {{"characteristics": ["list", "of", "detected", "items"], "notes": "brief explanation"}}
Only return valid JSON, no other text.
"""


async def analyze_code_characteristics(
    files: dict[str, str],
    project_type: ProjectType,
) -> list[str]:
    if not settings.anthropic_api_key:
        return []

    # Limit payload size
    file_snippets = []
    total_chars = 0
    for fname, content in files.items():
        if not fname.endswith((".py", ".txt", ".toml")):
            continue
        snippet = content[:3000]
        file_snippets.append(f"=== {fname} ===\n{snippet}")
        total_chars += len(snippet)
        if total_chars > 15000:
            break

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    msg = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": CHARACTERISTICS_PROMPT.format(
                project_type=project_type.value,
                files="\n\n".join(file_snippets),
            ),
        }],
    )

    try:
        result = json.loads(msg.content[0].text)
        return result.get("characteristics", [])
    except (json.JSONDecodeError, IndexError, KeyError):
        return []
