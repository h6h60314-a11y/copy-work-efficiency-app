# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 作業平台", page_icon="🚚", layout="wide")
inject_logistics_theme()


def _route_by_query():
    """同一視窗切頁：?page=pages/xxx.py -> st.switch_page()"""
    qp = st.query_params
    raw = qp.get("page", "")

    if isinstance(raw, list):
        raw = raw[0] if raw else ""

    if not raw:
        return

    st.query_params.clear()
    st.switch_page(unquote(raw))


def _css_and_js():
    st.markdown(
        r"""
<style>
/* =========================
   ✅ 全站連結不要變藍底
   ========================= */
section[data-testid="stAppViewContainer"] a,
section[data-testid="stAppViewContainer"] a:visited{
  color: rgba(15, 23, 42, 0.92) !important;
  text-decoration: none !important;
}
section[data-testid="stAppViewContainer"] a,
section[data-testid="stAppViewContainer"] button{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  outline: none !important;
}
section[data-testid="stAppViewContainer"] a:focus,
section[data-testid="stAppViewContainer"] a:focus-visible,
section[data-testid="stAppViewContainer"] button:focus,
section[data-testid="stAppViewContainer"] button:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}

/* card wrapper */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background: rgba(255,255,255,0.98) !important;
  border-color: rgba(15, 23, 42, 0.10) !important;
  box-shadow: none !important;
}

/* =========================
   ✅ 上方「分頁列」(像你圖那種)
   ========================= */
.hub-topbar{
  display:flex;
  align-items:center;
  gap:10px;
  margin-top: 2px;
  margin-bottom: 14px;
}
.hub-pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.85);
  font-size: 13px;
  font-weight: 900;
  color: rgba(15,23,42,0.78);
  cursor:pointer;
  transition: transform .06s ease, box-shadow .12s ease, border-color .12s ease;
}
.hub-pill:hover{
  transform: translateY(-1px);
  border-color: rgba(15,23,42,0.18);
  box-shadow: 0 10px 18px rgba(2,6,23,0.06);
}
.hub-pill .dot{
  width:8px;height:8px;border-radius:999px;
  background: rgba(59,130,246,0.70);
}

/* =========================
   ✅ 入口卡片（像你圖那種卡片方塊）
   ========================= */
.hub-grid{
  display:grid;
  grid-template-columns: repeat(4, minmax(220px, 1fr));
  gap: 14px;
  align-items: stretch;
}
@media (max-width: 1200px){
  .hub-grid{ grid-template-columns: repeat(2, minmax(220px, 1fr)); }
}
@media (max-width: 680px){
  .hub-grid{ grid-template-columns: repeat(1, minmax(220px, 1fr)); }
}

.hub-card{
  position: relative;
  border-radius: 16px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.92);
  min-height: 118px;
  padding: 14px 14px 12px;
  overflow: hidden;
  box-shadow: 0 14px 28px rgba(2,6,23,0.06);
  transition: transform .08s ease, box-shadow .12s ease, border-color .12s ease;
}
.hub-card:hover{
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(2,6,23,0.10);
  border-color: rgba(15,23,42,0.18);
}

/* 卡片左側文字 */
.hub-title{
  font-size: 18px;
  font-weight: 950;
  line-height: 1.15;
  color: rgba(15,23,42,0.92);
  margin: 0 0 6px 0;
}
.hub-sub{
  font-size: 13px;
  font-weight: 850;
  color: rgba(15,23,42,0.60);
  margin: 0;
}

/* 右側裝飾插圖（用 CSS 畫出「盒子/倉儲」感） */
.hub-illu{
  position:absolute;
  right:-10px;
  top:-14px;
  width: 160px;
  height: 160px;
  border-radius: 28px;
  opacity: 0.95;
  transform: rotate(8deg);
  pointer-events:none;
  filter: saturate(1.05);
}
/* 不同卡片配色 */
.illu-outbound{
  background:
    radial-gradient(circle at 30% 30%, rgba(255,255,255,0.92) 0 36%, rgba(255,255,255,0) 37%),
    linear-gradient(135deg, rgba(59,130,246,0.22), rgba(37,99,235,0.10));
}
.illu-inbound{
  background:
    radial-gradient(circle at 30% 30%, rgba(255,255,255,0.92) 0 36%, rgba(255,255,255,0) 37%),
    linear-gradient(135deg, rgba(34,197,94,0.18), rgba(16,185,129,0.10));
}
/* 疊幾個「箱子」方塊 */
.hub-illu:before, .hub-illu:after{
  content:"";
  position:absolute;
  border-radius: 10px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.75);
  box-shadow: 0 12px 20px rgba(2,6,23,0.06);
}
.hub-illu:before{
  width: 74px; height: 54px;
  left: 30px; top: 46px;
}
.hub-illu:after{
  width: 54px; height: 40px;
  left: 78px; top: 82px;
}

/* CTA */
.hub-cta{
  position:absolute;
  right: 12px;
  bottom: 10px;
  font-size: 12px;
  font-weight: 950;
  color: rgba(15,23,42,0.55);
}

/* markdown margin reset */
div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>

<script>
/* ✅ 同一視窗導頁：攔截所有 hub 連結 */
(function () {
  function bind() {
    document.querySelectorAll('a[data-hub-link="1"]').forEach(a => {
      a.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.assign(a.getAttribute('href'));
      }, { passive: false });
    });
  }
  const root = document.querySelector('#root') || document.body;
  const obs = new MutationObserver(() => bind());
  obs.observe(root, { childList: true, subtree: true });
  bind();
})();
</script>
""",
        unsafe_allow_html=True,
    )


