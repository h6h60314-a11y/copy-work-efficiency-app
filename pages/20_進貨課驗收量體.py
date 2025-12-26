# pages/20_進貨課驗收量體.py
# -*- coding: utf-8 -*-
"""
功能：
1) 只保留欄位「到」=「QC」的資料（多工作表支援）
2) 計算不重複的商品數（各工作表與全檔合計）
3) 輸出新檔：各表過濾後明細 +「過濾統計」+「唯一商品統計」

部署版使用方式：
- 上傳 Excel/CSV/TXT → 產出 → 下載
"""

from __future__ import annotations

import os
from io import BytesIO
from typing import Dict, Tuple, Optional, List

import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

pd.options.display.max_columns = 200

# 你常見的商品欄位名稱候選（依序嘗試）
PRODUCT_COL_CANDIDATES = ["商品", "商品代號", "商品編號", "品號", "品名", "品號品名"]


def _safe_sheet_name(name: str) -> str:
    n = str(name).replace("/", "_").replace("\\", "_").strip()
    return (n[:31] if len(n) > 31 else n) or "Sheet"


def find_product_col(columns) -> Optional[str]:
    cols = [str(c).strip() for c in columns]
    for cand in PRODUCT_COL_CANDIDATES:
        if cand in cols:
            return cand
    # 寬鬆：找含「商品」「品號」關鍵字
    for c in cols:
        if ("商品" in c) or ("品號" in c):
            return c
    return None


def _read_excel_sheets_from_bytes(file_bytes: bytes, ext: str) -> Dict[str, pd.DataFrame]:
    """
    回傳：{sheet_name: DataFrame}
    """
    bio = BytesIO(file_bytes)

    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        try:
            return pd.read_excel(bio, sheet_name=None, engine="openpyxl")
        except Exception:
            bio.seek(0)
            return pd.read_excel(bio, sheet_name=None)

    if ext == ".xls":
        # 部署環境常見沒有 xlrd；給清楚提示
        try:
            return pd.read_excel(bio, sheet_name=None, engine="xlrd")
        except Exception as e:
            raise RuntimeError("目前環境可能未安裝 xlrd，導致 .xls 無法讀取；請先另存為 .xlsx 再上傳。") from e

    # 其他就先當 excel 試
    try:
        return pd.read_excel(bio, sheet_name=None, engine="openpyxl")
    except Exception:
        bio.seek(0)
        return pd.read_excel(bio, sheet_name=None)


def _read_csv_from_bytes_auto(file_bytes: bytes) -> pd.DataFrame:
    """
    不顯示編碼選擇，改用自動嘗試常見編碼。
    """
    last_err = None
    for enc in ("utf-8-sig", "utf-8", "cp950", "big5"):
        try:
            return pd.read_csv(BytesIO(file_bytes), encoding=enc, low_memory=False)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"CSV/TXT 讀取失敗，已嘗試 utf-8-sig/utf-8/cp950/big5：{last_err}")


def process_tables(
    tables: Dict[str, pd.DataFrame]
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame, pd.DataFrame, dict]:
    """
    tables: {sheet_name: df}
    回傳：
      filtered_tables: {sheet_name: filtered_df}
      summary_df: 過濾統計
      per_sheet_df: 唯一商品統計
      stats: dict(total_before, total_after, overall_unique_products)
    """
    filtered: Dict[str, pd.DataFrame] = {}

    total_before = 0
    total_after = 0

    per_sheet_unique: List[dict] = []
    all_products: List[pd.Series] = []

    for name, df in tables.items():
        df = df.copy()
        df.columns = [str(c).strip() for c in df.columns]

        # 沒有「到」欄位：當作 0 筆（仍輸出同欄位的空表）
        if "到" not in df.columns:
            filtered[name] = df.iloc[0:0].copy()
            per_sheet_unique.append(
                {
                    "工作表": _safe_sheet_name(name),
                    "使用商品欄位": "",
                    "原始筆數": int(len(df)),
                    "保留筆數(到=QC)": 0,
                    "唯一商品數": 0,
                }
            )
            continue

        total_before += len(df)

        mask = df["到"].astype(str).str.strip().str.upper().eq("QC")
        out_df = df.loc[mask].reset_index(drop=True)

        total_after += len(out_df)
        filtered[name] = out_df

        prod_col = find_product_col(out_df.columns)
        if prod_col and not out_df.empty:
            s = out_df[prod_col].astype(str).str.strip()
            uniq_cnt = int(s.nunique(dropna=True))
            all_products.append(s)
        else:
            uniq_cnt = 0

        per_sheet_unique.append(
            {
                "工作表": _safe_sheet_name(name),
                "使用商品欄位": prod_col or "",
                "原始筆數": int(len(df)),
                "保留筆數(到=QC)": int(len(out_df)),
                "唯一商品數": int(uniq_cnt),
            }
        )

    if all_products:
        overall_unique_products = int(pd.concat(all_products, ignore_index=True).nunique(dropna=True))
    else:
        overall_unique_products = 0

    summary_df = pd.DataFrame(
        {
            "項目": ["原始筆數", "保留筆數(到=QC)", "刪除筆數", "全檔唯一商品總數"],
            "數量": [
                int(total_before),
                int(total_after),
                int(total_before - total_after),
                int(overall_unique_products),
            ],
        }
    )

    per_sheet_df = pd.DataFrame(per_sheet_unique)[
        ["工作表", "使用商品欄位", "原始筆數", "保留筆數(到=QC)", "唯一商品數"]
    ]

    stats = {
        "total_before": int(total_before),
        "total_after": int(total_after),  # ITEM
        "overall_unique_products": int(overall_unique_products),  # SKU
    }
    return filtered, summary_df, per_sheet_df, stats


