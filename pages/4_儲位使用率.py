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

# ========= 1. 分類區碼定義 + 類別名稱 =========
CATEGORIES = {
    "輕型料架": ["001", "002", "003", "017", "016"],
    "落地儲": ["014", "018", "019", "020", "010", "081", "401", "402", "403"],
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


def compute(df: pd.DataFrame, col_zone: str, col_valid: str, col_used: str):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    df[col_zone] = df[col_zone].astype(str).str.strip()
    df[col_valid] = _to_num(df[col_valid])
    df[col_used] = _to_num(df[col_used])

    rows = []
    for name, zones in CATEGORIES.items():
        data = df[df[col_zone].isin([str(z) for z in zones])]
        total_valid = float(data[col_valid].sum())
        total_used = float(data[col_used].sum())
        usage_rate = (total_used / total_valid * 100.0) if total_valid > 0 else 0.0
        rows.append(
            {
                "類別": name,
                "有效貨位": int(round(total_valid)),
                "已使用貨位": int(round(total_used)),
                "未使用貨位": int(round(max(total_valid - total_used, 0))),
                "使用率(%)": round(usage_rate, 2),
            }
        )

    all_defined = [z for v in CATEGORIES.values() for z in v]
    others = sorted(
        df.loc[~df[col_zone].isin([str(x) for x in all_defined]), col_zone]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    res_df = pd.DataFrame(rows)
    return res_df, others


def _chart_usage_rate(res_df: pd.DataFrame, target: float | None = None):
    # Altair 失敗就 fallback
    try:
        import altair as alt  # type: ignore

        base = (
            alt.Chart(res_df)
            .mark_bar()
            .encode(
                x=alt.X("使用率(%):Q", title="使用率(%)"),
                y=alt.Y("類別:N", sort="-x", title=""),
                tooltip=["類別", "有效貨位", "已使用貨位", "未使用貨位", "使用率(%)"],
            )
            .properties(height=220)
        )

        layers = [base]
        if target is not None:
            rule = alt.Chart(pd.DataFrame({"target": [float(target)]})).mark_rule(strokeDash=[6, 4]).encode(
                x="target:Q"
            )
            layers.append(rule)

        st.altair_chart(alt.layer(*layers), use_container_width=True)
    except Exception:
        st.bar_chart(res_df.set_index("類別")["使用率(%)"])


def _chart_valid_used(res_df: pd.DataFrame):
    try:
        import altair as alt  # type: ignore

        melted = res_df.melt(id_vars=["類別"], value_vars=["有效貨位", "已使用貨位"], var_name="指標", value_name="數量")
        chart = (
            alt.Chart(melted)
            .mark_bar()
            .encode(
                x=alt.X("數量:Q", title="貨位數"),
                y=alt.Y("類別:N", sort="-x", title=""),
                color=alt.Color("指標:N", title=""),
                tooltip=["類別", "指標", "數量"],
            )
            .properties(height=240)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.bar_chart(res_df.set_index("類別")[["有效貨位", "已使用貨位"]])


def _chart_unused(res_df: pd.DataFrame):
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


def main():
    st.set_page_config(page_title="儲位分類統計", page_icon="📦", layout="wide")
    inject_logistics_theme()
    set_page("儲位分類統計", icon="📦", subtitle="KPI + 圖表｜依 區(溫層) 分類統計有效/已使用/使用率")

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
    # 欄位設定 + KPI目標（可選）
    # ======================
    with st.sidebar:
        st.header("⚙️ 欄位設定")
        col_zone = st.text_input("區(溫層) 欄位", value=DEFAULT_COL_ZONE)
        col_valid = st.text_input("有效貨位 欄位", value=DEFAULT_COL_VALID)
        col_used = st.text_input("已使用貨位 欄位", value=DEFAULT_COL_USED)

        st.divider()
        st.header("🎯 目標線（可選）")
        use_target = st.checkbox("顯示使用率目標線", value=False)
        target_rate = st.number_input("使用率目標(%)", min_value=0.0, max_value=100.0, value=90.0, step=1.0) if use_target else None

        st.divider()
        st.header("🧩 分類定義（固定）")
        for k, v in CATEGORIES.items():
            st.write(f"- **{k}**：{', '.join(v)}")

    missing = [c for c in [col_zone, col_valid, col_used] if c not in df.columns]
    if missing:
        st.error("❌ 找不到欄位")
        st.write("缺少欄位：", missing)
        st.write("目前欄位：", list(df.columns))
        return

    res_df, others = compute(df, col_zone, col_valid, col_used)

    # ======================
    # KPI 卡片
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
    # KPI 圖表
    # ======================
    c1, c2 = st.columns(2)

    with c1:
        card_open("📊 各類別使用率(%)")
        _chart_usage_rate(res_df, target=target_rate)
        card_close()

    with c2:
        card_open("📊 各類別有效 vs 已使用")
        _chart_valid_used(res_df)
        card_close()

    card_open("📊 各類別未使用貨位（有效-已使用）")
    _chart_unused(res_df)
    card_close()

    # ======================
    # 文字輸出（保留你原本格式）
    # ======================
    card_open("🧾 依格式顯示（與 Console 同邏輯）")
    for _, r in res_df.iterrows():
        st.markdown(f"### {r['類別']}:")
        st.write(f"有效貨位={int(r['有效貨位']):,}")
        st.write(f"已使用貨位={int(r['已使用貨位']):,}")
        st.write(f"使用率={float(r['使用率(%)']):.2f}%")
        st.write("")
    card_close()

    card_open("🔍 未納入四類分類的 區(溫層)")
    if others:
        st.write(others)
    else:
        st.success("全部已納入分類")
    card_close()

    # ======================
    # 匯出
    # ======================
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        res_df.to_excel(writer, index=False, sheet_name="儲位分類統計")
        pd.DataFrame({"未分類區(溫層)": others}).to_excel(writer, index=False, sheet_name="未分類清單")

    st.download_button(
        "⬇️ 匯出統計結果（Excel）",
        data=out.getvalue(),
        file_name="儲位分類統計.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
