import streamlit as st
from pathlib import Path

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="進貨課效能平台",
    page_icon="🏭",
    layout="wide",
)

inject_logistics_theme()

# ==================================================
# 讓「可點標題」看起來完全像純文字（不藍、不底線、不像按鈕）
# 並做出你截圖那種「• + 標題 + 說明」的條列排版
# ==================================================
st.markdown(
    """
<style>
/* 條列行容器：左 bullet + 右內容 */
._gt_li{
  display:flex;
  gap:12px;
  align-items:flex-start;
  margin: 10px 0 16px 0;
}
._gt_bullet{
  width: 14px;
  flex: 0 0 14px;
  font-size: 18px;
  line-height: 22px;
  color: rgba(15,23,42,0.85);
  padding-top: 1px;
}
._gt_body{
  flex: 1;
}

/* 把 Streamlit 的 button 變成純文字標題（完全不像按鈕） */
._gt_title button{
  all: unset;
  cursor: pointer;
  font-size: 16px;
  line-height: 22px;
  font-weight: 900;
  color: rgba(15,23,42,0.92);
}
._gt_title button:hover{
  opacity: 0.86;           /* 只做微亮，不要底色、不要底線 */
}

/* 說明文字：小一點、灰一點 */
._gt_desc{
  margin-top: 4px;
  font-size: 13px;
  line-height: 18px;
  font-weight: 600;
  color: rgba(15,23,42,0.68);
}

/* 去掉按鈕前後多餘空白（不同版本 Streamlit 可能會有） */
div[data-testid="stButton"]{
  margin: 0 !important;
  padding: 0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


def _list_pages():
    pages_dir = Path(__file__).parent / "pages"
    if not pages_dir.exists():
        return []
    return sorted(pages_dir.glob("*.py"))


def _find_page(pages, keywords):
    kws = [k for k in (keywords or []) if k]
    # 嚴格：全部命中
    for p in pages:
        if all(k in p.name for k in kws):
            return p
    # 放寬：任一命中
    for p in pages:
        if any(k in p.name for k in kws):
            return p
    return None


def _switch_to(p: Path | None):
    # ✅ 同視窗切換頁面（不會開新分頁/新視窗）
    if not p:
        st.warning("找不到對應頁面檔案（請確認 pages/ 檔名）")
        return
    st.switch_page(f"pages/{p.name}")


def _bullet_item(title_btn_text: str, desc: str, page: Path | None, key: str):
    """
    產生：• +（可點的純文字標題）+ 說明文字
    視覺 1:1 對齊你截圖的條列樣式
    """
    st.markdown('<div class="_gt_li">', unsafe_allow_html=True)
    st.markdown('<div class="_gt_bullet">•</div>', unsafe_allow_html=True)
    st.markdown('<div class="_gt_body">', unsafe_allow_html=True)

    st.markdown('<div class="_gt_title">', unsafe_allow_html=True)
    if st.button(title_btn_text, key=key):
        _switch_to(page)
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

    pages = _list_pages()

    # 依你的 pages 檔名（1~5）
    p_qc = _find_page(pages, ["1_", "驗收"])
    p_put = _find_page(pages, ["2_", "上架"])
    p_pick = _find_page(pages, ["3_", "總揀"])
    p_slot = _find_page(pages, ["4_", "儲位"])
    p_diff = _find_page(pages, ["5_", "揀貨"]) or _find_page(pages, ["揀貨", "差異"])

    card_open("📌 作業績效分析模組")

    _bullet_item(
        "✅ 驗收作業效能（KPI）",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        p_qc,
        key="nav_qc",
    )

    _bullet_item(
        "📦 上架作業效能（Putaway KPI）",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        p_put,
        key="nav_put",
    )

    _bullet_item(
        "🎯 總揀作業效能",
        "上午 / 下午達標分析、低空 / 高空門檻、排除非作業區間、匯出報表",
        p_pick,
        key="nav_pick",
    )

    _bullet_item(
        "🧊 儲位使用率分析",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、報表匯出",
        p_slot,
        key="nav_slot",
    )

    _bullet_item(
        "🔎 揀貨差異",
        "少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示",
        p_diff,
        key="nav_diff",
    )

    card_close()

    # 找不到頁面：顯示 pages 清單方便你核對（可保留）
    missing = [name for name, p in [
        ("驗收", p_qc),
        ("上架", p_put),
        ("總揀", p_pick),
        ("儲位", p_slot),
        ("揀貨差異", p_diff),
    ] if p is None]

    if missing:
        st.divider()
        st.warning(f"有模組找不到對應頁面檔案：{', '.join(missing)}")
        st.caption("目前 pages/ 檔案如下：")
        st.code("\n".join([p.name for p in pages]) if pages else "pages/ 資料夾不存在或沒有 .py")

    st.divider()
    st.caption("提示：左側選單與本頁模組導覽皆可切換模組頁面；各頁設定互不影響。")


if __name__ == "__main__":
    main()
