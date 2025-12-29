# -*- coding: utf-8 -*-
import os
import re
import math
import hashlib
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import Rule
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.chart import LineChart, BarChart, Reference
from openpyxl.chart.label import DataLabelList

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# =========================
# 設定
# =========================
TARGET_PER_MANHOUR_DEFAULT = 790
AM_HOURS = list(range(8, 13))     # 8-12
PM_HOURS = list(range(13, 19))    # 13-18

BASE_FONT_NAME = "微軟正黑體"
BASE_FONT_SIZE = 12
ROW_HEIGHT = 18

NUM_FMT_2_HIDE0 = "#,##0.00;-#,##0.00;;@"
NUM_FMT_4_HIDE0 = "#,##0.0000;-#,##0.0000;;@"
NUM_FMT_INT_HIDE0 = "#,##0;-#,##0;;@"
NUM_FMT_INT = "#,##0"
NUM_FMT_MONEY_HIDE0 = "#,##0;-#,##0;;@"

AM_DEFAULT_MONEY = 100
PM_DEFAULT_MONEY = 50

QCA_LIST = ["GT-B", "GT-C", "GT-D", "GT-E"]
QCB_LIST = ["GT-A", "GT-J", "GT-K"]

OLE_HEADER = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
ZIP_HEADER = b"PK\x03\x04"


# =========================
# robust reader（支援假xls / bytes）
# =========================
def _try_read_html(raw: bytes) -> pd.DataFrame:
    tables = pd.read_html(BytesIO(raw))
    if tables:
        return tables[0]
    raise ValueError("HTML 讀取不到表格")


def _try_read_text_like(raw: bytes) -> pd.DataFrame:
    for enc in ("utf-8-sig", "utf-8", "big5", "cp950", "latin1"):
        for sep in ("\t", ",", ";", "|"):
            try:
                df = pd.read_csv(BytesIO(raw), encoding=enc, sep=sep)
                if df.shape[1] >= 2:
                    return df
            except Exception:
                continue
    raise ValueError("不是可解析的文字分隔檔")


def robust_read_bytes(filename: str, raw: bytes) -> pd.DataFrame:
    ext = os.path.splitext(filename)[1].lower()
    head = raw[:8]
    is_ole = head.startswith(OLE_HEADER)
    is_zip = head.startswith(ZIP_HEADER)

    if is_zip or ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return pd.read_excel(BytesIO(raw), engine="openpyxl")

    if is_ole or ext in (".xls",):
        try:
            return pd.read_excel(BytesIO(raw), engine="xlrd")
        except Exception:
            try:
                return _try_read_html(raw)
            except Exception:
                return _try_read_text_like(raw)

    if ext == ".csv":
        for enc in ("utf-8-sig", "utf-8", "big5", "cp950", "latin1"):
            try:
                return pd.read_csv(BytesIO(raw), encoding=enc)
            except Exception:
                continue
        return pd.read_csv(BytesIO(raw), encoding="utf-8", errors="replace")

    try:
        return _try_read_html(raw)
    except Exception:
        return _try_read_text_like(raw)


# =========================
# Excel style helpers
# =========================
def _clone_font(cell_font: Font, *, name=None, size=None, bold=None, color=None):
    if cell_font is None:
        cell_font = Font()
    return Font(
        name=name if name is not None else cell_font.name,
        size=size if size is not None else cell_font.size,
        bold=bold if bold is not None else cell_font.bold,
        italic=cell_font.italic,
        vertAlign=cell_font.vertAlign,
        underline=cell_font.underline,
        strike=cell_font.strike,
        color=color if color is not None else cell_font.color,
        outline=cell_font.outline,
        shadow=cell_font.shadow,
        condense=cell_font.condense,
        extend=cell_font.extend,
        charset=cell_font.charset,
        family=cell_font.family,
        scheme=cell_font.scheme,
    )


def _set_base_font(cell, *, force_color=None, force_bold=None):
    cell.font = _clone_font(
        cell.font,
        name=BASE_FONT_NAME,
        size=BASE_FONT_SIZE,
        bold=force_bold if force_bold is not None else cell.font.bold,
        color=force_color if force_color is not None else cell.font.color,
    )


def _set_row_height(ws, r):
    ws.row_dimensions[r].height = ROW_HEIGHT


# =========================
# 欄位對照
# =========================
def normalize_columns(df: pd.DataFrame):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    colmap = {str(c).strip().upper(): c for c in df.columns}

    def pick(*cands):
        for k in cands:
            if k in colmap:
                return colmap[k]
        return None

    c_pickdate = pick("PICKDATE", "PICK_DATE", "PICK DATETIME", "PICKTIME", "PICK_TIME")
    c_packqty  = pick("PACKQTY", "PACK_QTY", "PCS", "QTY")
    c_cweight  = pick("CWEIGHT", "C_WEIGHT", "C WEIGHT", "WEIGHT")
    c_lineid   = pick("LINEID", "LINE_ID", "LINE", "LINE ID")
    c_stotype  = pick("STO_TYPE", "STOTYPE", "SO_TYPE", "TYPE")

    missing = [name for name, col in [
        ("PICKDATE", c_pickdate),
        ("PACKQTY",  c_packqty),
        ("Cweight",  c_cweight),
        ("LINEID",   c_lineid),
        ("STO_TYPE", c_stotype),
    ] if col is None]

    if missing:
        raise KeyError(f"缺少必要欄位：{missing}\n目前欄位：{list(df.columns)}")

    return df, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype


