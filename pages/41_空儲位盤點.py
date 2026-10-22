#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""企劃課｜空儲位盤點：上傳 XLSB/XLSX，排除棚別並匯出四欄盤點 Excel。"""
from __future__ import annotations

import io
import struct
import zipfile
from datetime import datetime

import streamlit as st
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close
except ImportError:
    # 可獨立使用 Streamlit 測試
    def inject_logistics_theme(): pass
    def set_page(title, icon='', subtitle=''):
        st.title(f'{icon} {title}')
        st.caption(subtitle)
    def card_open(title): st.subheader(title)
    def card_close(): pass

EXCLUDED_RANGES = ((1, 20), (31, 38), (61, 81), (401, 403))


def clean(value):
    if value is None:
        return ''
    s = str(value).strip()
    return s[:-2] if s.endswith('.0') and s[:-2].isdigit() else s


def biff_record(stream):
    first = stream.read(1)
    if not first:
        return None, b''
    kind = first[0]
    if kind & 0x80:
        second = stream.read(1)
        if not second:
            raise ValueError('XLSB 記錄不完整')
        kind = (kind & 0x7f) | (second[0] << 7)
    length = 0
    for i in range(4):
        part = stream.read(1)
        if not part:
            raise ValueError('XLSB 長度資料不完整')
        b = part[0]
        length |= (b & 0x7f) << (i * 7)
        if b < 128:
            break
    payload = stream.read(length)
    if len(payload) != length:
        raise ValueError('XLSB 儲存格資料不完整')
    return kind, payload


def read_xlsb(data):
    """先使用一般讀取器；若 Excel 採內嵌文字記錄則直接解析 XLSB。"""
    from pyxlsb import open_workbook
    with open_workbook(io.BytesIO(data)) as wb:
        with wb.get_sheet(1) as sheet:
            standard = [{cell.c: clean(cell.v) for cell in row if cell.v is not None}
                        for row in sheet.rows(sparse=False)]
    if standard and {'儲位', '棚別'} <= set(standard[0].values()):
        return standard

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        paths = sorted(p for p in archive.namelist()
                       if p.startswith('xl/worksheets/sheet') and p.endswith('.bin'))
        if not paths:
            raise ValueError('找不到 XLSB 工作表')
        stream = io.BytesIO(archive.read(paths[0]))
    rows = []
    current = None
    while True:
        kind, payload = biff_record(stream)
        if kind is None:
            break
        if kind == 0:  # BrtRowHdr
            current = {}
            rows.append(current)
        elif kind == 0x3e and current is not None and len(payload) >= 13:  # BrtCellSt
            col = struct.unpack_from('<I', payload, 0)[0]
            count = struct.unpack_from('<I', payload, 9)[0]
            if count <= 32767 and 13 + 2 * count <= len(payload):
                current[col] = payload[13:13 + count * 2].decode('utf-16le', errors='replace').strip()
    return rows


def read_xlsx(data):
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        return [{i: clean(v) for i, v in enumerate(values) if v is not None}
                for values in wb.worksheets[0].iter_rows(values_only=True)]
    finally:
        wb.close()


def filter_slots(filename, data):
    rows = read_xlsb(data) if filename.lower().endswith('.xlsb') else read_xlsx(data)
    if not rows:
        raise ValueError('找不到資料')
    headers = {clean(v): k for k, v in rows[0].items()}
    if '儲位' not in headers or '棚別' not in headers:
        raise ValueError('第一張工作表必須有「儲位」和「棚別」欄位')
    loc_col, bay_col = headers['儲位'], headers['棚別']
    kept, review = [], []
    excluded = 0
    for source_row, row in enumerate(rows[1:], start=2):
        loc, bay = clean(row.get(loc_col)), clean(row.get(bay_col))
        if not loc and not bay:
            continue
        try:
            bay_no = int(bay)
        except (ValueError, TypeError):
            review.append((source_row, loc, bay, '棚別無法辨識'))
            continue
        if any(low <= bay_no <= high for low, high in EXCLUDED_RANGES):
            excluded += 1
        elif not loc:
            review.append((source_row, loc, bay, '儲位空白'))
        else:
            kept.append(loc)
    return kept, excluded, review, len(rows) - 1




