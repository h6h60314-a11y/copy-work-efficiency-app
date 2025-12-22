# pages/3_總揀達標.py
from __future__ import annotations

import io
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from common_ui import (
    inject_logistics_theme,
    set_page,
    KPI,
    render_kpis,
    bar_topN,
    download_excel,
    card_open,
    card_close,
    sidebar_controls,  # 你已經有的：排除區間手動輸入 HH:MM（不下拉）
)

# =========================================================
# Config (上午/下午規則)
# =========================================================
MORNING_END_STR = "12:30:00"
M_REST_START_STR = "10:00:00"
M_REST_END_STR = "10:15:00"

AFTERNOON_START_STR = "13:30:00"
AFTERNOON_END_STR = "18:00:00"
A_REST_START_STR = "15:30:00"
A_REST_END_STR = "15:45:00"

IDLE_THRESHOLD_MINUTES = 10  # 空窗門檻(分鐘)
DEFAULT_START_TIME_STR = "08:05:00"

# 低空/高空達標門檻（可在 sidebar 調整）
LOW_TARGET_DEFAULT = 48
HIGH_TARGET_DEFAULT = 20

# =========================================================
# 揀貨人預設資料（合併版）
#  - 這段你原本合併版就有：姓名中文 & 起始時間 & 區域
# =========================================================
preset_picker_info = {
    "20230412002": {"姓名": "吳秉丞", "起始時間": "8:05:00", "區域": "低空"},
    "20200812002": {"姓名": "彭慈暉", "起始時間": "7:05:00", "區域": "低空"},
    "20210104001": {"姓名": "楊承珉", "起始時間": "7:05:00", "區域": "低空"},
    "20201109001": {"姓名": "梁冠如", "起始時間": "8:05:00", "區域": "低空"},
    "20201109003": {"姓名": "吳振凱", "起始時間": "8:05:00", "區域": "低空"},
    "20231226003": {"姓名": "顏秀菁", "起始時間": "8:05:00", "區域": "低空"},
    "20200922002": {"姓名": "葉欲弘", "起始時間": "8:05:00", "區域": "低空"},
    "20200924001": {"姓名": "黃雅君", "起始時間": "8:05:00", "區域": "低空"},
    "20220526001": {"姓名": "黃芷憶", "起始時間": "8:05:00", "區域": "低空"},
    "20240221003": {"姓名": "呂治明", "起始時間": "8:05:00", "區域": "低空"},
    "20240909001": {"姓名": "蔡麗珠", "起始時間": "8:05:00", "區域": "低空"},
    "20240926001": {"姓名": "陳莉娜", "起始時間": "8:05:00", "區域": "低空"},
    "20241011002": {"姓名": "林雙慧", "起始時間": "8:05:00", "區域": "低空"},
    "20250326001": {"姓名": "王大中", "起始時間": "8:05:00", "區域": "低空"},
    "20250303002": {"姓名": "周映華", "起始時間": "8:05:00", "區域": "低空"},
    "20250311001": {"姓名": "徐欣", "起始時間": "8:05:00", "區域": "低空"},
    "20250226002": {"姓名": "阮黃英", "起始時間": "7:05:00", "區域": "低空"},
    "20250901009": {"姓名": "張寶萱", "起始時間": "8:35:00", "區域": "低空"},
    "20250226010": {"姓名": "楊心如", "起始時間": "7:05:00", "區域": "低空"},
    "20250226011": {"姓名": "阮武玉玄", "起始時間": "7:05:00", "區域": "低空"},
    "20250226016": {"姓名": "阮氏美麗", "起始時間": "7:05:00", "區域": "低空"},
    "20250226018": {"姓名": "阮瑞美黃緣", "起始時間": "7:05:00", "區域": "低空"},
    "20250226020": {"姓名": "潘氏慶平", "起始時間": "7:05:00", "區域": "低空"},
    "20250226021": {"姓名": "潘氏青江", "起始時間": "7:05:00", "區域": "低空"},
    "20250923019": {"姓名": "阮氏紅深", "起始時間": "8:05:00", "區域": "低空"},
    "20250226026": {"姓名": "黎氏瓊", "起始時間": "7:05:00", "區域": "低空"},
    "20230119001": {"姓名": "陶春青", "起始時間": "7:05:00", "區域": "高空"},
    "20240313003": {"姓名": "阮曰忠", "起始時間": "7:05:00", "區域": "高空"},
    "20220421001": {"姓名": "阮德平", "起始時間": "8:05:00", "區域": "高空"},
    "20250617001": {"姓名": "阮文譚", "起始時間": "7:05:00", "區域": "高空"},
    "09963": {"姓名": "黃謙凱", "起始時間": "8:05:00", "區域": "低空"},
    "11399": {"姓名": "陳哲沅", "起始時間": "8:05:00", "區域": "低空"},
}


