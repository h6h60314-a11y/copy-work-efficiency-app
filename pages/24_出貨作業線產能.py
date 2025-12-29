# -*- coding: utf-8 -*-
import os
import re
import math
import hashlib
from io import BytesIO

import numpy as np
import pandas as pd
import streamlit as st

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import Rule
from openpyxl.styles.differential import DifferentialStyle
from openpyxl.chart import BarChart, Reference

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
# manpower
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


def _as_float(v):
    if v is None or (isinstance(v, str) and v.strip() == ""):
        return 0.0
    try:
        return float(v)
    except Exception:
        return 0.0


# =========================
# ✅ 手動輸入表格（穩定）
# =========================
def render_manual_input_grid(date_str: str, mp_df: pd.DataFrame, lineids: list[str], hours: list[int]) -> pd.DataFrame:
    mp_df = mp_df.copy()

    st.markdown("### 快速工具")
    t1, t2, t3, t4 = st.columns([2, 2, 2, 2])

    with t1:
        line_sel = st.selectbox("整列填入：Line ID", options=lineids, key=f"row_line_{date_str}")
    with t2:
        row_val = st.number_input("整列值", value=0.0, step=0.5, key=f"row_val_{date_str}")
    with t3:
        row_scope = st.selectbox("列範圍", ["整天", "上午", "下午"], key=f"row_scope_{date_str}")
    with t4:
        if st.button("套用整列", use_container_width=True, key=f"apply_row_{date_str}"):
            mp_df = _apply_fill(mp_df, str(line_sel), hours, float(row_val), row_scope)

    u1, u2, u3 = st.columns([2, 2, 2])
    with u1:
        hour_sel = st.selectbox("整欄填入：小時", options=[int(h) for h in hours], key=f"col_hour_{date_str}")
    with u2:
        col_val = st.number_input("整欄值", value=0.0, step=0.5, key=f"col_val_{date_str}")
    with u3:
        if st.button("套用整欄", use_container_width=True, key=f"apply_col_{date_str}"):
            col = str(int(hour_sel))
            for lid in lineids:
                mp_df.loc[str(lid), col] = float(col_val)

    st.markdown("---")
    st.markdown("### 人力手動輸入（Tab / 方向鍵可快速跳格）")

    header = st.columns([2] + [1] * len(hours))
    header[0].markdown("**Line ID**")
    for j, h in enumerate(hours, start=1):
        header[j].markdown(f"**{int(h)}**")

    for lid in lineids:
        cols = st.columns([2] + [1] * len(hours))
        cols[0].markdown(f"**{lid}**")

        for j, h in enumerate(hours, start=1):
            colname = str(int(h))
            cur = mp_df.loc[str(lid), colname]
            cur_val = 0.0 if (cur is pd.NA or cur is None or (isinstance(cur, float) and np.isnan(cur))) else float(cur)

            v = cols[j].number_input(
                label=f"{lid}_{colname}",
                value=float(cur_val),
                step=0.5,
                label_visibility="collapsed",
                key=f"cell_{date_str}_{lid}_{colname}",
            )
            mp_df.loc[str(lid), colname] = float(v)

    return mp_df


# =========================
# ✅ 我們的輸出 Sheet：戰情表（日期）
# =========================
def write_hourly_sheet(wb, sheet_name, date_value, hours, lineids, line_base_map, split_map, manpower_map):
    # 覆蓋同名（但不動原本其他分頁）
    if sheet_name in wb.sheetnames:
        wb.remove(wb[sheet_name])
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

    def write_row(label, values_by_hour=None, is_manpower=False):
        nonlocal r
        _set_row_height(ws, r)

        a = ws.cell(row=r, column=1, value=label)
        a.fill = black_fill
        a.alignment = left
        a.border = border
        _set_base_font(a, force_bold=True, force_color="FFFFFF")

        for j, h in enumerate(hours, start=2):
            v = None if values_by_hour is None else values_by_hour.get(int(h), None)

            if is_manpower:
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    c = ws.cell(row=r, column=j, value="")
                else:
                    fv = float(v)
                    c = ws.cell(row=r, column=j, value=fv if abs(fv-round(fv)) > 1e-12 else int(round(fv)))
                c.fill = manpower_fill
            else:
                vv = float(v) if v not in (None, "", np.nan) else 0.0
                c = ws.cell(row=r, column=j, value=("" if abs(vv) < 1e-12 else vv))
                c.number_format = NUM_FMT_2_HIDE0

            c.alignment = right
            c.border = border
            _set_base_font(c)

        row_idx = r
        r += 1
        return row_idx

    def write_formula_row(label, numerator_row, denom_row, fmt):
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
            c.number_format = fmt
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
            c.alignment = right
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
        man_row = write_row(f"{lid}（人數）", man_map, is_manpower=True)

        write_formula_row("平均產力(加權) 4", numerator_row=row_pcs_w, denom_row=man_row, fmt=NUM_FMT_4_HIDE0)
        write_formula_row("平均產力(加權)", numerator_row=row_pcs_w, denom_row=man_row, fmt=NUM_FMT_2_HIDE0)

        _set_row_height(ws, r)
        for j in range(1, 2 + len(hours)):
            c = ws.cell(row=r, column=j, value=None)
            c.border = border
            c.alignment = right if j >= 2 else left
            _set_base_font(c)
        r += 1

    for j in range(2, 2 + len(hours)):
        col = get_column_letter(j)
        refs = ",".join([f"{col}{rr}" for rr in pcs_weight_rows])
        c = ws.cell(row=2, column=j, value=f'=IF(SUM({refs})=0,"",SUM({refs}))')
        c.number_format = NUM_FMT_2_HIDE0
        c.alignment = right
        _set_base_font(c)

    ws.column_dimensions["A"].width = 24
    for j in range(2, 2 + len(hours)):
        ws.column_dimensions[get_column_letter(j)].width = 12
    ws.freeze_panes = "B3"
    return ws


