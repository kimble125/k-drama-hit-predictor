"""
가중치 실증 캘리브레이션 (6-method ensemble)
==============================================
종영작 데이터로부터 각 축의 최적 가중치를 학습.

6개 방법:
    1. Spearman 순위상관 (비선형 단조)
    2. OLS 표준화 계수
    3. Ridge (과적합 방지)
    4. Random Forest Feature Importance
    5. Gradient Boosting Feature Importance
    6. Naive Bayes (주상필 2019 최고 성능)
       → 분류형이므로 중앙값 기준 이진화 후 상관 계수 사용

가드레일:
    - n/p ratio ≥ 10 유지
    - 종영작 < 50편이면 단순 모델만 (NB/OLS/Ridge)
    - 복잡 모델(RF, GB)은 데이터 충분할 때만
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import StandardScaler

from ..core.axes import ALL_AXES


# ────────────────────────────────────────────────────────────────
# 개별 방법
# ────────────────────────────────────────────────────────────────
def spearman_importance(df: pd.DataFrame, target: str) -> dict[str, float]:
    return {a: abs(df[a].corr(df[target], method="spearman")) for a in ALL_AXES}


def ols_importance(df: pd.DataFrame, target: str) -> dict[str, float]:
    X = StandardScaler().fit_transform(df[list(ALL_AXES)].values)
    y = df[target].values
    lr = LinearRegression().fit(X, y)
    return {a: abs(c) for a, c in zip(ALL_AXES, lr.coef_)}


def ridge_importance(df: pd.DataFrame, target: str, alpha: float = 1.0) -> dict[str, float]:
    X = StandardScaler().fit_transform(df[list(ALL_AXES)].values)
    y = df[target].values
    r = Ridge(alpha=alpha).fit(X, y)
    return {a: abs(c) for a, c in zip(ALL_AXES, r.coef_)}


def rf_importance(df: pd.DataFrame, target: str, n_estimators: int = 100, max_depth: int = 3) -> dict[str, float]:
    X = df[list(ALL_AXES)].values
    y = df[target].values
    rf = RandomForestRegressor(
        n_estimators=n_estimators, max_depth=max_depth, random_state=42
    ).fit(X, y)
    return dict(zip(ALL_AXES, rf.feature_importances_))


def gb_importance(df: pd.DataFrame, target: str, n_estimators: int = 50, max_depth: int = 2) -> dict[str, float]:
    X = df[list(ALL_AXES)].values
    y = df[target].values
    gb = GradientBoostingRegressor(
        n_estimators=n_estimators, max_depth=max_depth, random_state=42
    ).fit(X, y)
    return dict(zip(ALL_AXES, gb.feature_importances_))


def naive_bayes_importance(df: pd.DataFrame, target: str) -> dict[str, float]:
    """Gaussian NB 기반 중요도.

    NB는 분류 모델이라 target을 중앙값 기준 이진화:
        - 중앙값 이상 → 1 (흥행)
        - 미만 → 0 (부진)
    각 축의 NB log-likelihood 기여도를 중요도로 사용 (근사).
    """
    y = df[target].values
    y_bin = (y > np.median(y)).astype(int)

    importances = {}
    for axis in ALL_AXES:
        X_single = df[[axis]].values
        try:
            nb = GaussianNB().fit(X_single, y_bin)
            # 클래스 간 평균 차이 / 표준편차로 discriminability 근사
            mean_diff = abs(nb.theta_[1][0] - nb.theta_[0][0])
            avg_std = np.sqrt((nb.var_[0][0] + nb.var_[1][0]) / 2)
            importances[axis] = mean_diff / (avg_std + 1e-6)
        except Exception:
            importances[axis] = 0.0
    return importances


# ────────────────────────────────────────────────────────────────
# 앙상블
# ────────────────────────────────────────────────────────────────
def ensemble_weights(
    df: pd.DataFrame,
    target: str,
    total: float = 60.0,
    use_complex_models: Optional[bool] = None,
) -> dict[str, float]:
    """6-method ensemble (데이터 적으면 단순 모델만).

    Args:
        use_complex_models: True면 RF/GB 포함. None이면 len(df)>=50 기준 자동.
    """
    if use_complex_models is None:
        use_complex_models = len(df) >= 50

    methods = [
        spearman_importance(df, target),
        ols_importance(df, target),
        ridge_importance(df, target),
        naive_bayes_importance(df, target),
    ]
    if use_complex_models:
        methods.append(rf_importance(df, target))
        methods.append(gb_importance(df, target))

    # 각 방법을 합=1로 정규화 후 평균
    agg = {a: [] for a in ALL_AXES}
    for m in methods:
        s = sum(m.values()) or 1.0
        for a in ALL_AXES:
            agg[a].append(m[a] / s)

    avg = {a: float(np.mean(agg[a])) for a in ALL_AXES}
    total_avg = sum(avg.values()) or 1.0
    weights = {a: round(avg[a] / total_avg * total, 1) for a in ALL_AXES}

    # 반올림 오차 보정
    diff = round(total - sum(weights.values()), 1)
    if diff != 0:
        top = max(weights, key=weights.get)
        weights[top] = round(weights[top] + diff, 1)

    return weights


# ────────────────────────────────────────────────────────────────
# 리포트
# ────────────────────────────────────────────────────────────────
def correlation_report(df: pd.DataFrame, target: str) -> pd.DataFrame:
    rows = []
    for a in ALL_AXES:
        rows.append({
            "axis": a,
            "pearson": df[a].corr(df[target]),
            "spearman": df[a].corr(df[target], method="spearman"),
            "n": df[a].notna().sum(),
        })
    return pd.DataFrame(rows).sort_values("spearman", ascending=False, key=abs)


def all_methods_report(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """모든 방법의 상대 중요도를 한 테이블에."""
    methods = {
        "spearman": spearman_importance(df, target),
        "ols": ols_importance(df, target),
        "ridge": ridge_importance(df, target),
        "naive_bayes": naive_bayes_importance(df, target),
    }
    if len(df) >= 50:
        methods["rf"] = rf_importance(df, target)
        methods["gb"] = gb_importance(df, target)

    # 각 방법을 상대 % 로 정규화
    rows = []
    for axis in ALL_AXES:
        row = {"axis": axis}
        for mname, mvals in methods.items():
            s = sum(mvals.values()) or 1.0
            row[mname] = round(mvals[axis] / s * 100, 1)
        rows.append(row)
    return pd.DataFrame(rows)
