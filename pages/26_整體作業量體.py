# pages/26_整體作業量體.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from io import BytesIO
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from common_ui import (
    inject_logistics_theme,
    set_page,
    KPI,
    render_kpis,
    card_open,
    card_close,
    download_excel_card,  # ✅ 一行=按鈕（且外框不分段）
)

st.set_page_config(page_title="大豐KPI｜整體作業量體", page_icon="🧹", layout="wide")
inject_logistics_theme()

set_page(
    "整體作業量體",
    icon="🧹",
    subtitle="刪除箱類型含『站所』｜計量單位數量｜出貨單位（判斷後）｜GM/一般倉 × 成箱/零散統計｜Excel下載",
)

# ----------------------------
# helpers
# ----------------------------
NEED_COLS = ["packqty", "入數", "箱類型", "載具號", "BOXTYPE", "boxid"]


def _fmt_int(x) -> str:
    try:
        return f"{int(round(float(x))):,}"
    except Exception:
        return "0"


def _fmt0(x) -> str:
    # 數值以 0 位小數呈現
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"


def _safe_str(s: pd.Series) -> pd.Series:
    return s.astype(str).fillna("").astype(str)


def robust_read_excel(uploaded_file) -> pd.DataFrame:
    raw = uploaded_file.getvalue()
    bio = BytesIO(raw)
    try:
        return pd.read_excel(bio, engine="openpyxl")
    except Exception:
        try:
            bio.seek(0)
            return pd.read_excel(bio, engine="xlrd")
        except Exception as e:
            raise RuntimeError(f"讀取 Excel 失敗：{e}")


def make_excel_bytes(df_processed: pd.DataFrame, summary_df: pd.DataFrame) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="統計結果")
        df_processed.to_excel(writer, index=False, sheet_name="處理後明細")
    return bio.getvalue()


def compute(df_raw: pd.DataFrame) -> dict:
    missing = [c for c in NEED_COLS if c not in df_raw.columns]
    if missing:
        raise KeyError(f"⚠️ 找不到必要欄位：{missing}，請確認表頭名稱是否一致。")

    df0 = df_raw.copy()

    # 1) 刪除「箱類型」含「站所」
    before = len(df0)
    df = df0[~_safe_str(df0["箱類型"]).str.contains("站所", na=False)].copy()
    removed_station = before - len(df)

    # 2) 新增欄位
    pack = pd.to_numeric(df["packqty"], errors="coerce")
    unit = pd.to_numeric(df["入數"], errors="coerce")

    # 計量單位數量 = packqty ÷ 入數（入數=0或空→NaN）
    qty_unit = np.where((~pd.isna(unit)) & (unit != 0), pack / unit, np.nan)
    df["計量單位數量"] = qty_unit

    # 出貨單位（判斷後）：
    # - 計量單位數量為整數 → 用計量單位數量
    # - 否則 → 用 packqty
    v = pd.to_numeric(df["計量單位數量"], errors="coerce")
    is_int = np.isfinite(v) & np.isclose(v, np.round(v))
    df["出貨單位（判斷後）"] = np.where(is_int, v, pack)

    # 2-3 欄位順序：插在「入數」右邊
    cols = list(df.columns)
    for c in ["計量單位數量", "出貨單位（判斷後）"]:
        if c in cols:
            cols.remove(c)
    ins_pos = cols.index("入數") + 1
    cols[ins_pos:ins_pos] = ["計量單位數量", "出貨單位（判斷後）"]
    df = df[cols]

    # 3) 統計遮罩
    mask_gm = _safe_str(df["載具號"]).str.contains("GM", case=False, na=False)
    boxtype = _safe_str(df["BOXTYPE"]).str.strip()
    mask_box1 = boxtype == "1"
    mask_box0 = boxtype == "0"
    mask_not_gm = ~mask_gm

    # 4) 四項統計
    # A：GM + BOXTYPE=1 → 不重複 boxid
    unique_boxid_count = (
        df.loc[mask_gm & mask_box1, "boxid"]
        .astype(str)
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .nunique()
    )

    ship_unit = pd.to_numeric(df["出貨單位（判斷後）"], errors="coerce")

    # B：非GM + BOXTYPE=0 → 出貨單位加總
    total_shipunit_notgm_box0 = ship_unit.loc[mask_not_gm & mask_box0].sum()

    # C：GM + BOXTYPE=1 → 出貨單位加總
    total_shipunit_gm_box1 = ship_unit.loc[mask_gm & mask_box1].sum()

    # D：非GM + BOXTYPE=1 → 出貨單位加總
    total_shipunit_notgm_box1 = ship_unit.loc[mask_not_gm & mask_box1].sum()

    summary = pd.DataFrame(
        [
            {"項目": "A) GM件數（GM + BOXTYPE=1，不重複boxid）", "數值": unique_boxid_count},
            {"項目": "B) 一般倉零散PCS（非GM + BOXTYPE=0）", "數值": total_shipunit_notgm_box0},
            {"項目": "C) GM成箱PCS（GM + BOXTYPE=1）", "數值": total_shipunit_gm_box1},
            {"項目": "D) 一般倉成箱PCS（非GM + BOXTYPE=1）", "數值": total_shipunit_notgm_box1},
        ]
    )

    return {
        "df_processed": df,
        "removed_station": removed_station,
        "total_in": len(df_raw),
        "total_after": len(df),
        "A_gm_cases": unique_boxid_count,
        "B_notgm_loose_pcs": total_shipunit_notgm_box0,
        "C_gm_box_pcs": total_shipunit_gm_box1,
        "D_notgm_box_pcs": total_shipunit_notgm_box1,
        "summary": summary,
    }


