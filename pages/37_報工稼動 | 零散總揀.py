# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from io import BytesIO
from typing import List, Tuple

import numpy as np
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

pd.options.display.max_columns = 200

# 需要排除的儲位關鍵字（子字串比對，不分大小寫）
EXCLUDE_SUBSTRINGS = ["CGS", "JCPL", "QC99", "GREAT0001X", "GX010", "PD99"]
EXCLUDE_PATTERN = re.compile("|".join(map(re.escape, EXCLUDE_SUBSTRINGS)), re.IGNORECASE)

# Line 定義：可選批次號 + 儲位類型 + 儲位 + 商品
PIVOT1_BASE_ROWS = ["儲位類型", "儲位", "商品"]
PIVOT1_OPTIONAL = ["揀貨批次號"]

# 應揀 / 實揀欄位配對，依序優先判斷
# 注意：一定用「一組明確配對」比較，不會把不同語意欄位任意混搭。
QTY_COLUMN_PAIRS = [
    ("應揀量", "RF揀貨量"),
    ("應揀數量", "實際揀貨量"),
    ("應揀數量", "實揀量"),
    ("原始配庫存量", "數量"),
    ("數量", "計量單位數量"),
]

# 若來源沒有商品欄位，補虛擬欄位
PRODUCT_FALLBACK_COL = "商品"


def normalize_loc(s):
    if pd.isna(s):
        return s
    return str(s).strip().upper()


def unit_mask_equal_2(series: pd.Series) -> pd.Series:
    """成箱：=2（字面 '2' 或數值 2/2.0）"""
    s = series.astype(str).str.strip()
    mask_str = s.eq("2")
    s_num = pd.to_numeric(s, errors="coerce")
    mask_num = np.isfinite(s_num) & np.isclose(s_num, 2.0, rtol=0, atol=1e-9)
    return mask_str | mask_num


def unit_mask_contains_3_or_6(series: pd.Series) -> pd.Series:
    """零散：字串含 3 或 6（含全形 ３／６），任意位置"""
    s = series.astype(str)
    pat = re.compile(r"[3３]|[6６]")
    return s.str.contains(pat, na=False)


def _read_csv_auto(file_bytes: bytes) -> pd.DataFrame:
    last_err = None
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return pd.read_csv(BytesIO(file_bytes), encoding=enc, low_memory=False, dtype=str)
        except Exception as e:
            last_err = e
    raise RuntimeError(
        f"CSV/TXT 讀取失敗（已嘗試 utf-8-sig/utf-8/cp950/big5）：{last_err}"
    )


def read_excel_or_csv(uploaded) -> pd.DataFrame:
    """讀單表，支援 Excel/CSV/TXT。"""
    name = uploaded.name
    _, ext = os.path.splitext(name)
    ext = ext.lower()
    b = uploaded.getvalue()

    if ext in (".csv", ".txt"):
        return _read_csv_auto(b)

    bio = BytesIO(b)
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        try:
            return pd.read_excel(bio, dtype=str, engine="openpyxl")
        except Exception:
            bio.seek(0)
            return pd.read_excel(bio, dtype=str)

    if ext == ".xls":
        try:
            return pd.read_excel(bio, dtype=str, engine="xlrd")
        except Exception as e:
            raise RuntimeError(
                "目前環境可能未安裝 xlrd，.xls 無法讀取；請先另存為 .xlsx 再上傳。"
            ) from e

    if ext == ".xlsb":
        try:
            return pd.read_excel(bio, dtype=str, engine="pyxlsb")
        except Exception as e:
            raise RuntimeError(
                "目前環境可能未安裝 pyxlsb，.xlsb 無法讀取；請先另存為 .xlsx 再上傳。"
            ) from e

    bio.seek(0)
    return pd.read_excel(bio, dtype=str)


def detect_qty_columns(df: pd.DataFrame) -> Tuple[str, str]:
    """偵測應揀量 / 實際揀貨量欄位，回傳 (應揀欄位, 實揀欄位)。"""
    for expected_col, actual_col in QTY_COLUMN_PAIRS:
        if expected_col in df.columns and actual_col in df.columns:
            return expected_col, actual_col

    pair_text = "、".join([f"{a} / {b}" for a, b in QTY_COLUMN_PAIRS])
    raise ValueError(
        "找不到可判定完成 Line 的『應揀 / 實揀』欄位配對。"
        f"目前支援：{pair_text}"
    )


