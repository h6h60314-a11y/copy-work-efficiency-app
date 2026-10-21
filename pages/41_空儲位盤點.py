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

from common_ui import card_close, card_open, inject_logistics_theme, set_page


EXCLUDED_RANGES = ((1, 20), (31, 38), (61, 81), (401, 403))


def clean(value):
    if value is None:
        return ''
    text = str(value).strip()
    return text[:-2] if text.endswith('.0') and text[:-2].isdigit() else text


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
    for index in range(4):
        part = stream.read(1)
        if not part:
            raise ValueError('XLSB 長度資料不完整')
        byte = part[0]
        length |= (byte & 0x7f) << (index * 7)
        if byte < 128:
            break
    payload = stream.read(length)
    if len(payload) != length:
        raise ValueError('XLSB 儲存格資料不完整')
    return kind, payload


def read_xlsb(data):
    """先使用一般讀取器；若 Excel 採內嵌文字記錄則直接解析 XLSB。"""
    from pyxlsb import open_workbook

    with open_workbook(io.BytesIO(data)) as workbook:
        with workbook.get_sheet(1) as sheet:
            standard = [
                {cell.c: clean(cell.v) for cell in row if cell.v is not None}
                for row in sheet.rows(sparse=False)
            ]
    if standard and {'儲位', '棚別'} <= set(standard[0].values()):
        return standard

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        paths = sorted(
            path
            for path in archive.namelist()
            if path.startswith('xl/worksheets/sheet') and path.endswith('.bin')
        )
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
            column = struct.unpack_from('<I', payload, 0)[0]
            count = struct.unpack_from('<I', payload, 9)[0]
            if count <= 32767 and 13 + 2 * count <= len(payload):
                current[column] = payload[13:13 + count * 2].decode(
                    'utf-16le', errors='replace'
                ).strip()
    return rows


def read_xlsx(data):
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        return [
            {index: clean(value) for index, value in enumerate(values) if value is not None}
            for values in workbook.worksheets[0].iter_rows(values_only=True)
        ]
    finally:
        workbook.close()


def filter_slots(filename, data):
    rows = read_xlsb(data) if filename.lower().endswith('.xlsb') else read_xlsx(data)
    if not rows:
        raise ValueError('找不到資料')
    headers = {clean(value): key for key, value in rows[0].items()}
    if '儲位' not in headers or '棚別' not in headers:
        raise ValueError('第一張工作表必須有「儲位」和「棚別」欄位')
    location_column, bay_column = headers['儲位'], headers['棚別']
    kept, review = [], []
    excluded = 0
    for source_row, row in enumerate(rows[1:], start=2):
        location = clean(row.get(location_column))
        bay = clean(row.get(bay_column))
        if not location and not bay:
            continue
        try:
            bay_number = int(bay)
        except (ValueError, TypeError):
            review.append((source_row, location, bay, '棚別無法辨識'))
            continue
        if any(low <= bay_number <= high for low, high in EXCLUDED_RANGES):
            excluded += 1
        elif not location:
            review.append((source_row, location, bay, '儲位空白'))
        else:
            kept.append(location)
    return kept, excluded, review, len(rows) - 1


def export_excel(slots, review):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = '空儲位盤點'
    sheet.append(['儲位', '是否', '儲位', '是否'])
    midpoint = (len(slots) + 1) // 2
    for index in range(midpoint):
        sheet.append([
            slots[index],
            '',
            slots[midpoint + index] if midpoint + index < len(slots) else '',
            '',
        ])
    sheet.freeze_panes = 'A2'
    for column, width in {'A': 22, 'B': 12, 'C': 22, 'D': 12}.items():
        sheet.column_dimensions[column].width = width
    edge = Side(style='thin', color='BEC6CE')
    for row in sheet:
        for cell in row:
            cell.border = Border(bottom=edge, right=edge)
            cell.alignment = Alignment(vertical='center')
            cell.font = Font(name='Microsoft JhengHei', size=11)
            if cell.row == 1:
                cell.font = Font(name='Microsoft JhengHei', color='FFFFFF', bold=True)
                cell.fill = PatternFill('solid', fgColor='274B6B')
        sheet.row_dimensions[row[0].row].height = 21
    if review:
        other = workbook.create_sheet('待確認')
        other.append(['原始列號', '儲位', '棚別', '原因'])
        for item in review:
            other.append(item)
        for column, width in {'A': 16, 'B': 22, 'C': 14, 'D': 28}.items():
            other.column_dimensions[column].width = width
    data = io.BytesIO()
    workbook.save(data)
    return data.getvalue()


def main():
    inject_logistics_theme()
    set_page(
        '空儲位盤點',
        icon='📍',
        subtitle='上傳空儲位清單，自動排除指定棚別並產出盤點 Excel。',
    )
    card_open('空儲位盤點')
    st.info('自動排除：001–020 棚、031–038 棚、061–081 棚、401–403 棚')
    uploaded_file = st.file_uploader(
        '上傳空儲位清單（.xlsb / .xlsx）',
        type=['xlsb', 'xlsx'],
    )
    if uploaded_file is not None:
        try:
            slots, excluded, review, total = filter_slots(
                uploaded_file.name,
                uploaded_file.getvalue(),
            )
            if not slots:
                st.warning('篩選後沒有可匯出的儲位。')
            else:
                original_column, excluded_column, kept_column, review_column = st.columns(4)
                original_column.metric('原始資料列', total)
                excluded_column.metric('排除棚別', excluded)
                kept_column.metric('保留儲位', len(slots))
                review_column.metric('待確認', len(review))
                st.download_button(
                    '下載空儲位盤點 Excel',
                    export_excel(slots, review),
                    file_name=f'空儲位盤點_{datetime.now():%Y%m%d}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    type='primary',
                    use_container_width=True,
                )
                if review:
                    st.warning(
                        f'有 {len(review)} 筆資料無法辨識，'
                        '請查看匯出檔案的「待確認」工作表。'
                    )
        except Exception as exc:
            st.error(f'處理失敗：{exc}')
    card_close()


if __name__ == '__main__':
    main()
