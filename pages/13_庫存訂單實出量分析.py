# pages/13_庫存訂單實出量分析.py
import io
import os
import re
import tempfile
from typing import Tuple, Optional

import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="庫存訂單實出量分析", page_icon="📦", layout="wide")
inject_logistics_theme()


# -----------------------------
# Helpers
# -----------------------------
REQUIRED_COLS = [
    "箱類型", "packqty", "入數",
    "buyersreference", "BOXTYPE",
    "externorderkey", "SKU", "boxid"
]

BUYERS_OK = {"GSO", "GCOR"}


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _is_provider_fake_xls(raw: bytes) -> bool:
    # 你遇到的錯誤：Expected BOF record; found b'PROVIDER'
    # 通常是 HTML table 或文字被包成 .xls
    head = raw[:2048].upper()
    return (b"PROVIDER" in head) or (b"<HTML" in head) or (b"<TABLE" in head)


def _read_html_from_bytes(raw: bytes) -> pd.DataFrame:
    # 用 pandas 直接吃 HTML
    # 先嘗試 utf-8，再退回 big5/latin1
    for enc in ("utf-8", "utf-8-sig", "big5", "cp950", "latin1"):
        try:
            text = raw.decode(enc, errors="ignore")
            tables = pd.read_html(io.StringIO(text))
            if tables:
                return tables[0]
        except Exception:
            continue
    raise ValueError("HTML 解析失敗（可能不是表格格式或內容不完整）")


def _read_txt_to_df(raw: bytes) -> pd.DataFrame:
    """
    TXT 可能是：
    - Tab 分隔
    - 逗號分隔
    - 管線 | 分隔
    - 固定寬度（比較少）
    這邊用「自動偵測分隔符」策略。
    """
    # 嘗試多種編碼
    content = None
    for enc in ("utf-8", "utf-8-sig", "cp950", "big5", "latin1"):
        try:
            content = raw.decode(enc)
            break
        except Exception:
            continue
    if content is None:
        content = raw.decode("latin1", errors="ignore")

    sample = content[:5000]

    # 分隔符偵測：tab > comma > pipe
    sep = None
    if "\t" in sample:
        sep = "\t"
    elif "," in sample:
        sep = ","
    elif "|" in sample:
        sep = "|"

    if sep:
        return pd.read_csv(io.StringIO(content), sep=sep, engine="python")
    # 沒偵測到就用自動空白分隔
    return pd.read_csv(io.StringIO(content), sep=r"\s+", engine="python")


def _read_any(uploaded) -> Tuple[pd.DataFrame, str]:
    """
    回傳 (df, source_name)
    """
    name = uploaded.name
    ext = os.path.splitext(name)[1].lower()
    raw = uploaded.getvalue()

    # TXT -> DF
    if ext == ".txt":
        df = _read_txt_to_df(raw)
        return _norm_cols(df), name

    # CSV
    if ext == ".csv":
        df = pd.read_csv(io.BytesIO(raw))
        return _norm_cols(df), name

    # HTML/HTM
    if ext in (".html", ".htm"):
        df = _read_html_from_bytes(raw)
        return _norm_cols(df), name

    # XLSX/XLSM
    if ext in (".xlsx", ".xlsm"):
        df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
        return _norm_cols(df), name

    # XLS：可能真 xls，也可能假 xls(HTML)
    if ext == ".xls":
        if _is_provider_fake_xls(raw):
            df = _read_html_from_bytes(raw)
            return _norm_cols(df), name
        # 真 xls
        try:
            df = pd.read_excel(io.BytesIO(raw), engine="xlrd")
            return _norm_cols(df), name
        except Exception:
            # 最後再嘗試當 html
            df = _read_html_from_bytes(raw)
            return _norm_cols(df), name

    # 其他：嘗試用 read_excel(openpyxl) / read_html
    try:
        df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
        return _norm_cols(df), name
    except Exception:
        df = _read_html_from_bytes(raw)
        return _norm_cols(df), name


def _validate_cols(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}")


