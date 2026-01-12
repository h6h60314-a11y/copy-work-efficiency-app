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
from openpyxl.styles import PatternFill

# ---- 套用平台風格（有就用，沒有就退回原生）----
try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close
    HAS_COMMON_UI = True
except Exception:
    HAS_COMMON_UI = False

TPE = ZoneInfo("Asia/Taipei")

# ✅ 狀態文字（你要的）
STATUS_PASS = "達標"
STATUS_FAIL = "未達標"


# =============================
# 強韌讀檔：CSV/Excel 自動處理編碼/分隔符
# =============================
def read_table_robust(file_name: str, raw: bytes, label: str = "檔案") -> pd.DataFrame:
    ext = os.path.splitext(file_name)[1].lower()

    # Excel
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm", ".xls"):
        try:
            return pd.read_excel(io.BytesIO(raw))
        except Exception as e:
            raise ValueError(f"{label} 讀取 Excel 失敗：{e}")

    # CSV：多編碼 + 多分隔符
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

    # 最後手段：bytes -> utf-8 replace，再自動分隔
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
# Excel：達標/未達標 上色（只輸出文字）
# =============================
def build_excel_bytes_pf(matrix_pf: pd.DataFrame, hour_cols: list[int]) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        matrix_pf.to_excel(writer, index=False, sheet_name="達標_矩陣")
    bio.seek(0)

    wb = load_workbook(bio)
    ws = wb.active

    fill_ok = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    fill_ng = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    base_cols = ["線別", "段數", "姓名", "開始時間"]
    min_col = len(base_cols) + 1
    max_col = len(base_cols) + len(hour_cols)

    for r in ws.iter_rows(min_row=2, min_col=min_col, max_col=max_col):
        for c in r:
            v = str(c.value).strip() if c.value is not None else ""
            if v == STATUS_PASS:
                c.fill = fill_ok
            elif v == STATUS_FAIL:
                c.fill = fill_ng

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# =============================
# 表格著色（前端 dataframe）
# =============================
def _style_pf(v):
    if v == STATUS_PASS:
        return "background-color: rgba(198,239,206,1); color: rgba(0,0,0,0.9); font-weight:700;"
    if v == STATUS_FAIL:
        return "background-color: rgba(255,199,206,1); color: rgba(0,0,0,0.9); font-weight:700;"
    return ""


def _kpi_counts(dist_df: pd.DataFrame):
    # dist_df columns: 小時, 狀態, count
    if dist_df is None or dist_df.empty:
        return 0, 0, None
    p = int(dist_df.loc[dist_df["狀態"] == STATUS_PASS, "count"].sum())
    f = int(dist_df.loc[dist_df["狀態"] == STATUS_FAIL, "count"].sum())
    rate = (p / (p + f) * 100.0) if (p + f) > 0 else None
    return p, f, rate


def _render_dist_chart(dist_df: pd.DataFrame, title: str):
    # dist_df columns: 小時, 狀態, count
    if dist_df is None or dist_df.empty:
        st.info("此區間沒有可呈現的 達標/未達標 分佈。")
        return

    chart = (
        alt.Chart(dist_df)
        .mark_bar()
        .encode(
            x=alt.X("小時:O", title="小時"),
            y=alt.Y("count:Q", title="段數數量", stack="zero"),
            color=alt.Color(
                "狀態:N",
                scale=alt.Scale(domain=[STATUS_PASS, STATUS_FAIL], range=["#2E7D32", "#C62828"]),
                legend=alt.Legend(title="狀態"),
            ),
            tooltip=[alt.Tooltip("小時:O"), alt.Tooltip("狀態:N"), alt.Tooltip("count:Q")],
        )
        .properties(title=title, height=220)
    )
    st.altair_chart(chart, use_container_width=True)


