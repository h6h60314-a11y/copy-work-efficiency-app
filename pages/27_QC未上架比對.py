# pages/27_QC未上架比對.py
# -*- coding: utf-8 -*-
import io
from collections import defaultdict
from datetime import datetime, date
from typing import Optional, Tuple, Dict

import pandas as pd
import streamlit as st
from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl import Workbook
import copy as _copy

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# =============================
# 參數
# =============================
QC_KEY_HEADER = "商品"
UN_KEY_HEADER = "商品碼"
UN_DATE_HEADER = "進貨日"
UNIT_HEADER = "可移動單位"

MATCH_SHEET_NAME = "符合未上架明細"


# =============================
# UI CSS（背景 + 上傳框風格）
# =============================
def _page_css():
    st.markdown(
        r"""
<style>
div[data-testid="stAppViewContainer"]{
  background: linear-gradient(
    180deg,
    rgba(232,245,255,1) 0%,
    rgba(244,250,255,1) 34%,
    rgba(255,255,255,1) 100%
  ) !important;
}

.qc-chips{
  margin-top: 4px;
  font-size: 12.5px;
  font-weight: 800;
  color: rgba(15,23,42,.62);
}
.qc-chips .sep{ margin: 0 8px; opacity:.55; }

.qc-u-label{
  font-size: 13.5px;
  font-weight: 900;
  color: rgba(15,23,42,.86);
  margin: 4px 0 6px 0;
}

section[data-testid="stFileUploadDropzone"]{
  border: 1px solid rgba(148,163,184,.35) !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,1) !important;
  padding: 12px 14px !important;
}
section[data-testid="stFileUploadDropzone"]:hover{
  border-color: rgba(59,130,246,.35) !important;
  box-shadow: 0 6px 18px rgba(59,130,246,.08);
}

section[data-testid="stFileUploadDropzone"] button{
  border-radius: 10px !important;
  font-weight: 900 !important;
}

div[data-testid="stButton"] > button{
  border-radius: 12px !important;
  font-weight: 900 !important;
  padding: 9px 14px !important;
}

.qc-banner{
  background: rgba(219, 234, 254, .9);
  border: 1px solid rgba(59,130,246,.18);
  color: rgba(15,23,42,.86);
  border-radius: 10px;
  padding: 10px 12px;
  font-weight: 900;
  font-size: 13px;
  margin-top: 14px;
}
</style>
""",
        unsafe_allow_html=True,
    )


# =============================
# 工具：定位欄位 / 文字格式（僅用於「比對」，不改原表）
# =============================
def get_ws(wb, sheet_name: Optional[str]):
    return wb[sheet_name] if sheet_name else wb.worksheets[0]


def find_header_col(ws, header_name: str, header_row: int = 1) -> Optional[int]:
    # exact
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=header_row, column=c).value
        if isinstance(v, str) and v.strip() == header_name:
            return c
    # contains
    target = header_name.strip()
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=header_row, column=c).value
        if isinstance(v, str) and target in v.strip():
            return c
    return None


def zero_run_width(number_format: str) -> int:
    if not number_format:
        return 0
    fmt = number_format.split(";")[0]
    best = cur = 0
    for ch in fmt:
        if ch == "0":
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def normalize_code(value, fmt: str, fallback_width: int = 0) -> str:
    """
    ⚠️ 只用於比對（不回寫）
    把碼類欄位轉字串，必要時依 number_format/fallback_width 補0
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")

    width = max(zero_run_width(fmt or ""), fallback_width)

    if isinstance(value, int):
        s = str(value)
        return s.zfill(width) if width >= 2 else s

    if isinstance(value, float):
        if abs(value - round(value)) < 1e-9:
            iv = int(round(value))
            s = str(iv)
            return s.zfill(width) if width >= 2 else s
        return str(value)

    return str(value).strip()


def normalize_unit(value) -> str:
    """只用於比對（不回寫）"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    if isinstance(value, int):
        return str(value)
    return str(value).strip()