def read_locked_slots(data):
    """每次讀取最新鎖庫表，僅取「鎖庫商品儲位」分頁的儲位欄位。"""
    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        if '鎖庫商品儲位' not in wb.sheetnames:
            raise ValueError('鎖庫清單缺少「鎖庫商品儲位」分頁')
        iterator = wb['鎖庫商品儲位'].iter_rows(values_only=True)
        head = next(iterator, None)
        if not head:
            raise ValueError('鎖庫清單是空白的')
        cols = {clean(value): idx for idx, value in enumerate(head) if value is not None}
        target_cols = [cols[c] for c in ('鎖庫儲位', '實際儲位') if c in cols]
        if not target_cols:
            raise ValueError('鎖庫清單找不到「鎖庫儲位」或「實際儲位」欄位')
        codes = set()
        for row in iterator:
            for idx in target_cols:
                if idx >= len(row):
                    continue
                raw = clean(row[idx])
                # 有些儲位以逗號或換行列出多個；不拆分含斜線的描述
                import re
                for piece in re.split(r'[,，、;；\n]+', raw):
                    code = piece.strip().upper()
                    if code:
                        codes.add(code)
        return codes
    finally:
        wb.close()

def export_excel(slots, review):
    wb = Workbook()
    ws = wb.active
    ws.title = '空儲位盤點'
    ws.append(['儲位', '是否', '儲位', '是否'])
    midpoint = (len(slots) + 1) // 2
    for i in range(midpoint):
        ws.append([slots[i], '', slots[midpoint + i] if midpoint + i < len(slots) else '', ''])
    ws.freeze_panes = 'A2'
    for col, width in {'A': 22, 'B': 12, 'C': 22, 'D': 12}.items():
        ws.column_dimensions[col].width = width
    edge = Side(style='thin', color='BEC6CE')
    for row in ws:
        for cell in row:
            cell.border = Border(bottom=edge, right=edge)
            cell.alignment = Alignment(vertical='center')
            cell.font = Font(name='Microsoft JhengHei', size=11)
            if cell.row == 1:
                cell.font = Font(name='Microsoft JhengHei', color='FFFFFF', bold=True)
                cell.fill = PatternFill('solid', fgColor='274B6B')
        ws.row_dimensions[row[0].row].height = 21
    if review:
        other = wb.create_sheet('待確認')
        other.append(['原始列號', '儲位', '棚別', '原因'])
        for item in review:
            other.append(item)
        for col, width in {'A': 16, 'B': 22, 'C': 14, 'D': 28}.items():
            other.column_dimensions[col].width = width
    data = io.BytesIO()
    wb.save(data)
    return data.getvalue()


def main():
    inject_logistics_theme()
    set_page('空儲位盤點', icon='📍', subtitle='上傳空儲位清單，自動排除指定棚別並產出盤點 Excel。')
    card_open('空儲位盤點')
    st.info('自動排除：001–020 棚、031–038 棚、061–081 棚、401–403 棚')
    file = st.file_uploader('① 上傳空儲位清單（.xlsb / .xlsx）', type=['xlsb', 'xlsx'], key='empty_source_41')
    locked_file = st.file_uploader('② 上傳最新版鎖庫商品清單（.xlsx）', type=['xlsx'], key='locked_source_41',
                                   help='讀取「鎖庫商品儲位」分頁；每次請上傳最新版本，避免沿用舊清單。')
    if file is not None and locked_file is not None:
        try:
            slots, excluded, review, total = filter_slots(file.name, file.getvalue())
            locked_slots = read_locked_slots(locked_file.getvalue())
            kept = [slot for slot in slots if slot.upper() not in locked_slots]
            locked_excluded = len(slots) - len(kept)
            if not kept:
                st.warning('排除指定棚別與鎖庫儲位後，沒有可匯出的儲位。')
            else:
                a, b, c, d = st.columns(4)
                a.metric('原始資料列', total)
                b.metric('排除棚別', excluded)
                c.metric('排除鎖庫儲位', locked_excluded)
                d.metric('保留儲位', len(kept))
                st.caption(f'待確認資料：{len(review)} 筆；鎖庫清單儲位代碼共 {len(locked_slots)} 個')
                st.download_button('下載空儲位盤點 Excel', export_excel(kept, review),
                                   file_name=f'空儲位盤點_{datetime.now():%Y%m%d}.xlsx',
                                   mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                   type='primary', use_container_width=True)
                if review:
                    st.warning(f'有 {len(review)} 筆資料無法辨識，請查看匯出檔案的「待確認」工作表。')
        except Exception as exc:
            st.error(f'處理失敗：{exc}')
    else:
        st.caption('請上傳空儲位清單與當次最新版的鎖庫清單，才會產生匯出檔。')
    card_close()


if __name__ == '__main__':
    main()
