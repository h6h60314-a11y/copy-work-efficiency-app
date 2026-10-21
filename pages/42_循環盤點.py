#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""42_循環盤點.py

獨立 Streamlit 頁面：上傳庫存明細與儲位明細（直接支援 .xls），
手動輸入棚別後，輸出與循環盤點紙本相同 9 欄的 A4 可列印 Excel。
依賴：streamlit, pandas, xlrd>=2.0.1, openpyxl
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.pagebreak import Break

try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close
except ImportError:
    def inject_logistics_theme():
        pass

    def set_page(title, icon="", subtitle=""):
        st.title(f"{icon} {title}")
        if subtitle:
            st.caption(subtitle)

    def card_open(title):
        st.subheader(title)

    def card_close():
        pass


OUTPUT_COLUMNS = ["序號", "商品碼", "實際商品", "實際效期", "系統效期", "儲位", "國際條碼", "國際條碼2", "品名"]
STOCK_FIELDS = {
    "商品碼": ("商品號", "商品碼", "商品編號", "貨號", "商品代碼", "SKU"),
    "儲位": ("儲位", "儲位編號", "儲位代碼"),
    "系統效期": ("商品效期", "效期", "有效期限", "系統效期", "有效日期"),
    "國際條碼": ("國際條碼", "國際條碼1", "商品條碼", "EAN", "條碼"),
    "國際條碼2": ("國際條碼2", "國際條碼二", "條碼2", "第二條碼", "商品條碼2"),
    "品名": ("全名", "品名", "商品名稱", "商品全名", "商品品名"),
}
LOCATION_FIELDS = {"儲位": ("儲位", "儲位編號", "儲位代碼"),
                   "棚別": ("棚別", "棚號", "棚別編號", "棚")}


