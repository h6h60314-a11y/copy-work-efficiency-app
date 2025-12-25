# pages/11_出貨訂單應出量分析.py
import os
import io
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close


def robust_read_from_upload(uploaded_file) -> pd.DataFrame:
    """
    依副檔名自動嘗試多種讀取方式（從上傳檔 bytes 讀）
    支援：Excel / CSV / HTML
    """
    name = uploaded_file.name
    ext = os.path.splitext(name)[1].lower()
    data = uploaded_file.getvalue()

    # Excel
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        engines = ["openpyxl", "xlrd"]
        for eng in engines:
            try:
                return pd.read_excel(io.BytesIO(data), engine=eng)
            except Exception:
                pass

    if ext == ".xls":
        engines = ["xlrd", "openpyxl"]
        for eng in engines:
            try:
                return pd.read_excel(io.BytesIO(data), engine=eng)
            except Exception:
                pass

    if ext == ".xlsb":
        try:
            return pd.read_excel(io.BytesIO(data), engine="pyxlsb")
        except Exception as e:
            raise ValueError(f"讀取 .xlsb 失敗：{e}")

    # CSV
    if ext == ".csv":
        # 先用 utf-8，失敗再用 cp950
        for enc in ("utf-8", "utf-8-sig", "cp950"):
            try:
                return pd.read_csv(io.BytesIO(data), encoding=enc)
            except Exception:
                pass
        raise ValueError("CSV 讀取失敗：請確認編碼（utf-8 / cp950）")

    # HTML
    if ext in (".html", ".htm"):
        try:
            html_text = data.decode("utf-8", errors="ignore")
            tables = pd.read_html(html_text)
            if tables:
                return tables[0]
        except Exception as e:
            raise ValueError(f"HTML 讀取失敗：{e}")

    raise ValueError("無法識別或讀取此文件，請上傳 Excel/CSV/HTML。")


def compute_kpi(df: pd.DataFrame) -> dict:
    need_cols = ["原始配庫存量", "出貨入數", "計量單位"]
    missing = [c for c in need_cols if c not in df.columns]
    if missing:
        raise KeyError(f"❌ 缺少 KPI 所需欄位：{missing}")

    d = df.copy()

    # 轉數值
    d["原始配庫存量"] = pd.to_numeric(d["原始配庫存量"], errors="coerce").fillna(0)
    d["出貨入數"] = pd.to_numeric(d["出貨入數"], errors="coerce").replace(0, pd.NA)
    d["計量單位"] = pd.to_numeric(d["計量單位"], errors="coerce")

    # 計算「原始配庫存出貨單位量」
    d["原始配庫存出貨單位量"] = (d["原始配庫存量"] / d["出貨入數"]).fillna(0)

    # 應出量計算（沿用你原本邏輯）
    mask1 = (d["原始配庫存出貨單位量"] == 1) & (d["計量單位"] == 2)
    total1 = d.loc[mask1, "原始配庫存量"].sum()

    mask2 = (d["原始配庫存出貨單位量"] != 1) & (d["計量單位"] == 2)
    total2 = d.loc[mask2, "原始配庫存出貨單位量"].sum()

    mask3 = d["計量單位"].isin([3, 6])
    total3 = d.loc[mask3, "原始配庫存出貨單位量"].sum()

    combined_2 = total1 + total2

    # 統計 儲位 / 商品（可選）
    slot_count = d["儲位"].nunique() if "儲位" in d.columns else None
    item_count = d["商品"].nunique() if "商品" in d.columns else None

    return {
        "df_out": d,
        "零散應出": float(total3),
        "成箱應出": float(combined_2),
        "儲位數": int(slot_count) if slot_count is not None else None,
        "品項數": int(item_count) if item_count is not None else None,
    }


def df_to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="處理結果")
    return bio.getvalue()


def main():
    st.set_page_config(page_title="出貨訂單應出量分析", page_icon="📦", layout="wide")
    inject_logistics_theme()

    set_page(
        "出貨訂單應出量分析",
        icon="📦",
        subtitle="自動讀檔｜計算零散/成箱應出｜輸出處理後明細",
    )

    card_open("📌 上傳明細檔")
    uploaded = st.file_uploader(
        "請上傳明細檔（Excel / CSV / HTML）",
        type=["xlsx", "xls", "xlsb", "xlsm", "csv", "html", "htm"],
        accept_multiple_files=False,
    )
    card_close()

    if not uploaded:
        st.info("請先上傳檔案。")
        return

    with st.spinner("讀取檔案中..."):
        df = robust_read_from_upload(uploaded)

    st.success(f"已讀取：{uploaded.name}（{len(df):,} 筆 / {len(df.columns)} 欄）")

    try:
        with st.spinner("計算中..."):
            result = compute_kpi(df)
    except Exception as e:
        st.error(str(e))
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("出貨訂單庫存零散應出", f"{result['零散應出']:,}")
    c2.metric("出貨訂單庫存成箱應出", f"{result['成箱應出']:,}")
    c3.metric("儲位數", "-" if result["儲位數"] is None else f"{result['儲位數']:,}")
    c4.metric("品項數", "-" if result["品項數"] is None else f"{result['品項數']:,}")

    st.markdown("### 📄 明細預覽（已加入：原始配庫存出貨單位量）")
    st.dataframe(result["df_out"], use_container_width=True, height=520)

    xlsx_bytes = df_to_xlsx_bytes(result["df_out"])
    st.download_button(
        label="💾 下載處理後 Excel",
        data=xlsx_bytes,
        file_name=os.path.splitext(uploaded.name)[0] + "_處理結果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )


if __name__ == "__main__":
    main()
