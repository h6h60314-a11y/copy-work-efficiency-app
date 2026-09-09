# pages/13_庫存訂單實出量分析.py
import io
import os
import re
from typing import Tuple, Dict, List

import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# -----------------------------
# Page setup
# -----------------------------
st.set_page_config(page_title="庫存訂單實出量分析", page_icon="📦", layout="wide")
inject_logistics_theme()


# -----------------------------
# Requirements
# -----------------------------
REQUIRED_COLS = [
    "箱類型", "packqty", "入數",
    "buyersreference", "BOXTYPE",
    "externorderkey", "SKU", "boxid"
]
BUYERS_OK = {"GSO", "GCOR"}


# -----------------------------
# Column mapping (auto)
# 你可以繼續加同義欄位，越完整越不會讀不到
# key=標準欄名, values=可能出現的同義欄名（大小寫不拘、可含空白/底線）
# -----------------------------
COLUMN_SYNONYMS: Dict[str, List[str]] = {
    "箱類型": ["箱類型", "箱型", "箱别", "箱別", "boxtype_name", "carton_type", "箱種", "箱种"],
    "packqty": ["packqty", "pack_qty", "pack quantity", "數量", "数量", "pcs", "qty", "pack"],
    "入數": ["入數", "入数", "入數量", "入数量", "innum", "in_qty", "unitspercase", "units_per_case", "casepack", "case_pack"],
    "buyersreference": ["buyersreference", "buyers_reference", "buyer reference", "buyerref", "order_type", "單別", "单别", "refer", "buyers ref"],
    "BOXTYPE": ["boxtype", "box_type", "箱別型態", "箱型態", "箱别型态", "箱類型代碼", "箱类型代码"],
    "externorderkey": ["externorderkey", "extern_order_key", "orderkey", "order_key", "order id", "order_id", "訂單號", "订单号", "單號", "单号", "externorder"],
    "SKU": ["sku", "item", "itemcode", "item_code", "商品", "商品碼", "商品码", "品號", "品号", "料號", "料号"],
    "boxid": ["boxid", "box_id", "box id", "箱號", "箱号", "箱碼", "箱码", "cartonid", "carton_id", "containerid", "container_id"],
}


def _normalize_col(s: str) -> str:
    """把欄名統一成：小寫 + 去空白 + 移除特殊字元"""
    s = str(s).strip()
    s = s.replace("\u3000", " ")  # 全形空白
    s = re.sub(r"\s+", "", s)     # 移除所有空白
    s = s.replace("-", "_").replace(".", "_").replace("/", "_")
    s = re.sub(r"[^0-9a-zA-Z_\u4e00-\u9fff]", "", s)  # 保留中英數與底線
    return s.lower()


