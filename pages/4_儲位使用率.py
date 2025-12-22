# pages/4_儲位分類統計.py
from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from common_ui import (
    inject_logistics_theme,
    set_page,
    card_open,
    card_close,
    KPI,
    render_kpis,
)

# ========= 預設分類（可在 sidebar 調整） =========
DEFAULT_CATEGORIES = {
    "輕型料架": ["001", "002", "003", "017", "016"],
    "落地儲": ["014", "018", "019", "020", "010", "081", "401", "402", "403","015"],
    "重型低空": ["011", "012", "013", "031", "032", "033", "034", "035", "036", "037", "038"],
    "高空儲": [
        "021", "022", "023",
        "041", "042", "043",
        "051", "052", "053", "054", "055", "056", "057",
        "301", "302", "303", "304", "305", "306",
    ],
}

DEFAULT_COL_ZONE = "區(溫層)"
DEFAULT_COL_VALID = "有效貨位"
DEFAULT_COL_USED = "已使用貨位"


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0)


def _inject_responsive_grid_css():
    """
    ✅ 依螢幕寬度自動切欄數：CSS Grid auto-fit + minmax
    """
    st.markdown(
        """
<style>
.gt-card-grid{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  align-items: stretch;
}
.gt-card-grid .gt-slot{
  min-width: 0;
}
</style>
""",
        unsafe_allow_html=True,
    )


def sidebar_category_editor() -> dict:
    if "categories" not in st.session_state:
        st.session_state.categories = {k: v[:] for k, v in DEFAULT_CATEGORIES.items()}

    st.sidebar.divider()
    st.sidebar.header("🧩 分類定義（可調整）")
    st.sidebar.caption("以逗號分隔，例如：001,002,003（會自動去空白）")

    for cat in list(st.session_state.categories.keys()):
        zones = st.session_state.categories.get(cat, [])
        text = st.sidebar.text_area(
            label=cat,
            value=",".join([str(z).strip() for z in zones]),
            height=70,
            key=f"cat_{cat}",
        )
        st.session_state.categories[cat] = [z.strip() for z in (text or "").split(",") if z.strip()]

    c1, c2 = st.sidebar.columns(2)
    with c1:
        if st.sidebar.button("↩️ 還原預設分類"):
            st.session_state.categories = {k: v[:] for k, v in DEFAULT_CATEGORIES.items()}
            st.rerun()
    with c2:
        if st.sidebar.button("➕ 新增類別"):
            new_name = f"新類別{len(st.session_state.categories) + 1}"
            st.session_state.categories[new_name] = []
            st.rerun()

    st.sidebar.caption("勾選後可刪除類別（請小心）")
    del_cat = st.sidebar.selectbox(
        "選擇要刪除的類別",
        options=["（不刪除）"] + list(st.session_state.categories.keys()),
        key="del_cat_select",
    )
    if del_cat != "（不刪除）":
        if st.sidebar.checkbox(f"確認刪除：{del_cat}", value=False, key="confirm_del_cat"):
            if st.sidebar.button("🗑️ 刪除類別", key="btn_del_cat"):
                st.session_state.categories.pop(del_cat, None)
                st.rerun()

    return st.session_state.categories


