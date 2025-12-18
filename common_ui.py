from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Dict, Any

import pandas as pd
import streamlit as st


# =========================================================
# Theme / CSS  (Logistics / Warehouse style)
# =========================================================
def inject_logistics_theme():
    """
    Logistics / Warehouse dashboard style:
    - Industrial blue + steel gray
    - Card layout
    - Reduce Streamlit top bar feeling
    """
    st.markdown(
        """
<style>
/* ---------- Base ---------- */
:root{
  --ink: rgba(15, 23, 42, 0.92);          /* slate-900 */
  --muted: rgba(15, 23, 42, 0.60);
  --line: rgba(15, 23, 42, 0.10);
  --card: rgba(255,255,255,0.88);
  --card2: rgba(255,255,255,0.70);
  --blue: rgba(2, 132, 199, 1.00);        /* sky-600 */
  --blueSoft: rgba(2, 132, 199, 0.12);
  --blueSoft2: rgba(2, 132, 199, 0.18);
  --ok: rgba(22, 163, 74, 1.0);
  --warn: rgba(245, 158, 11, 1.0);
  --bad: rgba(220, 38, 38, 1.0);
}

.stApp {
  color: var(--ink);
  background: radial-gradient(1200px 700px at 20% 0%, rgba(2,132,199,0.10) 0%, rgba(245,248,252,1) 55%, rgba(236,242,250,1) 100%);
}

/* remove top bar feeling */
header[data-testid="stHeader"] { background: transparent !important; }
div[data-testid="stToolbar"] { right: 0.8rem; }
div[data-testid="stDecoration"] { display: none; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"]{
  background: rgba(248,250,252,1);
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] *{
  color: var(--ink);
}

/* ---------- Container padding ---------- */
.block-container{
  padding-top: 1.2rem;
  padding-bottom: 2.0rem;
}

/* ---------- Buttons ---------- */
.stButton > button{
  border-radius: 14px;
  border: 1px solid rgba(2, 132, 199, 0.30);
  background: var(--blueSoft);
  color: var(--ink);
  padding: 0.55rem 0.9rem;
  font-weight: 700;
}
.stButton > button:hover{
  border: 1px solid rgba(2, 132, 199, 0.45);
  background: var(--blueSoft2);
}

/* ---------- File uploader ---------- */
div[data-testid="stFileUploaderDropzone"]{
  border-radius: 18px;
  border: 1px dashed rgba(15, 23, 42, 0.22);
  background: rgba(255,255,255,0.80);
}

/* ---------- Card blocks ---------- */
._gt_card{
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 20px;
  padding: 16px 16px 8px 16px;
  box-shadow: 0 10px 30px rgba(15,23,42,0.06);
  margin-bottom: 14px;
}
._gt_card h3{
  margin: 0 0 10px 0;
  letter-spacing: .2px;
}

/* ---------- KPI metric cards ---------- */
[data-testid="stMetric"]{
  background: rgba(255,255,255,0.90);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 14px 14px 10px 14px;
}
[data-testid="stMetricLabel"]{
  color: var(--muted) !important;
  font-weight: 700;
}
[data-testid="stMetricValue"]{
  font-weight: 900;
}

/* ---------- Tables ---------- */
div[data-testid="stDataFrame"]{
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--card2);
}

/* ---------- Small helper ---------- */
._gt_badge{
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,0.85);
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
}
._gt_hint{
  color: var(--muted);
  font-size: 13px;
  font-weight: 650;
  line-height: 1.55;
}
</style>
""",
        unsafe_allow_html=True,
    )


# Backward compatibility (你曾經用 inject_purple_theme)
def inject_purple_theme():
    inject_logistics_theme()


# =========================================================
# Page helpers
# =========================================================
def set_page(title: str, icon: str = "🏭", subtitle: Optional[str] = None):
    """
    Consistent page header/title block.
    Note: st.set_page_config should be in app.py or each page top-level.
    """
    inject_logistics_theme()
    st.markdown(f"## {icon} {title}")
    if subtitle:
        st.markdown(f'<div class="_gt_hint">{subtitle}</div>', unsafe_allow_html=True)


