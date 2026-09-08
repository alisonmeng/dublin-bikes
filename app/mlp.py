"""
Pure-NumPy inference for the trained MLP pipelines.

Each model is a ``StandardScaler`` followed by an ``MLPRegressor``, which at
prediction time is only a standardisation and a short chain of matrix
multiplications. Reimplementing that here lets the deployed application drop
scikit-learn and SciPy -- together roughly 145 MB -- which is the difference
between comfortably fitting the hosting bundle size limit and scraping past it.
It also removes several seconds of import time from every cold start.

The ``.joblib`` pipelines remain the source of truth. ``export_models.py``
converts them to the ``.npz`` files loaded here and checks that both paths
produce the same predictions.

Loading is pickle-free (``allow_pickle=False``), so unlike ``joblib.load`` it
cannot execute code from the model file.
"""
from pathlib import Path

import numpy as np

# The activations scikit-learn's MLPRegressor can be configured with.
ACTIVATIONS = {
    "identity": lambda x: x,
    "relu": lambda x: np.maximum(x, 0.0),
    "tanh": np.tanh,
    "logistic": lambda x: 1.0 / (1.0 + np.exp(-x)),
}


class MlpPipeline:
    """
    A scaler and a multi-layer perceptron.

    Exposes the two members of the scikit-learn Pipeline API that the
    prediction routes actually use -- ``feature_names_in_`` and ``predict`` --
    so it is a drop-in replacement for the object that used to be unpickled.
    """

    def __init__(self, feature_names_in_, mean, scale, weights, biases,
                 activation: str = "relu", out_activation: str = "identity"):
        self.feature_names_in_ = feature_names_in_
        self._mean = mean
        self._scale = scale
        self._weights = weights
        self._biases = biases

        for name in (activation, out_activation):
            if name not in ACTIVATIONS:
                raise ValueError(f"unsupported activation: {name!r}")

        self._activation = ACTIVATIONS[activation]
        self._out_activation = ACTIVATIONS[out_activation]

    @classmethod
    def load(cls, path: Path) -> "MlpPipeline":
        """Load a model exported by machine_learning/export_models.py."""
        with np.load(path, allow_pickle=False) as data:
            layer_count = int(data["layer_count"])
            return cls(
                feature_names_in_=data["feature_names"],
                mean=data["mean"],
                scale=data["scale"],
                weights=[data[f"weight_{i}"] for i in range(layer_count)],
                biases=[data[f"bias_{i}"] for i in range(layer_count)],
                activation=str(data["activation"]),
                out_activation=str(data["out_activation"]),
            )

    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        Return one prediction per row of ``features``.

        Columns must already be in ``feature_names_in_`` order; see
        ``_build_feature_matrix`` in the prediction routes.
        """
        layer = (np.asarray(features, dtype=float) - self._mean) / self._scale

        for weight, bias in zip(self._weights[:-1], self._biases[:-1]):
            layer = self._activation(layer @ weight + bias)

        output = self._out_activation(layer @ self._weights[-1] + self._biases[-1])

        # MLPRegressor ravels its single-output predictions; match that.
        return output.ravel()