def main():
    st.set_page_config(page_title="大豐物流 - 出貨課｜各時段作業效率", page_icon="⏱️", layout="wide")
    if HAS_COMMON_UI:
        inject_logistics_theme()
        set_page("📦 出貨課", "⏱️ 29｜各時段作業效率")

    st.markdown("### ⏱️ 各時段作業效率（達標/未達標｜段1~段4 分佈）")

    # --- 固定人員開始時間表 ---
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
        # =========================================================
        # 1) 人員名單：LINEID + 第一段~第四段 => 段數=ZONEID(1~4)
        # =========================================================
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

        # ✅ 同一線別+段數只留一筆（避免合併展開）
        df_members = df_members.drop_duplicates(["線別", "段數"], keep="first").copy()

        # =========================================================
        # 2) 生產資料（去重後加權PCS）
        # =========================================================
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

        # 合併 + 去重（核心）
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

        # =========================================================
        # 3) 以「累計」判斷 達標/未達標（每人每小時）
        # =========================================================
        df["小時"] = df["PICKDATE"].dt.hour
        base_cols = ["線別", "段數", "姓名", "開始時間"]

        hourly = df.groupby(base_cols + ["小時"], as_index=False)["加權PCS"].sum()
        hourly = hourly.sort_values(base_cols + ["小時"])
        hourly["累計實際量"] = hourly.groupby(["線別", "段數", "姓名"])["加權PCS"].cumsum()

        cur_h, cur_m = now.hour, now.minute

        st_parts2 = hourly["開始時間"].astype(str).str.split(":", n=1, expand=True)
        s_h = pd.to_numeric(st_parts2[0], errors="coerce").fillna(8).astype(float)
        s_m = pd.to_numeric(st_parts2[1], errors="coerce").fillna(0).astype(float)
        h = hourly["小時"].astype(float)

        elapsed = np.where(
            h < cur_h,
            (h - s_h + 1.0) - (s_m / 60.0),
            np.where(
                h == cur_h,
                (h - s_h) + ((cur_m - s_m) / 60.0),
                np.nan
            )
        )

        target = np.maximum(0.01, elapsed) * float(target_hr)

        # ✅ 直接輸出「達標/未達標」
        status = np.where(
            np.isnan(elapsed),
            None,
            np.where(hourly["累計實際量"].values >= target, STATUS_PASS, STATUS_FAIL)
        )
        hourly["狀態"] = status

        # =========================================================
        # 4) 建「完整網格」：每線 × 段(1~4) × 每小時，都用 達標/未達標 顯示
        # =========================================================
        hour_cols = list(range(int(hour_min), int(cur_h) + 1))

        keys = df_members[base_cols].drop_duplicates().copy()
        if keys.empty:
            raise ValueError("人員名單 keys 為空，請確認名單檔格式。")

        grid = keys.assign(_k=1).merge(pd.DataFrame({"小時": hour_cols, "_k": 1}), on="_k").drop(columns=["_k"])
        grid = grid.merge(hourly[base_cols + ["小時", "狀態"]], on=base_cols + ["小時"], how="left")

        # ✅ 產出總矩陣：線別+段數+姓名+開始時間 + 每小時 達標/未達標
        matrix_pf = (
            grid.pivot(index=base_cols, columns="小時", values="狀態")
            .reset_index()
        )
        matrix_pf.columns = [int(c) if str(c).isdigit() else c for c in matrix_pf.columns]
        for hh in hour_cols:
            if hh not in matrix_pf.columns:
                matrix_pf[hh] = None
        matrix_pf = matrix_pf[base_cols + hour_cols]

        # =========================================================
        # 5) KPI 圖表：每線（段1~段4 達標/未達標 分佈） + 全作業線總和
        # =========================================================
        st.success("計算完成 ✅（呈現：達標/未達標｜段1~段4 分佈）")
        st.markdown("## 📊 KPI（每線：段1~段4 達標/未達標 分佈）")

        # dist：每線、每小時 達標/未達標 有幾段
        dist = (
            grid[grid["狀態"].isin([STATUS_PASS, STATUS_FAIL])]
            .groupby(["線別", "小時", "狀態"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values(["線別", "小時", "狀態"])
        )

        eff_hour = int(cur_h)

        lines = sorted(keys["線別"].dropna().unique().tolist())
        for line in lines:
            if HAS_COMMON_UI:
                card_open(f"📦 {line}")
            else:
                st.markdown(f"### 📦 {line}")

            # KPI：目前小時的 達標/未達標 段數（段1~段4）
            dist_now = dist[(dist["線別"] == line) & (dist["小時"] == eff_hour)]
            p, f, rate = _kpi_counts(dist_now)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("判斷小時", f"{eff_hour} 點")
            c2.metric("達標 段數", p)
            c3.metric("未達標 段數", f)
            c4.metric("達標 率", (f"{rate:.1f}%" if rate is not None else "—"))

            # 圖：每小時 達標/未達標 段數（0~4）
            dist_line = dist[dist["線別"] == line].copy()
            _render_dist_chart(dist_line, title=f"{line}｜每小時 達標/未達標 段數（段1~段4）")

            # ✅ 表：段1~段4 × 小時（顯示姓名）
            tbl = grid[grid["線別"] == line][["段數", "姓名", "小時", "狀態"]].copy()
            tbl["段數"] = pd.to_numeric(tbl["段數"], errors="coerce").astype("Int64")

            line_matrix = (
                tbl.pivot(index=["段數", "姓名"], columns="小時", values="狀態")
                .reset_index()
            )
            line_matrix.columns = [int(c) if str(c).isdigit() else c for c in line_matrix.columns]

            # 補齊小時欄
            for hh in hour_cols:
                if hh not in line_matrix.columns:
                    line_matrix[hh] = None

            # 排序：段數 1~4
            line_matrix = line_matrix.sort_values(["段數", "姓名"]).reset_index(drop=True)
            line_matrix = line_matrix[["段數", "姓名"] + hour_cols]

            st.caption("段1~段4 × 每小時：顯示『姓名』與『達標/未達標』（空白=無判斷/未到時段）")
            st.dataframe(line_matrix.style.applymap(_style_pf), use_container_width=True, height=240)

            if HAS_COMMON_UI:
                card_close()

        # 全作業線總和
        st.markdown("## 🧾 全作業線總和（段1~段4 達標/未達標 分佈）")
        dist_all = (
            grid[grid["狀態"].isin([STATUS_PASS, STATUS_FAIL])]
            .groupby(["小時", "狀態"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
            .sort_values(["小時", "狀態"])
        )

        dist_all_now = dist_all[dist_all["小時"] == eff_hour]
        p_all, f_all, rate_all = _kpi_counts(dist_all_now)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("判斷小時", f"{eff_hour} 點")
        c2.metric("達標 段數", p_all)
        c3.metric("未達標 段數", f_all)
        c4.metric("達標 率", (f"{rate_all:.1f}%" if rate_all is not None else "—"))

        _render_dist_chart(dist_all, title="全作業線｜每小時 達標/未達標 段數（所有線別段1~段4）")

        # =========================================================
        # 6) 下載 Excel（達標/未達標 矩陣）
        # =========================================================
        st.markdown("## ⬇️ 下載")
        xlsx_bytes = build_excel_bytes_pf(matrix_pf, hour_cols)
        filename = f"產能時段_達標矩陣_{datetime.now(TPE).strftime('%H%M')}.xlsx"
        st.download_button(
            "⬇️ 下載 Excel（達標/未達標 矩陣，上色）",
            data=xlsx_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        # （可選）總矩陣預覽
        with st.expander("📋 展開查看：全體 達標/未達標 矩陣（含姓名）", expanded=False):
            st.dataframe(matrix_pf.style.applymap(_style_pf), use_container_width=True, height=520)

    except Exception as e:
        st.error(f"發生錯誤：{e}")


if __name__ == "__main__":
    main()