def badge(text: str):
    st.markdown(f'<span class="_gt_badge">{text}</span>', unsafe_allow_html=True)


def hint(text: str):
    st.markdown(f'<div class="_gt_hint">{text}</div>', unsafe_allow_html=True)


def card_open(title: str, right_badge: Optional[str] = None):
    if right_badge:
        st.markdown(
            f'<div class="_gt_card"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">'
            f'<h3 style="margin:0;">{title}</h3><span class="_gt_badge">{right_badge}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div class="_gt_card"><h3>{title}</h3>', unsafe_allow_html=True)


def card_close():
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# KPI / Metrics
# =========================================================
@dataclass
class KPI:
    label: str
    value: str
    delta: Optional[str] = None
    variant: str = "blue"  # reserved for future


def render_kpis(kpis: Sequence[KPI], cols: Optional[int] = None):
    if not kpis:
        return
    n = cols or min(5, len(kpis))
    columns = st.columns(n)
    for i, k in enumerate(kpis):
        with columns[i % n]:
            if k.delta is None:
                st.metric(label=k.label, value=k.value)
            else:
                st.metric(label=k.label, value=k.value, delta=k.delta)


# =========================================================
# Charts (no plotly dependency)
# =========================================================
def bar_topN(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    hover_cols: Optional[List[str]] = None,
    top_n: int = 30,
    target: Optional[float] = None,
    title: str = "",
):
    """
    Render a Top N bar chart using Altair (built-in friendly).
    """
    if df is None or df.empty:
        st.info("目前無可視覺化資料")
        return

    data = df.copy()
    keep_cols = [c for c in [x_col, y_col] + (hover_cols or []) if c in data.columns]
    data = data[keep_cols].copy()

    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    data = data.dropna(subset=[y_col])
    data = data.sort_values(y_col, ascending=False).head(int(top_n))

    try:
        import altair as alt  # type: ignore

        base = (
            alt.Chart(data)
            .mark_bar()
            .encode(
                x=alt.X(f"{y_col}:Q", title=y_col),
                y=alt.Y(f"{x_col}:N", sort="-x", title=""),
                tooltip=[c for c in [x_col, y_col] + (hover_cols or []) if c in data.columns],
            )
            .properties(height=min(560, 28 * max(6, len(data))))
        )

        layers = [base]
        if target is not None:
            rule = alt.Chart(pd.DataFrame({"target": [float(target)]})).mark_rule(strokeDash=[6, 4]).encode(
                x="target:Q"
            )
            layers.append(rule)

        if title:
            st.caption(title)
        st.altair_chart(alt.layer(*layers), use_container_width=True)

    except Exception:
        st.bar_chart(data.set_index(x_col)[y_col])


# =========================================================
# Table blocks
# =========================================================
def table_block(
    summary_title: str,
    summary_df: pd.DataFrame,
    detail_title: str = "",
    detail_df: Optional[pd.DataFrame] = None,
    detail_expanded: bool = False,
):
    card_open(summary_title)
    if summary_df is None or summary_df.empty:
        st.info("目前沒有可顯示的資料")
    else:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    card_close()

    if detail_title:
        with st.expander(detail_title, expanded=detail_expanded):
            if detail_df is None or detail_df.empty:
                st.info("目前沒有明細資料")
            else:
                st.dataframe(detail_df, use_container_width=True, hide_index=True)


# =========================================================
# Sidebar Controls (NO Operator)
# =========================================================
@dataclass
class ExcludeWindow:
    start: str  # "HH:MM"
    end: str    # "HH:MM"
    data_entry: str = ""  # 可留空


def _init_exclude_windows_state(key: str = "exclude_windows"):
    if key not in st.session_state:
        st.session_state[key] = []  # List[ExcludeWindow]


