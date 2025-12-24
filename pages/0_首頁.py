# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

# ✅ 直接對到你現有的 pages（不用新增課別首頁也能先跑）
ROUTES = {
    "出貨課": "pages/6_撥貨差異.py",
    "進貨課": "pages/1_驗收作業效能.py",
}

def _route_by_query():
    """同一視窗切頁：?page=pages/xxx.py -> st.switch_page(xxx)"""
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
/* ===== Page background / remove blue focus ===== */
:root{
  --bg: #F5F8FC;
  --card: #FFFFFF;
  --text: #0F172A;
  --muted: #64748B;
  --border: rgba(15, 23, 42, 0.10);
  --shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  --shadow2: 0 6px 14px rgba(15, 23, 42, 0.05);
  --radius: 18px;
}

section[data-testid="stAppViewContainer"]{ background: var(--bg) !important; }
.block-container{ padding-top: 18px !important; }

*:focus{ outline:none !important; box-shadow:none !important; }
button:focus{ outline:none !important; box-shadow:none !important; }

/* ===== Header area (match your screenshot vibe) ===== */
.gt-header{
  background: linear-gradient(180deg, rgba(59,130,246,0.10), rgba(255,255,255,0));
  border: 1px solid var(--border);
  border-radius: 22px;
  padding: 18px 20px;
  box-shadow: var(--shadow2);
}
.gt-title{
  display:flex; align-items:center; gap:10px;
  font-size: 26px; font-weight: 900; color: var(--text);
  margin: 0;
}
.gt-sub{
  margin-top: 6px;
  color: var(--muted);
  font-size: 13.5px;
}

/* ===== Section card ===== */
.gt-section{
  margin-top: 14px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 14px 16px;
}
.gt-section-title{
  display:flex; align-items:center; gap:10px;
  font-size: 16px; font-weight: 900; color: var(--text);
  margin: 0 0 8px 0;
}

/* ===== Department rows (clickable) ===== */
.dept-row{
  display:flex;
  align-items:center;
  justify-content: space-between;
  gap: 14px;
  padding: 12px 12px;
  border-radius: 16px;
  border: 1px solid rgba(15,23,42,0.08);
  background: #fff;
  text-decoration: none !important;
  color: var(--text) !important;
  margin-top: 10px;
}
.dept-row:hover{
  background: rgba(59,130,246,0.05);
  transform: translateY(-1px);
  box-shadow: var(--shadow2);
}
.dept-left{ display:flex; gap: 12px; align-items:flex-start; }

.dept-icon{
  width: 36px; height: 36px;
  border-radius: 12px;
  display:flex; align-items:center; justify-content:center;
  border: 1px solid rgba(15,23,42,0.08);
  background: rgba(59,130,246,0.06);
  font-size: 18px;
}

.dept-name{ font-size: 15px; font-weight: 900; margin: 0; }
.dept-desc{
  margin-top: 4px;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.55;
}

.dept-arrow{
  font-weight: 900;
  color: rgba(15,23,42,0.55);
  white-space: nowrap;
}

/* ===== Make markdown top margins smaller ===== */
h1,h2,h3{ margin-bottom: 0.2rem !important; }
</style>
""",
        unsafe_allow_html=True,
    )

# -----------------------------
# Main
# -----------------------------
_route_by_query()
_css()

# Header (你截圖上面那一條的感覺)
st.markdown(
    """
<div class="gt-header">
  <div class="gt-title">🚚 大豐物流・作業平台</div>
  <div class="gt-sub">作業KPI｜班別分析（AM/PM）｜排除非作業區間</div>
</div>
""",
    unsafe_allow_html=True,
)

# Section: 課別入口
st.markdown(
    """
<div class="gt-section">
  <div class="gt-section-title">📌 課別入口</div>

  <a class="dept-row" href="{out}">
    <div class="dept-left">
      <div class="dept-icon">📦</div>
      <div>
        <div class="dept-name">出貨課：Outbound</div>
        <div class="dept-desc">撥貨差異・出貨/包裝/異常（由課別首頁統一入口）</div>
      </div>
    </div>
    <div class="dept-arrow">進入 →</div>
  </a>

  <a class="dept-row" href="{inb}">
    <div class="dept-left">
      <div class="dept-icon">🚚</div>
      <div>
        <div class="dept-name">進貨課：Inbound</div>
        <div class="dept-desc">驗收/上架/總揀/儲位/差異代庫存（由課別首頁統一入口）</div>
      </div>
    </div>
    <div class="dept-arrow">進入 →</div>
  </a>

</div>
""".format(out=_link(ROUTES["出貨課"]), inb=_link(ROUTES["進貨課"])),
    unsafe_allow_html=True,
)