def build_output_excel_bytes(
    original_tables: Dict[str, pd.DataFrame],
    filtered_tables: Dict[str, pd.DataFrame],
    summary_df: pd.DataFrame,
    per_sheet_df: pd.DataFrame,
) -> bytes:
    """
    產出 Excel bytes（各sheet過濾後 + 過濾統計 + 唯一商品統計）
    """
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        for name, fdf in filtered_tables.items():
            safe_name = _safe_sheet_name(name)

            orig_cols = list(original_tables[name].columns) if name in original_tables else list(fdf.columns)
            if fdf.empty:
                pd.DataFrame(columns=orig_cols).to_excel(writer, sheet_name=safe_name, index=False)
            else:
                fdf.to_excel(writer, sheet_name=safe_name, index=False)

        summary_df.to_excel(writer, sheet_name="過濾統計", index=False)
        per_sheet_df.to_excel(writer, sheet_name="唯一商品統計", index=False)

    out.seek(0)
    return out.read()


def _kpi_stack(title: str, value: int):
    st.markdown(
        f"""
<div style="
  padding: 10px 12px;
  border: 1px solid rgba(15,23,42,0.12);
  border-radius: 12px;
  background: rgba(255,255,255,0.75);
  margin: 8px 0;
">
  <div style="font-weight: 850; color: rgba(15,23,42,0.70); font-size: 13px; line-height: 1.2;">
    {title}
  </div>
  <div style="font-weight: 950; color: rgba(15,23,42,0.92); font-size: 22px; margin-top: 6px; line-height: 1;">
    {value:,}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# =========================
# Page UI
# =========================
inject_logistics_theme()
set_page("進貨課｜驗收量體", icon="✅", subtitle="只保留「到=QC」｜SKU(唯一商品)｜ITEM(筆數)｜輸出Excel")

card_open("✅ 驗收量體（到=QC）")

up = st.file_uploader(
    "上傳檔案（Excel / CSV / TXT）",
    type=["xlsx", "xlsm", "xltx", "xltm", "xls", "csv", "txt"],
    accept_multiple_files=False,
)

st.markdown("---")

if up is None:
    st.info("請先上傳檔案。")
    card_close()
    st.stop()

filename = up.name
base, ext = os.path.splitext(filename)
ext = ext.lower()

run = st.button("開始產出", type="primary")  # ✅ 改字

if not run:
    card_close()
    st.stop()

# 1) 讀檔
try:
    file_bytes = up.getvalue()
    if ext in (".csv", ".txt"):
        df = _read_csv_from_bytes_auto(file_bytes)  # ✅ 自動編碼，不顯示選擇
        tables = {"CSV": df}
    else:
        tables = _read_excel_sheets_from_bytes(file_bytes, ext)
except Exception as e:
    st.error(f"讀檔失敗：{e}")
    card_close()
    st.stop()

# 2) 處理
try:
    filtered, summary_df, per_sheet_df, stats = process_tables(tables)
except Exception as e:
    st.error(f"處理失敗：{e}")
    card_close()
    st.stop()

# 3) KPI 直向顯示（你要的樣式）
_kpi_stack("SKU（全檔唯一商品）", stats["overall_unique_products"])
_kpi_stack("ITEM（到=QC 筆數）", stats["total_after"])
_kpi_stack("原始總筆數", stats["total_before"])

st.markdown("### 過濾統計")
st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.markdown("### 唯一商品統計（逐表）")
st.dataframe(per_sheet_df, use_container_width=True, hide_index=True)

with st.expander("🔎 預覽：過濾後明細（每張表前 200 筆）", expanded=False):
    for sheet_name, df in filtered.items():
        st.markdown(f"**{_safe_sheet_name(sheet_name)}**（{len(df):,} 筆）")
        st.dataframe(df.head(200), use_container_width=True, hide_index=True)

# 4) 產出 Excel
try:
    out_bytes = build_output_excel_bytes(tables, filtered, summary_df, per_sheet_df)
except Exception as e:
    st.error(f"寫檔失敗：{e}")
    card_close()
    st.stop()

out_name = f"{base}_只保留到QC.xlsx"
st.download_button(
    "⬇️ 下載輸出 Excel",
    data=out_bytes,
    file_name=out_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

card_close()
