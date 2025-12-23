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
# 取消連結藍色與底線（保留可點跳頁）
# ==================================================
st.markdown(
    """
<style>
/* 取消主畫面中的連結藍色與底線，改成跟文字一樣 */
.stMarkdown a {
    color: inherit !important;
    text-decoration: none !important;
    font-weight: 800;
}

/* hover 時微亮即可 */
.stMarkdown a:hover {
    text-decoration: none !important;
    opacity: 0.85;
}
</style>
""",
    unsafe_allow_html=True,
)


# ==================================================
# Pages 掃描與配對
# ==================================================
def _list_pages():
    pages_dir = Path(__file__).parent / "pages"
    if not pages_dir.exists():
        return []
    return sorted(pages_dir.glob("*.py"))


def _find_page(pages, keywords):
    kws = [k for k in (keywords or []) if k]

    # 先嚴格：全部命中
    for p in pages:
        if all(k in p.name for k in kws):
            return p

    # 再放寬：任一命中
    for p in pages:
        if any(k in p.name for k in kws):
            return p

    return None


def _page_param_from_filename(p: Path) -> str:
    # Streamlit 多頁：用 query param 切換頁面
    return f"pages/{p.name}"


def _link_text(label_bold: str, page_path: str | None) -> str:
    # 只讓標題可點；若找不到頁面則顯示純文字
    if page_path:
        return f"**[{label_bold}](?page={page_path})**"
    return f"**{label_bold}**"


# ==================================================
# Main
# ==================================================
def main():
    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業 KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    pages = _list_pages()

    # 依實際檔名關鍵字配對（避免寫死）
    p_qc = _find_page(pages, ["驗收"])
    p_put = _find_page(pages, ["上架"])
    p_pick = _find_page(pages, ["總揀"])
    p_slot = _find_page(pages, ["儲位"])
    p_diff = _find_page(pages, ["揀貨", "差異"])

    qc_path = _page_param_from_filename(p_qc) if p_qc else None
    put_path = _page_param_from_filename(p_put) if p_put else None
    pick_path = _page_param_from_filename(p_pick) if p_pick else None
    slot_path = _page_param_from_filename(p_slot) if p_slot else None
    diff_path = _page_param_from_filename(p_diff) if p_diff else None

    # ==================================================
    # 作業績效分析模組（首頁導覽）
    # ==================================================
    card_open("📌 作業績效分析模組")

    st.markdown(
        f"""
- ✅ {_link_text("驗收作業效能（KPI）", qc_path)}：  
  人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間  

- 📦 {_link_text("上架作業效能（Putaway KPI）", put_path)}：  
  上架產能、人時效率、班別（AM/PM）切分、報表匯出  

- 🎯 {_link_text("總揀作業效能", pick_path)}：  
  上午 / 下午達標分析、低空 / 高空門檻、排除非作業區間、匯出報表  

- 🧊 {_link_text("儲位使用率分析", slot_path)}：  
  依區(溫層)分類統計、使用率門檻紅色提示、分類可調整、報表匯出  

- 🔎 {_link_text("揀貨差異", diff_path)}：  
  少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示  
        """
    )

    card_close()

    # ==================================================
    # 偵錯輔助：找不到頁面時顯示 pages 清單
    # ==================================================
    if not all([qc_path, put_path, pick_path, slot_path, diff_path]):
        st.divider()
        st.warning("有模組找不到對應頁面檔案（可能檔名不同）。目前 pages/ 內檔案如下：")
        st.code("\n".join([p.name for p in pages]) if pages else "pages/ 資料夾不存在或沒有 .py")

    st.divider()
    st.caption("提示：左側選單與本頁模組導覽皆可切換各模組頁面；各頁設定互不影響。")


if __name__ == "__main__":
    main()

