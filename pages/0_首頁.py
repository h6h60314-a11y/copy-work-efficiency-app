# pages/0_首頁.py
import streamlit as st
from urllib.parse import quote, unquote

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(
    page_title="大豐物流 - 作業平台",
    page_icon="🚚",
    layout="wide",
)

inject_logistics_theme()


def _route_by_query():
    """
    用 query param 在同一視窗切頁（不走 st.button / st.page_link），避免被 common_ui 做成藍色膠囊。
    點標題會變成：?page=pages/1_驗收作業效能.py
    """
    qp = st.query_params
    raw = qp.get("page", "")

    # st.query_params 可能回傳 list[str] 或 str
    if isinstance(raw, list):
        raw = raw[0] if raw else ""

    if not raw:
        return

    # 清掉參數，避免回到首頁又重複跳轉
    st.query_params.clear()

    target = unquote(raw)
    st.switch_page(target)


def _home_css():
    st.markdown(
        r"""
<style>
/* =========================
   ✅ 去除藍色底 / 藍色框（全域覆蓋在首頁）
   ========================= */

/* 連結不要預設藍色 */
section[data-testid="stAppViewContainer"] a,
section[data-testid="stAppViewContainer"] a:visited{
  color: rgba(15, 23, 42, 0.92) !important;
  text-decoration: none !important;
}

/* 任何 button/link 類型外觀：透明底、無框、無陰影（避免藍色膠囊/藍框） */
section[data-testid="stAppViewContainer"] a,
section[data-testid="stAppViewContainer"] button{
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  outline: none !important;
}

/* 點擊焦點不要藍框 */
section[data-testid="stAppViewContainer"] a:focus,
section[data-testid="stAppViewContainer"] a:focus-visible,
section[data-testid="stAppViewContainer"] button:focus,
section[data-testid="stAppViewContainer"] button:focus-visible{
  outline: none !important;
  box-shadow: none !important;
}

/* 若 common_ui 對卡片/容器有藍框藍底，這裡強制改成白底+淺灰框 */
div[data-testid="stVerticalBlockBorderWrapper"]{
  background: rgba(255,255,255,0.98) !important;
  border-color: rgba(15, 23, 42, 0.12) !important;
  box-shadow: none !important;
}

/* =========================
   首頁清單：緊湊版（• + icon + 可點標題 + 同行描述）
   ========================= */

.home-list{ margin-top: 6px; }

/* 一列 */
.home-row{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 10px 0;
}

/* 左側（• + icon）佔位縮小，避免空格太大 */
.home-left{
  display: inline-flex;
  align-items: flex-start;
  gap: 8px;
  width: 34px;             /* ✅ 想更緊：改 28px */
  flex: 0 0 34px;
  margin-top: 2px;
}

.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
}
.home-ico{
  font-size: 16px;
  line-height: 1;
}

/* 右側文字區 */
.home-right{
  flex: 1 1 auto;
  line-height: 1.55;
}

/* 可點標題：純文字連結（不是膠囊） */
.home-link{
  display: inline;
  color: rgba(15, 23, 42, 0.92) !important;
  font-weight: 900;
  font-size: 16px;
  line-height: 1.45;
  text-decoration: none !important;
  cursor: pointer;
}
.home-link:hover{
  opacity: 0.86;
}

/* 同行描述 */
.home-desc{
  display: inline;
  margin-left: 6px;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}

/* 壓掉 markdown 容器預設外距 */
div[data-testid="stMarkdown"]{
  margin: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _nav_item(icon: str, title: str, page_path: str, desc: str):
    # query param 要 encoding（檔名含中文更穩）
    encoded = quote(page_path, safe="/_.-")
    st.markdown(
        f"""
<div class="home-row">
  <div class="home-left">
    <span class="home-bullet">•</span>
    <span class="home-ico">{icon}</span>
  </div>
  <div class="home-right">
    <a class="home-link" href="?page={encoded}">{title}：</a>
    <span class="home-desc">{desc}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def main():
    # ✅ 先處理跳頁（點標題後同視窗切換）
    _route_by_query()

    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")
    _home_css()

    st.markdown('<div class="home-list">', unsafe_allow_html=True)

    _nav_item(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、排除非作業區間（支援/離站/停機）",
    )
    _nav_item(
        "📦",
        "上架產能分析（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、區塊/報表規則、班別切分",
    )
    _nav_item(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、低空/高空門檻、排除非作業區間、匯出報表",
    )
    _nav_item(
        "🧊",
        "儲位使用率分析",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、KPI圖格呈現",
    )
    _nav_item(
        "🔎",
        "揀貨差異代庫存",
        "pages/5_揀貨差異代庫存.py",
        "少揀差異展開、庫存儲位/效期對應、國際條碼後五碼放大顯示",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    card_close()


if __name__ == "__main__":
    main()
