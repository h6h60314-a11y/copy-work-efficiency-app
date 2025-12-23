import streamlit as st
from pathlib import Path

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ==================================================
# Page config
# ==================================================
st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="assets/gf_logo.png",  # ✅ 瀏覽器 tab 用 logo
    layout="wide",
)

inject_logistics_theme()


# ==================================================
# 同視窗切頁（query param）
# ==================================================
def _goto_if_any():
    goto = st.query_params.get("goto")
    if goto:
        st.query_params.clear()
        st.switch_page(goto)


# ==================================================
# Styles + JS（首頁條列專用）
# ==================================================
st.markdown(
    """
<style>
._home_item{
  display: grid;
  grid-template-columns: 18px 1fr;
  column-gap: 10px;
  margin: 14px 0 18px 0;
}
._home_bullet{
  font-size: 18px;
  color: rgba(15,23,42,0.85);
  padding-top: 2px;
}
._home_title{
  font-size: 15.5px;
  font-weight: 900;
  color: rgba(15,23,42,0.92);
}
._home_desc{
  margin-top: 4px;
  font-size: 13px;
  color: rgba(15,23,42,0.68);
  font-weight: 650;
}
._home_click{
  cursor: pointer;
}
._home_click:hover{
  opacity: 0.85;
}
</style>

<script>
function homeGoto(pagePath){
  const url = new URL(window.location.href);
  url.searchParams.set("goto", pagePath);
  window.location.assign(url.toString());
}
</script>
""",
    unsafe_allow_html=True,
)


def _item(title: str, desc: str, page_path: str):
    st.markdown(
        f"""
<div class="_home_item">
  <div class="_home_bullet">•</div>
  <div>
    <div class="_home_title">
      <span class="_home_click" onclick="homeGoto('{page_path}')">{title}</span>
    </div>
    <div class="_home_desc">{desc}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# ==================================================
# Main
# ==================================================
def main():
    _goto_if_any()

    # ===== 自訂 Header（Logo + Title）=====
    logo_path = Path("assets/gf_logo.png")

    col_logo, col_title = st.columns([1.1, 8.9], vertical_alignment="center")

    with col_logo:
        if logo_path.exists():
            st.image(str(logo_path), width=72)

    with col_title:
        # ❌ 不用 emoji icon
        set_page(
            "大豐物流 - 作業平台",
            subtitle="作業 KPI｜班別分析（AM/PM）｜排除非作業區間",
        )

    # ===== 模組導覽 =====
    card_open("📌 作業績效分析模組")

    _item(
        "驗收作業效能（KPI）",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        "pages/1_驗收作業效能.py",
    )

    _item(
        "上架作業效能（Putaway KPI）",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        "pages/2_上架作業效能.py",
    )

    _item(
        "總揀作業效能",
        "上午 / 下午達標分析、低空 / 高空門檻、排除非作業區間、匯出報表",
        "pages/3_總揀作業效能.py",
    )

    _item(
        "儲位使用率分析",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、報表匯出",
        "pages/4_儲位使用率.py",
    )

    _item(
        "揀貨差異",
        "少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示",
        "pages/5_揀貨差異代庫存後五碼放大.py",
    )

    card_close()

    st.divider()
    st.caption("提示：左側選單與本頁模組導覽皆可切換模組頁面；各頁設定互不影響。")


if __name__ == "__main__":
    main()
