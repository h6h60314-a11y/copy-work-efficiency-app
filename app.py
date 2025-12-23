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
# 讓「按鈕」看起來像純文字（維持你截圖那種條列式）
# ==================================================
st.markdown(
    """
<style>
/* 一整列條列項目 */
._nav_row{
  display:flex;
  gap:10px;
  align-items:flex-start;
  margin: 6px 0 14px 0;
}
._nav_bullet{
  width: 20px;
  flex: 0 0 20px;
  font-size: 14px;
  line-height: 22px;
}
/* 右側內容：標題＋說明 */
._nav_body{ flex: 1; }

/* 把 streamlit button 變成「文字」 */
._nav_btn button{
  all: unset;
  cursor: pointer;
  font-weight: 900;
  font-size: 16px;
  line-height: 22px;
  color: rgba(15, 23, 42, 0.92);
}
._nav_btn button:hover{
  opacity: .85;
}

/* 說明文字 */
._nav_desc{
  margin-top: 4px;
  opacity: .75;
  font-weight: 600;
  font-size: 13px;
  line-height: 18px;
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
    # ✅ 同視窗切頁（不會開新分頁/新視窗）
    if not p:
        st.warning("找不到對應頁面檔案（請確認 pages/ 檔名）")
        return
    st.switch_page(f"pages/{p.name}")


def _nav_item(bullet: str, title: str, desc: str, page: Path | None, key: str):
    """
    條列式外觀（跟你截圖一樣），但標題可點（同視窗切頁）
    """
    st.markdown('<div class="_nav_row">', unsafe_allow_html=True)
    st.markdown(f'<div class="_nav_bullet">{bullet}</div>', unsafe_allow_html=True)

    st.markdown('<div class="_nav_body">', unsafe_allow_html=True)
    # 標題：看起來像文字的按鈕
    st.markdown('<div class="_nav_btn">', unsafe_allow_html=True)
    if st.button(title, key=key):
        _switch_to(page)
    st.markdown("</div>", unsafe_allow_html=True)

    # 說明：純文字
    st.markdown(f'<div class="_nav_desc">{desc}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def main():
    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業 KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    pages = _list_pages()

    # 依你實際 pages 檔名（你截圖那 5 支）
    p_qc = _find_page(pages, ["1_", "驗收"])
    p_put = _find_page(pages, ["2_", "上架"])
    p_pick = _find_page(pages, ["3_", "總揀"])
    p_slot = _find_page(pages, ["4_", "儲位"])
    p_diff = _find_page(pages, ["5_", "揀貨"]) or _find_page(pages, ["揀貨", "差異"])

    card_open("📌 作業績效分析模組")

    _nav_item(
        "✅",
        "驗收作業效能（KPI）",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        p_qc,
        key="nav_qc",
    )

    _nav_item(
        "📦",
        "上架作業效能（Putaway KPI）",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        p_put,
        key="nav_put",
    )

    _nav_item(
        "🎯",
        "總揀作業效能",
        "上午 / 下午達標分析、低空 / 高空門檻、排除非作業區間、匯出報表",
        p_pick,
        key="nav_pick",
    )

    _nav_item(
        "🧊",
        "儲位使用率分析",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、報表匯出",
        p_slot,
        key="nav_slot",
    )

    _nav_item(
        "🔎",
        "揀貨差異",
        "少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示",
        p_diff,
        key="nav_diff",
    )

    card_close()

    # 若有頁面找不到：顯示清單方便你核對（可保留，也可刪）
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
    st.caption("提示：左側選單與本頁模組導覽皆可切換模組；各頁設定互不影響。")


if __name__ == "__main__":
    main()