# ----------------------------
# UI
# ----------------------------
card_open("📥 上傳明細")
uploaded = st.file_uploader(
    "請上傳要處理的 Excel（.xlsx / .xls）",
    type=["xlsx", "xls", "xlsm"],
    accept_multiple_files=False,
)
card_close()

if not uploaded:
    st.info("請先上傳 Excel 檔。")
    st.stop()

try:
    df_raw = robust_read_excel(uploaded)
    out = compute(df_raw)
except Exception as e:
    st.error(str(e))
    st.stop()

st.caption(
    f"已讀取 {out['total_in']:,} 列；"
    f"刪除『箱類型含站所』 {out['removed_station']:,} 列；"
    f"剩餘 {out['total_after']:,} 列作為統計與輸出。"
)

# KPI：2 欄版型（左：GM、右：一般倉）
c1, c2 = st.columns(2, gap="large")

with c1:
    render_kpis(
        [
            KPI("A) GM件數", _fmt_int(out["A_gm_cases"])),
            KPI("C) GM成箱PCS", _fmt0(out["C_gm_box_pcs"])),
        ],
        cols=1,
    )

with c2:
    render_kpis(
        [
            KPI("B) 一般倉零散PCS", _fmt0(out["B_notgm_loose_pcs"])),
            KPI("D) 一般倉成箱PCS", _fmt0(out["D_notgm_box_pcs"])),
        ],
        cols=1,
    )

# 統計表
card_open("📌 統計結果")
sum_df = out["summary"].copy()
# 顯示用格式
sum_df["數值"] = sum_df["數值"].apply(_fmt0)
st.dataframe(sum_df, use_container_width=True, hide_index=True)
card_close()

# 匯出
card_open("📤 匯出")
stamp = datetime.now().strftime("%Y%m%d_%H%M")
filename = f"大豐KPI_整理作業量體_{stamp}.xlsx"

xlsx_bytes = make_excel_bytes(out["df_processed"], out["summary"])

download_excel_card(
    title="✅ 下載 Excel（含：統計結果 + 處理後明細）",
    data=xlsx_bytes,
    filename=filename,
)

with st.expander("🔎 處理後明細預覽（前 200 筆）", expanded=False):
    st.dataframe(out["df_processed"].head(200), use_container_width=True)

card_close()
