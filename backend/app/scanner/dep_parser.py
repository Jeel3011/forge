"""
Dependency parser — Layer 1 scanner.
Parses requirements.txt, pyproject.toml, setup.py, Pipfile, conda environment.yml,
package.json and returns normalised package names + weighted project type scores.
"""
import re
import json
from app.models import ProjectType

# ── Canonical aliases ───────────────────────────────────────────────────────
# Maps import/PyPI names that appear in code → canonical signal name used below
ALIASES: dict[str, str] = {
    "cv2":            "opencv-python",
    "PIL":            "pillow",
    "sklearn":        "scikit-learn",
    "tf":             "tensorflow",
    "keras":          "tensorflow",
    "sentence_transformers": "sentence-transformers",
    "llama_index":    "llama-index",
    "llama_cpp":      "llama-cpp-python",
    "chromadb":       "chroma",
    "qdrant_client":  "qdrant-client",
    "pinecone":       "pinecone-client",
    "weaviate":       "weaviate-client",
    "pg_vector":      "pgvector",
    "opentelemetry":  "opentelemetry-sdk",
    "rq":             "redis-queue",
    "dramatiq":       "dramatiq",
    "arq":            "arq",
    "pyautogen":      "autogen",
}

# ── Classification signals ──────────────────────────────────────────────────
# Each entry: (signal_name, project_type, weight)
# Weight philosophy:
#   5 = exclusive signal — only this type uses it (crewai, peft, airflow)
#   4 = very strong (langgraph, trl, dagster, bentoml)
#   3 = strong (celery+redis together, onnxruntime, prefect)
#   2 = moderate (torch, transformers — shared by many types)
#   1 = weak — present in many project types (fastapi, pandas)
SIGNALS: list[tuple[str, ProjectType, int]] = [
    # AI Agent
    ("crewai",            ProjectType.AI_AGENT,        5),
    ("autogen",           ProjectType.AI_AGENT,        5),
    ("pyautogen",         ProjectType.AI_AGENT,        5),
    ("langgraph",         ProjectType.AI_AGENT,        4),
    ("langchain-core",    ProjectType.AI_AGENT,        3),
    ("langchain-community",ProjectType.AI_AGENT,       3),
    ("celery",            ProjectType.AI_AGENT,        3),
    ("dramatiq",          ProjectType.AI_AGENT,        3),
    ("arq",               ProjectType.AI_AGENT,        3),
    ("redis-queue",       ProjectType.AI_AGENT,        3),
    ("langchain",         ProjectType.AI_AGENT,        2),

    # LLM Application (pure API usage, no training)
    ("openai",            ProjectType.LLM_APPLICATION, 4),
    ("anthropic",         ProjectType.LLM_APPLICATION, 4),
    ("litellm",           ProjectType.LLM_APPLICATION, 4),
    ("groq",              ProjectType.LLM_APPLICATION, 4),
    ("mistralai",         ProjectType.LLM_APPLICATION, 4),
    ("cohere",            ProjectType.LLM_APPLICATION, 3),
    ("llama-index",       ProjectType.LLM_APPLICATION, 3),
    ("llama-cpp-python",  ProjectType.LLM_APPLICATION, 3),
    ("langchain",         ProjectType.LLM_APPLICATION, 2),
    ("tiktoken",          ProjectType.LLM_APPLICATION, 2),
    ("chroma",            ProjectType.LLM_APPLICATION, 1),
    ("qdrant-client",     ProjectType.LLM_APPLICATION, 1),
    ("pinecone-client",   ProjectType.LLM_APPLICATION, 1),

    # Fine-tuning Pipeline
    ("peft",              ProjectType.FINE_TUNING,     5),
    ("trl",               ProjectType.FINE_TUNING,     5),
    ("bitsandbytes",      ProjectType.FINE_TUNING,     5),
    ("accelerate",        ProjectType.FINE_TUNING,     4),
    ("datasets",          ProjectType.FINE_TUNING,     3),
    ("transformers",      ProjectType.FINE_TUNING,     2),
    ("torch",             ProjectType.FINE_TUNING,     1),
    ("wandb",             ProjectType.FINE_TUNING,     2),
    ("mlflow",            ProjectType.FINE_TUNING,     2),
    ("deepspeed",         ProjectType.FINE_TUNING,     4),
    ("flash-attn",        ProjectType.FINE_TUNING,     4),

    # Model Serving
    ("bentoml",           ProjectType.MODEL_SERVING,   5),
    ("torchserve",        ProjectType.MODEL_SERVING,   5),
    ("triton",            ProjectType.MODEL_SERVING,   5),
    ("onnxruntime",       ProjectType.MODEL_SERVING,   4),
    ("ray",               ProjectType.MODEL_SERVING,   3),
    ("ray-serve",         ProjectType.MODEL_SERVING,   5),
    ("vllm",              ProjectType.MODEL_SERVING,   5),
    ("ctransformers",     ProjectType.MODEL_SERVING,   4),
    ("optimum",           ProjectType.MODEL_SERVING,   3),
    ("torch",             ProjectType.MODEL_SERVING,   1),

    # Data Pipeline
    ("airflow",           ProjectType.DATA_PIPELINE,   5),
    ("apache-airflow",    ProjectType.DATA_PIPELINE,   5),
    ("prefect",           ProjectType.DATA_PIPELINE,   5),
    ("dagster",           ProjectType.DATA_PIPELINE,   5),
    ("luigi",             ProjectType.DATA_PIPELINE,   4),
    ("dask",              ProjectType.DATA_PIPELINE,   3),
    ("pyspark",           ProjectType.DATA_PIPELINE,   4),
    ("great-expectations",ProjectType.DATA_PIPELINE,   3),
    ("dbt",               ProjectType.DATA_PIPELINE,   4),
    ("pandas",            ProjectType.DATA_PIPELINE,   1),
    ("polars",            ProjectType.DATA_PIPELINE,   2),

    # Computer Vision
    ("ultralytics",       ProjectType.COMPUTER_VISION, 5),
    ("detectron2",        ProjectType.COMPUTER_VISION, 5),
    ("mmdetection",       ProjectType.COMPUTER_VISION, 5),
    ("opencv-python",     ProjectType.COMPUTER_VISION, 4),
    ("torchvision",       ProjectType.COMPUTER_VISION, 3),
    ("albumentations",    ProjectType.COMPUTER_VISION, 3),
    ("pillow",            ProjectType.COMPUTER_VISION, 1),
    ("imageio",           ProjectType.COMPUTER_VISION, 2),
    ("supervision",       ProjectType.COMPUTER_VISION, 4),

    # Classical ML
    ("scikit-learn",      ProjectType.CLASSICAL_ML,    4),
    ("xgboost",           ProjectType.CLASSICAL_ML,    4),
    ("lightgbm",          ProjectType.CLASSICAL_ML,    4),
    ("catboost",          ProjectType.CLASSICAL_ML,    4),
    ("statsmodels",       ProjectType.CLASSICAL_ML,    3),
    ("shap",              ProjectType.CLASSICAL_ML,    3),
    ("optuna",            ProjectType.CLASSICAL_ML,    2),
    ("hyperopt",          ProjectType.CLASSICAL_ML,    2),
    ("scipy",             ProjectType.CLASSICAL_ML,    1),

    # Multimodal  (audio + vision + text together)
    ("whisper",           ProjectType.MULTIMODAL,      4),
    ("openai-whisper",    ProjectType.MULTIMODAL,      4),
    ("transformers",      ProjectType.MULTIMODAL,      1),
    ("diffusers",         ProjectType.MULTIMODAL,      4),
    ("torchaudio",        ProjectType.MULTIMODAL,      3),
    ("librosa",           ProjectType.MULTIMODAL,      3),
    ("speechbrain",       ProjectType.MULTIMODAL,      4),
    ("clip",              ProjectType.MULTIMODAL,      4),
    ("open-clip-torch",   ProjectType.MULTIMODAL,      4),
]