def sidebar_controls(
    *,
    default_top_n: int = 30,
    enable_exclude_windows: bool = True,
    state_key_prefix: str = "gt",
) -> Dict[str, Any]:
    """
    統一左側「計算條件設定」(物流版)：
    - ✅ 不包含「分析執行人（Operator）」：已完全取消
    - 包含 TopN 顯示筆數
    - 可新增/移除 非作業時段（排除區間）
    - 支援「資料登錄人」(可留空)：用於排除區間標註
    """
    inject_logistics_theme()

    result: Dict[str, Any] = {}

    st.sidebar.markdown("### ⚙️ 計算條件設定")
    hint("本區設定僅影響本次報表計算，不含個人績效追蹤。")

    # --- Top N
    top_n_key = f"{state_key_prefix}_top_n"
    top_n = st.sidebar.number_input(
        "效率排行顯示人數（Top N）",
        min_value=5,
        max_value=200,
        value=int(st.session_state.get(top_n_key, default_top_n)),
        step=1,
        key=top_n_key,
    )
    result["top_n"] = int(top_n)

    # --- Exclude windows
    if enable_exclude_windows:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⛔ 排除區間（非作業時段）")
        hint("用於排除支援、離站、停機、非驗收/非作業時間。")

        state_key = f"{state_key_prefix}_exclude_windows"
        _init_exclude_windows_state(state_key)

        # add window UI
        with st.sidebar.expander("新增排除區間", expanded=False):
            data_entry = st.text_input("資料登錄人（可留空）", value="", key=f"{state_key_prefix}_ex_data_entry")
            c1, c2 = st.columns(2)
            with c1:
                start_time = st.time_input("開始時間", value=pd.to_datetime("08:00").time(), key=f"{state_key_prefix}_ex_start")
            with c2:
                end_time = st.time_input("結束時間", value=pd.to_datetime("08:30").time(), key=f"{state_key_prefix}_ex_end")

            if st.button("＋ 新增排除區間", key=f"{state_key_prefix}_btn_add_ex"):
                s = f"{start_time:%H:%M}"
                e = f"{end_time:%H:%M}"
                st.session_state[state_key].append(ExcludeWindow(start=s, end=e, data_entry=data_entry or ""))
                st.success(f"已新增排除區間：{s} - {e}")

        # list + remove
        windows: List[ExcludeWindow] = st.session_state[state_key]
        if windows:
            st.sidebar.markdown("#### 已設定排除區間")
            for idx, w in enumerate(list(windows)):
                cols = st.sidebar.columns([0.72, 0.28])
                with cols[0]:
                    label = f"{w.start} - {w.end}"
                    if (w.data_entry or "").strip():
                        label += f" ｜登錄：{w.data_entry}"
                    st.write(label)
                with cols[1]:
                    if st.button("刪除", key=f"{state_key_prefix}_ex_del_{idx}"):
                        st.session_state[state_key].pop(idx)
                        st.experimental_rerun()
        else:
            st.sidebar.info("尚未新增排除區間")

        result["exclude_windows"] = [
            {"start": w.start, "end": w.end, "data_entry": w.data_entry} for w in st.session_state[state_key]
        ]
    else:
        result["exclude_windows"] = []

    return result


# =========================================================
# Downloads
# =========================================================
def download_excel(xlsx_bytes: bytes, filename: str = "KPI報表.xlsx"):
    st.download_button(
        label="📥 匯出KPI報表（Excel）",
        data=xlsx_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )


# =========================================================
# Excel helpers
# =========================================================
def dataframe_to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    """
    將多分頁 DataFrame 匯出成 Excel bytes（供 download_excel 使用）
    sheets: {"總表": df1, "明細": df2, ...}
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            if df is None:
                continue
            safe_name = str(name)[:31] or "Sheet1"
            df.to_excel(writer, sheet_name=safe_name, index=False)
    return output.getvalue()
