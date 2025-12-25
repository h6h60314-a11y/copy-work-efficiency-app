# pages/18_各類儲區使用率.py
# -*- coding: utf-8 -*-
"""
18_儲位使用率（部署版 / Streamlit）
整合兩支 Tkinter 程式：
A) 依「區(溫層)」統計：大/中/小儲位 有效貨位、已使用貨位、使用率
B) 依「棚別」分類：大型/中型/小型/未知，並輸出：明細(含分類)、棚別統計、儲位類型統計
"""

import warnings
warnings.filterwarnings("ignore")

import io
import os
import re
from datetime import datetime

import pandas as pd
import streamlit as st

# ---- 套用平台風格（有就用，沒有就退回原生） ----
try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close
    HAS_COMMON_UI = True
except Exception:
    HAS_COMMON_UI = False


# =========================
# ✅ 你的分區清單（原封不動整合）
# =========================
LARGE_ZONES = [
    '010','018','019','020','021','022','023','041',
    '042','043','051','052','053','054','055','056',
    '057','301','302','303','304','305','306','311',
    '312','313','314','081','401','402','061','014',
    '057','058','059','403','015'
]
MID_ZONES = ['011','012','013','031','032','033','034','035','036','037','038']
SMALL_ZONES = ['001','002','003','017','016']

LARGE = set(LARGE_ZONES)
MID   = set(MID_ZONES)
SMALL = set(SMALL_ZONES)


# =========================
# 工具：欄位偵測 / 轉區碼 / 讀檔
# =========================
def _spacer(h=10):
    st.markdown(f"<div style='height:{h}px'></div>", unsafe_allow_html=True)


def detect_sheet_for_column(xls: pd.ExcelFile, must_have: str) -> str:
    """在所有分頁中找第一個含 must_have 欄位的分頁；找不到就回第一張"""
    for name in xls.sheet_names:
        try:
            df0 = pd.read_excel(xls, sheet_name=name, nrows=0)
            if must_have in df0.columns:
                return name
        except Exception:
            continue
    return xls.sheet_names[0]


def robust_read_excel_bytes(uploaded_file) -> tuple[pd.DataFrame, str]:
    """
    上傳檔案讀取：
    - xlsx/xlsm: openpyxl
    - xls: xlrd（需 requirements 裝 xlrd==2.0.1）
    會自動選擇最適合的分頁：
      優先：含『區(溫層)』；其次：含『棚別』；再不行：第一張
    """
    filename = uploaded_file.name
    ext = os.path.splitext(filename)[1].lower()
    data = uploaded_file.getvalue()
    bio = io.BytesIO(data)

    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        engine = "openpyxl"
    elif ext == ".xls":
        engine = "xlrd"
    else:
        raise ValueError(f"不支援的檔案格式：{ext}")

    xls = pd.ExcelFile(bio, engine=engine)

    # 分頁策略：先找 區(溫層)，找不到再找 棚別
    sheet = None
    for key in ["區(溫層)", "棚別"]:
        candidate = detect_sheet_for_column(xls, key)
        # 若 candidate 的確含 key，再用它
        try:
            cols = pd.read_excel(xls, sheet_name=candidate, nrows=0).columns
            if key in cols:
                sheet = candidate
                break
        except Exception:
            pass

    if sheet is None:
        sheet = xls.sheet_names[0]

    df = pd.read_excel(xls, sheet_name=sheet)
    return df, sheet


def _to_zone3(x) -> str:
    """從『棚別』抓 3 碼區碼（010/011/001），找不到就回空字串"""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    m = re.search(r"\d{3}", s)
    if m:
        return m.group(0)
    s = re.sub(r"\D", "", s)
    return s.zfill(3) if s else ""


def classify_zone_from棚別(x) -> str:
    """回傳：大型儲位/中型儲位/小型儲位/未知"""
    z = _to_zone3(x)
    if not z:
        return "未知"
    if z in LARGE:
        return "大型儲位"
    if z in MID:
        return "中型儲位"
    if z in SMALL:
        return "小型儲位"
    return "未知"


def _safe_sum(s: pd.Series) -> float:
    return pd.to_numeric(s, errors="coerce").fillna(0).sum()


def calc_util_by_zone(df: pd.DataFrame) -> pd.DataFrame:
    """
    依『區(溫層)』『有效貨位』『已使用貨位』計算大/中/小
    回傳 DataFrame: 類型/有效貨位/已使用貨位/使用率
    """
    if "區(溫層)" not in df.columns:
        return pd.DataFrame()

    # 區碼轉三碼
    z = df["區(溫層)"].astype(str).str.strip()
    z = z.replace({"nan": "", "None": "", "": ""})
    z = z.str.zfill(3)
    df2 = df.copy()
    df2["區碼3"] = z

    need_cols = ["有效貨位", "已使用貨位"]
    for c in need_cols:
        if c not in df2.columns:
            # 不存在就補 0
            df2[c] = 0

    def _row(kind, zones):
        part = df2[df2["區碼3"].isin(zones)]
        eff = _safe_sum(part["有效貨位"])
        used = _safe_sum(part["已使用貨位"])
        rate = (used / eff * 100.0) if eff else 0.0
        return {"儲位類型": kind, "有效貨位": eff, "已使用貨位": used, "使用率(%)": round(rate, 2)}

    out = [
        _row("大儲位", LARGE),
        _row("中儲位", MID),
        _row("小儲位", SMALL),
    ]
    # 總計
    eff_total = sum(r["有效貨位"] for r in out)
    used_total = sum(r["已使用貨位"] for r in out)
    out.append({
        "儲位類型": "總計",
        "有效貨位": eff_total,
        "已使用貨位": used_total,
        "使用率(%)": round((used_total / eff_total * 100.0) if eff_total else 0.0, 2)
    })
    return pd.DataFrame(out)


