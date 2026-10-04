# -*- coding: utf-8 -*-
"""
35_報工稼動 | 揀貨成箱

計算規則
1. 僅「成箱箱號」有值的資料視為成箱作業。
2. Line = 不重複的「儲位 + 商品」。同一儲位 2 個不同商品 = 2 Line。
3. 同一 Line 內，只要任一筆「原始配庫存量 != 數量」，該 Line 即為未完成。
4. 完成 Line = 成箱 Line - 未完成 Line。
5. 應作業 PCS：以「原始配庫存量」套用既有成箱 PCS 換算邏輯。
6. 實際作業 PCS：以「數量」套用既有成箱 PCS 換算邏輯。
7. 支援一次選擇多個檔案，並提供各檔與合併彙總。
"""

from __future__ import annotations

import io
import os
import re
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st

try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close
except Exception:
    # 讓此頁在沒有 common_ui 時仍可單獨執行
    def inject_logistics_theme():
        return None

    def set_page(title: str, icon: str = "", subtitle: str = ""):
        st.title(f"{icon} {title}".strip())
        if subtitle:
            st.caption(subtitle)

    def card_open(_title: str):
        st.markdown(f"### {_title}")

    def card_close():
        return None


# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="報工稼動 | 揀貨作業",
    page_icon="📦",
    layout="wide",
)
inject_logistics_theme()


# --------------------------------------------------
# 基本工具
# --------------------------------------------------
def _fmt_qty(x) -> str:
    try:
        v = float(x)
    except Exception:
        return str(x)
    s = f"{v:,.2f}"
    return s[:-3] if s.endswith(".00") else s


def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)


def _clean_text_series(s: pd.Series) -> pd.Series:
    out = s.fillna("").astype(str).str.strip()
    return out.replace({"nan": "", "None": "", "NULL": "", "NaN": "", "<NA>": ""})


def _resolve_col(df: pd.DataFrame, want: str) -> Optional[str]:
    """欄名容錯：忽略欄名前後空白。"""
    if want in df.columns:
        return want
    w = str(want).strip()
    for c in df.columns:
        if str(c).strip() == w:
            return c
    return None


def _read_csv_best_effort(b: bytes) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "big5", "cp950"):
        try:
            return pd.read_csv(io.BytesIO(b), encoding=enc)
        except Exception:
            pass
    return pd.read_csv(io.BytesIO(b), encoding="latin-1")


def _read_html_best_effort(b: bytes) -> pd.DataFrame:
    text = None
    for enc in ("utf-8", "utf-8-sig", "big5", "cp950", "latin-1"):
        try:
            text = b.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = b.decode("utf-8", errors="ignore")

    tables = pd.read_html(text)
    if not tables:
        raise ValueError("HTML 內找不到表格")
    return tables[0]


def _excel_engines_for_ext(ext: str) -> list[str]:
    ext = ext.lower()
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return ["openpyxl"]
    if ext == ".xls":
        return ["xlrd", "openpyxl"]
    if ext == ".xlsb":
        return ["pyxlsb"]
    return []


def _load_dataframe(uploaded_file, key_prefix: str = "") -> tuple[pd.DataFrame, str]:
    """讀取單一上傳檔案；多工作表時可選擇工作表。"""
    name = uploaded_file.name
    ext = Path(name).suffix.lower()
    b = uploaded_file.getvalue()

    if ext == ".csv":
        return _read_csv_best_effort(b), "CSV"
    if ext in (".html", ".htm"):
        return _read_html_best_effort(b), "HTML"

    engines = _excel_engines_for_ext(ext)
    if not engines:
        raise ValueError("不支援的檔案格式，請使用 Excel / CSV / HTML")

    last_err = None
    for eng in engines:
        try:
            xf = pd.ExcelFile(io.BytesIO(b), engine=eng)
            sheet_names = xf.sheet_names
            sheet = sheet_names[0] if sheet_names else 0

            if len(sheet_names) > 1:
                sheet = st.selectbox(
                    f"選擇工作表：{name}",
                    sheet_names,
                    index=0,
                    key=f"{key_prefix}__sheet__{name}__{eng}",
                )

            df = pd.read_excel(io.BytesIO(b), engine=eng, sheet_name=sheet)
            return df, f"Excel({ext}, engine={eng}, sheet={sheet})"
        except Exception as e:
            last_err = e

    # 某些副檔名為 xls 的來源實際內容可能是 HTML
    if ext == ".xls":
        try:
            return _read_html_best_effort(b), "HTML(偽 xls)"
        except Exception:
            pass

    raise ValueError(f"Excel 讀取失敗：{last_err}")


