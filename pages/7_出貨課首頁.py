# pages/7_出貨課首頁.py
import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="出貨課", page_icon="📦", layout="wide")
inject_logistics_theme()


def _list_css():
    st.markdown(
        r"""
<style>
.dept-list{ margin-top: 4px; }
.dept-row{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin: 12px 0;
}
.dept-ico{
  width: 26px;
  flex: 0 0 26px;
  text-align: center;
  font-size: 16px;
  line-height: 1;
  margin-top: 2px;
}
.dept-right{ flex: 1 1 auto; line-height: 1.55; }
.dept-link{
  display: inline;
  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 950;
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
""",
        unsafe_allow_html=True,
    )


def _item(icon: str, title: str, page_path: str, desc: str):
    if st.button(f"{icon} {title}", key=f"btn_{page_path}", use_container_width=True):
        st.switch_page(page_path)

    st.markdown(
        f"""
<div class="dept-row">
  <div class="dept-ico">{icon}</div>
  <div class="dept-right">
    <a class="dept-link" onclick="void(0)">{title}</a>
    <span class="dept-desc">{desc}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def main():
    set_page("出貨課", icon="📦", subtitle="Outbound｜出貨相關模組入口")

    card_open("📦 出貨課模組")
    _list_css()

    st.markdown('<div class="dept-list">', unsafe_allow_html=True)

    _item(
        "📦",
        "撥貨差異",
        "pages/6_撥貨差異.py",
        "AllDIF/ALLACT 篩選、明細匯整、儲位比對棚別、輸出差異明細",
    )

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()


if __name__ == "__main__":
    main()