def build_output_excel_bytes(
    base_name: str,
    df_detail: pd.DataFrame,
    df_util: pd.DataFrame,
    df_shelf: pd.DataFrame,
    df_type: pd.DataFrame,
) -> tuple[str, bytes]:
    """輸出 Excel bytes：使用率 + 明細(含分類) + 棚別統計 + 儲位類型統計"""
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        if not df_util.empty:
            df_util.to_excel(writer, sheet_name="儲位使用率", index=False)
        df_detail.to_excel(writer, sheet_name="明細(含分類)", index=False)
        df_shelf.to_excel(writer, sheet_name="棚別統計", index=False)
        df_type.to_excel(writer, sheet_name="儲位類型統計", index=False)

    out.seek(0)
    filename = f"{base_name}_18_儲位使用率_輸出.xlsx"
    return filename, out.getvalue()


# =========================
# UI
# =========================
st.set_page_config(page_title="儲位使用率", page_icon="🧊", layout="wide")

if HAS_COMMON_UI:
    inject_logistics_theme()
    set_page("儲位使用率", icon="🧊", subtitle="大/中/小儲位｜使用率｜棚別統計｜Excel匯出")
else:
    st.title("🧊 儲位使用率")

st.markdown("上傳 Excel 後，自動統計：大/中/小儲位使用率，並依棚別分類統計。")
_spacer(8)

if HAS_COMMON_UI:
    card_open("📤 上傳檔案")
uploaded = st.file_uploader("請上傳 Excel（.xlsx / .xls / .xlsm）", type=["xlsx", "xls", "xlsm"])
if HAS_COMMON_UI:
    card_close()

_spacer(10)

if not uploaded:
    st.info("請先上傳檔案。")
    st.stop()

# 讀檔
try:
    df, sheet_used = robust_read_excel_bytes(uploaded)
except Exception as e:
    st.error(f"讀取失敗：{e}")
    st.stop()

st.caption(f"使用分頁：{sheet_used}")

# =========================
# A) 使用率（區(溫層)）
# =========================
df_util = calc_util_by_zone(df)

# =========================
# B) 棚別分類 + 統計
# =========================
df_detail = df.copy()
if "棚別" in df_detail.columns:
    df_detail["儲位類型"] = df_detail["棚別"].apply(classify_zone_from棚別)
else:
    df_detail["儲位類型"] = "未知"

# 棚別統計
if "棚別" in df_detail.columns:
    df_shelf = (
        df_detail.groupby(["棚別"], dropna=False)
        .size()
        .reset_index(name="筆數")
        .sort_values(["筆數", "棚別"], ascending=[False, True])
    )
else:
    df_shelf = pd.DataFrame([{"棚別": "（無棚別欄位）", "筆數": len(df_detail)}])

# 儲位類型統計
df_type = (
    df_detail.groupby(["儲位類型"], dropna=False)
    .size()
    .reset_index(name="筆數")
    .sort_values(["筆數", "儲位類型"], ascending=[False, True])
)

_spacer(12)

# =========================
# 顯示區塊：左右兩欄（直向）
# =========================
left, right = st.columns([1, 1], gap="large")

with left:
    if HAS_COMMON_UI:
        card_open("📊 大/中/小儲位使用率")
    else:
        st.subheader("📊 大/中/小儲位使用率")

    if df_util.empty:
        st.warning("此檔案沒有『區(溫層)』欄位，無法計算使用率。")
    else:
        # 直向呈現：大、中、小、總計
        util_map = {r["儲位類型"]: r for _, r in df_util.iterrows()}
        for k in ["大儲位", "中儲位", "小儲位", "總計"]:
            r = util_map.get(k, {"有效貨位": 0, "已使用貨位": 0, "使用率(%)": 0})
            st.metric(f"{k}｜使用率(%)", f"{float(r['使用率(%)']):.2f}")
            st.caption(f"有效貨位：{int(r['有效貨位'])}｜已使用貨位：{int(r['已使用貨位'])}")

    if HAS_COMMON_UI:
        card_close()

with right:
    if HAS_COMMON_UI:
        card_open("🏷️ 儲位類型統計（依棚別分類）")
    else:
        st.subheader("🏷️ 儲位類型統計（依棚別分類）")

    # 直向呈現：大型/中型/小型/未知
    type_map = {r["儲位類型"]: int(r["筆數"]) for _, r in df_type.iterrows()}
    for k in ["大型儲位", "中型儲位", "小型儲位", "未知"]:
        st.metric(k, f"{type_map.get(k, 0):,} 筆")

    if HAS_COMMON_UI:
        card_close()

_spacer(12)

# 棚別統計（表格）
if HAS_COMMON_UI:
    card_open("📋 棚別統計（Top 50）")
st.dataframe(df_shelf.head(50), use_container_width=True, hide_index=True)
if HAS_COMMON_UI:
    card_close()

_spacer(10)

# 下載
base = os.path.splitext(uploaded.name)[0]
download_name, excel_bytes = build_output_excel_bytes(
    base_name=base,
    df_detail=df_detail,
    df_util=df_util if not df_util.empty else pd.DataFrame([{"儲位類型": "（無區(溫層)欄位）"}]),
    df_shelf=df_shelf,
    df_type=df_type,
)

st.download_button(
    "⬇️ 下載 Excel（儲位使用率＋棚別統計）",
    data=excel_bytes,
    file_name=download_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
