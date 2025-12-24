import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="🚚",
    layout="wide",
)

inject_logistics_theme()


def _home_css():
    st.markdown(
        r"""
<style>
/* 讓首頁清單更緊湊（不留大空格） */
.home-list{ margin-top: 6px; }
.home-row{
  display: flex;
  align-items: flex-start;
  gap: 8px;                 /* ✅ 三者間距 */
  margin: 10px 0;           /* ✅ 每列間距 */
}

/* 左側 bullet + icon：固定很小寬度 */
.home-left{
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  min-width: 42px;          /* ✅ 控制左側佔位，越小越緊 */
}

/* bullet / icon */
.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
  margin-top: 2px;
}
.home-ico{
  font-size: 15px;
  line-height: 1;
  margin-top: 1px;
}

/* 右側文字區 */
.home-right{
  flex: 1 1 auto;
  line-height: 1.55;
}

/* page_link 變成 inline（避免自帶空白） */
.home-right [data-testid="stPageLink"]{
  display: inline !important;
  margin: 0 !important;
  padding: 0 !important;
}
.home-right [data-testid="stPageLink"] a{
  display: inline !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  border-radius: 0 !important;
  text-decoration: none !important;

  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900 !important;
  font-size: 16px !important;
  line-height: 1.45 !important;
}
.home-right [data-testid="stPageLink"] a:hover{
  opacity: 0.86 !important;
}

/* 同行描述 */
.home-desc{
  display: inline;
  margin-left: 6px;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}

/* 把 Streamlit block 預設空白壓到最小 */
div[data-testid="stMarkdown"], div[data-testid="stPageLink"]{
  margin: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def nav_item(icon: str, title: str, page: str, desc: str):
    # 用 HTML 做「• + icon」左側，再用 page_link 當可點標題
    st.markdown(
        f"""
<div class="home-row">
  <div class="home-left">
    <div class="home-bullet">•</div>
    <div class="home-ico">{icon}</div>
  </div>
  <div class="home-right">
""",
        unsafe_allow_html=True,
    )

    st.page_link(page, label=f"{title}：")
    st.markdown(f'<span class="home-desc">{desc}</span>', unsafe_allow_html=True)

    st.markdown("</div></div>", unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")

    # ✅ card_open 後注入，避免 common_ui 後續再蓋掉
    _home_css()

    st.markdown('<div class="home-list">', unsafe_allow_html=True)

    nav_item(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、排除非作業區間（支援/離站/停機）",
    )

    nav_item(
        "📦",
        "上架產能分析（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、區塊/報表規則、班別切分",
    )

    nav_item(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、低空/高空門檻、排除非作業區間、匯出報表",
    )

    nav_item(
        "🧊",
        "儲位使用率分析",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、KPI圖格呈現",
    )

    nav_item(
        "🔎",
        "揀貨差異代庫存",
        "pages/5_揀貨差異代庫存.py",
        "少揀差異展開、庫存儲位/效期對應、國際條碼後五碼放大顯示",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    card_close()


if __name__ == "__main__":
    main()
