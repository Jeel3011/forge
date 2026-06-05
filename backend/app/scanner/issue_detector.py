"""
Issue detector — 15 deterministic checks against fetched repo files.

Design rules:
- Each check is independent and returns [] or a list of DetectedIssue.
- AST parsing is used where regex would produce false positives.
- Test files, migration files, and __pycache__ are skipped.
- Each issue has a stable `issue_id` for frontend dedup tracking.
- No issue is raised more than once for the same root cause.
"""
import ast
import re
import hashlib
from app.models import DetectedIssue, IssueSeverity, ProjectType

# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_test_file(path: str) -> bool:
    parts = path.replace("\\", "/").split("/")
    fname = parts[-1]
    return (
        fname.startswith("test_")
        or fname.endswith("_test.py")
        or "tests/" in path
        or "test/" in path
        or "__pycache__" in path
        or "migrations/" in path
        or "alembic/" in path
    )


def _py_files(files: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in files.items() if k.endswith(".py") and not _is_test_file(k)}


def _make_id(*parts: str) -> str:
    return hashlib.md5(":".join(parts).encode()).hexdigest()[:8]


def _safe_parse(content: str):
    """Return AST tree or None if unparseable."""
    try:
        return ast.parse(content)
    except SyntaxError:
        return None


# ── Route decorator detection (AST) ──────────────────────────────────────────

_ROUTE_DECO_NAMES = {
    "get", "post", "put", "patch", "delete", "route", "api_route",
    "websocket",
}

def _route_handler_lines(tree) -> set[int]:
    """Return set of line numbers that are inside FastAPI/Flask route functions."""
    result: set[int] = set()
    if tree is None:
        return result
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        is_route = False
        for deco in node.decorator_list:
            if isinstance(deco, ast.Attribute) and deco.attr in _ROUTE_DECO_NAMES:
                is_route = True
            elif isinstance(deco, ast.Call):
                func = deco.func
                if isinstance(func, ast.Attribute) and func.attr in _ROUTE_DECO_NAMES:
                    is_route = True
        if is_route:
            for child in ast.walk(node):
                if hasattr(child, "lineno"):
                    result.add(child.lineno)
    return result


# ── Individual detectors ──────────────────────────────────────────────────────

def _check_dockerfile(files: dict[str, str]) -> list[DetectedIssue]:
    has = any(p.lower().endswith("dockerfile") or p.lower() == "dockerfile"
              for p in files)
    if has:
        return []
    return [DetectedIssue(
        issue_id="no_dockerfile",
        severity=IssueSeverity.CRITICAL,
        title="No Dockerfile found",
        description="Without a Dockerfile the deployment platform cannot pin your Python version, system dependencies, or build steps. Every cloud deployment will behave differently.",
        proposed_fix="Add a Dockerfile using a slim Python base image.",
        diff_preview=(
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "RUN apt-get update && apt-get install -y --no-install-recommends curl \\\n"
            "    && rm -rf /var/lib/apt/lists/*\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            'CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]'
        ),
    )]


