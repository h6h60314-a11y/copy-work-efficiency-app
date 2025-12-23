import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="進貨課效能平台｜首頁",
    page_icon="🏠",
    layout="wide",
)

inject_logistics_theme()

# ✅ 同視窗切頁：用 query param 觸發 switch_page
def _goto_if_any():
    goto = st.query_params.get("goto")
    if goto:
        st.query_params.clear()
        st.switch_page(goto)

st.markdown(
    """
<style>
/* 條列排版：• + 標題 + 說明（純文字樣式） */
._home_item{
  display: grid;
  grid-template-columns: 18px 1fr;
  column-gap: 10px;
  margin: 14px 0 18px 0;
}
._home_bullet{
  font-size: 18px;
  line-height: 18px;
  color: rgba(15,23,42,0.85);
  padding-top: 2px;
}
._home_title{
  font-size: 15.5px;
  line-height: 22px;
  color: rgba(15,23,42,0.92);
  font-weight: 900;
  margin: 0;
}
._home_desc{
  margin-top: 4px;
  font-size: 13px;
  line-height: 18px;
  color: rgba(15,23,42,0.68);
  font-weight: 650;
}

/* ✅ 可點但不像連結：不藍、不底線、不變按鈕 */
._home_click{
  cursor: pointer;
  display: inline-block;
  color: inherit;
  text-decoration: none;
}
._home_click:hover{
  opacity: 0.86;
}
</style>

<script>
function homeGoto(pagePath){
  // ✅ 同視窗：直接改目前頁面的 query param
  const url = new URL(window.location.href);
  url.searchParams.set("goto", pagePath);
  window.location.assign(url.toString()); // same tab
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

def main():
    _goto_if_any()

    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業 KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")

    _item(
        "✅ 驗收作業效能（KPI）：",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        "pages/1_驗收作業效能.py",
    )
    _item(
        "📦 上架作業效能（Putaway KPI）：",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        "pages/2_上架作業效能.py",
    )
    _item(
        "🎯 總揀作業效能：",
        "上午 / 下午達標分析、低空 / 高空門檻、排除非作業區間、匯出報表",
        "pages/3_總揀作業效能.py",
    )
    _item(
        "🧊 儲位使用率分析：",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、報表匯出",
        "pages/4_儲位使用率.py",
    )
    _item(
        "🔎 揀貨差異：",
        "少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示",
        "pages/5_揀貨差異代庫存後五碼放大.py",
    )

    card_close()

    st.divider()
    st.caption("提示：左側選單與本頁模組導覽皆可切換模組頁面；各頁設定互不影響。")

if __name__ == "__main__":
    main()
