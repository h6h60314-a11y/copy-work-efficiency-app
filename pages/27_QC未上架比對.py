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
import copy as _copy

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# =============================
# 參數
# =============================
QC_KEY_HEADER = "商品"
UN_KEY_HEADER = "商品碼"
UN_DATE_HEADER = "進貨日"

MATCH_SHEET_NAME = "符合未上架明細"

DELETE_HEADERS = [
    "移動的數量", "目的儲位", "可移動單位至",
    "計量單位由", "到包裝碼", "已試算", "已揀取"
]


# =============================
# UI CSS（背景 + 上傳框風格）
# =============================
def _page_css():
    st.markdown(
        r"""
<style>
/* 背景（淡藍漸層） */
div[data-testid="stAppViewContainer"]{
  background: linear-gradient(
    180deg,
    rgba(232,245,255,1) 0%,
    rgba(244,250,255,1) 34%,
    rgba(255,255,255,1) 100%
  ) !important;
}

/* Header 下面的 chips */
.qc-chips{
  margin-top: 4px;
  font-size: 12.5px;
  font-weight: 800;
  color: rgba(15,23,42,.62);
}
.qc-chips .sep{ margin: 0 8px; opacity:.55; }

/* 小標題（上傳區每段） */
.qc-u-label{
  font-size: 13.5px;
  font-weight: 900;
  color: rgba(15,23,42,.86);
  margin: 4px 0 6px 0;
}

/* Streamlit uploader dropzone：白底圓角（貼近你截圖） */
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

/* Browse files 按鈕更像卡片式 */
section[data-testid="stFileUploadDropzone"] button{
  border-radius: 10px !important;
  font-weight: 900 !important;
}

/* 產出按鈕不要太寬、跟截圖一致 */
div[data-testid="stButton"] > button{
  border-radius: 12px !important;
  font-weight: 900 !important;
  padding: 9px 14px !important;
}

/* 底部提示條（藍底） */
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
# 工具：定位欄位 / 文字格式
# =============================
def get_ws(wb, sheet_name: Optional[str]):
    return wb[sheet_name] if sheet_name else wb.worksheets[0]


def find_header_col(ws, header_name: str, header_row: int = 1) -> Optional[int]:
    for c in range(1, ws.max_column + 1):
        v = ws.cell(row=header_row, column=c).value
        if isinstance(v, str) and v.strip() == header_name:
            return c
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
    """把商品碼轉成字串並保留前導0（依 number_format 或 fallback_width）"""
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


def force_code_text_cell(cell, width: int):
    """把 cell 轉成文字並保留前導0（只針對純數字碼）"""
    v = cell.value
    fmt = cell.number_format
    s = normalize_code(v, fmt, width)
    if s and s.isdigit() and width >= 2:
        s = s.zfill(width)
    cell.value = s
    cell.number_format = "@"


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
# 讀取：僅支援 xlsx/xlsm（上傳 xls/xlsb 會提示先轉檔）
# =============================
def _load_wb_from_upload(uploaded_file) -> Tuple[str, "openpyxl.workbook.workbook.Workbook"]:
    name = uploaded_file.name
    ext = (name.split(".")[-1] or "").lower()

    if ext not in ("xlsx", "xlsm"):
        raise ValueError(
            f"目前上傳檔案為 .{ext}：{name}\n"
            "此頁面僅支援 .xlsx / .xlsm。\n"
            "（若是 .xls / .xlsb 請先用 Excel 另存新檔為 .xlsx 再上傳）"
        )

    bio = io.BytesIO(uploaded_file.getvalue())
    keep_vba = (ext == "xlsm")
    wb = load_workbook(bio, keep_vba=keep_vba)
    return name, wb


# =============================
# 主流程（回傳輸出 bytes）
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
    un_key_col = find_header_col(un_ws, UN_KEY_HEADER, 1)
    un_date_col = find_header_col(un_ws, UN_DATE_HEADER, 1)

    if qc_key_col is None:
        raise ValueError(f"QC 找不到欄位：{QC_KEY_HEADER}")
    if un_key_col is None:
        raise ValueError(f"未上架明細找不到欄位：{UN_KEY_HEADER}")
    if un_date_col is None:
        raise ValueError(f"未上架明細找不到欄位：{UN_DATE_HEADER}")

    # 推估碼長（保留 000000）
    code_len = 0
    for r in range(2, un_ws.max_row + 1):
        cell = un_ws.cell(row=r, column=un_key_col)
        if isinstance(cell.value, str):
            s = cell.value.strip()
            if s.isdigit():
                code_len = max(code_len, len(s))
    fallback_width = code_len or 6

    # 商品碼 -> 進貨日(可多筆合併)
    date_sets = defaultdict(set)
    for r in range(2, un_ws.max_row + 1):
        code_cell = un_ws.cell(row=r, column=un_key_col)
        code = normalize_code(code_cell.value, code_cell.number_format, fallback_width)

        d_cell = un_ws.cell(row=r, column=un_date_col)
        d_str = format_date_value(d_cell.value)

        if code and d_str:
            if code.isdigit():
                code = code.zfill(fallback_width)
            date_sets[code].add(d_str)

    date_map: Dict[str, str] = {k: "、".join(sorted(v)) for k, v in date_sets.items()}

    # QC 的商品欄位：統一轉文字並保留 000000
    for r in range(2, qc_ws.max_row + 1):
        force_code_text_cell(qc_ws.cell(row=r, column=qc_key_col), fallback_width)

    # 新增/定位「進貨日」
    qc_date_col = find_header_col(qc_ws, "進貨日", 1)
    if qc_date_col is None:
        qc_date_col = qc_ws.max_column + 1
        hdr = qc_ws.cell(row=1, column=qc_date_col, value="進貨日")
        src_hdr = qc_ws.cell(row=1, column=qc_key_col)
        hdr._style = _copy.copy(src_hdr._style)
        hdr.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # 填入進貨日 + 收集 match rows
    match_rows = []
    for r in range(2, qc_ws.max_row + 1):
        code_cell = qc_ws.cell(row=r, column=qc_key_col)
        code = normalize_code(code_cell.value, code_cell.number_format, fallback_width)
        if code and code.isdigit():
            code = code.zfill(fallback_width)

        d_str = date_map.get(code, "")
        out_cell = qc_ws.cell(row=r, column=qc_date_col)
        out_cell.value = d_str
        out_cell.number_format = "@"
        if d_str:
            match_rows.append(r)

    # 產生符合工作表
    if MATCH_SHEET_NAME in qc_wb.sheetnames:
        del qc_wb[MATCH_SHEET_NAME]
    mws = qc_wb.create_sheet(MATCH_SHEET_NAME)

    maxc = qc_ws.max_column
    for c in range(1, maxc + 1):
        src = qc_ws.cell(row=1, column=c)
        dst = mws.cell(row=1, column=c, value=src.value)
        dst._style = _copy.copy(src._style)
        dst.number_format = src.number_format
        dst.alignment = _copy.copy(src.alignment)

    out_r = 2
    for r in match_rows:
        for c in range(1, maxc + 1):
            src = qc_ws.cell(row=r, column=c)
            dst = mws.cell(row=out_r, column=c, value=src.value)
            dst._style = _copy.copy(src._style)
            dst.number_format = src.number_format
            dst.alignment = _copy.copy(src.alignment)
        out_r += 1

    # 刪除指定欄位（所有工作表）
    drop_set = {x.strip().lower() for x in DELETE_HEADERS}

    def header_map(ws):
        mp = {}
        for c in range(1, ws.max_column + 1):
            v = ws.cell(row=1, column=c).value
            if isinstance(v, str) and v.strip():
                mp[v.strip().lower()] = c
        return mp

    for ws in qc_wb.worksheets:
        hmap = header_map(ws)
        cols = [hmap[name] for name in drop_set if name in hmap]
        for col_idx in sorted(set(cols), reverse=True):
            ws.delete_cols(col_idx, 1)

    out = io.BytesIO()
    qc_wb.save(out)
    out.seek(0)
    return len(match_rows), out.getvalue()


# =============================
# Streamlit UI（檔案上傳格式已調整）
# =============================
st.set_page_config(page_title="大豐物流 - 進貨課｜QC未上架比對", page_icon="🧾", layout="wide")
inject_logistics_theme()
_page_css()

set_page("QC 未上架比對", icon="🧾", subtitle="0108QC「商品」比對 未上架明細「商品碼」，回填「進貨日」，並產生「符合未上架明細」分頁；同時刪除指定欄位。")

st.markdown(
    '<div class="qc-chips">少揀差異<span class="sep">｜</span>庫存儲位展開<span class="sep">｜</span>欄位刪除<span class="sep">｜</span>前導 0 保留</div>',
    unsafe_allow_html=True,
)

# ✅ 用 card_open / card_close：才會真的形成卡片（不會再出現空白大圓角）
card_open("📁 檔案上傳")

st.markdown('<div class="qc-u-label">0108QC（Excel：.xlsx / .xlsm）</div>', unsafe_allow_html=True)
qc_file = st.file_uploader(
    "0108QC",
    type=["xlsx", "xlsm"],
    accept_multiple_files=False,
    label_visibility="collapsed",
    key="qc_file",
)

st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

st.markdown('<div class="qc-u-label">未上架明細（同一個檔 / Excel：.xlsx / .xlsm）</div>', unsafe_allow_html=True)
un_file = st.file_uploader(
    "未上架明細",
    type=["xlsx", "xlsm"],
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
                qc_sheet_name = st.selectbox("0108QC 工作表", options=qc_wb_preview.sheetnames, index=0)
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

status_msg = "請依序上傳：0108QC + 未上架明細"
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
