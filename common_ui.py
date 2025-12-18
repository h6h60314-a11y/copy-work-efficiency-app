from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional, Sequence, Dict, Any

import pandas as pd
import streamlit as st


# =========================================================
# Theme / CSS（物流專業風格）
# =========================================================
def inject_logistics_theme():
    st.markdown(
        """
<style>
:root{
  --ink: rgba(15, 23, 42, 0.92);
  --muted: rgba(15, 23, 42, 0.60);
  --line: rgba(15, 23, 42, 0.10);
  --card: rgba(255,255,255,0.88);
  --card2: rgba(255,255,255,0.70);
  --blue: rgba(2, 132, 199, 1.00);
  --blueSoft: rgba(2, 132, 199, 0.12);
  --blueSoft2: rgba(2, 132, 199, 0.18);
}

.stApp {
  color: var(--ink);
  background: radial-gradient(1200px 700px at 20% 0%, rgba(2,132,199,0.10) 0%, #f5f8fc 55%, #ecf2fa 100%);
}

header[data-testid="stHeader"] { background: transparent !important; }
div[data-testid="stDecoration"] { display: none; }

section[data-testid="stSidebar"]{
  background: #f8fafc;
  border-right: 1px solid var(--line);
}

.block-container{
  padding-top: 1.2rem;
  padding-bottom: 2.0rem;
}

._gt_card{
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 20px;
  padding: 16px;
  margin-bottom: 14px;
  box-shadow: 0 10px 30px rgba(15,23,42,0.06);
}

._gt_hint{
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

._gt_badge{
  display:inline-block;
  padding:2px 10px;
  border-radius:999px;
  border:1px solid var(--line);
  font-size:12px;
  font-weight:700;
  background:#fff;
}
</style>
""",
        unsafe_allow_html=True,
    )


def inject_purple_theme():
    inject_logistics_theme()


# =========================================================
# Page helpers
# =========================================================
def set_page(title: str, icon: str = "🏭", subtitle: Optional[str] = None):
    inject_logistics_theme()
    st.markdown(f"## {icon} {title}")
    if subtitle:
        st.markdown(f'<div class="_gt_hint">{subtitle}</div>', unsafe_allow_html=True)