def tidy(value):
    """保留儲位、條碼字首零；清除 Excel 數字常見的 '.0'。"""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y/%m/%d")
    if isinstance(value, date):
        return value.strftime("%Y/%m/%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if re.fullmatch(r"\d+\.0", text):
        return text[:-2]
    return text


def zone_normalize(value):
    text = tidy(value)
    if not text:
        return ""
    text = text.replace("棚", "").strip()
    if re.fullmatch(r"\d+", text):
        return str(int(text)).zfill(3)
    return text.upper()


def parse_zones(text):
    """支援 053、053,054、053-055、053～055、053棚。"""
    selected = set()
    for token in re.split(r"[,，、;；\s\n]+", text.strip()):
        if not token:
            continue
        token = token.replace("棚", "").strip()
        pair = re.fullmatch(r"(\d{1,3})\s*[-~～至]\s*(\d{1,3})", token)
        if pair:
            first, last = map(int, pair.groups())
            if first > last:
                raise ValueError(f"棚別範圍起訖顛倒：{token}")
            if last - first > 400:
                raise ValueError(f"棚別範圍過大：{token}")
            selected.update(f"{i:03d}" for i in range(first, last + 1))
        elif re.fullmatch(r"\d{1,3}", token):
            selected.add(f"{int(token):03d}")
        else:
            raise ValueError(f"無法辨識的棚別：{token}。請輸入 053 或 053-055。")
    if not selected:
        raise ValueError("請先輸入要盤點的棚別，例如 053")
    return sorted(selected)


def read_excel(uploaded):
    """直接讀取真正的 .xls，不經轉檔；第一個工作表。"""
    filename = getattr(uploaded, "name", "")
    suffix = Path(filename).suffix.lower()
    if suffix not in (".xls", ".xlsx"):
        raise ValueError(f"不支援的檔案格式：{filename}，請上傳 .xls 或 .xlsx")
    engine = "xlrd" if suffix == ".xls" else "openpyxl"
    try:
        raw = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()
        # 以 object 載入以盡量避免系統自動更改資料型態
        df = pd.read_excel(io.BytesIO(raw), sheet_name=0, dtype=object,
                           engine=engine, keep_default_na=False)
    except ImportError as exc:
        raise RuntimeError("環境缺少讀取舊版 XLS 的套件：請在 requirements.txt 加入 xlrd>=2.0.1") from exc
    except Exception as exc:
        raise ValueError(f"無法開啟 {filename}：{exc}") from exc
    df.columns = [tidy(c).replace("\n", "").strip() for c in df.columns]
    if df.empty:
        raise ValueError(f"{filename} 沒有資料")
    return df


def get_field_map(frame, aliases, title, required):
    by_name = {str(name).replace(" ", "").lower(): name for name in frame.columns}
    found = {}
    for logical, choices in aliases.items():
        col = next((by_name[c.replace(" ", "").lower()]
                    for c in choices if c.replace(" ", "").lower() in by_name), None)
        if col is None and logical in required:
            raise ValueError(f"{title}缺少「{logical}」欄位；目前欄位：{'、'.join(map(str, frame.columns[:25]))}")
        found[logical] = col
    return found


def format_expiry(value, datemode=0):
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.strftime("%Y/%m/%d")
    text = tidy(value)
    if not text:
        return ""
    if re.fullmatch(r"\d{8}", text):
        try:
            return datetime.strptime(text, "%Y%m%d").strftime("%Y/%m/%d")
        except ValueError:
            return text
    if re.fullmatch(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}", text):
        parts = re.split(r"[-/]", text)
        try:
            return date(*map(int, parts)).strftime("%Y/%m/%d")
        except ValueError:
            return text
    # 對於原始 Excel 儲存為數值的效期序號，按 Excel 日期還原
    if isinstance(value, (int, float)) and 20000 < value < 80000:
        base = datetime(1904, 1, 1) if datemode == 1 else datetime(1899, 12, 30)
        return (base + timedelta(days=float(value))).strftime("%Y/%m/%d")
    return text


def build_records(stock, locations, zones, include_empty=False):
    stock_cols = get_field_map(stock, STOCK_FIELDS, "庫存明細", required={"儲位", "商品碼", "品名"})
    loc_cols = get_field_map(locations, LOCATION_FIELDS, "儲位明細", required={"儲位", "棚別"})
    zone_set = set(zones)
    location_to_zone = {}
    conflicts = []
    for row in locations.to_dict("records"):
        location = tidy(row[loc_cols["儲位"]])
        zone = zone_normalize(row[loc_cols["棚別"]])
        if not location or not zone:
            continue
        previous = location_to_zone.get(location)
        if previous and previous != zone:
            conflicts.append((location, previous, zone))
        else:
            location_to_zone[location] = zone

    selected_locations = {slot: zone for slot, zone in location_to_zone.items() if zone in zone_set}
    records = []
    locations_with_stock = set()
    for row in stock.to_dict("records"):
        slot = tidy(row[stock_cols["儲位"]])
        zone = selected_locations.get(slot)
        if zone is None:
            continue
        # 不自動合併不同效期/批次的紀錄，避免漏盤。
        item = {"棚別": zone, "儲位": slot}
        for field in OUTPUT_COLUMNS:
            if field in ("序號", "實際商品", "實際效期", "儲位"):
                continue
            col = stock_cols.get(field)
            item[field] = tidy(row[col]) if col is not None else ""
        item["系統效期"] = format_expiry(row[stock_cols["系統效期"]]) if stock_cols["系統效期"] else ""
        if not any(item[key] for key in ("商品碼", "系統效期", "國際條碼", "國際條碼2", "品名")):
            continue
        records.append(item)
        locations_with_stock.add(slot)

    if include_empty:
        for slot, zone in selected_locations.items():
            if slot not in locations_with_stock:
                records.append({"棚別": zone, **{c: slot if c == "儲位" else "" for c in OUTPUT_COLUMNS}})
    records.sort(key=lambda r: (r["棚別"], r["儲位"], r["品名"], r["系統效期"]))
    info = {
        "指定棚別": ", ".join(zones),
        "找到儲位": len(selected_locations),
        "有庫存儲位": len(locations_with_stock),
        "盤點明細": len(records),
        "空儲位": len(selected_locations) - len(locations_with_stock),
        "棚別衝突": conflicts,
        "找不到的棚別": sorted(zone_set - set(selected_locations.values())),
    }
    return records, info


def export_workbook(rows, info):
    """9 欄盤點表；盤點日期、起訖時間、棚別僅在列印頁首，不佔工作表儲存格。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "循環盤點單"
    ws.sheet_view.showGridLines = False

    # 第一列就是表格標題；不得插入任何日期／時間／棚別儲存格。
    ws.append(OUTPUT_COLUMNS)
    for number, rec in enumerate(rows, 1):
        ws.append([number if col == "序號" else "" if col in ("實際商品", "實際效期")
                   else rec.get(col, "") for col in OUTPUT_COLUMNS])
    ws.freeze_panes = "C2"
    border_side = Side(style="thin", color="666666")
    for cell in ws[1]:
        cell.font = Font(name="Microsoft JhengHei", size=10, bold=True)
        cell.fill = PatternFill("solid", fgColor="E8EDF2")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
    ws.row_dimensions[1].height = 25
    for row in ws.iter_rows(min_row=2, max_col=9):
        ws.row_dimensions[row[0].row].height = 23
        for col_index, cell in enumerate(row, 1):
            cell.font = Font(name="Microsoft JhengHei", size=9)
            cell.alignment = Alignment(horizontal="center" if col_index <= 4 else "left",
                                       vertical="center", wrap_text=(col_index == 9))
            cell.border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)
            if col_index in (2, 6, 7, 8):
                cell.number_format = "@"
    for col, width in {"A": 7, "B": 13, "C": 12, "D": 13, "E": 16,
                       "F": 15, "G": 20, "H": 20, "I": 48}.items():
        ws.column_dimensions[col].width = width

    ws.print_options.horizontalCentered = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:1"
    ws.print_area = f"A1:I{max(ws.max_row, 1)}"
    # 頁首預留兩行高度；頁首會在列印預覽及紙張上顯示，普通檢視不會出現。
    ws.page_margins = PageMargins(left=0.20, right=0.20, top=0.70, bottom=0.48,
                                   header=0.25, footer=0.23)
    ws.oddHeader.left.text = "盤點日期：\n盤點棚別：" + str(info["指定棚別"])
    ws.oddHeader.center.text = "開始時間：____________"
    ws.oddHeader.right.text = "結束時間：____________"
    ws.oddHeader.left.size = 10
    ws.oddHeader.center.size = 10
    ws.oddHeader.right.size = 10
    ws.oddFooter.center.text = "第 &P 頁，共 &N 頁"
    ws.oddFooter.center.size = 10

    # 第 1 列為表頭；每頁固定 20 筆，後續頁面重印表頭。
    # 在第 21、41、61... 筆資料之後插入手動分頁線。
    for record_count in range(20, len(rows), 20):
        ws.row_breaks.append(Break(id=record_count + 1))

    if info["棚別衝突"] or info["找不到的棚別"]:
        audit = wb.create_sheet("待確認")
        audit.append(["問題", "儲位/棚別", "內容1", "內容2"])
        for slot, prev, curr in info["棚別衝突"]:
            audit.append(["儲位對應多個棚別", slot, prev, curr])
        for zone in info["找不到的棚別"]:
            audit.append(["找不到指定棚別", zone, "", ""])
        for col, width in {"A": 25, "B": 25, "C": 18, "D": 18}.items():
            audit.column_dimensions[col].width = width
    memory = io.BytesIO()
    wb.save(memory)
    return memory.getvalue()


def main():
    inject_logistics_theme()
    set_page("循環盤點", icon="📋", subtitle="依指定棚別從庫存與儲位明細產生可列印 Excel 盤點單。")
    card_open("循環盤點 Excel 匯出")
    st.caption("獨立第 42 頁。原始 .xls 可直接讀取，不需先另存成 .xlsx。")
    first, second = st.columns(2)
    with first:
        stock_file = st.file_uploader("① 上傳庫存明細", type=["xls", "xlsx"], key="cycle_stock")
    with second:
        location_file = st.file_uploader("② 上傳儲位／棚別明細", type=["xls", "xlsx"], key="cycle_location")
    zone_text = st.text_input("③ 手動輸入要盤點的棚別", placeholder="例如：053 或 053,054 或 053-055")
    include_empty = st.checkbox("盤點單包含指定棚別中沒有庫存的儲位", value=False,
                                help="預設只輸出有庫存的商品明細；勾選後空儲位也會各新增一列。")
    if st.button("產生循環盤點 Excel", type="primary", use_container_width=True,
                 disabled=not(stock_file and location_file and zone_text.strip())):
        try:
            zones = parse_zones(zone_text)
            stock = read_excel(stock_file)
            locations = read_excel(location_file)
            rows, info = build_records(stock, locations, zones, include_empty)
            if not rows:
                raise ValueError("指定棚別沒有符合的盤點資料，請確認棚別、儲位與庫存明細。")
            st.session_state["cycle_42_result"] = (export_workbook(rows, info), info, zones)
        except Exception as exc:
            st.session_state.pop("cycle_42_result", None)
            st.error(f"處理失敗：{exc}")
    result = st.session_state.get("cycle_42_result")
    if result:
        data, info, zones = result
        st.success("循環盤點 Excel 已產出")
        a, b, c, d = st.columns(4)
        a.metric("指定棚別儲位", info["找到儲位"])
        b.metric("有庫存儲位", info["有庫存儲位"])
        c.metric("盤點明細", info["盤點明細"])
        d.metric("空儲位", info["空儲位"])
        if info["找不到的棚別"]:
            st.warning("儲位明細找不到棚別：" + ", ".join(info["找不到的棚別"]))
        if info["棚別衝突"]:
            st.warning(f"有 {len(info['棚別衝突'])} 筆儲位存在不同棚別對應，詳見 Excel「待確認」分頁。")
        st.download_button("下載循環盤點單 Excel", data=data,
                           file_name=f"循環盤點_{'_'.join(zones)}_{datetime.now():%Y%m%d}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    card_close()


if __name__ == "__main__":
    main()