def _infer_digit_width(ws, col_idx: int, scan_limit: int = 50000) -> int:
    """
    從「未上架明細」推斷碼長：
    - 字串純數字：用 len(s)（可抓到 0000446502 這種）
    - number_format 000000...：用 zero_run_width
    """
    if col_idx is None:
        return 0
    w = 0
    end_r = min(ws.max_row, scan_limit)
    for r in range(2, end_r + 1):
        cell = ws.cell(row=r, column=col_idx)
        v = cell.value
        if v is None:
            continue

        fmt = getattr(cell, "number_format", "") or ""
        w = max(w, zero_run_width(fmt))

        if isinstance(v, str):
            s = v.strip()
            if s.isdigit():
                w = max(w, len(s))
    return w


def _pad_digits_for_compare(s: str, width: int) -> str:
    """只拿來比對，不回寫到 QC"""
    if not s:
        return ""
    if width >= 2 and s.isdigit():
        return s.zfill(width)
    return s


def format_date_value(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%Y-%m-%d")
    s = str(v).strip()
    if not s:
        return ""
    try:
        dtv = pd.to_datetime(s)
        return pd.Timestamp(dtv).strftime("%Y-%m-%d")
    except Exception:
        return s


# =============================
# 轉換：DataFrames -> openpyxl Workbook（xls/xlsb 用）
# =============================
def _dfs_to_workbook(sheets: Dict[str, pd.DataFrame]) -> Workbook:
    wb = Workbook()
    if wb.worksheets:
        wb.remove(wb.worksheets[0])

    for sheet_name, df in sheets.items():
        name = str(sheet_name)[:31] if sheet_name else "Sheet1"
        ws = wb.create_sheet(title=name)

        ws.append([str(c) if c is not None else "" for c in df.columns.tolist()])

        for row in df.itertuples(index=False, name=None):
            out_row = []
            for v in row:
                if isinstance(v, float) and pd.isna(v):
                    out_row.append(None)
                else:
                    out_row.append(v)
            ws.append(out_row)

    return wb


# =============================
# 讀取：支援 xlsx/xlsm/xls/xlsb
# =============================
def _load_wb_from_upload(uploaded_file) -> Tuple[str, Workbook]:
    name = uploaded_file.name
    ext = (name.split(".")[-1] or "").lower()
    raw = uploaded_file.getvalue()
    bio = io.BytesIO(raw)

    if ext in ("xlsx", "xlsm"):
        keep_vba = (ext == "xlsm")
        wb = load_workbook(bio, keep_vba=keep_vba)
        return name, wb

    if ext == "xlsb":
        try:
            sheets = pd.read_excel(io.BytesIO(raw), engine="pyxlsb", sheet_name=None)
        except Exception as e:
            raise ValueError(
                f"讀取 .xlsb 失敗：{e}\n"
                "請確認 requirements.txt 有 pyxlsb"
            )
        wb = _dfs_to_workbook(sheets)
        return name, wb

    if ext == "xls":
        try:
            sheets = pd.read_excel(io.BytesIO(raw), engine="xlrd", sheet_name=None)
        except ModuleNotFoundError:
            raise ValueError(
                "目前環境缺少 xlrd，無法讀取 .xls。\n"
                "請在 requirements.txt 加上：xlrd==2.0.1\n"
                "或先用 Excel 另存為 .xlsx 再上傳。"
            )
        except Exception as e:
            raise ValueError(
                f"讀取 .xls 失敗：{e}\n"
                "建議先用 Excel 另存 .xlsx 再上傳。"
            )
        wb = _dfs_to_workbook(sheets)
        return name, wb

    raise ValueError(
        f"不支援的檔案格式：.{ext}\n"
        "支援：.xlsx / .xlsm / .xls / .xlsb"
    )


# =============================
# 主流程（回傳輸出 bytes）
# ✅ 保證：不改 QC 原欄位任何值/格式（只新增「進貨日」+ 新分頁）
# =============================
def process_wb(
    qc_wb,
    un_wb,
    qc_sheet_name: Optional[str] = None,
    un_sheet_name: Optional[str] = None,
) -> Tuple[int, bytes]:
    qc_ws = get_ws(qc_wb, qc_sheet_name)
    un_ws = get_ws(un_wb, un_sheet_name)

    qc_key_col = find_header_col(qc_ws, QC_KEY_HEADER, 1)
    qc_unit_col = find_header_col(qc_ws, UNIT_HEADER, 1)

    un_key_col = find_header_col(un_ws, UN_KEY_HEADER, 1)
    un_unit_col = find_header_col(un_ws, UNIT_HEADER, 1)
    un_date_col = find_header_col(un_ws, UN_DATE_HEADER, 1)

    if qc_key_col is None:
        raise ValueError(f"QC 找不到欄位：{QC_KEY_HEADER}")
    if qc_unit_col is None:
        raise ValueError(f"QC 找不到欄位：{UNIT_HEADER}")

    if un_key_col is None:
        raise ValueError(f"未上架明細找不到欄位：{UN_KEY_HEADER}")
    if un_unit_col is None:
        raise ValueError(f"未上架明細找不到欄位：{UNIT_HEADER}")
    if un_date_col is None:
        raise ValueError(f"未上架明細找不到欄位：{UN_DATE_HEADER}")

    # 1) 推估商品碼長（僅用於比對，不回寫）
    code_len = 0
    for r in range(2, un_ws.max_row + 1):
        cell = un_ws.cell(row=r, column=un_key_col)
        if isinstance(cell.value, str):
            s = cell.value.strip()
            if s.isdigit():
                code_len = max(code_len, len(s))
        else:
            code_len = max(code_len, zero_run_width(getattr(cell, "number_format", "") or ""))
    fallback_width = code_len or 6

    # 2) 推估可移動單位碼長（僅用於比對，不回寫）
    unit_width = _infer_digit_width(un_ws, un_unit_col)

    # 3) 建索引：(商品碼, 可移動單位) -> 進貨日(可多筆合併)
    date_sets = defaultdict(set)
    for r in range(2, un_ws.max_row + 1):
        code_cell = un_ws.cell(row=r, column=un_key_col)
        code = normalize_code(code_cell.value, getattr(code_cell, "number_format", ""), fallback_width)
        if code and code.isdigit():
            code = code.zfill(fallback_width)

        unit_cell = un_ws.cell(row=r, column=un_unit_col)
        unit = normalize_unit(unit_cell.value)
        unit = _pad_digits_for_compare(unit, unit_width)

        d_cell = un_ws.cell(row=r, column=un_date_col)
        d_str = format_date_value(d_cell.value)

        if code and unit and d_str:
            date_sets[(code, unit)].add(d_str)

    date_map: Dict[Tuple[str, str], str] = {k: "、".join(sorted(v)) for k, v in date_sets.items()}

    # 4) 新增/定位「進貨日」（只新增這一欄，不動原欄位）
    qc_date_col = find_header_col(qc_ws, "進貨日", 1)
    if qc_date_col is None:
        qc_date_col = qc_ws.max_column + 1
        hdr = qc_ws.cell(row=1, column=qc_date_col, value="進貨日")
        # header 樣式：盡量跟「商品」表頭一致
        src_hdr = qc_ws.cell(row=1, column=qc_key_col)
        try:
            hdr._style = _copy.copy(src_hdr._style)
        except Exception:
            pass
        hdr.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 5) 填入進貨日 + 收集 match rows（比對用補0，但不回寫 QC）
    match_rows = []
    for r in range(2, qc_ws.max_row + 1):
        # 商品（比對用 normalize，不回寫）
        code_cell = qc_ws.cell(row=r, column=qc_key_col)
        code = normalize_code(code_cell.value, getattr(code_cell, "number_format", ""), fallback_width)
        if code and code.isdigit():
            code = code.zfill(fallback_width)

        # 可移動單位（比對用補0，不回寫）
        unit_cell = qc_ws.cell(row=r, column=qc_unit_col)
        unit = normalize_unit(unit_cell.value)
        unit = _pad_digits_for_compare(unit, unit_width)

        d_str = date_map.get((code, unit), "")

        out_cell = qc_ws.cell(row=r, column=qc_date_col)
        out_cell.value = d_str
        out_cell.number_format = "@"  # 進貨日欄位本來不存在，這裡設定文字即可
        if d_str:
            match_rows.append(r)

    # 6) 產生符合工作表（內容/格式跟 QC 原列一致，只是挑出符合的列）
    if MATCH_SHEET_NAME in qc_wb.sheetnames:
        del qc_wb[MATCH_SHEET_NAME]
    mws = qc_wb.create_sheet(MATCH_SHEET_NAME)

    maxc = qc_ws.max_column
    # copy header
    for c in range(1, maxc + 1):
        src = qc_ws.cell(row=1, column=c)
        dst = mws.cell(row=1, column=c, value=src.value)
        try:
            dst._style = _copy.copy(src._style)
        except Exception:
            pass
        dst.number_format = getattr(src, "number_format", "")
        dst.alignment = _copy.copy(getattr(src, "alignment", Alignment()))

    # copy matched rows
    out_r = 2
    for r in match_rows:
        for c in range(1, maxc + 1):
            src = qc_ws.cell(row=r, column=c)
            dst = mws.cell(row=out_r, column=c, value=src.value)
            try:
                dst._style = _copy.copy(src._style)
            except Exception:
                pass
            dst.number_format = getattr(src, "number_format", "")
            dst.alignment = _copy.copy(getattr(src, "alignment", Alignment()))
        out_r += 1

    out = io.BytesIO()
    qc_wb.save(out)
    out.seek(0)
    return len(match_rows), out.getvalue()


