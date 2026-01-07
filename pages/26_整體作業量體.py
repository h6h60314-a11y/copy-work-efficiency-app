# pages/26_整體作業量體.py
# -*- coding: utf-8 -*-
from __future__ import annotations

from io import BytesIO, StringIO
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

from common_ui import (
    inject_logistics_theme,
    set_page,
    KPI,
    render_kpis,
    card_open,
    card_close,
    download_excel_card,
)

st.set_page_config(page_title="大豐KPI｜整體作業量體", page_icon="🧹", layout="wide")
inject_logistics_theme()

set_page(
    "整體作業量體",
    icon="🧹",
    subtitle="支援 Excel/TXT｜可多檔上傳｜自動偵測TXT編碼（解決中文亂碼）｜GM/一般倉 × 成箱/零散統計｜Excel下載",
)

NEED_COLS = ["packqty", "入數", "箱類型", "載具號", "BOXTYPE", "boxid"]
CANDIDATE_SEPS = ["\t", ",", "|", ";"]


def _safe_str(s: pd.Series) -> pd.Series:
    return s.astype(str).fillna("").astype(str)


def _fmt_int(x) -> str:
    try:
        return f"{int(round(float(x))):,}"
    except Exception:
        return "0"


def _fmt0(x) -> str:
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


# ----------------------------
# ✅ Encoding detection (fix garbled Chinese)
# ----------------------------
def _has_utf16_nulls(raw: bytes) -> bool:
    if len(raw) < 200:
        return raw.count(b"\x00") > 0
    head = raw[:2000]
    return head.count(b"\x00") / max(1, len(head)) > 0.08  # 有明顯 NUL 很像 UTF-16


def _bom_encoding(raw: bytes) -> str | None:
    if raw.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return "utf-16"
    return None


def _score_text(text: str) -> int:
    # 分數越高越像「正常中文表格」
    # 1) 亂碼替代符越少越好
    repl = text.count("\ufffd")
    # 2) 控制字元越少越好
    ctrl = sum(1 for ch in text if ord(ch) < 32 and ch not in ("\n", "\r", "\t"))
    # 3) 中文越多越好（只加分，不會害英文檔案變差太多）
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    # 4) 第一行表頭可讀性：可用分隔符數量略加分
    lines = [ln for ln in text.splitlines() if ln.strip()]
    first = lines[0] if lines else ""
    sep_bonus = max(first.count("\t"), first.count(","), first.count("|"), first.count(";"))

    # 這組權重足夠把「中文亂碼」跟「中文正常」分出來
    return (cjk * 2) + sep_bonus * 3 - repl * 25 - ctrl * 10


def detect_best_encoding(raw: bytes) -> tuple[str, str]:
    """
    回傳 (best_encoding, preview_text_head)
    """
    bom = _bom_encoding(raw)
    if bom:
        text = raw.decode(bom, errors="replace")
        return bom, text[:4000]

    # UTF-16 特徵：大量 NUL
    if _has_utf16_nulls(raw):
        for enc in ("utf-16", "utf-16le", "utf-16be"):
            try:
                text = raw.decode(enc, errors="replace")
                return enc, text[:4000]
            except Exception:
                pass

    # 候選：台灣常見 cp950/big5 + 可能 gb18030（簡中/混碼）+ utf-8
    candidates = [
        "utf-8-sig",
        "utf-8",
        "cp950",
        "big5",
        "gb18030",
        "cp936",
        "utf-16",
        "utf-16le",
        "utf-16be",
    ]

    best_enc = "utf-8"
    best_score = -10**18
    best_text = ""
    head = raw[:400_000]  # 只拿前面一段來打分（夠判斷表頭/中文）

    for enc in candidates:
        try:
            txt = head.decode(enc, errors="replace")
        except Exception:
            continue
        sc = _score_text(txt)
        if sc > best_score:
            best_score = sc
            best_enc = enc
            best_text = txt

    return best_enc, best_text[:4000]


def _detect_sep(text: str) -> str | None:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[0]
    best = None
    best_cnt = 0
    for sep in CANDIDATE_SEPS:
        cnt = first.count(sep)
        if cnt > best_cnt:
            best_cnt = cnt
            best = sep
    return best if best_cnt > 0 else None