def _check_model_loading_in_request(files: dict[str, str]) -> list[DetectedIssue]:
    """Uses AST to detect model loading calls inside route handler bodies.
    Groups all hits per file into a single issue to avoid duplicate spam."""
    LOAD_CALLS = {
        "from_pretrained", "load_model", "torch.load",
        "joblib.load", "pickle.load", "onnxruntime.InferenceSession",
        "AutoModel.from_pretrained", "AutoTokenizer.from_pretrained",
        "pipeline",
    }
    # Collect all (fname, lineno, call) hits grouped by file
    hits_by_file: dict[str, list[tuple[int, str]]] = {}

    for fname, content in _py_files(files).items():
        tree = _safe_parse(content)
        if tree is None:
            continue
        route_lines = _route_handler_lines(tree)
        if not route_lines:
            continue
        lines = content.splitlines()
        seen_lines: set[int] = set()
        for lineno in sorted(route_lines):
            if lineno - 1 >= len(lines) or lineno in seen_lines:
                continue
            line_text = lines[lineno - 1]
            for call in LOAD_CALLS:
                if call.split(".")[-1] in line_text:
                    hits_by_file.setdefault(fname, []).append((lineno, call))
                    seen_lines.add(lineno)
                    break

    issues = []
    for fname, hits in hits_by_file.items():
        first_line, first_call = hits[0]
        locations = ", ".join(f"line {ln}" for ln, _ in hits[:5])
        if len(hits) > 5:
            locations += f" (+{len(hits) - 5} more)"
        iid = _make_id("model_in_request", fname)
        issues.append(DetectedIssue(
            issue_id=iid,
            severity=IssueSeverity.CRITICAL,
            title=f"Model loaded on every request ({len(hits)} location{'s' if len(hits) > 1 else ''})",
            description=(
                f"Model loading calls found inside route handlers in `{fname}` at {locations}. "
                "This causes 4–8 s cold start on every request and will OOM under concurrent load."
            ),
            file=fname,
            line=first_line,
            proposed_fix="Move model loading to application startup using a FastAPI lifespan event. The model is loaded once, held in app.state, and reused across all requests.",
            diff_preview=(
                "from contextlib import asynccontextmanager\n\n"
                "@asynccontextmanager\nasync def lifespan(app: FastAPI):\n"
                "    app.state.model = AutoModel.from_pretrained(...)\n"
                "    yield\n\n"
                "app = FastAPI(lifespan=lifespan)\n\n"
                "# In your route:\n"
                "model = request.app.state.model"
            ),
        ))
    return issues


def _check_health_endpoint(files: dict[str, str]) -> list[DetectedIssue]:
    for content in _py_files(files).values():
        if re.search(r'''["'/]health["'/]''', content):
            return []
    return [DetectedIssue(
        issue_id="no_health_endpoint",
        severity=IssueSeverity.WARNING,
        title="No /health endpoint",
        description="Load balancers (ALB, Nginx, k8s liveness probes) require a /health route that returns 200. Without it they cannot detect crashed instances and will keep routing traffic to them.",
        proposed_fix="Add a GET /health endpoint to your FastAPI app.",
        diff_preview='@app.get("/health")\nasync def health():\n    return {"status": "ok"}',
    )]


def _check_hardcoded_secrets(files: dict[str, str]) -> list[DetectedIssue]:
    SECRET_PATTERNS = [
        (re.compile(r'sk-[A-Za-z0-9]{32,}'),                    "OpenAI API key"),
        (re.compile(r'sk-ant-[A-Za-z0-9_\-]{32,}'),             "Anthropic API key"),
        (re.compile(r'AIza[0-9A-Za-z_\-]{35}'),                 "Google API key"),
        (re.compile(r'AKIA[0-9A-Z]{16}'),                       "AWS Access Key"),
        (re.compile(r'gh[pousr]_[A-Za-z0-9]{36,}'),             "GitHub token"),
        (re.compile(
            r'(?:api_key|secret_key|password|token|passwd|pwd)\s*=\s*["\'][A-Za-z0-9_\-!@#$%^&*]{12,}["\']',
            re.I
        ), "hardcoded credential"),
    ]
    issues = []
    seen: set[str] = set()

    for fname, content in _py_files(files).items():
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments and env-var reads
            if stripped.startswith("#"):
                continue
            if "os.environ" in line or "os.getenv" in line or "getenv" in line:
                continue
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(line):
                    iid = _make_id("secret", fname, str(i))
                    if iid in seen:
                        continue
                    seen.add(iid)
                    issues.append(DetectedIssue(
                        issue_id=iid,
                        severity=IssueSeverity.CRITICAL,
                        title=f"Hardcoded {label}",
                        description=(
                            f"A {label} appears to be hardcoded in {fname}:{i}. "
                            "This leaks credentials in your git history and prevents key rotation."
                        ),
                        file=fname,
                        line=i,
                        proposed_fix="Load the secret from an environment variable.",
                        diff_preview='import os\n# Before: api_key = "sk-..."\napi_key = os.getenv("API_KEY")  # set in .env',
                    ))
    return issues