# Pre-build lookup: canonical_name → [(project_type, weight)]
_SIGNAL_MAP: dict[str, list[tuple[ProjectType, int]]] = {}
for _sig, _pt, _w in SIGNALS:
    _SIGNAL_MAP.setdefault(_sig.replace("-", "_"), []).append((_pt, _w))


def _normalise(name: str) -> str:
    """Lowercase, replace hyphens/spaces with underscores."""
    return re.sub(r"[-\s]", "_", name.strip().lower())


def _resolve(name: str) -> str:
    """Apply alias table, then normalise."""
    n = _normalise(name)
    return _normalise(ALIASES.get(name, ALIASES.get(n, name)))


# ── Parsers ──────────────────────────────────────────────────────────────────

def parse_requirements_txt(content: str) -> list[str]:
    pkgs = []
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "-r ", "--", "http://", "https://", "git+")):
            continue
        # Strip extras [extra], version specifiers, env markers
        # e.g.  httpx[http2]>=0.27  →  httpx
        name = re.split(r"[\[>=<!;@\s]", line)[0].strip()
        if name:
            pkgs.append(_resolve(name.lower()))
    return pkgs


def parse_pyproject_toml(content: str) -> list[str]:
    """
    Handles both:
      dep = "^1.0"            (poetry style)
      dependencies = ["dep>=1.0", ...]   (PEP 621 style)
    """
    pkgs: list[str] = []
    # PEP 621 array style: dependencies = ["pkg>=1", "pkg2"]
    array_match = re.search(
        r'dependencies\s*=\s*\[([^\]]+)\]', content, re.DOTALL
    )
    if array_match:
        for item in re.findall(r'"([^"]+)"|\'([^\']+)\'', array_match.group(1)):
            raw = (item[0] or item[1]).strip()
            name = re.split(r"[>=<!;\[]", raw)[0].strip()
            if name and name != "python":
                pkgs.append(_resolve(name))

    # Poetry / key=value style
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if re.match(r'^\[(tool\.poetry\.dependencies|project\.dependencies|dependencies)\]', stripped):
            in_deps = True
            continue
        if stripped.startswith("[") and in_deps:
            in_deps = False
        if in_deps and "=" in stripped and not stripped.startswith("["):
            name = re.split(r'[>=<!\s"\[{]', stripped)[0].strip().strip('"').strip("'")
            if name and name != "python" and not name.startswith("#"):
                pkgs.append(_resolve(name))

    return list(dict.fromkeys(pkgs))  # deduplicate, preserve order