# --------------------------------------------------
# 成箱 PCS 邏輯
# --------------------------------------------------
def _box_pcs_value(qty: pd.Series, ship_in: pd.Series) -> pd.Series:
    """
    沿用既有成箱 PCS 邏輯：
    - 出貨單位數量 = 作業量 / 出貨入數
    - = 1              → 計作業量
    - != 1 且為整數    → 計出貨單位數量
    - != 1 且為小數    → 計作業量

    qty 可分別傳入：
    - 原始配庫存量 → 應作業 PCS
    - 數量         → 實際作業 PCS
    """
    q = pd.to_numeric(qty, errors="coerce").fillna(0.0)
    si = pd.to_numeric(ship_in, errors="coerce")

    units = q / si
    valid = si.notna() & (si != 0) & units.notna()

    # 浮點容錯
    eq1 = valid & ((units - 1).abs() < 1e-9)
    is_integer = valid & (~eq1) & ((units - units.round()).abs() < 1e-9)
    is_decimal = valid & (~eq1) & (~is_integer)

    result = pd.Series(0.0, index=q.index)
    result.loc[eq1] = q.loc[eq1]
    result.loc[is_integer] = units.loc[is_integer]
    result.loc[is_decimal] = q.loc[is_decimal]

    # 出貨入數缺失/0：無法換算時，以原作業量保留，不讓 PCS 遺失
    invalid = ~valid
    result.loc[invalid] = q.loc[invalid]
    return result


# --------------------------------------------------
# 核心計算
# --------------------------------------------------
def _prepare_box_rows(df: pd.DataFrame, source_name: str = "") -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]

    required_names = [
        "成箱箱號",
        "儲位",
        "商品",
        "原始配庫存量",
        "數量",
        "出貨入數",
    ]

    col_map = {name: _resolve_col(out, name) for name in required_names}
    missing = [name for name, col in col_map.items() if col is None]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}")

    # 轉成標準欄名，避免來源欄名前後空白
    rename_map = {col: name for name, col in col_map.items() if col != name}
    if rename_map:
        out = out.rename(columns=rename_map)

    # 僅成箱箱號有值的資料
    box_no = _clean_text_series(out["成箱箱號"])
    out = out.loc[box_no.ne("")].copy()

    if out.empty:
        # 保留計算欄位，方便後續 concat
        out["來源檔名"] = source_name
        out["LineKey"] = ""
        out["Line完成"] = False
        out["應作業PCS計入值"] = 0.0
        out["實際作業PCS計入值"] = 0.0
        return out

    # 文字欄清理
    out["儲位"] = _clean_text_series(out["儲位"])
    out["商品"] = _clean_text_series(out["商品"])

    # 數值欄
    for c in ("原始配庫存量", "數量", "出貨入數"):
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # Line key：同儲位不同商品分開計 Line
    out["LineKey"] = out["儲位"] + "｜" + out["商品"]

    # 每筆完成判斷：原始配庫存量 == 數量
    expected_raw = out["原始配庫存量"].fillna(0.0)
    actual_raw = out["數量"].fillna(0.0)
    out["筆完成"] = (expected_raw - actual_raw).abs() < 1e-9

    # PCS 計入值
    out["應作業PCS計入值"] = _box_pcs_value(out["原始配庫存量"], out["出貨入數"])
    out["實際作業PCS計入值"] = _box_pcs_value(out["數量"], out["出貨入數"])

    # 同一 Line 任一筆不完成，整條 Line 就不完成
    line_complete_map = out.groupby("LineKey", dropna=False)["筆完成"].all()
    out["Line完成"] = out["LineKey"].map(line_complete_map).fillna(False)
    out["來源檔名"] = source_name

    return out


