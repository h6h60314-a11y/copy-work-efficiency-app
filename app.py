import streamlit as st
from pathlib import Path

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="進貨課效能平台",
    page_icon="🏭",
    layout="wide",
)

inject_logistics_theme()

# ✅ 取消「連結」藍色與底線（我們改用按鈕，不用連結）
st.markdown(
    """
<style>
/* 讓導覽列看起來像功能項目，而不是超連結 */
._nav_item button {
    width: 100%;
    text-align: left;
    border-radius: 14px;
    border: 1px solid rgba(15, 23, 42, 0.10);
    background: rgba(255,255,255,0.85);
    padding: 10px 12px;
    font-weight: 800;
}
._nav_item button:hover {
    background: rgba(2,132,199,0.12);
    border: 1px solid rgba(2,132,199,0.30);
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
    """
    ✅ 同視窗切換頁面（不開新分頁）
    Streamlit 多頁切換：st.switch_page("pages/xxx.py")
    """
    if not p:
        st.warning("找不到對應頁面檔案（請確認 pages/ 檔名）")
        return
    st.switch_page(f"pages/{p.name}")


def main():
    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業 KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    pages = _list_pages()

    # ✅ 用關鍵字配對 pages 檔名（避免寫死）
    p_qc = _find_page(pages, ["驗收"])
    p_put = _find_page(pages, ["上架"])
    p_pick = _find_page(pages, ["總揀"])
    p_slot = _find_page(pages, ["儲位"])
    p_diff = _find_page(pages, ["揀貨", "差異"]) or _find_page(pages, ["揀貨差異"])  # 你的第5頁命名

    card_open("📌 作業績效分析模組")

    # ✅ 用「按鈕」取代 markdown link：點了同視窗切頁
    st.markdown('<div class="_nav_item">', unsafe_allow_html=True)
    if st.button("✅ 驗收作業效能（KPI）", use_container_width=True):
        _switch_to(p_qc)
    st.caption("人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間")

    if st.button("📦 上架作業效能（Putaway KPI）", use_container_width=True):
        _switch_to(p_put)
    st.caption("上架產能、人時效率、班別（AM/PM）切分、報表匯出")

    if st.button("🎯 總揀作業效能", use_container_width=True):
        _switch_to(p_pick)
    st.caption("上午/下午達標分析、低空/高空門檻、排除非作業區間、匯出報表")

    if st.button("🧊 儲位使用率分析", use_container_width=True):
        _switch_to(p_slot)
    st.caption("依區(溫層)分類統計、使用率門檻紅色提示、分類可調整、報表匯出")

    if st.button("🔎 揀貨差異分析（庫存定位強化）", use_container_width=True):
        _switch_to(p_diff)
    st.caption("少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示")
    st.markdown("</div>", unsafe_allow_html=True)

    card_close()

    # 偵錯：找不到頁面時列出 pages 清單
    missing = [name for name, p in [
        ("驗收", p_qc),
        ("上架", p_put),
        ("總揀", p_pick),
        ("儲位", p_slot),
        ("揀貨差異", p_diff),
    ] if p is None]

    if missing:
        st.divider()
        st.warning(f"以下模組找不到對應頁面檔案：{', '.join(missing)}")
        st.caption("目前 pages/ 檔案如下：")
        st.code("\n".join([p.name for p in pages]) if pages else "pages/ 資料夾不存在或沒有 .py")

    st.divider()
    st.caption("提示：可由左側選單或本頁模組按鈕切換模組；各頁設定互不影響。")


if __name__ == "__main__":
    main()
