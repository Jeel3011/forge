"""
Dynamic questionnaire generator.
Passes real code snippets + detected signals to Claude so questions
reference specific things found in the repo, not generic forms.
"""
import json
import re
import logging
from openai import AsyncOpenAI
from app.config import settings
from app.models import ProjectType, Question, QuestionOption

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a senior DevOps engineer specialising in AI/ML infrastructure.
Generate deployment configuration questions that are SPECIFIC to the code provided.
Reference exact things found: package names, retry counts, file names, patterns.
Return ONLY valid JSON — no markdown, no explanations."""

QUESTION_PROMPT = """\
A {project_type} codebase needs deployment configuration questions.

What we found in the code:
- Characteristics: {characteristics}
- Dependencies: {deps}
- Key code snippets:
{snippets}

Generate 5 to 8 questions whose answers will directly set infrastructure values.

Rules:
1. Reference specific things from the code (e.g. "Your agent uses up to {retry_count} retries" if you see a retry count)
2. Each option maps to a CONCRETE config value (worker count, timeout seconds, memory MB, etc.)
3. Do NOT generate generic questions if you can make them specific
4. Include a "cloud_provider" question if not already obvious
5. 3-4 options per question

Return a JSON array:
[
  {{
    "id": "snake_case_unique_id",
    "text": "Question text referencing specifics from their code",
    "context": "One sentence: why this matters and what config value it drives",
    "options": [{{"value": "raw_value", "label": "Human label"}}],
    "allows_custom": false
  }}
]

