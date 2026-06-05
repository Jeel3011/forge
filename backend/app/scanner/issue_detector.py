"""
Issue detector — checks for common deployment anti-patterns.
Each detector returns a list of DetectedIssue.
"""
import ast
import re
from app.models import DetectedIssue, IssueSeverity, ProjectType


def detect_issues(files: dict[str, str], project_type: ProjectType) -> list[DetectedIssue]:
    issues: list[DetectedIssue] = []
    issues.extend(_check_dockerfile(files))
    issues.extend(_check_model_loading(files))
    issues.extend(_check_health_endpoint(files))
    issues.extend(_check_hardcoded_secrets(files))
    issues.extend(_check_sync_io_in_async(files))
    issues.extend(_check_celery_time_limits(files))
    issues.extend(_check_redis_retry(files))
    if project_type in (ProjectType.FINE_TUNING, ProjectType.MODEL_SERVING, ProjectType.COMPUTER_VISION):
        issues.extend(_check_gpu_config(files))
    return issues


def _check_dockerfile(files: dict[str, str]) -> list[DetectedIssue]:
    if "Dockerfile" not in files and "dockerfile" not in {k.lower() for k in files}:
        return [DetectedIssue(
            severity=IssueSeverity.CRITICAL,
            title="No Dockerfile found",
            description="Without a Dockerfile the platform cannot determine your Python version or system dependencies.",
            proposed_fix="Generate a Dockerfile based on detected dependencies and Python version.",
            diff_preview='FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]',
        )]
    return []


def _check_model_loading(files: dict[str, str]) -> list[DetectedIssue]:
    issues = []
    load_patterns = [
        r"(AutoModel|AutoTokenizer|pipeline|load_model|from_pretrained)\s*\(",
        r"torch\.load\s*\(",
        r"joblib\.load\s*\(",
        r"pickle\.load\s*\(",
    ]
    for fname, content in files.items():
        if not fname.endswith(".py"):
            continue
        for pattern in load_patterns:
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line):
                    # Check if it's inside a function that's called per-request
                    if _is_inside_route_handler(content, i):
                        issues.append(DetectedIssue(
                            severity=IssueSeverity.CRITICAL,
                            title="Model loaded on every request",
                            description=f"Model loading detected inside a route handler at {fname}:{i}. This causes 4–8s cold start per request under load.",
                            file=fname,
                            line=i,
                            proposed_fix="Move model loading to application startup using FastAPI lifespan events.",
                            diff_preview="# Move model loading to startup:\nfrom contextlib import asynccontextmanager\n\n@asynccontextmanager\nasync def lifespan(app: FastAPI):\n    app.state.model = load_model()\n    yield\n\napp = FastAPI(lifespan=lifespan)",
                        ))
    return issues


def _is_inside_route_handler(content: str, target_line: int) -> bool:
    route_decorators = {"@app.get", "@app.post", "@app.put", "@app.delete", "@router.get", "@router.post"}
    lines = content.splitlines()
    for i in range(min(target_line - 1, len(lines) - 1), max(target_line - 30, 0), -1):
        stripped = lines[i].strip()
        if any(stripped.startswith(d) for d in route_decorators):
            return True
        if stripped.startswith("def ") or stripped.startswith("async def "):
            break
    return False


def _check_health_endpoint(files: dict[str, str]) -> list[DetectedIssue]:
    for fname, content in files.items():
        if not fname.endswith(".py"):
            continue
        if re.search(r'["\'/]health["\']', content):
            return []
    return [DetectedIssue(
        severity=IssueSeverity.WARNING,
        title="No health check endpoint",
        description="Load balancers and orchestrators need a /health endpoint to detect unhealthy instances.",
        proposed_fix="Add a /health endpoint that returns 200 OK.",
        diff_preview='@app.get("/health")\nasync def health():\n    return {"status": "ok"}',
    )]