def _pill(label: str, page_path: str = ""):
    """上方分頁列（可點）"""
    if page_path:
        encoded = quote(page_path, safe="/_.-")
        href = f"?page={encoded}"
    else:
        href = "#"

    st.markdown(
        f"""
<a data-hub-link="1" class="hub-pill" href="{href}" target="_self">
  <span class="dot"></span>
  <span>{label}</span>
</a>
""",
        unsafe_allow_html=True,
    )


def _hub_card(title: str, sub: str, page_path: str, illu_class: str):
    encoded = quote(page_path, safe="/_.-")
    st.markdown(
        f"""
<a data-hub-link="1" href="?page={encoded}" target="_self">
  <div class="hub-card">
    <div class="hub-title">{title}</div>
    <div class="hub-sub">{sub}</div>
    <div class="hub-illu {illu_class}"></div>
    <div class="hub-cta">進入 →</div>
  </div>
</a>
""",
        unsafe_allow_html=True,
    )


def main():
    _route_by_query()

    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 課別入口")
    _css_and_js()

    # 上方分頁列（你要像圖那種）
    st.markdown('<div class="hub-topbar">', unsafe_allow_html=True)
    _pill("首頁")  # 目前就在首頁，先做樣式一致
    _pill("出貨課", "pages/7_出貨課首頁.py")
    _pill("進貨課", "pages/8_進貨課首頁.py")
    st.markdown("</div>", unsafe_allow_html=True)

    # 入口卡片區（方框，不是橫幅）
    st.markdown('<div class="hub-grid">', unsafe_allow_html=True)

    _hub_card(
        "出貨課",
        "Outbound｜撥貨差異、出貨/包裝/異常",
        "pages/7_出貨課首頁.py",
        "illu-outbound",
    )
    _hub_card(
        "進貨課",
        "Inbound｜驗收/上架/總揀/儲位/差異代庫存",
        "pages/8_進貨課首頁.py",
        "illu-inbound",
    )

    # 你之後想加更多入口（照這個格式加）
    # _hub_card("盤點中心", "Cycle Count｜盤點排程/異常", "pages/xx.py", "illu-outbound")
    # _hub_card("稽核中心", "Audit｜營運稽核與復盤", "pages/9_總檢討中心.py", "illu-inbound")

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()


if __name__ == "__main__":
    main()