def _check_sync_io_in_async(files: dict[str, str]) -> list[DetectedIssue]:
    """AST-based: find sync blocking calls inside async functions."""
    BLOCKING = {
        # (module_attr, call_name)
        ("requests", "get"), ("requests", "post"), ("requests", "put"),
        ("requests", "delete"), ("requests", "request"),
        ("urllib", "urlopen"), ("urllib.request", "urlopen"),
        ("time", "sleep"),
    }
    BLOCKING_NAMES = {"open"}  # builtin open() without aiofiles

    issues = []
    seen: set[str] = set()

    for fname, content in _py_files(files).items():
        tree = _safe_parse(content)
        if tree is None:
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            for child in ast.walk(node):
                if not isinstance(child, ast.Call):
                    continue
                func = child.func
                lineno = getattr(child, "lineno", 0)

                # builtin open()
                if isinstance(func, ast.Name) and func.id in BLOCKING_NAMES:
                    iid = _make_id("sync_io", fname, str(lineno))
                    if iid not in seen:
                        seen.add(iid)
                        issues.append(DetectedIssue(
                            issue_id=iid,
                            severity=IssueSeverity.WARNING,
                            title="Synchronous file I/O in async handler",
                            description=f"Blocking `open()` call in async function at {fname}:{lineno} will freeze the event loop under concurrent requests.",
                            file=fname, line=lineno,
                            proposed_fix="Replace with aiofiles.",
                            diff_preview="import aiofiles\nasync with aiofiles.open(path) as f:\n    data = await f.read()",
                        ))

                # requests.get / time.sleep etc.
                if isinstance(func, ast.Attribute):
                    obj = func.value
                    if isinstance(obj, ast.Name):
                        pair = (obj.id, func.attr)
                        if pair in BLOCKING:
                            iid = _make_id("sync_io", fname, str(lineno))
                            if iid not in seen:
                                seen.add(iid)
                                issues.append(DetectedIssue(
                                    issue_id=iid,
                                    severity=IssueSeverity.WARNING,
                                    title=f"Blocking `{obj.id}.{func.attr}` in async handler",
                                    description=f"`{obj.id}.{func.attr}()` at {fname}:{lineno} blocks the asyncio event loop. Under concurrency every other request waits.",
                                    file=fname, line=lineno,
                                    proposed_fix="Use httpx.AsyncClient for HTTP, asyncio.sleep for delays.",
                                    diff_preview="import httpx\nasync with httpx.AsyncClient() as client:\n    resp = await client.get(url)",
                                ))
    return issues


def _check_no_rate_limiting(files: dict[str, str]) -> list[DetectedIssue]:
    has_rate_limit = any(
        "slowapi" in c or "ratelimit" in c.lower() or "rate_limit" in c.lower()
        or "limiter" in c.lower()
        for c in files.values()
    )
    has_public_api = any(
        re.search(r'@(?:app|router)\.(get|post|put|delete)', c)
        for c in _py_files(files).values()
    )
    if has_rate_limit or not has_public_api:
        return []
    return [DetectedIssue(
        issue_id="no_rate_limiting",
        severity=IssueSeverity.WARNING,
        title="No rate limiting on API",
        description="A public API without rate limiting can be exhausted by a single aggressive client, taking down the service for all users.",
        proposed_fix="Add slowapi (FastAPI) or flask-limiter (Flask) rate limiting.",
        diff_preview=(
            "from slowapi import Limiter\nfrom slowapi.util import get_remote_address\n\n"
            "limiter = Limiter(key_func=get_remote_address)\n"
            'app.state.limiter = limiter\n\n@app.get("/predict")\n'
            '@limiter.limit("10/minute")\nasync def predict(request: Request): ...'
        ),
    )]


def _check_no_graceful_shutdown(files: dict[str, str]) -> list[DetectedIssue]:
    has_lifespan = any(
        "lifespan" in c or "on_event" in c or "shutdown" in c.lower()
        for c in _py_files(files).values()
    )
    has_fastapi = any("fastapi" in c.lower() for c in files.values())
    if has_lifespan or not has_fastapi:
        return []
    return [DetectedIssue(
        issue_id="no_graceful_shutdown",
        severity=IssueSeverity.WARNING,
        title="No graceful shutdown handler",
        description="Kubernetes rolling deploys send SIGTERM before killing a pod. Without a shutdown handler, in-flight requests are dropped immediately.",
        proposed_fix="Add a lifespan context manager that awaits in-flight requests.",
        diff_preview=(
            "from contextlib import asynccontextmanager\n\n"
            "@asynccontextmanager\nasync def lifespan(app: FastAPI):\n"
            "    yield  # startup\n"
            "    # shutdown: flush queues, close DB pools, etc.\n"
            "    await db_pool.close()\n\n"
            "app = FastAPI(lifespan=lifespan)"
        ),
    )]