# =========================
# ✅ 新 KPI 圖表：各 Line 指標（上午應達成/下午目標/總PCS加權）
# =========================
def add_line_kpi_chart_sheet(wb, date_str: str, line_kpi_df: pd.DataFrame):
    """
    Sheet: KPI圖表_YYYY-MM-DD
    欄位：Line ID | 上午應達成(加權) | 下午目標(加權) | 總PCS(加權)
    圖：Clustered Column（3 series）
    """
    sheet_name = f"KPI圖表_{date_str}"
    if sheet_name in wb.sheetnames:
        wb.remove(wb[sheet_name])
    ws = wb.create_sheet(sheet_name, 0)

    header_fill = PatternFill("solid", fgColor="D9E1F2")
    thin = Side(style="thin", color="D0D0D0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center")
    right = Alignment(horizontal="right", vertical="center")

    cols = ["Line ID", "上午應達成(加權)", "下午目標(加權)", "總PCS(加權)"]
    ws.append(cols)
    _set_row_height(ws, 1)
    for j in range(1, len(cols) + 1):
        c = ws.cell(1, j)
        c.fill = header_fill
        c.border = border
        c.alignment = center
        _set_base_font(c, force_bold=True)

    # 寫資料
    for _, row in line_kpi_df.iterrows():
        ws.append([
            row.get("Line ID", ""),
            row.get("上午應達成(加權)", None),
            row.get("下午目標(加權)", None),
            row.get("總PCS(加權)", None),
        ])

    for r in range(2, ws.max_row + 1):
        _set_row_height(ws, r)
        for j in range(1, 5):
            cell = ws.cell(r, j)
            cell.border = border
            cell.alignment = center if j == 1 else right
            _set_base_font(cell)
        # 數字格式
        for j in (2, 3, 4):
            ws.cell(r, j).number_format = NUM_FMT_INT_HIDE0

    ws.column_dimensions["A"].width = 12
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 18
    ws.column_dimensions["D"].width = 16

    # 圖表
    cats = Reference(ws, min_col=1, min_row=2, max_row=ws.max_row)
    data = Reference(ws, min_col=2, max_col=4, min_row=1, max_row=ws.max_row)

    chart = BarChart()
    chart.type = "col"
    chart.grouping = "clustered"
    chart.title = f"{date_str} 各Line KPI（目標 vs PCS）"
    chart.y_axis.title = "加權數值"
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 12
    chart.width = 26

    ws.add_chart(chart, "F2")
    ws.freeze_panes = "A2"


