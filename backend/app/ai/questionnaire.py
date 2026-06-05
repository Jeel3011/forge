"""
Dynamic questionnaire generator — uses Claude to create context-aware questions
based on the specific code patterns found in the scanned repo.
"""
import json
import anthropic
from app.config import settings
from app.models import ProjectType, Question, QuestionOption

QUESTION_GENERATION_PROMPT = """\
You are a deployment expert generating configuration questions for a {project_type} codebase.

Detected characteristics: {characteristics}
Detected dependencies: {dependencies}

Generate 5-8 targeted deployment questions. Each question should directly inform
infrastructure decisions (timeouts, workers, storage, GPU needs, scale, etc.).

Return a JSON array of question objects:
[
  {{
    "id": "unique_snake_case_id",
    "text": "Question text (reference specific things found in their code)",
    "context": "Why this matters for their deployment",
    "options": [
      {{"value": "option_value", "label": "Display label"}}
    ],
    "allows_custom": false
  }}
]

Rules:
- Reference specific patterns you see in their characteristics/dependencies
- Options should map to concrete infra decisions (e.g., "30min" → celery time_limit=1800)
- 3-4 options per question max
- Only return valid JSON, no other text.
"""


async def generate_questions(
    project_type: ProjectType,
    characteristics: list[str],
    dependencies: list[str],
) -> list[Question]:
    if not settings.anthropic_api_key:
        return _fallback_questions(project_type)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    msg = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": QUESTION_GENERATION_PROMPT.format(
                project_type=project_type.value,
                characteristics=", ".join(characteristics) or "none detected",
                dependencies=", ".join(dependencies[:20]),
            ),
        }],
    )

    try:
        raw = json.loads(msg.content[0].text)
        return [
            Question(
                id=q["id"],
                text=q["text"],
                context=q["context"],
                options=[QuestionOption(**o) for o in q["options"]],
                allows_custom=q.get("allows_custom", False),
            )
            for q in raw
        ]
    except (json.JSONDecodeError, KeyError, IndexError):
        return _fallback_questions(project_type)


def _fallback_questions(project_type: ProjectType) -> list[Question]:
    common = [
        Question(
            id="expected_users",
            text="How many concurrent users do you expect at peak?",
            context="Determines number of replicas and worker count.",
            options=[
                QuestionOption(value="small", label="Under 100"),
                QuestionOption(value="medium", label="100–1,000"),
                QuestionOption(value="large", label="1,000–10,000"),
                QuestionOption(value="xlarge", label="10,000+"),
            ],
        ),
        Question(
            id="cloud_provider",
            text="Which cloud provider will you deploy to?",
            context="Determines which Terraform modules and instance types to generate.",
            options=[
                QuestionOption(value="aws", label="AWS"),
                QuestionOption(value="gcp", label="GCP"),
                QuestionOption(value="azure", label="Azure"),
                QuestionOption(value="self_hosted", label="Self-hosted / VPS"),
            ],
        ),
    ]

    type_specific: dict[ProjectType, list[Question]] = {
        ProjectType.AI_AGENT: [
            Question(
                id="max_task_runtime",
                text="What's the maximum runtime you want to allow per agent task?",
                context="Sets Celery time_limit to prevent runaway tasks.",
                options=[
                    QuestionOption(value="30", label="30 seconds"),
                    QuestionOption(value="300", label="5 minutes"),
                    QuestionOption(value="1800", label="30 minutes"),
                    QuestionOption(value="custom", label="Custom"),
                ],
                allows_custom=True,
            ),
            Question(
                id="agent_memory",
                text="Does your agent need to remember context across separate user sessions?",
                context="Determines whether to provision a persistent vector store.",
                options=[
                    QuestionOption(value="persistent", label="Persistent memory (across sessions)"),
                    QuestionOption(value="session", label="Session-only memory"),
                    QuestionOption(value="none", label="No memory needed"),
                ],
            ),
        ],
        ProjectType.FINE_TUNING: [
            Question(
                id="dataset_size",
                text="Approximately how large is your training dataset?",
                context="Determines instance storage size and whether distributed training is needed.",
                options=[
                    QuestionOption(value="small", label="Under 1 GB"),
                    QuestionOption(value="medium", label="1–10 GB"),
                    QuestionOption(value="large", label="10–100 GB"),
                    QuestionOption(value="xlarge", label="100 GB+"),
                ],
            ),
            Question(
                id="post_training",
                text="After training completes, what do you need?",
                context="Determines whether to add a model serving endpoint.",
                options=[
                    QuestionOption(value="serve", label="Serve the fine-tuned model"),
                    QuestionOption(value="store", label="Store checkpoint only"),
                    QuestionOption(value="both", label="Both"),
                ],
            ),
        ],
        ProjectType.MODEL_SERVING: [
            Question(
                id="gpu_needed",
                text="Do you need GPU acceleration, or is CPU inference acceptable?",
                context="GPU gives ~100x speedup but costs significantly more.",
                options=[
                    QuestionOption(value="gpu", label="GPU required"),
                    QuestionOption(value="cpu", label="CPU is acceptable"),
                ],
            ),
            Question(
                id="latency_target",
                text="What's your target p95 response latency?",
                context="Sets autoscaler thresholds and instance size.",
                options=[
                    QuestionOption(value="200ms", label="Under 200ms"),
                    QuestionOption(value="1s", label="Under 1 second"),
                    QuestionOption(value="batch", label="Batch processing is fine"),
                ],
            ),
        ],
    }

    return type_specific.get(project_type, []) + common
