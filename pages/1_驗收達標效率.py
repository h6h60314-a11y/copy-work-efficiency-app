import streamlit as st
import pandas as pd

from common_ui import (
    set_page,
    sidebar_uploader_and_actions,
    KPI,
    render_kpis,
    bar_topN,
    pivot_am_pm,
    table_block,
    download_excel,
)

from qc_core import run_qc_efficiency


def render_params():
    """Sidebar 參數：排除規則 + TopN"""
    if "skip_rules" not in st.session_state:
        st.session_state.skip_rules = []

    st.caption("排除規則：該人(或全員)在此時間區間的紀錄不參與統計，且會從總分鐘/空窗扣除。")
    user = st.text_input("記錄輸入人（可空白＝全員）", value="")
    t1 = st.time_input("開始時間")
    t2 = st.time_input("結束時間")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("➕ 加入規則"):
            if t2 < t1:
                st.error("結束時間需 >= 開始時間")
            else:
                st.session_state.skip_rules.append({"user": user.strip(), "t_start": t1, "t_end": t2})
    with c2:
        if st.button("🧹 清空規則"):
            st.session_state.skip_rules = []

    if st.session_state.skip_rules:
        st.dataframe(pd.DataFrame(st.session_state.skip_rules), use_container_width=True, hide_index=True)

    top_n = st.number_input("Top N", min_value=10, max_value=100, value=30, step=10)
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


def main():
    set_page("驗收達標效率", icon="✅")

    uploaded, params, run_clicked = sidebar_uploader_and_actions(
        file_types=["xlsx", "xlsm", "xls", "csv", "txt"],
        params_renderer=render_params,
        run_label="🚀 開始計算",
    )

    if not (run_clicked and uploaded):
        st.info("請在左側上傳檔案並點『開始計算』。")
        return

    with st.spinner("計算中..."):
        result = run_qc_efficiency(uploaded.getvalue(), uploaded.name, params["skip_rules"])

    full_df = result.get("full_df", pd.DataFrame())
    ampm_df = result.get("ampm_df", pd.DataFrame())
    idle_df = result.get("idle_df", pd.DataFrame())

    target = float(result.get("target_eff", 20.0))

    # ===== KPI（穩定容錯版：不依賴 numpy）=====
    people = len(full_df) if isinstance(full_df, pd.DataFrame) else 0

    total_cnt = (
        full_df["筆數"].sum()
        if isinstance(full_df, pd.DataFrame) and "筆數" in full_df.columns
        else None
    )

    total_hours = (
        full_df["總工時"].sum()
        if isinstance(full_df, pd.DataFrame) and "總工時" in full_df.columns
        else None
    )

    avg_eff = (
        full_df["效率"].mean()
        if isinstance(full_df, pd.DataFrame) and "效率" in full_df.columns and len(full_df) > 0
        else None
    )

    pass_rate = None
    if isinstance(full_df, pd.DataFrame) and "效率" in full_df.columns and len(full_df) > 0:
        pass_rate = f"{(full_df['效率'] >= target).mean():.0%}"

    kpis = [
        KPI("人數", _fmt_int(people)),
        KPI("總筆數", _fmt_int(total_cnt)),
        KPI("總工時", _fmt_num(total_hours)),
        KPI("平均效率", _fmt_num(avg_eff)),
        KPI("達標率", pass_rate or "—"),
    ]
    render_kpis(kpis)
    st.divider()

    # ===== 圖表：左效率 TopN / 右空窗 TopN（若無則顯示 AMPM）=====
    left, right = st.columns([1.2, 1])

    with left:
        if isinstance(full_df, pd.DataFrame) and not full_df.empty:
            x_col = "姓名" if "姓名" in full_df.columns else full_df.columns[0]
            y_col = "效率" if "效率" in full_df.columns else full_df.columns[-1]
            bar_topN(
                full_df,
                x_col=x_col,
                y_col=y_col,
                hover_cols=[c for c in ["記錄輸入人", "筆數", "總工時", "空窗總分鐘"] if c in full_df.columns],
                top_n=params["top_n"],
                target=target,
                title="全日效率排行（Top N）",
            )
        else:
            st.info("full_df 無資料（可能找不到人員/時間欄位，或被排除規則排掉）。")

    with right:
        # 右側優先空窗排行
        if (
            isinstance(full_df, pd.DataFrame)
            and not full_df.empty
            and "空窗總分鐘" in full_df.columns
            and ("姓名" in full_df.columns or len(full_df.columns) > 0)
        ):
            x_col2 = "姓名" if "姓名" in full_df.columns else full_df.columns[0]
            bar_topN(
                full_df.sort_values("空窗總分鐘", ascending=False),
                x_col=x_col2,
                y_col="空窗總分鐘",
                hover_cols=[c for c in ["效率", "空窗筆數"] if c in full_df.columns],
                top_n=params["top_n"],
                target=-1.0,  # 讓顏色不影響解讀（全部視為達標色）
                title="空窗總分鐘排行（Top N）",
            )
        else:
            pivot_am_pm(ampm_df, index_col="姓名", segment_col="時段", value_col="效率", title="上午 vs 下午效率（平均）")

    st.divider()

    # ===== 表格：彙總（展開）+ 空窗明細（收合）=====
    table_block(
        summary_title="彙總表",
        summary_df=full_df if isinstance(full_df, pd.DataFrame) else pd.DataFrame(),
        detail_title="空窗明細（收合）",
        detail_df=idle_df if isinstance(idle_df, pd.DataFrame) else pd.DataFrame(),
        detail_expanded=False,
    )

    # ===== 下載 =====
    if result.get("xlsx_bytes"):
        download_excel(result["xlsx_bytes"], filename=result.get("xlsx_name", "驗收達標_含空窗_AMPM.xlsx"))


if __name__ == "__main__":
    main()
