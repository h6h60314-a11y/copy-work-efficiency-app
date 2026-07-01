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
    download_excel_card,
    sidebar_controls,
)
# =========================================================
# 參數
# =========================================================
TO_EXCLUDE_KEYWORDS = ["CGS", "JCPL", "QC99", "GREAT0001X", "GX010", "PD99"]
TO_EXCLUDE_PATTERN = re.compile("|".join(re.escape(k) for k in TO_EXCLUDE_KEYWORDS), flags=re.IGNORECASE)
INPUT_USER_CANDIDATES = ["記錄輸入人", "記錄輸入者", "建立人", "輸入人"]
REV_DT_CANDIDATES = ["修訂日期", "修訂時間", "修訂日", "異動時間", "修改時間"]
TARGET_EFF_DEFAULTS = {
    "低空": 13,
    "高空": 8,
}
IDLE_MIN_THRESHOLD_DEFAULT = 10
AM_START, AM_END = dt.time(7, 0, 0), dt.time(12, 30, 0)
PM_START, PM_END = dt.time(13, 30, 0), dt.time(23, 59, 59)
# ✅ 儲位類型（區碼3 → 類型）
STORAGE_TYPE_ZONES = {
    "低空": [
        "001", "002", "003", "017", "016",
        "014", "018", "019", "020", "010", "081", "401", "402", "403", "015",
        "011", "012", "013", "031", "032", "033", "034", "035", "036", "037", "038",
    ],
    "高空": [
        "021", "022", "023",
        "041", "042", "043",
        "051", "052", "053", "054", "055", "056", "057",
        "301", "302", "303", "304", "305", "306",
    ],
}
ZONE3_TO_STORAGE_TYPE = {z: t for t, zones in STORAGE_TYPE_ZONES.items() for z in zones}
# ✅ 既有代碼→姓名（仍保留）
NAME_MAP = {
    "20200924001": "黃雅君", "20210805001": "郭中合", "20220505002": "阮文青明",
    "20221221001": "阮文全", "20221222005": "謝忠龍", "20230119001": "陶春青",
    "20240926001": "陳莉娜", "20241011002": "林雙慧", "20250502001": "吳詩敏",
    "20250617001": "阮文譚", "20250617003": "喬家寶", "20250901009": "張寶萱",
    "G01": "0", "20201109003": "吳振凱", "09963": "黃謙凱",
    "20240313003": "阮曰忠", "20201109001": "梁冠如", "10003": "李茂銓",
    "20200922002": "葉欲弘", "20250923019": "阮氏紅深", "9963": "黃謙凱",
    "11399": "陳哲沅","12432":"徐敏芳","20250303002":"周映華",
}
FIXED_REST_INTERVALS = [
    (dt.time(10, 0, 0), dt.time(10, 15, 0), 15, "10:00-10:15"),
    (dt.time(12, 30, 0), dt.time(13, 30, 0), 60, "12:30-13:30"),
    (dt.time(13, 30, 0), dt.time(13, 45, 0), 15, "13:30-13:45"),
    (dt.time(15, 30, 0), dt.time(15, 45, 0), 15, "15:30-15:45"),
    (dt.time(18, 0, 0), dt.time(18, 30, 0), 30, "18:00-18:30"),
    (dt.time(20, 30, 0), dt.time(20, 45, 0), 15, "20:30-20:45"),
    (dt.time(22, 30, 0), dt.time(22, 45, 0), 15, "22:30-22:45"),
]
# ✅ 預設排除空窗時段（可被 sidebar 覆蓋）
EXCLUDE_IDLE_RANGES_DEFAULT = [
    (dt.time(10, 0, 0), dt.time(10, 15, 0)),
    (dt.time(12, 30, 0), dt.time(13, 30, 0)),
    (dt.time(13, 30, 0), dt.time(13, 45, 0)),
    (dt.time(15, 30, 0), dt.time(15, 45, 0)),
    (dt.time(18, 0, 0), dt.time(18, 30, 0)),
    (dt.time(20, 30, 0), dt.time(20, 45, 0)),
    (dt.time(22, 30, 0), dt.time(22, 45, 0)),
]
# =========================================================
# 通用 helpers
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
def _extract_zone3(s: Any) -> str:
    """從字串抓第一個 3 碼數字（001/014/301...）"""
    if s is None:
        return ""
    txt = str(s).strip()
    if not txt:
        return ""
    m = re.search(r"(\d{3})", txt)
    return m.group(1) if m else ""
def _map_storage_type(zone3: str) -> str:
    return ZONE3_TO_STORAGE_TYPE.get(str(zone3).strip(), "")
# =========================================================
# 上架人設定（session_state）
# =========================================================
PUTAWAY_PEOPLE_STATE_KEY = "putaway_people_settings"  # code -> {name, area}
def _get_putaway_people_settings() -> Dict[str, Dict[str, str]]:
    if PUTAWAY_PEOPLE_STATE_KEY not in st.session_state:
        st.session_state[PUTAWAY_PEOPLE_STATE_KEY] = {}
    return st.session_state[PUTAWAY_PEOPLE_STATE_KEY]
def _normalize_code(x: Any) -> str:
    return str(x).strip()
def render_putaway_people_settings_panel():
    settings = _get_putaway_people_settings()
    with st.sidebar.expander("📦 上架人設定（可中文姓名）", expanded=False):
        code = st.text_input("上架人代碼（可貼上）", key="putaway_person_code")
        name = st.text_input("姓名（中文可輸入）", key="putaway_person_name")
        area = st.selectbox("區域", ["低空", "高空"], index=0, key="putaway_person_area")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("➕ 新增 / 更新", key="putaway_person_upsert"):
                c = _normalize_code(code)
                if not c:
                    st.error("請先輸入上架人代碼")
                else:
                    settings[c] = {"name": str(name).strip(), "area": str(area).strip()}
                    st.success(f"已更新：{c}")
        with c2:
            del_code = st.selectbox("刪除代碼", [""] + sorted(list(settings.keys())), key="putaway_person_del_code")
            if st.button("🗑️ 刪除", key="putaway_person_delete", disabled=(del_code == "")):
                settings.pop(del_code, None)
                st.success(f"已刪除：{del_code}")
        if settings:
            df = pd.DataFrame(
                [{"代碼": k, "姓名": v.get("name", ""), "區域": v.get("area", "")} for k, v in settings.items()]
            ).sort_values(["區域", "代碼"], ascending=[True, True])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.caption("（尚未設定）")
# =========================================================
# sidebar_controls 排除區間解析
# =========================================================
def _parse_exclude_windows(val: Any) -> List[Tuple[dt.time, dt.time]]:
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
