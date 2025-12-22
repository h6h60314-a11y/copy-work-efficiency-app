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

    # basic clean
    df[col_zone] = df[col_zone].astype(str).str.strip()
    df[col_valid] = _to_num(df[col_valid])
    df[col_used] = _to_num(df[col_used])

    results = []
    for name, zones in CATEGORIES.items():
        data = df[df[col_zone].isin([str(z) for z in zones])]
        total_valid = float(data[col_valid].sum())
        total_used = float(data[col_used].sum())
        usage_rate = (total_used / total_valid * 100.0) if total_valid > 0 else 0.0
        results.append(
            {
                "類別": name,
                "有效貨位": int(round(total_valid)),
                "已使用貨位": int(round(total_used)),
                "使用率": usage_rate,
            }
        )

    # 未分類區(溫層)
    all_defined = [z for v in CATEGORIES.values() for z in v]
    others = sorted(df.loc[~df[col_zone].isin([str(x) for x in all_defined]), col_zone].dropna().unique().tolist())

    res_df = pd.DataFrame(results)
    res_df["使用率"] = res_df["使用率"].round(2)

    return res_df, others


def main():
    st.set_page_config(page_title="儲位分類統計", page_icon="📦", layout="wide")
    inject_logistics_theme()
    set_page("儲位分類統計", icon="📦", subtitle="依 區(溫層) 分類統計有效貨位 / 已使用貨位 / 使用率")

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

    # 讀檔（預設讀第一個 sheet；你也可以自己改成選 sheet）
    try:
        df = pd.read_excel(io.BytesIO(uploaded.getvalue()))
    except Exception as e:
        st.error("❌ 檔案讀取失敗")
        st.code(str(e))
        return

    df.columns = df.columns.astype(str).str.strip()

    # ======================
    # 欄位設定（保留你原本欄名，但也允許你調整）
    # ======================
    with st.sidebar:
        st.header("⚙️ 欄位設定")
        st.caption("如果你的欄位名稱跟預設不同，請在這裡指定。")

        col_zone = st.text_input("區(溫層) 欄位", value=DEFAULT_COL_ZONE)
        col_valid = st.text_input("有效貨位 欄位", value=DEFAULT_COL_VALID)
        col_used = st.text_input("已使用貨位 欄位", value=DEFAULT_COL_USED)

        st.divider()
        st.header("🧩 分類定義（固定）")
        for k, v in CATEGORIES.items():
            st.write(f"- **{k}**：{', '.join(v)}")

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
    res_df, others = compute(df, col_zone, col_valid, col_used)

    # ======================
    # 顯示結果（依你指定格式）
    # ======================
    card_open("📊 儲位分類統計結果")
    for _, r in res_df.iterrows():
        st.markdown(f"### {r['類別']}:")
        st.write(f"有效貨位={int(r['有效貨位']):,}")
        st.write(f"已使用貨位={int(r['已使用貨位']):,}")
        st.write(f"使用率={float(r['使用率']):.2f}%")
        st.write("")
    card_close()

    card_open("🔍 未納入四類分類的 區(溫層)")
    if others:
        st.write(others)
    else:
        st.success("全部已納入分類")
    card_close()

    # （可選）提供匯出結果
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
