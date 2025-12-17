import streamlit as st
import pandas as pd
import plotly.express as px
from qc_core import run_qc_efficiency

st.set_page_config(page_title="驗收達標可視化", layout="wide")
st.title("📦 驗收達標效率可視化（Streamlit）")

uploaded = st.file_uploader("上傳來源 Excel/CSV", type=["xlsx","xlsm","xls","csv","txt"])

# 用 session_state 存排除規則（多筆）
if "skip_rules" not in st.session_state:
    st.session_state.skip_rules = []

with st.sidebar:
    st.header("排除規則（不納入統計/不算空窗/會扣總分鐘）")

    user = st.text_input("記錄輸入人（可空白=全員）", value="")
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
        st.write("目前規則：")
        st.dataframe(pd.DataFrame(st.session_state.skip_rules), use_container_width=True)

run = st.button("🚀 開始計算", disabled=(uploaded is None))

if run and uploaded:
    with st.spinner("計算中..."):
        file_bytes = uploaded.getvalue()
        result = run_qc_efficiency(file_bytes, uploaded.name, st.session_state.skip_rules)

    full_df = result["full_df"]
    ampm_df = result["ampm_df"]
    idle_df = result["idle_df"]

    # KPI
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("人員-日資料筆數", f"{len(full_df):,}")
    k2.metric("AMPM 資料筆數", f"{len(ampm_df):,}")
    k3.metric("空窗明細筆數", f"{len(idle_df):,}")
    if not full_df.empty:
        k4.metric("平均效率（全日）", f"{full_df['效率'].mean():.2f}")
    else:
        k4.metric("平均效率（全日）", "—")

    st.divider()

    left, right = st.columns([1.2, 1])

    with left:
        st.subheader("全日效率排行")
        if not full_df.empty:
            top = full_df.sort_values("效率", ascending=False).head(30)
            fig = px.bar(top, x="姓名", y="效率", hover_data=["記錄輸入人","筆數","總工時","空窗總分鐘"])
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(full_df, use_container_width=True)
        else:
            st.info("full_df 沒有資料（可能上傳檔沒有時間欄/人員欄或被規則排除）。")

    with right:
        st.subheader("上午 vs 下午效率")
        if not ampm_df.empty:
            pivot = ampm_df.pivot_table(index=["姓名"], columns="時段", values="效率", aggfunc="mean").reset_index()
            st.dataframe(pivot, use_container_width=True)
        else:
            st.info("ampm_df 沒有資料。")

        st.subheader("空窗分鐘排行")
        if not full_df.empty:
            gap = full_df.sort_values("空窗總分鐘", ascending=False).head(30)
            fig2 = px.bar(gap, x="姓名", y="空窗總分鐘", hover_data=["空窗筆數","效率"])
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.download_button(
        "⬇️ 下載 Excel 結果（含分頁/條件著色/AMPM日期分組）",
        data=result["xlsx_bytes"],
        file_name="驗收達標_含空窗_AMPM.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
