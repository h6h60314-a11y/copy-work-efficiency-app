# pages/3_總揀達標.py
# ------------------------------------------------------------
#  總揀達標獎金計算報表（合併版：上午 + 下午同頁呈現）
#  - 第一階段：上午（<=12:30，休息 10:00-10:15）
#  - 第二階段：下午（13:30-18:00，休息 15:30-15:45）
#  - 版面：同一個 Sheet1 上下分段
#  - 匯出：openpyxl（避免 Streamlit Cloud 缺 xlsxwriter）
#  - 畫面 KPI 表格：整列紅/綠底（依區域+效率門檻）
# ------------------------------------------------------------

from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ---------- 可視參數 -------------------------------------------------
# 上午
MORNING_END = datetime.strptime("12:30:00", "%H:%M:%S").time()
M_REST_START = datetime.strptime("10:00:00", "%H:%M:%S").time()
M_REST_END = datetime.strptime("10:15:00", "%H:%M:%S").time()

# 下午
AFTERNOON_START = datetime.strptime("13:30:00", "%H:%M:%S").time()
AFTERNOON_END = datetime.strptime("18:00:00", "%H:%M:%S").time()
A_REST_START = datetime.strptime("15:30:00", "%H:%M:%S").time()
A_REST_END = datetime.strptime("15:45:00", "%H:%M:%S").time()

IDLE_THRESHOLD = timedelta(minutes=10)  # 空窗門檻
default_start_time_str = "08:05:00"

# ---------- 揀貨人預設資料 ------------------------------------------
# 若「區域」留空 → 以「低空」處理（原樣保留）
preset_picker_info: Dict[str, Dict[str, str]] = {
    "20230412002": {"姓名": "吳秉丞", "起始時間": "8:05:00", "區域": "低空"},
    "20200812002": {"姓名": "彭慈暉", "起始時間": "7:05:00", "區域": "低空"},
    "20210104001": {"姓名": "楊承珉", "起始時間": "7:05:00", "區域": "低空"},
    "20201109001": {"姓名": "梁冠如", "起始時間": "8:05:00", "區域": "低空"},
    "20201109003": {"姓名": "吳振凱", "起始時間": "8:05:00", "區域": "低空"},
    "20231226003": {"姓名": "顏秀菁", "起始時間": "8:05:00", "區域": "低空"},
    "20200922002": {"姓名": "葉欲弘", "起始時間": "8:05:00", "區域": "低空"},
    "20200924001": {"姓名": "黃雅君", "起始時間": "8:05:00", "區域": "低空"},
}


# =========================================================
# 小工具：中文姓名 / mapping（保留既有邏輯）
# =========================================================
def _get_name(picker_id: str, mapping: Dict[str, Dict[str, str]]) -> str:
    if picker_id in mapping and (mapping[picker_id].get("姓名") or "").strip():
        return str(mapping[picker_id].get("姓名")).strip()
    if picker_id in preset_picker_info:
        return str(preset_picker_info[picker_id].get("姓名", "")).strip()
    return ""


def _get_start_time(picker_id: str, mapping: Dict[str, Dict[str, str]]) -> str:
    if picker_id in mapping and (mapping[picker_id].get("起始時間") or "").strip():
        return str(mapping[picker_id].get("起始時間")).strip()
    if picker_id in preset_picker_info:
        return str(preset_picker_info[picker_id].get("起始時間", default_start_time_str)).strip()
    return default_start_time_str


def _get_region(picker_id: str, mapping: Dict[str, Dict[str, str]]) -> str:
    if picker_id in mapping and (mapping[picker_id].get("區域") or "").strip():
        return str(mapping[picker_id].get("區域")).strip()
    if picker_id in preset_picker_info:
        return str(preset_picker_info[picker_id].get("區域", "低空")).strip() or "低空"
    return "低空"


def _storage_area_str(records: pd.DataFrame) -> str:
    # 盡量保持原樣：若有儲位欄位則用儲位前綴彙總
    if records is None or records.empty:
        return ""
    if "儲位" not in records.columns:
        return ""
    vals = records["儲位"].dropna().astype(str).str.strip()
    vals = vals[vals != ""]
    if vals.empty:
        return ""
    # 取前2-3碼做簡易聚合（保留你的既有習慣）
    head = vals.str[:2].value_counts()
    top = head.head(8).index.tolist()
    return ",".join(top)


