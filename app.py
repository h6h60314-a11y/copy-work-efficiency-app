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
    base = Path(__file__).parent
    pages_dir = base / "pages"
    if not pages_dir.exists():
        return []
    return sorted(pages_dir.glob("*.py"))


def _find_page_path(pages, keywords):
    """
    在 pages/*.py 中，用關鍵字找最符合的檔案（避免寫死檔名造成 page_link 找不到）
    keywords: list[str]
    """
    kws = [k for k in (keywords or []) if k]
    for p in pages:
        name = p.name
        if all(k in name for k in kws):
            return str(Path("pages") / p.name)
    # 放寬：只要命中任一關鍵字就算
    for p in pages:
        name = p.name
        if any(k in name for k in kws):
            return str(Path("pages") / p.name)
    return None


def _page_link_safe(path, label, icon, desc):
    if path:
        st.page_link(path, label=label, icon=icon, help=desc)
    else:
        st.write(f"{icon} **{label}**（找不到對應頁面檔案）")
        st.caption("⚠️ 請確認 pages/ 內檔名是否包含此模組關鍵字。")


def main():
    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    pages = _list_pages()

    # 依你側邊欄的實際名稱，用關鍵字去配對檔案（避免檔名差一個字就壞）
    p_qc = _find_page_path(pages, ["驗收"])          # 例如：1_驗收達標效率.py
    p_putaway = _find_page_path(pages, ["上架"])     # 例如：2_總上組上架產能.py
    p_pick = _find_page_path(pages, ["總揀"])        # 例如：3_總揀達標.py
    p_slot = _find_page_path(pages, ["儲位"])        # 例如：4_儲位分類統計.py 或 4_儲位使用率.py

    card_open("📌 模組導覽（點一下跳頁）")

    _page_link_safe(
        p_qc,
        label="驗收達標效率",
        icon="✅",
        desc="人時效率、達標率、班別（AM/PM）切分、排除非作業區間",
    )
    st.caption("人時效率、達標率、班別（AM/PM）切分、支援/離站等非作業區間排除")
    st.markdown("---")

    _page_link_safe(
        p_putaway,
        label="總上組上架產能",
        icon="📦",
        desc="上架產能、人時效率、班別（AM/PM）切分、報表匯出",
    )
    st.caption("上架產能、人時效率、班別（AM/PM）切分、報表匯出")
    st.markdown("---")

    _page_link_safe(
        p_pick,
        label="總揀達標",
        icon="🎯",
        desc="分上午/下午達標、低空/高空門檻、排除非作業區間、匯出報表",
    )
    st.caption("分上午/下午達標、低空/高空門檻、排除非作業區間、匯出報表")
    st.markdown("---")

    _page_link_safe(
        p_slot,
        label="儲位使用率",
        icon="🧊",
        desc="依區(溫層)分類統計、使用率>門檻紅色提示、分類可調整、報表匯出",
    )
    st.caption("依區(溫層)分類統計、使用率>門檻紅色提示、分類可調整、報表匯出")

    card_close()

    # 若找不到頁面，顯示目前 pages 清單方便你核對檔名
    if not all([p_qc, p_putaway, p_pick, p_slot]):
        st.divider()
        st.warning("有模組找不到對應頁面檔案（可能是檔名不同）。目前 pages/ 內檔案如下：")
        st.code("\n".join([p.name for p in pages]) if pages else "pages/ 資料夾不存在或沒有 .py")

    st.divider()
    st.caption("提示：左側選單與本頁模組導覽皆可切換模組頁面；各頁設定互不影響。")


if __name__ == "__main__":
    main()
