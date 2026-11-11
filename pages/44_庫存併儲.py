"""大豐作業平台｜企劃課｜44_庫存併儲.py。"""

from io import BytesIO
import pandas as pd
import streamlit as st


"""倉庫少量併儲分析核心。輸入 pandas DataFrame，回傳各報表 DataFrame。

規則：同貨主、倉別、商品號、效期；只搬少量來源；同棚別優先；GM 不作目的。
此工具產出的結果是建議，目的儲位容量仍需人工確認。
"""
from collections import defaultdict
import math
import pandas as pd

REQUIRED_INVENTORY = ['貨主', '倉別', '儲位', '商品號', '全名', '數量', 'Canuseqty', '商品效期']
REQUIRED_STORAGE = ['儲位', '棚別']
OUTPUT_COLUMNS = [
    '併儲組號','貨主','倉別','商品號','商品全名','商品效期',
    '來源儲位','來源棚別','來源庫存數量','來源可用數量',
    '目的儲位','目的棚別','目的庫存數量','目的可用數量',
    '建議移動量','棚別匹配','來源批號','目的批號','併儲模式',
    '判定說明','建議狀態','注意事項','執行狀態','實際移動量','作業人員',
]
SUMMARY_COLUMNS = ['併儲組號','貨主','倉別','商品號','商品全名','商品效期',
                   '原始儲位數','大儲位數','小量來源數','同棚別移儲筆數',
                   '跨棚別移儲筆數','棚別未確認筆數','建議移動總量','少量門檻']
EXCLUDED_COLUMNS = ['併儲組號','貨主','倉別','商品號','商品效期','商品全名',
                    '原始儲位數','小量來源數','原因']


def clean_code(v, pad=0):
    if pd.isna(v):
        return ''
    v = str(v).strip()
    if v.endswith('.0'):
        v = v[:-2]
    return v.zfill(pad) if v else ''


def clean_location(v):
    return clean_code(v).upper()


def is_special(location):
    s = clean_location(location)
    return not s or any(x in s for x in ('QC', 'PD99', 'GRP', 'CGS', 'JCPL', 'GX010'))


def valid_shelf(v):
    return bool(v) and str(v).strip().upper() not in ('NOUSE', 'FACILITY', 'NAN', 'NONE')


def clean_date(series):
    result = pd.to_datetime(series, errors='coerce')
    # WMS Excel integer serial dates
    numeric = pd.to_numeric(series, errors='coerce')
    numeric_mask = result.isna() & numeric.between(1, 90000)
    if numeric_mask.any():
        result.loc[numeric_mask] = pd.to_datetime(numeric.loc[numeric_mask], unit='D', origin='1899-12-30')
    return result.dt.strftime('%Y-%m-%d').fillna('未設定')


def prepare_inventory(raw):
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    absent = [c for c in REQUIRED_INVENTORY if c not in df.columns]
    if absent:
        raise ValueError('庫存明細缺少欄位：' + '、'.join(absent))
    if '批號' not in df.columns:
        df['批號'] = ''
    for col in ('貨主', '倉別', '商品號', '儲位', '批號'):
        df[col] = df[col].map(clean_location if col == '儲位' else clean_code)
    df['商品號'] = df['商品號'].map(lambda s: s.zfill(6) if s else '')
    df['倉別'] = df['倉別'].map(lambda s: s.zfill(5) if s.isdigit() else s)
    df['商品效期'] = clean_date(df['商品效期'])
    df['全名'] = df['全名'].fillna('').astype(str)
    for col in ('數量','Canuseqty'):
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).clip(lower=0)
    return df[df['商品號'].ne('') & df['儲位'].ne('')].copy()


