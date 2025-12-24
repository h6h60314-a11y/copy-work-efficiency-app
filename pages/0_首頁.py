import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="🚚",
    layout="wide",
)

inject_logistics_theme()


def _home_css():
    # 一定要在 set_page + card_open 後面注入，避免被 common_ui 後續樣式蓋回去
    st.markdown(
        r"""
<style>
/* =========================
   Home list = match screenshot
   • + icon + (clickable bold title) + inline description
   ========================= */

.home-row{ margin: 10px 0; }
.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 18px;
  line-height: 1;
  margin-top: 2px;
}
.home-ico{
  font-size: 16px;
  line-height: 1;
  margin-top: 3px;
}

.home-item{ line-height: 1.6; }

/* ✅ page_link 外層容器改成 inline，才能跟描述同一行 */
.home-item [data-testid="stPageLink"]{
  display: inline-block !important;
  vertical-align: top !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* ✅ 把 page_link 渲染出來的 a 變成「粗體文字可點」，移除膠囊感 */
.home-item [data-testid="stPageLink"] a{
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
.home-item [data-testid="stPageLink"] a:hover{
  opacity: 0.86 !important;
}

/* ✅ 冒號後面描述（同一行） */
.home-desc-inline{
  display: inline !important;
  margin-left: 6px !important;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}

/* Streamlit columns 內距縮小 */
div[data-testid="column"]{
  padding-top: 0 !important;
  padding-bottom: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def nav_item(icon: str, title: str, page: str, desc: str):
    """
    目標：跟截圖一模一樣（同一行）
    •  [icon]  可點標題：描述
    """
    c1, c2, c3 = st.columns([0.02, 0.05, 0.93], vertical_alignment="top")

    with c1:
        st.markdown('<div class="home-bullet">•</div>', unsafe_allow_html=True)

    with c2:
        st.markdown(f'<div class="home-ico">{icon}</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="home-row"><div class="home-item">', unsafe_allow_html=True)

        # ✅ 可點跳頁：同一視窗切換（streamlit 原生導覽）
        st.page_link(page, label=f"{title}：")

        # ✅ 同一行描述
        st.markdown(f'<span class="home-desc-inline">{desc}</span>', unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")

    # ✅ 重要：card_open 後再注入，避免 common_ui 再覆蓋
    _home_css()

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

    card_close()


if __name__ == "__main__":
    main()
