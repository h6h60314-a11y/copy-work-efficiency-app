import streamlit as st

from common_ui import (
    card_close,
    card_open,
    inject_logistics_theme,
    set_page,
)

st.set_page_config(page_title="出貨課", page_icon="🚚", layout="wide")
inject_logistics_theme()


ITEMS = [
    {
        "icon": "🚚",
        "title": "撥貨差異",
        "desc": "比對撥貨來源與查詢資料，整理差異與儲位資訊。",
        "page": "pages/6_撥貨差異.py",
    },
    {
        "icon": "📍",
        "title": "播貨短少差異明細",
        "desc": "上傳短少明細、庫存明細、儲位明細，自動產出揀差異明細。",
        "page": "pages/33_播貨短少差異明細.py",
    },
    {
        "icon": "📦",
        "title": "採品門市差異量",
        "desc": "彙整採品與門市差異量，支援出貨異常檢核。",
        "page": "pages/23_採品門市差異量.py",
    },
    {
        "icon": "🏭",
        "title": "出貨作業線產能",
        "desc": "分析每日出貨作業線產能與人員效率。",
        "page": "pages/24_出貨作業線產能.py",
    },
    {
        "icon": "⏱️",
        "title": "各時段作業效率",
        "desc": "依時段、線別與區域檢視 PCS、PASS/FAIL 與效率。",
        "page": "pages/29_各時段作業效率.py",
    },
    {
        "icon": "🧾",
        "title": "客訂差異",
        "desc": "比對客訂差異、庫存與儲位，產出可追蹤明細。",
        "page": "pages/30_客訂差異.py",
    },
]


def render_manual_home_nav(items, columns=3):
    rows = [
        items[i:i + columns]
        for i in range(0, len(items), columns)
    ]

    for row_items in rows:
        cols = st.columns(columns)

        for col, item in zip(cols, row_items):
            with col:
                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid rgba(148, 163, 184, 0.35);
                        border-radius: 18px;
                        padding: 18px 18px 14px 18px;
                        background: rgba(255, 255, 255, 0.92);
                        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
                        min-height: 150px;
                        margin-bottom: 18px;
                    ">
                        <div style="font-size: 30px; margin-bottom: 8px;">
                            {item["icon"]}
                        </div>
                        <div style="
                            font-size: 18px;
                            font-weight: 800;
                            color: #0f172a;
                            margin-bottom: 8px;
                        ">
                            {item["title"]}
                        </div>
                        <div style="
                            font-size: 14px;
                            font-weight: 600;
                            color: rgba(15, 23, 42, 0.62);
                            line-height: 1.6;
                            min-height: 46px;
                        ">
                            {item["desc"]}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(
                    f"進入 {item['title']}",
                    key=f"go_{item['page']}",
                    use_container_width=True,
                ):
                    st.switch_page(item["page"])


def main():
    set_page(
        "出貨課",
        icon="🚚",
        subtitle="出貨差異、產能與效率分析入口。",
    )

    card_open("出貨課功能")
    render_manual_home_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