def build_pivot2(
    df_source: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str], str, str]:
    """
    Line 定義：
      揀貨批次號（若有） + 儲位類型 + 儲位 + 商品

    應作業Line：每個不重複 Line 算 1。

    實際完成Line：
      該 Line 底下每一筆原始資料都必須「實際揀貨量 == 應揀量」才算完成。
      少揀、多揀、未揀、數量空白，或有揀但不等於應揀，都不算完成。
      不允許同一 Line 內正負差異互相抵銷後被判完成。
    """
    df_tmp = df_source.copy()

    expected_col, actual_col = detect_qty_columns(df_tmp)

    df_tmp["_應揀量"] = pd.to_numeric(df_tmp[expected_col], errors="coerce")
    df_tmp["_實際揀貨量"] = pd.to_numeric(df_tmp[actual_col], errors="coerce")

    # 單筆必須有兩邊數值，且完全相等，才是無差異。
    df_tmp["_單筆完成"] = (
        df_tmp["_應揀量"].notna()
        & df_tmp["_實際揀貨量"].notna()
        & np.isclose(
            df_tmp["_應揀量"].astype(float),
            df_tmp["_實際揀貨量"].astype(float),
            rtol=0,
            atol=1e-9,
        )
    )

    gb1 = [k for k in (PIVOT1_OPTIONAL + PIVOT1_BASE_ROWS) if k in df_tmp.columns]
    if ("儲位類型" not in gb1) or ("儲位" not in gb1):
        raise ValueError("樞紐所需欄位不足，至少要有：儲位、儲位類型。")

    # 每個 group 即 1 Line。
    # 「全部完成」使用 all：Line 內只要一筆有差異，整個 Line 即未完成。
    pivot1 = (
        df_tmp.groupby(gb1, dropna=False)
        .agg(
            原始筆數=("_單筆完成", "size"),
            全部完成=("_單筆完成", "all"),
            應揀PCS=("_應揀量", "sum"),
            實際揀PCS=("_實際揀貨量", "sum"),
        )
        .reset_index()
    )

    pivot1["應作業Line"] = 1
    pivot1["實際完成Line"] = pivot1["全部完成"].fillna(False).astype(int)
    pivot1["未完成Line"] = pivot1["應作業Line"] - pivot1["實際完成Line"]

    group_keys = ["儲位類型"] + (
        ["揀貨批次號"] if "揀貨批次號" in pivot1.columns else []
    )

    pivot2 = (
        pivot1.groupby(group_keys, dropna=False)
        .agg(
            應作業Line=("應作業Line", "sum"),
            實際完成Line=("實際完成Line", "sum"),
            未完成Line=("未完成Line", "sum"),
            應揀PCS=("應揀PCS", "sum"),
            實際揀PCS=("實際揀PCS", "sum"),
        )
        .reset_index()
        .sort_values(group_keys, kind="mergesort")
        .reset_index(drop=True)
    )

    for c in ["應作業Line", "實際完成Line", "未完成Line"]:
        pivot2[c] = pivot2[c].fillna(0).astype(int)

    pivot2["Line完成率"] = np.where(
        pivot2["應作業Line"] > 0,
        pivot2["實際完成Line"] / pivot2["應作業Line"],
        0.0,
    )

    return pivot2, group_keys, expected_col, actual_col


