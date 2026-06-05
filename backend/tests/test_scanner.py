import pytest
from app.scanner.dep_parser import (
    parse_requirements_txt, classify_from_packages
)
from app.scanner.issue_detector import detect_issues
from app.models import ProjectType


def test_parse_requirements_basic():
    content = "fastapi==0.111.0\ncelery>=5.0\nredis\n# comment\n"
    pkgs = parse_requirements_txt(content)
    assert "fastapi" in pkgs
    assert "celery" in pkgs
    assert "redis" in pkgs


def test_classify_ai_agent():
    packages = ["celery", "redis", "langchain", "fastapi"]
    ptype, confidence = classify_from_packages(packages)
    assert ptype == ProjectType.AI_AGENT
    assert confidence > 0


def test_classify_fine_tuning():
    packages = ["torch", "transformers", "peft", "trl", "datasets"]
    ptype, confidence = classify_from_packages(packages)
    assert ptype == ProjectType.FINE_TUNING


def test_classify_unknown():
    packages = ["requests", "pytest"]
    ptype, _ = classify_from_packages(packages)
    assert ptype == ProjectType.UNKNOWN


def test_detect_missing_dockerfile():
    files = {"main.py": "from fastapi import FastAPI\napp = FastAPI()"}
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    titles = [i.title for i in issues]
    assert "No Dockerfile found" in titles


def test_detect_missing_health_endpoint():
    files = {"Dockerfile": "FROM python:3.11", "main.py": "from fastapi import FastAPI\napp = FastAPI()"}
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    titles = [i.title for i in issues]
    assert "No health check endpoint" in titles


def test_no_issue_with_health_endpoint():
    files = {
        "Dockerfile": "FROM python:3.11",
        "main.py": '@app.get("/health")\nasync def health(): return {"status": "ok"}',
    }
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    titles = [i.title for i in issues]
    assert "No health check endpoint" not in titles
