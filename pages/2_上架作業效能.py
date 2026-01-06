import io
import re
import datetime as dt
from typing import Dict, List, Tuple, Optional, Any

import pandas as pd
import streamlit as st

from common_ui import (
    inject_logistics_theme,
    set_page,
    KPI,
    render_kpis,
    bar_topN,
    card_open,
    card_close,
    download_excel_card,   # ✅ 一行=按鈕（且外框不分段）
    sidebar_controls,
)

# =========================================================
# 參數
# =========================================================
TO_EXCLUDE_KEYWORDS = ["CGS", "JCPL", "QC99", "GREAT0001X", "GX010", "PD99"]
TO_EXCLUDE_PATTERN = re.compile("|".join(re.escape(k) for k in TO_EXCLUDE_KEYWORDS), flags=re.IGNORECASE)

INPUT_USER_CANDIDATES = ["記錄輸入人", "記錄輸入者", "建立人", "輸入人"]
REV_DT_CANDIDATES = ["修訂日期", "修訂時間", "修訂日", "異動時間", "修改時間"]

TARGET_EFF_DEFAULT = 20
IDLE_MIN_THRESHOLD_DEFAULT = 10

AM_START, AM_END = dt.time(7, 0, 0), dt.time(12, 30, 0)
PM_START, PM_END = dt.time(13, 30, 0), dt.time(23, 59, 59)

NAME_MAP = {
    "20200924001": "黃雅君", "20210805001": "郭中合", "20220505002": "阮文青明",
    "20221221001": "阮文全", "20221222005": "謝忠龍", "20230119001": "陶春青",
    "20240926001": "陳莉娜", "20241011002": "林雙慧", "20250502001": "吳詩敏",
    "20250617001": "阮文譚", "20250617003": "喬家寶", "20250901009": "張寶萱",
    "G01": "0", "20201109003": "吳振凱", "09963": "黃謙凱",
    "20240313003": "阮曰忠", "20201109001": "梁冠如", "10003": "李茂銓",
    "20200922002": "葉欲弘", "20250923019": "阮氏紅深", "9963": "黃謙凱",
    "11399": "陳哲沅",
}

BREAK_RULES = [
    (dt.time(20, 45, 0), dt.time(22, 30, 0), 0,  "首≥20:45 且 末≤22:30 → 0 分鐘"),
    (dt.time(18, 30, 0), dt.time(20, 30, 0), 0,  "首≥18:30 且 末≤20:30 → 0 分鐘"),
    (dt.time(15, 30, 0), dt.time(18,  0, 0), 0,  "首≥15:30 且 末≤18:00 → 0 分鐘"),
    (dt.time(13, 30, 0), dt.time(15, 35, 0), 0,  "首≥13:30 且 末≤15:35 → 0 分鐘"),
    (dt.time(20, 45, 0), dt.time(23,  0, 0), 0,  "首≥20:45 且 末≤23:00 → 0 分鐘"),
    (dt.time(20,  0, 0), dt.time(22,  0, 0), 15, "首≥20:00 且 末≤22:00 → 15 分鐘"),
    (dt.time(18, 30, 0), dt.time(22,  0, 0), 15, "首≥18:30 且 末≤22:00 → 15 分鐘"),
    (dt.time(19,  0, 0), dt.time(22, 30, 0), 15, "首≥19:00 且 末≤22:30 → 15 分鐘"),
    (dt.time(13, 30, 0), dt.time(18,  0, 0), 15, "首≥13:30 且 末≤18:00 → 15 分鐘"),
    (dt.time(16,  0, 0), dt.time(20, 40, 0), 30, "首≥16:00 且 末≤20:40 → 30 分鐘"),
    (dt.time(15, 30, 0), dt.time(20, 30, 0), 30, "首≥15:30 且 末≤20:30 → 30 分鐘"),
    (dt.time(17,  0, 0), dt.time(22, 30, 0), 45, "首≥17:00 且 末≤22:30 → 45 分鐘"),
    (dt.time(15, 45, 0), dt.time(22, 30, 0), 45, "首≥15:45 且 末≤22:30 → 45 分鐘"),
    (dt.time(13, 30, 0), dt.time(20, 29, 0), 45, "首≥13:30 且 末≤20:29 → 45 分鐘"),
    (dt.time(13, 30, 0), dt.time(23,  0, 0), 60, "首≥13:30 且 末≤23:00 → 60 分鐘"),
    (dt.time(11,  0, 0), dt.time(17,  0, 0), 75, "首≥11:00 且 末≤17:00 → 75 分鐘"),
    (dt.time( 8,  0, 0), dt.time(17,  0, 0), 90, "首≥08:00 且 末≤17:00 → 90 分鐘"),
    (dt.time(10, 50, 0), dt.time(23,  0, 0), 120,"首≥10:50 且 末≤23:00 → 120 分鐘"),
    (dt.time( 8,  0, 0), dt.time(23,  0, 0), 135,"首≥08:00 且 末≤23:00 → 135 分鐘"),
]

