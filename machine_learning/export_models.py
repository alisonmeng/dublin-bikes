"""
Convert the trained .joblib pipelines into NumPy-only .npz models.

The .joblib files stay the source of truth; this script derives the .npz files
that the deployed application loads, so that the app itself needs neither
scikit-learn nor SciPy (about 145 MB) nor joblib at runtime.

Every export is verified: the exported model must reproduce the original
pipeline's predictions on random inputs before the file is accepted.

Run after retraining a model:

    python machine_learning/export_models.py

Requires the development dependencies (pip install -r requirements-dev.txt).
"""
import sys
from pathlib import Path

import importlib.util

import joblib
import numpy as np


def _load_mlp_module():
    """
    Load app/mlp.py directly, without importing the `app` package.

    Importing the package would build the Flask app and try to load the very
    .npz files this script exists to produce, which fails on a fresh checkout.
    """
    path = Path(__file__).resolve().parents[1] / "app" / "mlp.py"
    spec = importlib.util.spec_from_file_location("app_mlp", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MlpPipeline = _load_mlp_module().MlpPipeline

MODEL_DIR = Path(__file__).resolve().parent / "output_model"
MODEL_NAMES = (
    "bike_availability_mlp_pipeline",
    "bike_stands_mlp_pipeline",
)

# Predictions must match to floating-point noise, not merely "closely": the
# exported model is meant to be the same function, not an approximation of it.
TOLERANCE = 1e-9
VERIFY_SAMPLES = 500


def export(name: str) -> Path:
    """Export one pipeline to .npz and verify it against the original."""
    source = MODEL_DIR / f"{name}.joblib"
    destination = MODEL_DIR / f"{name}.npz"

    pipeline = joblib.load(source)
    scaler = pipeline.named_steps["scaler"]
    mlp = pipeline.named_steps["mlp"]

    # The NumPy implementation applies both a shift and a scale unconditionally.
    if not (scaler.with_mean and scaler.with_std):
        raise ValueError(
            f"{name}: scaler has with_mean={scaler.with_mean}, "
            f"with_std={scaler.with_std}; app/mlp.py assumes both are enabled"
        )

    arrays = {
        "feature_names": np.asarray(pipeline.feature_names_in_, dtype=str),
        "mean": np.asarray(scaler.mean_, dtype=float),
        "scale": np.asarray(scaler.scale_, dtype=float),
        "layer_count": np.asarray(len(mlp.coefs_)),
        "activation": np.asarray(mlp.activation),
        "out_activation": np.asarray(mlp.out_activation_),
    }
    for index, (weight, bias) in enumerate(zip(mlp.coefs_, mlp.intercepts_)):
        arrays[f"weight_{index}"] = np.asarray(weight, dtype=float)
        arrays[f"bias_{index}"] = np.asarray(bias, dtype=float)

    np.savez_compressed(destination, **arrays)

    verify(pipeline, MlpPipeline.load(destination), name)
    return destination


def verify(original, exported: MlpPipeline, name: str) -> None:
    """Fail loudly if the exported model disagrees with the original."""
    feature_count = len(original.feature_names_in_)
    rng = np.random.default_rng(0)

    # A spread of magnitudes, plus the all-zero row, since most real inputs are
    # mostly zeros: only one of the 100+ station one-hot columns is ever set.
    samples = np.vstack([
        np.zeros((1, feature_count)),
        rng.normal(0.0, 1.0, (VERIFY_SAMPLES, feature_count)),
        rng.normal(0.0, 1000.0, (VERIFY_SAMPLES, feature_count)),
    ])

    difference = np.max(np.abs(original.predict(samples) - exported.predict(samples)))
    if difference > TOLERANCE:
        raise AssertionError(
            f"{name}: exported model differs from the original by {difference:.3e}"
        )
    print(f"  verified against {len(samples)} samples, max difference {difference:.3e}")


def main() -> int:
    for name in MODEL_NAMES:
        print(f"exporting {name}")
        destination = export(name)
        size_kb = destination.stat().st_size / 1024
        print(f"  wrote {destination.name} ({size_kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