# =========================================================
# Utilities
# =========================================================
def _t(s: str):
    return datetime.strptime(s, "%H:%M:%S").time()


MORNING_END = _t(MORNING_END_STR)
M_REST_START = _t(M_REST_START_STR)
M_REST_END = _t(M_REST_END_STR)

AFTERNOON_START = _t(AFTERNOON_START_STR)
AFTERNOON_END = _t(AFTERNOON_END_STR)
A_REST_START = _t(A_REST_START_STR)
A_REST_END = _t(A_REST_END_STR)

IDLE_THRESHOLD = timedelta(minutes=IDLE_THRESHOLD_MINUTES)


def parse_tw_datetime(series: pd.Series) -> pd.Series:
    """
    支援：
      1) 2025/06/26 上午 09:35:01
      2) 2025/6/30 10:37:51
      3) Excel 浮點序列
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    s = series.astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    num_mask = s.str.match(r"^\d+(\.\d+)?$")
    if num_mask.any():
        out.loc[num_mask] = pd.to_datetime(s[num_mask].astype(float), unit="d", origin="1899-12-30")

    str_mask = ~num_mask
    if str_mask.any():
        tmp = s[str_mask]
        pm_mask = tmp.str.contains("下午")
        tmp = (
            tmp.str.replace("上午", "", regex=False)
            .str.replace("下午", "", regex=False)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

        parsed = pd.to_datetime(tmp, format="%Y/%m/%d %H:%M:%S", errors="coerce")
        need_fallback = parsed.isna()
        if need_fallback.any():
            parsed.loc[need_fallback] = pd.to_datetime(tmp[need_fallback], errors="coerce")

        if pm_mask.any():
            pm_idx = pm_mask[pm_mask].index
            adjust_idx = pm_idx[parsed.loc[pm_idx].dt.hour < 12]
            parsed.loc[adjust_idx] += pd.Timedelta(hours=12)

        out.loc[str_mask] = parsed

    return out


def _get_name(picker: str) -> str:
    info = preset_picker_info.get(str(picker).strip())
    if info and info.get("姓名"):
        return str(info["姓名"]).strip()
    return ""


def _get_region(picker: str) -> str:
    info = preset_picker_info.get(str(picker).strip())
    region = (info or {}).get("區域", "")
    region = str(region).strip() if region is not None else ""
    return region if region else "低空"


def _get_start_time(picker: str) -> str:
    info = preset_picker_info.get(str(picker).strip())
    s = (info or {}).get("起始時間", "") or ""
    s = str(s).strip()
    return s if s else DEFAULT_START_TIME_STR


def _storage_area_str(df: pd.DataFrame) -> str:
    # 你原始檔可能有「儲位區域」或相近欄位；沒有就回空
    for col in ["儲位區域", "到", "儲位", "儲位明細"]:
        if col in df.columns:
            vals = df[col].astype(str).str.strip()
            vals = vals[vals != ""].dropna().unique().tolist()
            if vals:
                return "、".join(vals[:12]) + ("…" if len(vals) > 12 else "")
    return ""


def _overlap_segments(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> list[tuple[datetime, datetime]]:
    s = max(a_start, b_start)
    e = min(a_end, b_end)
    if e > s:
        return [(s, e)]
    return []


def _split_idle_segment(seg_start: datetime, seg_end: datetime, rest_start: datetime, rest_end: datetime) -> list[tuple[datetime, datetime]]:
    """
    把空窗段扣掉休息段的重疊（避免把休息算空窗）
    """
    if seg_end <= seg_start:
        return []

    # 沒有重疊休息
    if seg_end <= rest_start or seg_start >= rest_end:
        return [(seg_start, seg_end)]

    parts = []
    if seg_start < rest_start:
        parts.append((seg_start, rest_start))
    if seg_end > rest_end:
        parts.append((rest_end, seg_end))
    return [(s, e) for s, e in parts if e > s]


def _get_effective_idle_segments(prev_t: datetime, curr_t: datetime, rest_start: datetime, rest_end: datetime) -> list[tuple[datetime, datetime]]:
    """
    只有 gap >= IDLE_THRESHOLD 才算空窗，並扣除休息重疊
    """
    gap = curr_t - prev_t
    if gap < IDLE_THRESHOLD:
        return []
    return _split_idle_segment(prev_t, curr_t, rest_start, rest_end)


def _calc_shift_stats(
    full_df: pd.DataFrame,
    shift: str,
    low_target: float,
    high_target: float,
) -> pd.DataFrame:
    """
    shift: "morning" or "afternoon"
    回傳 columns:
      區域, 揀貨人, 姓名, 筆數, 工作區間, 總分鐘, 效率, 空窗分鐘, 儲位區域, 空窗時間段
    """
    if full_df is None or full_df.empty:
        return pd.DataFrame(columns=["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"])

    if "揀貨人" not in full_df.columns or "揀貨完成時間" not in full_df.columns:
        return pd.DataFrame(columns=["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"])

    df = full_df.copy()
    df["揀貨人"] = df["揀貨人"].astype(str).str.strip()
    df["揀貨完成時間"] = parse_tw_datetime(df["揀貨完成時間"])
    df = df.dropna(subset=["揀貨完成時間"]).sort_values(["揀貨人", "揀貨完成時間"])

    stats_rows = []
    for picker, picker_df in df.groupby("揀貨人"):
        picker_df = picker_df.sort_values("揀貨完成時間").copy()
        times = picker_df["揀貨完成時間"].tolist()
        if not times:
            continue

        first_record = times[0]
        last_record = times[-1]

        # 基準日：用第一筆日期
        base_date = first_record.date()

        if shift == "morning":
            start_time = _t(_get_start_time(picker) if ":" in _get_start_time(picker) else DEFAULT_START_TIME_STR)
            shift_start = datetime.combine(base_date, start_time)
            shift_end = datetime.combine(base_date, MORNING_END)
            rest_start = datetime.combine(base_date, M_REST_START)
            rest_end = datetime.combine(base_date, M_REST_END)
        else:
            shift_start = datetime.combine(base_date, AFTERNOON_START)
            shift_end = datetime.combine(base_date, AFTERNOON_END)
            rest_start = datetime.combine(base_date, A_REST_START)
            rest_end = datetime.combine(base_date, A_REST_END)

        # 有效起訖：以班別規則框住，再和實際有資料的範圍交集
        effective_start = max(shift_start, first_record)
        effective_end = min(shift_end, last_record)

        # 若完全沒有落在該班別，略過
        if effective_end <= effective_start:
            continue

        # 扣除休息（只扣和有效區間有重疊的部分）
        rest_overlap = _overlap_segments(effective_start, effective_end, rest_start, rest_end)
        rest_duration = sum((e - s for s, e in rest_overlap), timedelta(0))

        work_duration = (effective_end - effective_start) - rest_duration
        total_minutes = round(work_duration.total_seconds() / 60, 2)
        if total_minutes <= 0:
            total_minutes = 0.0

        # 只統計落在有效區間內的筆數
        working = picker_df[(picker_df["揀貨完成時間"] >= effective_start) & (picker_df["揀貨完成時間"] <= effective_end)]
        num_records = int(len(working))

        # 空窗段
        idle_segments: list[tuple[datetime, datetime]] = []
        work_times = working["揀貨完成時間"].tolist()

        if work_times:
            # 開頭空窗
            if work_times[0] > effective_start:
                idle_segments.extend(_split_idle_segment(effective_start, work_times[0], rest_start, rest_end))
            # 中間空窗
            for i in range(1, len(work_times)):
                idle_segments.extend(_get_effective_idle_segments(work_times[i - 1], work_times[i], rest_start, rest_end))
            # 結尾空窗
            if work_times[-1] < effective_end:
                idle_segments.extend(_get_effective_idle_segments(work_times[-1], effective_end, rest_start, rest_end))

        idle_minutes = round(sum((e - s).total_seconds() for s, e in idle_segments) / 60, 2)

        efficiency = round((num_records / total_minutes * 60) if total_minutes else 0, 2)
        time_period_str = f"{effective_start.strftime('%H:%M:%S')} ~ {effective_end.strftime('%H:%M:%S')}"
        idle_segments_str = "; ".join(f"{s.strftime('%H:%M:%S')} ~ {e.strftime('%H:%M:%S')}" for s, e in idle_segments)

        storage_area_str = _storage_area_str(working)
        region = _get_region(picker)
        name = _get_name(picker)

        stats_rows.append(
            {
                "區域": region,
                "揀貨人": picker,
                "姓名": name,  # 中文
                "筆數": num_records,
                "工作區間": time_period_str,
                "總分鐘": total_minutes,
                "效率": efficiency,
                "空窗分鐘": idle_minutes,
                "儲位區域": storage_area_str,
                "空窗時間段": idle_segments_str,
            }
        )

    out = pd.DataFrame(stats_rows)
    if out.empty:
        return pd.DataFrame(columns=["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"])

    out["區域"] = pd.Categorical(out["區域"], categories=["低空", "高空"], ordered=True)
    out = out.sort_values(["區域", "揀貨人"], ascending=[True, True]).reset_index(drop=True)
    return out[
        ["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"]
    ]


def build_export_xlsx_bytes_single_sheet(
    title: str,
    morning_df: pd.DataFrame,
    afternoon_df: pd.DataFrame,
    low_target: float,
    high_target: float,
) -> bytes:
    """
    單一 Sheet1 上下分段（第一階段=上午、第二階段=下午）
    並依區域門檻套色：達標綠 / 未達標紅
    """
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

    cols = ["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"]
    max_col = len(cols)

    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    fill_green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_red = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    title_font = Font(name="新細明體", size=18, bold=True)
    stage_font = Font(name="新細明體", size=16, bold=True)
    head_font = Font(name="新細明體", size=11, bold=True)
    body_font = Font(name="新細明體", size=11)

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    def threshold(region: str) -> float:
        return float(high_target) if str(region).strip() == "高空" else float(low_target)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"

    def merge_row(row: int, text: str, font: Font):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=max_col)
        cell = ws.cell(row=row, column=1, value=text)
        cell.font = font
        cell.alignment = align_center
        for c in range(1, max_col + 1):
            ws.cell(row=row, column=c).border = border

    def write_header(row: int):
        for c, h in enumerate(cols, start=1):
            cell = ws.cell(row=row, column=c, value=h)
            cell.font = head_font
            cell.alignment = align_center
            cell.border = border

    def write_df(start_row: int, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return start_row - 1

        for r_idx, (_, r) in enumerate(df.iterrows(), start=start_row):
            for c_idx, col in enumerate(cols, start=1):
                val = r.get(col, "")
                cell = ws.cell(row=r_idx, column=c_idx, value=val)
                cell.font = body_font
                cell.alignment = align_center
                cell.border = border
        return start_row + len(df) - 1

    def paint_rows(data_first_row: int, data_last_row: int, eff_col_idx: int, region_col_idx: int):
        if data_last_row < data_first_row:
            return
        for rr in range(data_first_row, data_last_row + 1):
            reg = str(ws.cell(row=rr, column=region_col_idx).value or "").strip()
            th = threshold(reg)
            try:
                eff = float(ws.cell(row=rr, column=eff_col_idx).value)
            except Exception:
                eff = 0.0
            fill = fill_green if eff >= th else fill_red
            for cc in range(1, max_col + 1):
                ws.cell(row=rr, column=cc).fill = fill

    # ===== Title / Stage1 / Morning =====
    merge_row(1, title, title_font)
    merge_row(2, "第一階段", stage_font)

    header_row_1 = 3
    write_header(header_row_1)
    data_start_1 = header_row_1 + 1

    mdf = morning_df.copy() if morning_df is not None else pd.DataFrame()
    if not mdf.empty:
        for c in cols:
            if c not in mdf.columns:
                mdf[c] = ""
        mdf = mdf[cols]

    last_row_1 = write_df(data_start_1, mdf)

    eff_col = cols.index("效率") + 1
    reg_col = cols.index("區域") + 1
    if not mdf.empty:
        paint_rows(data_start_1, last_row_1, eff_col, reg_col)

    # ===== Stage2 / Afternoon =====
    gap = 2
    stage_row_2 = (last_row_1 if last_row_1 >= data_start_1 else (data_start_1 - 1)) + gap + 1
    merge_row(stage_row_2, "第二階段", stage_font)

    header_row_2 = stage_row_2 + 1
    write_header(header_row_2)
    data_start_2 = header_row_2 + 1

    adf = afternoon_df.copy() if afternoon_df is not None else pd.DataFrame()
    if not adf.empty:
        for c in cols:
            if c not in adf.columns:
                adf[c] = ""
        adf = adf[cols]

    last_row_2 = write_df(data_start_2, adf)
    if not adf.empty:
        paint_rows(data_start_2, last_row_2, eff_col, reg_col)

    # Column widths（照你之前合併版習慣）
    widths = {"A": 8, "B": 22, "C": 14, "D": 6, "E": 20, "F": 10, "G": 10, "H": 10, "I": 30, "J": 35}
    for col_letter, w in widths.items():
        ws.column_dimensions[col_letter].width = w

    ws.freeze_panes = "A4"

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _adapt_exclude_windows_to_skip_rules(exclude_windows):
    """
    把 common_ui.sidebar_controls() 的 exclude_windows：
      [{"start":"HH:MM","end":"HH:MM","data_entry":""}, ...]
    轉成這頁使用的 skip_rules：
      [{"start": time, "end": time}, ...]
    """
    rules = []
    for w in exclude_windows or []:
        try:
            s = pd.to_datetime(w.get("start", "")).time()
            e = pd.to_datetime(w.get("end", "")).time()
        except Exception:
            continue
        rules.append({"start": s, "end": e})
    return rules


def _apply_skip_rules(df: pd.DataFrame, skip_rules: list[dict]) -> pd.DataFrame:
    """
    排除區間：把落在排除時段內的資料剔除（依時間）
    """
    if df is None or df.empty or not skip_rules:
        return df

    if "揀貨完成時間" not in df.columns:
        return df

    out = df.copy()
    out["揀貨完成時間"] = parse_tw_datetime(out["揀貨完成時間"])
    out = out.dropna(subset=["揀貨完成時間"])

    mask_keep = pd.Series(True, index=out.index)
    for r in skip_rules:
        stt = r.get("start")
        edt = r.get("end")
        if stt is None or edt is None:
            continue
        t = out["揀貨完成時間"].dt.time
        mask_keep &= ~((t >= stt) & (t <= edt))

    return out.loc[mask_keep].copy()


def _read_uploads(uploaded_files: list[st.runtime.uploaded_file_manager.UploadedFile]) -> pd.DataFrame:
    dfs = []
    for uf in uploaded_files:
        name = (uf.name or "").lower()
        b = uf.getvalue()
        bio = io.BytesIO(b)

        if name.endswith(".csv"):
            df = pd.read_csv(bio)
        else:
            df = pd.read_excel(bio, dtype={"揀貨完成時間": str} if "揀貨完成時間" else None)

        df["__source_file__"] = uf.name
        dfs.append(df)

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


# =========================================================
# Streamlit Page
# =========================================================
def main():
    inject_logistics_theme()
    set_page("總揀達標（上午/下午分段）", icon="🧺", subtitle="同頁上下分段｜達標紅綠底色｜匯出按鈕不清畫面")

    # Sidebar controls（沿用你統一 UI：手動輸入排除區間，不下拉）
    controls = sidebar_controls(default_top_n=30, enable_exclude_windows=True, state_key_prefix="pick")
    top_n = int(controls["top_n"])
    skip_rules = _adapt_exclude_windows_to_skip_rules(controls.get("exclude_windows", []))

    with st.sidebar:
        st.markdown("---")
        low_target = st.number_input("低空達標門檻（效率 ≥）", min_value=1, max_value=999, value=int(LOW_TARGET_DEFAULT), step=1)
        high_target = st.number_input("高空達標門檻（效率 ≥）", min_value=1, max_value=999, value=int(HIGH_TARGET_DEFAULT), step=1)
        report_title = st.text_input("報表標題（可留空）", value="總揀達標獎金計算報表（合併版）")
        st.caption("提示：匯出為同一個 Sheet1，上下分段（第一階段=上午，第二階段=下午）")

    # Upload
    card_open("📤 上傳作業原始資料（總揀）")
    uploaded_files = st.file_uploader(
        "上傳 Excel / CSV（需包含：揀貨人、揀貨完成時間）",
        type=["xlsx", "xls", "xlsm", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    run = st.button("🚀 產出 KPI", type="primary", disabled=not uploaded_files)
    card_close()

    # 第一次進來：不跑
    if not run and "pick_result" not in st.session_state:
        st.info("請先上傳資料後，點『產出 KPI』")
        return

    # 只有按下產出才重新計算（確保匯出按鈕不會清掉畫面）
    if run:
        with st.spinner("計算中，請稍候..."):
            raw_df = _read_uploads(uploaded_files)
            raw_df = _apply_skip_rules(raw_df, skip_rules)

            morning_stats = _calc_shift_stats(raw_df, "morning", low_target=low_target, high_target=high_target)
            afternoon_stats = _calc_shift_stats(raw_df, "afternoon", low_target=low_target, high_target=high_target)

            # 存到 session_state，讓按匯出時畫面不消失
            st.session_state.pick_result = {
                "raw_rows": int(len(raw_df)) if raw_df is not None else 0,
                "morning_stats": morning_stats,
                "afternoon_stats": afternoon_stats,
                "low_target": float(low_target),
                "high_target": float(high_target),
                "title": report_title.strip() or "總揀達標獎金計算報表（合併版）",
                "top_n": int(top_n),
            }

    # 從 session_state 取結果
    res = st.session_state.get("pick_result", {})
    morning_stats: pd.DataFrame = res.get("morning_stats", pd.DataFrame())
    afternoon_stats: pd.DataFrame = res.get("afternoon_stats", pd.DataFrame())
    low_target = float(res.get("low_target", LOW_TARGET_DEFAULT))
    high_target = float(res.get("high_target", HIGH_TARGET_DEFAULT))
    title = str(res.get("title", "總揀達標獎金計算報表（合併版）"))
    top_n = int(res.get("top_n", 30))

    # KPI blocks
    st.divider()
    col_l, col_r = st.columns(2)

    def _render_shift_block(label: str, sdf: pd.DataFrame, region_target_low: float, region_target_high: float):
        card_open(f"{label} KPI")
        if sdf is None or sdf.empty:
            st.info("本區段無資料")
            card_close()
            return

        # 混合門檻的達標率：逐列依區域判斷
        def _row_ok(r):
            th = region_target_high if str(r.get("區域", "")).strip() == "高空" else region_target_low
            try:
                return float(r.get("效率", 0)) >= float(th)
            except Exception:
                return False

        ok_rate = float(sdf.apply(_row_ok, axis=1).mean()) if len(sdf) else 0.0

        render_kpis(
            [
                KPI("人數", f"{len(sdf):,}"),
                KPI("總筆數", f"{int(sdf['筆數'].sum()) if '筆數' in sdf.columns else 0:,}"),
                KPI("總分鐘", f"{float(sdf['總分鐘'].sum()) if '總分鐘' in sdf.columns else 0:.2f}"),
                KPI("平均效率", f"{float(sdf['效率'].mean()) if '效率' in sdf.columns and len(sdf) else 0:.2f}"),
                KPI("達標率", f"{ok_rate:.0%}"),
            ]
        )
        card_close()

        card_open(f"{label} 效率排行（Top {top_n}）")
        # 這裡用 common_ui.bar_topN 的 target 只能一條線，
        # 我用低空門檻當參考線（高空另用底色在 Excel）
        ref_target = float(region_target_low)
        bar_topN(
            sdf,
            x_col="姓名" if "姓名" in sdf.columns else "揀貨人",
            y_col="效率",
            hover_cols=["區域", "筆數", "總分鐘", "工作區間"],
            top_n=top_n,
            target=ref_target,
            title=f"參考線=低空達標 {int(region_target_low)}（高空達標 {int(region_target_high)} 於 Excel 以底色判斷）",
        )
        card_close()

        # 明細表（你要低於門檻紅色：在頁面上用 dataframe style）
        def _style_rows(row):
            th = region_target_high if str(row.get("區域", "")).strip() == "高空" else region_target_low
            try:
                ok = float(row.get("效率", 0)) >= float(th)
            except Exception:
                ok = False
            # 這裡只做背景提示，真正輸出 Excel 會整列紅/綠
            return ["background-color: rgba(220,38,38,0.18)" if not ok else "" for _ in row.index]

        card_open(f"{label} 明細（未達標紅底）")
        try:
            st.dataframe(sdf.style.apply(_style_rows, axis=1), use_container_width=True, hide_index=True)
        except Exception:
            st.dataframe(sdf, use_container_width=True, hide_index=True)
        card_close()

    with col_l:
        _render_shift_block("☀️ 上午（第一階段）", morning_stats, low_target, high_target)

    with col_r:
        _render_shift_block("🌙 下午（第二階段）", afternoon_stats, low_target, high_target)

    # Export (按鈕，不清畫面)
    st.divider()
    card_open("⬇️ 匯出報表（按鈕）")
    xlsx_bytes = build_export_xlsx_bytes_single_sheet(
        title=title,
        morning_df=morning_stats,
        afternoon_df=afternoon_stats,
        low_target=low_target,
        high_target=high_target,
    )
    download_excel(xlsx_bytes, filename=f"{title}.xlsx")
    card_close()


if __name__ == "__main__":
    main()
