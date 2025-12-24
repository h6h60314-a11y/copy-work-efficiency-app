# pages/9_大樹KPI首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大樹KPI", page_icon="📈", layout="wide")
inject_logistics_theme()

# 之後你新增 KPI 模組頁面，把路徑加進來
ALLOW_PAGES = {
    # "pages/9_大樹KPI_總覽.py",
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


def _css_and_js():
    st.markdown(
        r"""
<style>
.kpi-list{ margin-top: 6px; }
.kpi-row{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 12px 0;
}
.kpi-left{
  width: 34px;
  flex: 0 0 34px;
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 2px;
}
.kpi-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
}
.kpi-ico{ font-size: 16px; line-height: 1; }
.kpi-right{ flex: 1 1 auto; line-height: 1.55; }
.kpi-link{
  display: inline;
  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900;
  font-size: 16px;
  line-height: 1.45;
  text-decoration: none !important;
  cursor: pointer;
}
.kpi-link:hover{ opacity: 0.86; }
.kpi-desc{
  display: inline;
  margin-left: 6px;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}
div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>

<script>
(function () {
  function bind() {
    document.querySelectorAll('a.kpi-link').forEach(a => {
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


def _nav_item(icon: str, title: str, page_path: str, desc: str):
    encoded = quote(page_path, safe="/_.-")
    st.markdown(
        (
            f'<div class="kpi-row">'
            f'  <div class="kpi-left">'
            f'    <span class="kpi-bullet">•</span>'
            f'    <span class="kpi-ico">{icon}</span>'
            f'  </div>'
            f'  <div class="kpi-right">'
            f'    <a class="kpi-link" href="?page={encoded}" target="_self">{title}：</a>'
            f'    <span class="kpi-desc">{desc}</span>'
            f'  </div>'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )


def main():
    _route_by_query()

    set_page("大樹KPI", icon="📈", subtitle="KPI 模組入口｜匯總｜告警｜趨勢")

    card_open("📈 大樹KPI模組")
    _css_and_js()

    st.markdown('<div class="kpi-list">', unsafe_allow_html=True)

    # ✅ 先放「待新增」提示（你新增模組後，把下面改成真正頁面）
    st.info("請把新的 KPI 模組頁面加入 pages/，並在 app.py 與此頁面新增入口。")

    # 範例（你建立 pages/9_大樹KPI_總覽.py 後再打開）
    # _nav_item("📊", "KPI總覽", "pages/9_大樹KPI_總覽.py", "達標率、人時效率、趨勢、門檻告警")

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()


if __name__ == "__main__":
    main()
