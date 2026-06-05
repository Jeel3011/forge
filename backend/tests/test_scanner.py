import pytest
from app.scanner.dep_parser import (
    parse_requirements_txt, parse_pyproject_toml, parse_setup_py,
    parse_pipfile, classify_from_packages,
)
from app.scanner.issue_detector import detect_issues
from app.models import ProjectType


# ── dep_parser ────────────────────────────────────────────────────────────────

def test_parse_requirements_basic():
    content = "fastapi==0.111.0\ncelery>=5.0\nredis\n# comment\n-r base.txt\n"
    pkgs = parse_requirements_txt(content)
    assert "fastapi" in pkgs
    assert "celery" in pkgs
    assert "redis" in pkgs
    assert "-r" not in pkgs
    assert "" not in pkgs


def test_parse_requirements_extras_stripped():
    pkgs = parse_requirements_txt("uvicorn[standard]==0.29.0\nhttpx[http2]>=0.27")
    assert "uvicorn" in pkgs
    assert "httpx" in pkgs
    assert "uvicorn[standard]" not in pkgs


def test_parse_pyproject_toml_pep621_array():
    content = '[project]\ndependencies = [\n  "peft>=0.10",\n  "trl==0.8.0",\n  "accelerate",\n]'
    pkgs = parse_pyproject_toml(content)
    assert "peft" in pkgs
    assert "trl" in pkgs
    assert "accelerate" in pkgs


def test_parse_pyproject_toml_poetry():
    content = "[tool.poetry.dependencies]\npython = \"^3.11\"\nlangchain = \"^0.2\"\ncelery = \"*\"\n"
    pkgs = parse_pyproject_toml(content)
    assert "langchain" in pkgs
    assert "celery" in pkgs
    assert "python" not in pkgs


def test_parse_setup_py():
    content = 'setup(install_requires=["torch>=2.0", "transformers", "datasets>=2.0"])'
    pkgs = parse_setup_py(content)
    assert "torch" in pkgs
    assert "transformers" in pkgs
    assert "datasets" in pkgs


def test_classify_ai_agent():
    pkgs = ["celery", "redis", "langchain", "fastapi", "crewai"]
    ptype, conf, _ = classify_from_packages(pkgs)
    assert ptype == ProjectType.AI_AGENT
    assert conf > 0.5


def test_classify_fine_tuning():
    pkgs = ["torch", "transformers", "peft", "trl", "datasets", "accelerate"]
    ptype, conf, _ = classify_from_packages(pkgs)
    assert ptype == ProjectType.FINE_TUNING
    assert conf > 0.6


def test_classify_model_serving():
    pkgs = ["onnxruntime", "fastapi", "bentoml"]
    ptype, conf, _ = classify_from_packages(pkgs)
    assert ptype == ProjectType.MODEL_SERVING


def test_classify_computer_vision():
    pkgs = ["ultralytics", "opencv-python", "torchvision", "albumentations"]
    ptype, conf, _ = classify_from_packages(pkgs)
    assert ptype == ProjectType.COMPUTER_VISION


def test_classify_data_pipeline():
    pkgs = ["airflow", "pandas", "sqlalchemy", "dbt"]
    ptype, conf, _ = classify_from_packages(pkgs)
    assert ptype == ProjectType.DATA_PIPELINE


def test_classify_llm_app_not_agent():
    # langchain alone — no celery/crewai/langgraph → should be LLM_APPLICATION
    pkgs = ["langchain", "openai", "fastapi", "tiktoken"]
    ptype, _, _ = classify_from_packages(pkgs)
    assert ptype == ProjectType.LLM_APPLICATION


def test_classify_unknown():
    pkgs = ["requests", "pytest", "click"]
    ptype, _, _ = classify_from_packages(pkgs)
    assert ptype == ProjectType.UNKNOWN


def test_confidence_penalty_single_signal():
    pkgs = ["torch"]
    _, conf, _ = classify_from_packages(pkgs)
    assert conf <= 0.55


