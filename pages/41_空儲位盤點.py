#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""企劃課｜空儲位盤點：以儲位明細比對棚別並匯出四欄盤點 Excel。"""
from __future__ import annotations

import io
import re
import struct
import zipfile
from datetime import datetime

import streamlit as st
import pandas as pd
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
    try:
        from pyxlsb import open_workbook

        with open_workbook(io.BytesIO(data)) as workbook:
            with workbook.get_sheet(1) as sheet:
                standard = [
                    {cell.c: clean(cell.v) for cell in row if cell.v is not None}
                    for row in sheet.rows(sparse=False)
                ]
        if standard and '儲位' in set(standard[0].values()):
            return standard
    except Exception:
        # 部分 WMS 匯出的 XLSB 採內嵌文字記錄，改由下方直接解析。
        pass

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


def read_xls(data):
    frame = pd.read_excel(
        io.BytesIO(data),
        sheet_name=0,
        dtype=object,
        engine='xlrd',
        keep_default_na=False,
    )
    columns = [clean(column).replace('\n', '').strip() for column in frame.columns]
    rows = [{index: columns[index] for index in range(len(columns))}]
    rows.extend(
        {
            index: clean(value)
            for index, value in enumerate(values)
            if clean(value)
        }
        for values in frame.itertuples(index=False, name=None)
    )
    return rows


def read_rows(filename, data):
    lower_name = filename.lower()
    if lower_name.endswith('.xlsb'):
        return read_xlsb(data)
    if lower_name.endswith('.xlsx'):
        return read_xlsx(data)
    if lower_name.endswith('.xls'):
        return read_xls(data)
    raise ValueError(f'不支援的檔案格式：{filename}')


def get_headers(rows, filename, required):
    if not rows:
        raise ValueError(f'{filename} 找不到資料')
    headers = {clean(value).replace('\n', '').strip(): key for key, value in rows[0].items()}
    missing = [column for column in required if column not in headers]
    if missing:
        raise ValueError(f'{filename} 第一張工作表缺少「{"、".join(missing)}」欄位')
    return headers


def filter_slots(empty_filename, empty_data, detail_filename, detail_data):
    source_rows = read_rows(empty_filename, empty_data)
    detail_rows = read_rows(detail_filename, detail_data)
    source_headers = get_headers(source_rows, empty_filename, ['儲位'])
    detail_headers = get_headers(detail_rows, detail_filename, ['儲位', '棚別'])

    source_location_column = source_headers['儲位']
    source_bay_column = source_headers.get('棚別')
    detail_location_column = detail_headers['儲位']
    detail_bay_column = detail_headers['棚別']

    review = []
    location_to_bay = {}
    for detail_row_number, row in enumerate(detail_rows[1:], start=2):
        location = clean(row.get(detail_location_column))
        bay = clean(row.get(detail_bay_column))
        if not location and not bay:
            continue
        if not location:
            review.append(('儲位明細', detail_row_number, '', '', bay, '儲位空白'))
            continue
        if not bay:
            review.append(('儲位明細', detail_row_number, location, '', '', '棚別空白'))
            continue
        previous = location_to_bay.get(location)
        if previous and previous != bay:
            review.append(
                ('儲位明細', detail_row_number, location, previous, bay, '同一儲位對應不同棚別')
            )
            continue
        location_to_bay[location] = bay

    kept = []
    excluded = 0
    matched = 0
    for source_row_number, row in enumerate(source_rows[1:], start=2):
        location = clean(row.get(source_location_column))
        source_bay = clean(row.get(source_bay_column)) if source_bay_column is not None else ''
        if not location and not source_bay:
            continue
        if not location:
            review.append(('空儲位清單', source_row_number, '', source_bay, '', '儲位空白'))
            continue
        detail_bay = location_to_bay.get(location, '')
        if not detail_bay:
            review.append(
                ('空儲位清單', source_row_number, location, source_bay, '', '儲位明細找不到儲位')
            )
            continue
        matched += 1
        if source_bay and clean(source_bay).zfill(3) != clean(detail_bay).zfill(3):
            review.append(
                ('空儲位清單', source_row_number, location, source_bay, detail_bay, '棚別不一致；採用儲位明細')
            )
        try:
            bay_number = int(detail_bay)
        except (ValueError, TypeError):
            review.append(
                ('空儲位清單', source_row_number, location, source_bay, detail_bay, '棚別無法辨識')
            )
            continue
        if any(low <= bay_number <= high for low, high in EXCLUDED_RANGES):
            excluded += 1
        else:
            kept.append(location)
    info = {
        '原始資料列': len(source_rows) - 1,
        '成功比對': matched,
        '排除棚別': excluded,
        '保留儲位': len(kept),
        '待確認': len(review),
    }
    return kept, review, info


