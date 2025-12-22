def _chart_usage_rate(res_df: pd.DataFrame, target: float | None = None):
    if res_df is None or res_df.empty:
        st.info("無資料可視覺化")
        return

    threshold = float(target) if target is not None else 90.0

    try:
        import altair as alt  # type: ignore

        data = res_df.copy()
        data["超過門檻"] = data["使用率(%)"].astype(float) > threshold

        base = (
            alt.Chart(data)
            .mark_bar()
            .encode(
                x=alt.X("使用率(%):Q", title="使用率(%)"),
                y=alt.Y("類別:N", sort="-x", title=""),
                color=alt.condition(
                    alt.datum["超過門檻"] == True,
                    alt.value("red"),          # ✅ 大於門檻：紅色
                    alt.value("steelblue"),    # ✅ 其他：藍色
                ),
                tooltip=["類別", "有效貨位", "已使用貨位", "未使用貨位", "使用率(%)"],
            )
            .properties(height=220)
        )

        layers = [base]

        # 目標線
        rule = alt.Chart(pd.DataFrame({"target": [threshold]})).mark_rule(strokeDash=[6, 4]).encode(
            x="target:Q"
        )
        layers.append(rule)

        st.altair_chart(alt.layer(*layers), use_container_width=True)

    except Exception:
        # fallback（st.bar_chart 無法條件著色，只能顯示柱狀）
        st.bar_chart(res_df.set_index("類別")["使用率(%)"])
        st.caption(f"⚠️ 目前環境無法套用條件著色，已用簡易圖表替代。門檻：{threshold:.0f}%")