def _line_summary(box_df: pd.DataFrame) -> pd.DataFrame:
    """產出 Line 層級明細。"""
    cols = [
        "來源檔名",
        "儲位",
        "商品",
        "LineKey",
        "Line完成",
        "應作業PCS",
        "實際作業PCS",
        "PCS差異",
        "成箱筆數",
        "成箱箱數",
    ]
    if box_df.empty:
        return pd.DataFrame(columns=cols)

    group_cols = ["來源檔名", "儲位", "商品", "LineKey"]
    line = (
        box_df.groupby(group_cols, dropna=False)
        .agg(
            Line完成=("筆完成", "all"),
            應作業PCS=("應作業PCS計入值", "sum"),
            實際作業PCS=("實際作業PCS計入值", "sum"),
            成箱筆數=("LineKey", "size"),
            成箱箱數=("成箱箱號", "nunique"),
        )
        .reset_index()
    )
    line["PCS差異"] = line["應作業PCS"] - line["實際作業PCS"]
    return line[cols]


def _metrics_from_box_rows(box_df: pd.DataFrame) -> dict:
    if box_df.empty:
        return {
            "成箱Line": 0,
            "完成Line": 0,
            "未完成Line": 0,
            "Line完成率": 0.0,
            "應作業PCS": 0.0,
            "實際作業PCS": 0.0,
            "PCS完成率": 0.0,
            "成箱資料筆數": 0,
            "成箱箱數": 0,
        }

    line_status = box_df.groupby("LineKey", dropna=False)["筆完成"].all()
    total_line = int(line_status.shape[0])
    completed_line = int(line_status.sum())
    unfinished_line = total_line - completed_line

    expected_pcs = float(box_df["應作業PCS計入值"].sum())
    actual_pcs = float(box_df["實際作業PCS計入值"].sum())

    return {
        "成箱Line": total_line,
        "完成Line": completed_line,
        "未完成Line": unfinished_line,
        "Line完成率": (completed_line / total_line) if total_line else 0.0,
        "應作業PCS": expected_pcs,
        "實際作業PCS": actual_pcs,
        "PCS完成率": (actual_pcs / expected_pcs) if expected_pcs else 0.0,
        "成箱資料筆數": int(len(box_df)),
        "成箱箱數": int(box_df["成箱箱號"].nunique()),
    }


def _combined_metrics(all_box_df: pd.DataFrame) -> dict:
    """
    多檔合併後，以「儲位 + 商品」重新去重計 Line。
    同一 Line 若跨檔出現，仍只算 1 Line；任一檔有不完成則整體未完成。
    """
    return _metrics_from_box_rows(all_box_df)


def _download_xlsx(
    summary_df: pd.DataFrame,
    combined_line_df: pd.DataFrame,
    combined_detail_df: pd.DataFrame,
    per_file_line_dfs: list[tuple[str, pd.DataFrame]],
) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="彙總")
        combined_line_df.to_excel(writer, index=False, sheet_name="Line明細_合併")
        combined_detail_df.to_excel(writer, index=False, sheet_name="原始明細_合併")

        used_names = set(writer.book.sheetnames)
        for name, line_df in per_file_line_dfs:
            base = (Path(name).stem + "_Line")[:31]
            safe = base
            n = 1
            while safe in used_names:
                suffix = f"_{n}"
                safe = (base[: 31 - len(suffix)] + suffix)[:31]
                n += 1
            used_names.add(safe)
            line_df.to_excel(writer, index=False, sheet_name=safe)

    return bio.getvalue()



