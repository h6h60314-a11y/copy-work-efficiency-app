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


def render_card(item):
    st.markdown(
        f"""
        <div style="
            background: rgba(255,255,255,0.95);
            border: 1px solid rgba(148,163,184,0.28);
            border-radius: 16px;
            padding: 18px 18px 14px 18px;
            min-height: 132px;
            box-shadow: 0 10px 24px rgba(15,23,42,0.06);
            margin-bottom: 10px;
        ">
            <div style="
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 10px;
            ">
                <div style="
                    width: 38px;
                    height: 38px;
                    border-radius: 12px;
                    background: #e0f2fe;
                    border: 1px solid #bae6fd;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 20px;
                ">
                    {item["icon"]}
                </div>
                <div style="
                    font-size: 18px;
                    font-weight: 900;
                    color: #0f172a;
                ">
                    {item["title"]}
                </div>
            </div>

            <div style="
                font-size: 14px;
                font-weight: 650;
                color: rgba(15,23,42,0.68);
                line-height: 1.65;
                min-height: 42px;
            ">
                {item["desc"]}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        f"進入 → {item['title']}",
        key=f"go_{item['page']}",
        use_container_width=True,
    ):
        st.switch_page(item["page"])


def render_nav(items, columns=3):
    for i in range(0, len(items), columns):
        row_items = items[i:i + columns]
        cols = st.columns(columns)

        for col, item in zip(cols, row_items):
            with col:
                render_card(item)


def main():
    set_page(
        "出貨課",
        icon="🚚",
        subtitle="出貨差異、產能與效率分析入口。",
    )

    card_open("出貨課功能")
    render_nav(ITEMS, columns=3)
    card_close()


if __name__ == "__main__":
    main()
