import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="🚚",
    layout="wide",
)

inject_logistics_theme()


def _home_css():
    # ⚠️ 一定要在 set_page 之後再注入，才能蓋掉 common_ui 的按鈕膠囊樣式
    st.markdown(
        """
<style>
/* =========================================================
   Home navigation: force buttons to look like plain text
   (override common_ui .stButton > button)
   ========================================================= */

div[data-testid="stButton"] > button{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  border-radius: 0 !important;

  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900 !important;
  font-size: 16px !important;
  line-height: 1.25 !important;
}

div[data-testid="stButton"] > button:hover{
  opacity: 0.86 !important;
}

div[data-testid="stButton"] > button:focus,
div[data-testid="stButton"] > button:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}

/* reduce column padding + vertical whitespace */
div[data-testid="column"]{
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
.home-item{
  margin: 0 0 12px 0;
}
.home-desc{
  margin: 2px 0 0 0;
  color: rgba(15, 23, 42, 0.70);
  font-weight: 650;
  font-size: 13px;
  line-height: 1.45;
}
.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 18px;
  line-height: 1.0;
  margin-top: 2px;
}
.home-ico{
  font-size: 15px;
  line-height: 1.0;
  margin-top: 3px;
}
</style>
""",
        unsafe_allow_html=True,
    )


def nav_item(icon: str, title: str, page: str, desc: str, key: str):
    """
    乾淨條列式：
    • [icon]  標題（可點、但外觀是文字）：
      描述
    """
    c1, c2, c3 = st.columns([0.035, 0.05, 0.915], vertical_alignment="top")

    with c1:
        st.markdown('<div class="home-bullet">•</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div class="home-ico">{icon}</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="home-item">', unsafe_allow_html=True)
        if st.button(f"{title}：", key=key):
            st.switch_page(page)  # ✅ 同一視窗切頁
        st.markdown(f'<div class="home-desc">{desc}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    # ✅ 重要：在 set_page 後面注入，才能蓋掉 common_ui 的 button 膠囊樣式
    _home_css()

    card_open("📌 作業績效分析模組")

    nav_item(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        key="nav_qc",
    )

    nav_item(
        "📦",
        "上架作業效能（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        key="nav_put",
    )

    nav_item(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、門檻設定、排除非作業區間、匯出報表",
        key="nav_pick",
    )

    nav_item(
        "🧊",
        "儲位使用率分析",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、門檻提示、分類可調整、KPI圖格呈現",
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

    st.divider()
    st.caption("提示：點上方「模組標題」會在同一個視窗切換到對應頁面；外觀維持條列式呈現。")


if __name__ == "__main__":
    main()
