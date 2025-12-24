import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="🚚",
    layout="wide",
)

inject_logistics_theme()


def _home_css():
    # ⚠️ 一定要在 set_page 之後再注入，才能蓋掉 common_ui 的樣式
    st.markdown(
        r"""
<style>
/* =========================================================
   Home list style: match screenshot (• + icon + clickable title + inline desc)
   ========================================================= */

/* row spacing */
.home-row{
  margin: 10px 0 10px 0;
}

/* bullet / icon */
.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 18px;
  line-height: 1;
  margin-top: 2px;
}
.home-ico{
  font-size: 15px;
  line-height: 1;
  margin-top: 3px;
}

/* container that holds (button + inline desc) */
.home-item{
  margin: 0;
}

/* ✅ make st.button wrapper inline so it can sit next to the desc */
.home-item div[data-testid="stButton"]{
  display: inline-block !important;
  vertical-align: top !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* ✅ make button look like bold text link */
.home-item div[data-testid="stButton"] > button{
  display: inline !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  padding: 0 !important;
  margin: 0 !important;
  border-radius: 0 !important;

  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900 !important;
  font-size: 16px !important;
  line-height: 1.45 !important;

  cursor: pointer !important;
}

.home-item div[data-testid="stButton"] > button:hover{
  opacity: 0.85 !important;
  text-decoration: none !important;
}

.home-item div[data-testid="stButton"] > button:focus,
.home-item div[data-testid="stButton"] > button:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}

/* ✅ inline description after title (same line) */
.home-desc-inline{
  display: inline !important;
  margin-left: 6px !important;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
  white-space: normal;
}

/* reduce Streamlit column vertical padding */
div[data-testid="column"]{
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def nav_item(icon: str, title: str, page: str, desc: str, key: str):
    """
    目標：跟截圖一模一樣
    • [icon]  粗體可點標題：描述（同一行，會自動換行）
    """
    c1, c2, c3 = st.columns([0.035, 0.05, 0.915], vertical_alignment="top")

    with c1:
        st.markdown('<div class="home-bullet">•</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div class="home-ico">{icon}</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="home-row"><div class="home-item">', unsafe_allow_html=True)

        # ✅ 可點標題（同視窗切頁）
        if st.button(f"{title}：", key=key):
            st.switch_page(page)

        # ✅ 同一行描述（緊接在標題後面）
        st.markdown(f'<span class="home-desc-inline">{desc}</span>', unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    # ✅ 必須在 set_page 後面注入
    _home_css()

    card_open("📌 作業績效分析模組")

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
