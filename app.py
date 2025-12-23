import streamlit as st
from pathlib import Path

from common_ui import inject_logistics_theme, set_page, card_open, card_close

# ==================================================
# Page config
# ==================================================
st.set_page_config(
    page_title="進貨課效能平台",
    page_icon="🏭",
    layout="wide",
)

# ==================================================
# Left navigation (✅ app -> 首頁)
# ==================================================
PAGES = {
    "首頁": [
        st.Page("app.py", title="首頁", icon="🏠"),
    ],
    "作業模組": [
        st.Page("pages/1_驗收作業效能.py", title="驗收作業效能", icon="✅"),
        st.Page("pages/2_上架作業效能.py", title="上架作業效能", icon="📦"),
        st.Page("pages/3_總揀作業效能.py", title="總揀作業效能", icon="🎯"),
        st.Page("pages/4_儲位使用率.py", title="儲位使用率", icon="🧊"),
        st.Page("pages/5_揀貨差異代庫存.py", title="揀貨差異代庫存", icon="🔎"),
    ],
}

pg = st.navigation(PAGES)
# 如果目前不是首頁（app.py），直接交給 navigation 跑對應 page
if pg.url_path != "app":
    pg.run()
    st.stop()


# ==================================================
# Theme + Home UI (1:1 條列樣式 + 同視窗切頁)
# ==================================================
inject_logistics_theme()

st.markdown(
    """
<style>
/* 條列式：• + 標題 + 說明（完全像你原本那張） */
._gt_list{ margin-top: 6px; }

._gt_item{
  display:flex;
  gap: 14px;
  align-items:flex-start;
  margin: 12px 0 18px 0;
}

._gt_bullet{
  width: 10px;
  flex: 0 0 10px;
  padding-top: 2px;
  color: rgba(15,23,42,0.85);
  font-size: 18px;
  line-height: 18px;
}

._gt_body{ flex: 1; }

._gt_title{
  font-weight: 900;
  font-size: 16px;
  line-height: 22px;
  color: rgba(15,23,42,0.92);
  margin: 0;
}

._gt_desc{
  margin-top: 4px;
  font-weight: 600;
  font-size: 13px;
  line-height: 18px;
  color: rgba(15,23,42,0.68);
}

/* 可點文字（看起來不是連結：不藍、不底線） */
._gt_click{
  cursor: pointer;
  text-decoration: none !important;
  color: inherit !important;
}
._gt_click:hover{
  opacity: 0.86;
  text-decoration: none !important;
}
</style>

<script>
function gtGoto(pagePath){
  // 同視窗改 query param，讓 streamlit rerun -> switch_page
  const url = new URL(window.location.href);
  url.searchParams.set("goto", pagePath);
  window.location.href = url.toString();
}
</script>
""",
    unsafe_allow_html=True,
)


def _render_item(title: str, desc: str, page_path: str | None):
    if page_path:
        title_html = f"""
        <a class="_gt_click" href="javascript:gtGoto('{page_path}')">
          {title}
        </a>
        """
    else:
        title_html = title

    st.markdown(
        f"""
<div class="_gt_item">
  <div class="_gt_bullet">•</div>
  <div class="_gt_body">
    <div class="_gt_title">{title_html}</div>
    <div class="_gt_desc">{desc}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def main():
    # ✅ 點條列後：同視窗切頁
    goto = st.query_params.get("goto", None)
    if goto:
        st.query_params.clear()
        st.switch_page(goto)

    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業 KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")

    st.markdown('<div class="_gt_list">', unsafe_allow_html=True)

    _render_item(
        "✅ 驗收作業效能（KPI）：",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        "pages/1_驗收作業效能.py",
    )
    _render_item(
        "📦 上架作業效能（Putaway KPI）：",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        "pages/2_上架作業效能.py",
    )
    _render_item(
        "🎯 總揀作業效能：",
        "上午 / 下午達標分析、低空 / 高空門檻、排除非作業區間、匯出報表",
        "pages/3_總揀作業效能.py",
    )
    _render_item(
        "🧊 儲位使用率分析：",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、報表匯出",
        "pages/4_儲位使用率.py",
    )
    _render_item(
        "🔎 揀貨差異：",
        "少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示",
        "pages/5_揀貨差異代庫存後五碼放大.py",
    )

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()

    st.divider()
    st.caption("提示：左側選單與本頁模組導覽皆可切換模組頁面；各頁設定互不影響。")


if __name__ == "__main__":
    main()

