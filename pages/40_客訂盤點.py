#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""客訂 + 手動異常商品總盤點，支援 .xls/.xlsx，匯出單一盤點明細。

操作：上傳客訂明細（選填，可多檔）、庫存明細、儲位明細；
      手動貼上商品號、國際條碼或條碼2（多筆），按一下產出異常總盤點。
套件：streamlit, pandas, openpyxl, xlrd>=2.0.1
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from common_ui import card_close, card_open, inject_logistics_theme, set_page

HEADERS = [
    '商品號', '實際數量', '實際效期', '儲位', '國際條碼', '條碼2', '全名',
    '數量', '已試算', '已揀取', 'Canuseqty', '商品效期', '棚別', '盤點來源',
]
STOCK_REQUIRED = {
    '商品號', '儲位', '國際條碼', '條碼2', '全名', '數量',
    '已試算', '已揀取', 'Canuseqty', '商品效期',
}


def norm(value):
    """比對一律以字串，保留前置 0。"""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ''
    text = str(value).strip()
    return text[:-2] if re.fullmatch(r'\d+\.0', text) else text


def parse_manual_codes(text):
    """每行一碼，亦支援逗號、頓號、分號及 Tab 分隔；去重不更改前置 0。"""
    return list(dict.fromkeys(
        code for code in (norm(x) for x in re.split(r'[,，、;；\t\r\n\s]+', text or ''))
        if code
    ))


def load_excel(source):
    name = getattr(source, 'name', str(source))
    suffix = name.lower().rsplit('.', 1)[-1] if '.' in name else ''
    if suffix not in ('xls', 'xlsx'):
        raise ValueError(f'不支援的格式：{name}，請使用 .xls/.xlsx')
    engine = 'xlrd' if suffix == 'xls' else 'openpyxl'
    if hasattr(source, 'seek'):
        source.seek(0)
    try:
        frame = pd.read_excel(source, dtype=str, engine=engine, keep_default_na=False)
    except ImportError as exc:
        raise RuntimeError('缺少 Excel 讀取套件，請安裝 pandas openpyxl xlrd>=2.0.1') from exc
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame


def make_records(orders, stock, locations, manual_codes=()):
    """客訂商品與手動輸入商品取聯集；一筆庫存只出現一次。"""
    for i, order in enumerate(orders, 1):
        if '商品' not in order.columns:
            raise ValueError(f'客訂第 {i} 份缺少「商品」欄位')
    missing = STOCK_REQUIRED - set(stock.columns)
    if missing:
        raise ValueError('庫存缺少欄位：' + '、'.join(sorted(missing)))
    if not {'儲位', '棚別'} <= set(locations.columns):
        raise ValueError('儲位明細缺少「儲位」或「棚別」欄位')

    customer_products = {
        norm(v) for df in orders for v in df['商品'] if norm(v)
    }
    manual_set = set(manual_codes)
    if not customer_products and not manual_set:
        raise ValueError('請上傳至少一份客訂明細，或手動輸入至少一個商品碼／條碼')

    locmap = {}
    for _, r in locations.iterrows():
        slot = norm(r['儲位'])
        if slot and slot not in locmap:
            locmap[slot] = norm(r['棚別'])

    rows = []
    matched_customers, matched_manual = set(), set()
    bad_locations = set()
    for _, r in stock.iterrows():
        sku = norm(r['商品號'])
        barcode1 = norm(r['國際條碼'])
        barcode2 = norm(r['條碼2'])
        from_customer = sku in customer_products
        manual_hits = manual_set.intersection(x for x in (sku, barcode1, barcode2) if x)
        if not from_customer and not manual_hits:
            continue
        if from_customer:
            matched_customers.add(sku)
        matched_manual.update(manual_hits)
        slot = norm(r['儲位'])
        shelf = locmap.get(slot, '')
        if not shelf:
            bad_locations.add(slot or '(空白儲位)')
        source = '客訂＋手動異常' if from_customer and manual_hits else (
            '客訂' if from_customer else '手動異常'
        )
        rows.append([
            sku, '', '', slot, barcode1, barcode2, norm(r['全名']),
            norm(r['數量']), norm(r['已試算']), norm(r['已揀取']),
            norm(r['Canuseqty']), norm(r['商品效期']), shelf, source,
        ])

    info = {
        '客訂商品數': len(customer_products),
        '手動輸入數': len(manual_set),
        '客訂匹配商品': len(matched_customers),
        '手動匹配條碼': len(matched_manual),
        '盤點筆數': len(rows),
        '客訂筆數': sum('客訂' in r[13] for r in rows),
        '手動異常筆數': sum('手動異常' in r[13] for r in rows),
        '重疊筆數': sum(r[13] == '客訂＋手動異常' for r in rows),
        '無庫存商品': sorted(customer_products - matched_customers),
        '無法匹配手動條碼': sorted(manual_set - matched_manual),
        '無棚別儲位': sorted(bad_locations),
    }
    # 相容原本介面的資訊鍵
    info['商品數'] = len(customer_products)
    return rows, info


