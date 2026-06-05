"""
Fetches file contents from a GitHub repo via the GitHub API.
Supports public repos without auth; private repos require GITHUB_TOKEN.
"""
import re
import httpx
from app.config import settings

ENTRY_FILES = [
    "requirements.txt", "pyproject.toml", "package.json", "Dockerfile",
    "main.py", "app.py", "server.py", "run.py", "wsgi.py", "asgi.py",
    "celery_app.py", "celery.py", "tasks.py", "worker.py",
    "train.py", "training.py", "finetune.py",
    "inference.py", "predict.py", "serve.py",
    "pipeline.py", "dag.py",
]

MAX_FILE_SIZE = 100_000  # 100 KB per file


def parse_github_url(url: str) -> tuple[str, str]:
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", url)
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return match.group(1), match.group(2)


async def fetch_repo_files(repo_url: str) -> dict[str, str]:
    owner, repo = parse_github_url(repo_url)
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    async with httpx.AsyncClient(timeout=30) as client:
        tree_resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/HEAD?recursive=1",
            headers=headers,
        )
        tree_resp.raise_for_status()
        tree = tree_resp.json()

    blobs = {item["path"]: item for item in tree.get("tree", []) if item["type"] == "blob"}

    # Prioritize entry files, then grab up to 20 .py files from root
    targets = []
    for entry in ENTRY_FILES:
        if entry in blobs:
            targets.append(entry)
    for path in blobs:
        if path.endswith(".py") and "/" not in path and path not in targets:
            targets.append(path)
        if len(targets) >= 30:
            break

    files: dict[str, str] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        for path in targets:
            blob = blobs[path]
            if blob.get("size", 0) > MAX_FILE_SIZE:
                continue
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=headers,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            if data.get("encoding") == "base64":
                import base64
                files[path] = base64.b64decode(data["content"]).decode("utf-8", errors="replace")

    return files
