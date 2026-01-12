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


# =============================
# 讀檔
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


# =============================
# Excel：輸出「當小時加權PCS」，顏色用達標/未達標
# =============================
def build_excel_bytes_volume(matrix_vol: pd.DataFrame, matrix_stat: pd.DataFrame, hour_cols: list[int]) -> bytes:
    out_df = matrix_vol.copy()
    # 空白處理
    for h in hour_cols:
        if h in out_df.columns:
            out_df[h] = out_df[h].where(pd.notna(out_df[h]), "")

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        out_df.to_excel(writer, index=False, sheet_name="時段量體_達標色塊")
    bio.seek(0)

    wb = load_workbook(bio)
    ws = wb.active

    fill_ok = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_ng = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    base_cols = ["線別", "段數", "姓名", "開始時間"]
    min_col = len(base_cols) + 1
    max_col = len(base_cols) + len(hour_cols)

    # 讓數字好看
    for r in ws.iter_rows(min_row=2, min_col=min_col, max_col=max_col):
        for c in r:
            c.alignment = Alignment(horizontal="center", vertical="center")

    # 依狀態著色
    # matrix_stat 與 matrix_vol 欄位一致（同 index）
    # 這裡直接用 DataFrame 位置去映射 Excel 儲存格（行列對齊）
    stat_values = matrix_stat[hour_cols].values.tolist()
    for i, r in enumerate(ws.iter_rows(min_row=2, min_col=min_col, max_col=max_col)):
        for j, c in enumerate(r):
            stat = stat_values[i][j] if i < len(stat_values) and j < len(stat_values[i]) else None
            if stat == STATUS_PASS:
                c.fill = fill_ok
                c.number_format = "0.0000"
            elif stat == STATUS_FAIL:
                c.fill = fill_ng
                c.number_format = "0.0000"
            else:
                # 未判斷/未到時段 -> 不上色
                pass

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# =============================
# KPI 計數
# =============================
def _kpi_counts(dist_df: pd.DataFrame):
    if dist_df is None or dist_df.empty:
        return 0, 0, None
    p = int(dist_df.loc[dist_df["狀態"] == STATUS_PASS, "count"].sum())
    f = int(dist_df.loc[dist_df["狀態"] == STATUS_FAIL, "count"].sum())
    rate = (p / (p + f) * 100.0) if (p + f) > 0 else None
    return p, f, rate


# =============================
# 長條圖矩陣（取代表格）
# 每一格顯示「當小時加權PCS」，顏色表示達標/未達標
# =============================
def render_hourly_matrix_bars(df_line: pd.DataFrame, hour_cols: list[int], title: str):
    """
    df_line: columns = 段數, 姓名, 小時, 當小時加權PCS, 狀態
    """
    if df_line is None or df_line.empty:
        st.info("此線別沒有資料可呈現。")
        return

    plot = df_line.copy()
    plot["段數"] = pd.to_numeric(plot["段數"], errors="coerce").fillna(0).astype(int)
    plot["row_label"] = plot["段數"].astype(str) + "段｜" + plot["姓名"].astype(str)
    plot["小時"] = pd.to_numeric(plot["小時"], errors="coerce").astype(int)

    # 顯示文字：量體（0 就不顯示，避免太亂）
    def _fmt(v):
        try:
            v = float(v)
        except Exception:
            return ""
        return "" if abs(v) < 1e-12 else f"{v:.2f}"

    plot["顯示量"] = plot["當小時加權PCS"].apply(_fmt)

    # 顏色：達標/未達標/未判斷
    color_cond = alt.condition(
        alt.datum["狀態"] == STATUS_PASS,
        alt.value("#2E7D32"),
        alt.condition(
            alt.datum["狀態"] == STATUS_FAIL,
            alt.value("#C62828"),
            alt.value("#D0D5DD"),  # 未判斷/未到時段
        ),
    )

    base = alt.Chart(plot).encode(
        x=alt.X("小時:O", sort=[str(h) for h in hour_cols], title="小時"),
        tooltip=[
            alt.Tooltip("row_label:N", title="段數｜姓名"),
            alt.Tooltip("小時:O", title="小時"),
            alt.Tooltip("當小時加權PCS:Q", title="當小時加權PCS", format=",.4f"),
            alt.Tooltip("狀態:N", title="狀態"),
        ],
    )

    bars = base.mark_bar(size=20).encode(
        y=alt.Y("當小時加權PCS:Q", title="當小時加權PCS"),
        color=color_cond,
    )

    labels = base.mark_text(dy=-10, fontSize=11).encode(
        y=alt.Y("當小時加權PCS:Q"),
        text=alt.Text("顯示量:N"),
    )

    layered = (bars + labels).properties(height=120)

    # 每個人一列（段1~段4），用 facet row
    chart = layered.facet(
        row=alt.Row("row_label:N", sort=alt.SortField(field="段數", order="ascending"), header=alt.Header(title=None)),
        spacing=8,
    ).resolve_scale(
        y="independent"
    ).properties(
        title=title
    )

    st.altair_chart(chart, use_container_width=True)


