from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
except Exception:
    px = None


# ========= UI Data =========
@dataclass
class KPI:
    label: str
    value: str
    help: str = ""
    variant: str = "purple"  # purple/blue/cyan/teal/gray


# ========= Theme =========
def inject_purple_theme():
    """
    Purple + Blue Tech SaaS theme.
    NOTE: do NOT call st.set_page_config here (app.py owns config in navigation mode).
    """
    st.markdown(
        """
<style>
/* ===== Purple-Blue Tech Dashboard Theme ===== */
:root{
  --bg: #0B1020;
  --bg2:#0F1631;
  --card:#FFFFFF;
  --text:#0F172A;
  --muted:#64748B;
  --stroke: rgba(15,23,42,0.08);
  --shadow: 0 14px 40px rgba(2, 6, 23, .10);
  --shadow2: 0 10px 24px rgba(2, 6, 23, .08);
}

/* App background */
.stApp{
  background: radial-gradient(1200px 700px at 20% -10%, rgba(142,45,226,.18), transparent 55%),
              radial-gradient(1100px 700px at 80% 0%, rgba(54,209,220,.16), transparent 50%),
              #F5F7FB;
}

/* Content width like SaaS */
.block-container{
  padding-top: 1.2rem;
  padding-bottom: 2.4rem;
  max-width: 1240px;
}

/* Sidebar: glassy white */
section[data-testid="stSidebar"]{
  background: rgba(255,255,255,.82);
  backdrop-filter: blur(12px);
  border-right: 1px solid rgba(15,23,42,0.06);
}
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] label{
  color: #0F172A;
}

/* Headings */
h1,h2,h3{
  letter-spacing: .2px;
}

/* Card container */
.gt-card{
  background: rgba(255,255,255,.92);
  border: 1px solid rgba(15,23,42,0.06);
  border-radius: 18px;
  padding: 18px 18px;
  box-shadow: var(--shadow2);
}

/* Section title inside card */
.gt-card .gt-card-title{
  font-weight: 900;
  font-size: 1.02rem;
  margin: 0 0 12px 0;
  color: #0F172A;
}

/* KPI gradient cards */
.gt-kpi{
  border-radius: 18px;
  padding: 18px 18px;
  color: #fff;
  border: 1px solid rgba(255,255,255,0.18);
  box-shadow: var(--shadow);
  position: relative;
  overflow: hidden;
}
.gt-kpi:after{
  content:"";
  position:absolute;
  inset:-40px -60px auto auto;
  width:160px;height:160px;
  background: rgba(255,255,255,.16);
  transform: rotate(25deg);
  border-radius: 999px;
}
.gt-kpi .k{ font-size: .90rem; opacity:.92; margin:0 0 8px 0; }
.gt-kpi .v{ font-size: 1.65rem; font-weight: 950; margin:0; line-height: 1.08; }
.gt-kpi .h{ font-size: .82rem; opacity:.88; margin-top: 10px; }

.gt-purple{ background: linear-gradient(135deg,#7C3AED,#4F46E5); } /* purple -> indigo */
.gt-blue  { background: linear-gradient(135deg,#2563EB,#06B6D4); } /* blue -> cyan */
.gt-cyan  { background: linear-gradient(135deg,#06B6D4,#22C55E); } /* cyan -> green */
.gt-teal  { background: linear-gradient(135deg,#14B8A6,#3B82F6); } /* teal -> blue */
.gt-gray  { background: linear-gradient(135deg,#64748B,#334155); } /* slate */

/* Buttons: pill, tech */
.stButton>button, .stDownloadButton>button{
  border-radius: 14px !important;
  padding: .62rem 1.05rem !important;
  font-weight: 900 !important;
  border: 1px solid rgba(15,23,42,0.10) !important;
  box-shadow: 0 10px 22px rgba(2, 6, 23, .08) !important;
}
.stButton>button:hover, .stDownloadButton>button:hover{
  transform: translateY(-1px);
}

/* File uploader better */
[data-testid="stFileUploader"]{
  background: rgba(255,255,255,.75);
  border: 1px dashed rgba(79,70,229,.30);
  border-radius: 16px;
  padding: 10px 12px;
}

/* DataFrame: card-like */
[data-testid="stDataFrame"]{
  background: rgba(255,255,255,.92);
  border-radius: 16px;
  border: 1px solid rgba(15,23,42,0.06);
  overflow: hidden;
}

/* Plotly card wrapper */
[data-testid="stPlotlyChart"] > div{
  background: rgba(255,255,255,.92);
  border-radius: 16px;
  border: 1px solid rgba(15,23,42,0.06);
  box-shadow: var(--shadow2);
  padding: 10px;
}
</style>
""",
        unsafe_allow_html=True,
    )