def _check_celery_config(files: dict[str, str]) -> list[DetectedIssue]:
    all_content = "\n".join(files.values()).lower()
    if "celery" not in all_content:
        return []
    issues = []
    if "time_limit" not in all_content and "soft_time_limit" not in all_content:
        issues.append(DetectedIssue(
            issue_id="celery_no_time_limit",
            severity=IssueSeverity.WARNING,
            title="Celery tasks without time limits",
            description="Tasks without time limits can run indefinitely, starving all workers and requiring a full restart to recover.",
            proposed_fix="Set task_time_limit and task_soft_time_limit on the Celery app config.",
            diff_preview="app.conf.task_time_limit = 1800\napp.conf.task_soft_time_limit = 1740",
        ))
    if "task_acks_late" not in all_content:
        issues.append(DetectedIssue(
            issue_id="celery_no_acks_late",
            severity=IssueSeverity.SUGGESTION,
            title="Celery not configured for late acknowledgement",
            description="With early ack (default), tasks are lost if a worker crashes mid-execution. Late ack requeues them automatically.",
            proposed_fix="Enable task_acks_late and task_reject_on_worker_lost.",
            diff_preview="app.conf.task_acks_late = True\napp.conf.task_reject_on_worker_lost = True",
        ))
    return issues


def _check_redis_config(files: dict[str, str]) -> list[DetectedIssue]:
    py = _py_files(files)
    has_redis = any("redis" in c.lower() for c in py.values())
    if not has_redis:
        return []
    issues = []
    all_py = "\n".join(py.values()).lower()
    if "retry_on_error" not in all_py and "retry_on_timeout" not in all_py:
        issues.append(DetectedIssue(
            issue_id="redis_no_retry",
            severity=IssueSeverity.WARNING,
            title="Redis connection without retry logic",
            description="Redis connections without retry will fail permanently on the first transient network error or Redis restart, taking down dependent services.",
            proposed_fix="Add retry_on_error and socket keepalive to your Redis connection.",
            diff_preview=(
                "from redis import Redis\nfrom redis.exceptions import ConnectionError, TimeoutError\n\n"
                "redis_client = Redis(\n"
                "    host=host, port=6379,\n"
                "    retry_on_error=[ConnectionError, TimeoutError],\n"
                "    socket_connect_timeout=5,\n"
                "    socket_keepalive=True,\n"
                "    decode_responses=True,\n"
                ")"
            ),
        ))
    if "maxmemory" not in "\n".join(files.values()).lower():
        issues.append(DetectedIssue(
            issue_id="redis_no_maxmemory",
            severity=IssueSeverity.SUGGESTION,
            title="Redis maxmemory policy not configured",
            description="Without maxmemory-policy Redis will grow unboundedly until the container OOMs.",
            proposed_fix="Set maxmemory and maxmemory-policy in redis.conf or docker-compose.",
            diff_preview="command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru",
        ))
    return issues


def _check_gpu_config(files: dict[str, str]) -> list[DetectedIssue]:
    has_cuda = any(
        re.search(r'\.cuda\(\)|\.to\(["\']cuda["\']|device\s*=\s*["\']cuda|torch\.device\(["\']cuda', c)
        for c in _py_files(files).values()
    )
    if not has_cuda:
        return []
    dockerfile = next((v for k, v in files.items() if "dockerfile" in k.lower()), "")
    if "nvidia" in dockerfile.lower() or "cuda" in dockerfile.lower():
        return []
    return [DetectedIssue(
        issue_id="gpu_no_cuda_image",
        severity=IssueSeverity.CRITICAL,
        title="CUDA code without GPU base image",
        description="CUDA calls detected but your Dockerfile doesn't use an NVIDIA base image. PyTorch will silently fall back to CPU — approximately 100× slower.",
        proposed_fix="Use an official NVIDIA CUDA base image.",
        diff_preview="FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04\n# then install python + your deps",
    )]


