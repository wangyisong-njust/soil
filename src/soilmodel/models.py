from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.cross_decomposition import PLSRegression
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.compose import TransformedTargetRegressor


@dataclass(frozen=True)
class ModelSpec:
    name: str
    estimator: object
    family: str
    tree_like: bool = False


class LogImputedNGBoost(BaseEstimator, RegressorMixin):
    def __init__(self, n_estimators: int = 180, learning_rate: float = 0.035, random_state: int = 42):
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.random_state = random_state

    def fit(self, X, y):
        from ngboost import NGBRegressor

        self.imputer_ = SimpleImputer(strategy="median")
        x_imp = self.imputer_.fit_transform(X)
        self.model_ = NGBRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            random_state=self.random_state,
            verbose=False,
        )
        self.model_.fit(x_imp, np.log1p(np.asarray(y, dtype=float)))
        self.n_features_in_ = x_imp.shape[1]
        return self

    def predict(self, X):
        x_imp = self.imputer_.transform(X)
        pred = self.model_.predict(x_imp)
        return np.expm1(np.asarray(pred, dtype=float))


def _wrap(estimator, scaled: bool = False) -> TransformedTargetRegressor:
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if scaled:
        steps.append(("scaler", StandardScaler()))
    steps.append(("model", estimator))
    return TransformedTargetRegressor(
        regressor=Pipeline(steps),
        func=np.log1p,
        inverse_func=np.expm1,
        check_inverse=False,
    )


def _wrap_raw(estimator, scaled: bool = False) -> Pipeline:
    steps = [("imputer", SimpleImputer(strategy="median"))]
    if scaled:
        steps.append(("scaler", StandardScaler()))
    steps.append(("model", estimator))
    return Pipeline(steps)


