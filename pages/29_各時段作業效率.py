# pages/29_各時段作業效率.py
# -*- coding: utf-8 -*-
import io
import os
from io import StringIO
from datetime import datetime, date
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Alignment, Font

# ---- 套用平台風格（有就用，沒有就退回原生）----
try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close
    HAS_COMMON_UI = True
except Exception:
    HAS_COMMON_UI = False

TPE = ZoneInfo("Asia/Taipei")

STATUS_PASS = "達標"
STATUS_FAIL = "未達標"
STATUS_NA = "未判斷"

# ✅ 特殊工時（分鐘）：12點、13點只有 30 分鐘
WORK_MINUTES_BY_HOUR = {12: 30, 13: 30}


# =============================
# 讀檔：CSV/Excel 強韌讀取
# =============================
def read_table_robust(file_name: str, raw: bytes, label: str = "檔案") -> pd.DataFrame:
    ext = os.path.splitext(file_name)[1].lower()

    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"):
        try:
            return pd.read_excel(io.BytesIO(raw))
        except Exception as e:
            raise ValueError(f"{label} 讀取 Excel 失敗：{e}")

    encodings = ["utf-8-sig", "utf-8", "cp950", "big5", "ms950", "gb18030", "latin1"]
    seps = [",", "\t", ";", "|"]

    last_err = None
    for enc in encodings:
        for sep in seps:
            try:
                df = pd.read_csv(io.BytesIO(raw), encoding=enc, sep=sep, engine="python", low_memory=False)
                if df.shape[1] <= 1:
                    continue
                return df
            except Exception as e:
                last_err = e

    try:
        text = raw.decode("utf-8", errors="replace")
        df = pd.read_csv(StringIO(text), sep=None, engine="python", low_memory=False)
        if df.shape[1] <= 1:
            raise ValueError("偵測不到有效分隔符，請確認檔案是否為真正 CSV。")
        return df
    except Exception as e:
        raise ValueError(f"{label} 讀取 CSV 失敗（已嘗試多種編碼/分隔符）：{last_err} / 最終：{e}")


def require_columns(df: pd.DataFrame, required: list, label: str):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{label} 缺少欄位：{missing}\n目前欄位：{list(df.columns)}")


