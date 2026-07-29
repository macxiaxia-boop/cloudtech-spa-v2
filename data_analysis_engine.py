"""
数据分析引擎 v1.0 — 智能数据探索与可视化
==========================================
非技术创业者的数据分析助手：导入数据 → 自动分析 → 生成图表 → AI洞察 → 导出报告
对标: Julius AI / ChatGPT Advanced Data Analysis

功能:
  - 数据导入: CSV / Excel / JSON
  - 自动分析: 统计摘要 / 趋势检测 / 异常值检测 / 类型自动识别
  - 可视化: 柱状图 / 折线图 / 饼图 / 散点图 / 热力图
  - AI洞察: 自然语言解读数据含义
  - 导出: 图表PNG + Markdown报告 + JSON数据

用法:
  python data_analysis_engine.py --input data.csv --output both
  python data_analysis_engine.py --input data.xlsx --sheet "Sheet1" --charts all
  python data_analysis_engine.py --input data.json --focus "revenue,users" --lang zh

集成:
  学习循环: python tools/core/learning-loop.py record --domain data-analysis --task-type analysis
  图表输出: D:/个人文件/AI/04 素材资产系统/数据图表/
  报告输出: D:/个人文件/AI/05 项目生产系统/数据分析报告/
"""
import argparse
import json
import os
import sys
import warnings
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ---- 依赖检查 ----
_MISSING_DEPS = []
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
except ImportError:
    _MISSING_DEPS.append("matplotlib")

try:
    import seaborn as sns
except ImportError:
    _MISSING_DEPS.append("seaborn")

try:
    import openpyxl  # noqa: F401
except ImportError:
    _MISSING_DEPS.append("openpyxl")

if _MISSING_DEPS:
    print(f"[错误] 缺少依赖: {', '.join(_MISSING_DEPS)}")
    print(f"请运行: pip install {' '.join(_MISSING_DEPS)}")
    sys.exit(1)

# ---- 路径配置 ----
HOME = Path(os.environ.get("USERPROFILE", os.path.expanduser("~")))
TOOLS_CORE = HOME / ".openclaw" / "tools" / "core"
CHART_DIR = Path("D:/个人文件/AI/04 素材资产系统/数据图表")
REPORT_DIR = Path("D:/个人文件/AI/05 项目生产系统/数据分析报告")
LEARNING_LOOP = TOOLS_CORE / "learning-loop.py"

# ---- 中文字体设置 ----
_ZH_FONT = None
_ZH_FONT_CANDIDATES = [
    "Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC",
    "Source Han Sans SC", "WenQuanYi Micro Hei", "Arial Unicode MS",
]
for _fname in _ZH_FONT_CANDIDATES:
    try:
        _fp = fm.findfont(_fname, fallback_to_default=False)
        if _fp:
            _ZH_FONT = _fname
            break
    except Exception:
        continue

plt.rcParams["font.family"] = _ZH_FONT if _ZH_FONT else "sans-serif"
plt.rcParams["axes.unicode_minus"] = False

CHART_COLORS = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
                "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1"]


# ======================================================================
#  工具函数
# ======================================================================

def _ensure_dir(path: Path) -> Path:
    """Ensure directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _safe_filename(original: str) -> str:
    """Strip extension from a filename for use as a slug."""
    return Path(original).stem


def _normalize_column(name: str) -> str:
    """Clean column name for display."""
    return str(name).strip().replace("_", " ").replace("-", " ").title()


def _log_to_learning_loop(domain: str, task_type: str, outcome: str,
                          root_cause: str = "", fix: str = ""):
    """Record execution in learning loop if available."""
    if not LEARNING_LOOP.exists():
        return
    try:
        import subprocess
        cmd = [
            sys.executable, str(LEARNING_LOOP),
            "record",
            "--domain", domain,
            "--task-type", task_type,
            "--outcome", outcome,
        ]
        if root_cause:
            cmd += ["--root-cause", root_cause]
        if fix:
            cmd += ["--fix", fix]
        subprocess.run(cmd, capture_output=True, timeout=10)
    except Exception:
        pass


# ======================================================================
#  数据加载
# ======================================================================

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


def load_data(filepath: str, sheet: str = None) -> pd.DataFrame:
    """
    Load data from CSV, Excel, or JSON file.

    Args:
        filepath: Path to input file.
        sheet: Excel sheet name (ignored for CSV/JSON).

    Returns:
        DataFrame with loaded data.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If file format is unsupported.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}，支持: {', '.join(SUPPORTED_EXTENSIONS)}")

    if ext == ".csv":
        # Try multiple encodings for auto-detection
        for enc in ["utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"]:
            try:
                df = pd.read_csv(path, encoding=enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            df = pd.read_csv(path, encoding="utf-8", errors="replace")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=sheet or 0)
    elif ext == ".json":
        df = pd.read_json(path, encoding="utf-8")

    # Clean column names (strip whitespace)
    df.columns = [str(c).strip() for c in df.columns]

    # Drop completely empty columns
    df = df.dropna(axis=1, how="all")

    print(f"[加载] {path.name} ({ext}) — {len(df)} 行 × {len(df.columns)} 列")
    return df


# ======================================================================
#  列类型自动检测
# ======================================================================