# ── issue_detector ────────────────────────────────────────────────────────────

def test_detect_missing_dockerfile():
    files = {"main.py": "from fastapi import FastAPI\napp = FastAPI()"}
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    assert any(i.issue_id == "no_dockerfile" for i in issues)


def test_no_dockerfile_issue_when_present():
    files = {"Dockerfile": "FROM python:3.11", "main.py": "app = 1"}
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    assert not any(i.issue_id == "no_dockerfile" for i in issues)


def test_detect_missing_health_endpoint():
    files = {"Dockerfile": "FROM python:3.11", "main.py": "from fastapi import FastAPI\napp = FastAPI()"}
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    assert any(i.issue_id == "no_health_endpoint" for i in issues)


def test_no_health_issue_when_present():
    files = {
        "Dockerfile": "FROM python:3.11",
        "main.py": '@app.get("/health")\nasync def h(): return {"status":"ok"}',
    }
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    assert not any(i.issue_id == "no_health_endpoint" for i in issues)


def test_detect_hardcoded_openai_key():
    files = {
        "Dockerfile": "FROM python:3.11",
        "main.py": 'api_key = "sk-' + 'A' * 40 + '"',
    }
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    assert any("OpenAI" in i.title or "hardcoded" in i.title.lower() for i in issues)


def test_skip_secrets_in_test_files():
    files = {
        "Dockerfile": "FROM python:3.11",
        "tests/test_api.py": 'api_key = "sk-' + 'A' * 40 + '"',
    }
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    secret_issues = [i for i in issues if "OpenAI" in i.title or "hardcoded" in i.title.lower()]
    assert len(secret_issues) == 0


def test_detect_missing_requirements():
    files = {"main.py": "import fastapi"}
    issues = detect_issues(files, ProjectType.LLM_APPLICATION)
    assert any(i.issue_id == "no_requirements" for i in issues)


def test_detect_celery_no_time_limit():
    files = {
        "Dockerfile": "FROM python:3.11",
        "requirements.txt": "celery\nredis",
        "tasks.py": "from celery import Celery\napp = Celery('tasks')\n@app.task\ndef run(): pass",
    }
    issues = detect_issues(files, ProjectType.AI_AGENT)
    assert any(i.issue_id == "celery_no_time_limit" for i in issues)


def test_detect_redis_no_retry():
    files = {
        "Dockerfile": "FROM python:3.11",
        "requirements.txt": "redis",
        "main.py": "from redis import Redis\nclient = Redis(host='localhost')",
    }
    issues = detect_issues(files, ProjectType.AI_AGENT)
    assert any(i.issue_id == "redis_no_retry" for i in issues)


def test_detect_gpu_without_cuda_image():
    files = {
        "Dockerfile": "FROM python:3.11-slim",
        "requirements.txt": "torch",
        "model.py": "import torch\ndevice = torch.device('cuda')\nmodel.to(device)",
    }
    issues = detect_issues(files, ProjectType.MODEL_SERVING)
    assert any(i.issue_id == "gpu_no_cuda_image" for i in issues)


def test_no_gpu_issue_with_cuda_image():
    files = {
        "Dockerfile": "FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04",
        "model.py": "model.cuda()",
    }
    issues = detect_issues(files, ProjectType.MODEL_SERVING)
    assert not any(i.issue_id == "gpu_no_cuda_image" for i in issues)


def test_issues_deduplicated():
    files = {
        "Dockerfile": "FROM python:3.11",
        "requirements.txt": "redis\ncelery",
        "a.py": "from redis import Redis\nclient = Redis()",
        "b.py": "from redis import Redis\nclient = Redis()",
    }
    issues = detect_issues(files, ProjectType.AI_AGENT)
    ids = [i.issue_id for i in issues]
    assert len(ids) == len(set(ids)), "Duplicate issue_ids found"