def read_locked_slots(data):
    """讀取最新版鎖庫表，只取「鎖庫商品儲位」分頁的儲位欄位。"""
    workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        if '鎖庫商品儲位' not in workbook.sheetnames:
            raise ValueError('鎖庫清單缺少「鎖庫商品儲位」分頁')
        iterator = workbook['鎖庫商品儲位'].iter_rows(values_only=True)
        header = next(iterator, None)
        if not header:
            raise ValueError('鎖庫清單是空白的')
        columns = {clean(value): index for index, value in enumerate(header) if value is not None}
        target_columns = [
            columns[column]
            for column in ('鎖庫儲位', '實際儲位')
            if column in columns
        ]
        if not target_columns:
            raise ValueError('鎖庫清單找不到「鎖庫儲位」或「實際儲位」欄位')
        codes = set()
        for row in iterator:
            for index in target_columns:
                if index >= len(row):
                    continue
                for piece in re.split(r'[,，、;；\n]+', clean(row[index])):
                    code = piece.strip().upper()
                    if code:
                        codes.add(code)
        return codes
    finally:
        workbook.close()


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
        other.append(['來源', '原始列號', '儲位', '空儲位清單棚別', '儲位明細棚別', '原因'])
        for item in review:
            other.append(item)
        for column, width in {
            'A': 18,
            'B': 14,
            'C': 22,
            'D': 20,
            'E': 18,
            'F': 30,
        }.items():
            other.column_dimensions[column].width = width
    data = io.BytesIO()
    workbook.save(data)
    return data.getvalue()


def main():
    inject_logistics_theme()
    set_page(
        '空儲位盤點',
        icon='📍',
        subtitle='上傳空儲位清單與儲位明細，比對棚別後產出盤點 Excel。',
    )
    card_open('空儲位盤點')
    st.info('自動排除：001–020 棚、031–038 棚、061–081 棚、401–403 棚')
    first_column, second_column, third_column = st.columns(3)
    with first_column:
        empty_file = st.file_uploader(
            '① 上傳空儲位清單（.xlsb / .xlsx）',
            type=['xlsb', 'xlsx'],
            key='empty_slot_list',
        )
    with second_column:
        detail_file = st.file_uploader(
            '② 上傳儲位明細（.xls / .xlsx）',
            type=['xls', 'xlsx'],
            key='empty_slot_location_detail',
        )
    with third_column:
        locked_file = st.file_uploader(
            '③ 上傳最新版鎖庫商品清單（.xlsx）',
            type=['xlsx'],
            key='locked_source_41',
            help='讀取「鎖庫商品儲位」分頁；每次請上傳最新版本。',
        )
    if empty_file is not None and detail_file is not None and locked_file is not None:
        try:
            slots, review, info = filter_slots(
                empty_file.name,
                empty_file.getvalue(),
                detail_file.name,
                detail_file.getvalue(),
            )
            locked_slots = read_locked_slots(locked_file.getvalue())
            kept_slots = [slot for slot in slots if slot.upper() not in locked_slots]
            info['排除鎖庫儲位'] = len(slots) - len(kept_slots)
            info['保留儲位'] = len(kept_slots)
            if not kept_slots:
                st.warning('比對棚別並排除指定棚別與鎖庫儲位後，沒有可匯出的儲位。')
            else:
                metrics = st.columns(len(info))
                for column, (label, value) in zip(metrics, info.items()):
                    column.metric(label, value)
                st.download_button(
                    '下載空儲位盤點 Excel',
                    export_excel(kept_slots, review),
                    file_name=f'空儲位盤點_{datetime.now():%Y%m%d}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    type='primary',
                    use_container_width=True,
                )
                if review:
                    st.warning(
                        f'有 {len(review)} 筆比對異常，'
                        '請查看匯出檔案的「待確認」工作表。'
                    )
                st.caption(f'鎖庫清單儲位代碼共 {len(locked_slots)} 個。')
        except Exception as exc:
            st.error(f'處理失敗：{exc}')
    else:
        st.info('請上傳空儲位清單、儲位明細與當次最新版鎖庫商品清單。')
    card_close()


if __name__ == '__main__':
    main()