Only return the JSON array."""


def _extract_snippets(files: dict[str, str], project_type: ProjectType) -> str:
    """Pull the most informative snippets for the questionnaire prompt."""
    _PRIO_FNAMES = {
        ProjectType.AI_AGENT: ["celery.py", "celery_app.py", "tasks.py", "worker.py", "agent.py", "main.py"],
        ProjectType.FINE_TUNING: ["train.py", "finetune.py", "config.py", "main.py"],
        ProjectType.MODEL_SERVING: ["serve.py", "inference.py", "predict.py", "main.py", "app.py"],
        ProjectType.COMPUTER_VISION: ["inference.py", "predict.py", "main.py", "pipeline.py"],
        ProjectType.LLM_APPLICATION: ["main.py", "app.py", "chain.py", "router.py"],
        ProjectType.DATA_PIPELINE: ["dag.py", "pipeline.py", "etl.py", "main.py"],
        ProjectType.CLASSICAL_ML: ["predict.py", "serve.py", "model.py", "main.py"],
        ProjectType.MULTIMODAL: ["main.py", "pipeline.py", "inference.py"],
    }
    priority = _PRIO_FNAMES.get(project_type, ["main.py", "app.py"])

    def _rank(path: str) -> int:
        fname = path.split("/")[-1]
        if "test" in path or "__pycache__" in path:
            return -1
        if fname in priority:
            return priority.index(fname)
        if path.endswith(".py"):
            return len(priority) + 1
        return 99

    ranked = sorted(
        [(r, p) for p, r in {p: _rank(p) for p in files}.items() if r >= 0],
    )

    snippets = []
    budget = 6000
    for _, path in ranked[:8]:
        content = files[path][:1500]
        snippets.append(f"--- {path} ---\n{content}")
        budget -= len(content)
        if budget <= 0:
            break

    return "\n\n".join(snippets)


async def generate_questions(
    project_type: ProjectType,
    characteristics: list[str],
    dependencies: list[str],
    files: dict[str, str],
) -> list[Question]:
    if not settings.openai_api_key:
        return _fallback_questions(project_type, characteristics)

    snippets = _extract_snippets(files, project_type)

    prompt = QUESTION_PROMPT.format(
        project_type=project_type.value.replace("_", " ").title(),
        characteristics=", ".join(characteristics) or "none detected",
        deps=", ".join(dependencies[:25]) or "none",
        snippets=snippets or "(no .py files found)",
        retry_count="N",
    )

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        msg = await client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=2048,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        raw = msg.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()

        data = json.loads(raw)
        questions = []
        for q in data:
            try:
                questions.append(Question(
                    id=q["id"],
                    text=q["text"],
                    context=q["context"],
                    options=[QuestionOption(**o) for o in q["options"]],
                    allows_custom=q.get("allows_custom", False),
                ))
            except (KeyError, TypeError):
                continue

        if questions:
            # Always ensure cloud provider question exists
            if not any(q.id == "cloud_provider" for q in questions):
                questions.append(_cloud_provider_question())
            return questions

    except (json.JSONDecodeError, Exception) as e:
        log.warning("Question generation failed: %s", e)

    return _fallback_questions(project_type, characteristics)


def _cloud_provider_question() -> Question:
    return Question(
        id="cloud_provider",
        text="Which cloud provider will you deploy to?",
        context="Selects the right instance types, storage classes, and IAM config in generated Terraform/K8s.",
        options=[
            QuestionOption(value="aws", label="AWS"),
            QuestionOption(value="gcp", label="GCP"),
            QuestionOption(value="azure", label="Azure"),
            QuestionOption(value="self_hosted", label="Self-hosted / bare metal"),
        ],
    )


def _fallback_questions(project_type: ProjectType, characteristics: list[str]) -> list[Question]:
    """High-quality fallbacks per project type — used when no API key or AI fails."""

    common = [
        Question(
            id="expected_users",
            text="How many concurrent users do you expect at peak?",
            context="Sets replica count, HPA min/max, and Celery worker concurrency.",
            options=[
                QuestionOption(value="small",  label="Under 100"),
                QuestionOption(value="medium", label="100–1,000"),
                QuestionOption(value="large",  label="1,000–10,000"),
                QuestionOption(value="xlarge", label="10,000+"),
            ],
        ),
        _cloud_provider_question(),
    ]

    by_type: dict[ProjectType, list[Question]] = {
        ProjectType.AI_AGENT: [
            Question(
                id="max_task_runtime",
                text="What's the maximum time an agent task should run before being killed?",
                context="Sets Celery task_time_limit. Prevents runaway tasks from blocking all workers.",
                options=[
                    QuestionOption(value="60",   label="1 minute"),
                    QuestionOption(value="300",  label="5 minutes"),
                    QuestionOption(value="1800", label="30 minutes"),
                    QuestionOption(value="3600", label="1 hour"),
                ],
                allows_custom=True,
            ),
            Question(
                id="agent_memory",
                text="Does your agent need to persist memory across separate user sessions?",
                context="Persistent memory requires a vector store (Qdrant/Chroma/Pinecone) in the config.",
                options=[
                    QuestionOption(value="persistent", label="Yes — across sessions"),
                    QuestionOption(value="session",    label="No — session only"),
                    QuestionOption(value="none",       label="No memory needed"),
                ],
            ),
            Question(
                id="concurrent_tasks",
                text="How many agent tasks should run concurrently?",
                context="Sets Celery worker --concurrency. Each task needs its own thread + LLM API budget.",
                options=[
                    QuestionOption(value="2",  label="2 (low cost)"),
                    QuestionOption(value="5",  label="5 (balanced)"),
                    QuestionOption(value="10", label="10 (high throughput)"),
                    QuestionOption(value="20", label="20+ (dedicated infra)"),
                ],
            ),
        ],
        ProjectType.FINE_TUNING: [
            Question(
                id="dataset_size",
                text="How large is your training dataset?",
                context="Determines storage class, EBS volume size, and whether distributed training is needed.",
                options=[
                    QuestionOption(value="small",  label="Under 1 GB"),
                    QuestionOption(value="medium", label="1–10 GB"),
                    QuestionOption(value="large",  label="10–100 GB"),
                    QuestionOption(value="xlarge", label="100 GB+"),
                ],
            ),
            Question(
                id="gpu_type",
                text="What GPU tier do you need for training?",
                context="Directly selects EC2/GCE instance type and hourly cost.",
                options=[
                    QuestionOption(value="t4",   label="T4 16 GB — small models, cheapest"),
                    QuestionOption(value="a10g",  label="A10G 24 GB — 7B–13B models"),
                    QuestionOption(value="a100",  label="A100 40/80 GB — 30B+ models"),
                    QuestionOption(value="h100",  label="H100 80 GB — fastest, most expensive"),
                ],
            ),
            Question(
                id="post_training",
                text="After training, what happens with the checkpoint?",
                context="Determines whether to add a model serving endpoint and storage config.",
                options=[
                    QuestionOption(value="serve", label="Serve it as an API"),
                    QuestionOption(value="store", label="Store checkpoint only (S3/GCS)"),
                    QuestionOption(value="both",  label="Both"),
                ],
            ),
        ],
        ProjectType.MODEL_SERVING: [
            Question(
                id="gpu_needed",
                text="Does your inference require GPU acceleration?",
                context="GPU is ~100× faster but costs 10–50× more. CPU is fine for small models or low traffic.",
                options=[
                    QuestionOption(value="gpu", label="GPU required"),
                    QuestionOption(value="cpu", label="CPU is acceptable"),
                ],
            ),
            Question(
                id="latency_target",
                text="What's your p95 response latency target?",
                context="Drives instance size, autoscaler threshold, and whether to enable request batching.",
                options=[
                    QuestionOption(value="200ms", label="Under 200 ms"),
                    QuestionOption(value="1s",    label="Under 1 second"),
                    QuestionOption(value="5s",    label="Under 5 seconds"),
                    QuestionOption(value="batch", label="Batch — latency not critical"),
                ],
            ),
            Question(
                id="input_type",
                text="Are requests single inputs or batches?",
                context="Batch inputs enable dynamic batching in TorchServe/Triton for higher throughput.",
                options=[
                    QuestionOption(value="single", label="Single request per call"),
                    QuestionOption(value="batch",  label="Batch of inputs per call"),
                    QuestionOption(value="stream", label="Streaming output (tokens/chunks)"),
                ],
            ),
        ],
        ProjectType.COMPUTER_VISION: [
            Question(
                id="inference_mode",
                text="Real-time inference or batch processing?",
                context="Real-time needs a synchronous API + GPU. Batch can use an async queue + cheaper workers.",
                options=[
                    QuestionOption(value="realtime", label="Real-time (sync API)"),
                    QuestionOption(value="batch",    label="Batch (async queue)"),
                    QuestionOption(value="both",     label="Both"),
                ],
            ),
            Question(
                id="input_size",
                text="What's the largest input you expect?",
                context="Sets container memory limits and request timeout.",
                options=[
                    QuestionOption(value="small",  label="Images < 2 MB"),
                    QuestionOption(value="medium", label="Images 2–20 MB or short video"),
                    QuestionOption(value="large",  label="Video > 1 min or 20 MB+"),
                ],
            ),
        ],
        ProjectType.DATA_PIPELINE: [
            Question(
                id="schedule",
                text="How often does the pipeline run?",
                context="Sets the Airflow/Prefect schedule and whether to provision always-on workers.",
                options=[
                    QuestionOption(value="realtime", label="Streaming / continuous"),
                    QuestionOption(value="hourly",   label="Hourly"),
                    QuestionOption(value="daily",    label="Daily"),
                    QuestionOption(value="ondemand", label="On-demand only"),
                ],
            ),
            Question(
                id="data_volume",
                text="How much data does the pipeline process per run?",
                context="Determines whether to use Spark, Dask, or single-node pandas, and storage class.",
                options=[
                    QuestionOption(value="small",  label="Under 1 GB"),
                    QuestionOption(value="medium", label="1–100 GB"),
                    QuestionOption(value="large",  label="100 GB – 1 TB"),
                    QuestionOption(value="xlarge", label="1 TB+ (needs Spark)"),
                ],
            ),
        ],
        ProjectType.LLM_APPLICATION: [
            Question(
                id="session_persistence",
                text="Do users need conversation history between sessions?",
                context="Persistent history requires a Redis or DB session store in the config.",
                options=[
                    QuestionOption(value="persistent", label="Yes — save history to DB"),
                    QuestionOption(value="session",    label="In-memory during session only"),
                    QuestionOption(value="none",       label="Stateless — no history"),
                ],
            ),
            Question(
                id="streaming",
                text="Does your app stream LLM tokens to the client?",
                context="Streaming requires SSE/WebSocket support and affects load balancer timeout settings.",
                options=[
                    QuestionOption(value="streaming", label="Yes — token streaming"),
                    QuestionOption(value="batch",     label="No — wait for full response"),
                ],
            ),
        ],
        ProjectType.CLASSICAL_ML: [
            Question(
                id="retraining",
                text="How often do you retrain the model?",
                context="Frequent retraining needs a pipeline (Airflow/Prefect) and model registry. One-time needs only serving.",
                options=[
                    QuestionOption(value="once",    label="One-time training"),
                    QuestionOption(value="weekly",  label="Weekly retraining"),
                    QuestionOption(value="daily",   label="Daily retraining"),
                    QuestionOption(value="trigger", label="On-demand / triggered"),
                ],
            ),
        ],
    }

    specifics = by_type.get(project_type, [])

    # Add extra questions based on detected characteristics
    if "background_workers" in characteristics and project_type != ProjectType.AI_AGENT:
        specifics.append(Question(
            id="worker_count",
            text="How many background workers do you need?",
            context="Sets Celery --concurrency and replica count.",
            options=[
                QuestionOption(value="2",  label="2 workers"),
                QuestionOption(value="4",  label="4 workers"),
                QuestionOption(value="8",  label="8 workers"),
                QuestionOption(value="16", label="16+ workers"),
            ],
        ))

    if "persistent_memory" in characteristics:
        specifics.append(Question(
            id="vector_store",
            text="Which vector store does your project use (or should use)?",
            context="Determines which vector DB service to include in docker-compose / k8s manifests.",
            options=[
                QuestionOption(value="qdrant",   label="Qdrant"),
                QuestionOption(value="chroma",   label="Chroma"),
                QuestionOption(value="pinecone", label="Pinecone (managed)"),
                QuestionOption(value="pgvector", label="pgvector (PostgreSQL)"),
            ],
        ))

    return specifics + common