def process_subset(
    df_raw: pd.DataFrame,
    df_map: pd.DataFrame,
    subset_tag: str,
    mask: pd.Series,
):
    df_work = df_raw.loc[mask].copy()
    if df_work.empty:
        return subset_tag, None, 0, None, None, None

    # 排除儲位
    df_work = df_work[
        ~df_work["儲位"].astype(str).str.contains(EXCLUDE_PATTERN, na=False)
    ].copy()
    if df_work.empty:
        return subset_tag, None, 0, None, None, None

    # 回填儲位類型
    df_work["儲位_norm"] = df_work["儲位"].map(normalize_loc)
    map_first = (
        df_map.assign(儲位_norm=df_map["儲位"].map(normalize_loc))
        .sort_values(["儲位_norm"])
        .drop_duplicates(subset=["儲位_norm"], keep="first")[["儲位_norm", "儲位類型"]]
    )
    df_out = df_work.merge(map_first, on="儲位_norm", how="left").drop(
        columns=["儲位_norm"]
    )

    pivot2, group_keys, expected_col, actual_col = build_pivot2(df_out)
    total_count = int(pivot2["應作業Line"].sum(skipna=True))
    return subset_tag, pivot2, total_count, group_keys, expected_col, actual_col


def build_single_sheet_excel_bytes(
    df_type_total: pd.DataFrame,
    df_detail_all: pd.DataFrame,
    df_summary: pd.DataFrame,
) -> bytes:
    """
    單一工作表：
      1) 總揀 / Line 完成概況
      2) 明細表（合併）
      3) 彙總總表
    """
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        sheet = "結果"
        r = 0

        pd.DataFrame({"": ["總揀 / Line 完成概況"]}).to_excel(
            writer,
            sheet_name=sheet,
            index=False,
            header=False,
            startrow=r,
            startcol=0,
        )
        r += 1
        df_type_total.to_excel(writer, sheet_name=sheet, index=False, startrow=r, startcol=0)
        r += len(df_type_total) + 2

        pd.DataFrame({"": ["明細表（合併）"]}).to_excel(
            writer,
            sheet_name=sheet,
            index=False,
            header=False,
            startrow=r,
            startcol=0,
        )
        r += 1
        df_detail_all.to_excel(writer, sheet_name=sheet, index=False, startrow=r, startcol=0)
        r += len(df_detail_all) + 2

        pd.DataFrame({"": ["彙總總表"]}).to_excel(
            writer,
            sheet_name=sheet,
            index=False,
            header=False,
            startrow=r,
            startcol=0,
        )
        r += 1
        df_summary.to_excel(writer, sheet_name=sheet, index=False, startrow=r, startcol=0)

    out.seek(0)
    return out.read()


def _label_type_as_pick(type_name: str) -> str:
    t = str(type_name).strip()
    if t == "低空":
        return "低空"
    if t == "高空":
        return "高空"
    if t.upper() == "GM":
        return "GM"
    return t


def show_type_totals_as_text(df_type_total: pd.DataFrame):
    """依儲位類型顯示應作業 / 完成 Line。"""
    st.markdown("### 總揀 / Line 完成概況")
    if df_type_total is None or df_type_total.empty:
        st.caption("（無資料）")
        return

    for _, r in df_type_total.iterrows():
        t = _label_type_as_pick(r.get("儲位類型", ""))
        should_line = int(r.get("應作業Line", 0))
        done_line = int(r.get("實際完成Line", 0))
        undone_line = int(r.get("未完成Line", 0))
        rate = float(r.get("Line完成率", 0.0))

        st.markdown(f"**{t}**")
        st.markdown(
            f"應作業 Line：**{should_line:,}**　｜　"
            f"實際完成 Line：**{done_line:,}**　｜　"
            f"未完成 Line：**{undone_line:,}**　｜　"
            f"完成率：**{rate:.1%}**"
        )


# =========================
# UI
# =========================
inject_logistics_theme()
set_page(
    "報工稼動｜零散總揀",
    icon="🎯",
    subtitle="多檔批次｜成箱/零散（或ALL）｜排除儲位｜回填儲位類型｜應作業Line / 實際完成Line",
)

card_open("🎯 零散總揀｜Line 完成統計")

batch_files = st.file_uploader(
    "上傳【批次明細】（可多檔；至少含欄位：儲位；需有可辨識的應揀/實揀欄位）",
    type=["xlsx", "xlsm", "xltx", "xltm", "xls", "xlsb", "csv", "txt"],
    accept_multiple_files=True,
)