def _check_hardcoded_secrets(files: dict[str, str]) -> list[DetectedIssue]:
    issues = []
    secret_patterns = [
        (r'(api_key|secret_key|password|token)\s*=\s*["\'][A-Za-z0-9_\-]{16,}["\']', "hardcoded credential"),
        (r'sk-[A-Za-z0-9]{32,}', "OpenAI API key"),
        (r'sk-ant-[A-Za-z0-9_\-]{32,}', "Anthropic API key"),
    ]
    for fname, content in files.items():
        if not fname.endswith(".py"):
            continue
        for pattern, label in secret_patterns:
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(pattern, line, re.IGNORECASE) and "os.environ" not in line and "os.getenv" not in line:
                    issues.append(DetectedIssue(
                        severity=IssueSeverity.CRITICAL,
                        title=f"Hardcoded {label}",
                        description=f"Secret value found in {fname}:{i}. This is a security risk and prevents key rotation.",
                        file=fname,
                        line=i,
                        proposed_fix="Move to environment variable using os.getenv() and add to .env file.",
                        diff_preview='import os\napi_key = os.getenv("API_KEY")',
                    ))
    return issues


def _check_sync_io_in_async(files: dict[str, str]) -> list[DetectedIssue]:
    issues = []
    sync_io_patterns = [r"open\s*\(", r"requests\.get\s*\(", r"requests\.post\s*\("]
    for fname, content in files.items():
        if not fname.endswith(".py"):
            continue
        lines = content.splitlines()
        in_async = False
        for i, line in enumerate(lines, 1):
            if re.match(r"\s*async def ", line):
                in_async = True
            elif re.match(r"\s*def ", line) and not re.match(r"\s*async def ", line):
                in_async = False
            if in_async:
                for pattern in sync_io_patterns:
                    if re.search(pattern, line) and "await" not in line:
                        issues.append(DetectedIssue(
                            severity=IssueSeverity.WARNING,
                            title="Synchronous I/O inside async handler",
                            description=f"Blocking call in async function at {fname}:{i} will stall the event loop under concurrent requests.",
                            file=fname,
                            line=i,
                            proposed_fix="Replace with async equivalent: aiofiles for file I/O, httpx/aiohttp for HTTP calls.",
                            diff_preview="import aiofiles\nasync with aiofiles.open(path) as f:\n    content = await f.read()",
                        ))
    return issues


def _check_celery_time_limits(files: dict[str, str]) -> list[DetectedIssue]:
    for fname, content in files.items():
        if "celery" in content.lower() and "time_limit" not in content and "soft_time_limit" not in content:
            return [DetectedIssue(
                severity=IssueSeverity.WARNING,
                title="Celery tasks without time limits",
                description="Celery workers without time limits can run indefinitely, consuming all worker slots.",
                proposed_fix="Set time_limit and soft_time_limit on your Celery app or individual tasks.",
                diff_preview='app.conf.task_time_limit = 1800  # 30 minutes\napp.conf.task_soft_time_limit = 1700',
            )]
    return []


def _check_redis_retry(files: dict[str, str]) -> list[DetectedIssue]:
    for fname, content in files.items():
        if "redis" in content.lower() and "retry" not in content.lower() and "retry_on_error" not in content.lower():
            return [DetectedIssue(
                severity=IssueSeverity.WARNING,
                title="Redis connection without retry logic",
                description="Redis connections without retry logic will fail permanently on first transient error.",
                proposed_fix="Add retry_on_error and socket_connect_timeout to your Redis connection.",
                diff_preview='redis_client = Redis(\n    host=host,\n    retry_on_error=[ConnectionError, TimeoutError],\n    socket_connect_timeout=5,\n    socket_keepalive=True,\n)',
            )]
    return []


def _check_gpu_config(files: dict[str, str]) -> list[DetectedIssue]:
    for fname, content in files.items():
        if re.search(r"\.cuda\(\)|\.to\(['\"]cuda['\"]|device\s*=\s*['\"]cuda", content):
            dockerfile_content = files.get("Dockerfile", "")
            if "nvidia" not in dockerfile_content.lower() and "cuda" not in dockerfile_content.lower():
                return [DetectedIssue(
                    severity=IssueSeverity.CRITICAL,
                    title="GPU code without GPU-enabled container",
                    description="CUDA calls detected but no GPU base image configured. Will silently fall back to CPU (~100x slower).",
                    proposed_fix="Use an NVIDIA CUDA base image in your Dockerfile.",
                    diff_preview='FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04',
                )]
    return []
