import streamlit as st
from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="大豐物流 - 作業平台", page_icon="🚚", layout="wide")
inject_logistics_theme()

# ✅ 用 query param 同視窗跳頁（不經過 st.button / st.page_link，因此不會變膠囊）
def _route_by_query():
    qp = st.query_params
    target = qp.get("page", "")
    if not target:
        return
    # 清掉參數，避免回到首頁又再次觸發
    st.query_params.clear()
    st.switch_page(target)


def _home_css():
    st.markdown(
        r"""
<style>
/* 更緊湊、跟你示意圖一致：• + icon + 可點標題 + 同行描述 */
.home-row{
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 10px 0;
}

.home-left{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: 38px;            /* ✅ 左側固定很小寬度，避免大空格 */
  flex: 0 0 38px;
}

.home-bullet{
  color: rgba(15, 23, 42, 0.55);
  font-size: 16px;
  line-height: 1;
  margin-top: 2px;
}
.home-ico{
  font-size: 16px;
  line-height: 1;
  margin-top: 1px;
}

.home-right{
  flex: 1 1 auto;
  line-height: 1.55;
}

.home-link{
  display: inline;
  color: rgba(15, 23, 42, 0.92);
  font-weight: 900;
  font-size: 16px;
  line-height: 1.45;
  text-decoration: none;
  cursor: pointer;
}
.home-link:hover{ opacity: 0.86; }

.home-desc{
  display: inline;
  margin-left: 6px;
  color: rgba(15, 23, 42, 0.72);
  font-weight: 650;
  font-size: 14px;
  line-height: 1.45;
}

/* 壓掉 markdown 容器預設外距 */
div[data-testid="stMarkdown"]{ margin: 0 !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def nav_item(icon: str, title: str, page: str, desc: str):
    # 用 query param 觸發跳頁：?page=pages/1_xxx.py
    st.markdown(
        f"""
<div class="home-row">
  <div class="home-left">
    <span class="home-bullet">•</span>
    <span class="home-ico">{icon}</span>
  </div>
  <div class="home-right">
    <a class="home-link" href="?page={page}">{title}：</a>
    <span class="home-desc">{desc}</span>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def main():
    # 先處理路由（點了標題就直接跳頁）
    _route_by_query()

    set_page(
        "大豐物流 - 作業平台",
        icon="🚚",
        subtitle="作業KPI｜班別分析（AM/PM）｜排除非作業區間",
    )

    card_open("📌 作業績效分析模組")
    _home_css()

    nav_item(
        "✅",
        "驗收作業效能（KPI）",
        "pages/1_驗收作業效能.py",
        "人時效率、達標率、班別（AM/PM）切分、排除非作業區間（支援/離站/停機）",
    )
    nav_item(
        "📦",
        "上架產能分析（Putaway KPI）",
        "pages/2_上架作業效能.py",
        "上架產能、人時效率、區塊/報表規則、班別切分",
    )
    nav_item(
        "🎯",
        "總揀作業效能",
        "pages/3_總揀作業效能.py",
        "上午/下午達標分析、低空/高空門檻、排除非作業區間、匯出報表",
    )
    nav_item(
        "🧊",
        "儲位使用率分析",
        "pages/4_儲位使用率.py",
        "依區(溫層)分類統計、使用率門檻提示、分類可調整、KPI圖格呈現",
    )
    nav_item(
        "🔎",
        "揀貨差異代庫存",
        "pages/5_揀貨差異代庫存.py",
        "少揀差異展開、庫存儲位/效期對應、國際條碼後五碼放大顯示",
    )

    card_close()


if __name__ == "__main__":
    main()
