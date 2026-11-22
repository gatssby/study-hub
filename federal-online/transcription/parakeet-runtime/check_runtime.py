#!/usr/bin/env python3
"""Offline runtime check for the pinned Parakeet TDT v3 pt-BR ONNX pilot.

Validates the manifest schema, the six pinned files (size + SHA-256), the
isolated venv interpreter, the pinned pip closure, CPU-only onnxruntime, and
local model loading. It never downloads and never activates a service.

Run it with the install venv interpreter:

    <root>/venv/bin/python check_runtime.py --root <root>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

SCHEMA = "study-hub.parakeet-runtime.manifest/v1"
GPU_PROVIDERS = {
    "CUDAExecutionProvider",
    "ROCMExecutionProvider",
    "TensorrtExecutionProvider",
    "NvTensorRtRtxExecutionProvider",
    "CoreMLExecutionProvider",
    "DmlExecutionProvider",
    "WebGpuExecutionProvider",
}
FORBIDDEN_MODEL_NAMES = {
    "encoder-model.onnx",
    "decoder_joint-model.onnx",
    "encoder-model.onnx.data",
    "decoder_joint-model.onnx.data",
}

IMPORT_INFO_CODE = (
    "import json,platform,sys;"
    "print(json.dumps({'python':platform.python_version(),'machine':platform.machine(),"
    "'libc':platform.libc_ver()[1],'executable':sys.executable}))"
)

PIP_VERSIONS_CODE = (
    "import importlib.metadata as md,json,sys\n"
    "pins=json.loads(sys.argv[1])\n"
    "out={}\n"
    "for name in list(pins)+['torch']:\n"
    "    try: out[name]=md.version(name)\n"
    "    except md.PackageNotFoundError: out[name]=None\n"
    "print(json.dumps(out))\n"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def os_release() -> dict[str, str]:
    out: dict[str, str] = {}
    path = Path("/etc/os-release")
    if path.is_file():
        for line in path.read_text().splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                out[key] = value.strip().strip('"')
    return out


def run_json(python: Path, code: str, argv: list[str] | None = None):
    cmd = [str(python), "-c", code, *(argv or [])]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"exit {proc.returncode}")
    return json.loads(proc.stdout)


def finish(report: dict, args) -> int:
    report["ok"] = not report["errors"] and not report.get("error")
    text = json.dumps(report, indent=2)
    print(text)
    if args.json_out:
        Path(args.json_out).write_text(text + "\n")
    return 0 if report["ok"] else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--skip-model", action="store_true")
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--allow-missing", action="store_true")
    parser.add_argument("--allow-target-mismatch", action="store_true")
    parser.add_argument(
        "--probe",
        action="store_true",
        help="run 1 s of in-memory zeros through the model (synthetic; no audio file)",
    )
    args = parser.parse_args(argv)
    if args.threads < 1:
        parser.error("--threads must be >= 1")

    root = Path(args.root).resolve()
    manifest_path = Path(args.manifest).resolve() if args.manifest else root / "manifest.json"
    report: dict = {
        "ok": False,
        "schema": SCHEMA,
        "root": str(root),
        "manifest": str(manifest_path),
        "files": [],
        "target": {},
        "venv": {},
        "model": {"loaded": False},
        "warnings": [],
        "errors": [],
    }
    errors: list[str] = report["errors"]

    try:
        manifest = json.loads(manifest_path.read_text())
    except Exception as exc:  # noqa: BLE001
        report["error"] = f"manifest unreadable: {exc}"
        return finish(report, args)

    if manifest.get("schema") != SCHEMA:
        errors.append(f"schema mismatch: {manifest.get('schema')!r} != {SCHEMA!r}")

    target = manifest.get("target", {})
    layout = manifest.get("layout", {})
    models_dir = root / layout.get("models", "models")
    venv_dir = root / layout.get("venv", "venv")
    venv_python = venv_dir / "bin" / "python"
    expected_names = [item["name"] for item in manifest.get("files", [])]

    # --- target platform -------------------------------------------------
    actual_target = {
        "python": platform.python_version(),
        "machine": platform.machine(),
        "libc": platform.libc_ver()[1],
        "os_release": os_release(),
    }
    target_errors: list[str] = []
    if not args.allow_target_mismatch:
        for label, got, want in (
            ("python", actual_target["python"], target.get("python")),
            ("arch", actual_target["machine"], target.get("arch")),
            ("glibc", actual_target["libc"], target.get("glibc")),
        ):
            if want and got != want:
                target_errors.append(f"target {label}: {got!r} != {want!r}")
        release = actual_target["os_release"]
        if target.get("os"):
            if (
                release.get("ID") != "ubuntu"
                or release.get("VERSION_ID") != "24.04"
                or "24.04.5" not in release.get("VERSION", "")
            ):
                target_errors.append(f"target os: {release!r} != {target['os']!r}")
    report["target"] = {
        "expected": target,
        "actual": actual_target,
        "ok": not target_errors,
    }
    errors.extend(target_errors)

    # --- pinned files ----------------------------------------------------
    for spec in manifest.get("files", []):
        name = spec["name"]
        path = models_dir / name
        entry = {
            "name": name,
            "role": spec.get("role"),
            "expected_bytes": spec["bytes"],
            "expected_sha256": spec["sha256"],
            "present": path.is_file(),
            "ok": False,
        }
        if not path.is_file():
            if args.allow_missing:
                report["warnings"].append(f"missing {name}")
            else:
                errors.append(f"missing model file: {path}")
        else:
            size = path.stat().st_size
            digest = sha256_file(path)
            entry["bytes"] = size
            entry["sha256"] = digest
            if size != spec["bytes"]:
                errors.append(f"size mismatch {name}: {size} != {spec['bytes']}")
            elif digest != spec["sha256"]:
                errors.append(f"sha256 mismatch {name}: {digest} != {spec['sha256']}")
            else:
                entry["ok"] = True
        report["files"].append(entry)

    if models_dir.is_dir():
        extras = sorted(p.name for p in models_dir.iterdir() if p.name not in expected_names)
        forbidden = sorted(
            p.name
            for p in models_dir.iterdir()
            if p.name in FORBIDDEN_MODEL_NAMES or p.name.endswith(".onnx.data")
        )
        report["models_dir_extra"] = extras
        if forbidden:
            errors.append(f"forbidden FP32/external-data model files present: {forbidden}")
        if extras:
            report["warnings"].append(f"unexpected files in models dir: {extras}")

    if args.manifest_only:
        return finish(report, args)

    # --- venv ------------------------------------------------------------
    if not venv_python.is_file():
        errors.append(f"venv interpreter missing: {venv_python}")
    else:
        report["venv"]["python"] = str(venv_python)
        if Path(sys.executable).resolve() != venv_python.resolve():
            errors.append(
                f"check must run under the install venv: {sys.executable} != {venv_python}"
            )
        try:
            report["venv"].update(run_json(venv_python, IMPORT_INFO_CODE))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"venv introspection failed: {exc}")
        try:
            pins = manifest.get("pip", {})
            versions = run_json(venv_python, PIP_VERSIONS_CODE, [json.dumps(pins)])
            report["venv"]["packages"] = versions
            for name, want in pins.items():
                got = versions.get(name)
                if got is None:
                    errors.append(f"pip package missing: {name}")
                elif got != want:
                    errors.append(f"pip version mismatch {name}: {got} != {want}")
            if versions.get("torch") is not None:
                errors.append("torch is installed")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"pip verification failed: {exc}")

    # --- offline model load ---------------------------------------------
    if not args.skip_model and not errors:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        try:
            import onnxruntime as rt
            import onnx_asr
        except Exception as exc:  # noqa: BLE001
            errors.append(f"import onnxruntime/onnx_asr failed: {exc}")
        else:
            report["model"]["onnxruntime_version"] = rt.__version__
            report["model"]["onnx_asr_version"] = onnx_asr.__version__
            providers = list(rt.get_available_providers())
            report["model"]["available_providers"] = providers
            gpu = sorted(set(providers) & GPU_PROVIDERS)
            if gpu:
                errors.append(f"non-CPU execution providers available: {gpu}")
            if "CPUExecutionProvider" not in providers:
                errors.append("CPUExecutionProvider is not available")

            sess_options = rt.SessionOptions()
            sess_options.intra_op_num_threads = args.threads
            sess_options.inter_op_num_threads = 1
            sess_options.execution_mode = rt.ExecutionMode.ORT_SEQUENTIAL
            try:
                model = onnx_asr.load_model(
                    manifest["model"]["type"],
                    path=str(models_dir),
                    quantization=manifest["model"]["quantization"],
                    sess_options=sess_options,
                    providers=["CPUExecutionProvider"],
                )
                vad = onnx_asr.load_vad(
                    "silero",
                    path=str(models_dir),
                    sess_options=sess_options,
                    providers=["CPUExecutionProvider"],
                )
                report["model"]["loaded"] = True
                asr = getattr(model, "asr", None)
                for label, session in (
                    ("encoder_providers", getattr(asr, "_encoder", None)),
                    ("decoder_joint_providers", getattr(asr, "_decoder_joint", None)),
                    ("vad_providers", getattr(vad, "_model", None)),
                ):
                    if session is not None:
                        report["model"][label] = list(session.get_providers())
                if args.probe:
                    import numpy as np

                    result = model.recognize(np.zeros(16000, dtype=np.float32), sample_rate=16000)
                    report["model"]["probe"] = {
                        "input": "1 s in-memory zeros at 16 kHz (synthetic, no audio file)",
                        "text": result,
                    }
            except Exception as exc:  # noqa: BLE001
                errors.append(f"offline model load failed: {exc}")

    return finish(report, args)


if __name__ == "__main__":
    raise SystemExit(main())
