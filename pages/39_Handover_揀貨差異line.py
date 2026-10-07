# -*- coding: utf-8 -*-
"""Handover｜揀貨差異 Line。

同一輪合併揀貨的所有批次差異明細必須一起上傳。
Line 以「商品＋儲位＋效期＋庫存批號」識別；跨批次的應揀量加總，
重複呈現的 RF 揀貨量只計一次（若不同則採最大值並標示待確認）。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import streamlit as st

try:
    from common_ui import card_close, card_open, inject_logistics_theme, set_page
except Exception:
    def inject_logistics_theme():
        return None

    def set_page(title: str, icon: str = "", subtitle: str = ""):
        st.title(f"{icon} {title}".strip())
        if subtitle:
            st.caption(subtitle)

    def card_open(title: str):
        st.markdown(f"### {title}")

    def card_close():
        return None


REQUIRED_COLUMNS = ("批次號", "商品", "儲位", "應揀量", "RF揀貨量")
OPTIONAL_KEY_COLUMNS = ("效期", "庫存批號")
LINE_KEY_COLUMNS = ("商品", "儲位", "效期", "庫存批號")
TEXT_COLUMNS = (
    "批次號", "商品", "品名", "條碼1", "條碼2", "儲位", "效期",
    "庫存批號", "棚別", "揀貨時間",
)


def _clean_text(series: pd.Series) -> pd.Series:
    return (
        series.fillna("")
        .astype(str)
        .str.strip()
        .replace({"nan": "", "None": "", "NaN": "", "<NA>": ""})
    )


def _read_delimited(data: bytes) -> tuple[pd.DataFrame, str]:
    last_error = None
    for encoding in ("cp950", "big5", "utf-8-sig", "utf-8"):
        try:
            text = data.decode(encoding)
            first_line = text.splitlines()[0] if text.splitlines() else ""
            separator = "\t" if "\t" in first_line else ","
            frame = pd.read_csv(io.StringIO(text), sep=separator)
            if len(frame.columns) > 1:
                return frame, f"文字檔（{encoding}）"
        except Exception as exc:
            last_error = exc
    raise ValueError(f"無法判讀文字格式：{last_error}")


def read_picking_file(uploaded_file) -> tuple[pd.DataFrame, str]:
    """讀取真正 Excel，或副檔名為 .xls 的 Big5 tab 分隔明細。"""
    data = uploaded_file.getvalue()
    suffix = Path(uploaded_file.name).suffix.lower()

    # 現場匯出的 *.xls 常是 Big5 tab 分隔文字，先檢查檔頭是否為文字。
    if suffix in {".xls", ".txt", ".csv"} and not data.startswith(b"\xd0\xcf\x11\xe0"):
        return _read_delimited(data)

    engines = {
        ".xlsx": "openpyxl",
        ".xlsm": "openpyxl",
        ".xltx": "openpyxl",
        ".xltm": "openpyxl",
        ".xls": "xlrd",
        ".xlsb": "pyxlsb",
    }
    engine = engines.get(suffix)
    if engine is None:
        return _read_delimited(data)

    try:
        book = pd.ExcelFile(io.BytesIO(data), engine=engine)
        sheet = book.sheet_names[0]
        return pd.read_excel(io.BytesIO(data), engine=engine, sheet_name=sheet), f"Excel（{sheet}）"
    except Exception as excel_error:
        try:
            return _read_delimited(data)
        except Exception:
            raise ValueError(f"Excel 讀取失敗：{excel_error}") from excel_error


def prepare_rows(frame: pd.DataFrame, source_name: str) -> pd.DataFrame:
    data = frame.copy()
    data.columns = [str(column).strip() for column in data.columns]
    data = data.dropna(axis=1, how="all")

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{', '.join(missing)}")

    for column in OPTIONAL_KEY_COLUMNS:
        if column not in data.columns:
            data[column] = ""

    for column in TEXT_COLUMNS:
        if column in data.columns:
            data[column] = _clean_text(data[column])

    for column in ("應揀量", "RF揀貨量"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    invalid_qty = data["應揀量"].isna() | data["RF揀貨量"].isna()
    if invalid_qty.any():
        bad_rows = ", ".join(str(number) for number in (data.index[invalid_qty] + 2)[:10])
        raise ValueError(f"應揀量或 RF揀貨量不是數字，請檢查資料列：{bad_rows}")

    missing_key = data["商品"].eq("") | data["儲位"].eq("")
    if missing_key.any():
        bad_rows = ", ".join(str(number) for number in (data.index[missing_key] + 2)[:10])
        raise ValueError(f"商品或儲位空白，請檢查資料列：{bad_rows}")

    data.insert(0, "來源檔名", source_name)
    return data


def _join_unique(values: Iterable[object]) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return "、".join(dict.fromkeys(cleaned))


def build_line_detail(rows: pd.DataFrame) -> pd.DataFrame:
    """建立合併揀貨 Line；RF 數量重複時只取一次。"""
    if rows.empty:
        return pd.DataFrame()

    aggregation = {
        "來源檔名": ("來源檔名", _join_unique),
        "批次號": ("批次號", _join_unique),
        "應揀量": ("應揀量", "sum"),
        "RF揀貨量": ("RF揀貨量", "max"),
        "RF最小值": ("RF揀貨量", "min"),
        "RF數值種類": ("RF揀貨量", "nunique"),
        "來源檔數": ("來源檔名", "nunique"),
        "原始筆數": ("來源檔名", "size"),
    }
    for column in ("品名", "條碼1", "條碼2", "棚別"):
        if column in rows.columns:
            aggregation[column] = (column, "first")

    line = (
        rows.groupby(list(LINE_KEY_COLUMNS), dropna=False)
        .agg(**aggregation)
        .reset_index()
    )
    line["差異量"] = line["應揀量"] - line["RF揀貨量"]
    line["完成狀態"] = np.where(line["差異量"] > 1e-9, "未完成", "完成")
    line["RF判讀"] = np.where(
        line["RF數值種類"] > 1,
        "同 Line 的 RF 數量不同，採最大值，請確認",
        "正常",
    )

    preferred = [
        "完成狀態", "批次號", "商品", "品名", "儲位", "效期", "庫存批號",
        "應揀量", "RF揀貨量", "差異量", "RF判讀", "來源檔數", "原始筆數",
        "來源檔名", "棚別", "條碼1", "條碼2", "RF最小值", "RF數值種類",
    ]
    columns = [column for column in preferred if column in line.columns]
    return line[columns].sort_values(
        ["完成狀態", "差異量", "商品", "儲位"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def calculate_metrics(line: pd.DataFrame) -> dict:
    total = int(len(line))
    unfinished = int(line["差異量"].gt(1e-9).sum()) if total else 0
    over = int(line["差異量"].lt(-1e-9).sum()) if total else 0
    review = int(line["RF數值種類"].gt(1).sum()) if total else 0
    completed = total - unfinished
    shortage = float(line.loc[line["差異量"].gt(0), "差異量"].sum()) if total else 0.0
    return {
        "總Line": total,
        "完成Line": completed,
        "未完成Line": unfinished,
        "Line完成率": completed / total if total else 0.0,
        "應揀量": float(line["應揀量"].sum()) if total else 0.0,
        "RF揀貨量": float(line["RF揀貨量"].sum()) if total else 0.0,
        "缺揀量": shortage,
        "超揀Line": over,
        "待確認Line": review,
    }


def build_download(summary: pd.DataFrame, line: pd.DataFrame, rows: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary.to_excel(writer, index=False, sheet_name="彙總")
        line.to_excel(writer, index=False, sheet_name="Line明細_合併")
        line.loc[line["完成狀態"].eq("未完成")].to_excel(
            writer, index=False, sheet_name="未完成Line"
        )
        rows.to_excel(writer, index=False, sheet_name="原始明細_合併")

        for sheet in writer.book.worksheets:
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column_cells in sheet.columns:
                values = [len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells[:300]]
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(values, default=8) + 2, 36)
    output.seek(0)
    return output.getvalue()


def main():
    st.set_page_config(page_title="Handover｜揀貨差異 Line", page_icon="📦", layout="wide")
    inject_logistics_theme()
    set_page(
        "Handover｜揀貨差異 Line",
        icon="📦",
        subtitle="合併多個大批次的揀貨差異明細，計算完成與未完成 Line。",
    )

    card_open("上傳揀貨差異明細")
    uploaded_files = st.file_uploader(
        "請將同一輪合併揀貨的所有批次明細一起上傳",
        type=["xls", "xlsx", "xlsm", "xlsb", "csv", "txt"],
        accept_multiple_files=True,
    )
    st.caption(
        "必要欄位：批次號、商品、儲位、應揀量、RF揀貨量。"
        "建議保留效期與庫存批號，以免不同庫存批次被合併。"
    )
    card_close()

    if not uploaded_files:
        st.info("請上傳揀貨差異明細。只需此類明細，不需訂單／出貨明細。")
        return

    prepared = []
    file_summary = []
    errors = []
    for uploaded in uploaded_files:
        try:
            raw, method = read_picking_file(uploaded)
            rows = prepare_rows(raw, uploaded.name)
            prepared.append(rows)
            file_summary.append({
                "檔名": uploaded.name,
                "批次號": _join_unique(rows["批次號"]),
                "讀取方式": method,
                "原始筆數": len(rows),
            })
        except Exception as exc:
            errors.append((uploaded.name, str(exc)))

    if errors:
        with st.expander("部分檔案無法計算", expanded=True):
            for name, message in errors:
                st.error(f"{name}：{message}")
    if not prepared:
        st.error("沒有任何檔案可計算。")
        return

    all_rows = pd.concat(prepared, ignore_index=True)
    line = build_line_detail(all_rows)
    metrics = calculate_metrics(line)

    st.markdown("### 合併結果")
    columns = st.columns(4)
    columns[0].metric("總 Line", f'{metrics["總Line"]:,}')
    columns[1].metric("完成 Line", f'{metrics["完成Line"]:,}')
    columns[2].metric("未完成 Line", f'{metrics["未完成Line"]:,}')
    columns[3].metric("Line 完成率", f'{metrics["Line完成率"]:.2%}')

    quantities = st.columns(4)
    quantities[0].metric("應揀量", f'{metrics["應揀量"]:,.0f}')
    quantities[1].metric("RF 揀貨量", f'{metrics["RF揀貨量"]:,.0f}')
    quantities[2].metric("缺揀量", f'{metrics["缺揀量"]:,.0f}')
    quantities[3].metric("超揀 Line", f'{metrics["超揀Line"]:,}')

    if metrics["待確認Line"]:
        st.warning(
            f'有 {metrics["待確認Line"]:,} Line 的 RF 揀貨量在不同檔案中不一致；'
            "目前採最大值計算，請查看 RF判讀欄。"
        )

    card_open("未完成 Line")
    unfinished = line.loc[line["完成狀態"].eq("未完成")]
    st.dataframe(unfinished, use_container_width=True, hide_index=True, height=420)
    card_close()

    with st.expander("全部 Line 明細"):
        st.dataframe(line, use_container_width=True, hide_index=True, height=480)
    with st.expander("各檔讀取結果"):
        st.dataframe(pd.DataFrame(file_summary), use_container_width=True, hide_index=True)

    summary = pd.DataFrame([{
        **metrics,
        "上傳檔數": len(prepared),
        "原始明細筆數": len(all_rows),
        "計算規則": "商品＋儲位＋效期＋庫存批號；應揀量加總；RF揀貨量取最大值",
    }])
    download = build_download(summary, line, all_rows)
    st.download_button(
        "下載計算結果 Excel",
        data=download,
        file_name="揀貨差異_Line計算結果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )


if __name__ == "__main__":
    main()