def _norm_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def clean_line(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip()


def clean_zone_1to4(series: pd.Series) -> pd.Series:
    z = pd.to_numeric(series, errors="coerce").astype("Int64")
    return z.where(z.between(1, 4, inclusive="both"))


def _safe_time(s: str) -> str:
    s = str(s).strip()
    if not s:
        return "08:00"
    try:
        datetime.strptime(s, "%H:%M")
        return s
    except Exception:
        return "08:00"


def _bytes_sig(b: bytes) -> str:
    if b is None:
        return "0"
    n = len(b)
    head = b[:128]
    tail = b[-128:] if n >= 128 else b
    return f"{n}-{hash(head)}-{hash(tail)}"


def _slot_minutes(hour: int) -> int:
    return int(WORK_MINUTES_BY_HOUR.get(int(hour), 60))


# =============================
# KPI 計數（某小時）
# =============================
def _kpi_counts(dist_df: pd.DataFrame):
    if dist_df is None or dist_df.empty:
        return 0, 0, None
    p = int(dist_df.loc[dist_df["狀態"] == STATUS_PASS, "count"].sum())
    f = int(dist_df.loc[dist_df["狀態"] == STATUS_FAIL, "count"].sum())
    rate = (p / (p + f) * 100.0) if (p + f) > 0 else None
    return p, f, rate


# =============================
# Heatmap（Streamlit 顯示用：Python 計算）
# =============================
def render_hourly_heatmap(df_line_hourly: pd.DataFrame, hour_cols, title: str):
    if df_line_hourly is None or df_line_hourly.empty:
        st.info("沒有可呈現的圖。")
        return

    hour_cols = [int(h) for h in list(hour_cols)]
    plot = df_line_hourly.copy()

    plot["段數"] = pd.to_numeric(plot["段數"], errors="coerce").fillna(0).astype(int)
    plot["小時"] = pd.to_numeric(plot["小時"], errors="coerce").fillna(0).astype(int)
    plot["當小時加權PCS"] = pd.to_numeric(plot["當小時加權PCS"], errors="coerce").fillna(0.0)
    plot["本小時目標"] = pd.to_numeric(plot["本小時目標"], errors="coerce").fillna(0.0)

    plot["label"] = plot["段數"].astype(str) + "段｜" + plot["姓名"].astype(str)
    plot["狀態_色"] = plot["狀態"].fillna(STATUS_NA)
    plot["顯示量"] = plot["當小時加權PCS"].apply(lambda x: "" if abs(float(x)) < 1e-12 else f"{float(x):.2f}")

    order = (
        plot[["label", "段數", "姓名"]]
        .drop_duplicates()
        .sort_values(["段數", "姓名"])["label"]
        .tolist()
    )

    color_enc = alt.Color(
        "狀態_色:N",
        scale=alt.Scale(domain=[STATUS_PASS, STATUS_FAIL, STATUS_NA], range=["#2E7D32", "#C62828", "#D0D5DD"]),
        legend=alt.Legend(title="狀態"),
    )

    base = alt.Chart(plot).encode(
        x=alt.X("小時:O", sort=[str(h) for h in hour_cols], title="每小時"),
        y=alt.Y("label:N", sort=order, title="段數｜姓名"),
        tooltip=[
            alt.Tooltip("線別:N", title="線別"),
            alt.Tooltip("label:N", title="段數｜姓名"),
            alt.Tooltip("小時:O", title="小時"),
            alt.Tooltip("當小時加權PCS:Q", title="當小時加權PCS", format=",.4f"),
            alt.Tooltip("本小時目標:Q", title="本小時目標", format=",.2f"),
            alt.Tooltip("狀態:N", title="狀態"),
        ],
    )

    rect = base.mark_rect(cornerRadius=4).encode(color=color_enc)
    text = base.mark_text(fontSize=12, fontWeight=900).encode(text="顯示量:N")

    n_rows = max(1, plot["label"].nunique())
    height = min(42 * n_rows + 80, 900)
    st.altair_chart((rect + text).properties(title=title, height=height), use_container_width=True)


# =============================
# ✅ 輸出 Excel（保留公式）
#   - Sheet1: 完整明細（加權PCS用公式）
#   - Sheet2: 時段量體（每格SUMIFS；加總SUM；狀態IF）
# =============================
def build_excel_bytes_with_formulas(
    detail_df: pd.DataFrame,
    roster_df: pd.DataFrame,  # base_cols: 線別 段數 姓名 開始時間
    hour_cols: list[int],
    target_hr: float,
) -> bytes:
    wb = Workbook()
    ws_detail = wb.active
    ws_detail.title = "完整明細_去重後"

    ws_mat = wb.create_sheet("時段量體_公式")

    # ---- 寫入 Sheet1：完整明細 ----
    # 必須欄：PICKDATE 線別 段數 PACKQTY Cweight  (姓名/開始時間/納入計算/排除原因 也會寫)
    # 其中 加權PCS 用公式 =PACKQTY*Cweight
    cols = list(detail_df.columns)
    for c_idx, col in enumerate(cols, start=1):
        ws_detail.cell(row=1, column=c_idx, value=col).font = Font(bold=True)

    # 找 PACKQTY / Cweight 欄位位置
    try:
        col_pack = cols.index("PACKQTY") + 1
        col_w = cols.index("Cweight") + 1
    except Exception:
        col_pack, col_w = None, None

    for r_idx, row in enumerate(detail_df.itertuples(index=False), start=2):
        for c_idx, col in enumerate(cols, start=1):
            v = getattr(row, col) if hasattr(row, col) else None
            ws_detail.cell(row=r_idx, column=c_idx, value=v)

        # 若有加權PCS欄位 -> 用公式覆蓋
        if "加權PCS" in cols and col_pack and col_w:
            col_aw = cols.index("加權PCS") + 1
            p_cell = f"{get_column_letter(col_pack)}{r_idx}"
            w_cell = f"{get_column_letter(col_w)}{r_idx}"
            ws_detail.cell(row=r_idx, column=col_aw, value=f"={p_cell}*{w_cell}")
            ws_detail.cell(row=r_idx, column=col_aw).number_format = "0.0000"

    # 基本對齊
    for row in ws_detail.iter_rows(min_row=1, max_row=ws_detail.max_row, min_col=1, max_col=ws_detail.max_column):
        for cell in row:
            cell.alignment = Alignment(vertical="center")

    # ---- Sheet2：時段量體（公式）----
    base_cols = ["線別", "段數", "姓名", "開始時間"]
    mat_headers = base_cols + [str(h) for h in hour_cols] + ["加總", "加總狀態"]
    for c_idx, col in enumerate(mat_headers, start=1):
        ws_mat.cell(row=1, column=c_idx, value=col).font = Font(bold=True)

    # detail sheet 欄位字母定位
    detail_header_to_col = {ws_detail.cell(row=1, column=i).value: i for i in range(1, ws_detail.max_column + 1)}

    # SUMIFS 需要的欄：線別 段數 PICKDATE(取小時) 加權PCS 納入計算
    # 我們用 helper 欄位：明細中已有 "小時" 欄，若沒有就用 HOUR(PICKDATE) 公式做一欄
    # 這裡簡化：要求 detail_df 內已含 "小時"（我們在前面會加）
    need = ["線別", "段數", "小時", "加權PCS", "納入計算"]
    for k in need:
        if k not in detail_header_to_col:
            raise ValueError(f"明細缺少欄位「{k}」，無法建立 SUMIFS 公式。")

    d_line = get_column_letter(detail_header_to_col["線別"])
    d_zone = get_column_letter(detail_header_to_col["段數"])
    d_hour = get_column_letter(detail_header_to_col["小時"])
    d_aw = get_column_letter(detail_header_to_col["加權PCS"])
    d_in = get_column_letter(detail_header_to_col["納入計算"])

    d_first = 2
    d_last = ws_detail.max_row

    # roster_df 寫入 + 每小時公式
    for r_idx, row in enumerate(roster_df.itertuples(index=False), start=2):
        ws_mat.cell(row=r_idx, column=1, value=row.線別)
        ws_mat.cell(row=r_idx, column=2, value=int(row.段數))
        ws_mat.cell(row=r_idx, column=3, value=str(row.姓名))
        ws_mat.cell(row=r_idx, column=4, value=str(row.開始時間))

        # 每小時 SUMIFS（只加納入計算=TRUE）
        for j, h in enumerate(hour_cols, start=5):
            # SUMIFS(加權PCS, 線別=本列線別, 段數=本列段數, 小時=h, 納入計算=TRUE)
            line_cell = f"$A{r_idx}"
            zone_cell = f"$B{r_idx}"
            formula = (
                f'=SUMIFS('
                f'\'{ws_detail.title}\'!${d_aw}${d_first}:${d_aw}${d_last},'
                f'\'{ws_detail.title}\'!${d_line}${d_first}:${d_line}${d_last},{line_cell},'
                f'\'{ws_detail.title}\'!${d_zone}${d_first}:${d_zone}${d_last},{zone_cell},'
                f'\'{ws_detail.title}\'!${d_hour}${d_first}:${d_hour}${d_last},{h},'
                f'\'{ws_detail.title}\'!${d_in}${d_first}:${d_in}${d_last},TRUE)'
            )
            ws_mat.cell(row=r_idx, column=j, value=formula)
            ws_mat.cell(row=r_idx, column=j).number_format = "0.0000"

        # 加總（SUM）
        first_hour_col = 5
        last_hour_col = 4 + len(hour_cols)
        rng = f"{get_column_letter(first_hour_col)}{r_idx}:{get_column_letter(last_hour_col)}{r_idx}"
        ws_mat.cell(row=r_idx, column=last_hour_col + 1, value=f"=SUM({rng})")
        ws_mat.cell(row=r_idx, column=last_hour_col + 1).number_format = "0.0000"

        # 加總狀態：用「各小時目標加總」判斷（公式）
        # 目標：每小時 790*(有效分鐘/60)；這裡用固定規則：一般=790，12/13=790/2
        # 因為每個人開始時間不同，精準的「有效分鐘」需要很複雜公式；
        # ✅ 這裡按你目前規則做「整點目標」：每個小時固定 790（12/13=395）。
        # （你若要把開始時間分鐘也納入 Excel 公式，我也能再升級）
        target_terms = []
        for h in hour_cols:
            mins = _slot_minutes(h)
            target = target_hr * (mins / 60.0)
            target_terms.append(str(round(target, 6)))
        target_sum_formula = "+".join(target_terms) if target_terms else "0"
        sum_cell = f"{get_column_letter(last_hour_col + 1)}{r_idx}"
        ws_mat.cell(
            row=r_idx,
            column=last_hour_col + 2,
            value=f'=IF({sum_cell}>=({target_sum_formula}),"{STATUS_PASS}","{STATUS_FAIL}")'
        )

    # 基本對齊
    for row in ws_mat.iter_rows(min_row=1, max_row=ws_mat.max_row, min_col=1, max_col=ws_mat.max_column):
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")

    # ---- 下載 bytes ----
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def main():
    st.set_page_config(page_title="大豐物流 - 出貨課｜各時段作業效率", page_icon="⏱️", layout="wide")
    if HAS_COMMON_UI:
        inject_logistics_theme()
        set_page("📦 出貨課", "⏱️ 29｜各時段作業效率")

    st.markdown("### ⏱️ 各時段作業效率（保留完整明細＋計算公式；Excel 公式不存值）")

    fixed_time_map = {
        "范明俊": "08:00",
        "阮玉名": "08:00",
        "李茂銓": "08:00",
        "河文強": "08:00",
        "蔡麗珠": "08:00",
        "潘文一": "08:00",
        "阮伊黃": "08:00",
        "葉欲弘": "09:00",
        "阮武玉玄": "08:00",
        "吳黃金珠": "08:30",
        "潘氏青江": "08:00",
        "陳國慶": "08:30",
        "楊心如": "08:00",
        "阮瑞美黃緣": "08:00",
        "周芸蓁": "08:00",
        "黎氏瓊": "08:00",
        "王文楷": "08:30",
        "潘氏慶平": "08:00",
        "阮氏美麗": "08:00",
        "岳子恆": "08:30",
        "郭雙燕": "08:30",
        "阮孟勇": "08:00",
        "廖永成": "08:30",
        "楊浩傑": "08:30",
        "黃日康": "08:30",
        "蔣金妮": "08:30",
        "柴家欣": "08:30",
        "邱思捷": "09:00",
        "王建成": "09:00",
    }

    with st.sidebar:
        st.markdown("### 設定")
        target_hr = st.number_input("每小時目標（加權PCS/小時）", min_value=1.0, value=790.0, step=10.0)
        hour_min = st.number_input("起始小時", min_value=0, max_value=23, value=8, step=1)

        use_now = st.toggle("用現在時間作為判斷截止（台北時間）", value=True)
        if use_now:
            now = datetime.now(TPE)
        else:
            t_in = st.time_input("判斷截止時間（台北時間）", value=datetime.now(TPE).time())
            now = datetime.combine(date.today(), t_in).replace(tzinfo=TPE)

        st.caption(f"目前採用時間：{now.strftime('%Y-%m-%d %H:%M:%S')} (Asia/Taipei)")
        auto_calc = st.toggle("上傳/設定變更後自動更新", value=True)

    c1, c2 = st.columns(2)
    with c1:
        prod_file = st.file_uploader("① 上傳『原始生產資料』(CSV/Excel)", type=["csv", "xlsx", "xlsm", "xls"])
    with c2:
        mem_file = st.file_uploader("② 上傳『人員名單』(CSV/Excel)", type=["csv", "xlsx", "xlsm", "xls"])

    manual = st.button("🚀 立即更新/重算", type="primary", use_container_width=True)

    if prod_file is None or mem_file is None:
        st.info("請先上傳兩個檔案：生產資料 + 人員名單。")
        return

    prod_sig = _bytes_sig(prod_file.getvalue())
    mem_sig = _bytes_sig(mem_file.getvalue())
    settings_sig = f"{target_hr}-{hour_min}-{use_now}-{now.hour}-{now.minute}"

    last = st.session_state.get("_29_last_sig", None)
    cur_sig = (prod_sig, mem_sig, settings_sig)
    should_run = manual or (auto_calc and (last != cur_sig))
    if not should_run:
        st.caption("（目前結果已是最新；如有更新檔案/設定會自動同步）")
        return
    st.session_state["_29_last_sig"] = cur_sig

    try:
        # ========= 人員名單 =========
        df_mem_raw = _norm_cols(read_table_robust(mem_file.name, mem_file.getvalue(), label="人員名單檔案"))

        line_col_candidates = ["LINEID", "線別", "LineID", "LINE Id", "Line Id"]
        line_col = next((c for c in line_col_candidates if c in df_mem_raw.columns), None)
        if line_col is None:
            raise ValueError("人員名單找不到線別欄位（需要 LINEID 或 線別）。")

        seg_cols = {1: "第一段", 2: "第二段", 3: "第三段", 4: "第四段"}
        for _, colname in seg_cols.items():
            if colname not in df_mem_raw.columns:
                raise ValueError(f"人員名單缺少欄位：{colname}（需要 第一段～第四段）")

        member_list = []
        for _, row in df_mem_raw.iterrows():
            line_id = str(row.get(line_col, "")).strip()
            if not line_id or line_id.lower() == "nan":
                continue
            for zid, colname in seg_cols.items():
                name = row.get(colname, None)
                if pd.notna(name) and str(name).strip() != "":
                    n_str = str(name).strip()
                    st_time = _safe_time(fixed_time_map.get(n_str, "08:00"))
                    member_list.append({"線別": line_id, "段數": zid, "姓名": n_str, "開始時間": st_time})

        roster_df = pd.DataFrame(member_list)
        if roster_df.empty:
            raise ValueError("人員名單解析後為空：請確認 第一段～第四段 內有姓名。")

        roster_df["線別"] = clean_line(roster_df["線別"])
        roster_df["段數"] = clean_zone_1to4(roster_df["段數"])
        roster_df = roster_df[roster_df["段數"].notna()].copy()
        roster_df = roster_df.drop_duplicates(["線別", "段數"], keep="first").copy()
        roster_df = roster_df[["線別", "段數", "姓名", "開始時間"]].copy()

        # ========= 生產資料 =========
        df_raw = read_table_robust(prod_file.name, prod_file.getvalue(), label="生產資料檔案")
        require_columns(df_raw, ["PICKDATE", "LINEID", "ZONEID", "PACKQTY", "Cweight"], "生產資料檔案")

        df_raw["PICKDATE"] = pd.to_datetime(df_raw["PICKDATE"], errors="coerce")
        df_raw = df_raw[df_raw["PICKDATE"].notna()].copy()

        df_raw = df_raw.rename(columns={"LINEID": "線別", "ZONEID": "段數"})
        df_raw["線別"] = clean_line(df_raw["線別"])
        df_raw["段數"] = clean_zone_1to4(df_raw["段數"])
        df_raw = df_raw[df_raw["段數"].notna()].copy()

        df_raw["PACKQTY"] = pd.to_numeric(df_raw["PACKQTY"], errors="coerce").fillna(0)
        df_raw["Cweight"] = pd.to_numeric(df_raw["Cweight"], errors="coerce").fillna(0)

        # ✅ 去重指紋
        rid_cols = [c for c in df_raw.columns if c not in ("__rid",)]
        df_raw["__rid"] = pd.util.hash_pandas_object(df_raw[rid_cols], index=False)
        df_raw = df_raw.drop_duplicates("__rid", keep="first").copy()

        # 合併姓名/開始時間（用於 UI 顯示與 Excel SUMIFS Key）
        df = pd.merge(df_raw, roster_df, on=["線別", "段數"], how="left", validate="m:1")
        df["姓名"] = df["姓名"].fillna("未設定")
        df["開始時間"] = df["開始時間"].fillna("08:00").map(_safe_time)

        # ✅ 明細欄位：小時、納入計算
        df["小時"] = df["PICKDATE"].dt.hour
        df["PICK_MIN"] = df["PICKDATE"].dt.hour * 60 + df["PICKDATE"].dt.minute
        st_parts = df["開始時間"].astype(str).str.split(":", n=1, expand=True)
        st_h = pd.to_numeric(st_parts[0], errors="coerce").fillna(8).astype(int)
        st_m = pd.to_numeric(st_parts[1], errors="coerce").fillna(0).astype(int)
        df["開始分鐘"] = st_h * 60 + st_m
        df["納入計算"] = df["PICK_MIN"] >= df["開始分鐘"]
        df["排除原因"] = np.where(df["納入計算"], "", "早於開始時間")

        # ✅ Streamlit 顯示用（Python計算）加權PCS
        df["加權PCS"] = df["PACKQTY"] * df["Cweight"]

        # ========= Streamlit 顯示用：每小時彙總 + 狀態 =========
        cur_h, cur_m = now.hour, now.minute
        hour_cols = list(range(int(hour_min), int(cur_h) + 1)) if int(cur_h) >= int(hour_min) else [int(cur_h)]
        base_cols = ["線別", "段數", "姓名", "開始時間"]

        df_calc = df[df["納入計算"]].copy()
        hourly_sum = df_calc.groupby(base_cols + ["小時"], as_index=False)["加權PCS"].sum()
        hourly_sum = hourly_sum.rename(columns={"加權PCS": "當小時加權PCS"})

        keys = roster_df[base_cols].drop_duplicates().copy()
        grid_hours = keys.assign(_k=1).merge(pd.DataFrame({"小時": hour_cols, "_k": 1}), on="_k").drop(columns=["_k"])
        hourly_full = grid_hours.merge(hourly_sum, on=base_cols + ["小時"], how="left")
        hourly_full["當小時加權PCS"] = pd.to_numeric(hourly_full["當小時加權PCS"], errors="coerce").fillna(0.0)

        parts = hourly_full["開始時間"].astype(str).str.split(":", n=1, expand=True)
        s_h = pd.to_numeric(parts[0], errors="coerce").fillna(8).astype(int)
        s_m = pd.to_numeric(parts[1], errors="coerce").fillna(0).astype(int)
        hh = pd.to_numeric(hourly_full["小時"], errors="coerce").fillna(0).astype(int)
        slot = hh.map(lambda x: _slot_minutes(int(x))).astype(int)
        end_m = np.where(hh == cur_h, np.minimum(cur_m, slot), slot).astype(int)

        minutes_worked = np.where(
            hh > cur_h, 0,
            np.where(
                hh < s_h, 0,
                np.where(
                    hh == s_h, np.maximum(0, end_m - s_m),
                    end_m
                )
            )
        ).astype(float)

        hourly_full["本小時有效分鐘"] = minutes_worked
        hourly_full["本小時目標"] = (minutes_worked / 60.0) * float(target_hr)
        hourly_full["狀態"] = np.where(
            hourly_full["本小時有效分鐘"] <= 0,
            None,
            np.where(hourly_full["當小時加權PCS"] >= hourly_full["本小時目標"], STATUS_PASS, STATUS_FAIL)
        )

        dist = (
            hourly_full[hourly_full["狀態"].isin([STATUS_PASS, STATUS_FAIL])]
            .groupby(["線別", "小時", "狀態"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )

        st.success("計算完成 ✅（下載 Excel 將保留公式）")

        # ---- 顯示每線區塊 ----
        eff_hour = int(cur_h)
        lines = sorted(keys["線別"].dropna().unique().tolist())
        for line in lines:
            if HAS_COMMON_UI:
                card_open(f"📦 {line}")
            else:
                st.markdown(f"### 📦 {line}")

            dist_now = dist[(dist["線別"] == line) & (dist["小時"] == eff_hour)]
            p, f, rate = _kpi_counts(dist_now)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("判斷小時", f"{eff_hour} 點")
            c2.metric("達標 段數", p)
            c3.metric("未達標 段數", f)
            c4.metric("達標 率", (f"{rate:.1f}%" if rate is not None else "—"))

            df_line = hourly_full[hourly_full["線別"] == line][
                ["線別", "段數", "姓名", "小時", "當小時加權PCS", "本小時目標", "狀態"]
            ].copy()
            render_hourly_heatmap(df_line, hour_cols, title=f"{line}｜每小時（12/13=30分）")

            if HAS_COMMON_UI:
                card_close()

        # ---- 準備明細輸出（加權PCS欄位改成空，讓 Excel 公式填）----
        detail_df = df.copy()
        detail_df = detail_df.sort_values(["線別", "段數", "PICKDATE"]).reset_index(drop=True)

        # 確保欄位存在且順序合理
        if "加權PCS" not in detail_df.columns:
            detail_df["加權PCS"] = np.nan

        # 下載 Excel（含公式）
        xlsx_bytes = build_excel_bytes_with_formulas(
            detail_df=detail_df,
            roster_df=roster_df,
            hour_cols=hour_cols,
            target_hr=float(target_hr),
        )
        filename = f"產能時段_保留公式_{datetime.now(TPE).strftime('%H%M')}.xlsx"
        st.download_button(
            "⬇️ 下載 Excel（完整明細+矩陣皆保留公式）",
            data=xlsx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"發生錯誤：{e}")


if __name__ == "__main__":
    main()
