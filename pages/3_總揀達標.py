import io
import datetime as dt
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st

from common_ui import (
    inject_logistics_theme,
    set_page,
    KPI,
    render_kpis,
    card_open,
    card_close,
    sidebar_controls,  # 你現有的手動輸入排除區間（HH:MM）
)

# =========================================================
# 參數（依你合併版）
# =========================================================
MORNING_END = datetime.strptime("12:30:00", "%H:%M:%S").time()
M_REST_START = datetime.strptime("10:00:00", "%H:%M:%S").time()
M_REST_END = datetime.strptime("10:15:00", "%H:%M:%S").time()

AFTERNOON_START = datetime.strptime("13:30:00", "%H:%M:%S").time()
AFTERNOON_END = datetime.strptime("18:00:00", "%H:%M:%S").time()
A_REST_START = datetime.strptime("15:30:00", "%H:%M:%S").time()
A_REST_END = datetime.strptime("15:45:00", "%H:%M:%S").time()

IDLE_THRESHOLD = timedelta(minutes=10)
default_start_time_str = "08:05:00"

# 達標門檻（依你合併版的條件格式）
LOW_TARGET = 48   # 低空
HIGH_TARGET = 20  # 高空


# =========================================================
# 揀貨人預設資料（直接沿用你合併版）
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
    "20201019001": {"姓名": "邱清瑞", "起始時間": "8:05:00", "區域": "低空"},
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
    "20191205002": {"姓名": "阮功水", "起始時間": "8:05:00", "區域": "低空"},
    "20230119001": {"姓名": "陶春青", "起始時間": "7:05:00", "區域": "高空"},
    "20210318001": {"姓名": "陳文勇", "起始時間": "8:05:00", "區域": "低空"},
    "20210805001": {"姓名": "郭中合", "起始時間": "8:05:00", "區域": "低空"},
    "20220421002": {"姓名": "楊文點", "起始時間": "8:05:00", "區域": "低空"},
    "20220505001": {"姓名": "阮伊黃", "起始時間": "8:05:00", "區域": "低空"},
    "20220505002": {"姓名": "阮文青明", "起始時間": "7:05:00", "區域": "高空"},
    "20221222005": {"姓名": "謝忠龍", "起始時間": "8:05:00", "區域": "高空"},
    "20221222009": {"姓名": "潘文一", "起始時間": "8:05:00", "區域": "低空"},
    "20221221001": {"姓名": "阮文全", "起始時間": "7:05:00", "區域": "高空"},
    "20230504001": {"姓名": "黃文重", "起始時間": "8:05:00", "區域": "低空"},
    "20230511003": {"姓名": "范日明", "起始時間": "7:05:00", "區域": "低空"},
    "20230810003": {"姓名": "范明俊", "起始時間": "8:05:00", "區域": "低空"},
    "20231211004": {"姓名": "河文南", "起始時間": "8:05:00", "區域": "低空"},
    "20231218004": {"姓名": "河文強", "起始時間": "8:05:00", "區域": "低空"},
    "20240107001": {"姓名": "范文春", "起始時間": "8:05:00", "區域": "低空"},
    "20240313001": {"姓名": "陳文越", "起始時間": "8:05:00", "區域": "低空"},
    "20240313003": {"姓名": "阮曰忠", "起始時間": "7:05:00", "區域": "高空"},
    "20240730001": {"姓名": "阮文忠", "起始時間": "8:05:00", "區域": "低空"},
    "20241204005": {"姓名": "阮春水", "起始時間": "7:05:00", "區域": "低空"},
    "20241204007": {"姓名": "阮玉名", "起始時間": "8:05:00", "區域": "低空"},
    "20241204009": {"姓名": "阮長文", "起始時間": "7:05:00", "區域": "低空"},
    "20220421001": {"姓名": "阮德平", "起始時間": "8:05:00", "區域": "高空"},
    "20250502001": {"姓名": "吳詩敏", "起始時間": "8:05:00", "區域": "低空"},
    "20250617003": {"姓名": "喬家寶", "起始時間": "8:05:00", "區域": "低空"},
    "20250901011": {"姓名": "章愛玲", "起始時間": "8:35:00", "區域": "低空"},
    "20250617001": {"姓名": "阮文譚", "起始時間": "7:05:00", "區域": "高空"},
    "09963": {"姓名": "黃謙凱", "起始時間": "8:05:00", "區域": "低空"},
    "11399": {"姓名": "陳哲沅", "起始時間": "8:05:00", "區域": "低空"},
}


