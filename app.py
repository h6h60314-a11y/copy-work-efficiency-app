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
# 工具：掃 pages
# ==================================================
def _list_pages():
    pages_dir = Path(__file__).parent / "pages"
    if not pages_dir.exists():
        return []
    return sorted(pages_dir.glob("*.py"))


def _find_page(pages, keywords):
    kws = [k for k in (keywords or []) if k]
    for p in pages:
        if all(k in p.name for k in kws):
            return p
    for p in pages:
        if any(k in p.name for k in kws):
            return p
    return None


def _page_path(p: Path | None) -> str | None:
    if not p:
        return None
    return f"pages/{p.name}"


# ==================================================
# 1) 先處理「點擊後的切頁」（同視窗）
# ==================================================
qp = st.query_params
goto = qp.get("goto", None)
if goto:
    # 用完就清掉，避免每次 rerun 都跳
    st.query_params.clear()
    # 同視窗切頁
    st.switch_page(goto)


# ==================================================
# 2) 注入 1:1 條列樣式 + clickable title（不是按鈕）
# ==================================================
st.markdown(
    """
<style>
/* 讓導覽列看起來跟你原本那張一樣：bullet + 標題 + 說明 */
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
    """
    用 HTML 完整控制排版（才會跟你原本那張一模一樣）
    """
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
    set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業 KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    pages = _list_pages()

    p_qc = _find_page(pages, ["1_", "驗收"])
    p_put = _find_page(pages, ["2_", "上架"])
    p_pick = _find_page(pages, ["3_", "總揀"])
    p_slot = _find_page(pages, ["4_", "儲位"])
    p_diff = _find_page(pages, ["5_", "揀貨"]) or _find_page(pages, ["揀貨", "差異"])

    qc_path = _page_path(p_qc)
    put_path = _page_path(p_put)
    pick_path = _page_path(p_pick)
    slot_path = _page_path(p_slot)
    diff_path = _page_path(p_diff)

    card_open("📌 作業績效分析模組")

    st.markdown('<div class="_gt_list">', unsafe_allow_html=True)

    _render_item(
        "✅ 驗收作業效能（KPI）：",
        "人時效率、達標率、班別（AM/PM）切分、支援排除非作業區間",
        qc_path,
    )
    _render_item(
        "📦 上架作業效能（Putaway KPI）：",
        "上架產能、人時效率、班別（AM/PM）切分、報表匯出",
        put_path,
    )
    _render_item(
        "🎯 總揀作業效能：",
        "上午 / 下午達標分析、低空 / 高空門檻、排除非作業區間、匯出報表",
        pick_path,
    )
    _render_item(
        "🧊 儲位使用率分析：",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、報表匯出",
        slot_path,
    )
    _render_item(
        "🔎 揀貨差異：",
        "少揀差異展開、庫存儲位與棚別對應、國際條碼後五碼放大顯示",
        diff_path,
    )

    st.markdown("</div>", unsafe_allow_html=True)
    card_close()

    # 找不到頁面時提示
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