def card_open(title: str, right_badge: Optional[str] = None):
    if right_badge:
        st.markdown(
            f'<div class="_gt_card"><div style="display:flex;justify-content:space-between;align-items:center">'
            f'<h3 style="margin:0">{title}</h3><span class="_gt_badge">{right_badge}</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(f'<div class="_gt_card"><h3>{title}</h3>', unsafe_allow_html=True)


def card_close():
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# KPI
# =========================================================
@dataclass
class KPI:
    label: str
    value: str
    delta: Optional[str] = None


def render_kpis(kpis: Sequence[KPI], cols: Optional[int] = None):
    if not kpis:
        return
    n = cols or min(5, len(kpis))
    columns = st.columns(n)
    for i, k in enumerate(kpis):
        with columns[i % n]:
            if k.delta:
                st.metric(k.label, k.value, k.delta)
            else:
                st.metric(k.label, k.value)


# =========================================================
# Charts
# =========================================================
def bar_topN(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    hover_cols: Optional[List[str]] = None,
    top_n: int = 30,
    target: Optional[float] = None,
):
    if df is None or df.empty:
        st.info("目前無資料")
        return

    data = df.copy()
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    data = data.dropna(subset=[y_col]).sort_values(y_col, ascending=False).head(int(top_n))

    try:
        import altair as alt

        base = alt.Chart(data).mark_bar().encode(
            x=alt.X(f"{y_col}:Q", title=y_col),
            y=alt.Y(f"{x_col}:N", sort="-x", title=""),
            tooltip=[c for c in [x_col, y_col] + (hover_cols or []) if c in data.columns],
        )

        layers = [base]
        if target is not None:
            layers.append(
                alt.Chart(pd.DataFrame({"target": [target]}))
                .mark_rule(strokeDash=[6, 4])
                .encode(x="target:Q")
            )

        st.altair_chart(alt.layer(*layers), use_container_width=True)
    except Exception:
        st.bar_chart(data.set_index(x_col)[y_col])


# =========================================================
# Sidebar Controls（❗手動輸入時間）
# =========================================================
@dataclass
class ExcludeWindow:
    start: str   # HH:MM
    end: str     # HH:MM
    data_entry: str = ""


def _init_exclude_state(key: str):
    if key not in st.session_state:
        st.session_state[key] = []


def sidebar_controls(
    *,
    default_top_n: int = 30,
    enable_exclude_windows: bool = True,
    state_key_prefix: str = "gt",
) -> Dict[str, Any]:
    inject_logistics_theme()
    result: Dict[str, Any] = {}

    st.sidebar.markdown("### ⚙️ 計算條件設定")
    st.sidebar.markdown('<div class="_gt_hint">本區設定僅影響本次分析</div>', unsafe_allow_html=True)

    # Top N
    top_n = st.sidebar.number_input(
        "效率排行顯示人數（Top N）",
        min_value=5,
        max_value=200,
        value=default_top_n,
        step=1,
    )
    result["top_n"] = int(top_n)

    # 排除區間（手動輸入）
    if enable_exclude_windows:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ⛔ 排除區間（非作業時段）")
        st.sidebar.markdown(
            '<div class="_gt_hint">請手動輸入時間（HH:MM），例如 12:30</div>',
            unsafe_allow_html=True,
        )

        state_key = f"{state_key_prefix}_exclude_windows"
        _init_exclude_state(state_key)

        with st.sidebar.expander("新增排除區間", expanded=False):
            data_entry = st.text_input("資料登錄人（可留空）", value="")

            c1, c2 = st.columns(2)
            with c1:
                start_str = st.text_input("開始時間（HH:MM）", value="08:00", placeholder="08:00")
            with c2:
                end_str = st.text_input("結束時間（HH:MM）", value="08:30", placeholder="12:30")

            if st.button("＋ 新增排除區間"):
                try:
                    s = pd.to_datetime(start_str, format="%H:%M").time()
                    e = pd.to_datetime(end_str, format="%H:%M").time()
                    if s >= e:
                        st.error("❌ 開始時間需早於結束時間")
                    else:
                        st.session_state[state_key].append(
                            ExcludeWindow(
                                start=start_str,
                                end=end_str,
                                data_entry=data_entry.strip(),
                            )
                        )
                        st.success(f"已新增：{start_str} - {end_str}")
                except Exception:
                    st.error("❌ 時間格式錯誤，請使用 HH:MM")

        # 顯示與刪除
        if st.session_state[state_key]:
            st.sidebar.markdown("#### 已設定排除區間")
            for i, w in enumerate(list(st.session_state[state_key])):
                cols = st.sidebar.columns([0.7, 0.3])
                with cols[0]:
                    txt = f"{w.start} - {w.end}"
                    if w.data_entry:
                        txt += f"｜登錄：{w.data_entry}"
                    st.write(txt)
                with cols[1]:
                    if st.button("刪除", key=f"{state_key}_del_{i}"):
                        st.session_state[state_key].pop(i)
                        st.experimental_rerun()

        result["exclude_windows"] = [
            {"start": w.start, "end": w.end, "data_entry": w.data_entry}
            for w in st.session_state[state_key]
        ]
    else:
        result["exclude_windows"] = []

    return result


# =========================================================
# Download
# =========================================================
def download_excel(xlsx_bytes: bytes, filename: str = "KPI報表.xlsx"):
    st.download_button(
        "📥 匯出 KPI 報表（Excel）",
        data=xlsx_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def dataframe_to_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        for name, df in sheets.items():
            if df is not None:
                df.to_excel(writer, sheet_name=str(name)[:31], index=False)
    return output.getvalue()