def detect_column_types(df: pd.DataFrame) -> dict:
    """
    Auto-detect column types: numeric, categorical, datetime, text.

    Returns:
        dict with keys: 'numeric', 'categorical', 'datetime', 'text', 'other'.
        Each value is a list of column names.
    """
    types = {"numeric": [], "categorical": [], "datetime": [], "text": [], "other": []}

    for col in df.columns:
        series = df[col].dropna()
        if series.empty:
            types["other"].append(col)
            continue

        # Datetime detection (direct dtype)
        if pd.api.types.is_datetime64_any_dtype(series):
            types["datetime"].append(col)
            continue

        # Numeric detection
        if pd.api.types.is_numeric_dtype(series):
            unique_ratio = series.nunique() / max(len(series), 1)
            if series.nunique() <= 10 and unique_ratio < 0.05:
                types["categorical"].append(col)
            else:
                types["numeric"].append(col)
            continue

        # Object / string type
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            sample = series.iloc[0] if len(series) > 0 else ""
            sample_str = str(sample).strip()

            # --- Date pattern check (before full parse, faster) ---
            has_date_pattern = (
                bool(sample_str and len(sample_str) <= 20 and
                     any(kw in sample_str for kw in ["-", "/", "年", "月", ".", ":"]) and
                     any(c.isdigit() for c in sample_str))
            )
            is_datetime = False
            if len(series) >= 3:
                try:
                    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
                    success_ratio = parsed.notna().sum() / max(len(series), 1)
                    if success_ratio > 0.7:
                        types["datetime"].append(col)
                        is_datetime = True
                except (ValueError, TypeError, Exception):
                    # fallback: check if sample looks date-like
                    if has_date_pattern:
                        try:
                            parsed = pd.to_datetime(series, errors="coerce")
                            if parsed.notna().sum() / max(len(series), 1) > 0.7:
                                types["datetime"].append(col)
                                is_datetime = True
                        except Exception:
                            pass
            if is_datetime:
                continue

            # Categorical: low cardinality
            unique_ratio = series.nunique() / max(len(series), 1)
            if unique_ratio < 0.3 or series.nunique() <= 25:
                types["categorical"].append(col)
            elif series.str.len().mean() > 50:
                types["text"].append(col)
            else:
                types["categorical"].append(col)
            continue

        types["other"].append(col)

    return types


# ======================================================================
#  统计分析
# ======================================================================

def analyze_numeric(series: pd.Series) -> dict:
    """
    Full statistical analysis for a numeric column.

    Returns dict with: count, mean, median, std, min, max, q1, q3,
    iqr, skewness, missing_pct, outliers.
    """
    s = series.dropna()
    if s.empty:
        return {"count": 0, "error": "无有效数据"}

    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = s[(s < lower_bound) | (s > upper_bound)]

    stats = {
        "count": int(len(s)),
        "missing": int(series.isna().sum()),
        "missing_pct": round(series.isna().mean() * 100, 1),
        "mean": round(float(s.mean()), 2),
        "median": round(float(s.median()), 2),
        "std": round(float(s.std()), 2),
        "min": round(float(s.min()), 2),
        "max": round(float(s.max()), 2),
        "q1": round(float(q1), 2),
        "q3": round(float(q3), 2),
        "iqr": round(float(iqr), 2),
        "skewness": round(float(s.skew()), 3),
        "kurtosis": round(float(s.kurtosis()), 3),
        "outlier_count": int(len(outliers)),
        "outlier_pct": round(len(outliers) / max(len(s), 1) * 100, 1),
        "outlier_min": round(float(outliers.min()), 2) if not outliers.empty else None,
        "outlier_max": round(float(outliers.max()), 2) if not outliers.empty else None,
    }
    return stats


def analyze_categorical(series: pd.Series, top_n: int = 10) -> dict:
    """
    Frequency analysis for a categorical column.

    Returns dict with: count, unique_count, top_values, entropy.
    """
    s = series.dropna()
    if s.empty:
        return {"count": 0, "error": "无有效数据"}

    value_counts = s.value_counts()
    total = len(s)
    top_values = []
    for val, cnt in value_counts.head(top_n).items():
        top_values.append({
            "value": str(val),
            "count": int(cnt),
            "pct": round(cnt / total * 100, 1),
        })

    # Shannon entropy as a diversity measure
    probs = value_counts / total
    entropy = -sum(p * np.log2(p) for p in probs if p > 0)

    return {
        "count": int(len(s)),
        "missing": int(series.isna().sum()),
        "unique": int(s.nunique()),
        "top_values": top_values,
        "top_value": str(value_counts.index[0]) if not value_counts.empty else "",
        "top_pct": round(value_counts.iloc[0] / total * 100, 1) if not value_counts.empty else 0,
        "entropy": round(float(entropy), 3),
    }


