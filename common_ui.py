from __future__ import annotations

import io
from dataclasses import dataclass
from typing import List, Optional, Sequence

import pandas as pd
import streamlit as st


# =========================================================
# Theme / CSS
# =========================================================
def inject_logistics_theme():
    """
    Logistics / Warehouse dashboard style:
    - Industrial blue + steel gray
    - Card layout
    - Reduce "top white bar" feeling
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
  font-weight: 600;
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
  padding: 16px 16px 6px 16px;
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
  font-weight: 600;
}
[data-testid="stMetricValue"]{
  font-weight: 800;
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
  font-weight: 700;
}
</style>
""",
        unsafe_allow_html=True,
    )


# Backward compatibility (you曾經用 inject_purple_theme)
def inject_purple_theme():
    inject_logistics_theme()


# =========================================================
# Page helpers
# =========================================================
def set_page(title: str, icon: str = "🏭"):
    """
    Consistent page header/title block.
    Note: st.set_page_config should be in app.py or each page's top-level.
    """
    inject_logistics_theme()
    st.markdown(f"## {icon} {title}")


def card_open(title: str):
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
        st.info("無資料可視覺化")
        return

    data = df.copy()
    data = data[[c for c in [x_col, y_col] + (hover_cols or []) if c in data.columns]].copy()
    data[y_col] = pd.to_numeric(data[y_col], errors="coerce")
    data = data.dropna(subset=[y_col])

    data = data.sort_values(y_col, ascending=False).head(int(top_n))

    # Try to use Altair if available; fallback to st.bar_chart
    try:
        import altair as alt  # type: ignore

        base = alt.Chart(data).mark_bar().encode(
            x=alt.X(f"{y_col}:Q", title=y_col),
            y=alt.Y(f"{x_col}:N", sort="-x", title=""),
            tooltip=[c for c in [x_col, y_col] + (hover_cols or []) if c in data.columns],
        ).properties(height=min(560, 28 * max(6, len(data))))

        layers = [base]

        if target is not None:
            rule = alt.Chart(pd.DataFrame({"target": [float(target)]})).mark_rule(strokeDash=[6, 4]).encode(
                x="target:Q"
            )
            layers.append(rule)

        chart = alt.layer(*layers)
        if title:
            st.caption(title)

        st.altair_chart(chart, use_container_width=True)

    except Exception:
        # fallback
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
