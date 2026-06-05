"""
AI classifier — Layer 2 scanner.
Uses Claude to read the most informative files and return:
 - confirmed or corrected project type
 - list of detected characteristics
 - brief reasoning string

Runs after dep_parser so it can use the L1 classification as a prior.
"""
import re
import json
import logging
from openai import AsyncOpenAI
from app.config import settings
from app.models import ProjectType

log = logging.getLogger(__name__)

# Files that tell Claude the most about the project — prioritised
_INFORMATIVE_SUFFIXES = (".py", ".toml", ".txt", ".cfg", ".yml", ".yaml", ".md")
_SKIP_DIRS = {"tests/", "test/", "__pycache__/", ".git/", "migrations/", "alembic/"}

SYSTEM_PROMPT = """\
You are an expert DevOps and ML infrastructure engineer.
Your job is to analyse source code and classify the deployment requirements.
Be precise. Do not invent characteristics that are not evidenced in the code.
Return ONLY valid JSON — no markdown fences, no explanation text."""

ANALYSIS_PROMPT = """\
Analyse the codebase below and return a JSON object with these exact keys:

{{
  "project_type": one of {types},
  "confidence": float 0-1 (how certain you are given the evidence),
  "characteristics": [array of strings from the list below — only include if you see clear evidence],
  "reasoning": "1-2 sentence explanation of your classification"
}}

Allowed characteristic values:
- agent_retry_loops        (agent has retry/tool-call/reflection loops)
- streaming_responses      (SSE, WebSocket, or generator-based streaming)
- model_loaded_at_request  (model instantiated inside a route/handler)
- long_running_tasks       (tasks expected to run >30 seconds)
- sync_io_in_async         (blocking I/O calls inside async functions)
- no_connection_pooling    (DB/Redis connections opened per-request)
- background_workers       (Celery, RQ, arq, or similar worker queue)
- gpu_required             (explicit CUDA device usage)
- persistent_memory        (vector store, embedding DB, or stateful session store)
- multi_model              (multiple different AI models called in one flow)
- batch_inference          (processes inputs in batches, not one-at-a-time)
- fine_tune_then_serve     (trains a model then also serves it for inference)
- data_validation          (uses Great Expectations, pydantic for data quality)
- distributed_training     (DeepSpeed, FSDP, multi-GPU or multi-node training)
- external_tool_calls      (calls external APIs, search, web, databases as tools)

L1 classification (from dependency parsing): {l1_type} (confidence {l1_confidence:.0%})
Dependency list: {deps}

FILES:
{files}

Remember: return ONLY the JSON object."""


def _pick_files(files: dict[str, str], budget_chars: int = 28_000) -> str:
    """Select the most informative subset of files within char budget."""
    # Score files — same ordering as repo_fetcher relevance
    _PRIO = {
        "train.py": 10, "finetune.py": 10, "fine_tune.py": 10,
        "inference.py": 9, "predict.py": 9, "serve.py": 9,
        "main.py": 8, "app.py": 8, "server.py": 8,
        "celery.py": 8, "celery_app.py": 8, "tasks.py": 8, "worker.py": 8,
        "agent.py": 8, "agents.py": 8, "tools.py": 7,
        "pipeline.py": 7, "dag.py": 7,
        "model.py": 7, "models.py": 6,
        "requirements.txt": 5, "pyproject.toml": 5,
        "README.md": 3,
    }

    def score(path: str) -> int:
        fname = path.split("/")[-1]
        if any(path.startswith(d) for d in _SKIP_DIRS):
            return -1
        if not path.endswith(_INFORMATIVE_SUFFIXES):
            return -1
        return _PRIO.get(fname, 2 if path.endswith(".py") else 1)

    ranked = sorted(
        [(score(p), p) for p in files],
        key=lambda x: -x[0],
    )

    snippets = []
    total = 0
    for s, path in ranked:
        if s < 0:
            continue
        content = files[path]
        # Take up to 4000 chars per file (enough to see patterns)
        excerpt = content[:4000]
        if total + len(excerpt) > budget_chars:
            excerpt = content[:max(0, budget_chars - total)]
        if not excerpt:
            break
        snippets.append(f"### {path}\n{excerpt}")
        total += len(excerpt)
        if total >= budget_chars:
            break

    return "\n\n".join(snippets)


async def analyze_code_characteristics(
    files: dict[str, str],
    l1_type: ProjectType,
    l1_confidence: float,
    dependencies: list[str],
) -> tuple[ProjectType, float, list[str], str]:
    """
    Returns (project_type, confidence, characteristics, reasoning).
    Falls back to (l1_type, l1_confidence, [], "") if no API key.
    """
    if not settings.openai_api_key:
        return l1_type, l1_confidence, [], "AI analysis skipped — no API key configured."

    type_values = [pt.value for pt in ProjectType if pt != ProjectType.UNKNOWN]
    file_text = _pick_files(files)

    if not file_text.strip():
        return l1_type, l1_confidence, [], "No analysable files found."

    prompt = ANALYSIS_PROMPT.format(
        types=json.dumps(type_values),
        l1_type=l1_type.value,
        l1_confidence=l1_confidence,
        deps=", ".join(dependencies[:30]) or "none",
        files=file_text,
    )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        msg = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = msg.choices[0].message.content.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()

        data = json.loads(raw)

        # Validate type
        try:
            ai_type = ProjectType(data.get("project_type", l1_type.value))
        except ValueError:
            ai_type = l1_type

        ai_conf = float(data.get("confidence", l1_confidence))
        ai_conf = max(0.0, min(0.97, ai_conf))

        characteristics = [
            c for c in data.get("characteristics", [])
            if isinstance(c, str)
        ]
        reasoning = data.get("reasoning", "")

        # Blend L1 + L2 confidence:
        # If both agree → boost confidence.  If they disagree → penalise.
        if ai_type == l1_type:
            final_conf = min(0.97, (l1_confidence + ai_conf) / 2 + 0.05)
        else:
            # AI overrides L1 but with reduced confidence
            final_conf = ai_conf * 0.85

        return ai_type, round(final_conf, 2), characteristics, reasoning

    except (json.JSONDecodeError, KeyError, IndexError, Exception) as e:
        log.warning("AI classification failed: %s", e)
        return l1_type, l1_confidence, [], ""