def _read_txt_as_df(text: str, mode: str) -> pd.DataFrame:
    """
    mode:
      auto / sep:\t / sep:, / sep:| / sep:; / ws / fwf
    """
    if mode.startswith("sep:"):
        sep = mode.split(":", 1)[1]
        return pd.read_csv(StringIO(text), sep=sep, dtype=str, engine="python")

    if mode == "ws":
        return pd.read_csv(StringIO(text), sep=r"\s+", dtype=str, engine="python")

    if mode == "fwf":
        return pd.read_fwf(StringIO(text), dtype=str)

    # auto
    sep = _detect_sep(text)
    if sep is not None:
        return pd.read_csv(StringIO(text), sep=sep, dtype=str, engine="python")

    # fallback: ws -> fwf
    try:
        df_ws = pd.read_csv(StringIO(text), sep=r"\s+", dtype=str, engine="python")
        if df_ws.shape[1] >= 2:
            return df_ws
    except Exception:
        pass
    return pd.read_fwf(StringIO(text), dtype=str)


def read_txt_bytes(raw: bytes, parse_mode: str, encoding_choice: str) -> tuple[pd.DataFrame, str]:
    """
    回傳 (df, used_encoding)
    - encoding_choice: "自動(偵測)" or explicit encoding string
    """
    if encoding_choice == "自動(偵測)":
        used_enc, _ = detect_best_encoding(raw)
    else:
        used_enc = encoding_choice

    text = raw.decode(used_enc, errors="replace")
    df = _read_txt_as_df(text, parse_mode)
    return df, used_enc


def robust_read_file(uploaded_file, txt_parse_choice: str, txt_encoding_choice: str) -> tuple[pd.DataFrame, str | None]:
    name = (uploaded_file.name or "").lower()
    raw = uploaded_file.getvalue()

    parse_map = {
        "自動": "auto",
        "Tab": "sep:\t",
        "逗號 ,": "sep:,",
        "直線 |": "sep:|",
        "分號 ;": "sep:;",
        "多空白(對齊)": "ws",
        "固定寬度(FWF)": "fwf",
    }
    parse_mode = parse_map.get(txt_parse_choice, "auto")

    if name.endswith(".txt") or name.endswith(".csv"):
        df, used_enc = read_txt_bytes(raw, parse_mode=parse_mode, encoding_choice=txt_encoding_choice)
        return df, used_enc

    bio = BytesIO(raw)
    try:
        return pd.read_excel(bio, engine="openpyxl"), None
    except Exception:
        bio.seek(0)
        return pd.read_excel(bio, engine="xlrd"), None


# ----------------------------
# mapping helpers (optional)
# ----------------------------
def apply_column_mapping(df: pd.DataFrame, map_in: str | None, map_box: str | None, map_vehicle: str | None) -> pd.DataFrame:
    df = _normalize_columns(df)
    rename = {}
    if "入數" not in df.columns and map_in and map_in in df.columns:
        rename[map_in] = "入數"
    if "箱類型" not in df.columns and map_box and map_box in df.columns:
        rename[map_box] = "箱類型"
    if "載具號" not in df.columns and map_vehicle and map_vehicle in df.columns:
        rename[map_vehicle] = "載具號"
    return df.rename(columns=rename) if rename else df


