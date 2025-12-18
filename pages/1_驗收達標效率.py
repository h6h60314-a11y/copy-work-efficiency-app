import streamlit as st
import pandas as pd
import datetime as dt
import re

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


# ======================
# Time parser（時間必須自行輸入，預設空白）
# ======================
def _parse_time(text: str):
    if not text:
        return None
    text = text.strip()

    # HHMM → HH:MM
    if re.fullmatch(r"\d{3,4}", text):
        text = text.zfill(4)
        text = f"{text[:2]}:{text[2:]}"

    try:
        return dt.datetime.strptime(text, "%H:%M").time()
    except ValueError:
        return None


# ======================
# Sidebar params
# ======================
def render_params():
    if "skip_rules" not in st.session_state:
        st.session_state.skip_rules = []

    st.caption("排除規則：時間必須自行輸入；未啟用時間即視為全天（不限制時間）。")

    user = st.text_input("記錄輸入人（可空白＝全員）", value="")
    use_time = st.checkbox("啟用時間區間條件（自行輸入）", value=False)

    t_start = None
    t_end = None
    if use_time:
        c1, c2 = st.columns(2)
        with c1:
            t_start_txt = st.text_input("開始時間（HH:MM）", placeholder="例如 10:30")
        with c2:
            t_end_txt = st.text_input("結束時間（HH:MM）", placeholder="例如 15:45")
        t_start = _parse_time(t_start_txt)
        t_end = _parse_time(t_end_txt)

    c_add, c_clear = st.columns(2)
    with c_add:
        if st.button("➕ 加入排除規則"):
            if use_time:
                if t_start is None or t_end is None:
                    st.error("請自行輸入開始與結束時間（HH:MM）")
                else:
                    st.session_state.skip_rules.append(
                        {"user": user.strip(), "t_start": t_start, "t_end": t_end}
                    )
            else:
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

    top_n = st.number_input("排行顯示人數", 10, 100, 30, step=10)
    return {"skip_rules": st.session_state.skip_rules, "top_n": int(top_n)}


# ======================
# helpers
# ======================
def _fmt(x, n=2):
    try:
        if x is None:
            return "—"
        return f"{float(x):,.{n}f}"
    except Exception:
        return "—"


def _fmt_i(x):
    try:
        if x is None:
            return "—"
        return f"{int(x):,}"
    except Exception:
        return "—"


def _build_kpis(df: pd.DataFrame, target: float):
    if df is None or df.empty:
        return dict(p=0, c=None, h=None, e=None, r=None)

    total_cnt = df["筆數"].sum() if "筆數" in df.columns else None
    total_hours = df["總工時"].sum() if "總工時" in df.columns else None
    avg_eff = df["效率"].mean() if "效率" in df.columns else None
    pass_rate = f"{(df['效率'] >= target).mean():.0%}" if "效率" in df.columns and len(df) else None

    return dict(p=len(df), c=total_cnt, h=total_hours, e=avg_eff, r=pass_rate)


def _seg(df: pd.DataFrame, key: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if "時段" not in df.columns:
        return df.copy()
    return df[df["時段"].astype(str).str.contains(key, na=False)].copy()


def _pick_col(df: pd.DataFrame, candidates: list[str], fallback_idx: int = 0) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    return df.columns[fallback_idx]


def render_segment_panel(title: str, df: pd.DataFrame, idle_df: pd.DataFrame, target: float, top_n: int):
    # KPI
    k = _build_kpis(df, target)
    card_open(f"{title} KPI")
    render_kpis(
        [
            KPI("人數", _fmt_i(k["p"]), variant="purple"),
            KPI("總筆數", _fmt_i(k["c"]), variant="blue"),
            KPI("總工時", _fmt(k["h"]), variant="cyan"),
            KPI("平均效率", _fmt(k["e"]), variant="teal"),
            KPI("達標率", k["r"] or "—", variant="gray"),
        ]
    )
    card_close()

    if df is None or df.empty:
        st.info(f"{title} 無資料（可能被過濾或排除）。")
        return

    x_col = _pick_col(df, ["姓名", "人員", "員工姓名"], 0)
    y_col = _pick_col(df, ["效率"], -1)

    card_open(f"📊 {title} 效率排行（Top {top_n}）")
    bar_topN(
        df,
        x_col=x_col,
        y_col=y_col,
        hover_cols=[c for c in ["記錄輸入人", "筆數", "總工時", "空窗總分鐘"] if c in df.columns],
        top_n=top_n,
        target=target,
        title="",
    )
    card_close()

    table_block(
        summary_title=f"📄 {title} 彙總",
        summary_df=df,
        detail_title=f"{title} 空窗明細（收合）",
        detail_df=idle_df if isinstance(idle_df, pd.DataFrame) else pd.DataFrame(),
        detail_expanded=False,
    )


# ======================
# main
# ======================
def main():
    set_page("驗收達標效率", icon="✅")

    with st.sidebar:
        st.header("⚙️ 參數設定")
        params = render_params()

    # Upload
    card_open("📤 上傳資料")
    uploaded = st.file_uploader(
        "上傳驗收資料",
        type=["xlsx", "xls", "xlsm", "csv", "txt"],
        label_visibility="collapsed",
    )
    run = st.button("🚀 開始計算", type="primary", disabled=uploaded is None)
    card_close()

    if not run:
        st.info("請先上傳檔案")
        return

    with st.spinner("計算中..."):
        result = run_qc_efficiency(uploaded.getvalue(), uploaded.name, params["skip_rules"])

    ampm_df = result.get("ampm_df", pd.DataFrame())
    idle_df = result.get("idle_df", pd.DataFrame())
    target = float(result.get("target_eff", 20.0))
    top_n = int(params.get("top_n", 30))

    if not isinstance(ampm_df, pd.DataFrame) or ampm_df.empty or "時段" not in ampm_df.columns:
        st.error("AM/PM 資料缺少『時段』欄位，無法分上午/下午。")
        return

    am = _seg(ampm_df, "上午")
    pm = _seg(ampm_df, "下午")

    # idle_df 通常沒有時段，左右兩欄先用同一份避免出錯
    idle_left = idle_df.copy() if isinstance(idle_df, pd.DataFrame) else pd.DataFrame()
    idle_right = idle_df.copy() if isinstance(idle_df, pd.DataFrame) else pd.DataFrame()

    # ===== 左右雙欄：上午｜下午 =====
    col_left, col_right = st.columns(2)

    with col_left:
        render_segment_panel("🌓 上午", am, idle_left, target, top_n)

    with col_right:
        render_segment_panel("🌙 下午", pm, idle_right, target, top_n)

    # Export
    if result.get("xlsx_bytes"):
        card_open("⬇️ 匯出（含 AM/PM）")
        download_excel(result["xlsx_bytes"], result.get("xlsx_name", "驗收達標_含空窗_AMPM.xlsx"))
        card_close()


if __name__ == "__main__":
    main()
