# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 作業平台", page_icon="🚚", layout="wide")
inject_logistics_theme()

# ✅ 只允許跳到「app.py 有註冊的頁面」
ALLOW_PAGES = {
    "pages/7_出貨課首頁.py",
    "pages/8_進貨課首頁.py",
    "pages/6_撥貨差異.py",
    "pages/1_驗收作業效能.py",
    "pages/2_上架作業效能.py",
    "pages/3_總揀作業效能.py",
    "pages/4_儲位使用率.py",
    "pages/5_揀貨差異代庫存.py",
}


def _route_by_query():
    qp = st.query_params
    raw = qp.get("page", "")

    if isinstance(raw, list):
        raw = raw[0] if raw else ""

    if not raw:
        return

    target = unquote(raw)
    st.query_params.clear()

    if target not in ALLOW_PAGES:
        return

    try:
        st.switch_page(target)
    except Exception:
        return


def _home_css_and_js():
    st.markdown(
        r"""
<style>
/* ✅ 取消連結藍底/藍框 */
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

div[data-testid="stVerticalBlockBorderWrapper"]{
  background: rgba(255,255,255,0.98) !important;
  border-color: rgba(15, 23, 42, 0.12) !important;
  box-shadow: none !important;
}

/* ✅ 方框入口卡 */
.entry-grid{
  display: grid;
  grid-template-columns: repeat(5, minmax(190px, 1fr));
  gap: 14px;
  align-items: stretch;
  justify-content: start;
  margin-top: 8px;
}
@media (max-width: 1280px){
  .entry-grid{ grid-template-columns: repeat(3, minmax(190px, 1fr)); }
}
@media (max-width: 900px){
  .entry-grid{ grid-template-columns: repeat(2, minmax(190px, 1fr)); }
}
@media (max-width: 640px){
  .entry-grid{ grid-template-columns: repeat(1, minmax(190px, 1fr)); }
}

.dept-tile{
  position: relative;
  border-radius: 16px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.92);
  min-height: 110px;
  padding: 14px 14px 12px;
  overflow: hidden;
  box-shadow: 0 14px 26px rgba(2,6,23,0.06);
  transition: transform .08s ease, box-shadow .12s ease, border-color .12s ease;
}
.dept-tile:hover{
  transform: translateY(-1px);
  box-shadow: 0 18px 32px rgba(2,6,23,0.10);
  border-color: rgba(15,23,42,0.18);
}

.tile-head{
  display:flex; align-items:center; gap:10px;
}
.tile-icon{
  width: 36px; height: 36px;
  border-radius: 12px;
  display:flex; align-items:center; justify-content:center;
  font-size: 18px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.85);
}
.tile-name{
  font-size: 16px; font-weight: 950; line-height: 1.15;
  color: rgba(15,23,42,0.92);
}
.tile-desc{
  margin-top: 8px;
  font-size: 12px; font-weight: 850;
  color: rgba(15,23,42,0.62);
  line-height: 1.35;
}
.tile-foot{
  position:absolute;
  right: 12px;
  bottom: 10px;
  font-size: 12px;
  font-weight: 950;
  color: rgba(15,23,42,0.55);
}

.illu{
  position:absolute;
  right:-18px;
  top:-22px;
  width: 140px;
  height: 140px;
  border-radius: 30px;
  transform: rotate(10deg);
  opacity: 0.92;
  pointer-events:none;
}
.illu-out{
  background: linear-gradient(135deg, rgba(59,130,246,0.22), rgba(37,99,235,0.10));
}
.illu-in{
  background: linear-gradient(135deg, rgba(34,197,94,0.18), rgba(16,185,129,0.10));
}
.illu:before,.illu:after{
  content:"";
  position:absolute;
  border-radius: 10px;
  border: 1px solid rgba(15,23,42,0.10);
  background: rgba(255,255,255,0.75);
  box-shadow: 0 12px 20px rgba(2,6,23,0.06);
}
.illu:before{ width: 64px; height: 46px; left: 26px; top: 48px; }
.illu:after { width: 48px; height: 36px; left: 72px; top: 80px; }

div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>

<script>
/* ✅ 同一視窗導頁 */
(function () {
  function bind() {
    document.querySelectorAll('a[data-entry="1"]').forEach(a => {
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


def _tile_html(icon: str, title: str, desc: str, page_path: str, illu_class: str) -> str:
    """
    ⚠️ 這裡「完全不使用三引號」+「不插入換行/縮排」
    目的：避免 Streamlit/Markdown 把它判成 code block
    """
    encoded = quote(page_path, safe="/_.-")
    return (
        f'<a data-entry="1" class="dept-tile" href="?page={encoded}" target="_self">'
        f'<div class="tile-head">'
        f'<div class="tile-icon">{icon}</div>'
        f'<div class="tile-name">{title}</div>'
        f'</div>'
        f'<div class="tile-desc">{desc}</div>'
        f'<div class="illu {illu_class}"></div>'
        f'<div class="tile-foot">進入 →</div>'
        f'</a>'
    )


def main():
    _route_by_query()

    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 課別入口")
    _home_css_and_js()

    tiles = [
        _tile_html("📦", "出貨課", "撥貨差異、出貨/包裝/異常（進入後以條列式顯示模組）", "pages/7_出貨課首頁.py", "illu-out"),
        _tile_html("🚚", "進貨課", "驗收/上架/總揀/儲位/差異代庫存（進入後以條列式顯示模組）", "pages/8_進貨課首頁.py", "illu-in"),
    ]

    grid_html = '<div class="entry-grid">' + "".join(tiles) + "</div>"
    st.markdown(grid_html, unsafe_allow_html=True)

    card_close()


if __name__ == "__main__":
    main()