def prepare_storage(raw):
    df = raw.copy()
    df.columns = [str(c).strip() for c in df.columns]
    absent = [c for c in REQUIRED_STORAGE if c not in df.columns]
    if absent:
        raise ValueError('儲位明細缺少欄位：' + '、'.join(absent))
    df['儲位'] = df['儲位'].map(clean_location)
    df['棚別'] = df['棚別'].fillna('').astype(str).str.strip()
    df = df[df['儲位'].ne('')].copy()
    # 若同一儲位的棚別映射不一致，保留空白，避免錯誤判定同棚別
    mapping = {}
    conflicts = []
    for loc, g in df.groupby('儲位', sort=False):
        valid = set(v for v in g['棚別'] if valid_shelf(v))
        if len(valid) == 1:
            mapping[loc] = next(iter(valid))
        elif len(valid) > 1:
            mapping[loc] = ''
            conflicts.append(loc)
        else:
            mapping[loc] = ''
    return mapping, conflicts


def build_report(inventory, storage, ratio=0.20, cross_shelf=True):
    if not 0 < ratio <= 1:
        raise ValueError('少量比例須大於 0 且不超過 1。')
    inv = prepare_inventory(inventory)
    shelf_map, conflicts = prepare_storage(storage)
    key_cols = ['貨主','倉別','商品號','商品效期','儲位']
    grouped = inv.groupby(key_cols, dropna=False, sort=False)
    agg = grouped.agg(數量=('數量','sum'), Canuseqty=('Canuseqty','sum'), 全名=('全名','first'),
                      批號=('批號', lambda x: ' / '.join(sorted(set(t for t in x if t))))).reset_index()
    agg['棚別'] = agg['儲位'].map(lambda loc: shelf_map.get(loc, ''))
    move_rows, summary_rows, excluded_rows = [], [], []
    group_no = 0
    for (owner, warehouse, sku, exp), g in agg.groupby(['貨主','倉別','商品號','商品效期'], sort=True):
        bins = g.to_dict('records')
        if len(bins) < 2:
            continue
        bins.sort(key=lambda b: (-b['數量'], b['儲位']))
        reference = bins[1]['數量'] if len(bins) >= 3 else bins[0]['數量']
        threshold = reference * ratio
        low = sorted((b for b in bins if b['數量'] > 0 and b['數量'] <= threshold),
                     key=lambda b: (b['數量'], b['儲位']))
        if not low:
            continue
        large = [b for b in bins if b['數量'] > threshold]
        targets = [b for b in large if not b['儲位'].startswith('GM') and not is_special(b['儲位'])]
        group_no += 1
        if not targets:
            excluded_rows.append([group_no, owner,warehouse,sku,exp,bins[0]['全名'],
                                  len(bins),len(low),'無非 GM、非特殊儲位的大量目的儲位'])
            continue
        same_count = cross_count = unknown_count = 0
        moved_total = 0
        group_moved = 0
        for source in low:
            choices = [t for t in targets if t['儲位'] != source['儲位']]
            same_choices = [t for t in choices if valid_shelf(source['棚別']) and t['棚別'] == source['棚別']]
            if same_choices:
                target = min(same_choices, key=lambda b: (b['數量'], b['儲位']))
                match = '同棚別優先'
                same_count += 1
            elif cross_shelf and choices:
                target = min(choices, key=lambda b: (b['數量'], b['儲位']))
                match = '跨棚別' if valid_shelf(source['棚別']) and valid_shelf(target['棚別']) else '棚別未確認'
                if match == '跨棚別':cross_count += 1
                else:unknown_count += 1
            else:
                excluded_rows.append([group_no,owner,warehouse,sku,exp,bins[0]['全名'],
                                      len(bins),1,'同棚別無合格目的儲位（跨棚別功能已關閉）'])
                continue
            qty = min(source['數量'], source['Canuseqty'])
            notes = []
            if is_special(source['儲位']):notes.append('來源為特殊儲位')
            if source['Canuseqty'] < source['數量']:notes.append('來源部分庫存不可用，無法完全清空')
            if qty <= 0:notes.append('可用數量為 0，暫不可移')
            if set(source['批號'].split(' / ')) != set(target['批號'].split(' / ')):
                notes.append('批號不同或多批號，需核對')
            if not valid_shelf(source['棚別']) or not valid_shelf(target['棚別']):
                notes.append('棚別資訊缺失或非正式棚別，請確認')
            if match == '跨棚別':notes.append('同棚別無合格目的儲位，改跨棚別')
            status = '需人工確認' if notes else '可安排'
            record = [group_no,owner,warehouse,sku,source['全名'],exp,
                source['儲位'],source['棚別'] or '未對應',source['數量'],source['Canuseqty'],
                target['儲位'],target['棚別'] or '未對應',target['數量'],target['Canuseqty'],qty,
                match,source['批號'],target['批號'],'僅少量移儲',
                f'小量庫存≤參考儲位數量{ratio:.0%}（{threshold:g}）；同棚別優先，GM 禁入',
                status,'；'.join(notes),'待執行' if qty>0 else '暫不可移',None,None]
            move_rows.append(record)
            moved_total += qty
            group_moved += 1
        if group_moved:
            summary_rows.append([group_no,owner,warehouse,sku,bins[0]['全名'],exp,
                 len(bins),len(large),group_moved,same_count,cross_count,unknown_count,moved_total,threshold])
    execution = pd.DataFrame(move_rows, columns=OUTPUT_COLUMNS)
    manual = execution[execution['建議狀態'] == '需人工確認'].copy()
    summary = pd.DataFrame(summary_rows, columns=SUMMARY_COLUMNS)
    excluded = pd.DataFrame(excluded_rows, columns=EXCLUDED_COLUMNS)
    assert not execution['目的儲位'].astype(str).str.startswith('GM').any()
    assert not (execution['來源儲位'] == execution['目的儲位']).any()
    counts = {
        '庫存明細筆數':len(inv),'儲位棚別對照數':len(shelf_map),
        '棚別對照衝突儲位數':len(conflicts),'符合建議組數':len(summary),
        '建議移儲筆數':len(execution),
        '同棚別優先移儲筆數':int((execution['棚別匹配']=='同棚別優先').sum()),
        '跨棚別移儲筆數':int((execution['棚別匹配']=='跨棚別').sum()),
        '棚別未確認筆數':int((execution['棚別匹配']=='棚別未確認').sum()),
        '可直接安排':int((execution['建議狀態']=='可安排').sum()),
        '需人工確認':len(manual),
        '無合格目的儲位筆數':len(excluded),
        '建議移動總量':execution['建議移動量'].sum() if len(execution) else 0,
    }
    rules = [
      ('少量判定', f'3個以上儲位：≤第二大儲位數量的{ratio:.0%}；2個儲位：≤最大儲位的{ratio:.0%}'),
      ('來源原則','只移出少量儲位；大型儲位不列為來源'),
      ('目的優先','來源同棚別的合格大儲位優先；有多個時選數量較小者'),
      ('GM限制','GM開頭儲位可為來源，不可為目的'),
      ('跨棚別', '允許；需人工確認' if cross_shelf else '不允許'),
      ('保留審核','批號差異、不可用庫存、特殊來源或棚別不明需人工確認'),
      ('重要提醒','未取得目的儲位實際剩餘容量，移動前需現場核對'),
    ]
    overview = pd.DataFrame(list(counts.items()) + rules, columns=['統計項目 / 規則','結果 / 說明'])
    return {'併儲總覽':overview,'併儲執行明細':execution,'人工確認清單':manual,
            '商品效期彙總':summary,'無合格目的儲位':excluded}, counts


