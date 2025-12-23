import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="進貨課效能平台｜首頁",
    page_icon="🏠",
    layout="wide",
)

inject_logistics_theme()

# 條列樣式（• + 標題 + 說明、不藍不底線）
st.markdown(
    """
<style>
._gt_list{ margin-top: 6px; }
._gt_item{
  display:flex; gap: 14px; align-items:flex-start;
  margin: 12px 0 18px 0;
}
._gt_bullet{
  width: 10px; flex: 0 0 10px; padding-top: 2px;
  color: rgba(15,23,42,0.85); font-size: 18px; line-height: 18px;
}
._gt_body{ flex: 1; }
._gt_title{
  font-weight: 900; font-size: 16px; line-height: 22px;
  color: rgba(15,23,42,0.92); margin: 0;
}
._gt_desc{
  margin-top: 4px; font-weight: 600; font-size: 13px; line-height: 18px;
  color: rgba(15,23,42,0.68);
}
._gt_click{
  cursor: pointer; text-decoration: none !important; color: inherit !important;
}
._gt_click:hover{ opacity: 0.86; text-decoration: none !important; }
</style>
""",
    unsafe_allow_html=True,
)

def _render_item(title: str, desc: str, page_path: str):
    # ✅ 同視窗切頁：用 st.switch_page（不開新分頁）
    # 這裡用「看起來像文字的按鈕」最穩，不會有你先前那種藍色外框
    # 做法：用 st.button + CSS 變成文字（這支頁面不會再被 bullet 拆版）
    st.markdown('<div class="_gt_item">', unsafe_allow_html=True)
    st.markdown('<div class="_gt_bullet">•</div>', unsafe_allow_html=True)
    st.markdown('<div class="_gt_body">', unsafe_allow_html=True)

    # 讓按鈕看起來像純文字（只作用在本頁）
    st.markdown(
        """
<style>
div[data-testid="stButton"]{ margin:0; padding:0; }
._text_btn button{
  all: unset;
  cursor: pointer;
  font-weight: 900;
  font-size: 16px;
  line-height: 22px;
  color: rgba(15,23,42,0.92);
}
._text_btn button:hover{ opacity: 0.86; }
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="_gt_title _text_btn">', unsafe_allow_html=True)
    if st.button(title, key=f"goto_{page_path}"):
        st.switch_page(page_path)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="_gt_desc">{desc}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def main():
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