def compute(df_raw: pd.DataFrame) -> dict:
    df_raw = _normalize_columns(df_raw)

    missing = [c for c in NEED_COLS if c not in df_raw.columns]
    if missing:
        raise KeyError(
            f"⚠️ 找不到必要欄位：{missing}\n"
            f"目前讀到的欄位（前30）：{list(df_raw.columns)[:30]}{' ...' if len(df_raw.columns)>30 else ''}"
        )

    df0 = df_raw.copy()

    before = len(df0)
    df = df0[~_safe_str(df0["箱類型"]).str.contains("站所", na=False)].copy()
    removed_station = before - len(df)

    pack = pd.to_numeric(df["packqty"], errors="coerce")
    unit = pd.to_numeric(df["入數"], errors="coerce")

    df["計量單位數量"] = np.where((unit.notna()) & (unit != 0), pack / unit, np.nan)

    v = pd.to_numeric(df["計量單位數量"], errors="coerce")
    is_int = np.isfinite(v) & np.isclose(v, np.round(v))
    df["出貨單位（判斷後）"] = np.where(is_int, v, pack)

    cols = list(df.columns)
    for c in ["計量單位數量", "出貨單位（判斷後）"]:
        if c in cols:
            cols.remove(c)
    ins_pos = cols.index("入數") + 1
    cols[ins_pos:ins_pos] = ["計量單位數量", "出貨單位（判斷後）"]
    df = df[cols]

    mask_gm = _safe_str(df["載具號"]).str.contains("GM", case=False, na=False)
    boxtype = _safe_str(df["BOXTYPE"]).str.strip()
    mask_box1 = boxtype == "1"
    mask_box0 = boxtype == "0"
    mask_not_gm = ~mask_gm

    unique_boxid_count = (
        df.loc[mask_gm & mask_box1, "boxid"]
        .astype(str).str.strip().replace("", np.nan).dropna().nunique()
    )

    ship_unit = pd.to_numeric(df["出貨單位（判斷後）"], errors="coerce")
    total_shipunit_notgm_box0 = ship_unit.loc[mask_not_gm & mask_box0].sum()
    total_shipunit_gm_box1 = ship_unit.loc[mask_gm & mask_box1].sum()
    total_shipunit_notgm_box1 = ship_unit.loc[mask_not_gm & mask_box1].sum()

    return {
        "df_processed": df,
        "removed_station": int(removed_station),
        "total_in": int(len(df_raw)),
        "total_after": int(len(df)),
        "A_gm_cases": float(unique_boxid_count),
        "B_notgm_loose_pcs": float(total_shipunit_notgm_box0),
        "C_gm_box_pcs": float(total_shipunit_gm_box1),
        "D_notgm_box_pcs": float(total_shipunit_notgm_box1),
    }


def make_excel_bytes(summary_all: pd.DataFrame, detail_all: pd.DataFrame) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        summary_all.to_excel(writer, index=False, sheet_name="統計總表")
        detail_all.to_excel(writer, index=False, sheet_name="合併明細")
    return bio.getvalue()


# ----------------------------
# UI
# ----------------------------
card_open("📥 上傳明細（Excel / TXT，可多檔）")
colA, colB = st.columns(2)
with colA:
    txt_parse_choice = st.selectbox(
        "TXT 分欄方式",
        ["自動", "Tab", "逗號 ,", "直線 |", "分號 ;", "多空白(對齊)", "固定寬度(FWF)"],
        index=0,
    )
with colB:
    txt_encoding_choice = st.selectbox(
        "TXT 編碼",
        ["自動(偵測)", "cp950", "big5", "utf-8-sig", "utf-8", "gb18030", "cp936", "utf-16", "utf-16le", "utf-16be"],
        index=0,
    )

uploaded_files = st.file_uploader(
    "請上傳要處理的檔案（.xlsx / .xls / .txt）",
    type=["xlsx", "xls", "xlsm", "txt", "csv"],
    accept_multiple_files=True,
)
card_close()

if not uploaded_files:
    st.info("請先上傳檔案（可多選）。")
    st.stop()

# 先用第一個檔做 preview（顯示偵測到的編碼）
try:
    df_preview, used_enc_preview = robust_read_file(uploaded_files[0], txt_parse_choice, txt_encoding_choice)
    df_preview = _normalize_columns(df_preview)
except Exception as e:
    st.error(f"第一個檔案讀取失敗：{e}")
    st.stop()

if used_enc_preview:
    st.caption(f"第一個 TXT 偵測/使用的編碼：**{used_enc_preview}**（若中文仍亂碼，請改 TXT 編碼再試）")

# 欄位對照（必要時才用）
cols = list(df_preview.columns)
opt = ["（自動）"] + cols

with st.expander("🧩 欄位對照（若 TXT 中文欄名仍亂碼，請手動指定）", expanded=False):
    col1, col2, col3 = st.columns(3)
    with col1:
        map_in = st.selectbox("入數 欄位", opt, index=0)
    with col2:
        map_box = st.selectbox("箱類型 欄位", opt, index=0)
    with col3:
        map_vehicle = st.selectbox("載具號 欄位（用來判斷 GM）", opt, index=0)