def compute(df: pd.DataFrame, col_zone: str, col_valid: str, col_used: str, categories: dict):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    df[col_zone] = df[col_zone].astype(str).str.strip()
    df[col_valid] = _to_num(df[col_valid])
    df[col_used] = _to_num(df[col_used])

    rows = []
    for name, zones in (categories or {}).items():
        zones_str = [str(z).strip() for z in (zones or []) if str(z).strip() != ""]
        data = df[df[col_zone].isin(zones_str)] if zones_str else df.iloc[0:0]

        total_valid = float(data[col_valid].sum())
        total_used = float(data[col_used].sum())
        unused = max(total_valid - total_used, 0.0)
        usage_rate = (total_used / total_valid * 100.0) if total_valid > 0 else 0.0

        rows.append(
            {
                "類別": name,
                "有效貨位": int(round(total_valid)),
                "已使用貨位": int(round(total_used)),
                "未使用貨位": int(round(unused)),
                "使用率(%)": round(usage_rate, 2),
            }
        )

    all_defined = []
    for zlist in (categories or {}).values():
        all_defined.extend([str(z).strip() for z in (zlist or []) if str(z).strip() != ""])
    all_defined = list(dict.fromkeys(all_defined))

    others = sorted(
        df.loc[~df[col_zone].isin(all_defined), col_zone]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    res_df = pd.DataFrame(rows)
    return res_df, others


def _chart_usage_rate(res_df: pd.DataFrame, threshold: float):
    """
    ✅ 使用率 > threshold → bar 變紅（壓力過高）
    """
    if res_df is None or res_df.empty:
        st.info("無資料可視覺化")
        return

    threshold = float(threshold)

    try:
        import altair as alt  # type: ignore

        data = res_df.copy()
        data["超過門檻"] = data["使用率(%)"].astype(float) > threshold

        base = (
            alt.Chart(data)
            .mark_bar()
            .encode(
                x=alt.X("使用率(%):Q", title="使用率(%)"),
                y=alt.Y("類別:N", sort="-x", title=""),
                color=alt.condition(
                    alt.datum["超過門檻"] == True,
                    alt.value("red"),
                    alt.value("steelblue"),
                ),
                tooltip=["類別", "有效貨位", "已使用貨位", "未使用貨位", "使用率(%)"],
            )
            .properties(height=220)
        )

        rule = alt.Chart(pd.DataFrame({"target": [threshold]})).mark_rule(strokeDash=[6, 4]).encode(
            x="target:Q"
        )

        st.altair_chart(alt.layer(base, rule), use_container_width=True)

    except Exception:
        st.bar_chart(res_df.set_index("類別")["使用率(%)"])
        st.caption(f"⚠️ 無法套用條件著色（門檻：{threshold:.0f}%）")


def _chart_unused(res_df: pd.DataFrame):
    if res_df is None or res_df.empty:
        st.info("無資料可視覺化")
        return

    try:
        import altair as alt  # type: ignore

        chart = (
            alt.Chart(res_df)
            .mark_bar()
            .encode(
                x=alt.X("未使用貨位:Q", title="未使用貨位"),
                y=alt.Y("類別:N", sort="-x", title=""),
                tooltip=["類別", "未使用貨位"],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.bar_chart(res_df.set_index("類別")["未使用貨位"])


def _category_card_html(item: dict, warn_threshold: float) -> str:
    """
    ✅ 卡片 KPI：直向一項一列（符合你示意）
    ✅ 使用率 > warn_threshold → 紅卡（壓力過高）
    """
    cat = str(item.get("類別", ""))
    valid = int(item.get("有效貨位", 0))
    used = int(item.get("已使用貨位", 0))
    rate = float(item.get("使用率(%)", 0.0))

    # 🔴 使用率 > 門檻 → 紅卡
    is_bad = rate > float(warn_threshold)

    bg = "rgba(255,199,206,0.85)" if is_bad else "rgba(198,239,206,0.70)"
    bd = "rgba(156,0,6,0.45)" if is_bad else "rgba(0,97,0,0.30)"
    fg = "rgba(156,0,6,1.0)" if is_bad else "rgba(0,97,0,1.0)"

    return f"""
<div style="
  width:100%;
  border: 1px solid {bd};
  background: {bg};
  border-radius: 18px;
  padding: 16px 18px;
  box-shadow: 0 10px 24px rgba(15,23,42,0.06);
">
  <div style="font-weight:900; font-size:18px; margin-bottom:16px; color:{fg};">
    {cat}
  </div>

  <div style="margin-bottom:14px;">
    <div style="opacity:0.70; font-weight:700;">有效貨位</div>
    <div style="font-size:22px; font-weight:900;">{valid:,}</div>
  </div>

  <div style="margin-bottom:14px;">
    <div style="opacity:0.70; font-weight:700;">已使用貨位</div>
    <div style="font-size:22px; font-weight:900;">{used:,}</div>
  </div>

  <div>
    <div style="opacity:0.70; font-weight:700;">使用率</div>
    <div style="font-size:22px; font-weight:900;">{rate:.2f}%</div>
  </div>
</div>
"""


def main():
    st.set_page_config(page_title="儲位分類統計", page_icon="📦", layout="wide")
    inject_logistics_theme()
    _inject_responsive_grid_css()

    set_page("儲位分類統計", icon="📦", subtitle="KPI + 圖表｜卡片橫向自動切欄｜使用率>門檻紅色")

    # ======================
    # 上傳
    # ======================
    card_open("📤 上傳 Excel（儲位明細）")
    uploaded = st.file_uploader(
        "請上傳儲位明細 Excel",
        type=["xlsx", "xls", "xlsm"],
        label_visibility="collapsed",
    )
    card_close()

    if not uploaded:
        st.info("請先上傳儲位明細 Excel")
        return

    try:
        df = pd.read_excel(io.BytesIO(uploaded.getvalue()))
    except Exception as e:
        st.error("❌ 檔案讀取失敗")
        st.code(str(e))
        return

    df.columns = df.columns.astype(str).str.strip()

    # ======================
    # Sidebar：常駐顯示（不使用 expander）
    # ======================
    with st.sidebar:
        st.header("⚙️ 欄位設定")
        col_zone = st.text_input("區(溫層) 欄位", value=DEFAULT_COL_ZONE)
        col_valid = st.text_input("有效貨位 欄位", value=DEFAULT_COL_VALID)
        col_used = st.text_input("已使用貨位 欄位", value=DEFAULT_COL_USED)

        st.divider()
        st.header("🎯 圖表門檻（同目標線）")
        _ = st.checkbox("顯示使用率目標線", value=False)  # UI 常駐保留
        chart_threshold = st.number_input(
            "使用率門檻（%）",
            min_value=0.0,
            max_value=100.0,
            value=90.0,
            step=1.0,
        )
        st.caption("圖表：使用率 > 門檻 → 紅色 bar")

        st.divider()
        st.header("🔴 卡片紅卡門檻")
        warn_threshold = st.number_input(
            "紅卡門檻（使用率 %）",
            min_value=0.0,
            max_value=100.0,
            value=90.0,
            step=1.0,
        )
        st.caption("卡片：使用率 > 紅卡門檻 → 整塊紅底（壓力過高）")

    # 分類可調（Sidebar 下方常駐）
    categories = sidebar_category_editor()

    # 欄位檢查
    missing = [c for c in [col_zone, col_valid, col_used] if c not in df.columns]
    if missing:
        st.error("❌ 找不到欄位")
        st.write("缺少欄位：", missing)
        st.write("目前欄位：", list(df.columns))
        return

    # ======================
    # 計算
    # ======================
    res_df, others = compute(df, col_zone, col_valid, col_used, categories)

    # ======================
    # KPI 總覽
    # ======================
    total_valid = int(res_df["有效貨位"].sum()) if not res_df.empty else 0
    total_used = int(res_df["已使用貨位"].sum()) if not res_df.empty else 0
    total_rate = (total_used / total_valid * 100.0) if total_valid > 0 else 0.0

    card_open("📌 總覽 KPI")
    render_kpis(
        [
            KPI("有效貨位", f"{total_valid:,}"),
            KPI("已使用貨位", f"{total_used:,}"),
            KPI("總使用率", f"{total_rate:.2f}%"),
            KPI("未分類區(溫層)數", f"{len(others):,}"),
        ],
        cols=4,
    )
    card_close()

    # ======================
    # 🧾 圖格總覽（橫向 + 自動切欄）
    # ======================
    card_open("🧾 依格式顯示（圖格總覽｜使用率>門檻紅卡）")

    items = res_df.to_dict("records")
    cards_html = "\n".join(
        [f'<div class="gt-slot">{_category_card_html(it, float(warn_threshold))}</div>' for it in items]
    )
    st.markdown(f'<div class="gt-card-grid">{cards_html}</div>', unsafe_allow_html=True)

    card_close()

    # ======================
    # KPI 圖表（不含「有效 vs 已使用」）
    # ======================
    card_open("📊 各類別使用率(%)（>門檻紅色）")
    _chart_usage_rate(res_df, threshold=float(chart_threshold))
    card_close()

    # ======================
    # 未分類清單
    # ======================
    card_open("🔍 未納入分類的 區(溫層)")
    if others:
        st.write(others)
    else:
        st.success("全部已納入分類")
    card_close()

    # ======================
    # 匯出 Excel（含分類定義）
    # ======================
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        res_df.to_excel(writer, index=False, sheet_name="儲位分類統計")
        pd.DataFrame({"未分類區(溫層)": others}).to_excel(writer, index=False, sheet_name="未分類清單")

        cat_rows = []
        for k, v in (categories or {}).items():
            cat_rows.append({"類別": k, "區碼清單": ",".join([str(x) for x in (v or [])])})
        pd.DataFrame(cat_rows).to_excel(writer, index=False, sheet_name="分類定義")

    st.download_button(
        "⬇️ 匯出統計結果（Excel）",
        data=out.getvalue(),
        file_name="儲位分類統計.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