# ✅ 預設排除空窗時段（可被 sidebar 覆蓋）
EXCLUDE_IDLE_RANGES_DEFAULT = [
    (dt.time(10,  0, 0), dt.time(10, 15, 0)),
    (dt.time(12, 30, 0), dt.time(13, 30, 0)),
    (dt.time(15, 30, 0), dt.time(15, 45, 0)),
    (dt.time(18,  0, 0), dt.time(18, 30, 0)),
    (dt.time(20, 30, 0), dt.time(20, 45, 0)),
]

# =========================================================
# 讀檔（bytes）
# =========================================================
def read_excel_any_quiet_bytes(name: str, content: bytes) -> Dict[str, pd.DataFrame]:
    ext = (name.split(".")[-1] or "").lower()
    if ext in ("xlsx", "xlsm"):
        xl = pd.ExcelFile(io.BytesIO(content), engine="openpyxl")
        return {sn: pd.read_excel(xl, sheet_name=sn) for sn in xl.sheet_names}
    if ext == "xls":
        xl = pd.ExcelFile(io.BytesIO(content), engine="xlrd")
        return {sn: pd.read_excel(xl, sheet_name=sn) for sn in xl.sheet_names}
    if ext == "csv":
        for enc in ("utf-8-sig", "cp950", "big5"):
            try:
                return {"CSV": pd.read_csv(io.BytesIO(content), encoding=enc)}
            except Exception:
                continue
        raise Exception("CSV 讀取失敗（請確認編碼）")
    raise Exception("不支援的副檔名（僅支援 xlsx/xlsm/xls/csv）")


def _strip_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_first_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = [str(c).strip() for c in df.columns]
    s = set(cols)
    for name in candidates:
        if name in s:
            return name
    norm_map = {re.sub(r"[（）\(\)\s]", "", c): c for c in cols}
    for name in candidates:
        key = re.sub(r"[（）\(\)\s]", "", name)
        if key in norm_map:
            return norm_map[key]
    return None


