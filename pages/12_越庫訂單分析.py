# pages/12_越庫訂單分析.py
import re
from io import BytesIO

import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="越庫訂單分析", page_icon="🧾", layout="wide")
inject_logistics_theme()


# -----------------------------
# Helpers
# -----------------------------
def _read_excel(uploaded_file) -> pd.DataFrame:
    """依副檔名自動選 engine（.xlsx 用 openpyxl，.xls 用 xlrd）。"""
    name = (uploaded_file.name or "").lower()
    if name.endswith(".xls"):
        return pd.read_excel(uploaded_file, engine="xlrd")
    return pd.read_excel(uploaded_file, engine="openpyxl")


def _fmt_num(x):
    try:
        if pd.isna(x):
            return "0"
        if float(x).is_integer():
            return f"{int(float(x)):,}"
        return f"{float(x):,.2f}"
    except Exception:
        return str(x)


def _insert_note_col(df: pd.DataFrame, col_name="比對備註", pos_1based=18) -> pd.DataFrame:
    """把欄位插到第 pos_1based 欄（不足就放最後）"""
    if col_name not in df.columns:
        return df
    cols = list(df.columns)
    cols.remove(col_name)
    idx0 = max(0, min(len(cols), pos_1based - 1))
    cols.insert(idx0, col_name)
    return df[cols]


def _to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="結果")
    return output.getvalue()


# -----------------------------
# Main
# -----------------------------
def main():
    set_page(
        "越庫結案比對",
        icon="🧾",
        subtitle="上傳兩份報表｜結案人比對｜排除 FT03~FT11｜統計越庫應作/實作｜輸出結果",
    )

    card_open("📌 上傳檔案")
    c1, c2 = st.columns(2, gap="large")

    with c1:
        f1 = st.file_uploader(
            "導入-單據明細查看（Excel）",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
        )
    with c2:
        f2 = st.file_uploader(
            "製單-已結案單據查詢（Excel）",
            type=["xlsx", "xls"],
            accept_multiple_files=False,
        )

    run = st.button("開始分析", type="primary", use_container_width=True)
    card_close()

    if not run:
        return
    if not f1 or not f2:
        st.error("請先上傳兩個檔案（單據明細查看、已結案單據查詢）")
        return

    # 讀取
    try:
        df1 = _read_excel(f1)
        df2 = _read_excel(f2)
    except Exception as e:
        st.exception(e)
        return

    # 去空白
    df1.columns = df1.columns.astype(str).str.strip()
    df2.columns = df2.columns.astype(str).str.strip()

    # 必要欄位檢查
    need1 = ["單號", "單據類型", "作業類型", "應作量", "實作量"]
    need2 = ["SONO", "CLOSE_USER"]
    miss1 = [c for c in need1 if c not in df1.columns]
    miss2 = [c for c in need2 if c not in df2.columns]
    if miss1:
        st.error(f"第一個檔案缺少欄位：{miss1}")
        return
    if miss2:
        st.error(f"第二個檔案缺少欄位：{miss2}")
        return

    # 新增「比對備註」
    close_map = df2.set_index("SONO")["CLOSE_USER"]
    df1["比對備註"] = df1["單號"].map(close_map).fillna("無對應")

    # 剔除 CLOSE_USER 含 FT03~FT11（用你原本 pattern）
    pattern = r"FT0[3-9]|FT1[0-1]"
    mask_ft = df1["比對備註"].astype(str).str.contains(pattern, regex=True, na=False)
    df1 = df1.loc[~mask_ft].copy()

    # B/C 清理（一定要在計算不重複前）
    df1["單號"] = (
        df1["單號"].astype(str)
        .str.replace("B", "", regex=False)
        .str.replace("C", "", regex=False)
    )

    # 數值欄位轉數字
    df1["應作量"] = pd.to_numeric(df1["應作量"], errors="coerce").fillna(0)
    df1["實作量"] = pd.to_numeric(df1["實作量"], errors="coerce").fillna(0)

    # 越庫條件
    cond = df1["單據類型"].astype(str).eq("越庫")

    # 統計
    total_scatter_expected = df1.loc[cond & (df1["作業類型"] == "零散"), "應作量"].sum()
    total_box_expected = df1.loc[cond & (df1["作業類型"] == "成箱"), "應作量"].sum()
    total_scatter_actual = df1.loc[cond & (df1["作業類型"] == "零散"), "實作量"].sum()
    total_box_actual = df1.loc[cond & (df1["作業類型"] == "成箱"), "實作量"].sum()
    unique_count = df1.loc[cond, "單號"].nunique()

    # 插入「比對備註」到第18欄
    df1 = _insert_note_col(df1, col_name="比對備註", pos_1based=18)

    # 呈現：4 個區塊（直向）
    card_open("📊 統計結果")
    left, right = st.columns([1.2, 1], gap="large")

    with left:
        st.markdown("#### 越庫｜應作量（直向）")
        st.metric("越庫＋零散｜應作量總和", _fmt_num(total_scatter_expected))
        st.metric("越庫＋成箱｜應作量總和", _fmt_num(total_box_expected))
        st.metric("訂單筆數（越庫/去重）", _fmt_num(unique_count))

    with right:
        st.markdown("#### 越庫｜實作量（直向）")
        st.metric("越庫＋零散｜實作量總和", _fmt_num(total_scatter_actual))
        st.metric("越庫＋成箱｜實作量總和", _fmt_num(total_box_actual))

    card_close()

    # 預覽 + 下載
    card_open("📄 明細預覽（已插入：比對備註）")
    st.caption(f"已讀取：{f1.name}（{len(df1):,} 筆 / {df1.shape[1]} 欄）｜已排除 FT03~FT11")
    st.dataframe(df1, use_container_width=True, height=420)
    card_close()

    xlsx_bytes = _to_xlsx_bytes(df1)
    st.download_button(
        "⬇️ 下載結果 Excel（xlsx）",
        data=xlsx_bytes,
        file_name="越庫結案比對_結果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
