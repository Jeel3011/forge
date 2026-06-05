from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.scanner.repo_fetcher import fetch_repo_files, parse_github_url
from app.scanner.dep_parser import (
    parse_requirements_txt, parse_pyproject_toml, parse_package_json,
    classify_from_packages,
)
from app.scanner.issue_detector import detect_issues
from app.ai.classifier import analyze_code_characteristics
from app.ai.questionnaire import generate_questions
from app.generator.config_generator import generate_configs
from app.models import (
    ScanResult, GenerateRequest, GeneratedConfig, Question, FixApproval
)

router = APIRouter()


class ScanRequest(BaseModel):
    repo_url: str


@router.post("/scan", response_model=ScanResult)
async def scan_repo(req: ScanRequest):
    try:
        parse_github_url(req.repo_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        files = await fetch_repo_files(req.repo_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to fetch repo: {e}")

    # Layer 1: dependency parsing
    all_packages: list[str] = []
    if "requirements.txt" in files:
        all_packages.extend(parse_requirements_txt(files["requirements.txt"]))
    if "pyproject.toml" in files:
        all_packages.extend(parse_pyproject_toml(files["pyproject.toml"]))
    if "package.json" in files:
        all_packages.extend(parse_package_json(files["package.json"]))

    project_type, confidence = classify_from_packages(all_packages)

    # Layer 2: AI code analysis
    characteristics = await analyze_code_characteristics(files, project_type)

    # Issue detection
    issues = detect_issues(files, project_type)

    return ScanResult(
        repo_url=req.repo_url,
        project_type=project_type,
        confidence=confidence,
        detected_dependencies=list(set(all_packages)),
        detected_characteristics=characteristics,
        issues=issues,
    )


@router.post("/questions", response_model=list[Question])
async def get_questions(scan_result: ScanResult):
    return await generate_questions(
        project_type=scan_result.project_type,
        characteristics=scan_result.detected_characteristics,
        dependencies=scan_result.detected_dependencies,
    )


@router.post("/generate", response_model=GeneratedConfig)
async def generate(req: GenerateRequest):
    return generate_configs(req)


@router.get("/health")
async def health():
    return {"status": "ok"}