def parse_setup_py(content: str) -> list[str]:
    pkgs: list[str] = []
    # install_requires=[...] or install_requires=(...)
    m = re.search(r'install_requires\s*=\s*[\[\(]([^\]\)]+)[\]\)]', content, re.DOTALL)
    if m:
        for item in re.findall(r'"([^"]+)"|\'([^\']+)\'', m.group(1)):
            raw = item[0] or item[1]
            name = re.split(r"[>=<!;\[]", raw)[0].strip()
            if name:
                pkgs.append(_resolve(name))
    return pkgs


def parse_pipfile(content: str) -> list[str]:
    pkgs: list[str] = []
    in_packages = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ("[packages]", "[dev-packages]"):
            in_packages = True
            continue
        if stripped.startswith("[") and in_packages:
            in_packages = False
        if in_packages and "=" in stripped:
            name = stripped.split("=")[0].strip().strip('"')
            if name:
                pkgs.append(_resolve(name))
    return pkgs


def parse_conda_env(content: str) -> list[str]:
    """Parse conda environment.yml — grab pip: section and conda deps."""
    pkgs: list[str] = []
    in_pip = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "- pip:":
            in_pip = True
            continue
        if stripped.startswith("- ") and in_pip and not stripped.startswith("- pip:"):
            raw = stripped[2:].strip()
            name = re.split(r"[>=<!;\[]", raw)[0].strip()
            if name and "::" not in name:
                pkgs.append(_resolve(name))
        elif stripped.startswith("- ") and not in_pip:
            raw = stripped[2:].strip()
            if "=" in raw:
                name = raw.split("=")[0].strip()
            else:
                name = re.split(r"[>=<!;\[]", raw)[0].strip()
            if name and "::" not in name and name not in ("python", "pip", "conda"):
                pkgs.append(_resolve(name))
        if stripped and not stripped.startswith("-") and in_pip:
            in_pip = False
    return pkgs