def _check_db_connection_pooling(files: dict[str, str]) -> list[DetectedIssue]:
    py = _py_files(files)
    all_py = "\n".join(py.values())
    has_db = any(k in all_py.lower() for k in ["sqlalchemy", "psycopg2", "asyncpg", "pymysql"])
    if not has_db:
        return []
    has_pool = bool(re.search(
        r"pool_size|connection_pool|create_engine|NullPool|QueuePool|asyncpg\.create_pool",
        all_py,
    ))
    if has_pool:
        return []
    return [DetectedIssue(
        issue_id="no_db_pool",
        severity=IssueSeverity.WARNING,
        title="No database connection pooling",
        description="Opening a new DB connection per request adds 20–100 ms latency and will exhaust max_connections under concurrent load.",
        proposed_fix="Use SQLAlchemy's create_engine with pool_size, or asyncpg.create_pool.",
        diff_preview=(
            "from sqlalchemy.ext.asyncio import create_async_engine\n\n"
            "engine = create_async_engine(\n"
            '    DATABASE_URL,\n    pool_size=10,\n    max_overflow=20,\n'
            "    pool_pre_ping=True,\n)"
        ),
    )]


def _check_missing_env_gitignore(files: dict[str, str]) -> list[DetectedIssue]:
    gitignore = files.get(".gitignore", "")
    has_env_file = any(k.endswith(".env") or k == ".env" for k in files)
    env_ignored = ".env" in gitignore
    if not has_env_file or env_ignored:
        return []
    return [DetectedIssue(
        issue_id="env_not_gitignored",
        severity=IssueSeverity.CRITICAL,
        title=".env file not in .gitignore",
        description="A .env file exists in the repo but .gitignore doesn't exclude it. If committed, your secrets become public in the git history.",
        proposed_fix="Add .env to .gitignore immediately.",
        diff_preview="# .gitignore\n.env\n.env.*\n!.env.example",
    )]


def _check_missing_requirements(files: dict[str, str]) -> list[DetectedIssue]:
    manifest_files = {
        "requirements.txt", "pyproject.toml", "setup.py",
        "setup.cfg", "Pipfile", "environment.yml",
    }
    has_manifest = any(
        any(p.endswith(m) or p == m for p in files)
        for m in manifest_files
    )
    has_py = any(k.endswith(".py") for k in files)
    if has_manifest or not has_py:
        return []
    return [DetectedIssue(
        issue_id="no_requirements",
        severity=IssueSeverity.CRITICAL,
        title="No dependency manifest found",
        description="No requirements.txt, pyproject.toml, or setup.py detected. The container build will have no dependencies and will fail at runtime.",
        proposed_fix="Add a requirements.txt and pin your dependency versions.",
        diff_preview="# requirements.txt\nfastapi==0.111.0\nuvicorn[standard]==0.29.0\n# pin everything for reproducible builds",
    )]


def _check_unpinned_deps(files: dict[str, str]) -> list[DetectedIssue]:
    req = files.get("requirements.txt", "")
    if not req:
        return []
    unpinned = []
    for line in req.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", "-")):
            continue
        if not re.search(r"[=<>!]", line) and "@" not in line:
            name = re.split(r"[\s\[]", line)[0]
            unpinned.append(name)
    if len(unpinned) < 3:
        return []
    return [DetectedIssue(
        issue_id="unpinned_deps",
        severity=IssueSeverity.WARNING,
        title=f"{len(unpinned)} unpinned dependencies",
        description=f"Packages without version pins ({', '.join(unpinned[:5])}{'…' if len(unpinned) > 5 else ''}) will install latest on every build, causing non-reproducible deployments and silent breakage.",
        proposed_fix="Pin all dependencies with `pip freeze > requirements.txt` or use `pip-compile`.",
        diff_preview="# Run: pip freeze > requirements.txt\n# Or: pip install pip-tools && pip-compile",
    )]


def _check_no_logging(files: dict[str, str]) -> list[DetectedIssue]:
    py = _py_files(files)
    if not py:
        return []
    has_logging = any(
        "import logging" in c or "structlog" in c or "loguru" in c
        for c in py.values()
    )
    if has_logging:
        return []
    return [DetectedIssue(
        issue_id="no_logging",
        severity=IssueSeverity.SUGGESTION,
        title="No structured logging detected",
        description="Without logging, debugging production issues requires guesswork. Structured logs (JSON) are indexable by Datadog, CloudWatch, etc.",
        proposed_fix="Add Python logging or structlog.",
        diff_preview=(
            "import logging\nlogging.basicConfig(\n"
            "    level=logging.INFO,\n"
            '    format=\'{"time":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}\'\n'
            ")"
        ),
    )]


