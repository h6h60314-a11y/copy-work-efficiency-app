import io
import re
import datetime as dt
from dataclasses import dataclass
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
    sidebar_controls,
    download_excel_card,
)

# =========================================================
# 來源：你提供的 morning 版腳本核心（Streamlit 化 + 加下午）
# - 支援中文 上午/下午 + 24h + Excel 浮點序列
# - 空窗門檻、排除區間
# =========================================================

MORNING_END = dt.time(12, 30, 0)
AFTERNOON_START = dt.time(13, 30, 0)

DEFAULT_IDLE_THRESHOLD_MIN = 10

# 你的預設揀貨人資料（原檔很長，我這裡保留完整貼法）
# ✅ 你可以直接把你那份 preset_picker_info 全段貼進來替換（我先保留你原本的結構）
preset_picker_info = {
    # === 範例（你可保留/替換成你原本完整那份）===
    "20200812002": {"姓名": "彭慈暉", "起始時間": "7:05:00", "區域": "低空"},
    "20210104001": {"姓名": "楊承珉", "起始時間": "7:05:00", "區域": "低空"},
    # === 建議：把你原檔的 preset_picker_info 整段貼進來（最完整）===
}

default_start_time_str = "08:05:00"


def parse_tw_datetime(series: pd.Series) -> pd.Series:
    """
    支援：
      1) 2025/06/26 上午 09:35:01（中文 AM/PM）
      2) 2025/6/30 10:37:51（24h）
      3) 45549.435694444（Excel 浮點序列）
    """
    if pd.api.types.is_datetime64_any_dtype(series):
        return series

    s = series.astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    num_mask = s.str.match(r"^\d+(\.\d+)?$")
    if num_mask.any():
        out.loc[num_mask] = pd.to_datetime(
            s[num_mask].astype(float), unit="d", origin="1899-12-30"
        )

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


def read_excel_any_bytes(filename: str, content: bytes) -> pd.DataFrame:
    ext = (filename.split(".")[-1] or "").lower()
    if ext in ("xlsx", "xlsm"):
        return pd.read_excel(io.BytesIO(content), engine="openpyxl", dtype={"揀貨完成時間": str})
    if ext == "xls":
        return pd.read_excel(io.BytesIO(content), engine="xlrd", dtype={"揀貨完成時間": str})
    if ext == "csv":
        for enc in ("utf-8-sig", "cp950", "big5"):
            try:
                return pd.read_csv(io.BytesIO(content), encoding=enc)
            except Exception:
                continue
        raise ValueError("CSV 讀取失敗（請確認編碼）")
    raise ValueError("不支援的檔案格式（xlsx/xls/csv）")


def _adapt_exclude_windows_to_time_ranges(exclude_windows) -> List[Tuple[dt.time, dt.time]]:
    """
    common_ui.sidebar_controls() exclude_windows:
      [{"start":"HH:MM","end":"HH:MM","data_entry":""}, ...]
    -> [(time, time), ...]
    """
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