# --------------------------------------------------
# 訂單 Line（成箱箱號空白）
# --------------------------------------------------
ORDER_CANDIDATES = (
    "貨主訂單", "單號", "訂單號", "訂單編號", "訂單號碼", "單據號碼", "單據編號",
    "ORDERNO", "ORDER_NO", "OrderNo", "orderno", "訂單#", "訂單編號#",
    "揀貨單號", "出貨單號", "客戶訂單號碼",
)
PRODUCT_CANDIDATES = ("商品", "商品代號", "品號", "商品編號", "品項")
STORE_CANDIDATES = ("門市代號", "門市", "店號", "StoreID", "storeid", "門市編號")


def _normalize_order_col(value) -> str:
    return (
        str(value)
        .replace(" ", "")
        .replace("　", "")
        .replace("\\n", "")
        .replace("\\r", "")
        .replace("\\t", "")
        .strip()
    )


def _find_order_col(df: pd.DataFrame, candidates, label: str) -> str:
    columns = {_normalize_order_col(column): column for column in df.columns}
    for candidate in candidates:
        match = columns.get(_normalize_order_col(candidate))
        if match is not None:
            return match
    raise KeyError(f"找不到{label}欄位")


def _prepare_order_rows(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    data = df.copy()
    data.columns = [str(column).strip() for column in data.columns]
    qty_col = _find_order_col(data, ("數量",), "數量")
    unit_qty_col = _find_order_col(
        data,
        ("計量單位數量", "原始配庫存量"),
        "計量單位數量或原始配庫存量",
    )
    order_col = _find_order_col(data, ORDER_CANDIDATES, "單號")
    product_col = _find_order_col(data, PRODUCT_CANDIDATES, "商品")
    try:
        store_col = _find_order_col(data, STORE_CANDIDATES, "門市")
    except KeyError:
        store_col = "__ORDER_STORE__"
        data[store_col] = pd.NA

    # 訂單 Line 直接使用原始資料，不承接成箱 Line 的篩選結果。
    qty_numeric = pd.to_numeric(data[qty_col], errors="coerce")
    data = data.loc[qty_numeric.isna() | qty_numeric.ne(0)].copy()

    work = data[[order_col, product_col, store_col, qty_col, unit_qty_col]].copy()
    work.columns = ["ORDER_NO", "PRODUCT", "STORE", "QTY", "UNIT_QTY"]
    for column in ("ORDER_NO", "PRODUCT", "STORE"):
        work[column] = work[column].astype("string").str.strip().replace("", pd.NA)
    work["QTY"] = pd.to_numeric(work["QTY"], errors="coerce")
    work["UNIT_QTY"] = pd.to_numeric(work["UNIT_QTY"], errors="coerce")
    work = work.dropna(subset=["ORDER_NO", "PRODUCT"])
    work.insert(0, "來源檔名", source_name)
    return work


def _order_line_summary(work: pd.DataFrame) -> pd.DataFrame:
    if work.empty:
        return pd.DataFrame(
            columns=["ORDER_NO", "PRODUCT", "QTY", "UNIT_QTY", "DIFF_QTY", "完成狀態"]
        )
    line = (
        work.groupby(["ORDER_NO", "PRODUCT"], as_index=False, dropna=False)
        .agg(QTY=("QTY", "sum"), UNIT_QTY=("UNIT_QTY", "sum"))
    )
    line["DIFF_QTY"] = line["UNIT_QTY"] - line["QTY"]
    line["完成狀態"] = line["DIFF_QTY"].gt(0).map({True: "差異", False: "完成"})
    return line


def _order_metrics(work: pd.DataFrame, line: pd.DataFrame) -> dict:
    total = int(len(line))
    difference = int(line["DIFF_QTY"].gt(0).sum()) if total else 0
    complete = total - difference
    valid_store = work.dropna(subset=["STORE"]) if not work.empty else work
    product_store = valid_store.groupby("PRODUCT")["STORE"].nunique() if not valid_store.empty else pd.Series(dtype=int)
    return {
        "訂單Line": total,
        "完成Line": complete,
        "差異Line": difference,
        "完成率": complete / total if total else 0.0,
        "不重複商品數": int(work["PRODUCT"].nunique()) if not work.empty else 0,
        "品項門市家數合計": int(product_store.sum()),
        "有效明細": int(len(work)),
        "合併重複資料": int(len(work) - total),
    }


def _render_order_line_results(items: list[dict]) -> None:
    results = []
    errors = []
    for item in items:
        try:
            work = _prepare_order_rows(item["raw_df"], item["name"])
            line = _order_line_summary(work)
            results.append((item["name"], work, line, _order_metrics(work, line)))
        except Exception as exc:
            errors.append((item["name"], str(exc)))

    st.markdown("### 🧾 訂單 Line 結果（成箱箱號空白）")
    if not results:
        st.warning("沒有可計算的訂單 Line，請展開下方原因確認來源欄位名稱。")
        if errors:
            with st.expander("檢視無法計算原因"):
                for file_name, message in errors:
                    st.error(f"{file_name}：{message}")
        return

    combined_work = pd.concat([result[1] for result in results], ignore_index=True)
    combined_line = _order_line_summary(combined_work)
    metrics = _order_metrics(combined_work, combined_line)

    columns = st.columns(4)
    columns[0].metric("訂單 Line", _fmt_int(metrics["訂單Line"]))
    columns[1].metric("完成 Line", _fmt_int(metrics["完成Line"]))
    columns[2].metric("差異 Line", _fmt_int(metrics["差異Line"]))
    columns[3].metric("訂單 Line 完成率", f'{metrics["完成率"]:.2%}')
    st.caption(
        f'不重複商品數：{metrics["不重複商品數"]:,}｜'
        f'各品項門市家數合計：{metrics["品項門市家數合計"]:,}｜'
        f'有效原始明細：{metrics["有效明細"]:,}｜'
        f'合併重複資料：{metrics["合併重複資料"]:,}'
    )

    # 三套总览指标连续显示在页面上方，明细表随后呈现。
    _render_loose_pcs_results(items)

    summary = pd.DataFrame([{"檔名": name, **metrics} for name, _, _, metrics in results])
    display = summary.copy()
    display["完成率"] = display["完成率"].map(lambda value: f"{value:.2%}")
    card_open("📋 訂單 Line 各檔彙總")
    st.dataframe(display, use_container_width=True, height=min(430, 90 + len(display) * 38))
    card_close()

    with st.expander("🧾 訂單 Line 明細", expanded=False):
        st.dataframe(combined_line, use_container_width=True, height=430)

    if errors:
        with st.expander("⚠️ 部分檔案無法計算訂單 Line", expanded=False):
            for file_name, message in errors:
                st.error(f"{file_name}：{message}")



# --------------------------------------------------
# 零散揀貨 PCS（成箱箱號空白）
# --------------------------------------------------
def _prepare_loose_pcs_rows(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """直接從原始資料計算零散揀貨 PCS，不承接其他計算的篩選結果。"""
    data = df.copy()
    data.columns = [str(column).strip() for column in data.columns]

    box_col = _resolve_col(data, "成箱箱號")
    expected_col = _resolve_col(data, "原始配庫存量")
    actual_col = _resolve_col(data, "數量")
    ship_in_col = _resolve_col(data, "出貨入數")
    missing = [
        name
        for name, column in (
            ("成箱箱號", box_col),
            ("原始配庫存量", expected_col),
            ("數量", actual_col),
            ("出貨入數", ship_in_col),
        )
        if column is None
    ]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}")

    box_text = _clean_text_series(data[box_col])
    data = data.loc[box_text.eq("")].copy()
    data["來源檔名"] = source_name
    data["應作業PCS計入值"] = _box_pcs_value(data[expected_col], data[ship_in_col])
    data["實際作業PCS計入值"] = _box_pcs_value(data[actual_col], data[ship_in_col])
    return data


def _loose_pcs_metrics(rows: pd.DataFrame) -> dict:
    expected = float(rows["應作業PCS計入值"].sum()) if not rows.empty else 0.0
    actual = float(rows["實際作業PCS計入值"].sum()) if not rows.empty else 0.0
    return {
        "零散揀貨筆數": int(len(rows)),
        "應作業PCS": expected,
        "實際作業PCS": actual,
        "PCS差異": expected - actual,
        "PCS完成率": actual / expected if expected else 0.0,
    }


def _render_loose_pcs_results(items: list[dict]) -> None:
    results = []
    errors = []
    for item in items:
        try:
            rows = _prepare_loose_pcs_rows(item["raw_df"], item["name"])
            results.append((item["name"], rows, _loose_pcs_metrics(rows)))
        except Exception as exc:
            errors.append((item["name"], str(exc)))

    st.markdown("### 🧺 零散揀貨 PCS 結果（成箱箱號空白）")
    if not results:
        st.warning("沒有可計算的零散揀貨 PCS，請展開下方原因確認來源欄位名稱。")
        if errors:
            with st.expander("檢視無法計算原因"):
                for file_name, message in errors:
                    st.error(f"{file_name}：{message}")
        return

    combined_rows = pd.concat([result[1] for result in results], ignore_index=True)
    metrics = _loose_pcs_metrics(combined_rows)
    columns = st.columns(4)
    columns[0].metric("零散揀貨筆數", _fmt_int(metrics["零散揀貨筆數"]))
    columns[1].metric("應作業 PCS", _fmt_qty(metrics["應作業PCS"]))
    columns[2].metric("實際作業 PCS", _fmt_qty(metrics["實際作業PCS"]))
    columns[3].metric("PCS 完成率", f'{metrics["PCS完成率"]:.2%}')
    st.caption(f'PCS 差異：{_fmt_qty(metrics["PCS差異"])}')

    summary = pd.DataFrame([{"檔名": name, **file_metrics} for name, _, file_metrics in results])
    display = summary.copy()
    display["PCS完成率"] = display["PCS完成率"].map(lambda value: f"{value:.2%}")
    card_open("📋 零散揀貨 PCS 各檔彙總")
    st.dataframe(display, use_container_width=True, height=min(430, 90 + len(display) * 38))
    card_close()

    with st.expander("📄 零散揀貨原始明細", expanded=False):
        preferred = [
            "來源檔名", "成箱箱號", "貨主訂單", "商品", "原始配庫存量", "數量",
            "出貨入數", "應作業PCS計入值", "實際作業PCS計入值",
        ]
        columns_to_show = [column for column in preferred if column in combined_rows.columns]
        st.dataframe(combined_rows[columns_to_show].head(2000), use_container_width=True, height=430)
        if len(combined_rows) > 2000:
            st.caption("畫面僅預覽前 2,000 筆。")

    if errors:
        with st.expander("⚠️ 部分檔案無法計算零散揀貨 PCS", expanded=False):
            for file_name, message in errors:
                st.error(f"{file_name}：{message}")




# =========================
# 零散總揀独立计算逻辑（原第 37 页）
# =========================
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




# --------------------------------------------------
# 合并页面 UI：两套流程只共用外壳，资料与计算完全独立
# --------------------------------------------------
def _render_box_reporting_workflow():
    if "uploader_key_35_box" not in st.session_state:
        st.session_state["uploader_key_35_box"] = 0

    card_open("📌 上傳揀貨成箱明細（可一次多檔）")
    u1, u2 = st.columns([1, 0.08], gap="small")
    with u1:
        uploaded_files = st.file_uploader(
            "請選擇一個或多個檔案",
            type=["xlsx", "xls", "xlsb", "xlsm", "csv", "html", "htm"],
            accept_multiple_files=True,
            key=f"uploader_35_box_{st.session_state['uploader_key_35_box']}",
        )
    with u2:
        st.markdown(" ")
        if st.button("🧹", help="清除已上傳檔案", use_container_width=True):
            st.session_state["uploader_key_35_box"] += 1
            st.rerun()
    card_close()

    if not uploaded_files:
        st.info(
            "請上傳檔案。必要欄位：成箱箱號、儲位、商品、原始配庫存量、數量、出貨入數。"
        )
        return

    items = []
    errors = []

    for i, uf in enumerate(uploaded_files, start=1):
        try:
            raw_df, read_note = _load_dataframe(uf, key_prefix=f"box_f{i}")
            box_df = _prepare_box_rows(raw_df, source_name=uf.name)
            metrics = _metrics_from_box_rows(box_df)
            line_df = _line_summary(box_df)

            items.append(
                {
                    "name": uf.name,
                    "read_note": read_note,
                    "raw_rows": len(raw_df),
                    "raw_df": raw_df,
                    "box_df": box_df,
                    "line_df": line_df,
                    "metrics": metrics,
                }
            )
        except Exception as e:
            errors.append((uf.name, str(e)))

    if errors:
        with st.expander("⚠️ 部分檔案讀取 / 計算失敗", expanded=True):
            for fn, msg in errors:
                st.error(f"{fn}：{msg}")

    if not items:
        st.error("沒有任何檔案成功計算，請確認必要欄位是否完整。")
        return

    # 合併所有成功檔案
    combined_box_df = pd.concat([it["box_df"] for it in items], ignore_index=True)

    # 合併總覽 Line 必須跨檔重新以 儲位+商品 判斷
    combined_line_base = combined_box_df.copy()
    combined_line_base["來源檔名"] = "全部檔案"
    combined_line_df = _line_summary(combined_line_base)
    combined_metrics = _combined_metrics(combined_box_df)

    # --------------------------------------------------
    # 總覽 KPI
    # --------------------------------------------------
    st.markdown("### 📊 合併結果")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("成箱 Line", _fmt_int(combined_metrics["成箱Line"]))
    c2.metric("完成 Line", _fmt_int(combined_metrics["完成Line"]))
    c3.metric("未完成 Line", _fmt_int(combined_metrics["未完成Line"]))
    c4.metric("Line 完成率", f"{combined_metrics['Line完成率']:.1%}")

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("應作業 PCS", _fmt_qty(combined_metrics["應作業PCS"]))
    p2.metric("實際作業 PCS", _fmt_qty(combined_metrics["實際作業PCS"]))
    p3.metric(
        "PCS 差異",
        _fmt_qty(combined_metrics["應作業PCS"] - combined_metrics["實際作業PCS"]),
    )
    p4.metric("PCS 完成率", f"{combined_metrics['PCS完成率']:.1%}")

    st.caption(
        f"成箱資料筆數：{combined_metrics['成箱資料筆數']:,}｜"
        f"不重複成箱箱號：{combined_metrics['成箱箱數']:,}"
    )

    _render_order_line_results(items)

    # --------------------------------------------------
    # 各檔彙總
    # --------------------------------------------------
    summary_rows = []
    for it in items:
        m = it["metrics"]
        summary_rows.append(
            {
                "檔名": it["name"],
                "讀取方式": it["read_note"],
                "原始筆數": it["raw_rows"],
                "成箱資料筆數": m["成箱資料筆數"],
                "成箱箱數": m["成箱箱數"],
                "成箱Line": m["成箱Line"],
                "完成Line": m["完成Line"],
                "未完成Line": m["未完成Line"],
                "Line完成率": m["Line完成率"],
                "應作業PCS": m["應作業PCS"],
                "實際作業PCS": m["實際作業PCS"],
                "PCS差異": m["應作業PCS"] - m["實際作業PCS"],
                "PCS完成率": m["PCS完成率"],
            }
        )
    summary_df = pd.DataFrame(summary_rows)

    card_open("📋 各檔彙總")
    st.dataframe(
        summary_df,
        use_container_width=True,
        height=min(430, 90 + len(summary_df) * 38),
        column_config={
            "Line完成率": st.column_config.NumberColumn(format="%.1f%%"),
            "PCS完成率": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    card_close()

    # --------------------------------------------------
    # Line 明細
    # --------------------------------------------------
    card_open("🧾 Line 明細（合併）")
    show_line = combined_line_df.copy()
    show_line["完成狀態"] = show_line["Line完成"].map({True: "完成", False: "未完成"})
    line_display_cols = [
        "儲位",
        "商品",
        "完成狀態",
        "應作業PCS",
        "實際作業PCS",
        "PCS差異",
        "成箱筆數",
        "成箱箱數",
    ]
    st.dataframe(show_line[line_display_cols], use_container_width=True, height=430)
    card_close()

    with st.expander("🔎 各檔 Line 明細", expanded=False):
        tabs = st.tabs([f"{i+1}. {it['name']}" for i, it in enumerate(items)])
        for tab, it in zip(tabs, items):
            with tab:
                dfp = it["line_df"].copy()
                dfp["完成狀態"] = dfp["Line完成"].map({True: "完成", False: "未完成"})
                st.caption(
                    f"讀取方式：{it['read_note']}｜成箱 Line：{it['metrics']['成箱Line']:,}｜"
                    f"完成：{it['metrics']['完成Line']:,}｜未完成：{it['metrics']['未完成Line']:,}"
                )
                st.dataframe(
                    dfp[[
                        "儲位",
                        "商品",
                        "完成狀態",
                        "應作業PCS",
                        "實際作業PCS",
                        "PCS差異",
                        "成箱筆數",
                        "成箱箱數",
                    ]],
                    use_container_width=True,
                    height=380,
                )

    # --------------------------------------------------
    # 原始成箱明細預覽
    # --------------------------------------------------
    preferred = [
        "來源檔名",
        "成箱箱號",
        "儲位",
        "商品",
        "原始配庫存量",
        "數量",
        "出貨入數",
        "應作業PCS計入值",
        "實際作業PCS計入值",
        "筆完成",
        "Line完成",
        "LineKey",
    ]
    ordered_cols = [c for c in preferred if c in combined_box_df.columns] + [
        c for c in combined_box_df.columns if c not in preferred
    ]

    with st.expander("📄 原始成箱明細預覽", expanded=False):
        st.dataframe(
            combined_box_df[ordered_cols].head(1000),
            use_container_width=True,
            height=430,
        )

    # --------------------------------------------------
    # 下載
    # --------------------------------------------------
    xlsx_bytes = _download_xlsx(
        summary_df=summary_df,
        combined_line_df=combined_line_df,
        combined_detail_df=combined_box_df[ordered_cols],
        per_file_line_dfs=[(it["name"], it["line_df"]) for it in items],
    )

    st.download_button(
        label="⬇️ 下載計算結果 Excel",
        data=xlsx_bytes,
        file_name="揀貨成箱_多檔計算結果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


def _render_loose_total_workflow():
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
        return

    run = st.button("開始產出", type="primary")
    if not run:
        card_close()
        return

    # 讀取 map
    try:
        df_map = read_excel_or_csv(map_file)
        df_map.columns = [str(c).strip() for c in df_map.columns]
    except Exception as e:
        st.error(f"讀取『儲位棚別明細』失敗：{e}")
        card_close()
        return

    for c in ["儲位", "儲位類型"]:
        if c not in df_map.columns:
            st.error(f"儲位棚別明細缺少欄位：{c}")
            card_close()
            return

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
        return

    st.download_button(
        "⬇️ 下載輸出 Excel（單一工作表）",
        data=out_bytes,
        file_name=out_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    card_close()


set_page(
    "報工稼動｜揀貨作業",
    icon="⏱️",
    subtitle="揀貨成箱、訂單 Line、零散 PCS 與零散總揀的獨立計算入口。",
)

box_tab, loose_total_tab = st.tabs(["📦 揀貨成箱／報工", "🎯 零散總揀"])
with box_tab:
    _render_box_reporting_workflow()
with loose_total_tab:
    _render_loose_total_workflow()