# ========= Page Helpers =========
def set_page(title: str, icon: str = "📊"):
    """In navigation mode, DO NOT call st.set_page_config in pages. Only inject theme + title."""
    inject_purple_theme()
    st.markdown(f"# {icon} {title}")


def card_open(title: Optional[str] = None):
    st.markdown('<div class="gt-card">', unsafe_allow_html=True)
    if title:
        st.markdown(f'<div class="gt-card-title">{title}</div>', unsafe_allow_html=True)


def card_close():
    st.markdown("</div>", unsafe_allow_html=True)


def kpi_card(label: str, value: str, help_text: str = "", variant: str = "purple"):
    v = (variant or "purple").strip().lower()
    if v not in {"purple", "blue", "cyan", "teal", "gray"}:
        v = "purple"

    h = f'<div class="h">{help_text}</div>' if help_text else ""
    st.markdown(
        f"""
<div class="gt-kpi gt-{v}">
  <div class="k">{label}</div>
  <div class="v">{value}</div>
  {h}
</div>
""",
        unsafe_allow_html=True,
    )


def render_kpis(kpis: List[KPI]):
    if not kpis:
        return
    cols = st.columns(len(kpis))
    for c, k in zip(cols, kpis):
        with c:
            kpi_card(k.label, k.value, k.help, k.variant)


# ========= Charts / Tables =========
def _safe_float(x):
    try:
        if x is None or (isinstance(x, float) and pd.isna(x)):
            return None
        return float(x)
    except Exception:
        return None


def bar_topN(
    df: pd.DataFrame,
    *,
    x_col: str,
    y_col: str,
    hover_cols: List[str],
    top_n: int = 30,
    target: float = 20.0,
    title: str = "排行（Top N）",
):
    if df is None or df.empty or y_col not in df.columns:
        st.info("沒有可顯示的資料。")
        return

    view = df.copy()
    view = view.sort_values(y_col, ascending=False).head(int(top_n))

    if px is None:
        st.warning("plotly 未安裝：改用表格呈現（如需圖表請在 requirements.txt 加上 plotly）。")
        st.dataframe(view[[x_col, y_col] + [c for c in hover_cols if c in view.columns]], use_container_width=True)
        return

    def status(v):
        fv = _safe_float(v)
        if fv is None:
            return "—"
        return "達標" if fv >= float(target) else "未達標"

    view["_達標"] = view[y_col].apply(status)

    fig = px.bar(
        view,
        x=x_col,
        y=y_col,
        color="_達標",
        hover_data=[c for c in hover_cols if c in view.columns],
    )
    fig.update_layout(
        title=None,
        margin=dict(l=10, r=10, t=10, b=10),
        legend_title_text="",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)


def pivot_am_pm(
    ampm_df: pd.DataFrame,
    *,
    index_col: str = "姓名",
    segment_col: str = "時段",
    value_col: str = "效率",
    title: str = "上午 vs 下午（平均）",
):
    if ampm_df is None or ampm_df.empty:
        st.info("沒有 AM/PM 資料。")
        return

    need = {index_col, segment_col, value_col}
    if not need.issubset(set(ampm_df.columns)):
        st.info("AM/PM 欄位不足，無法製作對照。")
        return

    pivot = ampm_df.pivot_table(index=index_col, columns=segment_col, values=value_col, aggfunc="mean").reset_index()
    st.dataframe(pivot, use_container_width=True)


def table_block(
    *,
    summary_title: str,
    summary_df: pd.DataFrame,
    detail_title: str,
    detail_df: pd.DataFrame,
    detail_expanded: bool = False,
):
    card_open(summary_title)
    st.dataframe(summary_df, use_container_width=True)
    card_close()

    with st.expander(detail_title, expanded=detail_expanded):
        card_open()
        st.dataframe(detail_df, use_container_width=True)
        card_close()


def download_excel(xlsx_bytes: bytes, filename: str):
    st.download_button(
        "⬇️ 下載 Excel 結果",
        data=xlsx_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