# =========================
# 產出每小時彙整資料
# =========================
def build_hourly_metrics(df, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype):
    df = df.copy()
    df[c_stotype] = df[c_stotype].astype(str).str.strip()
    df[c_lineid] = df[c_lineid].astype(str).str.strip()

    df[c_pickdate] = pd.to_datetime(df[c_pickdate], errors="coerce")
    df[c_packqty] = pd.to_numeric(df[c_packqty], errors="coerce").fillna(0)
    df[c_cweight] = pd.to_numeric(df[c_cweight], errors="coerce").fillna(0)

    df["加權PCS"] = df[c_packqty] * df[c_cweight]
    df["PICK_HOUR"] = df[c_pickdate].dt.floor("h")
    df["PICK_DATE"] = df["PICK_HOUR"].dt.date
    df["HOUR"] = df["PICK_HOUR"].dt.hour

    line_base = (df.groupby(["PICK_DATE", c_lineid, "HOUR"])[[c_packqty, "加權PCS"]]
                   .sum()
                   .reset_index()
                   .rename(columns={c_packqty: "PCS"}))

    split = (df.groupby(["PICK_DATE", c_lineid, "HOUR", c_stotype])[[c_packqty, "加權PCS"]]
               .sum()
               .reset_index()
               .rename(columns={c_packqty: "PCS"}))

    return df, line_base, split


# =========================
# manpower helpers
# =========================
def _as_float(v):
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


def _as_blank_if_zero(val):
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return ""
    try:
        fv = float(val)
    except Exception:
        return ""
    if abs(fv) < 1e-12:
        return ""
    return fv


# =========================
# ✅ 人力：穩定快速貼上（主方案）
# =========================
def _init_manpower_table(lineids, hours):
    cols = [str(int(h)) for h in hours]
    idx = [str(x) for x in lineids]
    return pd.DataFrame(pd.NA, index=idx, columns=cols, dtype="Float64")


def _apply_fill(df: pd.DataFrame, line_id: str, hours: list[int], value: float, which: str):
    df2 = df.copy()
    if line_id not in df2.index:
        return df2

    if which == "整天":
        tgt_hours = hours
    elif which == "上午":
        tgt_hours = [h for h in hours if h in AM_HOURS]
    else:
        tgt_hours = [h for h in hours if h in PM_HOURS]

    for h in tgt_hours:
        c = str(int(h))
        if c in df2.columns:
            df2.loc[line_id, c] = value
    return df2


