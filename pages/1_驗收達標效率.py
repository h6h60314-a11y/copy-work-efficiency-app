import streamlit as st
import pandas as pd

from common_ui import (
    set_page,
    KPI,
    render_kpis,
    bar_topN,
    table_block,
    download_excel,
    card_open,
    card_close,
)

from qc_core import run_qc_efficiency


def render_params():
    if "skip_rules" not in st.session_state:
        st.session_state.skip_rules = []

    st.caption("排除規則：可選擇『全天』或『指定時間區間』排除；未勾選時間即視為全天。")

    user = st.text_input("記錄輸入人（可空白＝全員）", value="")

    # ✅ 關鍵：預設不啟用時間，完全不顯示 time_input（避免預設時間）
    use_time = st.checkbox("啟用時間區間條件（自行輸入）", value=False)

    t_start = None
    t_end = None
    if use_time:
        c1, c2 = st.columns(2)
        with c1:
            t_start = st.time_input("開始時間")
        with c2:
            t_end = st.time_input("結束時間")

    c_add, c_clear = st.columns(2)
    with c_add:
        if st.button("➕ 加入排除規則"):
            if use_time:
                if t_start is None or t_end is None:
                    st.error("請完整輸入開始與結束時間。")
                elif t_end < t_start:
                    st.error("結束時間需大於等於開始時間。")
                else:
                    st.session_state.skip_rules.append(
                        {"user": user.strip(), "t_start": t_start, "t_end": t_end}
                    )
            else:
                # 全天排除：t_start/t_end 以 None 表示
                st.session_state.skip_rules.append(
                    {"user": user.strip(), "t_start": None, "t_end": None}
                )

    with c_clear:
        if st.button("🧹 清空排除規則"):
            st.session_state.skip_rules = []

    if st.session_state.skip_rules:
        st.dataframe(
            pd.DataFrame(st.session_state.skip_rules),
            use_container_width=True,
            hide_index=True,
        )

    top_n = st.number_input("排行顯示人數", min_value=10, max_value=100, value=30, step=10)
    return {"skip_rules": st.session_state.skip_rules, "top_n": int(top_n)}


def _fmt_num(x, digits=2):
    try:
        if x is None:
            return "—"
        return f"{float(x):,.{digits}f}"
    except Exception:
        return "—"


def _fmt_int(x):
    try:
        if x is None:
            return "—"
        return f"{int(x):,}"
    except Exception:
        return "—"


def _build_kpis_from_df(df: pd.DataFrame, target: float):
    if df is None or df.empty:
        return dict(people=0, total_cnt=None, total_hours=None, avg_eff=None, pass_rate=None)

    people = len(df)
    total_cnt = df["筆數"].sum() if "筆數" in df.columns else None
    total_hours = df["總工時"].sum() if "總工時" in df.columns else None
    avg_eff = df["效率"].mean() if "效率" in df.columns else None

    pass_rate = None
    if "效率" in df.columns and len(df) > 0:
        pass_rate = f"{(df['效率'] >= target).mean():.0%}"

    return dict(
        people=people,
        total_cnt=total_cnt,
        total_hours=total_hours,
        avg_eff=avg_eff,
        pass_rate=pass_rate,
    )


def _filter_segment(df: pd.DataFrame, segment: str) -> pd.DataFrame:
    """segment: '上午' or '下午'"""
    if df is None or df.empty:
        return df
    if "時段" in df.columns:
        return df[df["時段"].astype(str).str.contains(segment, na=False)].copy()
    return df.copy()


def _safe_col(df: pd.DataFrame, candidates: list[str], fallback_index: int = 0) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    return df.columns[fallback_index]


