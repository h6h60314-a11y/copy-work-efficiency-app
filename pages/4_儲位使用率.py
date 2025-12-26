# pages/4_儲位使用率.py
from __future__ import annotations

import io
import os
import re
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

# =========================================================
# ✅ A) 依「區(溫層)」分類（保留你原本功能）
# =========================================================
DEFAULT_CATEGORIES = {
    "輕型料架": ["001", "002", "003", "017", "016"],
    "落地儲": ["014", "018", "019", "020", "010", "081", "401", "402", "403", "015"],
    "重型低空": ["011", "012", "013", "031", "032", "033", "034", "035", "036", "037", "038"],
    "高空儲": [
        "021", "022", "023",
        "041", "042", "043",
        "051", "052", "053", "054", "055", "056", "057",
        "301", "302", "303", "304", "305", "306",
        "311", "312", "313", "314",
        "061",
    ],
}

DEFAULT_COL_ZONE = "區(溫層)"
DEFAULT_COL_VALID = "有效貨位"
DEFAULT_COL_USED = "已使用貨位"


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0)


def _inject_responsive_grid_css():
    """卡片自動排版：依螢幕寬度自動切欄數"""
    st.markdown(
        """
<style>
.gt-card-grid{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  align-items: stretch;
}
.gt-card-grid .gt-slot{ min-width: 0; }
</style>
""",
        unsafe_allow_html=True,
    )


def sidebar_category_editor() -> dict:
    """Sidebar：可手動調整分類定義（逗號分隔）"""
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


def compute_by_zone_categories(
    df: pd.DataFrame, col_zone: str, col_valid: str, col_used: str, categories: dict
):
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


def _chart_usage_rate(res_df: pd.DataFrame, threshold: float, show_target_line: bool):
    """使用率圖：>threshold 紅色"""
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

        layers = [base]
        if show_target_line:
            rule = alt.Chart(pd.DataFrame({"target": [threshold]})).mark_rule(strokeDash=[6, 4]).encode(
                x="target:Q"
            )
            layers.append(rule)

        st.altair_chart(alt.layer(*layers), use_container_width=True)

    except Exception:
        st.bar_chart(res_df.set_index("類別")["使用率(%)"])
        if show_target_line:
            st.caption(f"目標線：{threshold:.0f}%（此模式下無法畫虛線）")


def _category_card_html(item: dict, warn_threshold: float) -> str:
    """卡片 KPI：直向一項一列；>門檻紅卡"""
    cat = str(item.get("類別", ""))
    valid = int(item.get("有效貨位", 0))
    used = int(item.get("已使用貨位", 0))
    unused = int(item.get("未使用貨位", 0))
    rate = float(item.get("使用率(%)", 0.0))

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

  <div style="margin-bottom:14px;">
    <div style="opacity:0.70; font-weight:700;">未使用貨位</div>
    <div style="font-size:22px; font-weight:900;">{unused:,}</div>
  </div>

  <div>
    <div style="opacity:0.70; font-weight:700;">使用率</div>
    <div style="font-size:22px; font-weight:900;">{rate:.2f}%</div>
  </div>