# =========================================================
# ✅ 支援：揀貨人欄位可輸入【代碼 或 中文姓名】
# =========================================================
name_to_code: Dict[str, str] = {}
for code, info in preset_picker_info.items():
    nm = str(info.get("姓名", "")).strip()
    if nm:
        name_to_code[nm] = code


def resolve_picker_key(picker_raw: str) -> str:
    s = str(picker_raw).strip()
    if s in preset_picker_info:
        return s
    return name_to_code.get(s, s)


def build_display_picker(picker_raw: str, preset: dict) -> str:
    p_raw = str(picker_raw).strip()
    p_key = resolve_picker_key(p_raw)
    code = p_key if p_key in preset_picker_info else p_raw
    cn = str(preset.get("姓名") or p_raw).strip()
    if code == cn:
        return code
    return f"{code} {cn}"


def _get_region(picker_key: str) -> str:
    return preset_picker_info.get(picker_key, {}).get("區域", "低空") or "低空"


def _get_name(picker_key: str, fallback: str) -> str:
    return preset_picker_info.get(picker_key, {}).get("姓名", fallback)


def _get_start_time_str(picker_key: str) -> str:
    return preset_picker_info.get(picker_key, {}).get("起始時間", default_start_time_str)


# =========================================================
# 解析時間（依你合併版）
# =========================================================
def parse_tw_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    s = series.astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    # Excel 浮點序列
    num_mask = s.str.match(r"^\d+(\.\d+)?$")
    if num_mask.any():
        out.loc[num_mask] = pd.to_datetime(
            s[num_mask].astype(float),
            unit="d",
            origin="1899-12-30",
        )

    # 字串解析（含 上午/下午）
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


# =========================================================
# 讀檔/前處理（依你合併版）
# =========================================================
def load_and_combine_uploads(uploaded_files: List) -> pd.DataFrame:
    dfs = []
    for up in uploaded_files:
        ext = up.name.split(".")[-1].lower()
        if ext in ("xlsx", "xlsm"):
            dfs.append(pd.read_excel(io.BytesIO(up.getvalue()), engine="openpyxl", dtype={"揀貨完成時間": str}))
        elif ext == "xls":
            dfs.append(pd.read_excel(io.BytesIO(up.getvalue()), engine="xlrd", dtype={"揀貨完成時間": str}))
        elif ext == "csv":
            # 盡量相容
            for enc in ("utf-8-sig", "cp950", "big5"):
                try:
                    dfs.append(pd.read_csv(io.BytesIO(up.getvalue()), encoding=enc))
                    break
                except Exception:
                    continue
        else:
            raise ValueError(f"不支援的檔案格式：{up.name}")

    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def remove_boxed_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "成箱箱號" not in df.columns:
        return df
    df["成箱箱號"] = df["成箱箱號"].astype(str).str.strip()
    return df[df["成箱箱號"] == ""]


def combine_rows(df: pd.DataFrame) -> pd.DataFrame:
    # 依你合併版：同 儲位/商品/揀貨人/完成時間 合併，數量 sum
    group_cols = ["儲位", "商品", "揀貨人", "揀貨完成時間"]
    if not all(c in df.columns for c in group_cols):
        # 最少要有 揀貨人 / 揀貨完成時間
        must = ["揀貨人", "揀貨完成時間"]
        if not all(c in df.columns for c in must):
            raise KeyError("缺少必要欄位：揀貨人、揀貨完成時間")
        return df.copy()

    if "數量" in df.columns:
        out = df.groupby(group_cols, as_index=False).agg({"數量": "sum"})
    else:
        out = df[group_cols].copy()
    return out


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["揀貨完成時間"] = parse_tw_datetime(df["揀貨完成時間"])
    df = df.dropna(subset=["揀貨完成時間"])
    return df