from common_ui import inject_logistics_theme, set_page, card_open, card_close


def read_excel(upload):
    engine = 'xlrd' if upload.name.lower().endswith('.xls') else 'openpyxl'
    upload.seek(0)
    frame = pd.read_excel(upload, engine=engine, dtype=str, keep_default_na=False)
    frame.columns = [str(c).strip() for c in frame.columns]
    return frame


def create_excel(sheets):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
            worksheet = writer.sheets[name]
            workbook = writer.book
            headers = workbook.add_format({'bold':True,'bg_color':'#1D3557','font_color':'white','border':0,'text_wrap':True,'valign':'vcenter'})
            worksheet.set_row(0, 32)
            worksheet.freeze_panes(1, 0)
            worksheet.set_default_row(21)
            for c, col in enumerate(df.columns):
                width = 38 if col in ('商品全名','判定說明','注意事項','結果 / 說明') else 18
                worksheet.set_column(c, c, width)
                worksheet.write(0, c, col, headers)
            if len(df):
                worksheet.autofilter(0,0,len(df),len(df.columns)-1)
                if name == '併儲執行明細':
                    status_col = df.columns.get_loc('建議狀態')
                    good = workbook.add_format({'bg_color':'#EAF7E8'})
                    worksheet.conditional_format(1,status_col,len(df),status_col,
                           {'type':'text','criteria':'containing','value':'可安排','format':good})
    return buffer.getvalue()

