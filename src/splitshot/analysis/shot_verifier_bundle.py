from __future__ import annotations

# The verifier bundle is intentionally plain Python/NumPy data so packaged
# inference remains deterministic and does not add a runtime dependency.
MODEL_METADATA = {
    "version": "wearer-shot-verifier-v1",
    "feature_schema_version": "shot-context-v1",
    "context_window_ms": 640,
    "feature_dimensions": 121,
    "training_source": "stage-relative bootstrap; replace only with verified-corpus training",
}

# Sparse linear bootstrap coefficients. The corpus trainer emits a fully
# learned dense replacement after manual labels pass the locked-test gates.
BIAS = -2.61
WEIGHTS = {
    4: 0.029166666666666667,  # RMS above stage-local noise
    7: 8.0,  # temporal energy entropy
    11: -0.45,  # 0-10 ms energy
    13: 0.45,  # 25-50 ms energy
}