def _apply_column_mapping(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    依 COLUMN_SYNONYMS 自動把同義欄名 rename 成標準欄名
    回傳：新df + 命中的對照表（原欄名 -> 標準欄名）
    """
    df = df.copy()
    orig_cols = list(df.columns)

    norm_to_orig = {}
    for c in orig_cols:
        norm_to_orig[_normalize_col(c)] = c

    rename_map = {}  # orig -> std
    for std, syns in COLUMN_SYNONYMS.items():
        for syn in syns:
            key = _normalize_col(syn)
            if key in norm_to_orig:
                rename_map[norm_to_orig[key]] = std
                break

    if rename_map:
        df = df.rename(columns=rename_map)

    return df, rename_map


def _is_provider_fake_xls(raw: bytes) -> bool:
    head = raw[:2048].upper()
    return (b"PROVIDER" in head) or (b"<HTML" in head) or (b"<TABLE" in head)


def _read_html_from_bytes(raw: bytes) -> pd.DataFrame:
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
    sep = None
    if "\t" in sample:
        sep = "\t"
    elif "," in sample:
        sep = ","
    elif "|" in sample:
        sep = "|"

    if sep:
        return pd.read_csv(io.StringIO(content), sep=sep, engine="python")
    return pd.read_csv(io.StringIO(content), sep=r"\s+", engine="python")


def _read_any(uploaded) -> Tuple[pd.DataFrame, str]:
    name = uploaded.name
    ext = os.path.splitext(name)[1].lower()
    raw = uploaded.getvalue()

    if ext == ".txt":
        df = _read_txt_to_df(raw)
        return df, name

    if ext == ".csv":
        df = pd.read_csv(io.BytesIO(raw))
        return df, name

    if ext in (".html", ".htm"):
        df = _read_html_from_bytes(raw)
        return df, name

    if ext in (".xlsx", ".xlsm"):
        df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
        return df, name

    if ext == ".xls":
        if _is_provider_fake_xls(raw):
            df = _read_html_from_bytes(raw)
            return df, name
        try:
            df = pd.read_excel(io.BytesIO(raw), engine="xlrd")
            return df, name
        except Exception:
            df = _read_html_from_bytes(raw)
            return df, name

    # fallback
    try:
        df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
        return df, name
    except Exception:
        df = _read_html_from_bytes(raw)
        return df, name


def _validate_cols(df: pd.DataFrame) -> List[str]:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    return missing


def _to_number(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in ("packqty", "入數", "BOXTYPE"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _compute(df: pd.DataFrame) -> dict:
    df = df.copy()

    # 排除「箱類型」含「站所」
    df = df[~df["箱類型"].astype(str).str.contains("站所", na=False)].copy()

    # 新增「出貨單位數量」
    if "出貨單位數量" not in df.columns:
        try:
            idx = df.columns.get_loc("入數")
            df.insert(idx + 1, "出貨單位數量", 0)
        except Exception:
            df["出貨單位數量"] = 0

    df["出貨單位數量"] = df["packqty"] / df["入數"]

    mask_base = df["buyersreference"].astype(str).isin(BUYERS_OK)

    mask0 = mask_base & (df["BOXTYPE"] == 0)
    total_packqty_box0 = df.loc[mask0, "packqty"].sum()

    # BOXTYPE = 1 的成箱計算
    # 1) 出貨單位數量 = 1：計 packqty
    mask1_eq = (
        mask_base
        & (df["BOXTYPE"] == 1)
        & (df["出貨單位數量"] == 1)
    )
    total_packqty_box1_eq = df.loc[mask1_eq, "packqty"].sum()

    # 2) 出貨單位數量 != 1：
    #    - 若為整數（例如 2、3、4），計 出貨單位數量 = packqty / 入數
    #    - 若為小數（例如 1.6、0.5、2.5），改計 packqty
    mask1_neq = (
        mask_base
        & (df["BOXTYPE"] == 1)
        & (df["出貨單位數量"] != 1)
    )

    units = df["出貨單位數量"]
    mask1_integer = mask1_neq & units.notna() & (units % 1 == 0)
    mask1_decimal = mask1_neq & units.notna() & (units % 1 != 0)

    total_units_box1_integer = df.loc[mask1_integer, "出貨單位數量"].sum()
    total_packqty_box1_decimal = df.loc[mask1_decimal, "packqty"].sum()

    total_combined = (
        total_packqty_box1_eq
        + total_units_box1_integer
        + total_packqty_box1_decimal
    )

    filtered = df[mask_base].copy()
    pivot = (
        filtered
        .pivot_table(index=["externorderkey", "SKU"], aggfunc="size")
        .reset_index(name="count")
    )
    total_groups = int(pivot.shape[0])

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
    subtitle="支援 TXT / 假xls(PROVIDER)｜欄位自動對照｜排除箱類型=站所｜實際出貨量(PTL)｜混庫出貨件數",
)

card_open("📌 上傳明細檔")
uploaded = st.file_uploader(
    "請上傳明細檔（XLSX / XLSM / XLS / CSV / HTML / TXT）",
    type=["xlsx", "xlsm", "xls", "csv", "html", "htm", "txt"],
)
st.caption("必要欄位：箱類型、packqty、入數、buyersreference、BOXTYPE、externorderkey、SKU、boxid（可同義欄名自動對照）")
card_close()

if not uploaded:
    st.stop()

progress = st.progress(0, text="資料讀取中…")
with st.spinner("資料讀取中…請稍候（檔案越大越久）"):
    progress.progress(15, text="資料讀取中…（讀取檔案）")
    df, src_name = _read_any(uploaded)

    progress.progress(35, text="資料讀取中…（欄位清理/自動對照）")
    df.columns = [str(c).strip() for c in df.columns]
    df, hit_map = _apply_column_mapping(df)

    progress.progress(55, text="資料讀取中…（欄位檢查）")
    missing = _validate_cols(df)

    # ✅ 缺欄位：不要讓整頁爆掉，直接顯示提示 + 欄位清單
    if missing:
        progress.empty()
        st.error(f"缺少必要欄位：{missing}")

        if hit_map:
            st.info("已自動對照（原欄名 → 標準欄名）：")
            st.write(hit_map)

        st.markdown("#### 你上傳檔案目前的欄位（請對照是否名稱不同/有同義欄位）")
        st.dataframe(pd.DataFrame({"columns": list(df.columns)}), use_container_width=True, height=300)

        st.stop()

    progress.progress(70, text="資料讀取中…（資料轉型）")
    df = _to_number(df)

    progress.progress(90, text="資料讀取中…（計算中）")
    result = _compute(df)

    progress.progress(100, text="完成 ✅")

progress.empty()
st.success(f"已讀取：{src_name}（{len(result['df']):,} 筆 / {len(result['df'].columns)} 欄）")

# Metrics
left, right = st.columns([1, 1], gap="large")

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

st.markdown("### 明細預覽（含：出貨單位數量）")
st.dataframe(result["df"].head(200), use_container_width=True, height=420)

# Export
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
