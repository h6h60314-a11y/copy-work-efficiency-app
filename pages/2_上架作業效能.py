# ======================
# 顯示（從 session_state）
# ======================
last = st.session_state.putaway_last
if not last:
    st.info("請先上傳上架作業原始資料並點選「🚀 產出 KPI」")
    return

user_col = last["user_col"]
summary = last["summary"]
target_eff_show = float(last["target_eff"])
top_n_show = int(controls.get("top_n", last.get("top_n", 30)))
total_people = int(last["total_people"])
met_people = int(last["met_people"])
rate = float(last["rate"])
xlsx_bytes = last["xlsx_bytes"]
xlsx_name = last["xlsx_name"]
total_match = int(last.get("total_match", 0))
match_rate_all = float(last.get("match_rate_all", 0.0))

# ✅ 只取兩張樞紐表（其他表格不顯示）
shelf_person_pivot = last.get("shelf_person_pivot", pd.DataFrame())
stype_person_pivot = last.get("stype_person_pivot", pd.DataFrame())

# KPI（不是表格，保留）
card_open("📌 總覽 KPI")
render_kpis([
    KPI("總人數", f"{total_people:,}"),
    KPI("達標人數", f"{met_people:,}"),
    KPI("達標率", f"{rate:.1%}"),
    KPI("達標門檻", f"效率 ≥ {int(target_eff_show)}"),
    KPI("棚別比對筆數", f"{total_match:,}"),
    KPI("棚別比對率", f"{match_rate_all:.1%}"),
])
card_close()

# ✅ 只顯示兩個表：棚別樞紐 + 儲位類型樞紐
col_a, col_b = st.columns(2)

with col_a:
    card_open("🏷️ 樞紐表（每人一列、每棚別一欄）")
    if shelf_person_pivot is None or shelf_person_pivot.empty:
        st.info("尚未產生棚別樞紐表（可能未上傳棚別主檔，或比對結果為空）。")
    else:
        st.dataframe(shelf_person_pivot, use_container_width=True, hide_index=True)
    card_close()

with col_b:
    card_open("🧩 樞紐表（每人一列、每儲位類型一欄）")
    if stype_person_pivot is None or stype_person_pivot.empty:
        st.info("尚未產生儲位類型樞紐表（可能到/棚別無法擷取區碼3，或資料為空）。")
    else:
        st.dataframe(stype_person_pivot, use_container_width=True, hide_index=True)
    card_close()

# AM/PM 排行（你原本的圖表保留）
col_l, col_r = st.columns(2)

with col_l:
    card_open(f"🌓 AM（上午）效率排行（Top {top_n_show}）")
    am_rank = summary[[user_col, "對應姓名", "上午筆數", "上午工時_分鐘", "上午效率_件每小時"]].copy()
    am_rank = am_rank.rename(columns={"上午效率_件每小時": "效率", "上午筆數": "筆數", "上午工時_分鐘": "工時"})
    am_rank["姓名"] = am_rank["對應姓名"].where(am_rank["對應姓名"].astype(str).str.len() > 0, am_rank[user_col].astype(str))
    bar_topN(
        am_rank[["姓名", "效率", "筆數", "工時"]],
        x_col="姓名",
        y_col="效率",
        hover_cols=["筆數", "工時"],
        top_n=top_n_show,
        target=float(target_eff_show),
    )
    card_close()

with col_r:
    card_open(f"🌙 PM（下午）效率排行（Top {top_n_show}）")
    pm_rank = summary[[user_col, "對應姓名", "下午筆數", "下午工時_分鐘_扣休", "下午效率_件每小時"]].copy()
    pm_rank = pm_rank.rename(columns={"下午效率_件每小時": "效率", "下午筆數": "筆數", "下午工時_分鐘_扣休": "工時"})
    pm_rank["姓名"] = pm_rank["對應姓名"].where(pm_rank["對應姓名"].astype(str).str.len() > 0, pm_rank[user_col].astype(str))
    bar_topN(
        pm_rank[["姓名", "效率", "筆數", "工時"]],
        x_col="姓名",
        y_col="效率",
        hover_cols=["筆數", "工時"],
        top_n=top_n_show,
        target=float(target_eff_show),
    )
    card_close()

# 下載保留
download_excel_card(
    xlsx_bytes,
    xlsx_name,
    label="⬇️ 匯出 KPI 報表（Excel）",
)
