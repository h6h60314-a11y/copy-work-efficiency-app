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
    subtitle="支援 Excel / TXT｜刪除箱類型含『站所』｜計量單位數量｜出貨單位（判斷後）｜GM/一般倉 × 成箱/零散統計｜Excel下載",
)

# ----------------------------
# constants / helpers
# ----------------------------
NEED_COLS = ["packqty", "入數", "箱類型", "載具號", "BOXTYPE", "boxid"]
CANDIDATE_SEPS = ["\t", ",", "|", ";"]  # 常見 txt 分隔符
CANDIDATE_ENCODINGS = ["utf-8-sig", "utf-8", "cp950", "big5"]  # 台灣常見


def _safe_str(s: pd.Series) -> pd.Series:
    return s.astype(str).fillna("").astype(str)


def _fmt_int(x) -> str:
    try:
        return f"{int(round(float(x))):,}"
    except Exception:
        return "0"


def _fmt0(x) -> str:
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"


def _detect_sep(text: str) -> str:
    """用第一行粗略猜分隔符"""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "\t"
    first = lines[0]
    best = "\t"
    best_cnt = -1
    for sep in CANDIDATE_SEPS:
        cnt = first.count(sep)
        if cnt > best_cnt:
            best_cnt = cnt
            best = sep
    return best


def read_txt_bytes(raw: bytes, force_sep: str | None = None, force_encoding: str | None = None) -> pd.DataFrame:
    """
    TXT 讀取（自動猜分隔符、嘗試多種編碼）。
    - 若 force_sep / force_encoding 有指定，會優先使用。
    """
    last_err = None

    encodings = [force_encoding] if force_encoding else []
    encodings += [e for e in CANDIDATE_ENCODINGS if e not in encodings]

    for enc in encodings:
        try:
            text = raw.decode(enc, errors="strict")
        except Exception as e:
            last_err = e
            continue

        sep = force_sep if force_sep else _detect_sep(text)

        # 用 pandas 讀取
        try:
            bio = BytesIO(raw)
            df = pd.read_csv(
                bio,
                sep=sep,
                encoding=enc,
                dtype=str,          # 先全部讀字串，後面再轉數值（比較穩）
                engine="python",    # 對於不規則分隔較容錯
            )
            return df
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"TXT 讀取失敗（可能是分隔符/編碼不符或檔案格式非表格）：{last_err}")


def robust_read_file(uploaded_file, txt_sep_choice: str, txt_encoding_choice: str) -> pd.DataFrame:
    name = (uploaded_file.name or "").lower()
    raw = uploaded_file.getvalue()

    # TXT 控制
    sep_map = {
        "自動": None,
        "Tab": "\t",
        "逗號 ,": ",",
        "直線 |": "|",
        "分號 ;": ";",
    }
    force_sep = sep_map.get(txt_sep_choice, None)
    force_enc = None if txt_encoding_choice == "自動" else txt_encoding_choice

    if name.endswith(".txt") or name.endswith(".csv"):
        return read_txt_bytes(raw, force_sep=force_sep, force_encoding=force_enc)

    # Excel
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


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把欄名前後空白去掉（TXT 很常發生）"""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def compute(df_raw: pd.DataFrame) -> dict:
    df_raw = _normalize_columns(df_raw)

    missing = [c for c in NEED_COLS if c not in df_raw.columns]
    if missing:
        # 再做一次「忽略大小寫/空白」嘗試對照（避免 TXT 欄名怪）
        lower_map = {str(c).strip().lower(): c for c in df_raw.columns}
        remap = {}
        for need in NEED_COLS:
            key = need.strip().lower()
            if key in lower_map:
                remap[lower_map[key]] = need
        if remap:
            df_raw = df_raw.rename(columns=remap)
            df_raw = _normalize_columns(df_raw)

        missing2 = [c for c in NEED_COLS if c not in df_raw.columns]
        if missing2:
            raise KeyError(f"⚠️ 找不到必要欄位：{missing2}，請確認 TXT/Excel 的表頭是否一致。")

    df0 = df_raw.copy()

    # 1) 刪除「箱類型」含「站所」
    before = len(df0)
    df = df0[~_safe_str(df0["箱類型"]).str.contains("站所", na=False)].copy()
    removed_station = before - len(df)

    # 2) 新增欄位
    pack = pd.to_numeric(df["packqty"], errors="coerce")
    unit = pd.to_numeric(df["入數"], errors="coerce")

    df["計量單位數量"] = np.where((unit.notna()) & (unit != 0), pack / unit, np.nan)

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
    unique_boxid_count = (
        df.loc[mask_gm & mask_box1, "boxid"]
        .astype(str)
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .nunique()
    )

    ship_unit = pd.to_numeric(df["出貨單位（判斷後）"], errors="coerce")
    total_shipunit_notgm_box0 = ship_unit.loc[mask_not_gm & mask_box0].sum()
    total_shipunit_gm_box1 = ship_unit.loc[mask_gm & mask_box1].sum()
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
card_open("📥 上傳明細（Excel / TXT）")

# TXT 讀取輔助（可不管它，預設自動）
colA, colB = st.columns(2)
with colA:
    txt_sep_choice = st.selectbox("TXT 分隔符", ["自動", "Tab", "逗號 ,", "直線 |", "分號 ;"], index=0)
with colB:
    txt_encoding_choice = st.selectbox("TXT 編碼", ["自動", "utf-8-sig", "utf-8", "cp950", "big5"], index=0)

uploaded = st.file_uploader(
    "請上傳要處理的檔案（.xlsx / .xls / .txt）",
    type=["xlsx", "xls", "xlsm", "txt", "csv"],
    accept_multiple_files=False,
)
card_close()

if not uploaded:
    st.info("請先上傳檔案。")
    st.stop()

try:
    df_raw = robust_read_file(uploaded, txt_sep_choice=txt_sep_choice, txt_encoding_choice=txt_encoding_choice)
    out = compute(df_raw)
except Exception as e:
    st.error(str(e))
    st.stop()

st.caption(
    f"已讀取 {out['total_in']:,} 列；"
    f"刪除『箱類型含站所』 {out['removed_station']:,} 列；"
    f"剩餘 {out['total_after']:,} 列作為統計與輸出。"
)

# KPI：2 欄（左：GM，右：一般倉）
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

card_open("📌 統計結果")
sum_df = out["summary"].copy()
sum_df["數值"] = sum_df["數值"].apply(_fmt0)
st.dataframe(sum_df, use_container_width=True, hide_index=True)
card_close()

card_open("📤 匯出")
stamp = datetime.now().strftime("%Y%m%d_%H%M")
filename = f"大豐KPI_整體作業量體_{stamp}.xlsx"
xlsx_bytes = make_excel_bytes(out["df_processed"], out["summary"])

download_excel_card(
    title="✅ 下載 Excel（含：統計結果 + 處理後明細）",
    data=xlsx_bytes,
    filename=filename,
)

with st.expander("🔎 處理後明細預覽（前 200 筆）", expanded=False):
    st.dataframe(out["df_processed"].head(200), use_container_width=True)
card_close()
