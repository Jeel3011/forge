"""
Config generator — takes scan result + questionnaire answers and renders
infrastructure config files using Jinja2 templates.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.models import GeneratedConfig, GenerateRequest, ProjectType

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def generate_configs(request: GenerateRequest) -> GeneratedConfig:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    context = _build_template_context(request)
    files: dict[str, str] = {}

    if request.output_tier == "docker_compose":
        files["docker-compose.yml"] = _render(env, "docker_compose/docker-compose.yml.j2", context)
        if "Dockerfile" not in {f for f in request.scan_result.detected_dependencies}:
            files["Dockerfile"] = _render(env, "docker_compose/Dockerfile.j2", context)
        files[".env.example"] = _render(env, "docker_compose/env.example.j2", context)

    elif request.output_tier == "kubernetes":
        for tmpl in ["deployment.yaml", "service.yaml", "hpa.yaml", "configmap.yaml"]:
            files[tmpl] = _render(env, f"kubernetes/{tmpl}.j2", context)

    guide = _render(env, "deployment_guide.md.j2", context)
    return GeneratedConfig(tier=request.output_tier, files=files, deployment_guide=guide)


def _render(env: Environment, template_name: str, context: dict) -> str:
    try:
        return env.get_template(template_name).render(**context)
    except Exception:
        return f"# Template {template_name} not yet implemented\n"


def _build_template_context(request: GenerateRequest) -> dict:
    answers = request.questionnaire_answers
    scan = request.scan_result

    workers = _workers_from_scale(answers.get("expected_users", "small"))
    memory_limit = _memory_from_project_type(scan.project_type)
    needs_gpu = answers.get("gpu_needed") == "gpu" or "gpu_required" in scan.detected_characteristics
    needs_celery = "background_workers" in scan.detected_characteristics or scan.project_type == ProjectType.AI_AGENT
    needs_redis = needs_celery or "celery" in scan.detected_dependencies
    needs_qdrant = "persistent_memory" in scan.detected_characteristics and answers.get("agent_memory") == "persistent"
    celery_time_limit = int(answers.get("max_task_runtime", "1800"))

    return {
        "project_type": scan.project_type.value,
        "detected_deps": scan.detected_dependencies,
        "workers": workers,
        "memory_limit": memory_limit,
        "needs_gpu": needs_gpu,
        "needs_celery": needs_celery,
        "needs_redis": needs_redis,
        "needs_qdrant": needs_qdrant,
        "celery_time_limit": celery_time_limit,
        "cloud_provider": answers.get("cloud_provider", "aws"),
        "scale": answers.get("expected_users", "small"),
        "answers": answers,
        "scan": scan,
    }


def _workers_from_scale(scale: str) -> int:
    return {"small": 2, "medium": 4, "large": 8, "xlarge": 16}.get(scale, 2)


def _memory_from_project_type(project_type: ProjectType) -> str:
    return {
        ProjectType.FINE_TUNING: "16G",
        ProjectType.MODEL_SERVING: "8G",
        ProjectType.COMPUTER_VISION: "4G",
        ProjectType.AI_AGENT: "2G",
        ProjectType.LLM_APPLICATION: "1G",
    }.get(project_type, "512M")