def as_date(value):
    if isinstance(value, (date, datetime)):
        return value
    text = norm(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return text


def as_number(value):
    text = norm(value)
    if not text:
        return None
    try:
        n = float(text.replace(',', ''))
        return int(n) if n.is_integer() else n
    except ValueError:
        return text


def save_report(rows, info, output):
    wb = Workbook()
    ws = wb.active
    ws.title = '異常總盤點'
    ws.append(HEADERS)
    for row in rows:
        ws.append([
            as_number(v) if i in (7, 8, 9, 10) else as_date(v) if i == 11 else v
            for i, v in enumerate(row)
        ])
    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:N{max(ws.max_row, 2)}'
    for cell in ws[1]:
        cell.font = Font(name='Microsoft JhengHei', bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor='234B70')
        cell.alignment = Alignment(horizontal='center')
    widths = [16, 14, 15, 17, 20, 18, 50, 12, 12, 12, 15, 17, 16, 20]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name='Microsoft JhengHei', size=10)
            if cell.column in (2, 3):
                cell.fill = PatternFill('solid', fgColor='FFF2CE')
            if cell.column == 12 and isinstance(cell.value, (date, datetime)):
                cell.number_format = 'yyyy/mm/dd'
            if cell.column == 14 and cell.value == '客訂＋手動異常':
                cell.fill = PatternFill('solid', fgColor='DDEBF7')
            if cell.column in (1, 4, 5, 6):
                cell.number_format = '@'

    issues = [
        ('客訂無庫存商品', v, '客訂商品號在庫存檔沒有對應紀錄') for v in info['無庫存商品']
    ] + [
        ('手動輸入未匹配', v, '商品號、國際條碼、條碼2 都找不到此代碼')
        for v in info['無法匹配手動條碼']
    ] + [
        ('無棚別儲位', v, '儲位明細找不到對應棚別') for v in info['無棚別儲位']
    ]
    if issues:
        audit = wb.create_sheet('待確認')
        audit.append(['類型', '代碼', '說明'])
        for issue in issues:
            audit.append(issue)
        for col, width in [('A', 23), ('B', 25), ('C', 52)]:
            audit.column_dimensions[col].width = width
        for cell in audit[1]:
            cell.fill = PatternFill('solid', fgColor='234B70')
            cell.font = Font(name='Microsoft JhengHei', bold=True, color='FFFFFF')

    wb.save(output)
    return output


def execute(order_paths, stock_path, location_path, output_path, manual_codes=()):
    orders = [load_excel(p) for p in order_paths]
    stock = load_excel(stock_path)
    locations = load_excel(location_path)
    rows, info = make_records(orders, stock, locations, manual_codes)
    if not rows:
        raise ValueError('無符合庫存的商品，請查看輸入碼與來源檔')
    save_report(rows, info, output_path)
    return info


def build_report(order_files, stock_file, location_file, manual_codes=()):
    orders = [load_excel(file) for file in order_files]
    stock = load_excel(stock_file)
    locations = load_excel(location_file)
    rows, info = make_records(orders, stock, locations, manual_codes)
    if not rows:
        raise ValueError('無符合庫存的商品，請確認輸入的商品碼／條碼與來源檔')
    output = io.BytesIO()
    save_report(rows, info, output)
    output.seek(0)
    return output.getvalue(), info


def main():
    inject_logistics_theme()
    set_page('異常總盤點（含客訂）', icon='🔎', subtitle='客訂明細與手動輸入的異常商品合併產出 Excel。')
    card_open('🔎 異常總盤點明細產生')
    st.caption('支援 .xlsx 與 .xls；客訂可多檔，上傳後與手動異常商品合併，不重複列出同一筆庫存。')

    order_files = st.file_uploader(
        '① 客訂未出明細（選填，可多選）',
        type=['xlsx', 'xls'], accept_multiple_files=True,
        key='abnormal_orders_40',
    )
    stock_file = st.file_uploader('② 庫存明細（必填）', type=['xlsx', 'xls'], key='abnormal_stock_40')
    location_file = st.file_uploader('③ 儲位明細（必填）', type=['xlsx', 'xls'], key='abnormal_locations_40')
    manual_text = st.text_area(
        '④ 手動輸入異常商品碼／條碼（可多筆）',
        placeholder='每行一碼，例如：\n000123\n4712345678901\n4712345678902\n\n亦可用逗號、空格分隔',
        height=170,
        help='會同時比對庫存的「商品號」、「國際條碼」、「條碼2」。前置 0 不會刪除。',
    )
    manual_codes = parse_manual_codes(manual_text)
    st.caption(f'目前手動輸入 {len(manual_codes)} 個不重複代碼。相同商品若同時在客訂與手動清單中，會標記「客訂＋手動異常」。')

    ready = bool(stock_file and location_file and (order_files or manual_codes))
    if st.button('開始產生異常總盤點', type='primary', use_container_width=True, disabled=not ready):
        try:
            report, info = build_report(order_files, stock_file, location_file, manual_codes)
            st.session_state['custom_order_inventory_report'] = report
            st.session_state['custom_order_inventory_info'] = info
        except Exception as exc:
            st.session_state.pop('custom_order_inventory_report', None)
            st.session_state.pop('custom_order_inventory_info', None)
            st.error(f'處理失敗：{exc}')

    report = st.session_state.get('custom_order_inventory_report')
    info = st.session_state.get('custom_order_inventory_info')
    if report and info:
        st.success('異常總盤點（含客訂）已產出。')
        a, b, c, d = st.columns(4)
        a.metric('客訂商品數', info['客訂商品數'])
        b.metric('手動輸入代碼', info['手動輸入數'])
        c.metric('盤點明細筆數', info['盤點筆數'])
        d.metric('同時符合兩種來源', info['重疊筆數'])
        st.caption(f"未匹配手動代碼：{len(info['無法匹配手動條碼'])}；客訂無庫存商品：{len(info['無庫存商品'])}；缺棚別儲位：{len(info['無棚別儲位'])}。詳細內容可查看匯出檔案的「待確認」分頁。")
        st.download_button(
            '下載異常總盤點 Excel', data=report,
            file_name=f'異常總盤點_含客訂_{datetime.now():%Y%m%d_%H%M}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            use_container_width=True,
        )
    elif not ready:
        st.info('請上傳庫存及儲位明細，並提供客訂明細或輸入至少一個異常商品碼／條碼。')
    card_close()


if __name__ == '__main__':
    main()
