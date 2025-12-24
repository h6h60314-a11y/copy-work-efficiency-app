import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # 依你的專案路徑調整
    layout="wide",
)

inject_logistics_theme()

# ✅ 讓「標題」是可點的，但外觀維持你現在的條列式（不藍、不底線、不像按鈕）
st.markdown(
    """
<style>
/* 條列區塊：把 st.button 偽裝成純文字標題 */
._nav_item .stButton > button{
  all: unset;
  cursor: pointer;
  display: inline;
  color: rgba(15, 23, 42, 0.92);
  font-weight: 900;
  font-size: 16px;
  line-height: 1.45;
}
._nav_item .stButton > button:hover{
  opacity: 0.85;
}

/* 次行描述 */
._nav_desc{
  margin: 2px 0 12px 0;
  color: rgba(15, 23, 42, 0.70);
  font-weight: 650;
  font-size: 13px;
  line-height: 1.45;
}

/* 讓 icon/點點對齊 */
._bullet{
  font-size: 18px;
  line-height: 1.2;
  color: rgba(15, 23, 42, 0.75);
  margin-top: 2px;
}
._ico{
  font-size: 16px;
  margin-top: 2px;
}
</style>
""",
    unsafe_allow_html=True,
)


def nav_row(icon: str, title: str, page_path: str, desc: str, key: str):
    """
    版型：• + icon + (可點標題) + 次行描述
    點標題：同視窗切到對應 page
    """
    row = st.columns([0.03, 0.04, 0.93], vertical_alignment="top")

    with row[0]:
        st.markdown('<div class="_bullet">•</div>', unsafe_allow_html=True)

    with row[1]:
        st.markdown(f'<div class="_ico">{icon}</div>', unsafe_allow_html=True)

    with row[2]:
        st.markdown('<div class="_nav_item">', unsafe_allow_html=True)
        if st.button(f"{title}：", key=key):
            st.switch_page(page_path)  # ✅ 同一個視窗切頁
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(f'<div class="_nav_desc">{desc}</div>', unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="🏠",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")

    nav_row(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        key="go_qc",
    )

    nav_row(
        "📦",
        "上架作業效能（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        key="go_putaway",
    )

    nav_row(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、門檻設定、排除非作業區間、匯出報表",
        key="go_pick",
    )

    nav_row(
        "🧊",
        "儲位使用率分析",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、門檻提示、分類可調整、KPI圖格呈現",
        key="go_slot",
    )

    nav_row(
        "🔎",
        "揀貨差異代庫存",
        "pages/5_揀貨差異代庫存後五碼放大.py",
        "少揀差異展開、庫存儲位/效期對應、國際條碼後五碼放大顯示",
        key="go_diff",
    )

    card_close()

    st.divider()
    st.caption("提示：點上方「模組標題」會在同一個視窗切換到對應頁面。")


if __name__ == "__main__":
    main()
