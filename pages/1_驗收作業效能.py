from __future__ import annotations

import streamlit as st
import pandas as pd

from common_ui import (
    set_page,               # set_page 內會 inject_logistics_theme()
    KPI,
    render_kpis,
    bar_topN,
    download_excel_card,    # ✅ 一行=按鈕、卡片外框、不分段
    sidebar_controls,       # ✅ 統一左側設定（TopN + 排除空窗）
    card_open,
    card_close,
    show_kpi_table,         # ✅ 整列紅/綠顯示（效率 < target 會紅）
)

from qc_core import run_qc_efficiency


# =========================================================
# 固定設定
# =========================================================

# 驗收作業上午、下午效率門檻統一為 29 筆／小時
QC_TARGET_EFFICIENCY = 29.0


# =========================================================
# Helpers
# =========================================================
def _adapt_exclude_windows_to_skip_rules(exclude_windows):
    """
    將 common_ui.sidebar_controls() 的 exclude_windows 格式：
      [{"start":"HH:MM","end":"HH:MM","data_entry":""}, ...]

    轉回 qc_core.run_qc_efficiency 需要的 skip_rules 格式：
      [{"user":"", "t_start": datetime.time, "t_end": datetime.time}, ...]
    """
    skip_rules = []

    for w in exclude_windows or []:
        start_str = (w.get("start") or "").strip()
        end_str = (w.get("end") or "").strip()
        user_str = (w.get("data_entry") or "").strip()

        try:
            # 明確指定 HH:MM，避免被解析成日期
            start_time = pd.to_datetime(
                start_str,
                format="%H:%M",
            ).time()

            end_time = pd.to_datetime(
                end_str,
                format="%H:%M",
            ).time()

        except Exception:
            continue

        # 安全檢查：開始時間必須早於結束時間
        if start_time >= end_time:
            continue

        skip_rules.append(
            {
                "user": user_str,
                "t_start": start_time,
                "t_end": end_time,
            }
        )

    return skip_rules


def _ensure_session_defaults():
    """
    建立 session_state 預設值。

    避免 Streamlit 因為調整左側設定、下載檔案或重新渲染，
    導致已計算的結果從畫面消失。
    """
    if "qc_last_result" not in st.session_state:
        st.session_state.qc_last_result = None

    if "qc_last_filename" not in st.session_state:
        st.session_state.qc_last_filename = None