# =============================
# Streamlit UI
# =============================
st.set_page_config(page_title="大豐物流 - 進貨課｜QC未上架比對", page_icon="🧾", layout="wide")
inject_logistics_theme()
_page_css()

set_page(
    "QC 未上架比對",
    icon="🧾",
    subtitle="比對條件：QC「商品+可移動單位」= 未上架明細「商品碼+可移動單位」；只新增「進貨日」與「符合未上架明細」分頁，QC 原明細格式/內容保持一致。",
)

st.markdown(
    '<div class="qc-chips">雙條件比對<span class="sep">｜</span>只新增進貨日/符合分頁<span class="sep">｜</span>QC明細保持原樣</div>',
    unsafe_allow_html=True,
)

card_open("📁 檔案上傳")

st.markdown('<div class="qc-u-label">QC 明細（支援：.xlsx / .xlsm / .xls / .xlsb）</div>', unsafe_allow_html=True)
qc_file = st.file_uploader(
    "QC 明細",
    type=["xlsx", "xlsm", "xls", "xlsb"],
    accept_multiple_files=False,
    label_visibility="collapsed",
    key="qc_file",
)

st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

st.markdown('<div class="qc-u-label">未上架明細（支援：.xlsx / .xlsm / .xls / .xlsb）</div>', unsafe_allow_html=True)
un_file = st.file_uploader(
    "未上架明細",
    type=["xlsx", "xlsm", "xls", "xlsb"],
    accept_multiple_files=False,
    label_visibility="collapsed",
    key="un_file",
)

