import argparse
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import OLLAMA_BASE_URL  # noqa: E402
from app.model_registry import MODEL_CANDIDATES  # noqa: E402


def _ollama_command() -> str:
    command = shutil.which("ollama")
    if command:
        return command
    system = platform.system()
    if system == "Windows":
        raise SystemExit(
            "Ollama is not in PATH. Install it from https://ollama.com/download/windows "
            "and reopen PowerShell."
        )
    if system == "Darwin":
        raise SystemExit(
            "Ollama is not in PATH. Install it from https://ollama.com/download/mac "
            "and start the Ollama app."
        )
    raise SystemExit(
        "Ollama is not in PATH. On Linux, install with: curl -fsSL https://ollama.com/install.sh | sh"
    )


def _parse_version(value: str) -> tuple[int, int, int]:
    parts = []
    for token in value.split(".")[:3]:
        digits = "".join(char for char in token if char.isdigit())
        parts.append(int(digits or "0"))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def _check_daemon() -> str:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=3)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(
            f"Ollama is installed but not reachable at {OLLAMA_BASE_URL}. "
            "Start it with `ollama serve` or open the Ollama desktop app."
        ) from exc
    return str(response.json().get("version", "0.0.0"))


def _check_model_runtime(candidate_id: str, ollama_version: str) -> None:
    candidate = MODEL_CANDIDATES[candidate_id]
    if candidate.ollama_model.startswith("qwen3-vl") and _parse_version(ollama_version) < (0, 12, 7):
        raise SystemExit(
            f"{candidate.ollama_model} requires Ollama >= 0.12.7. "
            f"Current version is {ollama_version}. Upgrade Ollama first."
        )


def _local_models() -> set[str]:
    response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
    response.raise_for_status()
    names: set[str] = set()
    for model in response.json().get("models", []):
        name = model.get("name")
        if name:
            names.add(name)
            names.add(name.split(":")[0])
    return names


def _candidate_ids_for_tier(tier: str) -> list[str]:
    if tier == "16gb":
        return [
            "qwen3-vl-4b-ollama",
            "qwen3-vl-2b-ollama",
            "qwen2_5-vl-3b-ollama",
            "gemma3-4b-ollama",
        ]
    if tier == "32gb":
        return [
            "qwen3-vl-4b-ollama",
            "qwen3-vl-8b-ollama",
            "qwen2_5-vl-7b-ollama",
            "gemma3-12b-ollama",
            "minicpm-v-ollama",
        ]
    return [
        model_id
        for model_id, candidate in MODEL_CANDIDATES.items()
        if candidate.mode == "local_ollama_vlm"
    ]


def pull_model(model_id: str) -> None:
    candidate = MODEL_CANDIDATES[model_id]
    if candidate.mode != "local_ollama_vlm":
        print(f"skip: {candidate.id} does not need Ollama weights")
        return
    before = _local_models()
    if candidate.ollama_model in before:
        print(f"exists: {candidate.ollama_model}")
        return

    command = [_ollama_command(), "pull", candidate.ollama_model]
    print(f"pulling: {candidate.ollama_model} (~{candidate.estimated_disk_gb}GB)")
    subprocess.run(command, check=True)
    time.sleep(0.5)
    after = _local_models()
    if candidate.ollama_model not in after:
        raise SystemExit(f"pull finished but model is not listed by Ollama: {candidate.ollama_model}")
    print(f"ready: {candidate.ollama_model}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download cross-platform local VLMs through Ollama.")
    parser.add_argument("--model", choices=sorted(MODEL_CANDIDATES.keys()))
    parser.add_argument("--tier", choices=["16gb", "32gb", "all"], default="16gb")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        for model_id, candidate in MODEL_CANDIDATES.items():
            if candidate.mode != "local_ollama_vlm":
                continue
            print(
                f"{candidate.id}\t{candidate.ollama_model}\t{candidate.memory_tier}\t"
                f"~{candidate.estimated_disk_gb}GB\t{candidate.pull_command}"
            )
        return

    _ollama_command()
    ollama_version = _check_daemon()
    model_ids = [args.model] if args.model else _candidate_ids_for_tier(args.tier)
    for model_id in model_ids:
        _check_model_runtime(model_id, ollama_version)
        pull_model(model_id)


if __name__ == "__main__":
    main()
