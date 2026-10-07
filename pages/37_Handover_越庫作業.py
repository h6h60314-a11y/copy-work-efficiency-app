#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
37_Handover_越庫作業.py

功能：
1. 可一次選擇一個或多個 Excel 檔案
2. 每個檔案只讀取第一個工作表
3. 只篩選「單據類型 = 越庫」
4. 計算：
   - 應作業 PCS = 越庫資料「應作量」加總
   - 實際作業 PCS = 越庫資料「實作量」加總
   - 應作業 Line = 每張訂單內「門市代號 + 商品碼」不重複組合數
   - 實際完成 Line = 該 Line 的「實作量合計 = 應作量合計」才算完成
   - 未完成 Line = 應作業 Line - 實際完成 Line
   - Line 完成率 = 實際完成 Line / 應作業 Line

Line 唯一鍵：
    單號 + 門市代號 + 商品碼

如果同一個 Line 在原始資料中分成多筆，
會先依「單號 + 門市代號 + 商品碼」彙總應作量與實作量，
再判斷該 Line 是否完全完成。
"""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from common_ui import card_close, card_open, inject_logistics_theme, set_page


st.set_page_config(page_title="Handover | 越庫作業", page_icon="🔄", layout="wide")
inject_logistics_theme()


REQUIRED_COLUMNS = [
    "單號",
    "單據類型",
    "門市代號",
    "商品碼",
    "應作量",
    "實作量",
]

LINE_KEYS = ["單號", "門市代號", "商品碼"]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """欄名去除前後空白。"""
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
    return df


def validate_columns(df: pd.DataFrame, filename: str) -> None:
    """確認必要欄位是否存在。"""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(
            f"{filename}\n缺少必要欄位：{', '.join(missing)}"
        )


def read_excel_first_sheet(uploaded) -> pd.DataFrame:
    """讀取上傳 Excel 的第一個工作表。"""
    extension = Path(uploaded.name).suffix.lower()
    data = io.BytesIO(uploaded.getvalue())
    if extension in {".xlsx", ".xlsm"}:
        df = pd.read_excel(data, sheet_name=0, engine="openpyxl")
    elif extension == ".xls":
        df = pd.read_excel(data, sheet_name=0, engine="xlrd")
    else:
        raise ValueError(f"{uploaded.name}：僅支援 xlsx、xlsm、xls")
    df = normalize_columns(df)
    validate_columns(df, uploaded.name)
    df["_來源檔案"] = uploaded.name
    return df


def calculate_handover(files):
    """讀取多檔並計算越庫作業指標。"""
    dfs = []

    for filepath in files:
        df = read_excel_first_sheet(filepath)
        dfs.append(df)

    if not dfs:
        raise ValueError("沒有可處理的資料。")

    all_df = pd.concat(dfs, ignore_index=True)

    # -------------------------
    # 只看「單據類型 = 越庫」
    # -------------------------
    doc_type = all_df["單據類型"].astype(str).str.strip()
    crossdock = all_df.loc[doc_type.eq("越庫")].copy()

    if crossdock.empty:
        raise ValueError("所選檔案中找不到「單據類型 = 越庫」的資料。")

    # -------------------------
    # 數量欄位轉數值
    # 無法轉換或空白視為 0
    # -------------------------
    crossdock["應作量"] = pd.to_numeric(
        crossdock["應作量"], errors="coerce"
    ).fillna(0)

    crossdock["實作量"] = pd.to_numeric(
        crossdock["實作量"], errors="coerce"
    ).fillna(0)

    # -------------------------
    # 清理 Line 關鍵欄位
    # -------------------------
    for col in LINE_KEYS:
        crossdock[col] = crossdock[col].fillna("").astype(str).str.strip()

    # 避免商品碼由 Excel 讀成 123456.0
    crossdock["商品碼"] = crossdock["商品碼"].str.replace(
        r"\.0$", "", regex=True
    )

    # -------------------------
    # PCS
    # -------------------------
    expected_pcs = crossdock["應作量"].sum()
    actual_pcs = crossdock["實作量"].sum()

    # -------------------------
    # Line
    #
    # 每張訂單中：
    # 門市代號 + 商品碼 不重複算 1 Line
    #
    # 實際上完整唯一鍵為：
    # 單號 + 門市代號 + 商品碼
    # -------------------------
    line_detail = (
        crossdock
        .groupby(LINE_KEYS, dropna=False, as_index=False)
        .agg(
            應作業PCS=("應作量", "sum"),
            實際作業PCS=("實作量", "sum"),
        )
    )

    # 應作業 Line
    expected_line = len(line_detail)

    # 實際完成 Line：
    # 必須「實際作業 PCS = 應作業 PCS」才算完整完成
    line_detail["是否完成"] = (
        line_detail["實際作業PCS"] == line_detail["應作業PCS"]
    )

    actual_completed_line = int(line_detail["是否完成"].sum())
    incomplete_line = expected_line - actual_completed_line

    line_completion_rate = (
        actual_completed_line / expected_line
        if expected_line > 0 else 0
    )

    # 訂單數
    order_count = crossdock["單號"].nunique()

    result = {
        "越庫原始資料筆數": len(crossdock),
        "訂單數": order_count,
        "應作業PCS": expected_pcs,
        "實際作業PCS": actual_pcs,
        "應作業Line": expected_line,
        "實際完成Line": actual_completed_line,
        "未完成Line": incomplete_line,
        "Line完成率": line_completion_rate,
    }

    return result, line_detail


def fmt_number(value):
    """數字顯示：整數不顯示小數。"""
    try:
        value = float(value)
        if value.is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    except Exception:
        return str(value)


def build_result_text(result):
    """產生畫面顯示文字。"""
    return (
        "【Handover｜越庫作業】\n\n"
        f"越庫原始資料：{result['越庫原始資料筆數']:,} 筆\n"
        f"訂單數：{result['訂單數']:,} 張\n\n"
        f"應作業 PCS：{fmt_number(result['應作業PCS'])} PCS\n"
        f"實際作業 PCS：{fmt_number(result['實際作業PCS'])} PCS\n\n"
        f"應作業 Line：{result['應作業Line']:,} Line\n"
        f"實際完成 Line：{result['實際完成Line']:,} Line\n"
        f"未完成 Line：{result['未完成Line']:,} Line\n"
        f"Line 完成率：{result['Line完成率']:.2%}"
    )


def build_result_excel(result: dict, line_detail: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    summary = pd.DataFrame([result])
    export_detail = line_detail.copy()
    export_detail["完成狀態"] = export_detail["是否完成"].map({True: "完成", False: "未完成"})
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="越庫彙總")
        export_detail.to_excel(writer, index=False, sheet_name="Line明細")
    return output.getvalue()


set_page(
    "Handover | 越庫作業",
    icon="🔄",
    subtitle="多檔第一張工作表合併｜單據類型＝越庫｜計算應作業／實際作業 PCS 與 Line 完成率。",
)

card_open("📌 上傳越庫作業明細（可一次多檔）")
uploaded_files = st.file_uploader(
    "請選擇一個或多個 Excel 檔案",
    type=["xlsx", "xlsm", "xls"],
    accept_multiple_files=True,
    key="handover_crossdock_37",
)
card_close()

if not uploaded_files:
    st.info("必要欄位：單號、單據類型、門市代號、商品碼、應作量、實作量。")
    st.stop()

try:
    result, line_detail = calculate_handover(uploaded_files)
except Exception as exc:
    st.error(f"計算失敗：{exc}")
    st.stop()

st.markdown("### 📊 越庫作業結果")
st.metric("越庫原始資料", f"{result['越庫原始資料筆數']:,}")
st.metric("訂單數", f"{result['訂單數']:,}")
st.metric("應作業 PCS", fmt_number(result["應作業PCS"]))
st.metric("實際作業 PCS", fmt_number(result["實際作業PCS"]))
st.metric("應作業 Line", f"{result['應作業Line']:,}")
st.metric("實際完成 Line", f"{result['實際完成Line']:,}")
st.metric("未完成 Line", f"{result['未完成Line']:,}")
st.metric("Line 完成率", f"{result['Line完成率']:.2%}")

display_detail = line_detail.copy()
display_detail["完成狀態"] = display_detail["是否完成"].map({True: "完成", False: "未完成"})
with st.expander("🧾 越庫 Line 明細", expanded=False):
    st.dataframe(display_detail, use_container_width=True, height=430)

st.download_button(
    "⬇️ 下載越庫作業結果",
    data=build_result_excel(result, line_detail),
    file_name="Handover_越庫作業結果.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
