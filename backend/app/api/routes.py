import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scanner.repo_fetcher import fetch_repo_files, parse_github_url
from app.scanner.dep_parser import (
    parse_requirements_txt, parse_pyproject_toml, parse_package_json,
    parse_setup_py, parse_pipfile, parse_conda_env,
    classify_from_packages,
)
from app.scanner.issue_detector import detect_issues
from app.ai.classifier import analyze_code_characteristics
from app.ai.questionnaire import generate_questions
from app.generator.config_generator import generate_configs
from app.models import (
    ScanResult, GenerateRequest, GeneratedConfig, Question,
)

router = APIRouter()


class ScanRequest(BaseModel):
    repo_url: str


@router.post("/scan", response_model=ScanResult)
async def scan_repo(req: ScanRequest):
    # ── Validate URL ─────────────────────────────────────────────────────────
    try:
        parse_github_url(req.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ── Fetch files ───────────────────────────────────────────────────────────
    try:
        files = await fetch_repo_files(req.repo_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to fetch repository: {e}")

    if not files:
        raise HTTPException(status_code=422, detail="Repository appears to be empty or inaccessible.")

    # ── Layer 1: dependency parsing ───────────────────────────────────────────
    all_packages: list[str] = []

    _PARSERS = [
        ("requirements.txt",  parse_requirements_txt),
        ("requirements-dev.txt", parse_requirements_txt),
        ("requirements_dev.txt", parse_requirements_txt),
        ("pyproject.toml",    parse_pyproject_toml),
        ("setup.py",          parse_setup_py),
        ("Pipfile",           parse_pipfile),
        ("environment.yml",   parse_conda_env),
        ("environment.yaml",  parse_conda_env),
        ("package.json",      parse_package_json),
    ]
    for fname, parser in _PARSERS:
        # Match by filename regardless of subdirectory
        for path, content in files.items():
            if path.endswith(fname) or path == fname:
                all_packages.extend(parser(content))
                break

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_packages = []
    for p in all_packages:
        if p and p not in seen:
            seen.add(p)
            unique_packages.append(p)

    l1_type, l1_confidence, _scores = classify_from_packages(unique_packages)

    # ── Layer 2: AI analysis + issue detection (parallel) ─────────────────────
    ai_task = analyze_code_characteristics(
        files, l1_type, l1_confidence, unique_packages
    )
    issue_task = asyncio.to_thread(detect_issues, files, l1_type)

    (ai_type, ai_confidence, characteristics, reasoning), issues = await asyncio.gather(
        ai_task, issue_task
    )

    return ScanResult(
        repo_url=req.repo_url,
        project_type=ai_type,
        confidence=ai_confidence,
        l1_confidence=l1_confidence,
        ai_reasoning=reasoning,
        detected_dependencies=unique_packages,
        detected_characteristics=characteristics,
        files_scanned=len(files),
        issues=issues,
    )


@router.post("/questions", response_model=list[Question])
async def get_questions(scan_result: ScanResult):
    # Re-fetch files so questionnaire has real code to reference
    # (kept small — only needed for snippet extraction)
    try:
        files = await fetch_repo_files(scan_result.repo_url)
    except Exception:
        files = {}

    return await generate_questions(
        project_type=scan_result.project_type,
        characteristics=scan_result.detected_characteristics,
        dependencies=scan_result.detected_dependencies,
        files=files,
    )


@router.post("/generate", response_model=GeneratedConfig)
async def generate(req: GenerateRequest):
    return generate_configs(req)


@router.get("/health")
async def health():
    return {"status": "ok"}