def analyze_correlation(df: pd.DataFrame, numeric_cols: list) -> dict:
    """
    Compute correlation matrix for numeric columns.

    Returns dict with: matrix (list of lists), pairs (sorted corr pairs).
    """
    if len(numeric_cols) < 2:
        return {"matrix": [], "pairs": [], "note": "需要至少2个数值列"}

    corr = df[numeric_cols].corr(method="pearson")
    matrix = {
        "columns": [str(c) for c in corr.columns],
        "index": [str(c) for c in corr.index],
        "values": [[round(float(v), 4) for v in row] for row in corr.values],
    }

    # Extract top correlated pairs (excluding self-correlation)
    pairs = []
    for i, col_i in enumerate(numeric_cols):
        for j, col_j in enumerate(numeric_cols):
            if i < j:
                val = corr.iloc[i, j]
                pairs.append({
                    "x": str(col_i),
                    "y": str(col_j),
                    "correlation": round(float(val), 3),
                    "strength": "强" if abs(val) >= 0.7 else ("中" if abs(val) >= 0.4 else "弱"),
                    "direction": "正相关" if val > 0 else "负相关",
                })

    pairs.sort(key=lambda p: abs(p["correlation"]), reverse=True)

    return {"matrix": matrix, "pairs": pairs}


def detect_trend(df: pd.DataFrame, datetime_col: str, value_col: str) -> dict:
    """
    Simple time series trend detection.

    Returns dict with trend direction, slope estimate, seasonality note.
    """
    ts = df[[datetime_col, value_col]].dropna().copy()
    if len(ts) < 3:
        return {"note": "数据点不足，至少需要3个点"}

    ts[datetime_col] = pd.to_datetime(ts[datetime_col], errors="coerce")
    ts = ts.sort_values(datetime_col)
    ts = ts.dropna(subset=[datetime_col])
    if len(ts) < 3:
        return {"note": "有效日期数据不足"}

    # Simple linear trend via polyfit
    x = np.arange(len(ts))
    y = ts[value_col].values.astype(float)
    slope, intercept = np.polyfit(x, y, 1)
    trend_line = intercept + slope * x

    # Direction
    if slope > 0:
        direction = "上升趋势"
        strength = "强劲" if slope > y.std() / max(len(y), 1) else "温和"
    elif slope < 0:
        direction = "下降趋势"
        strength = "显著" if abs(slope) > y.std() / max(len(y), 1) else "温和"
    else:
        direction = "平稳"
        strength = "无明显趋势"

    # Simple seasonality check (autocorrelation at lag ~ period/4)
    seasonality = None
    if len(y) >= 8:
        autocorr = np.corrcoef(y[:-1], y[1:])[0, 1]
        seasonality = "可能存在周期性" if abs(autocorr) > 0.5 else "无明显周期"

    return {
        "direction": direction,
        "strength": strength,
        "slope": round(float(slope), 4),
        "intercept": round(float(intercept), 2),
        "trend_line": [round(float(v), 2) for v in trend_line],
        "seasonality": seasonality,
        "data_points": len(ts),
        "start_date": str(ts[datetime_col].min().date()),
        "end_date": str(ts[datetime_col].max().date()),
    }


# ======================================================================
#  AI 洞察生成
# ======================================================================

