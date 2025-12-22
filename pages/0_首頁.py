from __future__ import annotations

from datetime import datetime
import streamlit as st

import common_ui as ui


APP_NAME = "倉儲產能平台"
DEPT_CODE = "GR"
DEPT_NAME = "大豐物流部"
VERSION = "v2.3"


def main():
    # ===== Company Brand =====
    ui.inject_logistics_theme()
    ui.brand_bar(
        dept_code=DEPT_CODE,
        dept_name=DEPT_NAME,
        system_name=APP_NAME,
        version=VERSION,
        env_text="Internal Dashboard",
    )

    ui.set_page("首頁（Dashboard）", icon="🏠", subtitle="內部系統入口｜快捷操作｜資料狀態｜公告與版本")

    # ===== Status line =====
    ui.card_open_plain()
    ui.status_line(
        [
            f"系統：{DEPT_NAME}｜{APP_NAME}",
            f"版本：{VERSION}",
            f"目前時間：{datetime.now():%Y-%m-%d %H:%M}",
        ]
    )
    ui.card_close()

    # ===== Quick Launch =====
    ui.card_open("🚀 快捷入口", right_badge="常用功能")
    c1, c2, c3, c4 = st.columns(4)

    # 方式A：用 st.page_link（Streamlit 新版支援；若你的版本沒有，下面有方式B）
    # 請把檔名改成你 pages 內實際檔名（例：pages/1_驗收作業效能.py）
    with c1:
        try:
            st.page_link("pages/1_驗收作業效能（KPI）.py", label="✅ 驗收作業 KPI", icon="✅")
        except Exception:
            st.button("✅ 驗收作業 KPI（請從左側選單進入）", use_container_width=True)

    with c2:
        try:
            st.page_link("pages/2_總上組上架產能.py", label="📥 上架產能", icon="📥")
        except Exception:
            st.button("📥 上架產能（請從左側選單進入）", use_container_width=True)

    with c3:
        try:
            st.page_link("pages/3_總揀達標.py", label="📦 總揀達標", icon="📦")
        except Exception:
            st.button("📦 總揀達標（請從左側選單進入）", use_container_width=True)

    with c4:
        try:
            st.page_link("pages/4_出貨達標.py", label="🚚 出貨達標", icon="🚚")
        except Exception:
            st.button("🚚 出貨達標（請從左側選單進入）", use_container_width=True)

    ui.card_close()

    # ===== Today Overview =====
    ui.card_open("📊 今日營運概況", right_badge="Overview")
    ui.render_kpis(
        [
            ui.KPI("今日上傳檔案", str(st.session_state.get("today_upload_cnt", 0))),
            ui.KPI("今日產出報表", str(st.session_state.get("today_report_cnt", 0))),
            ui.KPI("系統狀態", "正常"),
            ui.KPI("資料版本", VERSION),
        ],
        cols=4,
    )
    ui.hint("※ 此頁為入口總覽；各功能的 KPI 明細請由快捷入口進入。")
    ui.card_close()

    # ===== Announcement + ChangeLog =====
    left, right = st.columns([1.2, 1.0], gap="large")

    with left:
        ui.card_open("📌 公告（Announcement）", right_badge="Admin")
        st.markdown(
            """
- **資料上傳規範**：請使用原始報表（不得刪欄/改欄名），避免欄位對不到導致 KPI 缺失。
- **排除空窗**：請在左側「排除區間」設定非作業時段，系統會自動扣除並重新計算效率。
- **匯出一致**：畫面紅/綠判斷與 Excel 匯出一致（未達標整列紅底）。
            """.strip()
        )
        ui.card_close()

    with right:
        ui.card_open("🧾 版本更新（Changelog）", right_badge=VERSION)
        st.markdown(
            f"""
- **{VERSION}**
  - 首頁公司化入口（Brand Bar + 快捷入口 + 概況）
  - KPI 表格整列紅/綠一致化
  - Sidebar 排除空窗統一規格
            """.strip()
        )
        ui.card_close()

    # ===== Getting Started =====
    ui.card_open("🧭 使用指引（SOP）", right_badge="Guide")
    st.markdown(
        """
1. 先從左側選單進入對應課組功能（或使用上方「快捷入口」）。
2. 上傳原始資料 → 點「🚀 產出 KPI」。
3. 若有休息/非作業時段 → 先在左側新增「排除區間」再計算。
4. 確認 KPI（紅=未達標）→ 需要留存請匯出 Excel。
        """.strip()
    )
    ui.card_close()


if __name__ == "__main__":
    # 建議放 wide 讓首頁更像公司 Portal（如果你其他頁已 set_page_config，也可移除）
    st.set_page_config(page_title=f"{DEPT_NAME}｜{APP_NAME}", page_icon="🏠", layout="wide")
    main()
