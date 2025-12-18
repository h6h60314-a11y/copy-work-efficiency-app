import streamlit as st
import pandas as pd

from common_ui import (
    set_page, sidebar_uploader_and_actions, KPI,
    render_kpis, bar_topN, pivot_am_pm, table_block, download_excel
)

from shelf_core import run_shelf_efficiency


def render_params():
    target_eff = st.number_input("達標門檻（件/時）", min_value=1, max_value=200, value=20, step=1)
    idle_threshold = st.number_input("空窗門檻（分鐘）", min_value=1, max_value=120, value=10, step=1)
    top_n = st.number_input("Top N", min_value=10, max_value=100, value=30, step=10)
    return {"target_eff": float(target_eff), "idle_threshold": int(idle_threshold), "top_n": int(top_n)}


def main():
    set_page("總上組上架產能", icon="📦")

    uploaded, params, run_clicked = sidebar_uploader_and_actions(
        file_types=["xlsx", "xlsm", "xls", "xlsb", "csv"],
        params_renderer=render_params,
        run_label="🚀 開始計算",
    )

    if not (run_clicked and uploaded):
        st.info("請在左側上傳檔案並點『開始計算』。")
        return

    with st.spinner("計算中..."):
        result = run_shelf_efficiency(uploaded.getvalue(), uploaded.name, params)

    target = float(result.get("target_eff", 20.0))

    kpis = [
        KPI("人數", f"{int(result.get('people', 0)):,}"),
        KPI("總筆數", f"{int(result.get('total_count', 0)):,}"),
        KPI("總工時", f"{float(result.get('total_hours', 0.0)):,.2f}"),
        KPI("平均效率", f"{float(result.get('avg_eff', 0.0)):,.2f}"),
        KPI("達標率", str(result.get("pass_rate", "—"))),
    ]
    render_kpis(kpis)
    st.divider()

    summary_df = result.get("summary_df", pd.DataFrame())
    ampm_df = result.get("ampm_df", pd.DataFrame())
    detail_df = result.get("detail_df", pd.DataFrame())

    left, right = st.columns([1.2, 1])
    with left:
        bar_topN(
            summary_df,
            x_col="姓名" if "姓名" in summary_df.columns else (summary_df.columns[0] if len(summary_df.columns) else "姓名"),
            y_col="效率" if "效率" in summary_df.columns else summary_df.columns[-1],
            hover_cols=[c for c in ["記錄輸入人","筆數","總分鐘"] if c in summary_df.columns],
            top_n=params["top_n"],
            target=target,
            title="全日效率排行（Top N）"
        )
    with right:
        pivot_am_pm(ampm_df, index_col="姓名", segment_col="時段", value_col="效率_件每小時", title="上午 vs 下午效率（平均）")

    st.divider()
    table_block(
        summary_title="彙總表",
        summary_df=summary_df,
        detail_title="明細表（收合）",
        detail_df=detail_df,
        detail_expanded=False
    )

    if result.get("xlsx_bytes"):
        download_excel(result["xlsx_bytes"], filename=result.get("xlsx_name", "上架績效.xlsx"))


if __name__ == "__main__":
    main()