def _split_am_pm(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    依「時段」欄位分割上午與下午資料。

    支援原始時段值：
    - 上午
    - 下午

    轉換後班別：
    - AM 班
    - PM 班
    """
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = df.copy()

    if "時段" not in df.columns:
        return pd.DataFrame(), pd.DataFrame()

    df["班別"] = (
        df["時段"]
        .astype(str)
        .str.strip()
        .replace(
            {
                "上午": "AM 班",
                "下午": "PM 班",
                "AM": "AM 班",
                "PM": "PM 班",
                "AM 班": "AM 班",
                "PM 班": "PM 班",
            }
        )
    )

    am_df = df[df["班別"] == "AM 班"].copy()
    pm_df = df[df["班別"] == "PM 班"].copy()

    return am_df, pm_df


def _safe_sum(
    df: pd.DataFrame,
    col: str,
) -> float:
    """
    安全加總指定欄位。
    """
    if df is None or df.empty or col not in df.columns:
        return 0.0

    values = pd.to_numeric(
        df[col],
        errors="coerce",
    ).fillna(0)

    return float(values.sum())


def _safe_mean(
    df: pd.DataFrame,
    col: str,
) -> float:
    """
    安全計算指定欄位平均值。
    """
    if df is None or df.empty or col not in df.columns:
        return 0.0

    values = pd.to_numeric(
        df[col],
        errors="coerce",
    ).dropna()

    if values.empty:
        return 0.0

    return float(values.mean())


def _safe_rate_ge(
    df: pd.DataFrame,
    col: str,
    target: float,
) -> float:
    """
    計算指定欄位大於等於門檻的達標率。
    """
    if df is None or df.empty or col not in df.columns:
        return 0.0

    values = pd.to_numeric(
        df[col],
        errors="coerce",
    ).dropna()

    if values.empty:
        return 0.0

    return float(
        (values >= float(target)).mean()
    )


def _render_shift_block(
    title: str,
    sdf: pd.DataFrame,
    *,
    top_n: int,
    target: float,
):
    """
    顯示單一班別的 KPI、明細表與效率排行。
    """

    # ======================
    # KPI 卡片
    # ======================
    card_open(
        f"{title}｜KPI",
        right_badge=f"門檻 {target:.0f} 筆／小時",
    )

    if sdf is None or sdf.empty:
        st.info("本班別無資料")
        card_close()
        return

    render_kpis(
        [
            KPI(
                "人數",
                f"{len(sdf):,}",
            ),
            KPI(
                "總驗收筆數",
                f"{_safe_sum(sdf, '筆數'):,.0f}",
            ),
            KPI(
                "總工時",
                f"{_safe_sum(sdf, '總工時'):.2f}",
            ),
            KPI(
                "平均效率",
                f"{_safe_mean(sdf, '效率'):.2f}",
            ),
            KPI(
                "達標率",
                f"{_safe_rate_ge(sdf, '效率', target):.0%}",
            ),
        ],
        cols=5,
    )

    card_close()

    # ======================
    # KPI 明細表
    # ======================
    card_open(
        f"{title}｜KPI 明細",
        right_badge=f"紅色＜{target:.0f}｜綠色≥{target:.0f}",
    )

    show_kpi_table(
        sdf,
        eff_col="效率",
        target=float(target),
    )

    card_close()

    # ======================
    # Top N 效率排行
    # ======================
    card_open(
        f"{title}｜效率排行（Top {top_n}）",
        right_badge=f"門檻 {target:.0f}",
    )

    x_col = (
        "姓名"
        if "姓名" in sdf.columns
        else sdf.columns[0]
    )

    hover_cols = [
        col
        for col in [
            "筆數",
            "總工時",
            "空窗分鐘",
        ]
        if col in sdf.columns
    ]

    bar_topN(
        sdf,
        x_col=x_col,
        y_col="效率",
        hover_cols=hover_cols,
        top_n=int(top_n),
        target=float(target),
        title=f"低於 {target:.0f} 筆／小時自動標紅；虛線為達標門檻",
    )

    card_close()


# =========================================================
# Main
# =========================================================
def main():
    _ensure_session_defaults()

    set_page(
        "驗收作業效能（KPI）",
        icon="✅",
        subtitle=(
            "驗收作業｜人時效率｜AM / PM 班別｜"
            f"統一門檻 {QC_TARGET_EFFICIENCY:.0f} 筆／小時"
        ),
    )

    # ======================
    # Sidebar：計算條件設定
    # ======================
    controls = sidebar_controls(
        default_top_n=30,
        enable_exclude_windows=True,
        state_key_prefix="qc",
    )

    top_n = int(
        controls.get(
            "top_n",
            30,
        )
    )

    skip_rules = _adapt_exclude_windows_to_skip_rules(
        controls.get(
            "exclude_windows",
            [],
        )
    )

    # ======================
    # 顯示固定門檻
    # ======================
    with st.sidebar:
        st.divider()
        st.metric(
            "驗收效率門檻",
            f"{QC_TARGET_EFFICIENCY:.0f} 筆／小時",
            help="上午與下午均使用相同門檻。",
        )

    # ======================
    # 上傳資料與產出按鈕
    # ======================
    card_open(
        "📤 上傳作業原始資料（驗收）",
        right_badge="XLSX / XLS / CSV",
    )

    uploaded = st.file_uploader(
        "上傳驗收作業原始資料",
        type=[
            "xlsx",
            "xls",
            "csv",
        ],
        label_visibility="collapsed",
        key="qc_upload_file",
    )

    run_clicked = st.button(
        "🚀 產出 KPI",
        type="primary",
        disabled=(uploaded is None),
        use_container_width=True,
    )

    card_close()

    # ======================
    # 計算
    # ======================
    if run_clicked and uploaded is not None:
        try:
            with st.spinner("KPI 計算中，請稍候..."):
                result = run_qc_efficiency(
                    uploaded.getvalue(),
                    uploaded.name,
                    skip_rules,
                )

            if not result:
                st.session_state.qc_last_result = None
                st.session_state.qc_last_filename = None

                st.error(
                    "計算未產出結果，請確認上傳檔案內容與格式。"
                )

            else:
                # 強制統一前端顯示與後續使用門檻為 29
                result["target_eff"] = QC_TARGET_EFFICIENCY
                result["target_eff_am"] = QC_TARGET_EFFICIENCY
                result["target_eff_pm"] = QC_TARGET_EFFICIENCY

                st.session_state.qc_last_result = result
                st.session_state.qc_last_filename = uploaded.name

                st.success(
                    f"計算完成：上午與下午門檻均為 "
                    f"{QC_TARGET_EFFICIENCY:.0f} 筆／小時。"
                )

        except Exception as exc:
            st.session_state.qc_last_result = None
            st.session_state.qc_last_filename = None

            st.error(
                f"KPI 計算失敗：{exc}"
            )

            return

    # ======================
    # 從 session_state 取用結果
    # ======================
    result = st.session_state.qc_last_result

    if not result:
        st.info(
            "請先上傳驗收作業原始資料，"
            "再點選「🚀 產出 KPI」。"
        )
        return

    df = result.get(
        "ampm_df",
        pd.DataFrame(),
    )

    # 不採用 qc_core 回傳的舊門檻
    # 上午與下午一律固定使用 29
    am_target = QC_TARGET_EFFICIENCY
    pm_target = QC_TARGET_EFFICIENCY

    if df is None or df.empty:
        st.warning(
            "已計算完成，但沒有產出可顯示的資料，"
            "ampm_df 為空。"
        )
        return

    if "時段" not in df.columns:
        st.error(
            "資料缺少「時段」欄位，"
            "無法區分 AM 與 PM 班別。"
        )
        return

    if "效率" not in df.columns:
        st.error(
            "資料缺少「效率」欄位，"
            "無法進行達標判斷。"
        )
        return

    am_df, pm_df = _split_am_pm(df)

    # ======================
    # 匯出 Excel
    # ======================
    if result.get("xlsx_bytes"):
        download_excel_card(
            result["xlsx_bytes"],
            result.get(
                "xlsx_name",
                "驗收作業KPI.xlsx",
            ),
            label="⬇️ 匯出 KPI 報表（Excel）",
        )

    # ======================
    # AM / PM 兩欄呈現
    # ======================
    col_l, col_r = st.columns(
        2,
        gap="large",
    )

    with col_l:
        _render_shift_block(
            "🌓 AM 班（驗收）",
            am_df,
            top_n=top_n,
            target=am_target,
        )

    with col_r:
        _render_shift_block(
            "🌙 PM 班（驗收）",
            pm_df,
            top_n=top_n,
            target=pm_target,
        )


if __name__ == "__main__":
    main()