qc_sheet_name = None
un_sheet_name = None

with st.expander("進階設定（工作表選擇）", expanded=False):
    c1, c2 = st.columns(2)
    with c1:
        if qc_file:
            try:
                _, qc_wb_preview = _load_wb_from_upload(qc_file)
                qc_sheet_name = st.selectbox("QC 工作表", options=qc_wb_preview.sheetnames, index=0)
            except Exception as e:
                st.error(str(e))
    with c2:
        if un_file:
            try:
                _, un_wb_preview = _load_wb_from_upload(un_file)
                un_sheet_name = st.selectbox("未上架明細 工作表", options=un_wb_preview.sheetnames, index=0)
            except Exception as e:
                st.error(str(e))

ready = bool(qc_file and un_file)
run = st.button("🚀 產出比對", disabled=not ready)

card_close()

status_msg = "請依序上傳：QC 明細 + 未上架明細"
xlsx_bytes = None
matched = None

if ready:
    status_msg = "檔案已就緒，可按「產出比對」"

if run:
    try:
        with st.spinner("處理中…"):
            _, qc_wb = _load_wb_from_upload(qc_file)
            _, un_wb = _load_wb_from_upload(un_file)

            matched, xlsx_bytes = process_wb(
                qc_wb=qc_wb,
                un_wb=un_wb,
                qc_sheet_name=qc_sheet_name,
                un_sheet_name=un_sheet_name,
            )
    except Exception as e:
        st.error(f"❌ 執行失敗：{e}")

if xlsx_bytes is not None:
    card_open("✅ 產出結果")
    st.success(f"完成！符合筆數：{matched}")
    out_name = f"QC未上架比對_輸出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    st.download_button(
        label="📥 下載輸出 Excel",
        data=xlsx_bytes,
        file_name=out_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    card_close()

st.markdown(f'<div class="qc-banner">{status_msg}</div>', unsafe_allow_html=True)