def parse_package_json(content: str) -> list[str]:
    try:
        data = json.loads(content)
        deps = list(data.get("dependencies", {}).keys())
        deps += list(data.get("devDependencies", {}).keys())
        return [_normalise(d) for d in deps]
    except json.JSONDecodeError:
        return []


# ── Classifier ───────────────────────────────────────────────────────────────

def classify_from_packages(packages: list[str]) -> tuple[ProjectType, float, dict[ProjectType, float]]:
    """
    Returns (best_type, confidence_0_to_1, scores_per_type).
    Confidence = best_score / total_score (min 2 signals to trust it).
    """
    scores: dict[ProjectType, float] = {pt: 0.0 for pt in ProjectType}
    matched_signals: set[str] = set()

    for pkg in packages:
        n = _normalise(pkg)
        hits = _SIGNAL_MAP.get(n, [])
        for pt, weight in hits:
            scores[pt] += weight
            matched_signals.add(n)

    # ── Disambiguation rules (applied after raw scoring) ──────────────────

    pkg_set = set(packages)

    # If both fine-tuning AND model-serving scored, check for training-only signals
    ft = scores[ProjectType.FINE_TUNING]
    ms = scores[ProjectType.MODEL_SERVING]
    if ft > 0 and ms > 0:
        has_training_signal = bool(
            pkg_set & {"peft", "trl", "bitsandbytes", "accelerate", "deepspeed", "flash_attn"}
        )
        if has_training_signal:
            scores[ProjectType.MODEL_SERVING] *= 0.3
        else:
            scores[ProjectType.FINE_TUNING] *= 0.3

    # langchain alone → LLM_APPLICATION, not AI_AGENT (need celery/crewai/langgraph for agent)
    agent_exclusive = pkg_set & {"celery", "crewai", "autogen", "pyautogen", "langgraph",
                                  "dramatiq", "arq", "redis_queue"}
    if not agent_exclusive and scores[ProjectType.AI_AGENT] > 0:
        scores[ProjectType.AI_AGENT] *= 0.4

    # multimodal: needs at least 2 different modality signals to win
    multimodal_signals = pkg_set & {"whisper", "openai_whisper", "diffusers", "torchaudio",
                                     "librosa", "clip", "open_clip_torch", "speechbrain"}
    if len(multimodal_signals) < 2:
        scores[ProjectType.MULTIMODAL] *= 0.3

    # ── Pick winner ────────────────────────────────────────────────────────
    valid = {k: v for k, v in scores.items() if k != ProjectType.UNKNOWN}
    best = max(valid, key=lambda k: valid[k])
    total = sum(valid.values()) or 1.0
    raw_confidence = valid[best] / total

    # Confidence penalty: if only 1 signal matched, cap at 0.55
    if len(matched_signals) <= 1:
        raw_confidence = min(raw_confidence, 0.55)
    # Penalty: if top-2 scores are close (within 15%), lower confidence
    sorted_scores = sorted(valid.values(), reverse=True)
    if len(sorted_scores) >= 2 and sorted_scores[0] > 0:
        gap = (sorted_scores[0] - sorted_scores[1]) / sorted_scores[0]
        if gap < 0.15:
            raw_confidence *= 0.8

    if valid[best] == 0:
        return ProjectType.UNKNOWN, 0.0, scores

    return best, round(min(raw_confidence, 0.97), 2), scores