def _clip_segments(a: pd.Timestamp, b: pd.Timestamp, ex_ranges: List[Tuple[dt.time, dt.time]]) -> List[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    把 [a,b] 切掉與排除區間重疊的部分，回傳剩餘片段
    """
    if a >= b or not ex_ranges:
        return [(a, b)]

    segs = [(a, b)]
    for s_t, e_t in ex_ranges:
        ex_s = pd.Timestamp.combine(a.date(), s_t)
        ex_e = pd.Timestamp.combine(a.date(), e_t)
        new = []
        for x, y in segs:
            if y <= ex_s or x >= ex_e:
                new.append((x, y))
            else:
                if x < ex_s:
                    new.append((x, ex_s))
                if y > ex_e:
                    new.append((ex_e, y))
        segs = [(x, y) for x, y in new if x < y]
    return segs


def _sum_minutes_of_segments(segs: List[Tuple[pd.Timestamp, pd.Timestamp]]) -> float:
    return round(sum((b - a).total_seconds() for a, b in segs) / 60.0, 2)


def _calc_idle_minutes(times: List[pd.Timestamp], ex_ranges: List[Tuple[dt.time, dt.time]], threshold_min: int) -> Tuple[float, str]:
    if len(times) < 2:
        return 0.0, ""

    times = sorted(times)
    idle_segs: List[Tuple[pd.Timestamp, pd.Timestamp]] = []
    for i in range(1, len(times)):
        prev, cur = times[i - 1], times[i]
        if cur <= prev:
            continue
        for a, b in _clip_segments(prev, cur, ex_ranges):
            if (b - a) >= pd.Timedelta(minutes=threshold_min):
                idle_segs.append((a, b))

    idle_min = round(sum((b - a).total_seconds() for a, b in idle_segs) / 60.0, 2)
    idle_txt = "; ".join(f"{a.time().strftime('%H:%M:%S')} ~ {b.time().strftime('%H:%M:%S')}" for a, b in idle_segs)
    return idle_min, idle_txt


def _eff(records: int, minutes: float) -> float:
    return round((records / minutes * 60.0), 2) if minutes and minutes > 0 else 0.0


def _get_region_threshold(region: str, low_target: float, high_target: float) -> float:
    region = (region or "低空").strip()
    return float(high_target) if region == "高空" else float(low_target)


def build_shift_stats(
    df: pd.DataFrame,
    shift: str,
    ex_ranges: List[Tuple[dt.time, dt.time]],
    idle_threshold_min: int,
    morning_end: dt.time = MORNING_END,
    afternoon_start: dt.time = AFTERNOON_START,
) -> pd.DataFrame:
    """
    shift: "AM" or "PM"
    必要欄位：揀貨人、揀貨完成時間、儲位、成箱箱號(可無)、數量(可無)
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # 成箱箱號：若存在就移除成箱（你原本規則：成箱箱號=="" 才留）
    if "成箱箱號" in df.columns:
        df["成箱箱號"] = df["成箱箱號"].astype(str).str.strip()
        df = df[df["成箱箱號"] == ""]

    # 時間解析
    if "揀貨完成時間" not in df.columns or "揀貨人" not in df.columns:
        return pd.DataFrame()

    df["揀貨完成時間"] = parse_tw_datetime(df["揀貨完成時間"])
    df = df.dropna(subset=["揀貨完成時間"]).copy()
    if df.empty:
        return pd.DataFrame()

    df["日期"] = df["揀貨完成時間"].dt.date

    # AM / PM 分段
    if shift == "AM":
        sdf = df[df["揀貨完成時間"].dt.time <= morning_end].copy()
    else:
        sdf = df[df["揀貨完成時間"].dt.time > morning_end].copy()

    if sdf.empty:
        return pd.DataFrame()

    stats = []
    for (date, picker), g in sdf.groupby(["日期", "揀貨人"], dropna=False):
        g = g.sort_values("揀貨完成時間")
        times = list(g["揀貨完成時間"])

        if not times:
            continue

        # 區域與姓名（沿用 preset）
        p = str(picker).strip()
        preset = preset_picker_info.get(p, {})
        region = (preset.get("區域") or "低空").strip()
        name = (preset.get("姓名") or p).strip()

        # 工作區間：AM 用 preset 起始時間；PM 用固定 13:30
        first = times[0]
        last = times[-1]

        if shift == "AM":
            cfg_str = preset.get("起始時間", default_start_time_str)
            try:
                cfg_t = dt.datetime.strptime(cfg_str, "%H:%M:%S").time()
            except Exception:
                cfg_t = dt.time(8, 5, 0)

            cfg_start = pd.Timestamp.combine(first.date(), cfg_t)
            end_cap = pd.Timestamp.combine(first.date(), morning_end)

            effective_start = min(first, cfg_start)
            # 若當天有 PM 紀錄，AM 強制結束到 12:30；否則到最後一筆（<=12:30）
            has_pm = ((df["日期"] == date) & (df["揀貨人"] == picker) & (df["揀貨完成時間"].dt.time > morning_end)).any()
            effective_end = end_cap if has_pm else min(last, end_cap)

        else:
            start_cap = pd.Timestamp.combine(first.date(), afternoon_start)
            effective_start = min(first, start_cap)
            effective_end = last  # PM 到最後一筆

        if effective_end <= effective_start:
            continue

        # 總分鐘：扣掉排除區間
        segs = _clip_segments(effective_start, effective_end, ex_ranges)
        total_minutes = _sum_minutes_of_segments(segs)

        records = int(len(times))
        eff = _eff(records, total_minutes)

        # 空窗（扣除排除區間後判斷）
        idle_min, idle_txt = _calc_idle_minutes(times, ex_ranges, idle_threshold_min)

        # 儲位區域(前3碼 unique)
        storage_area = ""
        if "儲位" in g.columns:
            prefixes = []
            for loc in g["儲位"].astype(str).tolist():
                pre = str(loc)[:3]
                if pre and pre not in prefixes:
                    prefixes.append(pre)
            storage_area = ",".join(prefixes)

        stats.append({
            "班別": "上午" if shift == "AM" else "下午",
            "日期": date,
            "區域": region,
            "揀貨人": p,
            "姓名": name,
            "筆數": records,
            "工作區間": f"{effective_start.time().strftime('%H:%M:%S')} ~ {effective_end.time().strftime('%H:%M:%S')}",
            "總分鐘": float(total_minutes),
            "效率": float(eff),
            "空窗分鐘": float(idle_min),
            "儲位區域": storage_area,
            "空窗時間段": idle_txt,
        })

    out = pd.DataFrame(stats)
    if out.empty:
        return out

    out["區域"] = pd.Categorical(out["區域"], categories=["低空", "高空"], ordered=True)
    out = out.sort_values(["日期", "區域", "揀貨人"]).reset_index(drop=True)
    return out


def _style_pass_fail(df: pd.DataFrame, low_target: float, high_target: float):
    if df is None or df.empty:
        return df

    def row_style(r):
        th = _get_region_threshold(str(r.get("區域", "")), low_target, high_target)
        ok = float(r.get("效率", 0)) >= th
        # 未達標：整列淡紅
        return ["background-color: #FFC7CE" if not ok else "" for _ in r.index]

    return df.style.apply(row_style, axis=1)


def build_excel_bytes(
    am_df: pd.DataFrame,
    pm_df: pd.DataFrame,
    low_target: float,
    high_target: float,
) -> bytes:
    import openpyxl
    from openpyxl.styles import PatternFill
    from openpyxl.utils.dataframe import dataframe_to_rows

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    green = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
    red = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

    def add_sheet(name: str, df: pd.DataFrame):
        ws = wb.create_sheet(name)
        if df is None or df.empty:
            ws["A1"] = "無資料"
            return

        for r in dataframe_to_rows(df, index=False, header=True):
            ws.append(r)

        # 找「效率」「區域」欄
        headers = [str(c.value).strip() for c in ws[1]]
        try:
            eff_idx = headers.index("效率") + 1
            reg_idx = headers.index("區域") + 1
        except Exception:
            return

        for row in range(2, ws.max_row + 1):
            reg = str(ws.cell(row=row, column=reg_idx).value or "").strip()
            th = _get_region_threshold(reg, low_target, high_target)
            v = ws.cell(row=row, column=eff_idx).value
            try:
                val = float(v)
            except Exception:
                continue

            fill = green if val >= th else red
            for col in range(1, ws.max_column + 1):
                ws.cell(row=row, column=col).fill = fill

        # 欄寬簡單調整
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col[:200]:
                if cell.value is None:
                    continue
                max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

    add_sheet("上午達標", am_df)
    add_sheet("下午達標", pm_df)

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def main():
    inject_logistics_theme()
    set_page("總揀達標", icon="🧺", subtitle="總揀｜上午達標/下午達標｜效率門檻（低空/高空）｜匯出報表")

    # ✅ 保留結果（按匯出不會消失）
    if "pick_last" not in st.session_state:
        st.session_state.pick_last = None

    # Sidebar：共用控制（TopN + 排除區間手打 HH:MM）
    controls = sidebar_controls(default_top_n=30, enable_exclude_windows=True, state_key_prefix="pick")
    top_n = int(controls["top_n"])
    ex_ranges = _adapt_exclude_windows_to_time_ranges(controls.get("exclude_windows", []))

    with st.sidebar:
        st.markdown("---")
        st.subheader("🎯 達標門檻")
        low_target = st.number_input("低空達標（效率 ≥）", min_value=1.0, max_value=999.0, value=48.0, step=1.0)
        high_target = st.number_input("高空達標（效率 ≥）", min_value=1.0, max_value=999.0, value=20.0, step=1.0)

        st.markdown("---")
        idle_threshold_min = st.number_input("空窗門檻（分鐘 ≥）", min_value=1, max_value=120, value=DEFAULT_IDLE_THRESHOLD_MIN, step=1)

    # 上傳
    card_open("📤 上傳總揀原始資料")
    uploaded = st.file_uploader(
        "上傳總揀原始資料（需包含：揀貨人、揀貨完成時間；建議包含：儲位、成箱箱號）",
        type=["xlsx", "xls", "csv"],
        label_visibility="collapsed",
    )
    run_clicked = st.button("🚀 產出 KPI", type="primary", disabled=uploaded is None)
    card_close()

    if run_clicked:
        with st.spinner("計算中，請稍候..."):
            base_df = read_excel_any_bytes(uploaded.name, uploaded.getvalue())

            am_df = build_shift_stats(
                base_df,
                shift="AM",
                ex_ranges=ex_ranges,
                idle_threshold_min=int(idle_threshold_min),
            )
            pm_df = build_shift_stats(
                base_df,
                shift="PM",
                ex_ranges=ex_ranges,
                idle_threshold_min=int(idle_threshold_min),
            )

            xlsx_bytes = build_excel_bytes(am_df, pm_df, float(low_target), float(high_target))
            xlsx_name = f"{uploaded.name.rsplit('.', 1)[0]}_總揀達標_上午下午.xlsx"

            st.session_state.pick_last = {
                "am_df": am_df,
                "pm_df": pm_df,
                "xlsx_bytes": xlsx_bytes,
                "xlsx_name": xlsx_name,
                "low_target": float(low_target),
                "high_target": float(high_target),
            }

    last = st.session_state.pick_last
    if not last:
        st.info("請先上傳資料並點選「🚀 產出 KPI」")
        return

    am_df = last["am_df"]
    pm_df = last["pm_df"]
    low_target = float(last["low_target"])
    high_target = float(last["high_target"])

    # KPI：上午 / 下午
    c1, c2 = st.columns(2)

    def kpi_block(title: str, df: pd.DataFrame):
        if df is None or df.empty:
            card_open(title)
            st.info("無資料")
            card_close()
            return

        # 以「人」為單位看達標（同一人同一天多筆已是彙總筆數）
        people = int(df["揀貨人"].nunique()) if "揀貨人" in df.columns else int(len(df))
        # 達標：依區域不同門檻
        met = 0
        for _, r in df.drop_duplicates(["日期", "揀貨人"]).iterrows():
            th = _get_region_threshold(str(r.get("區域", "")), low_target, high_target)
            if float(r.get("效率", 0)) >= th:
                met += 1
        rate = (met / people) if people > 0 else 0.0

        card_open(title)
        render_kpis(
            [
                KPI("人數", f"{people:,}"),
                KPI("達標人數", f"{met:,}"),
                KPI("達標率", f"{rate:.1%}"),
                KPI("門檻", f"低空≥{int(low_target)} / 高空≥{int(high_target)}"),
            ],
            cols=4,
        )
        card_close()

    with c1:
        kpi_block("🌓 上午達標 KPI", am_df)

    with c2:
        kpi_block("🌙 下午達標 KPI", pm_df)

    # 排行：用「當日效率」排行（可再依日期切，你若要加我也能加）
    def top_rank(df: pd.DataFrame, title: str):
        card_open(title)
        if df is None or df.empty:
            st.info("無排行資料")
            card_close()
            return

        # 做一份用於排行的表：姓名顯示
        rank = df.copy()
        rank["顯示"] = rank["姓名"].where(rank["姓名"].astype(str).str.len() > 0, rank["揀貨人"].astype(str))
        rank = rank.sort_values("效率", ascending=False).head(int(top_n))

        # 因低空/高空門檻不同，排行分兩張更直覺
        left, right = st.columns(2)

        with left:
            sub = rank[rank["區域"] == "低空"].copy()
            st.caption(f"低空 Top {top_n}（門檻≥{int(low_target)}）")
            if sub.empty:
                st.info("低空無資料")
            else:
                try:
                    import altair as alt  # type: ignore
                    sub["達標"] = sub["效率"] >= float(low_target)
                    chart = (
                        alt.Chart(sub)
                        .mark_bar()
                        .encode(
                            x=alt.X("效率:Q", title="效率"),
                            y=alt.Y("顯示:N", sort="-x", title=""),
                            color=alt.condition(
                                alt.datum.達標,
                                alt.value("#0B84F3"),
                                alt.value("#D62728"),
                            ),
                            tooltip=["顯示", "效率", "筆數", "總分鐘", "工作區間", "空窗分鐘"],
                        )
                        .properties(height=min(520, 28 * max(6, len(sub))))
                    )
                    rule = alt.Chart(pd.DataFrame({"t": [float(low_target)]})).mark_rule(strokeDash=[6, 4]).encode(x="t:Q")
                    st.altair_chart(alt.layer(chart, rule), use_container_width=True)
                except Exception:
                    st.dataframe(sub, use_container_width=True, hide_index=True)

        with right:
            sub = rank[rank["區域"] == "高空"].copy()
            st.caption(f"高空 Top {top_n}（門檻≥{int(high_target)}）")
            if sub.empty:
                st.info("高空無資料")
            else:
                try:
                    import altair as alt  # type: ignore
                    sub["達標"] = sub["效率"] >= float(high_target)
                    chart = (
                        alt.Chart(sub)
                        .mark_bar()
                        .encode(
                            x=alt.X("效率:Q", title="效率"),
                            y=alt.Y("顯示:N", sort="-x", title=""),
                            color=alt.condition(
                                alt.datum.達標,
                                alt.value("#0B84F3"),
                                alt.value("#D62728"),
                            ),
                            tooltip=["顯示", "效率", "筆數", "總分鐘", "工作區間", "空窗分鐘"],
                        )
                        .properties(height=min(520, 28 * max(6, len(sub))))
                    )
                    rule = alt.Chart(pd.DataFrame({"t": [float(high_target)]})).mark_rule(strokeDash=[6, 4]).encode(x="t:Q")
                    st.altair_chart(alt.layer(chart, rule), use_container_width=True)
                except Exception:
                    st.dataframe(sub, use_container_width=True, hide_index=True)

        card_close()

    top_rank(am_df, f"🌓 上午效率排行（Top {top_n}）")
    top_rank(pm_df, f"🌙 下午效率排行（Top {top_n}）")

    # KPI 表（未達標整列紅）
    tab1, tab2 = st.tabs(["上午達標明細", "下午達標明細"])
    with tab1:
        if am_df is None or am_df.empty:
            st.info("無資料")
        else:
            st.dataframe(_style_pass_fail(am_df, low_target, high_target), use_container_width=True, hide_index=True)
    with tab2:
        if pm_df is None or pm_df.empty:
            st.info("無資料")
        else:
            st.dataframe(_style_pass_fail(pm_df, low_target, high_target), use_container_width=True, hide_index=True)

    # ✅ 匯出：一行=按鈕，按了 KPI 仍保留
    if last.get("xlsx_bytes"):
        download_excel_card(
            last["xlsx_bytes"],
            last.get("xlsx_name", "總揀達標_上午下午.xlsx"),
            label="⬇️ 匯出 總揀達標 報表（上午/下午）",
        )


if __name__ == "__main__":
    main()
