import streamlit as st
import pandas as pd
import datetime as dt
import uuid

from common_ui import (
    inject_logistics_theme,
    set_page,
    KPI,
    render_kpis,
    bar_topN,
    download_excel,
    card_open,
    card_close,
    sidebar_controls,  # ✅ 新增：統一左側設定（不含 Operator）
)

from qc_core import run_qc_efficiency
from audit_store import sha256_bytes, upload_export_bytes, insert_audit_run


def _adapt_exclude_windows_to_skip_rules(exclude_windows):
    """
    將 common_ui.sidebar_controls() 的 exclude_windows 格式：
      [{"start":"HH:MM","end":"HH:MM","data_entry":""}, ...]
    轉回 qc_core.run_qc_efficiency 目前頁面原本使用的 skip_rules 格式：
      [{"user":"", "t_start": datetime.time, "t_end": datetime.time}, ...]
    """
    skip_rules = []
    for w in exclude_windows or []:
        try:
            s = pd.to_datetime(w.get("start", "")).time()
            e = pd.to_datetime(w.get("end", "")).time()
        except Exception:
            # 若格式異常，跳過
            continue

        skip_rules.append(
            {
                "user": (w.get("data_entry") or "").strip(),
                "t_start": s,
                "t_end": e,
            }
        )
    return skip_rules


def main():
    inject_logistics_theme()
    set_page("驗收作業效能（KPI）", icon="✅", subtitle="驗收作業｜人時效率｜AM / PM 班別｜KPI 達標分析")

    # ======================
    # Sidebar：計算條件設定（✅ 已取消 Operator）
    # ======================
    controls = sidebar_controls(default_top_n=30, enable_exclude_windows=True, state_key_prefix="qc")
    top_n = int(controls["top_n"])
    skip_rules = _adapt_exclude_windows_to_skip_rules(controls.get("exclude_windows", []))

    # ======================
    # 上傳資料
    # ======================
    card_open("📤 上傳作業原始資料（驗收）")
    uploaded = st.file_uploader(
        "上傳驗收作業原始資料",
        type=["xlsx", "xls", "csv"],
        label_visibility="collapsed",
    )
    run = st.button("🚀 產出 KPI", type="primary", disabled=uploaded is None)
    card_close()

    if not run:
        st.info("請先上傳驗收作業原始資料")
        return

    # ======================
    # 計算
    # ======================
    with st.spinner("KPI 計算中，請稍候..."):
        result = run_qc_efficiency(
            uploaded.getvalue(),
            uploaded.name,
            skip_rules,  # ✅ 使用轉換後的 skip_rules
        )

    df = result.get("ampm_df", pd.DataFrame())
    idle_df = result.get("idle_df", pd.DataFrame())
    target = float(result.get("target_eff", 20.0))

    if df.empty or "時段" not in df.columns:
        st.error("資料缺少『時段』欄位，無法區分 AM / PM 班別")
        return

    # 顯示層轉換為 AM / PM
    df = df.copy()
    df["班別"] = df["時段"].replace({"上午": "AM 班", "下午": "PM 班"})
    am_df = df[df["班別"] == "AM 班"].copy()
    pm_df = df[df["班別"] == "PM 班"].copy()

    # ======================
    # KPI 區塊
    # ======================
    col_l, col_r = st.columns(2)

    def render_shift(title, sdf: pd.DataFrame):
        card_open(f"{title} KPI")
        if sdf is None or sdf.empty:
            st.info("本班別無資料")
        else:
            render_kpis(
                [
                    KPI("人數", f"{len(sdf):,}"),
                    KPI("總驗收筆數", f"{sdf['筆數'].sum():,}"),
                    KPI("總工時", f"{sdf['總工時'].sum():.2f}"),
                    KPI("平均效率", f"{sdf['效率'].mean():.2f}"),
                    KPI("達標率", f"{(sdf['效率'] >= target).mean():.0%}"),
                ]
            )
        card_close()

        card_open(f"{title} 效率排行（Top {top_n}）")
        if sdf is None or sdf.empty:
            st.info("本班別無排行資料")
        else:
            bar_topN(
                sdf,
                x_col="姓名",
                y_col="效率",
                hover_cols=["筆數", "總工時"],
                top_n=top_n,
                target=target,
            )
        card_close()

    with col_l:
        render_shift("🌓 AM 班（驗收）", am_df)

    with col_r:
        render_shift("🌙 PM 班（驗收）", pm_df)

    # ======================
    # 匯出
    # ======================
    if result.get("xlsx_bytes"):
        card_open("⬇️ 匯出 KPI 報表")
        download_excel(result["xlsx_bytes"], result.get("xlsx_name", "驗收作業KPI.xlsx"))
        card_close()

    # ======================
    # 稽核留存
    # ======================
    st.divider()
    st.subheader("🧾 稽核留存狀態")

    try:
        export_path = None
        if result.get("xlsx_bytes"):
            export_path = upload_export_bytes(
                content=result["xlsx_bytes"],
                object_path=f"qc_runs/{dt.datetime.now():%Y%m%d}/{uuid.uuid4().hex}.xlsx",
            )

        payload = {
            "app_name": "驗收作業效能（KPI）",
            # ✅ operator 已取消：不再寫入
            "source_filename": uploaded.name,
            "source_sha256": sha256_bytes(uploaded.getvalue()),
            "params": {
                "top_n": top_n,
                "target_eff": target,
                "skip_rules": skip_rules,  # ✅ 留存本次排除區間（轉換後格式）
            },
            "kpi_am": {"avg_eff": float(am_df["效率"].mean()) if not am_df.empty else None, "people": int(len(am_df))},
            "kpi_pm": {"avg_eff": float(pm_df["效率"].mean()) if not pm_df.empty else None, "people": int(len(pm_df))},
            "export_object_path": export_path,
        }

        row = insert_audit_run(payload)
        st.success(f"✅ 已成功留存本次分析（ID：{row.get('id')}）")

    except Exception as e:
        st.error("❌ 稽核留存失敗")
        st.code(str(e))


if __name__ == "__main__":
    main()
