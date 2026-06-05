"""
Repo fetcher — fetches the most relevant files from a GitHub repo.

Strategy:
1. Pull the full recursive tree in one API call.
2. Score every file by relevance (entry point, config, known patterns).
3. Fetch top-N files in parallel using asyncio.gather.
4. Prioritise: manifest files > entry points > src/**/*.py > root .py files
"""
import re
import base64
import asyncio
import httpx
from app.config import settings

MAX_FILES        = 50
MAX_FILE_BYTES   = 120_000   # 120 KB — skip binary/generated blobs
MAX_TOTAL_CHARS  = 400_000   # total budget across all files

# Highest-priority filenames (fetched regardless of position in tree)
PRIORITY_EXACT: list[str] = [
    "requirements.txt", "requirements-dev.txt", "requirements_dev.txt",
    "requirements-prod.txt", "requirements_prod.txt",
    "pyproject.toml", "setup.py", "setup.cfg", "Pipfile",
    "environment.yml", "environment.yaml", "conda.yml",
    "package.json",
    "Dockerfile", "dockerfile", "Dockerfile.prod", "Dockerfile.dev",
    "docker-compose.yml", "docker-compose.yaml",
    "docker-compose.prod.yml", "docker-compose.prod.yaml",
    ".env.example", ".env.sample", "env.example",
    "README.md", "README.rst", "readme.md",
]

# Patterns scored for relevance (higher = fetched first)
RELEVANCE_PATTERNS: list[tuple[re.Pattern, int]] = [
    # Training / fine-tuning
    (re.compile(r"(train|finetune|fine_tune|pretrain|sft)[^/]*\.py$", re.I), 10),
    # Inference / serving
    (re.compile(r"(inference|predict|serve|infer)[^/]*\.py$", re.I), 10),
    # Entry points
    (re.compile(r"^(main|app|server|run|start|wsgi|asgi)[^/]*\.py$", re.I), 9),
    # Celery / workers
    (re.compile(r"(celery|worker|task)[^/]*\.py$", re.I), 9),
    # Agents / tools
    (re.compile(r"(agent|tool|chain|graph|crew)[^/]*\.py$", re.I), 8),
    # Pipeline / DAG
    (re.compile(r"(pipeline|dag|flow|etl)[^/]*\.py$", re.I), 8),
    # Models
    (re.compile(r"(model|net|network|backbone)[^/]*\.py$", re.I), 7),
    # Config
    (re.compile(r"(config|settings|conf)[^/]*\.py$", re.I), 6),
    # API routes
    (re.compile(r"(route|api|endpoint|view)[^/]*\.py$", re.I), 6),
    # DB / storage
    (re.compile(r"(database|db|store|repository)[^/]*\.py$", re.I), 5),
    # Any .py in src/ or app/ or backend/
    (re.compile(r"^(src|app|backend|core|lib)/[^/]+\.py$", re.I), 4),
    # Any other .py
    (re.compile(r"\.py$"), 1),
]

# Never fetch these (binary, generated, vendored)
SKIP_PATTERNS = re.compile(
    r"\.(png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|otf|"
    r"pyc|pyo|so|dylib|dll|exe|bin|pkl|pt|pth|ckpt|safetensors|"
    r"lock|sum|mod|min\.js|min\.css|map)$",
    re.I,
)
SKIP_DIRS = re.compile(
    r"^(node_modules|\.git|__pycache__|\.venv|venv|env|"
    r"\.mypy_cache|\.pytest_cache|dist|build|\.next|\.nuxt)/",
    re.I,
)


def parse_github_url(url: str) -> tuple[str, str]:
    """Accept https://github.com/owner/repo, github.com/owner/repo, owner/repo."""
    url = url.strip().rstrip("/")
    # Full URL
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    # Without scheme
    m = re.match(r"(?:github\.com/)?([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    raise ValueError(
        f"Cannot parse GitHub URL: '{url}'. "
        "Expected format: https://github.com/owner/repo"
    )


def _score_path(path: str) -> int:
    fname = path.split("/")[-1]
    # Exact priority files score highest
    if fname in PRIORITY_EXACT or path in PRIORITY_EXACT:
        return 100
    if SKIP_PATTERNS.search(path):
        return -1
    if SKIP_DIRS.search(path):
        return -1
    for pattern, score in RELEVANCE_PATTERNS:
        if pattern.search(path):
            return score
    return 0


async def _fetch_one(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    path: str,
    headers: dict,
) -> tuple[str, str] | None:
    try:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
            timeout=20,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return path, content
    except Exception:
        pass
    return None


async def fetch_repo_files(repo_url: str) -> dict[str, str]:
    owner, repo = parse_github_url(repo_url)

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    # ── Step 1: get full tree ──────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=30) as client:
        tree_resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1",
            headers=headers,
        )
        if tree_resp.status_code == 409:  # empty repo
            return {}
        tree_resp.raise_for_status()
        tree_data = tree_resp.json()

    if tree_data.get("truncated"):
        # Very large repo — fall back to non-recursive root listing
        async with httpx.AsyncClient(timeout=30) as client:
            root_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/",
                headers=headers,
                timeout=20,
            )
            root_resp.raise_for_status()
            items = root_resp.json()
        blobs = {
            item["path"]: item
            for item in items
            if item.get("type") == "file"
        }
    else:
        blobs = {
            item["path"]: item
            for item in tree_data.get("tree", [])
            if item["type"] == "blob"
        }

    # ── Step 2: score and rank ─────────────────────────────────────────────
    scored = []
    for path, meta in blobs.items():
        s = _score_path(path)
        if s < 0:
            continue
        if meta.get("size", 0) > MAX_FILE_BYTES:
            continue
        scored.append((s, path))

    scored.sort(key=lambda x: (-x[0], x[1]))
    targets = [path for _, path in scored[:MAX_FILES]]

    # ── Step 3: parallel fetch ─────────────────────────────────────────────
    files: dict[str, str] = {}
    total_chars = 0

    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [_fetch_one(client, owner, repo, path, headers) for path in targets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, tuple) and result is not None:
            path, content = result
            if total_chars + len(content) > MAX_TOTAL_CHARS:
                # Still include manifest files even if over budget
                fname = path.split("/")[-1]
                if fname not in PRIORITY_EXACT:
                    continue
            files[path] = content
            total_chars += len(content)

    return files