def parse_tw_datetime(series: pd.Series) -> pd.Series:
    # 原樣保留：容錯解析
    return pd.to_datetime(series, errors="coerce")


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "揀貨完成時間" in df.columns:
        df["揀貨完成時間"] = parse_tw_datetime(df["揀貨完成時間"])
    return df


# =========================================================
# 前處理：讀檔、去成箱、合併列（保留原邏輯）
# =========================================================
def _load_uploaded_files(files: List[st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
    frames: List[pd.DataFrame] = []
    for f in files:
        name = (f.name or "").lower()
        b = f.getvalue()
        try:
            if name.endswith(".csv"):
                frames.append(pd.read_csv(io.BytesIO(b)))
            else:
                frames.append(pd.read_excel(io.BytesIO(b)))
        except Exception:
            # 讀不到就跳過
            continue
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def remove_boxed_rows(df: pd.DataFrame) -> pd.DataFrame:
    # 保留原本規則：成箱箱號為空才納入
    if df is None or df.empty:
        return df
    if "成箱箱號" in df.columns:
        tmp = df.copy()
        tmp["成箱箱號"] = tmp["成箱箱號"].astype(str).fillna("").str.strip()
        tmp = tmp[tmp["成箱箱號"] == ""]
        return tmp
    return df


def combine_rows(df: pd.DataFrame) -> pd.DataFrame:
    # 與你合併版一致：同儲位/商品/揀貨人/完成時間 → 數量加總
    if df is None or df.empty:
        return df
    group_cols = ["儲位", "商品", "揀貨人", "揀貨完成時間"]
    for c in group_cols:
        if c not in df.columns:
            # 若缺欄位，直接回傳原 df（避免破壞你既有資料）
            return df

    if "數量" not in df.columns:
        df = df.copy()
        df["數量"] = 1

    combined_df = df.groupby(group_cols, as_index=False).agg({"數量": "sum"})
    return combined_df


# =========================================================
# 上午/下午切段（保留原邏輯）
# =========================================================
def filter_morning_period(df: pd.DataFrame) -> pd.DataFrame:
    dtv = parse_tw_datetime(df["揀貨完成時間"])
    df = df.assign(揀貨完成時間=dtv).dropna(subset=["揀貨完成時間"])
    df = df[df["揀貨完成時間"].dt.time <= MORNING_END]
    return df


def filter_afternoon_period(df: pd.DataFrame) -> pd.DataFrame:
    dtv = parse_tw_datetime(df["揀貨完成時間"])
    df = df.assign(揀貨完成時間=dtv).dropna(subset=["揀貨完成時間"])
    df = df[(df["揀貨完成時間"].dt.time >= AFTERNOON_START) & (df["揀貨完成時間"].dt.time <= AFTERNOON_END)]
    return df


# =========================================================
# 空窗拆段（保留原邏輯）
# =========================================================
def split_idle_segment(start: datetime, end: datetime, rest_start: datetime, rest_end: datetime) -> List[Tuple[datetime, datetime]]:
    segs: List[Tuple[datetime, datetime]] = []
    if end <= start:
        return segs

    # 切掉休息重疊
    if end <= rest_start or start >= rest_end:
        segs.append((start, end))
        return segs

    if start < rest_start:
        segs.append((start, rest_start))
    if end > rest_end:
        segs.append((rest_end, end))
    return [(s, e) for s, e in segs if e > s]


def get_effective_idle_segments(prev_t: datetime, cur_t: datetime, rest_start: datetime, rest_end: datetime) -> List[Tuple[datetime, datetime]]:
    if cur_t <= prev_t:
        return []
    gap = cur_t - prev_t
    if gap < IDLE_THRESHOLD:
        return []
    return split_idle_segment(prev_t, cur_t, rest_start, rest_end)


# =========================================================
# 計算：上午 / 下午（保留你合併版邏輯）
# =========================================================
def calculate_statistics_morning(morning_df: pd.DataFrame, full_df: pd.DataFrame, mapping: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    columns_order = ["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"]
    if morning_df is None or morning_df.empty:
        return pd.DataFrame(columns=columns_order)

    stats: List[Dict[str, object]] = []
    morning_df = morning_df.copy()
    morning_df["揀貨完成時間"] = parse_tw_datetime(morning_df["揀貨完成時間"])
    morning_df = morning_df.dropna(subset=["揀貨完成時間"])

    full_df = full_df.copy()
    full_df["揀貨完成時間"] = parse_tw_datetime(full_df["揀貨完成時間"])
    full_df = full_df.dropna(subset=["揀貨完成時間"])

    for picker in sorted(morning_df["揀貨人"].dropna().astype(str).unique()):
        picker_m = morning_df[morning_df["揀貨人"].astype(str) == picker].sort_values("揀貨完成時間")
        if picker_m.empty:
            continue

        first_record = picker_m["揀貨完成時間"].iloc[0].to_pydatetime()
        last_record = picker_m["揀貨完成時間"].iloc[-1].to_pydatetime()

        # 起始時間（可被設定覆蓋）
        start_time_str = _get_start_time(picker, mapping) or default_start_time_str
        try:
            st_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
        except Exception:
            st_time = datetime.strptime(default_start_time_str, "%H:%M:%S").time()

        start_dt = datetime.combine(first_record.date(), st_time)
        end_dt = datetime.combine(first_record.date(), MORNING_END)

        effective_start = min(first_record, start_dt)

        # 若該揀貨人在 full_df 有下午紀錄，上午結束用 12:30；否則用 min(最後一筆, 12:30)
        picker_full = full_df[full_df["揀貨人"].astype(str) == picker]
        has_afternoon = any(rec.time() >= AFTERNOON_START for rec in picker_full["揀貨完成時間"])
        effective_end = end_dt if has_afternoon else min(last_record, end_dt)

        rest_start_dt = datetime.combine(first_record.date(), M_REST_START)
        rest_end_dt = datetime.combine(first_record.date(), M_REST_END)

        overlap_start = max(effective_start, rest_start_dt)
        overlap_end = min(effective_end, rest_end_dt)
        rest_duration = (overlap_end - overlap_start) if overlap_end > overlap_start else timedelta(0)

        work_duration = (effective_end - effective_start) - rest_duration
        total_minutes = round(work_duration.total_seconds() / 60, 2)

        times = picker_m["揀貨完成時間"].dt.to_pydatetime().tolist()
        idle_segments: List[Tuple[datetime, datetime]] = []

        if times and times[0] > effective_start:
            idle_segments.extend(split_idle_segment(effective_start, times[0], rest_start_dt, rest_end_dt))

        for i in range(1, len(times)):
            idle_segments.extend(get_effective_idle_segments(times[i - 1], times[i], rest_start_dt, rest_end_dt))

        if last_record < effective_end:
            idle_segments.extend(get_effective_idle_segments(last_record, effective_end, rest_start_dt, rest_end_dt))

        idle_minutes = round(sum((e - s).total_seconds() for s, e in idle_segments) / 60, 2)
        num_records = len(picker_m)
        efficiency = round((num_records / total_minutes * 60) if total_minutes else 0, 2)

        time_period_str = f"{effective_start.strftime('%H:%M:%S')} ~ {effective_end.strftime('%H:%M:%S')}"
        idle_segments_str = "; ".join(f"{s.strftime('%H:%M:%S')} ~ {e.strftime('%H:%M:%S')}" for s, e in idle_segments)

        working_records = picker_m[(picker_m["揀貨完成時間"] >= effective_start) & (picker_m["揀貨完成時間"] <= effective_end)]
        storage_area_str = _storage_area_str(working_records)

        region = _get_region(picker, mapping)

        stats.append(
            {
                "區域": region,
                "揀貨人": picker,
                "姓名": _get_name(picker, mapping),
                "筆數": num_records,
                "工作區間": time_period_str,
                "總分鐘": total_minutes,
                "效率": efficiency,
                "空窗分鐘": idle_minutes,
                "儲位區域": storage_area_str,
                "空窗時間段": idle_segments_str,
            }
        )

    statistics_df = pd.DataFrame(stats)
    if statistics_df.empty:
        return pd.DataFrame(columns=columns_order)

    statistics_df["區域"] = pd.Categorical(statistics_df["區域"], categories=["低空", "高空"], ordered=True)
    statistics_df = statistics_df.sort_values(by=["區域", "揀貨人"])
    return statistics_df[columns_order]


def calculate_statistics_afternoon(afternoon_df: pd.DataFrame, full_df: pd.DataFrame, mapping: Dict[str, Dict[str, str]]) -> pd.DataFrame:
    columns_order = ["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"]
    if afternoon_df is None or afternoon_df.empty:
        return pd.DataFrame(columns=columns_order)

    stats: List[Dict[str, object]] = []
    afternoon_df = afternoon_df.copy()
    afternoon_df["揀貨完成時間"] = parse_tw_datetime(afternoon_df["揀貨完成時間"])
    afternoon_df = afternoon_df.dropna(subset=["揀貨完成時間"])

    full_df = full_df.copy()
    full_df["揀貨完成時間"] = parse_tw_datetime(full_df["揀貨完成時間"])
    full_df = full_df.dropna(subset=["揀貨完成時間"])

    for picker in sorted(afternoon_df["揀貨人"].dropna().astype(str).unique()):
        picker_a = afternoon_df[afternoon_df["揀貨人"].astype(str) == picker].sort_values("揀貨完成時間")
        if picker_a.empty:
            continue

        first_record = picker_a["揀貨完成時間"].iloc[0].to_pydatetime()
        last_record = picker_a["揀貨完成時間"].iloc[-1].to_pydatetime()

        start_dt = datetime.combine(first_record.date(), AFTERNOON_START)
        end_dt = datetime.combine(first_record.date(), AFTERNOON_END)
        effective_start = min(first_record, start_dt)

        picker_full = full_df[full_df["揀貨人"].astype(str) == picker]
        has_after_end = any(rec.time() > AFTERNOON_END for rec in picker_full["揀貨完成時間"])
        effective_end = end_dt if has_after_end else min(last_record, end_dt)

        rest_start_dt = datetime.combine(first_record.date(), A_REST_START)
        rest_end_dt = datetime.combine(first_record.date(), A_REST_END)

        overlap_start = max(effective_start, rest_start_dt)
        overlap_end = min(effective_end, rest_end_dt)
        rest_duration = (overlap_end - overlap_start) if overlap_end > overlap_start else timedelta(0)

        work_duration = (effective_end - effective_start) - rest_duration
        total_minutes = round(work_duration.total_seconds() / 60, 2)

        times = picker_a["揀貨完成時間"].dt.to_pydatetime().tolist()
        idle_segments: List[Tuple[datetime, datetime]] = []

        if times and times[0] > effective_start:
            idle_segments.extend(split_idle_segment(effective_start, times[0], rest_start_dt, rest_end_dt))

        for i in range(1, len(times)):
            idle_segments.extend(get_effective_idle_segments(times[i - 1], times[i], rest_start_dt, rest_end_dt))

        if last_record < effective_end:
            idle_segments.extend(get_effective_idle_segments(last_record, effective_end, rest_start_dt, rest_end_dt))

        idle_minutes = round(sum((e - s).total_seconds() for s, e in idle_segments) / 60, 2)
        num_records = len(picker_a)
        efficiency = round((num_records / total_minutes * 60) if total_minutes else 0, 2)

        time_period_str = f"{effective_start.strftime('%H:%M:%S')} ~ {effective_end.strftime('%H:%M:%S')}"
        idle_segments_str = "; ".join(f"{s.strftime('%H:%M:%S')} ~ {e.strftime('%H:%M:%S')}" for s, e in idle_segments)

        working_records = picker_a[(picker_a["揀貨完成時間"] >= effective_start) & (picker_a["揀貨完成時間"] <= effective_end)]
        storage_area_str = _storage_area_str(working_records)

        region = _get_region(picker, mapping)

        stats.append(
            {
                "區域": region,
                "揀貨人": picker,
                "姓名": _get_name(picker, mapping),
                "筆數": num_records,
                "工作區間": time_period_str,
                "總分鐘": total_minutes,
                "效率": efficiency,
                "空窗分鐘": idle_minutes,
                "儲位區域": storage_area_str,
                "空窗時間段": idle_segments_str,
            }
        )

    statistics_df = pd.DataFrame(stats)
    if statistics_df.empty:
        return pd.DataFrame(columns=columns_order)

    statistics_df["區域"] = pd.Categorical(statistics_df["區域"], categories=["低空", "高空"], ordered=True)
    statistics_df = statistics_df.sort_values(by=["區域", "揀貨人"])
    return statistics_df[columns_order]


# =========================================================
# 匯出（openpyxl）：同一張 Sheet 上下分段 + 達標紅綠底色（保留原邏輯）
# =========================================================
def build_export_xlsx_bytes(
    title: str,
    morning_df: pd.DataFrame,
    afternoon_df: pd.DataFrame,
    low_threshold: float = 48.0,
    high_threshold: float = 20.0,
) -> bytes:
    # 你原本的匯出邏輯：openpyxl + 同一張 sheet 上下段 + 依效率做紅綠
    from openpyxl import Workbook
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    thin = Side(style="thin", color="333333")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    fill_green = PatternFill("solid", fgColor="C6EFCE")
    fill_red = PatternFill("solid", fgColor="FFC7CE")
    font_green = Font(color="006100")
    font_red = Font(color="9C0006")

    def autosize_cols(start_row: int, end_row: int, start_col: int, end_col: int):
        widths = {}
        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                v = ws.cell(r, c).value
                if v is None:
                    continue
                widths[c] = max(widths.get(c, 0), len(str(v)))
        for c, w in widths.items():
            ws.column_dimensions[get_column_letter(c)].width = min(max(10, w + 2), 48)

    def write_block(block_title: str, df: pd.DataFrame, start_row: int) -> int:
        # title row
        ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=max(1, len(df.columns) if df is not None else 1))
        c = ws.cell(start_row, 1, block_title)
        c.font = Font(size=14, bold=True)
        c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[start_row].height = 22

        if df is None or df.empty:
            ws.cell(start_row + 1, 1, "（本段無資料）")
            return start_row + 3

        # header
        header_row = start_row + 1
        for j, col in enumerate(df.columns, start=1):
            cell = ws.cell(header_row, j, col)
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = border

        # body
        for i, row in enumerate(df.itertuples(index=False), start=header_row + 1):
            for j, v in enumerate(row, start=1):
                cell = ws.cell(i, j, v)
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                cell.border = border

            # row color by efficiency
            try:
                region = str(df.iloc[i - (header_row + 1)]["區域"])
                eff = float(df.iloc[i - (header_row + 1)]["效率"])
            except Exception:
                region, eff = "", 0.0

            ok = False
            if region == "高空":
                ok = eff >= float(high_threshold)
            elif region == "低空":
                ok = eff >= float(low_threshold)

            for j in range(1, len(df.columns) + 1):
                if ok:
                    ws.cell(i, j).fill = fill_green
                    ws.cell(i, j).font = font_green
                else:
                    ws.cell(i, j).fill = fill_red
                    ws.cell(i, j).font = font_red

        end_row = header_row + len(df)
        autosize_cols(header_row, end_row, 1, len(df.columns))
        return end_row + 2

    # report title
    # 取最大欄數避免 merge 長度不一致
    max_cols = max(
        1,
        (len(morning_df.columns) if morning_df is not None and not morning_df.empty else 1),
        (len(afternoon_df.columns) if afternoon_df is not None and not afternoon_df.empty else 1),
    )
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max_cols)
    t = ws.cell(1, 1, title)
    t.font = Font(size=18, bold=True)
    t.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    next_row = 3
    next_row = write_block("第一階段（上午）", morning_df, next_row)
    next_row = write_block("第二階段（下午）", afternoon_df, next_row)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# =========================================================
# UI：mapping editor（保留原邏輯：姓名可中文輸入）
# =========================================================
def _mapping_editor():
    if "pick_map" not in st.session_state:
        st.session_state.pick_map = {}

    with st.sidebar:
        st.subheader("👤 揀貨人設定（可中文姓名）")
        st.caption("輸入「揀貨人」代碼後，可設定姓名/起始時間/區域（高空/低空）。")

        picker_id = st.text_input("揀貨人代碼（可貼上）", value="")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("姓名（中文可輸入）", value="")
        with col2:
            region = st.selectbox("區域", options=["低空", "高空"], index=0)

        start_time = st.text_input("起始時間（HH:MM:SS）", value=default_start_time_str)

        if st.button("➕ 新增 / 更新"):
            pid = (picker_id or "").strip()
            if not pid:
                st.warning("請輸入揀貨人代碼")
            else:
                st.session_state.pick_map[pid] = {
                    "姓名": (name or "").strip(),
                    "起始時間": (start_time or "").strip(),
                    "區域": (region or "").strip(),
                }
                st.success("已更新")

        if st.session_state.pick_map:
            st.divider()
            st.caption("目前設定：")
            mdf = pd.DataFrame(
                [{"揀貨人": k, **v} for k, v in st.session_state.pick_map.items()]
            )
            st.dataframe(mdf, use_container_width=True, hide_index=True)


# =========================================================
# ✅ 畫面 KPI 表格：整列紅/綠底（新增，不改計算/匯出邏輯）
# =========================================================
def _style_kpi_rows(df: pd.DataFrame, low_threshold: float, high_threshold: float) -> "pd.io.formats.style.Styler":
    if df is None or df.empty:
        return df.style

    def _row_style(row: pd.Series) -> List[str]:
        try:
            region = str(row.get("區域", ""))
            eff = float(row.get("效率", 0))
        except Exception:
            region, eff = "", 0.0

        ok = False
        if region == "高空":
            ok = eff >= float(high_threshold)
        elif region == "低空":
            ok = eff >= float(low_threshold)

        if ok:
            bg, fg = "#C6EFCE", "#006100"
        else:
            bg, fg = "#FFC7CE", "#9C0006"
        return [f"background-color: {bg}; color: {fg};" for _ in row.index]

    return df.style.apply(_row_style, axis=1)


# =========================================================
# Main
# =========================================================
def main():
    inject_logistics_theme()
    set_page(
        "總揀達標（合併版）",
        icon="🧾",
        subtitle="同一張報表 Sheet 上下分段｜達標紅綠底色｜姓名可中文輸入",
    )

    # sidebar controls
    _mapping_editor()
    with st.sidebar:
        st.divider()
        st.subheader("⚙️ 報表設定")
        report_title = st.text_input("報表標題", value="總揀達標獎金計算報表（合併版）")
        st.caption("達標門檻（沿用你原本條件）：高空 20、低空 48")
        high_threshold = st.number_input("高空達標（效率）", min_value=0.0, max_value=9999.0, value=20.0, step=1.0)
        low_threshold = st.number_input("低空達標（效率）", min_value=0.0, max_value=9999.0, value=48.0, step=1.0)

    # upload
    card_open("📤 上傳原始資料（可多檔合併）")
    files = st.file_uploader(
        "上傳 Excel / CSV",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    run = st.button("🚀 產出報表", type="primary", disabled=not files)
    card_close()

    if "picking_result" not in st.session_state:
        st.session_state.picking_result = None

    if run:
        # 計算一次後存 session，避免你按匯出導致 KPI 畫面消失
        with st.spinner("計算中，請稍候."):
            raw_df = _load_uploaded_files(files)
            if raw_df.empty:
                st.error("未讀到任何資料，請確認檔案內容。")
                return

            # 合併版邏輯：去成箱 + 合併列 + 解析時間
            df = remove_boxed_rows(raw_df)
            full_df = combine_rows(df)
            full_df = ensure_datetime(full_df).dropna(subset=["揀貨完成時間"])

            # 篩上午/下午 + 計算
            morning_df = filter_morning_period(full_df)
            afternoon_df = filter_afternoon_period(full_df)

            mapping = st.session_state.pick_map

            morning_stats = calculate_statistics_morning(morning_df, full_df, mapping)
            afternoon_stats = calculate_statistics_afternoon(afternoon_df, full_df, mapping)

            # 產出 xlsx bytes（同一張 Sheet 上下分段）
            xlsx_bytes = build_export_xlsx_bytes(
                title=report_title.strip() or "總揀達標獎金計算報表（合併版）",
                morning_df=morning_stats,
                afternoon_df=afternoon_stats,
                low_threshold=float(low_threshold),
                high_threshold=float(high_threshold),
            )

            st.session_state.picking_result = {
                "report_title": report_title.strip() or "總揀達標獎金計算報表（合併版）",
                "morning_stats": morning_stats,
                "afternoon_stats": afternoon_stats,
                "xlsx_bytes": xlsx_bytes,
                "low_threshold": float(low_threshold),
                "high_threshold": float(high_threshold),
            }

    # render result (persist)
    result = st.session_state.picking_result
    if not result:
        st.info("請先上傳檔案並點「產出報表」。")
        return

    morning_stats = result["morning_stats"]
    afternoon_stats = result["afternoon_stats"]
    low_thr = float(result.get("low_threshold", 48.0))
    high_thr = float(result.get("high_threshold", 20.0))

    # KPI畫面：上午/下午上下顯示（維持你現在呈現）
    card_open("📊 第一階段（上午）")
    if morning_stats is None or morning_stats.empty:
        st.info("上午無資料")
    else:
        st.dataframe(
            _style_kpi_rows(morning_stats, low_thr, high_thr),
            use_container_width=True,
            hide_index=True,
        )
    card_close()

    card_open("📊 第二階段（下午）")
    if afternoon_stats is None or afternoon_stats.empty:
        st.info("下午無資料")
    else:
        st.dataframe(
            _style_kpi_rows(afternoon_stats, low_thr, high_thr),
            use_container_width=True,
            hide_index=True,
        )
    card_close()

    # ✅ 匯出按鈕：直接是按鈕（不會讓 KPI 消失，因為已存 session_state）
    st.download_button(
        label="⬇️ 匯出報表（Excel）",
        data=result["xlsx_bytes"],
        file_name=f"{result['report_title']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