def normalize_to_qc(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper().eq("QC")


def to_not_excluded_mask(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    return ~s.str.contains(TO_EXCLUDE_PATTERN, na=False)


def prepare_filtered_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    df = _strip_cols(df)
    if "由" not in df.columns or "到" not in df.columns:
        return pd.DataFrame()
    return df[normalize_to_qc(df["由"]) & to_not_excluded_mask(df["到"])].copy()


def break_minutes_for_span(first_dt: pd.Timestamp, last_dt: pd.Timestamp) -> Tuple[int, str]:
    if pd.isna(first_dt) or pd.isna(last_dt):
        return 0, "無時間資料"
    stt, edt = first_dt.time(), last_dt.time()
    for st_ge, ed_le, mins, tag in BREAK_RULES:
        if (stt >= st_ge) and (edt <= ed_le):
            return int(mins), str(tag)
    return 0, "未命中規則"


# =========================================================
# ✅ 排除區間切段 + 「工時」扣除排除時段（關鍵）
# =========================================================
def _subtract_exclusions(s_dt: pd.Timestamp, e_dt: pd.Timestamp, exclude_ranges):
    if s_dt >= e_dt or not exclude_ranges:
        return [(s_dt, e_dt)]
    segments = [(s_dt, e_dt)]
    for ex_s_t, ex_e_t in exclude_ranges:
        ex_s = pd.Timestamp.combine(s_dt.date(), ex_s_t)
        ex_e = pd.Timestamp.combine(s_dt.date(), ex_e_t)
        new_segments = []
        for a, b in segments:
            if b <= ex_s or a >= ex_e:
                new_segments.append((a, b))
            else:
                if a < ex_s:
                    new_segments.append((a, ex_s))
                if b > ex_e:
                    new_segments.append((ex_e, b))
        segments = [(x, y) for (x, y) in new_segments if x < y]
    return segments


def _work_minutes_excluding_windows(
    first_dt: pd.Timestamp,
    last_dt: pd.Timestamp,
    exclude_ranges: List[Tuple[dt.time, dt.time]],
) -> int:
    """first~last 扣掉排除時段後的工作分鐘（✅ 讓效率/圖表跟著更新）"""
    if pd.isna(first_dt) or pd.isna(last_dt) or first_dt >= last_dt:
        return 0
    segs = _subtract_exclusions(first_dt, last_dt, exclude_ranges or [])
    mins = sum((b - a).total_seconds() for a, b in segs) / 60.0
    return max(int(round(mins)), 0)


def _compute_idle(
    series_dt: pd.Series,
    min_minutes: int,
    exclude_ranges: List[Tuple[dt.time, dt.time]],
) -> Tuple[int, str]:
    if series_dt is None or series_dt.size < 2:
        return 0, ""

    s = pd.to_datetime(series_dt, errors="coerce").dropna().sort_values()
    if s.size < 2:
        return 0, ""

    total_min, ranges_txt = 0, []
    prev = s.iloc[0]
    for cur in s.iloc[1:]:
        if cur <= prev:
            prev = cur
            continue

        # ✅ 空窗分鐘：gap 裡面扣掉「排除空窗時段」
        for a, b in _subtract_exclusions(prev, cur, exclude_ranges or []):
            gap_min = int(round((b - a).total_seconds() / 60.0))
            if gap_min >= int(min_minutes):
                total_min += gap_min
                ranges_txt.append(f"{a.time()} ~ {b.time()}")
        prev = cur

    return int(total_min), "；".join(ranges_txt)


def _span_metrics(series_dt: pd.Series):
    if series_dt is None or series_dt.empty:
        return pd.NaT, pd.NaT, 0
    s = pd.to_datetime(series_dt, errors="coerce").dropna()
    if s.empty:
        return pd.NaT, pd.NaT, 0
    return s.min(), s.max(), int(s.size)


def _eff(n: int, m_minutes: int) -> float:
    return round((n / m_minutes * 60.0), 2) if m_minutes and m_minutes > 0 else 0.0


def compute_am_pm_for_group(
    g: pd.DataFrame,
    idle_threshold_min: int,
    exclude_idle_ranges: List[Tuple[dt.time, dt.time]],
) -> pd.Series:
    times = pd.to_datetime(g["__dt__"], errors="coerce").dropna()

    # 上午：07:00–12:30（✅ 工時也扣排除時段；上午不扣休）
    t_am = times[times.dt.time.between(AM_START, AM_END)]
    am_first, am_last, am_cnt = _span_metrics(t_am)
    am_mins = _work_minutes_excluding_windows(am_first, am_last, exclude_idle_ranges) if am_cnt > 0 else 0
    am_eff = _eff(am_cnt, am_mins)
    am_idle_min, am_idle_ranges = _compute_idle(
        t_am, min_minutes=int(idle_threshold_min), exclude_ranges=exclude_idle_ranges
    )

    # 下午：13:30–23:59:59（✅ 先扣排除時段，再依規則扣休）
    t_pm = times[times.dt.time.between(PM_START, PM_END)]
    pm_first, pm_last, pm_cnt = _span_metrics(t_pm)
    if pm_cnt > 0:
        pm_break, pm_rule = break_minutes_for_span(pm_first, pm_last)
        raw_pm_mins = _work_minutes_excluding_windows(pm_first, pm_last, exclude_idle_ranges)
        pm_mins = max(int(raw_pm_mins - pm_break), 0)
    else:
        pm_break, pm_rule, pm_mins = 0, "無時間資料", 0
        pm_first, pm_last = pd.NaT, pd.NaT
    pm_eff = _eff(pm_cnt, pm_mins)
    pm_idle_min, pm_idle_ranges = _compute_idle(
        t_pm, min_minutes=int(idle_threshold_min), exclude_ranges=exclude_idle_ranges
    )

    # 整體：✅ 改成「上午工時 + 下午工時」（避免跨段空檔被算進去）
    whole_first, whole_last, day_cnt = _span_metrics(times)
    whole_mins = int(am_mins) + int(pm_mins)
    whole_break = int(pm_break) if pm_cnt > 0 else 0
    br_tag_whole = f"整體=上午+下午；下午規則：{pm_rule}" if pm_cnt > 0 else "整體=上午+下午；無下午資料"
    whole_eff = _eff(int(day_cnt), int(whole_mins))

    return pd.Series({
        "第一筆時間": whole_first, "最後一筆時間": whole_last, "當日筆數": int(day_cnt),
        "休息分鐘_整體": int(whole_break), "命中規則": br_tag_whole,
        "當日工時_分鐘_扣休": int(whole_mins), "效率_件每小時": whole_eff,

        "上午_第一筆": am_first, "上午_最後一筆": am_last, "上午_筆數": int(am_cnt),
        "上午_工時_分鐘": int(am_mins), "上午_效率_件每小時": am_eff,
        "上午_空窗分鐘": int(am_idle_min), "上午_空窗時段": am_idle_ranges,

        "下午_第一筆": pm_first, "下午_最後一筆": pm_last, "下午_筆數": int(pm_cnt),
        "下午_休息分鐘": int(pm_break), "下午_命中規則": pm_rule,
        "下午_工時_分鐘_扣休": int(pm_mins), "下午_效率_件每小時": pm_eff,
        "下午_空窗分鐘_扣休": int(pm_idle_min), "下午_空窗時段": pm_idle_ranges,
    })


# =========================================================
# sidebar_controls 排除區間解析（避免 common_ui 回傳格式不同造成失效）
# =========================================================
def _parse_time_any(x: Any) -> Optional[dt.time]:
    if x is None:
        return None
    if isinstance(x, dt.time):
        return x
    s = str(x).strip()
    if not s:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", s)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = int(m.group(3) or 0)
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        return None
    return dt.time(hh, mm, ss)


def _parse_exclude_windows(val: Any) -> List[Tuple[dt.time, dt.time]]:
    """
    支援：
    - [(time,time), ...]
    - [("10:00","10:15"), ...]
    - [{"start":"10:00","end":"10:15"}, ...]
    - {"windows":[...]} 之類包一層
    - "10:00-10:15,12:30-13:30" (字串)
    """
    if val is None:
        return EXCLUDE_IDLE_RANGES_DEFAULT

    if isinstance(val, dict):
        for k in ("exclude_windows", "exclude_windows_times", "windows", "ranges", "exclude_ranges"):
            if k in val:
                return _parse_exclude_windows(val.get(k))
        return EXCLUDE_IDLE_RANGES_DEFAULT

    if isinstance(val, str):
        raw = val.strip()
        if not raw:
            return EXCLUDE_IDLE_RANGES_DEFAULT
        parts = re.split(r"[，,;；\n]+", raw)
        items = []
        for p in parts:
            p = p.strip()
            if not p:
                continue
            m = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s*[-~～]\s*(\d{1,2}:\d{2}(?::\d{2})?)$", p)
            if m:
                items.append((m.group(1), m.group(2)))
        return _parse_exclude_windows(items) if items else EXCLUDE_IDLE_RANGES_DEFAULT

    if not isinstance(val, (list, tuple)):
        return EXCLUDE_IDLE_RANGES_DEFAULT

    out: List[Tuple[dt.time, dt.time]] = []
    for item in val:
        if isinstance(item, dict):
            s = _parse_time_any(item.get("start") or item.get("s") or item.get("from"))
            e = _parse_time_any(item.get("end") or item.get("e") or item.get("to"))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            s = _parse_time_any(item[0])
            e = _parse_time_any(item[1])
        else:
            s, e = None, None

        if s and e and (dt.datetime.combine(dt.date.today(), s) < dt.datetime.combine(dt.date.today(), e)):
            out.append((s, e))

    return out if out else EXCLUDE_IDLE_RANGES_DEFAULT


def _extract_exclude_value_from_controls(controls: Dict[str, Any]) -> Any:
    if not isinstance(controls, dict) or not controls:
        return None
    for k in (
        "exclude_windows",
        "exclude_windows_times",
        "exclude_ranges",
        "exclude_idle_ranges",
        "idle_exclude_windows",
        "idle_exclude_ranges",
    ):
        if k in controls and controls.get(k):
            return controls.get(k)
    for k, v in controls.items():
        lk = str(k).lower()
        if ("exclude" in lk) and (("window" in lk) or ("range" in lk)) and v:
            return v
    return None


# =========================================================
# Excel 匯出（bytes）
# =========================================================
def autosize_columns(ws, df: pd.DataFrame):
    from openpyxl.utils import get_column_letter
    cols = list(df.columns) if df is not None else []
    for i, col in enumerate(cols, start=1):
        if df is not None and not df.empty:
            sample = [len(str(x)) for x in df[col].head(800).tolist()]
            max_len = max([len(str(col))] + sample)
        else:
            max_len = max(len(str(col)), 8)
        ws.column_dimensions[get_column_letter(i)].width = min(max_len + 2, 60)


def shade_rows_by_efficiency(ws, header_name="效率_件每小時", green="C6EFCE", red="FFC7CE", target_eff=20):
    from openpyxl.styles import PatternFill
    eff_col = None
    for c in range(1, ws.max_column + 1):
        if str(ws.cell(row=1, column=c).value).strip() == header_name:
            eff_col = c
            break
    if eff_col is None:
        return
    green_fill = PatternFill(start_color=green, end_color=green, fill_type="solid")
    red_fill = PatternFill(start_color=red, end_color=red, fill_type="solid")
    for r in range(2, ws.max_row + 1):
        v = ws.cell(row=r, column=eff_col).value
        try:
            val = float(v) if v is not None and str(v).strip() != "" else None
        except Exception:
            val = None
        if val is None:
            continue
        fill = green_fill if val >= float(target_eff) else red_fill
        for c in range(1, ws.max_column + 1):
            ws.cell(row=r, column=c).fill = fill


def write_block_report(writer, detail_long: pd.DataFrame, user_col: str, target_eff: float):
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter

    sheet_name = "報表_區塊"
    wb = writer.book
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(sheet_name)

    header = ["代碼", "姓名", "筆數", "工作區間", "總分鐘", "效率(件/時)", "休息分鐘", "空窗分鐘", "空窗時段"]
    title_font = Font(bold=True, size=14)
    sec_font = Font(bold=True, size=12)
    header_fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
    border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    df = detail_long.copy()
    df["工作區間"] = df.apply(
        lambda r: (
            ("" if pd.isna(r["第一筆時間"]) else str(r["第一筆時間"].time()))
            + " ~ "
            + ("" if pd.isna(r["最後一筆時間"]) else str(r["最後一筆時間"].time()))
        ),
        axis=1,
    )
    df["總分鐘"] = df["工時_分鐘"].astype(int)

    for dt_date, g in df.groupby("日期"):
        row = ws.max_row + 1
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(header))
        cell = ws.cell(row=row, column=1, value=f"{dt_date} 上架績效")
        cell.font = title_font
        cell.alignment = center

        for seg in ["上午", "下午"]:
            seg_df = g[g["時段"] == seg]
            if seg_df.empty:
                continue

            row = ws.max_row + 1
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=len(header))
            cell = ws.cell(row=row, column=1, value=seg)
            cell.font = sec_font
            cell.alignment = left

            row = ws.max_row + 1
            for c, h in enumerate(header, start=1):
                hc = ws.cell(row=row, column=c, value=h)
                hc.fill = header_fill
                hc.alignment = center
                hc.border = border
                hc.font = Font(bold=True)

            seg_df = seg_df.sort_values(["效率_件每小時", "筆數"], ascending=[False, False])
            for _, r in seg_df.iterrows():
                row = ws.max_row + 1
                values = [
                    r[user_col],
                    r["對應姓名"],
                    int(r["筆數"]),
                    r["工作區間"],
                    int(r["總分鐘"]),
                    float(r["效率_件每小時"]),
                    int(r["休息分鐘"]),
                    int(r["空窗分鐘"]),
                    r["空窗時段"],
                ]
                for c, v in enumerate(values, start=1):
                    cell = ws.cell(row=row, column=c, value=v)
                    cell.alignment = center if c not in (4, 9) else left
                    cell.border = border

                eff = float(r["效率_件每小時"]) if pd.notna(r["效率_件每小時"]) else 0.0
                color = "C6EFCE" if eff >= float(target_eff) else "FFC7CE"
                fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
                for c in range(1, len(header) + 1):
                    ws.cell(row=row, column=c).fill = fill

    for c in range(1, len(header) + 1):
        max_len = 0
        for r in range(1, ws.max_row + 1):
            v = ws.cell(row=r, column=c).value
            max_len = max(max_len, len(str(v)) if v is not None else 0)
        ws.column_dimensions[get_column_letter(c)].width = min(max(max_len + 2, len(str(header[c - 1])) + 2), 60)


