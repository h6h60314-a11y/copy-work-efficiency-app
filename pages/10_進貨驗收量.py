# pages/10_進貨驗收量.py
import io
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="進貨驗收量｜大樹KPI", page_icon="📥", layout="wide")
inject_logistics_theme()

SHEET_DEFAULT = "採購單驗收量明細"

REQ_COLS = ["入庫類型", "驗收入庫數量", "供應商代號", "DC採購單號", "商品品號"]


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


@st.cache_data(show_spinner=False)
def _read_excel_bytes(file_name: str, file_bytes: bytes, sheet_name: str) -> pd.DataFrame:
    ext = file_name.lower().split(".")[-1]

    bio = io.BytesIO(file_bytes)

    if ext == "xlsb":
        # 需要 requirements.txt 加 pyxlsb
        df = pd.read_excel(bio, sheet_name=sheet_name, engine="pyxlsb")
    else:
        # xlsx / xlsm
        df = pd.read_excel(bio, sheet_name=sheet_name, engine="openpyxl")

    return _normalize_cols(df)


def _compute_stats(df: pd.DataFrame, inbound_type: str) -> dict:
    df = df.copy()

    # 欄位保護
    for c in REQ_COLS:
        if c not in df.columns:
            raise KeyError(f"找不到必要欄位：{c}")

    df_type = df[df["入庫類型"].astype(str).str.strip().eq(inbound_type)].copy()
    df_type["驗收入庫數量"] = pd.to_numeric(df_type["驗收入庫數量"], errors="coerce").fillna(0)

    return {
        "type": inbound_type,
        "unique_suppliers": int(df_type["供應商代號"].nunique(dropna=True)),
        "unique_dc_orders": int(df_type["DC採購單號"].nunique(dropna=True)),
        "unique_products": int(df_type["商品品號"].nunique(dropna=True)),
        "total_qty": float(df_type["驗收入庫數量"].sum()),
    }


def _fmt_qty(x: float) -> str:
    # 數量通常是整數，但保留小數安全
    if abs(x - round(x)) < 1e-9:
        return f"{int(round(x)):,}"
    return f"{x:,.2f}"


def main():
    set_page(
        "進貨驗收量",
        icon="📥",
        subtitle="大樹KPI｜採購單驗收量明細｜GPO / GXPO 統計",
    )

    card_open("📌 上傳檔案")
    up = st.file_uploader("上傳 .xlsb 或 .xlsx", type=["xlsb", "xlsx", "xlsm"])
    sheet_name = st.text_input("工作表名稱", value=SHEET_DEFAULT)
    card_close()

    if not up:
        st.info("請先上傳檔案後再執行統計。")
        return

    with st.spinner("讀取資料中..."):
        try:
            df = _read_excel_bytes(up.name, up.getvalue(), sheet_name)
        except Exception as e:
            st.error(f"讀取失敗：{e}")
            st.stop()

    # 基本檢查
    missing = [c for c in REQ_COLS if c not in df.columns]
    if missing:
        st.error(f"缺少必要欄位：{', '.join(missing)}")
        st.write("目前欄位：", list(df.columns))
        st.stop()

    # 統計
    types = ["GPO", "GXPO"]
    stats_rows = []
    for t in types:
        stats_rows.append(_compute_stats(df, t))

    overall_unique_suppliers = int(df["供應商代號"].nunique(dropna=True))

    # 顯示結果（條列 + 指標）
    card_open("📊 統計結果")
    cols = st.columns(len(types))
    for i, s in enumerate(stats_rows):
        with cols[i]:
            st.subheader(f"{s['type']} 類型")
            st.metric("不重複供應商代號", f"{s['unique_suppliers']:,} 筆")
            st.metric("不重複 DC採購單號", f"{s['unique_dc_orders']:,} 筆")
            st.metric("不重複 商品品號", f"{s['unique_products']:,} 筆")
            st.metric("驗收入庫數量總量", _fmt_qty(s["total_qty"]))

    st.divider()
    st.metric("總明細：不重複供應商代號總數", f"{overall_unique_suppliers:,} 筆")
    card_close()

    # 表格 + 下載
    out_df = pd.DataFrame(
        [
            {
                "入庫類型": r["type"],
                "不重複供應商代號數": r["unique_suppliers"],
                "不重複DC採購單號數": r["unique_dc_orders"],
                "不重複商品品號數": r["unique_products"],
                "驗收入庫數量總量": r["total_qty"],
            }
            for r in stats_rows
        ]
    )
    out_df.loc[len(out_df)] = {
        "入庫類型": "總明細",
        "不重複供應商代號數": overall_unique_suppliers,
        "不重複DC採購單號數": None,
        "不重複商品品號數": None,
        "驗收入庫數量總量": None,
    }

    card_open("📤 匯出")
    st.dataframe(out_df, use_container_width=True)

    csv_bytes = out_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("下載 CSV", data=csv_bytes, file_name="進貨驗收量_統計.csv", mime="text/csv")
    card_close()


if __name__ == "__main__":
    main()
