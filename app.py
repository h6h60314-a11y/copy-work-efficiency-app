import streamlit as st
from pathlib import Path

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="進貨課效能平台",
    page_icon="🏭",
    layout="wide",
)

inject_logistics_theme()


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


def _page_param_from_filename(p: Path) -> str:
    """
    Streamlit 內建多頁：可用 ?page=pages/xxx.py 方式跳頁（同 app 內切換）
    """
    return f"pages/{p.name}"


def _link_text(label_bold: str, page_path: str | None) -> str:
    if page_path:
        # 使用相對連結（不寫死 domain）
        return f"**[{label_bold}](?page={page_path})**"
    return f"**{label_bold}**"


def main():
    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    pages = _list_pages()

    p_qc = _find_page(pages, ["驗收"])
    p_put = _find_page(pages, ["上架"])
    p_pick = _find_page(pages, ["總揀"])
    p_slot = _find_page(pages, ["儲位"])

    qc_path = _page_param_from_filename(p_qc) if p_qc else None
    put_path = _page_param_from_filename(p_put) if p_put else None
    pick_path = _page_param_from_filename(p_pick) if p_pick else None
    slot_path = _page_param_from_filename(p_slot) if p_slot else None

    card_open("📌 模組導覽")

    st.markdown(
        f"""
- ✅ {_link_text("驗收作業效能（KPI）", qc_path)}：人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間  
- 📦 {_link_text("上架產能分析（Putaway KPI）", put_path)}：上架產能、人時效率、班別（AM/PM）切分、報表匯出  
- 🎯 {_link_text("總揀達標", pick_path)}：分上午/下午達標、低空/高空門檻、排除非作業區間、匯出報表  
- 🧊 {_link_text("儲位使用率", slot_path)}：依區(溫層)分類統計、使用率>門檻紅色提示、分類可調整、報表匯出  
        """
    )

    card_close()

    # 找不到頁面時，列出 pages 方便你核對檔名
    if not all([qc_path, put_path, pick_path, slot_path]):
        st.divider()
        st.warning("有模組找不到對應頁面檔案（可能檔名不同）。目前 pages/ 檔案如下：")
        st.code("\n".join([p.name for p in pages]) if pages else "pages/ 資料夾不存在或沒有 .py")

    st.divider()
    st.caption("提示：左側選單也可切換各模組頁面；各頁面的設定互不影響。")


if __name__ == "__main__":
    main()
