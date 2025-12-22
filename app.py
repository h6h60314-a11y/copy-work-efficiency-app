from __future__ import annotations

import streamlit as st
from datetime import datetime

import common_ui as ui


st.set_page_config(
    page_title="進貨課效能平台",
    page_icon="🏭",
    layout="wide",
)

# 全站物流風格（公司化 A：深色側欄）
ui.inject_logistics_theme()


def main():
    # ===== Company Brand Bar（公司入口感）=====
    # 需要你 common_ui.py 已經有 brand_bar()（我前面提供的那版）
    try:
        ui.brand_bar(
            dept_code="GR",
            dept_name="大豐物流部",
            system_name="倉儲產能平台",
            version="v2.3",
            env_text="Internal Dashboard",
        )
    except Exception:
        # 若你尚未更新 common_ui.brand_bar，也不會報錯，先略過
        pass

    # ===== Page Title =====
    ui.set_page(
        "進貨課效能平台",
        icon="🏭",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    # ===== Status Line（公司感：來源/時間/版本）=====
    ui.card_open_plain()
    try:
        ui.status_line(
            [
                "模組：進貨課",
                "系統：倉儲產能平台",
                f"時間：{datetime.now():%Y-%m-%d %H:%M}",
                "版本：v2.3",
            ]
        )
    except Exception:
        st.caption(f"時間：{datetime.now():%Y-%m-%d %H:%M}｜版本：v2.3")
    ui.card_close()

    # ===== Portal Modules（入口卡片化）=====
    ui.card_open("📌 模組導覽", right_badge="Warehouse KPI")

    col1, col2, col3 = st.columns(3, gap="large")

    with col1:
        ui.card_open("✅ 驗收作業效能（KPI）", right_badge="QC")
        st.markdown("- 人時效率、達標率\n- 班別 AM/PM 切分\n- 支援排除非作業區間\n- 報表匯出（Excel）")
        # 若你的 Streamlit 支援 page_link，可直接點進去；不支援也沒關係
        try:
            st.page_link("pages/1_驗收作業效能（KPI）.py", label="進入模組", icon="➡️")
        except Exception:
            st.caption("請由左側選單進入：驗收作業效能（KPI）")
        ui.card_close()

    with col2:
        ui.card_open("📦 上架產能分析（Putaway KPI）", right_badge="PUT")
        st.markdown("- 上架產能、人時效率\n- 班別 AM/PM 切分\n- 支援排除非作業區間\n- 報表匯出（Excel）")
        try:
            st.page_link("pages/2_總上組上架產能.py", label="進入模組", icon="➡️")
        except Exception:
            st.caption("請由左側選單進入：上架產能分析")
        ui.card_close()

    with col3:
        ui.card_open("🧺 總揀達標", right_badge="PICK")
        st.markdown("- 上午/下午分段達標\n- 高空/低空門檻\n- 支援排除非作業區間\n- 報表匯出（Excel）")
        try:
            st.page_link("pages/3_總揀達標.py", label="進入模組", icon="➡️")
        except Exception:
            st.caption("請由左側選單進入：總揀達標")
        ui.card_close()

    ui.card_close()

    # ===== Notice / SOP =====
    ui.card_open("🧭 使用提示（SOP）", right_badge="Guide")
    st.markdown(
        """
1. 由左側選單（或上方模組入口）進入功能頁面  
2. 上傳原始資料 → 點選 **🚀 產出 KPI**  
3. 如遇休息/非作業時段，先在左側新增 **排除區間（HH:MM）** 再計算  
4. 畫面紅色代表未達標；匯出 Excel 與畫面紅/綠判斷一致  
        """.strip()
    )
    ui.card_close()

    st.caption("提示：左側選單可切換各模組頁面；各頁面的「計算條件設定」只影響本次分析結果。")


if __name__ == "__main__":
    main()