def generate_insights(df: pd.DataFrame, col_types: dict,
                      num_stats: dict, cat_stats: dict,
                      corr_result: dict, trend_result: dict) -> list:
    """
    Generate 3-5 key business insights in Chinese based on actual data patterns.

    Returns a list of insight dicts: {title, content, type}.
    """
    insights = []
    n_rows, n_cols = df.shape

    # --- Insight 1: Data overview ---
    total_cells = n_rows * n_cols
    missing_total = sum(
        int(df[col].isna().sum()) for col in df.columns
    )
    completeness = round((1 - missing_total / max(total_cells, 1)) * 100, 1)
    insights.append({
        "title": "数据完整性",
        "content": (
            f"数据集共 {n_rows} 行、{n_cols} 列，数据完整率 {completeness}%。"
            f"{'质量良好，可以支撑可靠分析。' if completeness >= 90 else '存在缺失值，建议补充后再做关键决策。'}"
        ),
        "type": "overview",
    })

    # --- Insight 2: Key numeric findings ---
    num_cols = col_types.get("numeric", [])
    if len(num_stats) > 0:
        # Find most spread / interesting column
        high_variation = []
        for col, stats in num_stats.items():
            if "error" in stats:
                continue
            cv = stats["std"] / max(abs(stats["mean"]), 0.001) if stats["mean"] != 0 else 0
            if cv > 0.5:
                high_variation.append((col, cv, stats))

        if high_variation:
            high_variation.sort(key=lambda x: -x[1])
            top_var_col, top_cv, top_s = high_variation[0]
            insights.append({
                "title": f"高波动指标: {_normalize_column(top_var_col)}",
                "content": (
                    f"{_normalize_column(top_var_col)} 波动较大 (变异系数 {top_cv:.1f})，"
                    f"范围从 {top_s['min']} 到 {top_s['max']}，"
                    f"均值 {top_s['mean']}，中位数 {top_s['median']}。"
                    f"存在 {top_s['outlier_count']} 个异常值 ({top_s['outlier_pct']}%)。"
                    "建议细分维度寻找波动原因。"
                ),
                "type": "numeric",
            })
        else:
            # Pick the first numeric column
            col = num_cols[0]
            s = num_stats.get(col, {})
            if "error" not in s:
                insights.append({
                    "title": f"核心指标: {_normalize_column(col)}",
                    "content": (
                        f"{_normalize_column(col)} 均值 {s['mean']}，中位数 {s['median']}，"
                        f"标准差 {s['std']}。"
                        f"偏度 {s['skewness']}，"
                        f"{'数据分布基本对称。' if abs(s['skewness']) < 0.5 else '数据存在偏态分布，需关注极端值影响。'}"
                    ),
                    "type": "numeric",
                })

    # --- Insight 3: Categorical findings ---
    cat_cols = col_types.get("categorical", [])
    if cat_stats:
        col = list(cat_stats.keys())[0]
        s = cat_stats[col]
        if "error" not in s and s["top_values"]:
            top = s["top_values"][0]
            insights.append({
                "title": f"分类分布: {_normalize_column(col)}",
                "content": (
                    f"{_normalize_column(col)} 有 {s['unique']} 个唯一值，"
                    f"TOP1 「{top['value']}」占比 {top['pct']}%。"
                    f"{'分布集中，头部效应明显。' if top['pct'] > 50 else '分布相对分散，多样性较好。'}"
                ),
                "type": "categorical",
            })

    # --- Insight 4: Correlation findings ---
    if corr_result.get("pairs"):
        strong_pairs = [p for p in corr_result["pairs"] if abs(p["correlation"]) >= 0.5]
        if strong_pairs:
            top_pair = strong_pairs[0]
            insights.append({
                "title": "关键变量关系",
                "content": (
                    f"发现 {len(strong_pairs)} 对强相关变量。最强关系: "
                    f"「{_normalize_column(top_pair['x'])}」与「{_normalize_column(top_pair['y'])}」"
                    f"({top_pair['direction']}，相关系数 {top_pair['correlation']})。"
                    f"{'建议深入分析因果关系。' if abs(top_pair['correlation']) >= 0.8 else '可作为交叉分析维度。'}"
                ),
                "type": "correlation",
            })

    # --- Insight 5: Trend findings ---
    if trend_result and "direction" in trend_result:
        insights.append({
            "title": f"趋势分析: {trend_result['direction']}",
            "content": (
                f"数据呈现{trend_result['strength']}{trend_result['direction']}"
                f"(斜率 {trend_result['slope']})。"
                f"{trend_result.get('seasonality', '')}。"
                f"时间跨度: {trend_result.get('start_date', 'N/A')} → {trend_result.get('end_date', 'N/A')}。"
            ),
            "type": "trend",
        })

    # Ensure at least 3 insights
    if len(insights) < 3:
        insights.append({
            "title": "数据维度说明",
            "content": (
                f"数据集包含 {n_rows} 条记录，涵盖 {num_cols}/{n_cols} 个数值变量。"
                f"建议增加更多维度数据以获得更深入洞察。"
            ),
            "type": "general",
        })

    return insights[:5]


# ======================================================================
#  图表生成
# ======================================================================

