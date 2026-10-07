#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Handover 實際完成 Line：多檔第一張工作表直接合併並統計有效資料列。"""

import io
from pathlib import Path

import pandas as pd
import streamlit as st

from common_ui import card_close, card_open, inject_logistics_theme, set_page


st.set_page_config(page_title="Handover | 實際完成 Line", page_icon="✅", layout="wide")
inject_logistics_theme()


def read_excel_first_sheet(uploaded):
    """讀取 Excel 第一個工作表，並移除真正的整列空白資料。"""
    extension = Path(uploaded.name).suffix.lower()
    data = io.BytesIO(uploaded.getvalue())

    if extension == ".xlsx":
        df = pd.read_excel(data, sheet_name=0, engine="openpyxl")
    elif extension == ".xls":
        df = pd.read_excel(data, sheet_name=0, engine="xlrd")
    else:
        raise ValueError(f"{uploaded.name}：不支援的檔案格式 {extension}")

    df.columns = [str(column).strip() for column in df.columns]
    return df.dropna(how="all").reset_index(drop=True)


def merge_uploaded_files(uploaded_files):
    """依第一份檔案的欄位合併；不去重、不排除任何有值資料列。"""
    dataframes = []
    file_details = []
    base_columns = None

    for uploaded in uploaded_files:
        df = read_excel_first_sheet(uploaded)

        if base_columns is None:
            base_columns = list(df.columns)
        else:
            if set(df.columns) != set(base_columns):
                missing = [column for column in base_columns if column not in df.columns]
                extra = [column for column in df.columns if column not in base_columns]
                raise ValueError(
                    f"檔案欄位不一致：{uploaded.name}；"
                    f"缺少欄位：{missing or '無'}；多出欄位：{extra or '無'}"
                )
            df = df[base_columns]

        file_details.append({"檔名": uploaded.name, "有效資料行數": len(df)})
        dataframes.append(df)

    return pd.concat(dataframes, ignore_index=True), pd.DataFrame(file_details)


def build_excel(merged_df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        merged_df.to_excel(writer, index=False, sheet_name="實際完成Line")
    return output.getvalue()


set_page(
    "Handover | 實際完成 Line",
    icon="✅",
    subtitle="多個 Excel 第一張工作表直接合併｜不去重｜僅排除整列完全空白資料。",
)

card_open("📌 上傳實際完成 Line 明細（可一次多檔）")
uploaded_files = st.file_uploader(
    "請選擇一個或多個 Excel 檔案",
    type=["xlsx", "xls"],
    accept_multiple_files=True,
    key="handover_actual_line_38",
)
card_close()

if not uploaded_files:
    st.info("請上傳 Excel 檔案；每個檔案會讀取第一個工作表。")
    st.stop()

try:
    merged_df, file_details = merge_uploaded_files(uploaded_files)
except Exception as exc:
    st.error(f"處理檔案時發生錯誤：{exc}")
    st.stop()

st.markdown("### 📊 實際完成 Line 結果")
st.metric("合併後總行數", f"{len(merged_df):,}")
st.caption("不去重、不排除有值資料列；僅不計 Excel 標題列與整列完全空白資料。")

with st.expander("📄 各檔案行數", expanded=True):
    st.dataframe(file_details, use_container_width=True, hide_index=True)

with st.expander("🧾 合併資料明細", expanded=False):
    st.dataframe(merged_df, use_container_width=True, height=430)

st.download_button(
    "⬇️ 下載合併後 Excel",
    data=build_excel(merged_df),
    file_name="Handover_實際完成line_合併.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
