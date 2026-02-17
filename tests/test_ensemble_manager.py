import os
from tempfile import TemporaryDirectory

import pandas as pd

from src.ml.ensemble_manager import EnsembleManager


def test_predict_proba_returns_neutral_when_not_trained():
    with TemporaryDirectory() as tmpdir:
        em = EnsembleManager(models_dir=tmpdir)
        em.is_trained = False
        prob = em.predict_proba(pd.DataFrame())
        assert prob == 0.5


def test_load_models_handles_corrupted_file_and_falls_back(monkeypatch):
    with TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "rf_model.pkl")
        with open(path, "wb") as f:
            f.write(b"invalid")

        def fail_load(p):
            raise RuntimeError("corrupted")

        monkeypatch.setattr("src.ml.ensemble_manager.joblib.load", fail_load)

        em = EnsembleManager(models_dir=tmpdir)
        df = pd.DataFrame()
        prob = em.predict_proba(df)
        assert prob == 0.5


def test_predict_proba_handles_model_error_and_returns_neutral(monkeypatch):
    with TemporaryDirectory() as tmpdir:
        em = EnsembleManager(models_dir=tmpdir)

        class FailingModel:
            def predict_proba(self, X):
                raise RuntimeError("boom")

        em.models = {"rf": FailingModel()}
        em.is_trained = True

        def fake_prepare(df):
            return pd.DataFrame([{"a": 1.0}])

        monkeypatch.setattr(em, "prepare_features", fake_prepare)

        df = pd.DataFrame([{"close": 1.0}])
        prob = em.predict_proba(df)
        assert prob == 0.5

