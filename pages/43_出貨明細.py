from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
import streamlit as st
from openpyxl import load_workbook

from common_ui import card_close, card_open, inject_logistics_theme, set_page


st.set_page_config(page_title="出貨明細", page_icon="🚚", layout="wide")
inject_logistics_theme()
set_page("出貨明細", "上傳每日出貨 TXT，自動篩選並依站所產生 Excel。")


SHEET_ORDER = (
    "五股所",
    "北區所",
    "新竹所",
    "台中所",
    "嘉義所",
    "台南所",
    "高雄所",
    "花蓮所",
    "宜蘭所",
)

OUTPUT_COLUMNS = {
    "storename": "店名",
    "boxid": "箱號",
    "SKU": "商品碼",
    "manufacturersku": "國際條碼",
    "descr": "品名",
    "載具號": "載具號",
    "站所別": "站所別",
}

REQUIRED_COLUMNS = ["shippeddate", *OUTPUT_COLUMNS]
COLUMN_WIDTHS = {"A": 43, "B": 19.75, "C": 7.5, "D": 16.125, "E": 62, "F": 12.75, "G": 7.5}


def decode_txt(file_bytes):
    for encoding in ("cp950", "utf-8-sig", "utf-8"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("無法辨識 TXT 編碼，請確認檔案為 CP950 或 UTF-8。")


def clean_text(series):
    return series.fillna("").astype(str)


def read_shipping_txt(file_bytes):
    text = decode_txt(file_bytes)
    source = pd.read_csv(StringIO(text), sep="\t", dtype=str, keep_default_na=False)
    source.columns = [str(column).strip() for column in source.columns]

    missing = [column for column in REQUIRED_COLUMNS if column not in source.columns]
    if missing:
        raise ValueError(f"TXT 缺少必要欄位：{', '.join(missing)}")

    for column in REQUIRED_COLUMNS:
        source[column] = clean_text(source[column])

    shipped_date = source["shippeddate"].str.strip()
    station = source["站所別"].str.strip()
    selected = source.loc[
        shipped_date.ne("") & station.isin(SHEET_ORDER),
        list(OUTPUT_COLUMNS),
    ].copy()

    selected.rename(columns=OUTPUT_COLUMNS, inplace=True)
    for column in ("箱號", "商品碼", "國際條碼", "載具號", "站所別"):
        selected[column] = selected[column].str.strip()
    selected["商品碼"] = pd.to_numeric(selected["商品碼"], errors="coerce").astype("Int64")

    # 既有出貨明細會將純數字國際條碼轉成無前置零的文字。
    selected["國際條碼"] = selected["國際條碼"].map(
        lambda value: str(int(value)) if value.isdigit() else value
    )

    # 與既有檔一致：純數字載具號以數值輸出，其餘維持文字。
    selected["載具號"] = selected["載具號"].map(
        lambda value: int(value) if value.isdigit() else value
    )

    return source, selected


def build_excel(selected):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for station in SHEET_ORDER:
            station_data = selected.loc[selected["站所別"].eq(station)].copy()
            station_data.to_excel(writer, sheet_name=station, index=False)

    output.seek(0)
    workbook = load_workbook(output)
    for worksheet in workbook.worksheets:
        worksheet.column_dimensions["B"].number_format = "@"
        worksheet.column_dimensions["D"].number_format = "@"
        for column, width in COLUMN_WIDTHS.items():
            worksheet.column_dimensions[column].width = width
        for cell in worksheet["B"]:
            cell.number_format = "@"
        for cell in worksheet["D"]:
            cell.number_format = "@"

    final_output = BytesIO()
    workbook.save(final_output)
    return final_output.getvalue()


def output_filename(uploaded_name, selected):
    stem = Path(uploaded_name).stem
    dates = selected["箱號"].astype(str).str.extract(r"^(\d{8})", expand=False).dropna()
    prefix = dates.mode().iloc[0] if not dates.empty else stem
    return f"{prefix}-出貨明細.xlsx"


card_open("🚚 出貨明細轉檔")
st.write("上傳出貨 TXT，系統會保留已出貨資料、排除新屋倉，並依站所拆成九個工作表。")

uploaded_file = st.file_uploader("上傳出貨 TXT", type=["txt"])

if uploaded_file:
    try:
        source_data, shipping_data = read_shipping_txt(uploaded_file.getvalue())

        if shipping_data.empty:
            st.warning("檔案中沒有符合條件的已出貨資料。")
        else:
            summary = (
                shipping_data["站所別"]
                .value_counts()
                .reindex(SHEET_ORDER, fill_value=0)
                .rename_axis("站所別")
                .reset_index(name="筆數")
            )

            metric_1, metric_2, metric_3 = st.columns(3)
            metric_1.metric("原始筆數", f"{len(source_data):,}")
            metric_2.metric("輸出筆數", f"{len(shipping_data):,}")
            metric_3.metric("排除筆數", f"{len(source_data) - len(shipping_data):,}")

            st.dataframe(summary, use_container_width=True, hide_index=True)

            excel_bytes = build_excel(shipping_data)
            st.download_button(
                "下載出貨明細 Excel",
                data=excel_bytes,
                file_name=output_filename(uploaded_file.name, shipping_data),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    except Exception as error:
        st.error(f"轉檔失敗：{error}")

card_close()