def normalize_picker_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    新增：
      - 揀貨人_raw：原始值（可能是中文/代碼）
      - 揀貨人_key：統一代碼（能反查就轉代碼）
      - 姓名：中文姓名
      - 區域：低空/高空
      - 揀貨人顯示：代碼 + 中文姓名
    """
    df = df.copy()
    df["揀貨人_raw"] = df["揀貨人"].astype(str).str.strip()
    df["揀貨人_key"] = df["揀貨人_raw"].apply(resolve_picker_key)

    def _name(row):
        return _get_name(row["揀貨人_key"], row["揀貨人_raw"])

    def _region(row):
        return _get_region(row["揀貨人_key"])

    df["姓名"] = df.apply(_name, axis=1)
    df["區域"] = df.apply(_region, axis=1)

    def _disp(row):
        preset = preset_picker_info.get(row["揀貨人_key"], {})
        return build_display_picker(row["揀貨人_raw"], preset)

    df["揀貨人顯示"] = df.apply(_disp, axis=1)
    return df


# =========================================================
# 排除區間（固定休息 + 使用者排除）
# =========================================================
def _adapt_exclude_windows_to_ranges(exclude_windows) -> List[Tuple[dt.time, dt.time]]:
    ranges: List[Tuple[dt.time, dt.time]] = []
    for w in exclude_windows or []:
        try:
            s = pd.to_datetime(w.get("start", "")).time()
            e = pd.to_datetime(w.get("end", "")).time()
        except Exception:
            continue
        if s and e and s != e:
            ranges.append((s, e))
    return ranges


def _ranges_to_dt(date_: dt.date, ranges: List[Tuple[dt.time, dt.time]]) -> List[Tuple[datetime, datetime]]:
    out = []
    for s, e in ranges:
        a = datetime.combine(date_, s)
        b = datetime.combine(date_, e)
        if b > a:
            out.append((a, b))
    return out


def clip_segments(a: datetime, b: datetime, exclude: List[Tuple[datetime, datetime]]) -> List[Tuple[datetime, datetime]]:
    if b <= a:
        return []
    segs = [(a, b)]
    for ex_s, ex_e in exclude:
        new = []
        for x, y in segs:
            if y <= ex_s or x >= ex_e:
                new.append((x, y))
            else:
                if x < ex_s:
                    new.append((x, ex_s))
                if y > ex_e:
                    new.append((ex_e, y))
        segs = [(x, y) for x, y in new if y > x]
    return segs


def sum_minutes(segs: List[Tuple[datetime, datetime]]) -> float:
    return round(sum((y - x).total_seconds() for x, y in segs) / 60.0, 2)


def idle_segments_between(
    a: datetime,
    b: datetime,
    exclude: List[Tuple[datetime, datetime]],
    threshold: timedelta = IDLE_THRESHOLD,
) -> List[Tuple[datetime, datetime]]:
    segs = clip_segments(a, b, exclude)
    out = []
    for x, y in segs:
        if (y - x) >= threshold:
            out.append((x, y))
    return out


def storage_area_str(records: pd.DataFrame) -> str:
    prefixes = []
    if "儲位" not in records.columns:
        return ""
    for loc in records["儲位"].astype(str).tolist():
        pre = str(loc)[:3]
        if pre and pre not in prefixes:
            prefixes.append(pre)
    return ",".join(prefixes)


def pass_threshold(region: str, eff: float) -> bool:
    th = HIGH_TARGET if str(region).strip() == "高空" else LOW_TARGET
    return float(eff) >= float(th)


# =========================================================
# 上午 / 下午 統計（依你合併版邏輯）
# =========================================================
def calc_stats(
    full_df: pd.DataFrame,
    shift: str,
    user_ex_ranges: List[Tuple[dt.time, dt.time]],
) -> pd.DataFrame:
    """
    shift: "AM" or "PM"
    回傳欄位順序同你合併版：
    ['區域','揀貨人','姓名','筆數','工作區間','總分鐘','效率','空窗分鐘','儲位區域','空窗時間段']
    """
    if full_df.empty:
        return pd.DataFrame(columns=[
            "區域", "揀貨人", "姓名", "筆數", "工作區間",
            "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"
        ])

    df = full_df.copy()

    # 班別篩選
    if shift == "AM":
        df = df[df["揀貨完成時間"].dt.time <= MORNING_END].copy()
    else:
        df = df[
            (df["揀貨完成時間"].dt.time >= AFTERNOON_START) &
            (df["揀貨完成時間"].dt.time <= AFTERNOON_END)
        ].copy()

    if df.empty:
        return pd.DataFrame(columns=[
            "區域", "揀貨人", "姓名", "筆數", "工作區間",
            "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"
        ])

    df["日期"] = df["揀貨完成時間"].dt.date

    stats_rows = []

    # ✅ 避免跨日混算：以 日期 + 揀貨人_key 分組（更穩）
    for (date_, picker_key), g in df.groupby(["日期", "揀貨人_key"], dropna=False):
        g = g.sort_values("揀貨完成時間")
        times = list(g["揀貨完成時間"])
        if not times:
            continue

        picker_raw_sample = str(g["揀貨人_raw"].iloc[0])
        preset = preset_picker_info.get(str(picker_key), {})

        region = _get_region(str(picker_key))
        name = _get_name(str(picker_key), picker_raw_sample)
        display_picker = build_display_picker(picker_raw_sample, preset)

        first_record: datetime = times[0].to_pydatetime() if hasattr(times[0], "to_pydatetime") else times[0]
        last_record: datetime = times[-1].to_pydatetime() if hasattr(times[-1], "to_pydatetime") else times[-1]

        # 固定休息 + 使用者排除（同一天）
        if shift == "AM":
            fixed = [(M_REST_START, M_REST_END)]
        else:
            fixed = [(A_REST_START, A_REST_END)]
        exclude_dt = _ranges_to_dt(date_, fixed + user_ex_ranges)

        # 有無跨段（依你合併版：上午若有下午紀錄，上午結尾補到 12:30）
        full_same = full_df[(full_df["日期"] == date_) & (full_df["揀貨人_key"] == picker_key)].copy()
        # 如果你上面 full_df 沒有 日期欄（保險）
        if "日期" not in full_df.columns:
            full_same = full_df[
                (full_df["揀貨完成時間"].dt.date == date_) & (full_df["揀貨人_key"] == picker_key)
            ].copy()

        if shift == "AM":
            try:
                cfg_t = datetime.strptime(_get_start_time_str(str(picker_key)), "%H:%M:%S").time()
            except Exception:
                cfg_t = datetime.strptime(default_start_time_str, "%H:%M:%S").time()

            configured_start = datetime.combine(date_, cfg_t)
            effective_start = min(first_record, configured_start)

            morning_end_dt = datetime.combine(date_, MORNING_END)
            has_afternoon = any(t.time() > MORNING_END for t in full_same["揀貨完成時間"])
            effective_end = morning_end_dt if has_afternoon else min(last_record, morning_end_dt)

        else:
            start_dt = datetime.combine(date_, AFTERNOON_START)
            end_dt = datetime.combine(date_, AFTERNOON_END)

            effective_start = max(first_record, start_dt)

            has_after_end = any(t.time() > AFTERNOON_END for t in full_same["揀貨完成時間"])
            effective_end = end_dt if has_after_end else min(last_record, end_dt)

        if effective_end <= effective_start:
            continue

        # 總分鐘：扣除排除區間
        working_segs = clip_segments(effective_start, effective_end, exclude_dt)
        total_minutes = sum_minutes(working_segs)

        num_records = int(len(g))

        # 空窗：>=10 分鐘，且切掉排除區間
        idle_segs: List[Tuple[datetime, datetime]] = []

        # 開頭
        if first_record > effective_start:
            idle_segs.extend(idle_segments_between(effective_start, first_record, exclude_dt, IDLE_THRESHOLD))

        # 中間
        for i in range(1, len(times)):
            prev = times[i - 1].to_pydatetime() if hasattr(times[i - 1], "to_pydatetime") else times[i - 1]
            cur = times[i].to_pydatetime() if hasattr(times[i], "to_pydatetime") else times[i]
            if cur > prev:
                idle_segs.extend(idle_segments_between(prev, cur, exclude_dt, IDLE_THRESHOLD))

        # 結尾
        if shift == "AM":
            # 依你合併版：只有「有下午紀錄」才補到 12:30
            if "has_afternoon" in locals() and has_afternoon and last_record < datetime.combine(date_, MORNING_END):
                idle_segs.extend(idle_segments_between(last_record, datetime.combine(date_, MORNING_END), exclude_dt, IDLE_THRESHOLD))
        else:
            if last_record < effective_end:
                idle_segs.extend(idle_segments_between(last_record, effective_end, exclude_dt, IDLE_THRESHOLD))

        idle_minutes = round(sum((b - a).total_seconds() for a, b in idle_segs) / 60.0, 2)
        efficiency = round((num_records / total_minutes * 60) if total_minutes else 0, 2)

        time_period_str = f"{effective_start.strftime('%H:%M:%S')} ~ {effective_end.strftime('%H:%M:%S')}"
        idle_segments_str = "; ".join(f"{a.strftime('%H:%M:%S')} ~ {b.strftime('%H:%M:%S')}" for a, b in idle_segs)

        # 儲位區域：取有效區間內紀錄
        working_records = g[
            (g["揀貨完成時間"] >= pd.Timestamp(effective_start)) &
            (g["揀貨完成時間"] <= pd.Timestamp(effective_end))
        ]
        storage_str = storage_area_str(working_records)

        stats_rows.append({
            "區域": region,
            "揀貨人": display_picker,  # ✅ 代碼 + 中文姓名
            "姓名": name,
            "筆數": num_records,
            "工作區間": time_period_str,
            "總分鐘": total_minutes,
            "效率": efficiency,
            "空窗分鐘": idle_minutes,
            "儲位區域": storage_str,
            "空窗時間段": idle_segments_str,
        })

    out = pd.DataFrame(stats_rows)
    if out.empty:
        return out

    out["區域"] = pd.Categorical(out["區域"], categories=["低空", "高空"], ordered=True)
    out = out.sort_values(by=["區域", "揀貨人"]).reset_index(drop=True)

    cols = ["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"]
    return out[cols]


def style_pass_fail(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    # 未達標整列紅
    def row_style(r):
        ok = pass_threshold(r.get("區域", ""), r.get("效率", 0))
        return ["background-color: #FFC7CE" if not ok else "" for _ in r.index]
    return df.style.apply(row_style, axis=1)


# =========================================================
# 匯出（同你合併版：Sheet1 上下分段 + 紅綠底色）
# =========================================================
def build_export_xlsx_bytes(title: str, morning_df: pd.DataFrame, afternoon_df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        sheet_name = "Sheet1"
        workbook = writer.book
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet

        title_fmt = workbook.add_format({
            "align": "center", "valign": "vcenter",
            "font_size": 18, "font_name": "新細明體", "border": 1
        })
        stage_fmt = workbook.add_format({
            "align": "center", "valign": "vcenter",
            "font_size": 16, "font_name": "新細明體", "border": 1
        })
        border_fmt = workbook.add_format({"border": 1})

        fmt_green = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})
        fmt_red = workbook.add_format({"bg_color": "#FFC7CE", "font_color": "#9C0006"})

        cols = ["區域", "揀貨人", "姓名", "筆數", "工作區間", "總分鐘", "效率", "空窗分鐘", "儲位區域", "空窗時間段"]
        max_col = len(cols)

        # 標題 + 第一階段
        worksheet.merge_range(0, 0, 0, max_col - 1, title, title_fmt)
        worksheet.merge_range(1, 0, 1, max_col - 1, "第一階段", stage_fmt)

        # 上午表
        startrow_1 = 2
        mdf = (morning_df[cols].copy() if not morning_df.empty else pd.DataFrame(columns=cols))
        mdf.to_excel(writer, index=False, sheet_name=sheet_name, startrow=startrow_1)

        # 邊框（含表頭/資料）
        for r in range(startrow_1, startrow_1 + 1 + len(mdf)):
            for c in range(0, max_col):
                worksheet.write(r, c, worksheet.table[r][c].value if hasattr(worksheet, "table") else (mdf.columns[c] if r == startrow_1 else mdf.iloc[r - startrow_1 - 1, c] if not mdf.empty else ""), border_fmt)

        # ✅ 正確的條件格式（以第一筆資料列為基準做相對參照）
        if not mdf.empty:
            first_data_row_1 = startrow_1 + 1
            last_data_row_1 = first_data_row_1 + len(mdf) - 1
            excel_row_1 = first_data_row_1 + 1  # 1-based

            # 高空
            worksheet.conditional_format(first_data_row_1, 0, last_data_row_1, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_1}="高空",$G{excel_row_1}>={HIGH_TARGET})',
                "format": fmt_green
            })
            worksheet.conditional_format(first_data_row_1, 0, last_data_row_1, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_1}="高空",$G{excel_row_1}<{HIGH_TARGET})',
                "format": fmt_red
            })
            # 低空
            worksheet.conditional_format(first_data_row_1, 0, last_data_row_1, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_1}="低空",$G{excel_row_1}>={LOW_TARGET})',
                "format": fmt_green
            })
            worksheet.conditional_format(first_data_row_1, 0, last_data_row_1, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_1}="低空",$G{excel_row_1}<{LOW_TARGET})',
                "format": fmt_red
            })
        else:
            last_data_row_1 = startrow_1

        # 第二階段（下午）
        gap = 2
        stage_row_2 = last_data_row_1 + gap + 1
        header_row_2 = stage_row_2 + 1

        worksheet.merge_range(stage_row_2, 0, stage_row_2, max_col - 1, "第二階段", stage_fmt)

        adf = (afternoon_df[cols].copy() if not afternoon_df.empty else pd.DataFrame(columns=cols))
        adf.to_excel(writer, index=False, sheet_name=sheet_name, startrow=header_row_2)

        if not adf.empty:
            first_data_row_2 = header_row_2 + 1
            last_data_row_2 = first_data_row_2 + len(adf) - 1
            excel_row_2 = first_data_row_2 + 1

            worksheet.conditional_format(first_data_row_2, 0, last_data_row_2, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_2}="高空",$G{excel_row_2}>={HIGH_TARGET})',
                "format": fmt_green
            })
            worksheet.conditional_format(first_data_row_2, 0, last_data_row_2, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_2}="高空",$G{excel_row_2}<{HIGH_TARGET})',
                "format": fmt_red
            })
            worksheet.conditional_format(first_data_row_2, 0, last_data_row_2, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_2}="低空",$G{excel_row_2}>={LOW_TARGET})',
                "format": fmt_green
            })
            worksheet.conditional_format(first_data_row_2, 0, last_data_row_2, max_col - 1, {
                "type": "formula",
                "criteria": f'=AND($A{excel_row_2}="低空",$G{excel_row_2}<{LOW_TARGET})',
                "format": fmt_red
            })

        # 欄寬（依你合併版）
        worksheet.set_column(0, 0, 8)    # 區域
        worksheet.set_column(1, 2, 18)   # 揀貨人/姓名
        worksheet.set_column(3, 3, 6)    # 筆數
        worksheet.set_column(4, 4, 20)   # 工作區間
        worksheet.set_column(5, 7, 10)   # 總分鐘/效率/空窗分鐘
        worksheet.set_column(8, 8, 30)   # 儲位區域
        worksheet.set_column(9, 9, 35)   # 空窗時間段

    return output.getvalue()


# =========================================================
# Streamlit Page
# =========================================================
def main():
    inject_logistics_theme()
    set_page("總揀達標", icon="🧺", subtitle="合併版：上午 + 下午同頁｜休息自動扣除｜空窗門檻 10 分鐘｜顯示：代碼 + 中文姓名")

    # ✅ 保留結果：按「匯出」不清空 KPI
    if "pick_result" not in st.session_state:
        st.session_state.pick_result = None

    # Sidebar：TopN + 手動排除區間（你現有的 sidebar_controls）
    controls = sidebar_controls(default_top_n=30, enable_exclude_windows=True, state_key_prefix="pick")
    top_n = int(controls.get("top_n", 30))
    user_ex_ranges = _adapt_exclude_windows_to_ranges(controls.get("exclude_windows", []))

    with st.sidebar:
        st.markdown("---")
        report_title = st.text_input("報表標題", value="總揀達標獎金計算報表（合併版）")
        st.caption(f"達標門檻：低空 ≥ {LOW_TARGET}｜高空 ≥ {HIGH_TARGET}")
        st.caption("固定休息：上午 10:00-10:15｜下午 15:30-15:45")

    # 上傳（支援多檔）
    card_open("📤 上傳總揀原始資料（可多檔合併）")
    uploads = st.file_uploader(
        "上傳 Excel / CSV",
        type=["xlsx", "xls", "xlsm", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    run_clicked = st.button("🚀 產出 KPI", type="primary", disabled=not uploads)
    card_close()

    if run_clicked:
        with st.spinner("計算中，請稍候..."):
            raw = load_and_combine_uploads(uploads)
            raw = remove_boxed_rows(raw)
            full_df = combine_rows(raw)
            full_df = ensure_datetime(full_df)

            # ✅ 先加日期欄，讓上面 calc_stats 可以用
            full_df["日期"] = full_df["揀貨完成時間"].dt.date

            # ✅ 支援中文姓名輸入：normalize
            full_df = normalize_picker_columns(full_df)

            morning_stats = calc_stats(full_df, "AM", user_ex_ranges)
            afternoon_stats = calc_stats(full_df, "PM", user_ex_ranges)

            xlsx_bytes = build_export_xlsx_bytes(
                title=report_title.strip() or "總揀達標獎金計算報表（合併版）",
                morning_df=morning_stats,
                afternoon_df=afternoon_stats,
            )

            st.session_state.pick_result = {
                "morning": morning_stats,
                "afternoon": afternoon_stats,
                "xlsx_bytes": xlsx_bytes,
                "xlsx_name": f"{(report_title.strip() or '總揀達標')}_上午下午同頁.xlsx",
                "top_n": top_n,
            }

    res = st.session_state.pick_result
    if not res:
        st.info("請先上傳資料並點「🚀 產出 KPI」")
        return

    morning_df = res["morning"]
    afternoon_df = res["afternoon"]

    # KPI 區塊
    def kpi_block(title: str, df: pd.DataFrame):
        card_open(title)
        if df is None or df.empty:
            st.info("無資料")
            card_close()
            return

        people = int(df["揀貨人"].nunique()) if "揀貨人" in df.columns else int(len(df))
        total_records = int(df["筆數"].sum()) if "筆數" in df.columns else 0
        total_minutes = float(df["總分鐘"].sum()) if "總分鐘" in df.columns else 0.0
        avg_eff = float(df["效率"].mean()) if "效率" in df.columns else 0.0

        # 達標率（依區域不同門檻）
        met = 0
        for _, r in df.iterrows():
            if pass_threshold(r.get("區域", ""), r.get("效率", 0)):
                met += 1
        rate = (met / people) if people else 0.0

        render_kpis(
            [
                KPI("人數", f"{people:,}"),
                KPI("總筆數", f"{total_records:,}"),
                KPI("總分鐘", f"{total_minutes:.2f}"),
                KPI("平均效率", f"{avg_eff:.2f}"),
                KPI("達標率", f"{rate:.0%}"),
            ],
            cols=5,
        )
        card_close()

    c1, c2 = st.columns(2)
    with c1:
        kpi_block("🌓 上午達標 KPI", morning_df)
    with c2:
        kpi_block("🌙 下午達標 KPI", afternoon_df)

    # 明細 + TopN
    tab1, tab2 = st.tabs(["上午明細", "下午明細"])

    def show_detail(df: pd.DataFrame):
        if df is None or df.empty:
            st.info("無資料")
            return

        # TopN（依效率）
        topn = df.sort_values("效率", ascending=False).head(int(res["top_n"])).copy()
        with st.expander(f"效率排行（Top {int(res['top_n'])}）", expanded=False):
            st.dataframe(style_pass_fail(topn), use_container_width=True, hide_index=True)

        # 全明細（未達標紅）
        st.dataframe(style_pass_fail(df), use_container_width=True, hide_index=True)

    with tab1:
        show_detail(morning_df)

    with tab2:
        show_detail(afternoon_df)

    # ✅ 匯出：只顯示「按鈕」，按下不會讓 KPI 消失（session_state 保留）
    st.markdown("---")
    st.download_button(
        label="⬇️ 匯出報表（上午+下午同頁）",
        data=res["xlsx_bytes"],
        file_name=res["xlsx_name"],
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


if __name__ == "__main__":
    main()