def build_model_registry(n_features: int, random_state: int = 42, n_jobs: int = -1) -> dict[str, ModelSpec]:
    specs: dict[str, ModelSpec] = {}

    specs["RF"] = ModelSpec(
        "RF",
        _wrap(
            RandomForestRegressor(
                n_estimators=220,
                max_features=0.8,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=n_jobs,
            )
        ),
        family="bagging",
        tree_like=True,
    )
    specs["RF_raw"] = ModelSpec(
        "RF_raw",
        _wrap_raw(
            RandomForestRegressor(
                n_estimators=260,
                max_features=0.8,
                min_samples_leaf=1,
                random_state=random_state,
                n_jobs=n_jobs,
            )
        ),
        family="bagging_raw",
        tree_like=True,
    )
    specs["ExtraTrees"] = ModelSpec(
        "ExtraTrees",
        _wrap(
            ExtraTreesRegressor(
                n_estimators=220,
                max_features=0.85,
                min_samples_leaf=2,
                random_state=random_state,
                n_jobs=n_jobs,
            )
        ),
        family="bagging",
        tree_like=True,
    )
    specs["ExtraTrees_raw"] = ModelSpec(
        "ExtraTrees_raw",
        _wrap_raw(
            ExtraTreesRegressor(
                n_estimators=260,
                max_features=0.85,
                min_samples_leaf=1,
                random_state=random_state,
                n_jobs=n_jobs,
            )
        ),
        family="bagging_raw",
        tree_like=True,
    )
    specs["HistGBR"] = ModelSpec(
        "HistGBR",
        _wrap(
            HistGradientBoostingRegressor(
                max_iter=220,
                learning_rate=0.045,
                max_leaf_nodes=31,
                l2_regularization=0.05,
                random_state=random_state,
            )
        ),
        family="boosting",
        tree_like=True,
    )
    specs["HistGBR_raw"] = ModelSpec(
        "HistGBR_raw",
        _wrap_raw(
            HistGradientBoostingRegressor(
                max_iter=260,
                learning_rate=0.04,
                max_leaf_nodes=31,
                l2_regularization=0.05,
                random_state=random_state,
            )
        ),
        family="boosting_raw",
        tree_like=True,
    )
    specs["ElasticNet"] = ModelSpec(
        "ElasticNet",
        _wrap(ElasticNet(alpha=0.01, l1_ratio=0.25, max_iter=30000, random_state=random_state), scaled=True),
        family="linear",
    )
    specs["PLSR"] = ModelSpec(
        "PLSR",
        _wrap(PLSRegression(n_components=max(1, min(8, n_features - 1))), scaled=True),
        family="linear",
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            from xgboost import XGBRegressor

            specs["XGBoost"] = ModelSpec(
                "XGBoost",
                _wrap(
                    XGBRegressor(
                        n_estimators=260,
                        learning_rate=0.035,
                        max_depth=3,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        reg_lambda=2.0,
                        objective="reg:squarederror",
                        tree_method="hist",
                        random_state=random_state,
                        n_jobs=n_jobs,
                        verbosity=0,
                    )
                ),
                family="boosting",
                tree_like=True,
            )
            specs["XGBoost_raw"] = ModelSpec(
                "XGBoost_raw",
                _wrap_raw(
                    XGBRegressor(
                        n_estimators=300,
                        learning_rate=0.035,
                        max_depth=3,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        reg_lambda=2.0,
                        objective="reg:squarederror",
                        tree_method="hist",
                        random_state=random_state,
                        n_jobs=n_jobs,
                        verbosity=0,
                    )
                ),
                family="boosting_raw",
                tree_like=True,
            )
        except Exception:
            pass

        try:
            from lightgbm import LGBMRegressor

            specs["LightGBM"] = ModelSpec(
                "LightGBM",
                _wrap(
                    LGBMRegressor(
                        n_estimators=280,
                        learning_rate=0.035,
                        num_leaves=31,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        min_child_samples=12,
                        reg_lambda=1.0,
                        random_state=random_state,
                        n_jobs=n_jobs,
                        verbose=-1,
                    )
                ),
                family="boosting",
                tree_like=True,
            )
            specs["LightGBM_raw"] = ModelSpec(
                "LightGBM_raw",
                _wrap_raw(
                    LGBMRegressor(
                        n_estimators=300,
                        learning_rate=0.035,
                        num_leaves=31,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        min_child_samples=8,
                        reg_lambda=2.0,
                        random_state=random_state,
                        n_jobs=n_jobs,
                        verbose=-1,
                    )
                ),
                family="boosting_raw",
                tree_like=True,
            )
        except Exception:
            pass

        try:
            from catboost import CatBoostRegressor

            specs["CatBoost"] = ModelSpec(
                "CatBoost",
                _wrap(
                    CatBoostRegressor(
                        iterations=260,
                        learning_rate=0.035,
                        depth=5,
                        l2_leaf_reg=3.0,
                        loss_function="RMSE",
                        random_seed=random_state,
                        verbose=False,
                        allow_writing_files=False,
                        thread_count=n_jobs if n_jobs and n_jobs > 0 else -1,
                    )
                ),
                family="boosting",
                tree_like=True,
            )
            specs["CatBoost_raw"] = ModelSpec(
                "CatBoost_raw",
                _wrap_raw(
                    CatBoostRegressor(
                        iterations=300,
                        learning_rate=0.035,
                        depth=5,
                        l2_leaf_reg=3.0,
                        loss_function="RMSE",
                        random_seed=random_state,
                        verbose=False,
                        allow_writing_files=False,
                        thread_count=n_jobs if n_jobs and n_jobs > 0 else -1,
                    )
                ),
                family="boosting_raw",
                tree_like=True,
            )
        except Exception:
            pass

        try:
            from ngboost import NGBRegressor  # noqa: F401

            specs["NGBoost"] = ModelSpec(
                "NGBoost",
                LogImputedNGBoost(n_estimators=180, learning_rate=0.035, random_state=random_state),
                family="boosting",
            )
        except Exception:
            pass

    return specs


def fresh_model(spec: ModelSpec):
    return clone(spec.estimator)


def final_estimator_from_wrapped(model):
    if hasattr(model, "regressor_"):
        pipe = model.regressor_
    else:
        pipe = model
    return pipe.named_steps["model"]


def transformed_features_from_wrapped(model, x):
    if hasattr(model, "regressor_"):
        pipe = model.regressor_
    else:
        pipe = model
    return pipe[:-1].transform(x)
