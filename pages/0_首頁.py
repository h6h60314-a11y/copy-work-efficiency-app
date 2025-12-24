import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="🚚",
    layout="wide",
)

inject_logistics_theme()


def _home_css():
    # ✅ 一定要在 set_page + card_open 後注入，才不會被 common_ui 後續覆蓋
    st.markdown(
        r"""
<style>
/* =========================
   Home list (tight + inline)
   ========================= */

/* 左側：• + icon 緊湊 */
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

/* 每列間距（你要更緊：12px→8px） */
.home-row-space{
  height: 12px;
}

/* =========================
   🔥 核心：用 marker 精準抓「下一顆 stButton」並解除膠囊
   DOM 會是：
   [stMarkdown(marker)] + [stButton] + [stMarkdown(desc)] + [stMarkdown(spacer)]
   ========================= */

/* marker 那個 stMarkdown 容器直接隱藏（不佔空間，但仍可用來做 selector） */
div[data-testid="stMarkdown"]:has(.nav-marker){
  display: none !important;
}

/* marker 後面的那顆 stButton：改成 inline，避免換行 */
div[data-testid="stMarkdown"]:has(.nav-marker) + div[data-testid="stButton"]{
  display: inline-block !important;
  margin: 0 !important;
  padding: 0 !important;
  vertical-align: top !important;
}

/* ✅ 把 common_ui 的膠囊樣式完全拔掉 */
div[data-testid="stMarkdown"]:has(.nav-marker) + div[data-testid="stButton"] button{
  all: unset !important;            /* 直接清空所有主題/預設 */
  display: inline !important;
  cursor: pointer !important;

  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900 !important;
  font-size: 16px !important;
  line-height: 1.45 !important;
}
div[data-testid="stMarkdown"]:has(.nav-marker) + div[data-testid="stButton"] button:hover{
  opacity: 0.86 !important;
}

/* ✅ 描述那個 stMarkdown：強制 inline，貼在標題後面同一行 */
div[data-testid="stMarkdown"]:has(.nav-marker)
  + div[data-testid="stButton"]
  + div[data-testid="stMarkdown"]{
  display: inline-block !important;
  margin: 0 !important;
  padding: 0 !important;
  vertical-align: top !important;
}

.home-desc-inline{
  display: inline !important;
  margin-left: 6px !important;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}

/* 壓掉 Streamlit 容器預設空白 */
div[data-testid="stButton"], div[data-testid="stMarkdown"]{
  margin: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def nav_item(icon: str, title: str, page: str, desc: str, key: str):
    # 左(•+icon) / 右(可點標題 + 同行描述)
    c1, c2 = st.columns([0.07, 0.93], vertical_alignment="top")

    with c1:
        st.markdown(
            f'<div class="home-left"><span class="home-bullet">•</span><span class="home-ico">{icon}</span></div>',
            unsafe_allow_html=True,
        )

    with c2:
        # ✅ marker：用來讓 CSS 精準鎖到「下一顆 stButton」
        st.markdown(f'<span class="nav-marker" data-k="{key}"></span>', unsafe_allow_html=True)

        # ✅ 可點標題：同視窗跳頁
        if st.button(f"{title}：", key=key, use_container_width=False):
            st.switch_page(page)

        # ✅ 描述：會被 CSS 拉成同一行
        st.markdown(f'<span class="home-desc-inline">{desc}</span>', unsafe_allow_html=True)

        # ✅ 列與列之間的間距
        st.markdown('<div class="home-row-space"></div>', unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")

    # ✅ card_open 後注入，避免被 common_ui 蓋回去
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