map_in = None if map_in == "（自動）" else map_in
map_box = None if map_box == "（自動）" else map_box
map_vehicle = None if map_vehicle == "（自動）" else map_vehicle

results = []
details = []
errors = []

with st.spinner("處理中…"):
    for f in uploaded_files:
        fname = f.name
        try:
            df_raw, used_enc = robust_read_file(f, txt_parse_choice, txt_encoding_choice)
            df_raw = apply_column_mapping(df_raw, map_in=map_in, map_box=map_box, map_vehicle=map_vehicle)
            out = compute(df_raw)

            results.append(
                {
                    "檔名": fname,
                    "TXT編碼": used_enc or "",
                    "讀取列數": out["total_in"],
                    "刪除站所列數": out["removed_station"],
                    "處理後列數": out["total_after"],
                    "A) GM件數": out["A_gm_cases"],
                    "B) 一般倉零散PCS": out["B_notgm_loose_pcs"],
                    "C) GM成箱PCS": out["C_gm_box_pcs"],
                    "D) 一般倉成箱PCS": out["D_notgm_box_pcs"],
                }
            )

            df_p = out["df_processed"].copy()
            df_p.insert(0, "來源檔名", fname)
            details.append(df_p)

        except Exception as e:
            errors.append({"檔名": fname, "錯誤": str(e)})

if errors:
    with st.expander("⚠️ 部分檔案處理失敗（已略過）", expanded=True):
        st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)

if not results:
    st.error("沒有任何檔案成功處理：請先把 TXT 編碼調到中文正常（最常見 cp950 / big5 / utf-16）。")
    st.stop()

summary_all = pd.DataFrame(results)
detail_all = pd.concat(details, ignore_index=True) if details else pd.DataFrame()

# KPI（合計）
total_files_ok = len(summary_all)
total_in = int(summary_all["讀取列數"].sum())
total_removed = int(summary_all["刪除站所列數"].sum())
total_after = int(summary_all["處理後列數"].sum())

A_sum = float(summary_all["A) GM件數"].sum())
B_sum = float(summary_all["B) 一般倉零散PCS"].sum())
C_sum = float(summary_all["C) GM成箱PCS"].sum())
D_sum = float(summary_all["D) 一般倉成箱PCS"].sum())

st.caption(
    f"成功處理 {total_files_ok} 個檔案；"
    f"合計讀取 {total_in:,} 列；刪除站所 {total_removed:,} 列；處理後 {total_after:,} 列。"
)

c1, c2 = st.columns(2, gap="large")
with c1:
    render_kpis(
        [
            KPI("A) GM件數（合計）", _fmt_int(A_sum)),
            KPI("C) GM成箱PCS（合計）", _fmt0(C_sum)),
        ],
        cols=1,
    )
with c2:
    render_kpis(
        [
            KPI("B) 一般倉零散PCS（合計）", _fmt0(B_sum)),
            KPI("D) 一般倉成箱PCS（合計）", _fmt0(D_sum)),
        ],
        cols=1,
    )

card_open("📌 多檔統計總表")
show_df = summary_all.copy()
for c in ["A) GM件數", "B) 一般倉零散PCS", "C) GM成箱PCS", "D) 一般倉成箱PCS"]:
    show_df[c] = show_df[c].apply(_fmt0)
st.dataframe(show_df, use_container_width=True, hide_index=True)
card_close()

card_open("📤 匯出（統計總表 + 合併明細）")
stamp = datetime.now().strftime("%Y%m%d_%H%M")
filename = f"大豐KPI_整體作業量體_多檔_{stamp}.xlsx"
xlsx_bytes = make_excel_bytes(summary_all, detail_all)

download_excel_card(
    title="✅ 下載 Excel（含：統計總表 + 合併明細）",
    data=xlsx_bytes,
    filename=filename,
)

with st.expander("🔎 合併明細預覽（前 200 筆）", expanded=False):
    st.dataframe(detail_all.head(200), use_container_width=True)

card_close()
