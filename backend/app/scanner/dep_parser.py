"""
Dependency parser — Layer 1 of the scanner.
Reads requirements.txt, pyproject.toml, package.json, Dockerfile and returns
a normalized list of package names + a preliminary project type classification.
"""
import re
from pathlib import Path
from app.models import ProjectType

CLASSIFICATION_MAP: dict[ProjectType, list[str]] = {
    ProjectType.AI_AGENT: [
        "celery", "redis", "langchain", "langchain-core", "langchain-community",
        "crewai", "autogen", "pyautogen", "langgraph",
    ],
    ProjectType.LLM_APPLICATION: [
        "openai", "anthropic", "langchain", "llamaindex", "llama-index",
        "litellm", "groq", "cohere", "mistralai",
    ],
    ProjectType.FINE_TUNING: [
        "torch", "transformers", "datasets", "peft", "trl",
        "accelerate", "bitsandbytes", "wandb", "mlflow",
    ],
    ProjectType.MODEL_SERVING: [
        "onnxruntime", "triton", "bentoml", "ray", "torchserve",
        "fastapi", "flask", "torch", "tensorflow",
    ],
    ProjectType.DATA_PIPELINE: [
        "airflow", "prefect", "dagster", "luigi", "pandas",
        "dask", "pyspark", "sqlalchemy",
    ],
    ProjectType.COMPUTER_VISION: [
        "opencv-python", "cv2", "pillow", "PIL", "torchvision",
        "ultralytics", "detectron2", "albumentations",
    ],
    ProjectType.CLASSICAL_ML: [
        "scikit-learn", "sklearn", "xgboost", "lightgbm", "catboost",
        "statsmodels", "scipy",
    ],
}

# Score weights: higher = stronger signal
WEIGHTS: dict[str, int] = {
    "celery": 3, "langchain": 2, "crewai": 3, "autogen": 3,
    "torch": 1, "transformers": 2, "peft": 3, "trl": 3,
    "onnxruntime": 3, "bentoml": 3,
    "airflow": 3, "prefect": 3, "dagster": 3,
    "opencv-python": 3, "torchvision": 2,
    "scikit-learn": 2, "xgboost": 2, "lightgbm": 2,
}


def parse_requirements_txt(content: str) -> list[str]:
    packages = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-r"):
            continue
        name = re.split(r"[>=<!;@\[]", line)[0].strip().lower()
        if name:
            packages.append(name)
    return packages


def parse_pyproject_toml(content: str) -> list[str]:
    packages = []
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ('[tool.poetry.dependencies]', '[project.dependencies]',
                        '[project]') or 'dependencies' in stripped:
            in_deps = True
            continue
        if stripped.startswith('[') and in_deps:
            in_deps = False
        if in_deps and '=' in stripped:
            name = re.split(r'[>=<!"\s\[]', stripped)[0].strip().strip('"').lower()
            if name and name != 'python':
                packages.append(name)
    return packages


def parse_package_json(content: str) -> list[str]:
    import json
    try:
        data = json.loads(content)
        deps = list(data.get("dependencies", {}).keys())
        deps += list(data.get("devDependencies", {}).keys())
        return [d.lower() for d in deps]
    except json.JSONDecodeError:
        return []


def classify_from_packages(packages: list[str]) -> tuple[ProjectType, float]:
    scores: dict[ProjectType, float] = {pt: 0.0 for pt in ProjectType}

    pkg_set = set(p.replace("-", "_") for p in packages)
    for pkg in packages:
        normalized = pkg.replace("-", "_")
        for project_type, signals in CLASSIFICATION_MAP.items():
            for signal in signals:
                if signal.replace("-", "_") == normalized or signal in normalized:
                    weight = WEIGHTS.get(signal, 1)
                    scores[project_type] += weight

    # Fine-tuning beats model serving if train-related packages present
    if scores[ProjectType.FINE_TUNING] > 0 and scores[ProjectType.MODEL_SERVING] > 0:
        if "peft" in pkg_set or "trl" in pkg_set or "trainer" in pkg_set:
            scores[ProjectType.MODEL_SERVING] *= 0.5

    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values()) or 1
    confidence = round(scores[best] / total, 2)

    if scores[best] == 0:
        return ProjectType.UNKNOWN, 0.0
    return best, confidence