map_file = st.file_uploader(
    "上傳【儲位棚別明細】（需含欄位：儲位、儲位類型）",
    type=["xlsx", "xlsm", "xltx", "xltm", "xls", "xlsb", "csv", "txt"],
    accept_multiple_files=False,
)

st.markdown("---")

if (not batch_files) or (map_file is None):
    st.info("請先上傳『批次明細（可多檔）』與『儲位棚別明細』。")
    card_close()
    st.stop()

run = st.button("開始產出", type="primary")
if not run:
    card_close()
    st.stop()

# 讀取 map
try:
    df_map = read_excel_or_csv(map_file)
    df_map.columns = [str(c).strip() for c in df_map.columns]
except Exception as e:
    st.error(f"讀取『儲位棚別明細』失敗：{e}")
    card_close()
    st.stop()

for c in ["儲位", "儲位類型"]:
    if c not in df_map.columns:
        st.error(f"儲位棚別明細缺少欄位：{c}")
        card_close()
        st.stop()

summary_rows: List[dict] = []
detail_frames: List[pd.DataFrame] = []
ok, fail = 0, 0

for up in batch_files:
    base = os.path.basename(up.name)
    name_noext = os.path.splitext(base)[0]

    try:
        df_raw = read_excel_or_csv(up)
        df_raw.columns = [str(c).strip() for c in df_raw.columns]
    except Exception as e:
        summary_rows.append(
            {
                "來源檔名": name_noext,
                "子集": "讀檔失敗",
                "分組鍵": "無",
                "應作業Line": 0,
                "實際完成Line": 0,
                "未完成Line": 0,
                "Line完成率": 0.0,
                "應揀欄位": "無",
                "實揀欄位": "無",
                "備註": str(e),
            }
        )
        fail += 1
        continue

    if "儲位" not in df_raw.columns:
        summary_rows.append(
            {
                "來源檔名": name_noext,
                "子集": "缺欄位",
                "分組鍵": "無",
                "應作業Line": 0,
                "實際完成Line": 0,
                "未完成Line": 0,
                "Line完成率": 0.0,
                "應揀欄位": "無",
                "實揀欄位": "無",
                "備註": "缺少儲位欄位",
            }
        )
        fail += 1
        continue

    if "商品" not in df_raw.columns:
        df_raw[PRODUCT_FALLBACK_COL] = 1

    has_unit_col = "計量單位" in df_raw.columns
    masks = (
        [
            ("成箱", unit_mask_equal_2(df_raw["計量單位"])),
            ("零散", unit_mask_contains_3_or_6(df_raw["計量單位"])),
        ]
        if has_unit_col
        else [("ALL", pd.Series([True] * len(df_raw), index=df_raw.index))]
    )

    any_ok = False
    for tag, mask in masks:
        try:
            (
                tag,
                pivot2,
                total_count,
                group_keys,
                expected_col,
                actual_col,
            ) = process_subset(df_raw, df_map, tag, mask)
        except Exception as e:
            summary_rows.append(
                {
                    "來源檔名": name_noext,
                    "子集": tag,
                    "分組鍵": "無",
                    "應作業Line": 0,
                    "實際完成Line": 0,
                    "未完成Line": 0,
                    "Line完成率": 0.0,
                    "應揀欄位": "無",
                    "實揀欄位": "無",
                    "備註": str(e),
                }
            )
            continue

        if pivot2 is None:
            summary_rows.append(
                {
                    "來源檔名": name_noext,
                    "子集": tag,
                    "分組鍵": "無",
                    "應作業Line": 0,
                    "實際完成Line": 0,
                    "未完成Line": 0,
                    "Line完成率": 0.0,
                    "應揀欄位": "無",
                    "實揀欄位": "無",
                    "備註": "篩選後無資料",
                }
            )
            continue

        grp_desc = " × ".join(group_keys)

        df_detail = pivot2.copy()
        df_detail.insert(0, "來源檔名", name_noext)
        df_detail.insert(1, "子集", tag)
        df_detail["應揀欄位"] = expected_col
        df_detail["實揀欄位"] = actual_col
        detail_frames.append(df_detail)

        should_line = int(pivot2["應作業Line"].sum())
        done_line = int(pivot2["實際完成Line"].sum())
        undone_line = int(pivot2["未完成Line"].sum())
        line_rate = done_line / should_line if should_line else 0.0

        summary_rows.append(
            {
                "來源檔名": name_noext,
                "子集": tag,
                "分組鍵": grp_desc,
                "應作業Line": should_line,
                "實際完成Line": done_line,
                "未完成Line": undone_line,
                "Line完成率": line_rate,
                "應揀欄位": expected_col,
                "實揀欄位": actual_col,
                "備註": "",
            }
        )
        any_ok = True

    if any_ok:
        ok += 1
    else:
        fail += 1