def main():
    set_page("驗收達標效率", icon="✅")

    # Sidebar：參數
    with st.sidebar:
        st.header("⚙️ 參數設定")
        params = render_params()

    # 上傳（置中卡片）
    card_open("📤 上傳資料檔案")
    st.caption("請上傳驗收資料（Excel / CSV）。上傳後按『開始計算』即可產出上午/下午 KPI、圖表與下載報表。")
    uploaded = st.file_uploader(
        "請上傳驗收資料",
        type=["xlsx", "xlsm", "xls", "csv", "txt"],
        label_visibility="collapsed",
    )
    run_clicked = st.button("🚀 開始計算", type="primary", disabled=(uploaded is None))
    card_close()

    if not run_clicked:
        st.info("請先上傳檔案，再點『開始計算』。")
        return

    with st.spinner("計算中..."):
        result = run_qc_efficiency(uploaded.getvalue(), uploaded.name, params["skip_rules"])

    # qc_core 回傳（你已在 qc_core 做一致過濾：姓名+記錄輸入人 + 排除羅仲宇）
    full_df = result.get("full_df", pd.DataFrame())
    ampm_df = result.get("ampm_df", pd.DataFrame())
    idle_df = result.get("idle_df", pd.DataFrame())

    target = float(result.get("target_eff", 20.0))
    top_n = int(params.get("top_n", 30))

    # 必須要能用「時段」拆 AM/PM
    if not (isinstance(ampm_df, pd.DataFrame) and (not ampm_df.empty) and ("時段" in ampm_df.columns)):
        st.warning("目前回傳的 AM/PM 資料缺少「時段」欄位，無法分上午/下午顯示。請確認 qc_core 是否有產出 ampm_df['時段']。")
        card_open("📄 全體彙總（Fallback）")
        st.dataframe(full_df, use_container_width=True)
        card_close()

        if result.get("xlsx_bytes"):
            card_open("⬇️ 匯出")
            download_excel(result["xlsx_bytes"], filename=result.get("xlsx_name", "驗收達標_含空窗_AMPM.xlsx"))
            card_close()
        return

    # 分段：上午 / 下午
    am_df = _filter_segment(ampm_df, "上午")
    pm_df = _filter_segment(ampm_df, "下午")

    am_idle = _filter_segment(idle_df, "上午")
    pm_idle = _filter_segment(idle_df, "下午")

    tab_am, tab_pm = st.tabs(["🌓 上午", "🌙 下午"])

    def render_segment(segment_name: str, seg_df: pd.DataFrame, seg_idle: pd.DataFrame):
        # KPI
        k = _build_kpis_from_df(seg_df, target)
        card_open(f"{segment_name} KPI")
        render_kpis(
            [
                KPI("人數", _fmt_int(k["people"]), variant="purple"),
                KPI("總筆數", _fmt_int(k["total_cnt"]), variant="blue"),
                KPI("總工時", _fmt_num(k["total_hours"]), variant="cyan"),
                KPI("平均效率", _fmt_num(k["avg_eff"]), variant="teal"),
                KPI("達標率", k["pass_rate"] or "—", variant="gray"),
            ]
        )
        card_close()

        if seg_df is None or seg_df.empty:
            st.info(f"{segment_name} 沒有可顯示的資料（可能都被過濾或排除）。")
            return

        left, right = st.columns([1.15, 1])

        with left:
            card_open(f"📊 {segment_name} 效率排行（Top {top_n}）")
            x_col = _safe_col(seg_df, ["姓名", "人員", "員工姓名"], 0)
            y_col = _safe_col(seg_df, ["效率"], -1)
            bar_topN(
                seg_df,
                x_col=x_col,
                y_col=y_col,
                hover_cols=[c for c in ["記錄輸入人", "筆數", "總工時", "空窗總分鐘"] if c in seg_df.columns],
                top_n=top_n,
                target=target,
                title="",
            )
            card_close()

        with right:
            if "空窗總分鐘" in seg_df.columns:
                card_open(f"⏱️ {segment_name} 空窗總分鐘排行（Top {top_n}）")
                x2 = _safe_col(seg_df, ["姓名", "人員", "員工姓名"], 0)
                bar_topN(
                    seg_df.sort_values("空窗總分鐘", ascending=False),
                    x_col=x2,
                    y_col="空窗總分鐘",
                    hover_cols=[c for c in ["效率", "空窗筆數", "記錄輸入人"] if c in seg_df.columns],
                    top_n=top_n,
                    target=-1.0,
                    title="",
                )
                card_close()
            else:
                card_open(f"ℹ️ {segment_name} 空窗")
                st.caption("此段資料沒有「空窗總分鐘」欄位，改以下方『空窗明細』呈現。")
                card_close()

        # 表格：彙總 + 空窗明細
        table_block(
            summary_title=f"📄 {segment_name} 彙總表",
            summary_df=seg_df if isinstance(seg_df, pd.DataFrame) else pd.DataFrame(),
            detail_title=f"{segment_name} 空窗明細（收合）",
            detail_df=seg_idle if isinstance(seg_idle, pd.DataFrame) else pd.DataFrame(),
            detail_expanded=False,
        )

    with tab_am:
        render_segment("上午", am_df, am_idle)

    with tab_pm:
        render_segment("下午", pm_df, pm_idle)

    # 匯出（同一份 Excel，內含 AM/PM）
    if result.get("xlsx_bytes"):
        card_open("⬇️ 匯出（含 AM/PM）")
        download_excel(result["xlsx_bytes"], filename=result.get("xlsx_name", "驗收達標_含空窗_AMPM.xlsx"))
        card_close()


if __name__ == "__main__":
    main()