</div>
"""


# =========================================================
# ✅ B) 依「棚別」分類（同步部署你的 Tkinter 邏輯）
# =========================================================
大型儲位 = [
    '010','018','019','020','021','022','023','041',
    '042','043','051','052','053','054','055','056',
    '057','301','302','303','304','305','306','311',
    '312','313','314','081','401','402','061','014',
    '057','058','059','015'
]
中型儲位 = ['011','012','013','031','032','033','034','035','036','037','038']
小型儲位 = ['001','002','003','017','016']

LARGE = set(大型儲位)
MID   = set(中型儲位)
SMALL = set(小型儲位)


def _to_zone3(x) -> str:
    """從『棚別』抓出 3 碼區碼（例如：010 / 011 / 001）"""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    m = re.search(r"\d{3}", s)
    if m:
        return m.group(0)
    s = re.sub(r"\D", "", s)
    return s.zfill(3) if s else ""


def classify_zone_from棚別(x) -> str:
    """回傳：大型儲位/中型儲位/小型儲位/未知"""
    z = _to_zone3(x)
    if not z:
        return "未知"
    if z in LARGE:
        return "大型儲位"
    if z in MID:
        return "中型儲位"
    if z in SMALL:
        return "小型儲位"
    return "未知"


def robust_read_any_sheet_bytes(uploaded) -> tuple[pd.DataFrame, str]:
    """
    ✅ 支援：xlsx / xls / xlsm / xlsb / csv
    ✅ 自動找分頁：先找「區(溫層)」→ 再找「棚別」→ 最後第一張
    """
    filename = uploaded.name
    ext = os.path.splitext(filename)[1].lower()
    data = uploaded.getvalue()

    if ext == ".csv":
        df = pd.read_csv(io.BytesIO(data), encoding="utf-8-sig")
        return df, "CSV"

    if ext == ".xlsb":
        xls = pd.ExcelFile(io.BytesIO(data), engine="pyxlsb")
        sheet = None
        for key in [DEFAULT_COL_ZONE, "棚別"]:
            for name in xls.sheet_names:
                try:
                    probe = pd.read_excel(xls, sheet_name=name, engine="pyxlsb", nrows=50)
                    if key in probe.columns:
                        sheet = name
                        break
                except Exception:
                    continue
            if sheet:
                break
        if sheet is None:
            sheet = xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet, engine="pyxlsb")
        return df, sheet

    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        engine = "openpyxl"
    elif ext == ".xls":
        engine = "xlrd"
    else:
        raise ValueError(f"不支援的檔案格式：{ext}")

    xls = pd.ExcelFile(io.BytesIO(data), engine=engine)

    sheet = None
    for key in [DEFAULT_COL_ZONE, "棚別"]:
        for name in xls.sheet_names:
            try:
                cols = pd.read_excel(xls, sheet_name=name, nrows=0).columns
                if key in cols:
                    sheet = name
                    break
            except Exception:
                continue
        if sheet:
            break

    if sheet is None:
        sheet = xls.sheet_names[0]

    df = pd.read_excel(xls, sheet_name=sheet)
    return df, sheet


def build_shelf_output_excel_bytes(
    base_name: str,
    df_detail: pd.DataFrame,
    df_shelf: pd.DataFrame,
    df_type: pd.DataFrame,
    df_unknown: pd.DataFrame,
):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df_detail.to_excel(writer, sheet_name="明細(含分類)", index=False)
        df_shelf.to_excel(writer, sheet_name="棚別統計", index=False)
        df_type.to_excel(writer, sheet_name="儲位類型統計", index=False)
        df_unknown.to_excel(writer, sheet_name="未知明細", index=False)
    out.seek(0)
    return f"{base_name}_棚別統計.xlsx", out.getvalue()


# =========================================================
# MAIN
# =========================================================
def main():
    st.set_page_config(page_title="儲位使用率", page_icon="🧊", layout="wide")
    inject_logistics_theme()
    _inject_responsive_grid_css()

    set_page("儲位使用率", icon="🧊", subtitle="區(溫層)分類 + 棚別分類（含未知明細）｜支援 xlsb")

    # Sidebar（永遠顯示）
    with st.sidebar:
        st.header("⚙️ 欄位設定（區(溫層)分類）")
        col_zone = st.text_input("區(溫層) 欄位", value=DEFAULT_COL_ZONE, key="col_zone")
        col_valid = st.text_input("有效貨位 欄位", value=DEFAULT_COL_VALID, key="col_valid")
        col_used = st.text_input("已使用貨位 欄位", value=DEFAULT_COL_USED, key="col_used")

        st.divider()
        st.header("🎯 圖表門檻（同目標線）")
        show_target_line = st.checkbox("顯示使用率目標線", value=True, key="show_usage_target_line")
        chart_threshold = st.number_input(
            "使用率門檻（%）", min_value=0.0, max_value=100.0, value=90.0, step=1.0, key="chart_threshold"
        )
        st.caption("圖表：使用率 > 門檻 → 紅色")

        st.divider()
        st.header("🔴 卡片紅卡門檻")
        warn_threshold = st.number_input(
            "紅卡門檻（使用率 %）", min_value=0.0, max_value=100.0, value=90.0, step=1.0, key="card_warn_threshold"
        )

    categories = sidebar_category_editor()

    # 上傳
    card_open("📤 上傳 Excel（儲位明細）")
    uploaded = st.file_uploader(
        "請上傳儲位明細檔案（支援 xlsx/xls/xlsm/xlsb/csv）",
        type=["xlsx", "xls", "xlsm", "xlsb", "csv"],
        label_visibility="collapsed",
    )
    card_close()

    if not uploaded:
        st.info("請先上傳儲位明細檔案")
        return

    # 讀檔（支援 xlsb）
    try:
        df, sheet_used = robust_read_any_sheet_bytes(uploaded)
    except Exception as e:
        st.error("❌ 檔案讀取失敗")
        st.code(str(e))
        return

    df.columns = df.columns.astype(str).str.strip()
    st.caption(f"使用分頁：{sheet_used}")

    # =====================================================
    # ✅ 兩欄：左 區(溫層)分類｜右 棚別分類統計
    # =====================================================
    left_col, right_col = st.columns([1, 1], gap="large")

    # --------------------------
    # 左欄：區(溫層)分類
    # --------------------------
    with left_col:
        card_open("📌 區(溫層)分類（KPI + 卡片 + 圖表）")

        missing = [c for c in [col_zone, col_valid, col_used] if c not in df.columns]
        if missing:
            st.warning("⚠️ 此檔案缺少『區(溫層)分類』必要欄位，已跳過此段。")
            st.write("缺少欄位：", missing)
        else:
            res_df, others = compute_by_zone_categories(df, col_zone, col_valid, col_used, categories)

            total_valid = int(res_df["有效貨位"].sum()) if not res_df.empty else 0
            total_used = int(res_df["已使用貨位"].sum()) if not res_df.empty else 0
            total_rate = (total_used / total_valid * 100.0) if total_valid > 0 else 0.0

            render_kpis(
                [
                    KPI("有效貨位", f"{total_valid:,}"),
                    KPI("已使用貨位", f"{total_used:,}"),
                    KPI("總使用率", f"{total_rate:.2f}%"),
                    KPI("未分類區(溫層)數", f"{len(others):,}"),
                ],
                cols=4,
            )

            st.divider()

            # 卡片
            items = res_df.to_dict("records")
            cards_html = "\n".join(
                [f'<div class="gt-slot">{_category_card_html(it, float(warn_threshold))}</div>' for it in items]
            )
            st.markdown(f'<div class="gt-card-grid">{cards_html}</div>', unsafe_allow_html=True)

            st.divider()

            # 圖表
            _chart_usage_rate(res_df, threshold=float(chart_threshold), show_target_line=bool(show_target_line))

            st.divider()
            st.subheader("🔍 未納入分類的 區(溫層)")
            if others:
                st.write(others)
            else:
                st.success("全部已納入分類")

            # 匯出（區(溫層)分類結果）
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
                res_df.to_excel(writer, index=False, sheet_name="儲位分類統計")
                pd.DataFrame({"未分類區(溫層)": others}).to_excel(writer, index=False, sheet_name="未分類清單")
                cat_rows = [{"類別": k, "區碼清單": ",".join([str(x) for x in (v or [])])} for k, v in (categories or {}).items()]
                pd.DataFrame(cat_rows).to_excel(writer, index=False, sheet_name="分類定義")

            st.download_button(
                "⬇️ 匯出（區(溫層)分類結果 Excel）",
                data=out.getvalue(),
                file_name="4_儲位使用率_區(溫層)分類.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        card_close()

    # --------------------------
    # 右欄：棚別分類統計
    # --------------------------
    with right_col:
        card_open("🏷️ 棚別分類統計（大型/中型/小型/未知）")

        if "棚別" not in df.columns:
            st.error("❌ 找不到欄位『棚別』，無法進行棚別分類統計。")
            st.write("目前欄位：", list(df.columns))
            card_close()
            return

        df_shelf_detail = df.copy()
        df_shelf_detail["儲位類型"] = df_shelf_detail["棚別"].apply(classify_zone_from棚別)

        # 棚別統計
        df_shelf = (
            df_shelf_detail.groupby(["棚別"], dropna=False)
            .size()
            .reset_index(name="筆數")
            .sort_values(["筆數", "棚別"], ascending=[False, True])
        )

        # 儲位類型統計
        df_type = (
            df_shelf_detail.groupby(["儲位類型"], dropna=False)
            .size()
            .reset_index(name="筆數")
            .sort_values(["筆數", "儲位類型"], ascending=[False, True])
        )
        type_map = {str(r["儲位類型"]): int(r["筆數"]) for _, r in df_type.iterrows()}

        # ✅ 未知明細
        df_unknown = df_shelf_detail[df_shelf_detail["儲位類型"] == "未知"].copy()

        # ✅ 顯示方式：兩欄換列（大型/中型｜小型/未知）
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("### 大型儲位")
            st.markdown(f"**{type_map.get('大型儲位', 0):,} 筆**")
        with c2:
            st.markdown("### 中型儲位")
            st.markdown(f"**{type_map.get('中型儲位', 0):,} 筆**")

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        c3, c4 = st.columns(2, gap="large")
        with c3:
            st.markdown("### 小型儲位")
            st.markdown(f"**{type_map.get('小型儲位', 0):,} 筆**")
        with c4:
            st.markdown("### 未知")
            st.markdown(f"**{type_map.get('未知', 0):,} 筆**")

        st.divider()

        st.subheader("📋 棚別統計（Top 50）")
        st.dataframe(df_shelf.head(50), use_container_width=True, hide_index=True)

        st.divider()
        if len(df_unknown) == 0:
            st.info("未知：0 筆（無需列明細）")
        else:
            with st.expander(f"📌 未知明細（{len(df_unknown):,} 筆）", expanded=True):
                st.dataframe(df_unknown, use_container_width=True, hide_index=True)

                out_unknown = io.BytesIO()
                with pd.ExcelWriter(out_unknown, engine="xlsxwriter") as writer:
                    df_unknown.to_excel(writer, sheet_name="未知明細", index=False)
                out_unknown.seek(0)

                st.download_button(
                    "⬇️ 下載 未知明細.xlsx",
                    data=out_unknown.getvalue(),
                    file_name="未知明細.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        base = os.path.splitext(uploaded.name)[0]
        shelf_filename, shelf_bytes = build_shelf_output_excel_bytes(
            base_name=base,
            df_detail=df_shelf_detail,
            df_shelf=df_shelf,
            df_type=df_type,
            df_unknown=df_unknown,
        )

        st.download_button(
            "⬇️ 匯出（棚別分類統計 Excel）",
            data=shelf_bytes,
            file_name=shelf_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        card_close()


if __name__ == "__main__":
    main()