summary_columns = [
    "來源檔名",
    "子集",
    "分組鍵",
    "應作業Line",
    "實際完成Line",
    "未完成Line",
    "Line完成率",
    "應揀欄位",
    "實揀欄位",
    "備註",
]
df_summary = (
    pd.DataFrame(summary_rows)
    if summary_rows
    else pd.DataFrame(columns=summary_columns)
)
if not df_summary.empty:
    df_summary = df_summary.sort_values(
        ["來源檔名", "子集"], kind="mergesort"
    ).reset_index(drop=True)

if detail_frames:
    df_detail_all = pd.concat(detail_frames, ignore_index=True)
    base_cols = ["來源檔名", "子集", "儲位類型"]
    cols = (
        base_cols
        + (["揀貨批次號"] if "揀貨批次號" in df_detail_all.columns else [])
        + [
            "應作業Line",
            "實際完成Line",
            "未完成Line",
            "Line完成率",
            "應揀PCS",
            "實際揀PCS",
            "應揀欄位",
            "實揀欄位",
        ]
    )
    others = [c for c in df_detail_all.columns if c not in cols]
    df_detail_all = df_detail_all[cols + others]
else:
    df_detail_all = pd.DataFrame(
        columns=[
            "來源檔名",
            "子集",
            "儲位類型",
            "應作業Line",
            "實際完成Line",
            "未完成Line",
            "Line完成率",
            "應揀PCS",
            "實際揀PCS",
            "應揀欄位",
            "實揀欄位",
        ]
    )

# 依儲位類型加總 Line 與 PCS
if (
    not df_detail_all.empty
    and "儲位類型" in df_detail_all.columns
    and "應作業Line" in df_detail_all.columns
):
    df_type_total = (
        df_detail_all.groupby("儲位類型", dropna=False)
        .agg(
            應作業Line=("應作業Line", "sum"),
            實際完成Line=("實際完成Line", "sum"),
            未完成Line=("未完成Line", "sum"),
            應揀PCS=("應揀PCS", "sum"),
            實際揀PCS=("實際揀PCS", "sum"),
        )
        .reset_index()
    )
    df_type_total["Line完成率"] = np.where(
        df_type_total["應作業Line"] > 0,
        df_type_total["實際完成Line"] / df_type_total["應作業Line"],
        0.0,
    )
    df_type_total = df_type_total.sort_values(
        "應作業Line", ascending=False, kind="mergesort"
    ).reset_index(drop=True)
else:
    df_type_total = pd.DataFrame(
        columns=[
            "儲位類型",
            "應作業Line",
            "實際完成Line",
            "未完成Line",
            "Line完成率",
            "應揀PCS",
            "實際揀PCS",
        ]
    )

show_type_totals_as_text(df_type_total)

st.markdown("### 明細表（合併）")
st.dataframe(df_detail_all, use_container_width=True, hide_index=True)

st.markdown("### 彙總總表")
st.dataframe(df_summary, use_container_width=True, hide_index=True)

st.caption(f"成功：{ok} 檔；失敗：{fail} 檔")

try:
    out_bytes = build_single_sheet_excel_bytes(
        df_type_total, df_detail_all, df_summary
    )
    out_name = "零散總揀_Line完成統計.xlsx"
except Exception as e:
    st.error(f"輸出失敗：{e}")
    card_close()
    st.stop()

st.download_button(
    "⬇️ 下載輸出 Excel（單一工作表）",
    data=out_bytes,
    file_name=out_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

card_close()
