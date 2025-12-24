import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="🚚",
    layout="wide",
)

inject_logistics_theme()


def _home_css():
    # ⚠️ 一定要在 set_page / card_open 後注入，權重才壓得過 common_ui
    st.markdown(
        r"""
<style>
/* ===== 左側：• + icon 緊湊 ===== */
.home-left{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}
.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
}
.home-ico{
  font-size: 16px;
  line-height: 1;
}

/* ===== 右側：標題可點 + 描述同一行 ===== */
/* 只針對「後面緊接著 .home-desc-inline 的那顆 button」做 inline 化，避免影響其它頁 */
div[data-testid="stButton"]:has(+ div .home-desc-inline){
  display: inline-block !important;
  margin: 0 !important;
  padding: 0 !important;
  vertical-align: top !important;
}
div[data-testid="stButton"]:has(+ div .home-desc-inline) + div{
  display: inline-block !important; /* 描述那個 markdown 容器也 inline */
  margin: 0 !important;
  padding: 0 !important;
  vertical-align: top !important;
}

/* ✅ 把按鈕徹底重置成純文字（壓過 common_ui 的膠囊樣式） */
div[data-testid="stButton"]:has(+ div .home-desc-inline) button{
  all: unset !important;             /* 直接清空所有預設/主題樣式 */
  display: inline !important;
  cursor: pointer !important;

  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900 !important;
  font-size: 16px !important;
  line-height: 1.45 !important;
}
div[data-testid="stButton"]:has(+ div .home-desc-inline) button:hover{
  opacity: 0.86 !important;
}

/* 同行描述 */
.home-desc-inline{
  display: inline !important;
  margin-left: 6px !important;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}

/* 列與列之間緊湊一點 */
.home-row-space{
  margin: 10px 0 !important;
}

/* 壓掉 Streamlit 元件容器的多餘空白（只在首頁注入，不影響其它檔案） */
div[data-testid="stMarkdown"], div[data-testid="stButton"]{
  margin: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def nav_item(icon: str, title: str, page: str, desc: str, key: str):
    # 兩欄：左(•+icon) / 右(可點標題+描述同行)
    c1, c2 = st.columns([0.09, 0.91], vertical_alignment="top")

    with c1:
        st.markdown(
            f'<div class="home-left"><span class="home-bullet">•</span><span class="home-ico">{icon}</span></div>',
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown('<div class="home-row-space">', unsafe_allow_html=True)

        # ✅ 可點跳頁（同一視窗）
        if st.button(f"{title}：", key=key, use_container_width=False):
            st.switch_page(page)

        # ✅ 描述（會被 CSS 拉到同一行）
        st.markdown(f'<span class="home-desc-inline">{desc}</span>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")

    _home_css()

    nav_item(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、排除非作業區間（支援/離站/停機）",
        key="nav_qc",
    )

    nav_item(
        "📦",
        "上架產能分析（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、區塊/報表規則、班別切分",
        key="nav_put",
    )

    nav_item(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、低空/高空門檻、排除非作業區間、匯出報表",
        key="nav_pick",
    )

    nav_item(
        "🧊",
        "儲位使用率分析",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、KPI圖格呈現",
        key="nav_slot",
    )

    nav_item(
        "🔎",
        "揀貨差異代庫存",
        "pages/5_揀貨差異代庫存.py",
        "少揀差異展開、庫存儲位/效期對應、國際條碼後五碼放大顯示",
        key="nav_diff",
    )

    card_close()


if __name__ == "__main__":
    main()