# =========================
# ✅ 輸出：保留原檔，追加分頁（關鍵修改）
# =========================
def build_output_excel_bytes(original_filename: str, original_bytes: bytes, df_raw: pd.DataFrame, target_per_mh: int, manpower_by_date: dict):
    # 先做資料彙整
    df_raw, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype = normalize_columns(df_raw)
    df2, line_base, split = build_hourly_metrics(df_raw, c_pickdate, c_packqty, c_cweight, c_lineid, c_stotype)

    dates = sorted(df2["PICK_DATE"].dropna().unique())
    if not dates:
        raise ValueError("PICKDATE 解析後沒有日期資料。")

    date_to_hours = {}
    date_to_lineids = {}
    for d in dates:
        hours = sorted(df2.loc[df2["PICK_DATE"] == d, "HOUR"].dropna().unique().tolist())
        date_to_hours[d] = [int(x) for x in hours]
        lineids = sorted(df2.loc[df2["PICK_DATE"] == d, c_lineid].dropna().astype(str).unique().tolist())
        date_to_lineids[d] = [str(x) for x in lineids]

    # 將 manpower_by_date 攤平成 map
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

    # ✅ 讀取原活頁簿（保留原本內容）
    ext = os.path.splitext(original_filename)[1].lower()
    wb = None
    preserved = True
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        try:
            wb = load_workbook(BytesIO(original_bytes), keep_vba=(ext == ".xlsm"))
        except Exception:
            wb = None

    if wb is None:
        # .xls 或讀取失敗：只能新建
        preserved = False
        wb = Workbook()
        # 移除預設空白 sheet
        if wb.active and wb.active.title == "Sheet":
            wb.remove(wb.active)

    # 逐日產出：日期戰情表 + KPI圖表_日期
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

        # ✅ 1) 日期戰情表（同名覆蓋）
        write_hourly_sheet(
            wb=wb,
            sheet_name=str(d),
            date_value=d,
            hours=hours,
            lineids=lineids,
            line_base_map=line_base_map,
            split_map=split_map,
            manpower_map=manpower_map,
        )

        # ✅ 2) KPI圖表：各Line（上午應達成/下午目標/總PCS加權）
        rows = []
        for lid in lineids:
            lid = str(lid)
            am_man = sum(_as_float(manpower_map.get((d, lid, int(h)), 0)) for h in AM_HOURS if h in hours)
            pm_man = sum(_as_float(manpower_map.get((d, lid, int(h)), 0)) for h in PM_HOURS if h in hours)

            am_target = math.trunc(target_per_mh * am_man)
            pm_target = math.trunc(target_per_mh * pm_man)

            pcs_w_map = line_base_map.get((lid, "加權PCS"), {})
            total_pcs_w = math.trunc(sum(float(pcs_w_map.get(int(h), 0) or 0) for h in hours))

            rows.append({
                "Line ID": lid,
                "上午應達成(加權)": am_target,
                "下午目標(加權)": pm_target,
                "總PCS(加權)": total_pcs_w,
            })

        line_kpi_df = pd.DataFrame(rows)
        add_line_kpi_chart_sheet(wb, date_str=str(d), line_kpi_df=line_kpi_df)

    # 存檔
    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue(), preserved


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

        st.session_state.pop("last_out_bytes", None)
        st.session_state.pop("last_out_name", None)
        st.session_state.pop("preserve_ok", None)

    dates = st.session_state["ship_line_prod_dates"]
    date_to_hours = st.session_state["ship_line_prod_date_to_hours"]
    date_to_lineids = st.session_state["ship_line_prod_date_to_lineids"]
    df_source = st.session_state["ship_line_prod_df"]

    # 人力輸入（手動）
    card_open("👥 人力輸入（手動輸入 / ✅不會跳格）")
    tabs = st.tabs(dates)
    manpower_by_date = {}

    for i, d in enumerate(dates):
        with tabs[i]:
            hours = date_to_hours.get(d, [])
            lineids = date_to_lineids.get(d, [])
            key = f"mp_{d}"

            mp_df = st.session_state.get(key)
            if mp_df is None:
                mp_df = _init_manpower_table(lineids, hours)
                st.session_state[key] = mp_df

            mp_df_new = render_manual_input_grid(d, mp_df, lineids=lineids, hours=hours)
            st.session_state[key] = mp_df_new
            manpower_by_date[d] = mp_df_new

    card_close()

    # 匯出
    card_open("📤 匯出 Excel（✅保留原檔分頁 + 新增 KPI圖表_日期 + 日期戰情表）")
    if st.button("產出並準備下載", use_container_width=True):
        try:
            out_bytes, preserved = build_output_excel_bytes(
                original_filename=up.name,
                original_bytes=raw,
                df_raw=df_source,
                target_per_mh=int(target_per_mh),
                manpower_by_date=manpower_by_date,
            )
            st.session_state["last_out_bytes"] = out_bytes
            st.session_state["preserve_ok"] = preserved

            base = os.path.splitext(up.name)[0]
            st.session_state["last_out_name"] = f"{base}_出貨作業線產能_保留原檔.xlsx"

            if preserved:
                st.success("已完成：匯出檔保留原本分頁，並新增 KPI圖表_日期 + 日期戰情表。")
            else:
                st.warning("來源檔非 xlsx/xlsm（或讀取失敗），無法保留原活頁簿；已改用新建活頁簿輸出。")
        except Exception as e:
            st.error(f"匯出失敗：{e}")

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
        st.caption("新增分頁：KPI圖表_YYYY-MM-DD（各Line：上午應達成/下午目標/總PCS加權）+ YYYY-MM-DD（日期戰情表）")
    else:
        st.info("請先按「產出並準備下載」。")
    card_close()


if __name__ == "__main__":
    main()