def _to_number(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("packqty", "入數", "BOXTYPE"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _compute(df: pd.DataFrame) -> dict:
    df = df.copy()

    # 排除「箱類型」含「站所」
    df = df[~df["箱類型"].astype(str).str.contains("站所", na=False)].copy()

    # 新增「出貨單位數量」
    if "出貨單位數量" not in df.columns:
        # 放在 入數 後面（若存在）
        try:
            idx = df.columns.get_loc("入數")
            df.insert(idx + 1, "出貨單位數量", 0)
        except Exception:
            df["出貨單位數量"] = 0

    df["出貨單位數量"] = df["packqty"] / df["入數"]

    # A. 實際出貨量（PTL）
    mask_base = df["buyersreference"].isin(BUYERS_OK)

    mask0 = mask_base & (df["BOXTYPE"] == 0)
    total_packqty_box0 = df.loc[mask0, "packqty"].sum()

    mask1_eq = mask_base & (df["BOXTYPE"] == 1) & (df["出貨單位數量"] == 1)
    total_packqty_box1_eq = df.loc[mask1_eq, "packqty"].sum()

    mask1_neq = mask_base & (df["BOXTYPE"] == 1) & (df["出貨單位數量"] != 1)
    total_units_box1_neq = df.loc[mask1_neq, "出貨單位數量"].sum()

    total_combined = total_packqty_box1_eq + total_units_box1_neq

    filtered = df[mask_base].copy()
    # 訂單筆數：externorderkey + SKU 組合
    pivot = (
        filtered
        .pivot_table(index=["externorderkey", "SKU"], aggfunc="size")
        .reset_index(name="count")
    )
    total_groups = int(pivot.shape[0])

    # B. 混庫出貨件數（boxid 不重複）
    df_box0 = df[df["BOXTYPE"] == 0]
    df_box1 = df[df["BOXTYPE"] == 1]
    count_box0 = int(df_box0["boxid"].nunique())
    count_box1 = int(df_box1["boxid"].nunique())

    return {
        "df": df,
        "實際出貨量PTL_訂單筆數": total_groups,
        "實際出貨量_庫存零散PCS": float(total_packqty_box0),
        "實際出貨量_庫存成箱PCS": float(total_combined),
        "混庫零散出貨件數": count_box0,
        "混庫成箱出貨件數": count_box1,
    }


def _fmt_num(x) -> str:
    try:
        if x is None:
            return "-"
        if float(x).is_integer():
            return f"{int(x):,}"
        return f"{float(x):,.2f}"
    except Exception:
        return str(x)


# -----------------------------
# UI
# -----------------------------
set_page(
    "庫存訂單實出量分析",
    icon="📦",
    subtitle="支援 TXT 先轉成 Excel 再計算｜排除箱類型=站所｜實際出貨量(PTL)｜混庫出貨件數",
)

card_open("📌 上傳明細檔")
uploaded = st.file_uploader(
    "請上傳明細檔（XLSX / XLSM / XLS / CSV / HTML / TXT）",
    type=["xlsx", "xlsm", "xls", "csv", "html", "htm", "txt"],
)

st.caption("必要欄位：箱類型、packqty、入數、buyersreference、BOXTYPE、externorderkey、SKU、boxid")
card_close()

if not uploaded:
    st.stop()

# ✅ 這裡就是你要的「資料讀取中」
progress = st.progress(0, text="資料讀取中…")
with st.spinner("資料讀取中…請稍候（檔案越大越久）"):
    # 1) 讀取
    progress.progress(15, text="資料讀取中…（讀取檔案）")
    df, src_name = _read_any(uploaded)

    # 2) 欄位檢查
    progress.progress(35, text="資料讀取中…（欄位檢查）")
    _validate_cols(df)

    # 3) 轉數字 + 清理
    progress.progress(55, text="資料讀取中…（資料清理/轉型）")
    df = _to_number(df)

    # 4) 計算
    progress.progress(80, text="資料讀取中…（計算中）")
    result = _compute(df)

    progress.progress(100, text="完成 ✅")

# 讀完就把進度條收掉（畫面更乾淨）
progress.empty()

st.success(f"已讀取：{src_name}（{len(result['df']):,} 筆 / {len(result['df'].columns)} 欄）")

# -----------------------------
# Metrics
# -----------------------------
left, mid, right = st.columns([1.2, 0.12, 1.2])

with left:
    st.markdown("### 實際出貨量（PTL）")
    st.metric("訂單筆數", _fmt_num(result["實際出貨量PTL_訂單筆數"]))
    st.metric("庫存零散 PCS", _fmt_num(result["實際出貨量_庫存零散PCS"]))
    st.metric("庫存成箱 PCS", _fmt_num(result["實際出貨量_庫存成箱PCS"]))

with right:
    st.markdown("### 混庫出貨件數")
    st.metric("混庫零散出貨件數", _fmt_num(result["混庫零散出貨件數"]))
    st.metric("混庫成箱出貨件數", _fmt_num(result["混庫成箱出貨件數"]))

st.divider()

# -----------------------------
# Preview & Export
# -----------------------------
st.markdown("### 明細預覽（含：出貨單位數量）")
st.dataframe(result["df"].head(200), use_container_width=True, height=420)

# 匯出
out_df = result["df"].copy()
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as writer:
    out_df.to_excel(writer, index=False, sheet_name="明細")
buf.seek(0)

st.download_button(
    "⬇️ 下載處理後明細（Excel）",
    data=buf.getvalue(),
    file_name="庫存訂單實出量分析_明細.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