def main():
    inject_logistics_theme()
    set_page('庫存併儲', icon='📦', subtitle='少量庫存併儲｜同棚別優先｜GM 儲位不可作為目的儲位')
    card_open('📦 庫存併儲建議')
    st.info('上傳庫存明細及儲位明細，支援 .xls 與 .xlsx；結果為建議，不會寫回 WMS。')
    left, right = st.columns(2)
    with left:
        inventory_file = st.file_uploader('① 庫存明細', type=['xls','xlsx'], key='merge44_inventory')
    with right:
        location_file = st.file_uploader('② 儲位明細（儲位、棚別）', type=['xls','xlsx'], key='merge44_storage')
    with st.expander('⚙️ 進階設定', expanded=False):
        ratio_pct = st.number_input('少量判定比例（%）', min_value=1, max_value=100, value=20, step=1,
                                    help='三個以上儲位以第二大量為基準，兩個儲位以最大量為基準')
        allow_cross = st.checkbox('找不到同棚別目的時，允許跨棚別建議（需人工確認）', value=True)

    fingerprint = (inventory_file.name, inventory_file.size, location_file.name, location_file.size,
                   ratio_pct, allow_cross) if inventory_file and location_file else None
    if st.session_state.get('merge44_fingerprint') != fingerprint:
        st.session_state.pop('merge44_last_report', None)
        st.session_state['merge44_fingerprint'] = fingerprint

    if st.button('🚀 產生併儲明細', type='primary', use_container_width=True,
                 disabled=not(inventory_file and location_file)):
        try:
            with st.spinner('分析儲位、效期、數量與棚別中…'):
                inv = read_excel(inventory_file)
                loc = read_excel(location_file)
                sheets, counts = build_report(inv, loc, ratio=ratio_pct/100, cross_shelf=allow_cross)
                blob = create_excel(sheets)
                st.session_state['merge44_last_report'] = (sheets, counts, blob)
        except Exception as exc:
            st.session_state.pop('merge44_last_report', None)
            st.error(f'產生失敗：{exc}')

    if 'merge44_last_report' in st.session_state:
        sheets, counts, blob = st.session_state['merge44_last_report']
        stats = st.columns(4)
        for metric, key in zip(stats, ['建議移儲筆數', '同棚別優先移儲筆數', '可直接安排', '需人工確認']):
            metric.metric(key, f'{counts[key]:,}')
        st.download_button('⬇️ 下載完整併儲 Excel', blob, file_name='庫存併儲明細_同棚別優先.xlsx',
                           mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                           type='primary', use_container_width=True)
        tab_names = ['併儲執行明細', '人工確認清單', '商品效期彙總', '無合格目的儲位', '併儲總覽']
        for tab, name in zip(st.tabs(tab_names), tab_names):
            with tab:
                st.dataframe(sheets[name], use_container_width=True, hide_index=True)
        st.caption('建議未包含目的儲位實際剩餘容量；現場操作前請確認容量、批號與效期。')
    card_close()


if __name__ == '__main__':
    main()