def _save_fig(fig, name: str, slug: str) -> str:
    """Save figure to chart directory, return filepath."""
    _ensure_dir(CHART_DIR)
    ts = _timestamp()
    filename = f"{slug}_{name}_{ts}.png"
    filepath = CHART_DIR / filename
    fig.savefig(str(filepath), dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(filepath)


def chart_bar(df: pd.DataFrame, col: str, slug: str, top_n: int = 15) -> str:
    """Generate bar chart for categorical value counts."""
    counts = df[col].dropna().value_counts().head(top_n)
    if counts.empty:
        return ""
    fig, ax = plt.subplots(figsize=(10, max(4, len(counts) * 0.35)))
    bars = ax.barh(range(len(counts)), counts.values, color=CHART_COLORS[0], alpha=0.85)
    ax.set_yticks(range(len(counts)))
    ax.set_yticklabels([str(v)[:25] for v in counts.index], fontsize=9)
    ax.set_xlabel("数量", fontsize=10)
    ax.set_title(f"{_normalize_column(col)} — TOP {len(counts)} 分布", fontsize=13, fontweight="bold")
    ax.invert_yaxis()
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_width() + max(counts.values) * 0.01, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return _save_fig(fig, f"bar_{col}", slug)


def chart_line(series_data: dict, title: str, slug: str,
               xlabel: str = "", ylabel: str = "") -> str:
    """Generate line chart (for time series or ordered data)."""
    x = list(series_data.keys())
    y = list(series_data.values())
    if len(x) < 2:
        return ""
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(range(len(x)), y, color=CHART_COLORS[0], linewidth=2, marker="o", markersize=4)
    ax.fill_between(range(len(x)), y, alpha=0.1, color=CHART_COLORS[0])
    # Show only readable number of x labels
    step = max(1, len(x) // 12)
    visible = list(range(0, len(x), step))
    ax.set_xticks(visible)
    ax.set_xticklabels([str(x[i]) for i in visible], rotation=45, ha="right", fontsize=8)
    ax.set_xlabel(xlabel or "顺序", fontsize=10)
    ax.set_ylabel(ylabel or "数值", fontsize=10)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return _save_fig(fig, "line", slug)


def chart_pie(df: pd.DataFrame, col: str, slug: str, max_slices: int = 8) -> str:
    """Generate pie chart for categorical composition."""
    counts = df[col].dropna().value_counts()
    if counts.empty:
        return ""
    # Group small slices
    if len(counts) > max_slices:
        top = counts.head(max_slices - 1)
        other = counts.iloc[max_slices - 1:].sum()
        top["其他"] = other
        counts = top
    colors = CHART_COLORS[:len(counts)]
    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=None, autopct="%1.1f%%",
        colors=colors, startangle=90, pctdistance=0.75,
        wedgeprops={"linewidth": 1, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(9)
    ax.legend(
        [f"{str(k)[:20]}: {v} ({v / max(counts.sum(), 1) * 100:.1f}%)"
         for k, v in zip(counts.index, counts.values)],
        loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8,
    )
    ax.set_title(f"{_normalize_column(col)} 构成", fontsize=13, fontweight="bold")
    plt.tight_layout()
    return _save_fig(fig, f"pie_{col}", slug)


def chart_scatter(df: pd.DataFrame, x_col: str, y_col: str, slug: str) -> str:
    """Generate scatter plot for two numeric columns."""
    data = df[[x_col, y_col]].dropna()
    if len(data) < 3:
        return ""
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(data[x_col], data[y_col], alpha=0.6, s=20, color=CHART_COLORS[0], edgecolors="white", linewidth=0.5)
    ax.set_xlabel(_normalize_column(x_col), fontsize=10)
    ax.set_ylabel(_normalize_column(y_col), fontsize=10)
    ax.set_title(f"{_normalize_column(x_col)} vs {_normalize_column(y_col)}", fontsize=13, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Add trend line
    try:
        z = np.polyfit(data[x_col].values.astype(float), data[y_col].values.astype(float), 1)
        p = np.poly1d(z)
        x_sorted = np.sort(data[x_col].values.astype(float))
        ax.plot(x_sorted, p(x_sorted), "--", color=CHART_COLORS[3], linewidth=1.5, alpha=0.7)
    except Exception:
        pass

    plt.tight_layout()
    return _save_fig(fig, f"scatter_{x_col}_vs_{y_col}", slug)


def chart_heatmap(corr_matrix: dict, slug: str) -> str:
    """Generate heatmap from correlation matrix."""
    if not corr_matrix.get("values"):
        return ""
    vals = np.array(corr_matrix["values"])
    if vals.shape[0] < 2:
        return ""
    labels = [str(c)[:15] for c in corr_matrix["columns"]]
    fig, ax = plt.subplots(figsize=(max(6, len(labels) * 0.7), max(5, len(labels) * 0.6)))
    sns.heatmap(vals, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                xticklabels=labels, yticklabels=labels,
                linewidths=0.5, ax=ax, cbar_kws={"shrink": 0.8})
    ax.set_title("相关性热力图", fontsize=13, fontweight="bold")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    plt.tight_layout()
    return _save_fig(fig, "heatmap", slug)


def generate_charts(df: pd.DataFrame, col_types: dict,
                    corr_matrix: dict, slug: str,
                    chart_types: list = None) -> dict:
    """
    Generate all requested charts. Returns {chart_type: filepath}.
    """
    if chart_types is None or "all" in chart_types:
        chart_types = ["bar", "line", "pie", "scatter", "heatmap"]

    chart_files = {}
    numeric = col_types.get("numeric", [])
    categorical = col_types.get("categorical", [])
    datetime_cols = col_types.get("datetime", [])

    # --- Bar: top categorical columns ---
    if "bar" in chart_types:
        for col in categorical[:2]:
            fp = chart_bar(df, col, slug)
            if fp:
                chart_files[f"bar_{col}"] = fp

    # --- Pie: first categorical ---
    if "pie" in chart_types:
        for col in categorical[:1]:
            fp = chart_pie(df, col, slug)
            if fp:
                chart_files[f"pie_{col}"] = fp

    # --- Scatter: top numeric pair ---
    if "scatter" in chart_types and len(numeric) >= 2:
        x_col, y_col = numeric[0], numeric[1]
        fp = chart_scatter(df, x_col, y_col, slug)
        if fp:
            chart_files[f"scatter_{x_col}_vs_{y_col}"] = fp

    # --- Line: time series or first numeric ---
    if "line" in chart_types:
        if datetime_cols and numeric:
            ts_data = df.set_index(datetime_cols[0])[numeric[0]].dropna().to_dict()
            fp = chart_line(ts_data, f"{_normalize_column(numeric[0])} 趋势",
                            slug, xlabel=str(datetime_cols[0]), ylabel=str(numeric[0]))
            if fp:
                chart_files["line_trend"] = fp
        elif len(numeric) >= 1:
            # Just plot first numeric in index order
            s = df[numeric[0]].dropna()
            fp = chart_line(
                dict(zip(s.index.astype(str), s.values)),
                f"{_normalize_column(numeric[0])} 分布", slug,
                ylabel=str(numeric[0]),
            )
            if fp:
                chart_files["line_distribution"] = fp

    # --- Heatmap ---
    if "heatmap" in chart_types and corr_matrix.get("values"):
        if len(corr_matrix["values"]) >= 2:
            fp = chart_heatmap(corr_matrix, slug)
            if fp:
                chart_files["heatmap"] = fp

    return chart_files


# ======================================================================
#  报告生成
# ======================================================================

def build_report_metadata(filename: str, df: pd.DataFrame) -> dict:
    """Build Obsidian-compatible frontmatter."""
    return {
        "title": f"数据分析报告: {_safe_filename(filename)}",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": filename,
        "rows": len(df),
        "cols": len(df.columns),
        "tool": "data_analysis_engine v1.0",
    }


def generate_report(filename: str, df: pd.DataFrame,
                    col_types: dict, num_stats: dict, cat_stats: dict,
                    corr_result: dict, trend_result: dict,
                    insights: list, chart_files: dict) -> str:
    """
    Generate a full Markdown analysis report with Obsidian frontmatter.
    """
    slug = _safe_filename(filename)
    meta = build_report_metadata(filename, df)

    # Frontmatter
    lines = ["---"]
    for k, v in meta.items():
        lines.append(f"{k}: {v}")
    lines.append("---\n")

    lines.append(f"# 数据分析报告: {_safe_filename(filename)}")
    lines.append(f"\n**日期**: {meta['date']}")
    lines.append(f"**数据概览**: {meta['rows']} 行 × {meta['cols']} 列\n")

    # ---- Section 1: 数据总览 ----
    lines.append("## 1. 数据总览\n")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 行数 | {len(df)} |")
    lines.append(f"| 列数 | {len(df.columns)} |")
    total_cells = len(df) * len(df.columns)
    missing_total = sum(int(df[col].isna().sum()) for col in df.columns)
    complete_pct = round((1 - missing_total / max(total_cells, 1)) * 100, 1)
    lines.append(f"| 完整率 | {complete_pct}% |")
    lines.append(f"| 数值列 | {len(col_types.get('numeric', []))} |")
    lines.append(f"| 分类列 | {len(col_types.get('categorical', []))} |")
    lines.append(f"| 时间列 | {len(col_types.get('datetime', []))} |")
    lines.append(f"| 文本列 | {len(col_types.get('text', []))} |")
    lines.append("")

    # Column list
    lines.append("### 列清单\n")
    lines.append("| 列名 | 类型 | 非空数 | 唯一值 |")
    lines.append("|------|------|--------|--------|")
    for col in df.columns:
        ctype = "数值" if col in col_types.get("numeric", []) else \
                "分类" if col in col_types.get("categorical", []) else \
                "时间" if col in col_types.get("datetime", []) else \
                "文本" if col in col_types.get("text", []) else "其他"
        non_null = df[col].notna().sum()
        unique = df[col].nunique() if col in col_types.get("categorical", []) else "-"
        lines.append(f"| {_normalize_column(col)} | {ctype} | {non_null} | {unique} |")
    lines.append("")

    # ---- Section 2: 变量分析 ----
    lines.append("## 2. 变量分析\n")

    for col, stats in num_stats.items():
        if "error" in stats:
            continue
        lines.append(f"### {_normalize_column(col)} (数值)\n")
        lines.append("| 统计量 | 数值 |")
        lines.append("|--------|------|")
        lines.append(f"| 计数 | {stats['count']} |")
        lines.append(f"| 缺失 | {stats['missing']} ({stats['missing_pct']}%) |")
        lines.append(f"| 均值 | {stats['mean']} |")
        lines.append(f"| 中位数 | {stats['median']} |")
        lines.append(f"| 标准差 | {stats['std']} |")
        lines.append(f"| 最小值 | {stats['min']} |")
        lines.append(f"| Q1 (25%) | {stats['q1']} |")
        lines.append(f"| Q3 (75%) | {stats['q3']} |")
        lines.append(f"| 最大值 | {stats['max']} |")
        lines.append(f"| 四分位距 | {stats['iqr']} |")
        lines.append(f"| 偏度 | {stats['skewness']} |")
        lines.append(f"| 峰度 | {stats['kurtosis']} |")
        lines.append(f"| 异常值数 | {stats['outlier_count']} ({stats['outlier_pct']}%) |")
        if stats["outlier_count"] > 0:
            lines.append(f"| 异常值范围 | {stats['outlier_min']} ~ {stats['outlier_max']} |")
        lines.append("")

    for col, stats in cat_stats.items():
        if "error" in stats:
            continue
        lines.append(f"### {_normalize_column(col)} (分类)\n")
        lines.append(f"- 唯一值数量: {stats['unique']}")
        lines.append(f"- 缺失: {stats['missing']}")
        lines.append(f"- 多样性 (熵): {stats['entropy']}")
        lines.append("")
        lines.append("| 值 | 数量 | 占比 |")
        lines.append("|------|------|------|")
        for tv in stats["top_values"][:15]:
            lines.append(f"| {tv['value']} | {tv['count']} | {tv['pct']}% |")
        lines.append("")

    # ---- Section 3: 相关性分析 ----
    lines.append("## 3. 相关性分析\n")
    pairs = corr_result.get("pairs", [])
    if pairs:
        lines.append("| 变量X | 变量Y | 相关系数 | 强度 | 方向 |")
        lines.append("|-------|-------|---------|------|------|")
        for p in pairs:
            lines.append(f"| {_normalize_column(p['x'])} | {_normalize_column(p['y'])} | "
                         f"{p['correlation']} | {p['strength']} | {p['direction']} |")
        lines.append("")

    if "heatmap" in chart_files:
        rel_path = os.path.relpath(chart_files["heatmap"], REPORT_DIR.parent.parent)
        lines.append(f"![相关性热力图](/{rel_path})\n")

    # ---- Section 4: 趋势与异常 ----
    lines.append("## 4. 趋势与异常\n")
    if trend_result and "direction" in trend_result:
        lines.append(f"**趋势**: {trend_result['strength']}{trend_result['direction']}")
        lines.append(f"- 斜率: {trend_result['slope']}")
        lines.append(f"- 时间跨度: {trend_result.get('start_date', 'N/A')} → {trend_result.get('end_date', 'N/A')}")
        if trend_result.get("seasonality"):
            lines.append(f"- {trend_result['seasonality']}")
        lines.append("")
    else:
        lines.append("未检测到时间序列数据或趋势。\n")

    # --- Anomaly summary ---
    anomaly_cols = []
    for col, stats in num_stats.items():
        if "error" not in stats and stats["outlier_count"] > 0:
            anomaly_cols.append((col, stats["outlier_count"], stats["outlier_pct"]))
    if anomaly_cols:
        lines.append("### 异常值检测\n")
        lines.append("| 列名 | 异常值数 | 占比 |")
        lines.append("|------|---------|------|")
        for col, cnt, pct in sorted(anomaly_cols, key=lambda x: -x[1]):
            lines.append(f"| {_normalize_column(col)} | {cnt} | {pct}% |")
        lines.append("")

    # ---- Section 5: 关键洞察 ----
    lines.append("## 5. 关键洞察\n")
    for i, ins in enumerate(insights, 1):
        lines.append(f"### 洞察 {i}: {ins['title']}\n")
        lines.append(f"{ins['content']}\n")

    # ---- Append chart references ----
    if chart_files:
        lines.append("## 6. 可视化图表\n")
        lines.append("| 图表 | 文件 |")
        lines.append("|------|------|")
        for name, fp in chart_files.items():
            rel = os.path.relpath(fp, REPORT_DIR.parent.parent)
            lines.append(f"| {name} | ![{name}](/{rel}) |")
        lines.append("")

    return "\n".join(lines)


def generate_json_output(filename: str, df: pd.DataFrame,
                         col_types: dict, num_stats: dict, cat_stats: dict,
                         corr_result: dict, trend_result: dict,
                         insights: list, chart_files: dict) -> dict:
    """Generate JSON-serializable output for dashboard consumption."""
    return {
        "meta": {
            "title": f"数据分析报告: {_safe_filename(filename)}",
            "generated_at": datetime.now().isoformat(),
            "source": filename,
            "rows": len(df),
            "columns": len(df.columns),
            "engine": "data_analysis_engine v1.0",
        },
        "column_types": {k: v for k, v in col_types.items() if v},
        "numeric_stats": num_stats,
        "categorical_stats": cat_stats,
        "correlation": {
            "pair_count": len(corr_result.get("pairs", [])),
            "top_pairs": corr_result.get("pairs", [])[:5],
        },
        "trend": trend_result,
        "insights": insights,
        "charts": list(chart_files.values()),
    }


def write_report(report_md: str, slug: str) -> str:
    """Write markdown report to disk, return filepath."""
    _ensure_dir(REPORT_DIR)
    ts = _timestamp()
    filepath = REPORT_DIR / f"数据分析报告_{slug}_{ts}.md"
    filepath.write_text(report_md, encoding="utf-8")
    print(f"[报告] 已保存: {filepath}")
    return str(filepath)


def write_json(data: dict, slug: str) -> str:
    """Write JSON output to disk, return filepath."""
    _ensure_dir(REPORT_DIR)
    ts = _timestamp()
    filepath = REPORT_DIR / f"数据分析报告_{slug}_{ts}.json"
    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[JSON] 已保存: {filepath}")
    return str(filepath)


# ======================================================================
#  主流程
# ======================================================================

def run_analysis(filepath: str, sheet: str = None,
                 chart_types: list = None,
                 output: str = "both",
                 focus: str = None,
                 lang: str = "zh") -> dict:
    """
    Run the full data analysis pipeline.

    Args:
        filepath: Path to data file.
        sheet: Excel sheet name (optional).
        chart_types: List of chart types, or ["all"].
        output: "report" | "json" | "both".
        focus: Comma-separated columns to focus on (optional).
        lang: Output language (default "zh").

    Returns:
        dict with keys: report_path, json_path, chart_files, insights, error.
    """
    result = {"report_path": None, "json_path": None,
              "chart_files": {}, "insights": [], "error": None}

    # --- Step 1: Load data ---
    try:
        df = load_data(filepath, sheet)
    except Exception as e:
        result["error"] = str(e)
        print(f"[错误] 数据加载失败: {e}")
        _log_to_learning_loop("data-analysis", "load", "fail",
                              root_cause=str(e))
        return result

    # Filter focus columns if specified
    if focus:
        focus_cols = [c.strip() for c in focus.split(",") if c.strip() in df.columns]
        if focus_cols:
            df = df[focus_cols]
            print(f"[聚焦] 限定列: {focus_cols}")

    slug = _safe_filename(filepath)

    # --- Step 2: Detect column types ---
    col_types = detect_column_types(df)
    print(f"[类型] 数值: {len(col_types['numeric'])} | "
          f"分类: {len(col_types['categorical'])} | "
          f"时间: {len(col_types['datetime'])} | "
          f"文本: {len(col_types['text'])}")

    # --- Step 3: Analyze columns ---
    num_stats = {}
    for col in col_types["numeric"]:
        num_stats[col] = analyze_numeric(df[col])
        s = num_stats[col]
        if "error" not in s:
            print(f"  {_normalize_column(col)}: 均值={s['mean']}, "
                  f"中位数={s['median']}, 异常值={s['outlier_count']}")

    cat_stats = {}
    for col in col_types["categorical"]:
        cat_stats[col] = analyze_categorical(df[col])
        s = cat_stats[col]
        if "error" not in s and s["top_values"]:
            print(f"  {_normalize_column(col)}: TOP1={s['top_value']} ({s['top_pct']}%), "
                  f"唯一值={s['unique']}")

    # --- Step 4: Correlation ---
    corr_result = analyze_correlation(df, col_types["numeric"])
    strong_pairs = [p for p in corr_result.get("pairs", []) if abs(p["correlation"]) >= 0.7]
    if strong_pairs:
        print(f"[相关] 发现 {len(strong_pairs)} 对强相关变量")
        for p in strong_pairs[:3]:
            print(u"  {} <-> {}: {} ({})".format(
                _normalize_column(p['x']), _normalize_column(p['y']),
                p['correlation'], p['direction']))

    # --- Step 5: Trend detection ---
    trend_result = {}
    if col_types["datetime"] and col_types["numeric"]:
        dt_col = col_types["datetime"][0]
        num_col = col_types["numeric"][0]
        trend_result = detect_trend(df, dt_col, num_col)
        if "direction" in trend_result:
            print(f"[趋势] {trend_result['direction']} (斜率={trend_result['slope']})")

    # --- Step 6: AI Insights ---
    insights = generate_insights(df, col_types, num_stats, cat_stats,
                                 corr_result, trend_result)
    print(f"[洞察] 生成 {len(insights)} 条关键洞察")
    for i, ins in enumerate(insights, 1):
        print(f"  {i}. {ins['title']}: {ins['content'][:80]}...")

    # --- Step 7: Charts ---
    chart_files = {}
    if chart_types:
        chart_files = generate_charts(df, col_types, corr_result, slug, chart_types)
        if chart_files:
            print(f"[图表] 生成 {len(chart_files)} 张图表")
            for name, fp in chart_files.items():
                print(f"  {name}: {fp}")

    # --- Step 8: Generate report ---
    report_md = generate_report(filepath, df, col_types, num_stats, cat_stats,
                                corr_result, trend_result, insights, chart_files)
    result["insights"] = insights
    result["chart_files"] = chart_files

    if output in ("report", "both"):
        result["report_path"] = write_report(report_md, slug)

    json_data = generate_json_output(filepath, df, col_types, num_stats, cat_stats,
                                     corr_result, trend_result, insights, chart_files)
    if output in ("json", "both"):
        result["json_path"] = write_json(json_data, slug)

    # Print summary
    print(f"\n{'='*50}")
    print(f"  分析完成: {_safe_filename(filepath)}")
    print(f"  行数: {len(df)} | 列数: {len(df.columns)}")
    print(f"  图表: {len(chart_files)} 张")
    print(f"  洞察: {len(insights)} 条")
    if result["report_path"]:
        print(f"  报告: {result['report_path']}")
    if result["json_path"]:
        print(f"  JSON: {result['json_path']}")
    print(f"{'='*50}")

    # Log to learning loop
    _log_to_learning_loop("data-analysis", "analysis", "success",
                          root_cause="",
                          fix=f"analyzed {len(df)} rows × {len(df.columns)} cols")

    return result


# ======================================================================
#  CLI 入口
# ======================================================================

def main():
    parser = argparse.ArgumentParser(
        description="数据分析引擎 v1.0 — 导入数据 → 自动分析 → 生成图表 → AI洞察 → 导出报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python data_analysis_engine.py --input data.csv
  python data_analysis_engine.py --input data.xlsx --sheet "Sheet1" --charts all
  python data_analysis_engine.py --input data.json --focus "revenue,users" --output both
  python data_analysis_engine.py --input sales.csv --charts bar,line,heatmap --output report
        """,
    )
    parser.add_argument("--input", "-i", required=True, help="输入数据文件路径 (CSV/XLSX/JSON)")
    parser.add_argument("--sheet", "-s", default=None, help="Excel工作表名称 (默认: 第一个工作表)")
    parser.add_argument("--charts", "-c", default="all",
                        help="图表类型: all/bar,line,pie,scatter,heatmap (默认: all)")
    parser.add_argument("--output", "-o", choices=["report", "json", "both"],
                        default="both", help="输出格式 (默认: both)")
    parser.add_argument("--focus", "-f", default=None,
                        help="聚焦列 (逗号分隔, 如 'revenue,users')")
    parser.add_argument("--lang", "-l", choices=["zh", "en"], default="zh",
                        help="输出语言 (默认: zh)")

    args = parser.parse_args()

    # Parse chart types
    chart_types = None
    if args.charts and args.charts != "all":
        chart_types = [c.strip() for c in args.charts.split(",")]

    result = run_analysis(
        filepath=args.input,
        sheet=args.sheet,
        chart_types=chart_types or ["all"],
        output=args.output,
        focus=args.focus,
        lang=args.lang,
    )

    if result["error"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