def _check_no_dockerfile_healthcheck(files: dict[str, str]) -> list[DetectedIssue]:
    dockerfile = next((v for k, v in files.items() if "dockerfile" in k.lower()), None)
    if dockerfile is None:
        return []
    if "HEALTHCHECK" in dockerfile:
        return []
    return [DetectedIssue(
        issue_id="no_dockerfile_healthcheck",
        severity=IssueSeverity.SUGGESTION,
        title="Dockerfile missing HEALTHCHECK instruction",
        description="Without a HEALTHCHECK Docker and k8s cannot detect when your container is running but unhealthy (e.g. stuck model load).",
        proposed_fix="Add a HEALTHCHECK instruction to your Dockerfile.",
        diff_preview=(
            "HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \\\n"
            "    CMD curl -f http://localhost:8000/health || exit 1"
        ),
    )]


def _check_missing_main_guard(files: dict[str, str]) -> list[DetectedIssue]:
    """Detect scripts that run code at import time without __main__ guard."""
    issues = []
    seen: set[str] = set()
    TRAINING_PATTERNS = re.compile(r"\.(fit|train|run)\s*\(|Trainer\(")

    for fname, content in _py_files(files).items():
        if "__main__" in content:
            continue
        if not TRAINING_PATTERNS.search(content):
            continue
        # Check it's a top-level script (has if/for outside functions)
        tree = _safe_parse(content)
        if tree is None:
            continue
        top_level_exec = any(
            isinstance(n, (ast.Expr, ast.Assign, ast.For, ast.If))
            and not isinstance(n, ast.FunctionDef)
            for n in ast.walk(tree)
            if isinstance(n, ast.Module)
            # walk Module children directly
            for n in getattr(tree, "body", [])
            if isinstance(n, (ast.Expr, ast.Assign))
        )
        if top_level_exec:
            iid = _make_id("no_main_guard", fname)
            if iid not in seen:
                seen.add(iid)
                issues.append(DetectedIssue(
                    issue_id=iid,
                    severity=IssueSeverity.WARNING,
                    title="Training code runs at import time",
                    description=f"{fname} appears to execute training code at the top level without `if __name__ == '__main__':`. Importing this module (e.g. by a web server) will trigger training.",
                    file=fname,
                    proposed_fix="Wrap top-level execution in `if __name__ == '__main__': main()`.",
                    diff_preview='if __name__ == "__main__":\n    train()',
                ))
    return issues


# ── Public entry point ────────────────────────────────────────────────────────

def detect_issues(files: dict[str, str], project_type: ProjectType) -> list[DetectedIssue]:
    """Run all detectors. Order = roughly severity (critical first)."""
    issues: list[DetectedIssue] = []

    issues += _check_missing_requirements(files)
    issues += _check_dockerfile(files)
    issues += _check_missing_env_gitignore(files)
    issues += _check_hardcoded_secrets(files)
    issues += _check_model_loading_in_request(files)
    issues += _check_health_endpoint(files)
    issues += _check_unpinned_deps(files)
    issues += _check_sync_io_in_async(files)
    issues += _check_no_graceful_shutdown(files)
    issues += _check_no_rate_limiting(files)
    issues += _check_celery_config(files)
    issues += _check_redis_config(files)
    issues += _check_db_connection_pooling(files)
    issues += _check_no_dockerfile_healthcheck(files)
    issues += _check_no_logging(files)

    # GPU check only for relevant project types
    if project_type in (
        ProjectType.FINE_TUNING, ProjectType.MODEL_SERVING,
        ProjectType.COMPUTER_VISION, ProjectType.MULTIMODAL,
    ):
        issues += _check_gpu_config(files)

    # Training main guard only for fine-tuning
    if project_type == ProjectType.FINE_TUNING:
        issues += _check_missing_main_guard(files)

    # Deduplicate by issue_id (keeps first occurrence)
    seen_ids: set[str] = set()
    deduped = []
    for issue in issues:
        if issue.issue_id not in seen_ids:
            seen_ids.add(issue.issue_id)
            deduped.append(issue)

    return deduped