def build_excel_bytes(
    user_col: str,
    summary_out: pd.DataFrame,
    daily: pd.DataFrame,
    detail_long: pd.DataFrame,
    target_eff: float,
) -> bytes:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl", datetime_format="yyyy-mm-dd hh:mm:ss", date_format="yyyy-mm-dd") as writer:
        sum_cols = [
            user_col, "對應姓名", "総日數",
            "總筆數", "總工時_分鐘_扣休", "效率_件每小時",
            "上午筆數", "上午工時_分鐘", "上午效率_件每小時",
            "下午筆數", "下午工時_分鐘_扣休", "下午效率_件每小時",
        ]
        summary_out[sum_cols].to_excel(writer, index=False, sheet_name="彙總")
        ws_sum = writer.sheets["彙總"]
        autosize_columns(ws_sum, summary_out[sum_cols])
        shade_rows_by_efficiency(ws_sum, "效率_件每小時", target_eff=target_eff)

        det_cols = [
            user_col, "對應姓名", "日期",
            "第一筆時間", "最後一筆時間", "當日筆數",
            "休息分鐘_整體", "當日工時_分鐘_扣休", "效率_件每小時",
            "上午_第一筆", "上午_最後一筆", "上午_筆數", "上午_工時_分鐘", "上午_效率_件每小時",
            "上午_空窗分鐘", "上午_空窗時段",
            "下午_第一筆", "下午_最後一筆", "下午_筆數", "下午_休息分鐘",
            "下午_工時_分鐘_扣休", "下午_效率_件每小時",
            "下午_空窗分鐘_扣休", "下午_空窗時段",
        ]
        daily.sort_values([user_col, "日期", "第一筆時間"])[det_cols].to_excel(writer, index=False, sheet_name="明細")
        ws_det = writer.sheets["明細"]
        autosize_columns(ws_det, daily[det_cols])
        shade_rows_by_efficiency(ws_det, "效率_件每小時", target_eff=target_eff)

        if detail_long is not None and not detail_long.empty:
            long_cols = [
                user_col, "對應姓名", "日期", "時段",
                "第一筆時間", "最後一筆時間",
                "筆數", "工時_分鐘", "休息分鐘",
                "空窗分鐘", "空窗時段",
                "效率_件每小時", "命中規則",
            ]
            detail_long[long_cols].to_excel(writer, index=False, sheet_name="明細_時段")
            ws_long = writer.sheets["明細_時段"]
            autosize_columns(ws_long, detail_long[long_cols])
            shade_rows_by_efficiency(ws_long, "效率_件每小時", target_eff=target_eff)

        if detail_long is not None and not detail_long.empty:
            write_block_report(writer, detail_long, user_col, target_eff=target_eff)

        rules_rows = []
        for i, (st_ge, ed_le, mins, tag) in enumerate(BREAK_RULES, start=1):
            rules_rows.append({
                "優先序": i,
                "首時間條件(>=)": st_ge.strftime("%H:%M:%S"),
                "末時間條件(<=)": ed_le.strftime("%H:%M:%S"),
                "休息分鐘": int(mins),
                "規則說明": str(tag),
            })
        rules_df = pd.DataFrame(
            rules_rows,
            columns=["優先序", "首時間條件(>=)", "末時間條件(<=)", "休息分鐘", "規則說明"],
        )
        rules_df.to_excel(writer, index=False, sheet_name="休息規則")
        autosize_columns(writer.sheets["休息規則"], rules_df)

    return out.getvalue()


