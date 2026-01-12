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
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Alignment

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
# ✅ Heatmap：X=每小時，格內=量體，色=達標/未達標/未判斷
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
# ✅ 表格（每格=量體；色=達標/未達標/未判斷）+ ✅ 加總（也上色）
# =============================
def render_grid_table_with_total(df_line: pd.DataFrame, hour_cols, title: str):
    if df_line is None or df_line.empty:
        st.info("此線別沒有資料可呈現。")
        return

    hour_cols = [int(h) for h in list(hour_cols)]

    base = df_line[["段數", "姓名", "小時", "當小時加權PCS", "本小時目標", "狀態"]].copy()
    base["段數"] = pd.to_numeric(base["段數"], errors="coerce").fillna(0).astype(int)
    base["小時"] = pd.to_numeric(base["小時"], errors="coerce").fillna(0).astype(int)
    base["當小時加權PCS"] = pd.to_numeric(base["當小時加權PCS"], errors="coerce").fillna(0.0)
    base["本小時目標"] = pd.to_numeric(base["本小時目標"], errors="coerce").fillna(0.0)

    vol = base.pivot_table(index=["段數", "姓名"], columns="小時", values="當小時加權PCS", aggfunc="first")
    tar = base.pivot_table(index=["段數", "姓名"], columns="小時", values="本小時目標", aggfunc="first")
    stat = base.pivot_table(index=["段數", "姓名"], columns="小時", values="狀態", aggfunc="first")

    for h in hour_cols:
        if h not in vol.columns:
            vol[h] = 0.0
        if h not in tar.columns:
            tar[h] = 0.0
        if h not in stat.columns:
            stat[h] = None

    vol = vol[hour_cols]
    tar = tar[hour_cols]
    stat = stat[hour_cols]

    total_pcs = vol.sum(axis=1)
    total_tar = tar.sum(axis=1)
    total_stat = np.where(total_tar <= 0, None, np.where(total_pcs >= total_tar, STATUS_PASS, STATUS_FAIL))

    vol2 = vol.reset_index().copy()
    stat2 = stat.reset_index().copy()

    show = vol2.copy()
    for h in hour_cols:
        show[h] = show[h].apply(lambda x: "" if abs(float(x)) < 1e-12 else f"{float(x):.2f}")

    # ✅ 欄名用「加總」（跟你截圖一致）
    show["加總"] = total_pcs.values
    show["加總"] = show["加總"].apply(lambda x: "" if abs(float(x)) < 1e-12 else f"{float(x):.4f}")
    total_stat_list = list(total_stat)

    def _style(_df: pd.DataFrame):
        styles = pd.DataFrame("", index=_df.index, columns=_df.columns)
        if "段數" in styles.columns:
            styles["段數"] = "text-align:center;font-weight:800;"
        if "姓名" in styles.columns:
            styles["姓名"] = "text-align:left;font-weight:800;"

        for h in hour_cols:
            if h not in styles.columns:
                continue
            for i in range(len(_df)):
                s = None
                try:
                    s = stat2.at[i, h]
                except Exception:
                    s = None
                if s == STATUS_PASS:
                    styles.at[i, h] = "background-color:#C6EFCE;color:#1b4332;font-weight:900;text-align:center;"
                elif s == STATUS_FAIL:
                    styles.at[i, h] = "background-color:#FFC7CE;color:#7a0019;font-weight:900;text-align:center;"
                else:
                    styles.at[i, h] = "background-color:#F2F4F7;color:#667085;text-align:center;"

        # ✅ 加總上色
        if "加總" in styles.columns:
            for i in range(len(_df)):
                s = total_stat_list[i] if i < len(total_stat_list) else None
                if s == STATUS_PASS:
                    styles.at[i, "加總"] = "background-color:#C6EFCE;color:#1b4332;font-weight:950;text-align:center;"
                elif s == STATUS_FAIL:
                    styles.at[i, "加總"] = "background-color:#FFC7CE;color:#7a0019;font-weight:950;text-align:center;"
                else:
                    styles.at[i, "加總"] = "background-color:#F2F4F7;color:#667085;font-weight:900;text-align:center;"

        return styles

    st.markdown(f"#### {title}")
    st.dataframe(show.style.apply(_style, axis=None), use_container_width=True, hide_index=True)


