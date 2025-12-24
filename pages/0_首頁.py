import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # 依你的路徑調整
    layout="wide",
)

inject_logistics_theme()

# 讓首頁的「標題按鈕」看起來像條列文字（不藍、不底線、不像按鈕）
st.markdown(
    """
<style>
/* 模組條列：按鈕偽裝成文字 */
._home_link .stButton>button{
  all: unset;
  cursor: pointer;
  display: inline-block;
  font-weight: 900;
  font-size: 16px;
  line-height: 1.4;
  color: rgba(15,23,42,0.92);
  padding: 2px 0;
}
._home_link .stButton>button:hover{
  opacity: 0.85;
}

/* 每個條列的次行描述 */
._home_desc{
  margin: 4px 0 10px 0;
  color: rgba(15,23,42,0.70);
  font-weight: 650;
  font-size: 13px;
}
</style>
""",
    unsafe_allow_html=True,
)

def nav_item(icon: str, title: str, page_path: str, desc: str):
    """條列式：點標題就同視窗切換到 pages"""
    st.markdown("- ", unsafe_allow_html=True)
    cols = st.columns([0.06, 0.94])
    with cols[0]:
        st.write(icon)
    with cols[1]:
        st.markdown('<div class="_home_link">', unsafe_allow_html=True)
        if st.button(f"{title}", key=f"go_{page_path}"):
            st.switch_page(page_path)  # ✅ 同一視窗切換
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(f'<div class="_home_desc">{desc}</div>', unsafe_allow_html=True)


def main():
    set_page(
        "大豐物流 - 作業平台",
        icon="",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組（首頁導覽）")

    nav_item(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
    )
    nav_item(
        "📦",
        "上架作業效能（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
    )
    nav_item(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、門檻設定、排除非作業區間、匯出報表",
    )
    nav_item(
        "🧊",
        "儲位使用率",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、門檻提示、分類可調整、KPI圖表呈現",
    )
    nav_item(
        "🔎",
        "揀貨差異代庫存",
        "pages/5_揀貨差異代庫存.py",
        "少揀差異展開、庫存儲位/效期對應、國際條碼後五碼放大顯示",
    )

    card_close()

    st.divider()
    st.caption("提示：點上方模組名稱會直接在同一個視窗切換到對應頁面。")


if __name__ == "__main__":
    main()
