"""
캘리브레이션 검증 (Validation)
==============================
LOO (Leave-One-Out) CV와 n/p 비율 체크.

- n/p 비율: 데이터 수 / 변수 수 ≥ 10 유지 (과적합 방지 가드레일)
- LOO CV: 한 편을 테스트로 빼고 나머지로 학습, 예측 오차 측정
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from ..core.axes import ALL_AXES


def check_np_ratio(df: pd.DataFrame, n_variables: int = 6, threshold: float = 10.0) -> dict:
    """n/p 비율 검증. threshold 미달 시 경고."""
    n = len(df)
    ratio = n / n_variables
    return {
        "n_samples": n,
        "n_variables": n_variables,
        "np_ratio": round(ratio, 2),
        "threshold": threshold,
        "passes": ratio >= threshold,
        "warning": (
            None if ratio >= threshold
            else f"n/p 비율 {ratio:.1f} < {threshold}. 과적합 위험."
        ),
    }


def loo_cv_ridge(df: pd.DataFrame, target: str, alpha: float = 1.0) -> dict:
    """Ridge 회귀 LOO CV. MAE/RMSE 반환."""
    X = df[list(ALL_AXES)].values
    y = df[target].values
    n = len(X)
    if n < 5:
        return {"error": f"Too few samples ({n})"}

    errors = []
    for i in range(n):
        X_train = np.delete(X, i, axis=0)
        y_train = np.delete(y, i)
        X_test = X[i:i+1]
        y_true = y[i]

        scaler = StandardScaler().fit(X_train)
        X_train_s = scaler.transform(X_train)
        X_test_s = scaler.transform(X_test)

        model = Ridge(alpha=alpha).fit(X_train_s, y_train)
        y_pred = model.predict(X_test_s)[0]
        errors.append(y_pred - y_true)

    errors = np.array(errors)
    return {
        "n_samples": n,
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "mean_error": float(np.mean(errors)),
        "std_error": float(np.std(errors)),
    }


def full_validation_report(df: pd.DataFrame, target: str) -> dict:
    """전체 검증 리포트."""
    return {
        "np_check": check_np_ratio(df, n_variables=len(ALL_AXES)),
        "loo_cv_ridge": loo_cv_ridge(df, target),
        "data_size": len(df),
        "target": target,
    }