def _render_hbar_person(dist_person: pd.DataFrame, title: str):
    if dist_person is None or dist_person.empty:
        st.info("沒有可呈現的橫條圖。")
        return
    labels = dist_person["label"].drop_duplicates().tolist()
    height = min(26 * len(labels) + 40, 520)

    chart = (
        alt.Chart(dist_person)
        .mark_bar()
        .encode(
            y=alt.Y("label:N", sort=alt.SortField(field="total", order="descending"), title="段數｜姓名"),
            x=alt.X("count:Q", title="時段數（小時格數）", stack="zero"),
            color=alt.Color(
                "狀態:N",
                scale=alt.Scale(domain=[STATUS_PASS, STATUS_FAIL], range=["#2E7D32", "#C62828"]),
                legend=alt.Legend(title="狀態"),
            ),
            tooltip=[
                alt.Tooltip("label:N", title="段數｜姓名"),
                alt.Tooltip("狀態:N"),
                alt.Tooltip("count:Q", title="時段數"),
            ],
        )
        .properties(title=title, height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_hbar_lines(dist_line: pd.DataFrame, title: str):
    if dist_line is None or dist_line.empty:
        st.info("沒有可呈現的全線橫條圖。")
        return
    height = min(26 * dist_line["線別"].nunique() + 40, 520)
    chart = (
        alt.Chart(dist_line)
        .mark_bar()
        .encode(
            y=alt.Y("線別:N", sort=alt.SortField(field="total", order="descending"), title="線別"),
            x=alt.X("count:Q", title="時段數（小時格數）", stack="zero"),
            color=alt.Color(
                "狀態:N",
                scale=alt.Scale(domain=[STATUS_PASS, STATUS_FAIL], range=["#2E7D32", "#C62828"]),
                legend=alt.Legend(title="狀態"),
            ),
            tooltip=[alt.Tooltip("線別:N"), alt.Tooltip("狀態:N"), alt.Tooltip("count:Q", title="時段數")],
        )
        .properties(title=title, height=height)
    )
    st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config(page_title="大豐物流 - 出貨課｜各時段作業效率", page_icon="⏱️", layout="wide")
    if HAS_COMMON_UI:
        inject_logistics_theme()
        set_page("📦 出貨課", "⏱️ 29｜各時段作業效率")

    st.markdown("### ⏱️ 各時段作業效率（量體＋達標色塊｜段1~段4）")

    fixed_time_map = {
        '范明俊': '08:00', '阮玉名': '08:00', '李茂銓': '08:00', '河文強': '08:00',
        '蔡麗珠': '08:00', '潘文一': '08:00', '阮伊黃': '08:00', '葉欲弘': '09:00',
        '阮武玉玄': '08:00', '吳黃金珠': '08:30', '潘氏青江': '08:00', '陳國慶': '08:30',
        '楊心如': '08:00', '阮瑞美黃緣': '08:00', '周芸蓁': '08:00', '黎氏瓊': '08:00',
        '王文楷': '08:30', '潘氏慶平': '08:00', '阮氏美麗': '08:00', '岳子恆': '08:30',
        '郭雙燕': '08:30', '阮孟勇': '08:00', '廖永成':'08:30', '楊浩傑':'08:30', '黃日康':'08:30',
        '蔣金妮':'08:30', '柴家欣':'08:30',
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

    c1, c2 = st.columns(2)
    with c1:
        prod_file = st.file_uploader("① 上傳『原始生產資料』(CSV/Excel)", type=["csv", "xlsx", "xlsm", "xls"])
    with c2:
        mem_file = st.file_uploader("② 上傳『人員名單』(CSV/Excel)", type=["csv", "xlsx", "xlsm", "xls"])

    run = st.button("🚀 開始計算", type="primary", use_container_width=True)
    if not run:
        return
    if prod_file is None or mem_file is None:
        st.error("請先上傳兩個檔案：生產資料 + 人員名單。")
        return

    try:
        # 1) 人員名單
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
        df_members = df_members.drop_duplicates(["線別", "段數"], keep="first").copy()

        # 2) 生產資料（去重後加權PCS）
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

        rid_cols = [c for c in df_raw.columns if c not in ("姓名", "開始時間", "小時", "__rid")]
        df_raw["__rid"] = pd.util.hash_pandas_object(df_raw[rid_cols], index=False)

        df = pd.merge(df_raw, df_members, on=["線別", "段數"], how="left", validate="m:1")
        df["姓名"] = df["姓名"].fillna("未設定")
        df["開始時間"] = df["開始時間"].fillna("08:00").map(_safe_time)
        df = df.drop_duplicates("__rid", keep="first").copy()

        # 開始時間過濾（原始紀錄）
        pick_minutes = df["PICKDATE"].dt.hour * 60 + df["PICKDATE"].dt.minute
        st_parts = df["開始時間"].astype(str).str.split(":", n=1, expand=True)
        st_h = pd.to_numeric(st_parts[0], errors="coerce").fillna(8).astype(int)
        st_m = pd.to_numeric(st_parts[1], errors="coerce").fillna(0).astype(int)
        st_minutes = st_h * 60 + st_m
        df = df[pick_minutes >= st_minutes].copy()
        if df.empty:
            raise ValueError("套用開始時間過濾後沒有資料：請確認 PICKDATE 與開始時間設定。")

        # 3) 每小時加總（當小時量）
        df["小時"] = df["PICKDATE"].dt.hour
        base_cols = ["線別", "段數", "姓名", "開始時間"]

        hourly_sum = df.groupby(base_cols + ["小時"], as_index=False)["加權PCS"].sum()
        hourly_sum = hourly_sum.rename(columns={"加權PCS": "當小時加權PCS"})

        # ✅ 補齊每小時（就算該小時沒有資料，也要有 0 才能判斷未達標）
        cur_h, cur_m = now.hour, now.minute
        hour_cols = list(range(int(hour_min), int(cur_h) + 1))

        keys = df_members[base_cols].drop_duplicates().copy()
        grid_hours = keys.assign(_k=1).merge(pd.DataFrame({"小時": hour_cols, "_k": 1}), on="_k").drop(columns=["_k"])

        hourly_full = grid_hours.merge(hourly_sum, on=base_cols + ["小時"], how="left")
        hourly_full["當小時加權PCS"] = pd.to_numeric(hourly_full["當小時加權PCS"], errors="coerce").fillna(0.0)

        hourly_full = hourly_full.sort_values(base_cols + ["小時"]).reset_index(drop=True)
        hourly_full["累計實際量"] = hourly_full.groupby(["線別", "段數", "姓名"])["當小時加權PCS"].cumsum()

        # 判斷達標/未達標（用累計）
        st_parts2 = hourly_full["開始時間"].astype(str).str.split(":", n=1, expand=True)
        s_h = pd.to_numeric(st_parts2[0], errors="coerce").fillna(8).astype(float)
        s_m = pd.to_numeric(st_parts2[1], errors="coerce").fillna(0).astype(float)
        h = hourly_full["小時"].astype(float)

        elapsed = np.where(
            h < cur_h,
            (h - s_h + 1.0) - (s_m / 60.0),
            np.where(
                h == cur_h,
                (h - s_h) + ((cur_m - s_m) / 60.0),
                np.nan
            )
        )

        # ✅ elapsed <= 0 代表尚未開始（例如 08:30 在 08:00）
        valid = (~np.isnan(elapsed)) & (elapsed > 0)
        target = np.where(valid, elapsed * float(target_hr), np.nan)

        status = np.where(
            ~valid,
            None,
            np.where(hourly_full["累計實際量"].values >= target, STATUS_PASS, STATUS_FAIL)
        )
        hourly_full["狀態"] = status

        # 供 KPI 計數使用
        dist = (
            hourly_full[hourly_full["狀態"].isin([STATUS_PASS, STATUS_FAIL])]
            .groupby(["線別", "小時", "狀態"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values(["線別", "小時", "狀態"])
        )

        # 下載用：輸出「當小時加權PCS」矩陣 + 狀態矩陣（用於上色）
        matrix_vol = hourly_full.pivot(index=base_cols, columns="小時", values="當小時加權PCS").reset_index()
        matrix_stat = hourly_full.pivot(index=base_cols, columns="小時", values="狀態").reset_index()

        matrix_vol.columns = [int(c) if str(c).isdigit() else c for c in matrix_vol.columns]
        matrix_stat.columns = [int(c) if str(c).isdigit() else c for c in matrix_stat.columns]
        for hh in hour_cols:
            if hh not in matrix_vol.columns:
                matrix_vol[hh] = np.nan
            if hh not in matrix_stat.columns:
                matrix_stat[hh] = None
        matrix_vol = matrix_vol[base_cols + hour_cols]
        matrix_stat = matrix_stat[base_cols + hour_cols]

        st.success("計算完成 ✅（每格顯示：當小時加權PCS；顏色：達標/未達標）")
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

            # ✅ 用長條圖矩陣取代表格
            df_line = hourly_full[hourly_full["線別"] == line][["段數", "姓名", "小時", "當小時加權PCS", "狀態"]].copy()
            render_hourly_matrix_bars(df_line, hour_cols, title=f"{line}｜段1~段4 × 每小時（量體＋達標色塊）")

            # 你原本要的橫條圖（仍保留）
            dist_person = (
                hourly_full[(hourly_full["線別"] == line) & (hourly_full["狀態"].isin([STATUS_PASS, STATUS_FAIL]))]
                .groupby(["段數", "姓名", "狀態"], as_index=False)
                .size()
                .rename(columns={"size": "count"})
            )
            if not dist_person.empty:
                dist_person["label"] = dist_person["段數"].astype(int).astype(str) + "段｜" + dist_person["姓名"].astype(str)
                totals = dist_person.groupby("label", as_index=False)["count"].sum().rename(columns={"count": "total"})
                dist_person = dist_person.merge(totals, on="label", how="left")

            st.markdown("#### 📌 橫條圖（段1~段4｜姓名：達標/未達標次數）")
            _render_hbar_person(dist_person, title=f"{line}｜段1~段4（含姓名）達標/未達標 次數")

            if HAS_COMMON_UI:
                card_close()

        # 全作業線總和
        st.markdown("## 🧾 全作業線總和（達標/未達標）")
        dist_all_now = dist[dist["小時"] == eff_hour]
        p_all, f_all, rate_all = _kpi_counts(dist_all_now)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("判斷小時", f"{eff_hour} 點")
        c2.metric("達標 段數", p_all)
        c3.metric("未達標 段數", f_all)
        c4.metric("達標 率", (f"{rate_all:.1f}%" if rate_all is not None else "—"))

        dist_lines = (
            hourly_full[hourly_full["狀態"].isin([STATUS_PASS, STATUS_FAIL])]
            .groupby(["線別", "狀態"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )
        if not dist_lines.empty:
            totals = dist_lines.groupby("線別", as_index=False)["count"].sum().rename(columns={"count": "total"})
            dist_lines = dist_lines.merge(totals, on="線別", how="left")

        st.markdown("#### 📌 橫條圖（各線：達標/未達標次數）")
        _render_hbar_lines(dist_lines, title="全作業線｜各線達標/未達標 次數")

        # 下載 Excel（現在輸出量體，顏色表示達標/未達標）
        st.markdown("## ⬇️ 下載")
        xlsx_bytes = build_excel_bytes_volume(matrix_vol, matrix_stat, hour_cols)
        filename = f"產能時段_量體達標色塊_{datetime.now(TPE).strftime('%H%M')}.xlsx"
        st.download_button(
            "⬇️ 下載 Excel（每格=當小時加權PCS，顏色=達標/未達標）",
            data=xlsx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    except Exception as e:
        st.error(f"發生錯誤：{e}")


if __name__ == "__main__":
    main()