# =========================================================
# Streamlit Page
# =========================================================
def main():
    inject_logistics_theme()
    set_page("上架產能分析（Putaway KPI）", icon="📦", subtitle="總上組（上架）｜上午/下午分段｜效率門檻著色｜報表_區塊輸出")

    if "putaway_last" not in st.session_state:
        st.session_state.putaway_last = None

    controls = sidebar_controls(default_top_n=30, enable_exclude_windows=True, state_key_prefix="putaway")
    top_n = int(controls.get("top_n", 30))

    exclude_raw = _extract_exclude_value_from_controls(controls)
    exclude_idle_ranges = _parse_exclude_windows(exclude_raw)

    with st.sidebar:
        st.markdown("---")
        target_eff = st.number_input("達標門檻（效率 ≥）", min_value=1, max_value=999, value=int(TARGET_EFF_DEFAULT), step=1)
        idle_threshold = st.number_input("空窗門檻（分鐘 ≥ 才算）", min_value=1, max_value=240, value=int(IDLE_MIN_THRESHOLD_DEFAULT), step=1)

        preview = "、".join([f"{a.strftime('%H:%M')}~{b.strftime('%H:%M')}" for a, b in exclude_idle_ranges]) if exclude_idle_ranges else "（無）"
        st.caption(f"✅ 已讀取排除空窗時段：{preview}")
        st.caption("⚠️ 若你改了排除時段/門檻，需再按一次「🚀 產出 KPI」才會重新計算。")
        st.caption("提示：上傳 .xls 需 requirements 安裝 xlrd==2.0.1")

    card_open("📤 上傳作業原始資料（上架）")
    uploaded = st.file_uploader(
        "上傳 Excel / CSV（需包含：由、到、修訂日期/時間、記錄輸入人）",
        type=["xlsx", "xlsm", "xls", "csv"],
        label_visibility="collapsed",
    )
    run_clicked = st.button("🚀 產出 KPI", type="primary", disabled=uploaded is None)
    card_close()

    last = st.session_state.putaway_last
    current_params = {
        "target_eff": int(target_eff),
        "idle_threshold": int(idle_threshold),
        "exclude_idle_ranges": [(a.strftime("%H:%M:%S"), b.strftime("%H:%M:%S")) for a, b in exclude_idle_ranges],
        "top_n": int(top_n),
    }
    if last and last.get("params") and last.get("params") != current_params:
        st.warning("⚠️ 你已變更側邊欄條件（含排除空窗時段/門檻），請再按一次「🚀 產出 KPI」才會套用新條件。")

    if run_clicked:
        with st.spinner("計算中，請稍候..."):
            sheets = read_excel_any_quiet_bytes(uploaded.name, uploaded.getvalue())

            kept_all = []
            for sn, df in sheets.items():
                k = prepare_filtered_df(df)
                if not k.empty:
                    k["__sheet__"] = sn
                    kept_all.append(k)

            if not kept_all:
                st.error("無符合資料（可能缺『由/到』欄或過濾後為空）。")
                st.session_state.putaway_last = None
                return

            data = pd.concat(kept_all, ignore_index=True)

            user_col = find_first_column(data, INPUT_USER_CANDIDATES)
            revdt_col = find_first_column(data, REV_DT_CANDIDATES)
            if user_col is None:
                st.error("找不到『記錄輸入人』欄位（候選：記錄輸入人/記錄輸入者/建立人/輸入人）。")
                st.session_state.putaway_last = None
                return
            if revdt_col is None:
                st.error("找不到『修訂日期/時間』欄位（候選：修訂日期/修訂時間/修訂日/異動時間/修改時間）。")
                st.session_state.putaway_last = None
                return

            data["__dt__"] = pd.to_datetime(data[revdt_col], errors="coerce")
            data["__code__"] = data[user_col].astype(str).str.strip()
            data["對應姓名"] = data["__code__"].map(NAME_MAP).fillna("")

            dt_data = data.dropna(subset=["__dt__"]).copy()
            if dt_data.empty:
                st.error("資料沒有可用的修訂日期時間，無法計算。")
                st.session_state.putaway_last = None
                return

            dt_data["日期"] = dt_data["__dt__"].dt.date

            daily = (
                dt_data.groupby([user_col, "對應姓名", "日期"], dropna=False)
                .apply(lambda g: compute_am_pm_for_group(
                    g,
                    idle_threshold_min=int(idle_threshold),
                    exclude_idle_ranges=exclude_idle_ranges,
                ))
                .reset_index()
            )

            summary = (
                daily.groupby([user_col, "對應姓名"], dropna=False, as_index=False)
                .agg(
                    総日數=("日期", "nunique"),
                    總筆數=("當日筆數", "sum"),
                    上午筆數=("上午_筆數", "sum"),
                    上午工時_分鐘=("上午_工時_分鐘", "sum"),
                    下午筆數=("下午_筆數", "sum"),
                    下午工時_分鐘_扣休=("下午_工時_分鐘_扣休", "sum"),
                )
            )

            summary["上午效率_件每小時"] = summary.apply(lambda r: _eff(int(r["上午筆數"]), int(r["上午工時_分鐘"])), axis=1)
            summary["下午效率_件每小時"] = summary.apply(lambda r: _eff(int(r["下午筆數"]), int(r["下午工時_分鐘_扣休"])), axis=1)

            # ✅ 總工時採「上午+下午」：跟整體（day）一致，避免跨段空檔影響
            summary["總工時_分鐘_扣休"] = summary["上午工時_分鐘"].fillna(0).astype(int) + summary["下午工時_分鐘_扣休"].fillna(0).astype(int)
            summary["效率_件每小時"] = summary.apply(lambda r: _eff(int(r["總筆數"]), int(r["總工時_分鐘_扣休"])), axis=1)

            for c in ["總筆數", "總工時_分鐘_扣休", "上午筆數", "上午工時_分鐘", "下午筆數", "下午工時_分鐘_扣休"]:
                summary[c] = summary[c].fillna(0).astype(int)

            total_people = int(summary[user_col].nunique())
            met_people = int((summary["效率_件每小時"] >= float(target_eff)).sum())
            rate = (met_people / total_people) if total_people > 0 else 0.0

            total_row = {
                user_col: "整體合計",
                "對應姓名": "",
                "総日數": int(summary["総日數"].sum()),
                "總筆數": int(summary["總筆數"].sum()),
                "總工時_分鐘_扣休": int(summary["總工時_分鐘_扣休"].sum()),
                "上午筆數": int(summary["上午筆數"].sum()),
                "上午工時_分鐘": int(summary["上午工時_分鐘"].sum()),
                "下午筆數": int(summary["下午筆數"].sum()),
                "下午工時_分鐘_扣休": int(summary["下午工時_分鐘_扣休"].sum()),
                "效率_件每小時": _eff(int(summary["總筆數"].sum()), int(summary["總工時_分鐘_扣休"].sum())),
                "上午效率_件每小時": _eff(int(summary["上午筆數"].sum()), int(summary["上午工時_分鐘"].sum())),
                "下午效率_件每小時": _eff(int(summary["下午筆數"].sum()), int(summary["下午工時_分鐘_扣休"].sum())),
            }
            summary_out = pd.concat([summary, pd.DataFrame([total_row])], ignore_index=True)

            long_rows = []
            for _, r in daily.iterrows():
                if int(r["上午_筆數"]) > 0:
                    long_rows.append({
                        user_col: r[user_col], "對應姓名": r["對應姓名"], "日期": r["日期"], "時段": "上午",
                        "第一筆時間": r["上午_第一筆"], "最後一筆時間": r["上午_最後一筆"],
                        "筆數": int(r["上午_筆數"]), "工時_分鐘": int(r["上午_工時_分鐘"]),
                        "休息分鐘": 0,
                        "空窗分鐘": int(r["上午_空窗分鐘"]), "空窗時段": r["上午_空窗時段"],
                        "效率_件每小時": float(r["上午_效率_件每小時"]),
                        "命中規則": "上午不扣休",
                    })
                if int(r["下午_筆數"]) > 0:
                    long_rows.append({
                        user_col: r[user_col], "對應姓名": r["對應姓名"], "日期": r["日期"], "時段": "下午",
                        "第一筆時間": r["下午_第一筆"], "最後一筆時間": r["下午_最後一筆"],
                        "筆數": int(r["下午_筆數"]), "工時_分鐘": int(r["下午_工時_分鐘_扣休"]),
                        "休息分鐘": int(r["下午_休息分鐘"]),
                        "空窗分鐘": int(r["下午_空窗分鐘_扣休"]), "空窗時段": r["下午_空窗時段"],
                        "效率_件每小時": float(r["下午_效率_件每小時"]),
                        "命中規則": str(r["下午_命中規則"]),
                    })
            detail_long = pd.DataFrame(long_rows)
            if not detail_long.empty:
                detail_long = detail_long.sort_values([user_col, "日期", "時段", "第一筆時間"])

            xlsx_bytes = build_excel_bytes(user_col, summary_out, daily, detail_long, target_eff=float(target_eff))
            xlsx_name = f"{uploaded.name.rsplit('.', 1)[0]}_上架績效.xlsx"

            st.session_state.putaway_last = {
                "params": current_params,
                "user_col": user_col,
                "summary": summary,
                "summary_out": summary_out,
                "daily": daily,
                "detail_long": detail_long,
                "target_eff": float(target_eff),
                "top_n": int(top_n),
                "total_people": int(total_people),
                "met_people": int(met_people),
                "rate": float(rate),
                "xlsx_bytes": xlsx_bytes,
                "xlsx_name": xlsx_name,
            }

    last = st.session_state.putaway_last
    if not last:
        st.info("請先上傳上架作業原始資料並點選「🚀 產出 KPI」")
        return

    user_col = last["user_col"]
    summary = last["summary"]
    target_eff_show = float(last["target_eff"])
    top_n_show = int(last.get("top_n", 30))
    total_people = int(last["total_people"])
    met_people = int(last["met_people"])
    rate = float(last["rate"])
    xlsx_bytes = last["xlsx_bytes"]
    xlsx_name = last["xlsx_name"]

    card_open("📌 總覽 KPI")
    render_kpis([
        KPI("總人數", f"{total_people:,}"),
        KPI("達標人數", f"{met_people:,}"),
        KPI("達標率", f"{rate:.1%}"),
        KPI("達標門檻", f"效率 ≥ {int(target_eff_show)}"),
    ])
    card_close()

    col_l, col_r = st.columns(2)

    with col_l:
        card_open(f"🌓 AM（上午）效率排行（Top {top_n_show}）")
        am_rank = summary[[user_col, "對應姓名", "上午筆數", "上午工時_分鐘", "上午效率_件每小時"]].copy()
        am_rank = am_rank.rename(columns={"上午效率_件每小時": "效率", "上午筆數": "筆數", "上午工時_分鐘": "工時"})
        am_rank["姓名"] = am_rank["對應姓名"].where(am_rank["對應姓名"].astype(str).str.len() > 0, am_rank[user_col].astype(str))
        bar_topN(
            am_rank[["姓名", "效率", "筆數", "工時"]],
            x_col="姓名",
            y_col="效率",
            hover_cols=["筆數", "工時"],
            top_n=top_n_show,
            target=float(target_eff_show),
        )
        card_close()

    with col_r:
        card_open(f"🌙 PM（下午）效率排行（Top {top_n_show}）")
        pm_rank = summary[[user_col, "對應姓名", "下午筆數", "下午工時_分鐘_扣休", "下午效率_件每小時"]].copy()
        pm_rank = pm_rank.rename(columns={"下午效率_件每小時": "效率", "下午筆數": "筆數", "下午工時_分鐘_扣休": "工時"})
        pm_rank["姓名"] = pm_rank["對應姓名"].where(pm_rank["對應姓名"].astype(str).str.len() > 0, pm_rank[user_col].astype(str))
        bar_topN(
            pm_rank[["姓名", "效率", "筆數", "工時"]],
            x_col="姓名",
            y_col="效率",
            hover_cols=["筆數", "工時"],
            top_n=top_n_show,
            target=float(target_eff_show),
        )
        card_close()

    download_excel_card(
        xlsx_bytes,
        xlsx_name,
        label="⬇️ 匯出 KPI 報表（Excel）",
    )


if __name__ == "__main__":
    main()
