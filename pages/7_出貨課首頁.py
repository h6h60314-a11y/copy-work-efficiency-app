# pages/7_出貨課首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="出貨課", page_icon="📦", layout="wide")
inject_logistics_theme()

ALLOW_PAGES = {
    "pages/6_撥貨差異.py",
    "pages/23_採品門市差異量.py",
    "pages/24_出貨作業線產能.py",
    "pages/29_各時段作業效率.py",
    "pages/30_客訂差異.py",
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
/* 條列式（跟你原本那種一致） */
.dept-list{ margin-top: 6px; }
.dept-row{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 12px 0;
}
.dept-left{
  width: 34px;
  flex: 0 0 34px;
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 2px;
}
.dept-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
}
.dept-ico{
  font-size: 16px;
  line-height: 1;
}
.dept-right{
  flex: 1 1 auto;
  line-height: 1.55;
}
.dept-link{
  display: inline;
  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900;
  font-size: 16px;
  line-height: 1.45;
  text-decoration: none !important;
  cursor: pointer;
}
.dept-link:hover{ opacity: 0.86; }
.dept-desc{
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
/* 同一視窗導頁 */
(function () {
  function bind() {
    document.querySelectorAll('a.dept-link').forEach(a => {
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
            f'<div class="dept-row">'
            f'  <div class="dept-left">'
            f'    <span class="dept-bullet">•</span>'
            f'    <span class="dept-ico">{icon}</span>'
            f'  </div>'
            f'  <div class="dept-right">'
            f'    <a class="dept-link" href="?page={encoded}" target="_self">{title}：</a>'
            f'    <span class="dept-desc">{desc}</span>'
            f'  </div>'
            f'</div>'
        ),
        unsafe_allow_html=True,
    )


def main():
    _route_by_query()

    set_page("出貨課", icon="📦", subtitle="Outbound｜出貨相關模組入口")

    card_open("📦 出貨課模組")
    _css_and_js()

    st.markdown('<div class="dept-list">', unsafe_allow_html=True)

    _nav_item(
        "📦",
        "撥貨差異",
        "pages/6_撥貨差異.py",
        "AllDIF/ALLACT 篩選、明細匯整、儲位比對棚別、輸出差異明細",
    )

    _nav_item(
        "📄",
        "採品門市差異量",
        "pages/23_採品門市差異量.py",
        "依『未配出原因』回填至同名分頁，輸出更新後差異量檔",
    )

    _nav_item(
        "📦",
        "出貨作業線產能",
        "pages/24_出貨作業線產能.py",
        "每日各作業線產力狀況，輸出每日達標檔",
    )

    _nav_item(
        "⏱️",
        "各時段作業效率",
        "pages/29_各時段作業效率.py",
        "依 LINEID/ZONEID(1~4) 計算去重後加權PCS，逐時段 PASS/FAIL 著色並可下載 Excel",
    )

    _nav_item(
        "🧾",
        "客訂差異",
        "pages/30_客訂差異.py",
        "客訂差異篩選、商品主檔比對、其他儲位短效優先、棚別回填並輸出最後篩選明細",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    card_close()


if __name__ == "__main__":
    main()
