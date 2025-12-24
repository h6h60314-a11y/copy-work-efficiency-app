# pages/8_進貨課首頁.py
import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="進貨課", page_icon="🚚", layout="wide")
inject_logistics_theme()


def _list_css():
    st.markdown(
        r"""
<style>
/* 條列式清單（跟你截圖那種） */
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
.dept-right{
  flex: 1 1 auto;
  line-height: 1.55;
}
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
    # 用 st.switch_page 最穩（保證是 st.navigation 註冊的頁）
    if st.button(f"{icon} {title}", key=f"btn_{page_path}", use_container_width=True):
        st.switch_page(page_path)
    # 讓按鈕變成「條列式」外觀（不想要按鈕感）
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
    set_page("進貨課", icon="🚚", subtitle="Inbound｜進貨相關模組入口")

    card_open("🚚 進貨課模組")
    _list_css()

    st.markdown('<div class="dept-list">', unsafe_allow_html=True)

    _item(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、排除非作業區間（支援/離站/停機）",
    )
    _item(
        "📦",
        "上架產能分析（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、區塊/報表規則、班別切分",
    )
    _item(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、低空/高空門檻、排除非作業區間、匯出報表",
    )
    _item(
        "🧊",
        "儲位使用率分析",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、KPI圖格呈現",
    )
    _item(
        "🔎",
        "揀貨差異代庫存",
        "pages/5_揀貨差異代庫存.py",
        "少揀差異展開、庫存儲位/效期對應、國際條碼後五碼放大顯示",
    )

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()


if __name__ == "__main__":
    main()
