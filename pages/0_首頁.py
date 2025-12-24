# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

ROUTES = {
    "出貨課首頁": "pages/7_出貨課首頁.py",
    "進貨課首頁": "pages/8_進貨課首頁.py",
}

def _route_by_query():
    qp = st.query_params
    raw = qp.get("page", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    if not raw:
        return
    st.query_params.clear()
    st.switch_page(unquote(raw))

def _link(page_path: str) -> str:
    return f"?page={quote(page_path)}"

def _css():
    st.markdown(
        r"""
<style>
:root{
  --bg: #F5F8FC;
  --card:#fff;
  --text:#0F172A;
  --muted:#64748B;
  --border: rgba(15,23,42,0.10);
  --shadow: 0 10px 24px rgba(15,23,42,0.06);
  --shadow2: 0 6px 14px rgba(15,23,42,0.05);
  --radius: 18px;
}
section[data-testid="stAppViewContainer"]{ background: var(--bg) !important; }
.block-container{ padding-top: 18px !important; }
*:focus{ outline:none !important; box-shadow:none !important; }

.gt-header{
  background: linear-gradient(180deg, rgba(59,130,246,0.10), rgba(255,255,255,0));
  border: 1px solid var(--border);
  border-radius: 22px;
  padding: 18px 20px;
  box-shadow: var(--shadow2);
}
.gt-title{ display:flex; align-items:center; gap:10px; font-size:26px; font-weight:900; color:var(--text); margin:0; }
.gt-sub{ margin-top:6px; color:var(--muted); font-size:13.5px; }

.gt-section{
  margin-top: 14px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px 16px;
}
.gt-section-title{ display:flex; align-items:center; gap:10px; font-size:16px; font-weight:900; color:var(--text); margin:0; }

.dept-tiles{ margin-top: 10px; display:flex; gap: 18px; flex-wrap: wrap; }
.dept-tile{
  width: 320px;
  border: 1px solid rgba(15,23,42,0.10);
  border-radius: 18px;
  background: #fff;
  box-shadow: var(--shadow2);
  padding: 14px 14px;
  text-decoration: none !important;
  color: var(--text) !important;
}
.dept-tile:hover{ transform: translateY(-1px); box-shadow: var(--shadow); background: rgba(59,130,246,0.03); }
.tile-head{ display:flex; align-items:center; gap: 10px; }
.tile-icon{
  width: 38px; height: 38px; border-radius: 14px;
  display:flex; align-items:center; justify-content:center;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(59,130,246,0.08);
}
.tile-name{ font-weight: 950; font-size: 16px; margin:0; }
.tile-desc{ color: var(--muted); font-size: 13px; margin-top: 8px; line-height: 1.55; }
.tile-foot{ margin-top: 10px; display:flex; justify-content:flex-end; color: rgba(15,23,42,0.55); font-weight: 900; }
</style>
""",
        unsafe_allow_html=True,
    )

_route_by_query()
_css()

st.markdown(
    """
<div class="gt-header">
  <div class="gt-title">🚚 大豐物流・作業平台</div>
  <div class="gt-sub">作業KPI｜班別分析（AM/PM）｜排除非作業區間</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="gt-section">
  <div class="gt-section-title">📌 課別入口</div>

  <div class="dept-tiles">
    <a class="dept-tile" href="{out}">
      <div class="tile-head">
        <div class="tile-icon">📦</div>
        <div class="tile-name">出貨課</div>
      </div>
      <div class="tile-desc">撥貨差異・出貨/包裝/異常（進入後以條列式顯示模組）</div>
      <div class="tile-foot">進入 →</div>
    </a>

    <a class="dept-tile" href="{inb}">
      <div class="tile-head">
        <div class="tile-icon">🚚</div>
        <div class="tile-name">進貨課</div>
      </div>
      <div class="tile-desc">驗收/上架/總揀/儲位/差異代庫存（進入後以條列式顯示模組）</div>
      <div class="tile-foot">進入 →</div>
    </a>
  </div>
</div>
""".format(out=_link(ROUTES["出貨課首頁"]), inb=_link(ROUTES["進貨課首頁"])),
    unsafe_allow_html=True,
)