# =============================
# Excel：輸出「每小時PCS」+「加總」，顏色皆套用達標/未達標
# =============================
def build_excel_bytes_volume(matrix_vol: pd.DataFrame, matrix_stat: pd.DataFrame, hour_cols: list[int]) -> bytes:
    out_df = matrix_vol.copy()

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        out_df.to_excel(writer, index=False, sheet_name="時段量體_達標色塊")
    bio.seek(0)

    wb = load_workbook(bio)
    ws = wb.active

    fill_ok = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_ng = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    base_cols = ["線別", "段數", "姓名", "開始時間"]
    hour_cols = [int(h) for h in hour_cols]

    # 小時欄位在 Excel 的起迄
    min_col = len(base_cols) + 1
    max_col = len(base_cols) + len(hour_cols)

    # 找「加總」欄位
    headers = [c.value for c in ws[1]]
    total_col_idx = None
    for name in ("加總", "加總PCS"):
        if name in headers:
            total_col_idx = headers.index(name) + 1
            break

    # 格式
    end_col = total_col_idx if total_col_idx is not None else max_col
    for r in ws.iter_rows(min_row=2, min_col=min_col, max_col=end_col):
        for c in r:
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.number_format = "0.0000"

    # 小時格子著色
    stat_values = matrix_stat[hour_cols].values.tolist()
    for i, r in enumerate(ws.iter_rows(min_row=2, min_col=min_col, max_col=max_col)):
        for j, c in enumerate(r):
            stat = stat_values[i][j] if i < len(stat_values) and j < len(stat_values[i]) else None
            if stat == STATUS_PASS:
                c.fill = fill_ok
            elif stat == STATUS_FAIL:
                c.fill = fill_ng

    # ✅ 加總欄位著色（用 matrix_stat["加總狀態"]）
    if total_col_idx is not None and "加總狀態" in matrix_stat.columns:
        total_stats = matrix_stat["加總狀態"].tolist()
        for i in range(2, ws.max_row + 1):
            stat = total_stats[i - 2] if (i - 2) < len(total_stats) else None
            cell = ws.cell(row=i, column=total_col_idx)
            cell.number_format = "0.0000"
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if stat == STATUS_PASS:
                cell.fill = fill_ok
            elif stat == STATUS_FAIL:
                cell.fill = fill_ng

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def main():
    st.set_page_config(page_title="大豐物流 - 出貨課｜各時段作業效率", page_icon="⏱️", layout="wide")
    if HAS_COMMON_UI:
        inject_logistics_theme()
        set_page("📦 出貨課", "⏱️ 29｜各時段作業效率")

    st.markdown("### ⏱️ 各時段作業效率（每格顯示量體｜顏色=達標/未達標｜含加總上色）")

    fixed_time_map = {
        '范明俊': '08:00', '阮玉名': '08:00', '李茂銓': '08:00', '河文強': '08:00',
        '蔡麗珠': '08:00', '潘文一': '08:00', '阮伊黃': '08:00', '葉欲弘': '09:00',
        '阮武玉玄': '08:00', '吳黃金珠': '08:30', '潘氏青江': '08:00', '陳國慶': '08:30',
        '楊心如': '08:00', '阮瑞美黃緣': '08:00', '周芸蓁': '08:00', '黎氏瓊': '08:00',
        '王文楷': '08:30', '潘氏慶平': '08:00', '阮氏美麗': '08:00', '岳子恆': '08:30',
        '郭雙燕': '08:30', '阮孟勇': '08:00', '廖永成': '08:30', '楊浩傑': '08:30', '黃日康': '08:30',
        '蔣金妮': '08:30', '柴家欣': '08:30',
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
        show_table = st.toggle("顯示表格（含加總）", value=True)

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
    settings_sig = f"{target_hr}-{hour_min}-{use_now}-{now.hour}-{now.minute}-{show_table}"

    last = st.session_state.get("_29_last_sig", None)
    cur_sig = (prod_sig, mem_sig, settings_sig)
    should_run = manual or (auto_calc and (last != cur_sig))
    if not should_run:
        st.caption("（目前結果已是最新；如有更新檔案/設定會自動同步）")
        return
    st.session_state["_29_last_sig"] = cur_sig

    try:
        # ========= 1) 人員名單 =========
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

        df_members = pd.DataFrame(member_list)
        if df_members.empty:
            raise ValueError("人員名單解析後為空：請確認 第一段～第四段 內有姓名。")

        df_members["線別"] = clean_line(df_members["線別"])
        df_members["段數"] = clean_zone_1to4(df_members["段數"])
        df_members = df_members[df_members["段數"].notna()].copy()

        # ✅ 同線別+段數只取第一筆，避免 merge 展開
        df_members = df_members.drop_duplicates(["線別", "段數"], keep="first").copy()

        # ========= 2) 生產資料（去重後加權PCS） =========
        df_raw = read_table_robust(prod_file.name, prod_file.getvalue(), label="生產資料檔案")
        require_columns(df_raw, ["PICKDATE", "LINEID", "ZONEID", "PACKQTY", "Cweight"], "生產資料檔案")

        df_raw["PICKDATE"] = pd.to_datetime(df_raw["PICKDATE"], errors="coerce")
        df_raw = df_raw[df_raw["PICKDATE"].notna()].copy()

        df_raw = df_raw.rename(columns={"LINEID": "線別", "ZONEID": "段數"})
        df_raw["線別"] = clean_line(df_raw["線別"])
        df_raw["段數"] = clean_zone_1to4(df_raw["段數"])
        df_raw = df_raw[df_raw["段數"].notna()].copy()
        if df_raw.empty:
            raise ValueError("生產資料清理後為空：請確認 ZONEID 是否為 1~4。")

        df_raw["PACKQTY"] = pd.to_numeric(df_raw["PACKQTY"], errors="coerce").fillna(0)
        df_raw["Cweight"] = pd.to_numeric(df_raw["Cweight"], errors="coerce").fillna(0)
        df_raw["加權PCS"] = df_raw["PACKQTY"] * df_raw["Cweight"]

        # ✅ 唯一指紋去重（避免翻倍）
        rid_cols = [c for c in df_raw.columns if c not in ("姓名", "開始時間", "小時", "__rid")]
        df_raw["__rid"] = pd.util.hash_pandas_object(df_raw[rid_cols], index=False)

        df = pd.merge(df_raw, df_members, on=["線別", "段數"], how="left", validate="m:1")
        df["姓名"] = df["姓名"].fillna("未設定")
        df["開始時間"] = df["開始時間"].fillna("08:00").map(_safe_time)
        df = df.drop_duplicates("__rid", keep="first").copy()

        # 開始時間過濾
        pick_minutes = df["PICKDATE"].dt.hour * 60 + df["PICKDATE"].dt.minute
        st_parts = df["開始時間"].astype(str).str.split(":", n=1, expand=True)
        st_h = pd.to_numeric(st_parts[0], errors="coerce").fillna(8).astype(int)
        st_m = pd.to_numeric(st_parts[1], errors="coerce").fillna(0).astype(int)
        st_minutes = st_h * 60 + st_m
        df = df[pick_minutes >= st_minutes].copy()
        if df.empty:
            raise ValueError("套用開始時間過濾後沒有資料：請確認 PICKDATE 與開始時間設定。")

        # ========= 3) 每小時量體 =========
        df["小時"] = df["PICKDATE"].dt.hour
        base_cols = ["線別", "段數", "姓名", "開始時間"]

        hourly_sum = df.groupby(base_cols + ["小時"], as_index=False)["加權PCS"].sum()
        hourly_sum = hourly_sum.rename(columns={"加權PCS": "當小時加權PCS"})

        cur_h, cur_m = now.hour, now.minute
        if int(cur_h) >= int(hour_min):
            hour_cols = list(range(int(hour_min), int(cur_h) + 1))
        else:
            hour_cols = [int(cur_h)]  # 避免空 range

        keys = df_members[base_cols].drop_duplicates().copy()
        grid_hours = keys.assign(_k=1).merge(pd.DataFrame({"小時": hour_cols, "_k": 1}), on="_k").drop(columns=["_k"])

        hourly_full = grid_hours.merge(hourly_sum, on=base_cols + ["小時"], how="left")
        hourly_full["當小時加權PCS"] = pd.to_numeric(hourly_full["當小時加權PCS"], errors="coerce").fillna(0.0)

        # ========= 4) ✅ 每小時判斷（本小時目標） =========
        parts = hourly_full["開始時間"].astype(str).str.split(":", n=1, expand=True)
        s_h = pd.to_numeric(parts[0], errors="coerce").fillna(8).astype(int)
        s_m = pd.to_numeric(parts[1], errors="coerce").fillna(0).astype(int)

        hh = pd.to_numeric(hourly_full["小時"], errors="coerce").fillna(0).astype(int)
        slot = hh.map(lambda x: _slot_minutes(int(x))).astype(int)

        # end_m：若是目前小時，用現在分鐘，但 cap 到 slot（12/13最多 30）
        end_m = np.where(hh == cur_h, np.minimum(cur_m, slot), slot).astype(int)

        # minutes_worked in this hour:
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

        # KPI（某小時）
        dist = (
            hourly_full[hourly_full["狀態"].isin([STATUS_PASS, STATUS_FAIL])]
            .groupby(["線別", "小時", "狀態"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )

        # ========= 5) ✅ 匯出矩陣 + ✅ 加總（逐列相加，保證有值） =========
        matrix_vol = hourly_full.pivot(index=base_cols, columns="小時", values="當小時加權PCS").reset_index()
        matrix_stat = hourly_full.pivot(index=base_cols, columns="小時", values="狀態").reset_index()
        matrix_tar = hourly_full.pivot(index=base_cols, columns="小時", values="本小時目標").reset_index()

        matrix_vol.columns = [int(c) if str(c).isdigit() else c for c in matrix_vol.columns]
        matrix_stat.columns = [int(c) if str(c).isdigit() else c for c in matrix_stat.columns]
        matrix_tar.columns = [int(c) if str(c).isdigit() else c for c in matrix_tar.columns]

        for h in hour_cols:
            if h not in matrix_vol.columns:
                matrix_vol[h] = 0.0
            if h not in matrix_stat.columns:
                matrix_stat[h] = None
            if h not in matrix_tar.columns:
                matrix_tar[h] = 0.0

        matrix_vol = matrix_vol[base_cols + hour_cols]
        matrix_stat = matrix_stat[base_cols + hour_cols]
        matrix_tar = matrix_tar[base_cols + hour_cols]

        # ✅ 加總（欄名=加總，跟你截圖一致）
        matrix_vol["加總"] = (
            matrix_vol[hour_cols]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0.0)
            .sum(axis=1)
        )

        total_target = (
            matrix_tar[hour_cols]
            .apply(pd.to_numeric, errors="coerce")
            .fillna(0.0)
            .sum(axis=1)
        )

        matrix_stat["加總狀態"] = np.where(
            total_target <= 0,
            None,
            np.where(matrix_vol["加總"] >= total_target, STATUS_PASS, STATUS_FAIL)
        )

        st.success("計算完成 ✅（加總已確保計算；加總也會上色；12/13=30分）")
        st.markdown("## 📊 KPI（每線：段1~段4）")

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
                ["段數", "姓名", "小時", "當小時加權PCS", "本小時目標", "狀態"]
            ].copy()

            st.markdown("#### 📌 每小時量體格（顏色=達標/未達標｜格內=量體）")
            render_hourly_heatmap(
                df_line_hourly=df_line,
                hour_cols=hour_cols,
                title=f"{line}｜每小時（12/13=30分）"
            )

            if show_table:
                render_grid_table_with_total(
                    df_line=df_line,
                    hour_cols=hour_cols,
                    title="段1~段4 × 每小時（表格：每格=量體；最右=加總，上色）"
                )

            if HAS_COMMON_UI:
                card_close()

        st.markdown("## ⬇️ 下載")
        xlsx_bytes = build_excel_bytes_volume(matrix_vol, matrix_stat, hour_cols)
        filename = f"產能時段_量體達標色塊_含加總_{datetime.now(TPE).strftime('%H%M')}.xlsx"
        st.download_button(
            "⬇️ 下載 Excel（每格=當小時加權PCS；含加總；顏色=達標/未達標）",
            data=xlsx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"發生錯誤：{e}")


if __name__ == "__main__":
    main()