def _parse_paste(text: str, lineids: list[str], hours: list[int]) -> pd.DataFrame:
    """
    支援 3 種貼法：
    A) 含表頭：第一列=小時，第一欄=Line ID
       Line ID\t8\t9\t10...
       GT-A\t1\t1...
    B) 不含表頭：純數字矩陣，依 lineids 順序、hours 順序套用
       1\t1\t1...
       0\t1\t1...
    C) 每列一個 line：第一欄是 Line ID，後面直接數字
       GT-A\t1\t1\t...
    """
    text = (text or "").strip()
    if not text:
        return pd.DataFrame()

    rows = [r for r in text.splitlines() if r.strip() != ""]
    grid = [r.split("\t") for r in rows]
    if not grid:
        return pd.DataFrame()

    def _is_hour_token(x: str) -> bool:
        x = str(x).strip()
        if x == "":
            return False
        try:
            v = int(float(x))
            return 0 <= v <= 23
        except Exception:
            return False

    # 表頭判斷：第一列第二格後，大半是 hour
    header_like = False
    if len(grid[0]) >= 2:
        tokens = grid[0][1:]
        if tokens:
            hits = sum(_is_hour_token(t) for t in tokens)
            if hits >= max(2, len(tokens) // 2):
                header_like = True

    base = _init_manpower_table(lineids, hours)
    base.index = [str(x) for x in base.index]
    base.columns = [str(c) for c in base.columns]

    # A) 有表頭
    if header_like:
        hdr = [str(x).strip() for x in grid[0]]
        cols = []
        for x in hdr[1:]:
            if _is_hour_token(x):
                cols.append(str(int(float(x))))
        data = grid[1:]
        for r in data:
            if not r:
                continue
            rid = str(r[0]).strip()
            if rid not in base.index:
                continue
            for j, col in enumerate(cols, start=1):
                if col not in base.columns:
                    continue
                if j >= len(r):
                    continue
                v = str(r[j]).strip()
                if v == "":
                    continue
                try:
                    base.loc[rid, col] = float(v)
                except Exception:
                    continue
        return base

    # B/C) 無表頭：若第一欄像 GT- -> C，否則 B
    first_col_is_line = any((len(r) >= 1 and str(r[0]).strip().upper().startswith("GT-")) for r in grid)

    if first_col_is_line:
        # C) 每列第一欄是 line id
        cols = [str(int(h)) for h in hours]
        for r in grid:
            if not r:
                continue
            rid = str(r[0]).strip()
            if rid not in base.index:
                continue
            for j, col in enumerate(cols, start=1):
                if j >= len(r):
                    continue
                v = str(r[j]).strip()
                if v == "":
                    continue
                try:
                    base.loc[rid, col] = float(v)
                except Exception:
                    continue
        return base

    # B) 純矩陣：依 lineids/hours 順序套
    cols = [str(int(h)) for h in hours]
    for i, rid in enumerate(lineids):
        if i >= len(grid):
            break
        r = grid[i]
        for j, col in enumerate(cols):
            if j >= len(r):
                break
            v = str(r[j]).strip()
            if v == "":
                continue
            try:
                base.loc[str(rid), col] = float(v)
            except Exception:
                continue
    return base


# =========================
# 寫入每小時戰情表（日期工作表）
# =========================
def write_hourly_sheet(
    wb, sheet_name, date_value, hours, lineids,
    line_base_map, split_map, manpower_map
):
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        wb.remove(ws)
    ws = wb.create_sheet(sheet_name)

    black_fill = PatternFill("solid", fgColor="111111")
    head_fill = PatternFill("solid", fgColor="F2F2F2")
    manpower_fill = PatternFill("solid", fgColor="FFF2CC")

    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")
    right = Alignment(horizontal="right", vertical="center")

    _set_row_height(ws, 1)
    ws["A1"] = str(date_value)
    ws["A1"].alignment = center
    ws["A1"].fill = head_fill
    ws["A1"].border = border
    _set_base_font(ws["A1"], force_bold=True)

    for j, h in enumerate(hours, start=2):
        c = ws.cell(row=1, column=j, value=int(h))
        c.alignment = center
        c.fill = head_fill
        c.border = border
        _set_base_font(c, force_bold=True)

    _set_row_height(ws, 2)
    ws["A2"] = "撿貨（已撿數量）"
    ws["A2"].fill = black_fill
    ws["A2"].alignment = left
    ws["A2"].border = border
    _set_base_font(ws["A2"], force_bold=True, force_color="FFFFFF")

    for j in range(2, 2 + len(hours)):
        cell = ws.cell(row=2, column=j, value=None)
        cell.alignment = right
        cell.border = border
        cell.number_format = NUM_FMT_2_HIDE0
        _set_base_font(cell)

    r = 3
    pcs_weight_rows = []

    def write_row(label, values_by_hour=None, style_black=True, fill=None, is_manpower=False):
        nonlocal r
        _set_row_height(ws, r)

        a = ws.cell(row=r, column=1, value=label)
        a.fill = black_fill if style_black else (fill or None)
        a.alignment = left
        a.border = border
        if style_black:
            _set_base_font(a, force_bold=True, force_color="FFFFFF")
        else:
            _set_base_font(a, force_bold=True)

        for j, h in enumerate(hours, start=2):
            raw = None if values_by_hour is None else values_by_hour.get(int(h), None)

            if is_manpower:
                v = raw
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    c = ws.cell(row=r, column=j, value="")
                else:
                    fv = float(v)
                    if abs(fv - round(fv)) < 1e-12:
                        c = ws.cell(row=r, column=j, value=int(round(fv)))
                    else:
                        c = ws.cell(row=r, column=j, value=fv)
                        c.number_format = "#,##0.##;-#,##0.##;;@"
            else:
                v = _as_blank_if_zero(raw)
                c = ws.cell(row=r, column=j, value=("" if v == "" else float(v)))
                if v != "":
                    c.number_format = NUM_FMT_2_HIDE0

            c.alignment = right
            c.border = border
            if fill is not None:
                c.fill = fill
                _set_base_font(c, force_bold=True)
            else:
                _set_base_font(c)

        row_idx = r
        r += 1
        return row_idx

    def write_formula_row(label, numerator_row, denom_row, number_format):
        nonlocal r
        _set_row_height(ws, r)

        a = ws.cell(row=r, column=1, value=label)
        a.fill = black_fill
        a.alignment = left
        a.border = border
        _set_base_font(a, force_bold=True, force_color="FFFFFF")

        for j in range(2, 2 + len(hours)):
            col = get_column_letter(j)
            num = f"{col}{numerator_row}"
            den = f"{col}{denom_row}"
            formula = f'=IF(OR({den}="",{den}=0),"",IF({num}/{den}=0,"",{num}/{den}))'
            c = ws.cell(row=r, column=j, value=formula)
            c.alignment = right
            c.border = border
            c.number_format = number_format
            _set_base_font(c)

        r += 1

    for lid in lineids:
        lid = str(lid)

        _set_row_height(ws, r)
        a = ws.cell(row=r, column=1, value=f"{lid} Line")
        a.fill = black_fill
        a.alignment = left
        a.border = border
        _set_base_font(a, force_bold=True, force_color="FFFFFF")
        for j in range(2, 2 + len(hours)):
            c = ws.cell(row=r, column=j, value=None)
            c.border = border
            c.alignment = Alignment(horizontal="right", vertical="center")
            _set_base_font(c)
        r += 1

        pcs_weight_map = line_base_map.get((lid, "加權PCS"), {})
        pcs_map = line_base_map.get((lid, "PCS"), {})

        gso_w = split_map.get((lid, "GSO", "加權PCS"), {})
        gxso_w = split_map.get((lid, "GXSO", "加權PCS"), {})
        gso = split_map.get((lid, "GSO", "PCS"), {})
        gxso = split_map.get((lid, "GXSO", "PCS"), {})

        row_pcs_w = write_row(f"{lid}（PCS）加權", pcs_weight_map, is_manpower=False)
        pcs_weight_rows.append(row_pcs_w)

        write_row(f"{lid}（PCS）", pcs_map, is_manpower=False)
        write_row("GSO(加權)", gso_w, is_manpower=False)
        write_row("GXSO(加權)", gxso_w, is_manpower=False)
        write_row("GSO", gso, is_manpower=False)
        write_row("GXSO", gxso, is_manpower=False)

        man_map = {int(h): manpower_map.get((date_value, lid, int(h)), np.nan) for h in hours}
        write_row(f"{lid}（人數）", man_map, fill=manpower_fill, is_manpower=True)

        write_formula_row("平均產力(加權) 4", numerator_row=row_pcs_w, denom_row=row_pcs_w + 6, number_format=NUM_FMT_4_HIDE0)
        write_formula_row("平均產力(加權)", numerator_row=row_pcs_w, denom_row=row_pcs_w + 6, number_format=NUM_FMT_2_HIDE0)

        _set_row_height(ws, r)
        for j in range(1, 2 + len(hours)):
            c = ws.cell(row=r, column=j, value=None)
            c.border = border
            c.alignment = Alignment(horizontal="right", vertical="center") if j >= 2 else Alignment(horizontal="left", vertical="center")
            _set_base_font(c)
        r += 1

    # 撿貨(已撿數量) = 各 Line 的（PCS）加權加總
    for j in range(2, 2 + len(hours)):
        col = get_column_letter(j)
        refs = ",".join([f"{col}{rr}" for rr in pcs_weight_rows])
        c = ws.cell(row=2, column=j, value=f'=IF(SUM({refs})=0,"",SUM({refs}))')
        c.number_format = NUM_FMT_2_HIDE0
        c.alignment = Alignment(horizontal="right", vertical="center")
        _set_base_font(c)

    ws.column_dimensions["A"].width = 24
    for j in range(2, 2 + len(hours)):
        ws.column_dimensions[get_column_letter(j)].width = 12
    ws.freeze_panes = "B3"
    return ws


# =========================
# ✅ 達標計算
# =========================
def compute_achievers(date_value, lineids, hours, line_base_map, manpower_map, target_per_mh: int):
    am_ach, pm_ach = [], []
    for lid in lineids:
        lid = str(lid)
        am_man = sum(_as_float(manpower_map.get((date_value, lid, int(h)), 0)) for h in AM_HOURS if h in hours)
        pm_man = sum(_as_float(manpower_map.get((date_value, lid, int(h)), 0)) for h in PM_HOURS if h in hours)

        pcs_w_map = line_base_map.get((lid, "加權PCS"), {})
        am_pcs = sum(float(pcs_w_map.get(int(h), 0) or 0) for h in AM_HOURS if h in hours)
        pm_pcs = sum(float(pcs_w_map.get(int(h), 0) or 0) for h in PM_HOURS if h in hours)

        am_target = math.trunc(target_per_mh * am_man)
        pm_target = math.trunc(target_per_mh * pm_man)
        if am_man > 0 and math.trunc(am_pcs) >= am_target:
            am_ach.append(lid)
        if pm_man > 0 and math.trunc(pm_pcs) >= pm_target:
            pm_ach.append(lid)
    return am_ach, pm_ach


# =========================
# 彙總 sheet helpers
# =========================
def _is_hour(v):
    try:
        iv = int(str(v).strip())
        return 0 <= iv <= 23
    except Exception:
        return False


def find_hour_header_row(ws):
    max_r = min(ws.max_row, 10)
    max_c = min(ws.max_column, 120)
    for r in range(1, max_r + 1):
        hour_to_col = {}
        for c in range(1, max_c + 1):
            v = ws.cell(r, c).value
            if _is_hour(v):
                hour_to_col[int(str(v).strip())] = c
        if len(hour_to_col) >= 3:
            return r, hour_to_col
    return None, {}


def parse_line_rows(ws):
    out = {}
    for r in range(1, ws.max_row + 1):
        v = ws.cell(r, 1).value
        if not v:
            continue
        t = str(v).strip()

        m1 = re.match(r"(.+?)（PCS）加權$", t)
        if m1:
            lid = m1.group(1).strip()
            out.setdefault(lid, {})["pcs_w"] = r
            continue

        m2 = re.match(r"(.+?)（人數）$", t)
        if m2:
            lid = m2.group(1).strip()
            out.setdefault(lid, {})["man"] = r
            continue

    return {k: v for k, v in out.items() if "pcs_w" in v and "man" in v}


def sum_cells_formula(sheet, row, cols):
    if not cols:
        return "=0"
    refs = [f"'{sheet}'!{get_column_letter(c)}{row}" for c in cols]
    return f"=SUM({','.join(refs)})"


def countif_sum(range_a1: str, items: list[str]) -> str:
    return "+".join([f'COUNTIF({range_a1},"{it}")' for it in items]) if items else "0"


def build_summary_sheet_with_achievers(
    wb, summary_name, date_ws, line_map, am_cols, pm_cols,
    am_achievers, pm_achievers, target_per_mh: int
):
    if summary_name in wb.sheetnames:
        wb.remove(wb[summary_name])
    ws = wb.create_sheet(summary_name)

    thin = Side(style="thin", color="D0D0D0")
    thick = Side(style="medium", color="111111")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    box_border = Border(left=thick, right=thick, top=thick, bottom=thick)

    header_fill = PatternFill("solid", fgColor="F8CBAD")
    sub_header_fill = PatternFill("solid", fgColor="F2F2F2")

    center = Alignment(horizontal="center", vertical="center")
    right = Alignment(horizontal="right", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    headers = {
        1: "Line ID",
        2: "每小時目標(加權)",
        3: "上午人力",
        4: "上午應達成(加權)",
        5: "總PCS(加權)",
        6: "差異(加權)",
        7: "下午人力",
        8: "下午目標(加權)",
        9: "總PCS(加權)",
        10: "差異(加權)",
    }

    _set_row_height(ws, 1)
    for col, title in headers.items():
        cell = ws.cell(1, col, title)
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center
        _set_base_font(cell, force_bold=True)

    widths = {
        "A": 12, "B": 16, "C": 12, "D": 18, "E": 14, "F": 12,
        "G": 12, "H": 16, "I": 14, "J": 12,
        "K": 2,  "L": 14, "M": 18, "N": 18,
    }
    for k, v in widths.items():
        ws.column_dimensions[k].width = v

    r0 = 2
    src = date_ws.title

    def text_no_trailing_dot(expr: str):
        t = f'TEXT({expr},"#,##0.##")'
        return f'IF(RIGHT({t},1)=".",LEFT({t},LEN({t})-1),{t})'

    for i, (lid, rows) in enumerate(line_map.items()):
        r = r0 + i
        _set_row_height(ws, r)

        for col in range(1, 11):
            cell = ws.cell(r, col)
            cell.border = border
            cell.alignment = center if col in (1, 2, 3) else right
            _set_base_font(cell)

        ws.cell(r, 1, str(lid).strip())
        ws.cell(r, 2, int(target_per_mh)).number_format = NUM_FMT_INT

        man_row = rows["man"]
        pcsw_row = rows["pcs_w"]

        am_man_expr = sum_cells_formula(src, man_row, am_cols)[1:]
        am_pcs_expr = sum_cells_formula(src, pcsw_row, am_cols)[1:]
        pm_man_expr = sum_cells_formula(src, man_row, pm_cols)[1:]
        pm_pcs_expr = sum_cells_formula(src, pcsw_row, pm_cols)[1:]

        ws.cell(r, 3, f'=IF({am_man_expr}=0,"",{text_no_trailing_dot(am_man_expr)})').number_format = "@"
        ws.cell(r, 7, f'=IF({pm_man_expr}=0,"",{text_no_trailing_dot(pm_man_expr)})').number_format = "@"

        ws.cell(r, 4, f'=IF($C{r}="","",TRUNC($B{r}*VALUE(SUBSTITUTE($C{r},",","")),0))').number_format = NUM_FMT_INT_HIDE0
        ws.cell(r, 8, f'=IF($G{r}="","",TRUNC($B{r}*VALUE(SUBSTITUTE($G{r},",","")),0))').number_format = NUM_FMT_INT_HIDE0

        ws.cell(r, 5, f'=IF($C{r}="","",IF({am_pcs_expr}=0,"",TRUNC({am_pcs_expr},0)))').number_format = NUM_FMT_INT_HIDE0
        ws.cell(r, 9, f'=IF($G{r}="","",IF({pm_pcs_expr}=0,"",TRUNC({pm_pcs_expr},0)))').number_format = NUM_FMT_INT_HIDE0

        ws.cell(r, 6, f'=IF(OR($D{r}="",$E{r}=""),"",TRUNC($E{r}-$D{r},0))').number_format = NUM_FMT_INT_HIDE0
        ws.cell(r, 10, f'=IF(OR($H{r}="",$I{r}=""),"",TRUNC($I{r}-$H{r},0))').number_format = NUM_FMT_INT_HIDE0

    last_row = r0 + len(line_map) - 1
    if last_row < r0:
        last_row = r0

    if last_row >= r0:
        red_fill = PatternFill(fill_type="solid", start_color="FFC7CE", end_color="FFC7CE")
        green_fill = PatternFill(fill_type="solid", start_color="C6EFCE", end_color="C6EFCE")
        dxf_red = DifferentialStyle(font=Font(color="9C0006"), fill=red_fill)
        dxf_green = DifferentialStyle(font=Font(color="006100"), fill=green_fill)

        rule_e_red = Rule(type="expression", dxf=dxf_red, stopIfTrue=True)
        rule_e_red.formula = [f'AND($D{r0}<>"",E{r0}<>"",E{r0}<$D{r0})']
        ws.conditional_formatting.add(f"E{r0}:E{last_row}", rule_e_red)

        rule_e_green = Rule(type="expression", dxf=dxf_green, stopIfTrue=True)
        rule_e_green.formula = [f'AND($D{r0}<>"",E{r0}<>"",E{r0}>=$D{r0})']
        ws.conditional_formatting.add(f"E{r0}:E{last_row}", rule_e_green)

        rule_i_red = Rule(type="expression", dxf=dxf_red, stopIfTrue=True)
        rule_i_red.formula = [f'AND($H{r0}<>"",I{r0}<>"",I{r0}<$H{r0})']
        ws.conditional_formatting.add(f"I{r0}:I{last_row}", rule_i_red)

        rule_i_green = Rule(type="expression", dxf=dxf_green, stopIfTrue=True)
        rule_i_green.formula = [f'AND($H{r0}<>"",I{r0}<>"",I{r0}>=$H{r0})']
        ws.conditional_formatting.add(f"I{r0}:I{last_row}", rule_i_green)

    # 達標名單（含金額可輸入）
    def draw_achiever_block(start_row, title, achievers, default_money, qc_mult, restock_mult):
        col_line = 12
        col_name = 13
        col_money = 14

        _set_row_height(ws, start_row)
        tcell = ws.cell(start_row, col_line, title)
        tcell.alignment = left
        _set_base_font(tcell, force_bold=True)
        ws.merge_cells(start_row=start_row, start_column=col_line, end_row=start_row, end_column=col_money)

        hr = start_row + 1
        _set_row_height(ws, hr)
        h1 = ws.cell(hr, col_line, "達標 Line ID")
        h2 = ws.cell(hr, col_name, "姓名（手動輸入）")
        h3 = ws.cell(hr, col_money, "金額（可輸入/預設公式）")
        for c in (h1, h2, h3):
            c.fill = sub_header_fill
            c.border = border
            c.alignment = center
            _set_base_font(c, force_bold=True)

        rr = hr + 1
        first_list_row = rr

        def _write_row(label, money_formula_or_blank):
            nonlocal rr
            _set_row_height(ws, rr)

            c1 = ws.cell(rr, col_line, label)
            c1.alignment = center
            c1.border = border
            _set_base_font(c1, force_bold=True)

            c2 = ws.cell(rr, col_name, "")
            c2.border = box_border
            c2.alignment = left
            _set_base_font(c2)

            c3 = ws.cell(rr, col_money, money_formula_or_blank)
            c3.border = box_border
            c3.alignment = right
            c3.number_format = NUM_FMT_MONEY_HIDE0
            _set_base_font(c3)

            rr += 1

        if achievers:
            for lid in achievers:
                _write_row(str(lid), f"={int(default_money)}")
        else:
            _write_row("（無）", "")

        open_rng = f"$A$2:$A${last_row}"
        ach_rng = f"$L${first_list_row}:$L${rr-1}"

        open_qca = "(" + countif_sum(open_rng, QCA_LIST) + ")"
        ach_qca  = "(" + countif_sum(ach_rng,  QCA_LIST) + ")"
        open_qcb = "(" + countif_sum(open_rng, QCB_LIST) + ")"
        ach_qcb  = "(" + countif_sum(ach_rng,  QCB_LIST) + ")"

        open_all = f'COUNTIF({open_rng},"GT-*")'
        ach_all  = f'COUNTIF({ach_rng},"GT-*")'

        qca_formula = f'=IF({open_qca}=0,"",TRUNC({ach_qca}/{open_qca}*{qc_mult},0))'
        qcb_formula = f'=IF({open_qcb}=0,"",TRUNC({ach_qcb}/{open_qcb}*{qc_mult},0))'
        restock_formula = f'=IF({open_all}=0,"",TRUNC({ach_all}/{open_all}*{restock_mult},0))'

        _write_row("QCA", qca_formula)
        _write_row("QCB", qcb_formula)
        _write_row("補貨", restock_formula)

        return rr

    start = last_row + 3
    next_row = draw_achiever_block(start, "上午達標名單（PCS≥上午應達成）", am_achievers, AM_DEFAULT_MONEY, 50, 100)
    draw_achiever_block(next_row, "下午達標名單（PCS≥下午目標）", pm_achievers, PM_DEFAULT_MONEY, 100, 50)

    ws.freeze_panes = "A2"
    return ws


# =========================
# KPI 圖表 sheet（新增）
# =========================
def add_kpi_chart_sheet(wb: Workbook, kpi_df: pd.DataFrame):
    name = "KPI圖表"
    if name in wb.sheetnames:
        wb.remove(wb[name])
    ws = wb.create_sheet(name, 0)

    header_fill = PatternFill("solid", fgColor="D9E1F2")
    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center")
    right = Alignment(horizontal="right", vertical="center")

    cols = list(kpi_df.columns)
    ws.append(cols)
    _set_row_height(ws, 1)
    for j in range(1, len(cols) + 1):
        cell = ws.cell(1, j)
        cell.fill = header_fill
        cell.border = border
        cell.alignment = center
        _set_base_font(cell, force_bold=True)

    for _, row in kpi_df.iterrows():
        ws.append([row.get(c, None) for c in cols])

    for r in range(2, ws.max_row + 1):
        _set_row_height(ws, r)
        for j in range(1, ws.max_column + 1):
            cell = ws.cell(r, j)
            cell.border = border
            cell.alignment = right if j >= 2 else center
            _set_base_font(cell)

    ws.column_dimensions["A"].width = 14
    for col_letter in "BCDEFG":
        ws.column_dimensions[col_letter].width = 16

    for col in ("B", "C"):
        for r in range(2, ws.max_row + 1):
            ws[f"{col}{r}"].number_format = "0.0%"
    for col in ("D", "E"):
        for r in range(2, ws.max_row + 1):
            ws[f"{col}{r}"].number_format = "#,##0.00"
    for col in ("F", "G"):
        for r in range(2, ws.max_row + 1):
            ws[f"{col}{r}"].number_format = "#,##0"

    cats = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)

    bar1 = BarChart()
    bar1.type = "col"
    bar1.title = "達標率（上午/下午）"
    bar1.y_axis.title = "達標率"
    data = Reference(ws, min_col=2, max_col=3, min_row=1, max_row=ws.max_row)
    bar1.add_data(data, titles_from_data=True)
    bar1.set_categories(cats)
    ws.add_chart(bar1, "I2")

    line = LineChart()
    line.title = "平均產力（加權PCS/人力）"
    line.y_axis.title = "平均產力"
    data2 = Reference(ws, min_col=4, max_col=5, min_row=1, max_row=ws.max_row)
    line.add_data(data2, titles_from_data=True)
    line.set_categories(cats)
    ws.add_chart(line, "I18")

    bar2 = BarChart()
    bar2.type = "col"
    bar2.title = "總PCS(加權)（上午/下午）"
    bar2.y_axis.title = "總PCS(加權)"
    data3 = Reference(ws, min_col=6, max_col=7, min_row=1, max_row=ws.max_row)
    bar2.add_data(data3, titles_from_data=True)
    bar2.set_categories(cats)
    ws.add_chart(bar2, "I34")

    ws.freeze_panes = "A2"
    return ws


# =========================
# 產出 Excel bytes（含 KPI圖表）
# =========================
def build_output_excel_bytes(df_raw: pd.DataFrame, target_per_mh: int, manpower_by_date: dict):
    df_raw, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype = normalize_columns(df_raw)
    df2, line_base, split = build_hourly_metrics(df_raw, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype)

    dates = sorted(df2["PICK_DATE"].dropna().unique())
    if not dates:
        raise ValueError("PICKDATE 解析後沒有日期資料，請確認 PICKDATE 欄位內容。")

    date_to_hours = {}
    date_to_lineids = {}
    for d in dates:
        hours = sorted(df2.loc[df2["PICK_DATE"] == d, "HOUR"].dropna().unique().tolist())
        date_to_hours[d] = [int(x) for x in hours]
        lineids = sorted(df2.loc[df2["PICK_DATE"] == d, c_lineid].dropna().astype(str).unique().tolist())
        date_to_lineids[d] = [str(x) for x in lineids]

    manpower_map = {}
    for d in dates:
        hours = date_to_hours.get(d, [])
        lineids = date_to_lineids.get(d, [])
        table = manpower_by_date.get(str(d))
        if table is None:
            continue

        table2 = table.copy()
        for col in table2.columns:
            table2[col] = pd.to_numeric(table2[col], errors="coerce")

        for lid in lineids:
            for h in hours:
                v = np.nan
                try:
                    v = table2.loc[str(lid), str(h)]
                except Exception:
                    v = np.nan
                manpower_map[(d, str(lid), int(h))] = v

    wb = Workbook()
    wb.remove(wb.active)

    summary_inputs = {}
    kpi_rows = []

    for d in dates:
        hours = date_to_hours[d]
        if not hours:
            continue
        lineids = date_to_lineids[d]

        sub_base = line_base[line_base["PICK_DATE"] == d]
        line_base_map = {}
        for lid in lineids:
            tmp = sub_base[sub_base[c_lineid].astype(str).str.strip() == str(lid)]
            line_base_map[(str(lid), "PCS")] = {int(r["HOUR"]): r["PCS"] for _, r in tmp.iterrows()}
            line_base_map[(str(lid), "加權PCS")] = {int(r["HOUR"]): r["加權PCS"] for _, r in tmp.iterrows()}

        sub_split = split[split["PICK_DATE"] == d]
        split_map = {}
        for lid in lineids:
            tmpL = sub_split[sub_split[c_lineid].astype(str).str.strip() == str(lid)]
            for t in ["GSO", "GXSO"]:
                tmpT = tmpL[tmpL[c_stotype].astype(str).str.strip() == t]
                split_map[(str(lid), t, "PCS")] = {int(r["HOUR"]): r["PCS"] for _, r in tmpT.iterrows()}
                split_map[(str(lid), t, "加權PCS")] = {int(r["HOUR"]): r["加權PCS"] for _, r in tmpT.iterrows()}

        date_ws = write_hourly_sheet(
            wb=wb,
            sheet_name=str(d),
            date_value=d,
            hours=hours,
            lineids=lineids,
            line_base_map=line_base_map,
            split_map=split_map,
            manpower_map=manpower_map,
        )

        am_ach, pm_ach = compute_achievers(d, lineids, hours, line_base_map, manpower_map, target_per_mh=target_per_mh)

        def _period_metrics(period_hours, achievers):
            total_man = 0.0
            total_pcs = 0.0
            open_lines = 0
            for lid in lineids:
                lid = str(lid)
                man = sum(_as_float(manpower_map.get((d, lid, int(h)), 0)) for h in period_hours if h in hours)
                if man > 0:
                    open_lines += 1
                total_man += man

                pcs_map = line_base_map.get((lid, "加權PCS"), {})
                pcs = sum(float(pcs_map.get(int(h), 0) or 0) for h in period_hours if h in hours)
                total_pcs += pcs

            ach_lines = len(achievers)
            ach_rate = (ach_lines / open_lines) if open_lines > 0 else np.nan
            avg_prod = (total_pcs / total_man) if total_man > 0 else np.nan
            return ach_rate, avg_prod, total_pcs

        am_rate, am_prod, am_pcs = _period_metrics(AM_HOURS, am_ach)
        pm_rate, pm_prod, pm_pcs = _period_metrics(PM_HOURS, pm_ach)

        kpi_rows.append({
            "日期": str(d),
            "上午達標率": am_rate,
            "下午達標率": pm_rate,
            "上午平均產力": am_prod,
            "下午平均產力": pm_prod,
            "上午總PCS加權": math.trunc(am_pcs) if not (isinstance(am_pcs, float) and np.isnan(am_pcs)) else np.nan,
            "下午總PCS加權": math.trunc(pm_pcs) if not (isinstance(pm_pcs, float) and np.isnan(pm_pcs)) else np.nan,
        })

        _, hour_to_col = find_hour_header_row(date_ws)
        line_map2 = parse_line_rows(date_ws)
        am_cols = [hour_to_col[h] for h in AM_HOURS if h in hour_to_col]
        pm_cols = [hour_to_col[h] for h in PM_HOURS if h in hour_to_col]

        summary_inputs[d] = (date_ws, line_map2, am_cols, pm_cols, am_ach, pm_ach)

    kpi_df = pd.DataFrame(kpi_rows)
    if not kpi_df.empty:
        add_kpi_chart_sheet(wb, kpi_df)

    for d in dates:
        pack = summary_inputs.get(d)
        if not pack:
            continue
        date_ws, line_map2, am_cols, pm_cols, am_ach, pm_ach = pack
        if date_ws is None or not line_map2:
            continue
        build_summary_sheet_with_achievers(
            wb=wb,
            summary_name=f"彙總_{str(d)}",
            date_ws=date_ws,
            line_map=line_map2,
            am_cols=am_cols,
            pm_cols=pm_cols,
            am_achievers=am_ach,
            pm_achievers=pm_ach,
            target_per_mh=target_per_mh,
        )

    sheet_order = []
    if "KPI圖表" in wb.sheetnames:
        sheet_order.append("KPI圖表")
    sheet_order += [sn for sn in wb.sheetnames if sn.startswith("彙總_")]
    sheet_order += [sn for sn in wb.sheetnames if sn not in sheet_order]
    wb._sheets = [wb[sn] for sn in sheet_order]

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue(), kpi_df


# =========================
# misc
# =========================
def _hash_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# =========================
# Streamlit main
# =========================
def main():
    inject_logistics_theme()
    set_page("出貨課｜出貨作業線產能", "📦")

    card_open("📥 來源檔案")
    up = st.file_uploader(
        "上傳來源檔（含 PICKDATE / PACKQTY / Cweight / LINEID / STO_TYPE）",
        type=["xlsx", "xlsm", "xltx", "xltm", "xls", "csv"],
        accept_multiple_files=False,
    )
    card_close()

    if not up:
        st.info("請先上傳檔案。")
        return

    raw = up.getvalue()
    file_sig = _hash_bytes(raw)

    card_open("⚙️ 參數設定")
    target_per_mh = st.number_input(
        "每小時目標(加權)（TARGET_PER_MANHOUR）",
        min_value=1, max_value=99999, value=int(TARGET_PER_MANHOUR_DEFAULT), step=1
    )
    card_close()

    # 解析資料（只在檔案變動時重新解析）
    if st.session_state.get("ship_line_prod_file_sig") != file_sig:
        try:
            df = robust_read_bytes(up.name, raw)
            df_norm, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype = normalize_columns(df)
            df2, _, _ = build_hourly_metrics(df_norm, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype)
        except Exception as e:
            st.error(f"讀取/解析失敗：{e}")
            return

        dates = sorted(df2["PICK_DATE"].dropna().unique())
        if not dates:
            st.error("PICKDATE 解析後沒有日期資料。")
            return

        date_to_hours = {}
        date_to_lineids = {}
        for d in dates:
            hours = sorted(df2.loc[df2["PICK_DATE"] == d, "HOUR"].dropna().unique().tolist())
            lineids = sorted(df2.loc[df2["PICK_DATE"] == d, c_lineid].dropna().astype(str).unique().tolist())
            date_to_hours[str(d)] = [int(x) for x in hours]
            date_to_lineids[str(d)] = [str(x) for x in lineids]

        st.session_state["ship_line_prod_file_sig"] = file_sig
        st.session_state["ship_line_prod_df"] = df
        st.session_state["ship_line_prod_dates"] = [str(d) for d in dates]
        st.session_state["ship_line_prod_date_to_hours"] = date_to_hours
        st.session_state["ship_line_prod_date_to_lineids"] = date_to_lineids

        # 初始化每日期人力表
        for d in st.session_state["ship_line_prod_dates"]:
            key = f"mp_{d}"
            st.session_state[key] = _init_manpower_table(date_to_lineids[d], date_to_hours[d])

        # 清掉舊的計算結果
        st.session_state.pop("kpi_preview_df", None)
        st.session_state.pop("last_out_bytes", None)
        st.session_state.pop("last_out_name", None)

    dates = st.session_state["ship_line_prod_dates"]
    date_to_hours = st.session_state["ship_line_prod_date_to_hours"]
    date_to_lineids = st.session_state["ship_line_prod_date_to_lineids"]
    df_source = st.session_state["ship_line_prod_df"]

    # =========================
    # 👥 人力輸入（穩定快速貼上）
    # =========================
    card_open("👥 人力輸入（✅Excel 整塊貼上 → 一鍵套用）")
    st.caption("支援：①含表頭（Line ID + 小時） ②純矩陣 ③每列含 Line ID。")

    tabs = st.tabs(dates)
    manpower_by_date = {}

    for i, d in enumerate(dates):
        with tabs[i]:
            hours = date_to_hours.get(d, [])
            lineids = date_to_lineids.get(d, [])
            key = f"mp_{d}"

            # ✅ 修正：不能用 DataFrame 做 or 判斷
            mp_df = st.session_state.get(key)
            if mp_df is None:
                mp_df = _init_manpower_table(lineids, hours)
                st.session_state[key] = mp_df

            c1, c2 = st.columns([1.25, 1.0])

            with c1:
                st.markdown("### 快速填入（不用貼上也很快）")
                r1, r2, r3 = st.columns([2, 2, 2])
                with r1:
                    sel_line = st.selectbox("Line ID", options=lineids, key=f"sel_line_{d}")
                with r2:
                    fill_val = st.number_input("人力值", value=0.0, step=0.5, key=f"fill_val_{d}")
                with r3:
                    which = st.selectbox("範圍", options=["整天", "上午", "下午"], key=f"which_{d}")

                if st.button("套用填入", use_container_width=True, key=f"apply_{d}"):
                    mp_df = _apply_fill(mp_df, str(sel_line), hours, float(fill_val), which)
                    st.session_state[key] = mp_df

                st.markdown("### 貼上區（建議用這個，最快最穩）")
                paste = st.text_area(
                    "把 Excel 的區塊直接貼這裡（Tab 分隔）",
                    height=220,
                    key=f"paste_{d}",
                    placeholder="例：\nLine ID\t8\t9\t10\nGT-A\t1\t1\t1\nGT-B\t0\t1\t1\n\n或純矩陣：\n1\t1\t1\n0\t1\t1\n\n或每列含 Line：\nGT-A\t1\t1\t1\nGT-B\t0\t1\t1",
                )

                b1, b2 = st.columns([1, 1])
                with b1:
                    if st.button("✅ 解析並套用（覆蓋）", use_container_width=True, key=f"paste_apply_{d}"):
                        parsed = _parse_paste(paste, lineids=lineids, hours=hours)
                        if parsed.empty:
                            st.warning("貼上內容解析不到資料")
                        else:
                            st.session_state[key] = parsed
                            mp_df = parsed
                            st.success("已套用貼上內容")
                with b2:
                    if st.button("清空此日人力", use_container_width=True, key=f"clear_{d}"):
                        mp_df = _init_manpower_table(lineids, hours)
                        st.session_state[key] = mp_df

            with c2:
                st.markdown("### 人力表預覽（只顯示，避免 data_editor 貼上 bug）")
                st.dataframe(mp_df, use_container_width=True, height=460)

            manpower_by_date[d] = mp_df

    card_close()

    # =========================
    # 📊 KPI 預覽 + 匯出
    # =========================
    card_open("📊 KPI 預覽（頁面）")
    if st.button("計算 KPI 預覽", use_container_width=True):
        try:
            out_bytes, kpi_df = build_output_excel_bytes(
                df_raw=df_source,
                target_per_mh=int(target_per_mh),
                manpower_by_date=manpower_by_date,
            )
            st.session_state["kpi_preview_df"] = kpi_df
            st.session_state["last_out_bytes"] = out_bytes
            st.session_state["last_out_name"] = f"{os.path.splitext(up.name)[0]}_出貨作業線產能_含KPI圖表.xlsx"
            st.success("KPI 已計算完成（下方有預覽與下載）")
        except Exception as e:
            st.error(f"KPI 計算失敗：{e}")

    kpi_df = st.session_state.get("kpi_preview_df")
    if isinstance(kpi_df, pd.DataFrame) and not kpi_df.empty:
        st.dataframe(kpi_df, use_container_width=True)

        chart_df = kpi_df.copy().set_index("日期")
        st.caption("達標率（上午/下午）")
        st.bar_chart(chart_df[["上午達標率", "下午達標率"]])

        st.caption("平均產力（上午/下午）")
        st.line_chart(chart_df[["上午平均產力", "下午平均產力"]])

        st.caption("總PCS(加權)（上午/下午）")
        st.bar_chart(chart_df[["上午總PCS加權", "下午總PCS加權"]])
    card_close()

    card_open("📤 匯出 Excel（含 KPI圖表 Sheet + 圖表）")
    out_bytes = st.session_state.get("last_out_bytes")
    out_name = st.session_state.get("last_out_name")

    if out_bytes:
        st.download_button(
            "⬇️ 下載輸出 Excel",
            data=out_bytes,
            file_name=out_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption("輸出包含：KPI圖表（含圖表）→ 彙總_日期 → 各日期戰情表")
    else:
        st.info("先按「計算 KPI 預覽」後就可以下載。")
    card_close()


if __name__ == "__main__":
    main()
