# pages/14_每日上架分析.py
import io
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="每日上架分析", page_icon="📦", layout="wide")
inject_logistics_theme()

# ================== 固定規則 ==================
EXCLUDE_PATTERNS = [
    "PD99", "QC99", "GRP", "CGS",
    "999", "GX010", "JCPL", "GREAT0001X",
]

COL_LOC_IDX = 1   # B 欄 → 上架儲位（0-based）
COL_QTY_IDX = 2   # C 欄 → 上架數量（0-based）
# ============================================


def _read_excel_from_upload(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> pd.DataFrame:
    # Streamlit uploader -> bytes -> pandas
    data = uploaded_file.getvalue()
    xls = pd.ExcelFile(io.BytesIO(data), engine="openpyxl")

    sheet_name = "前一日上架清單" if "前一日上架清單" in xls.sheet_names else xls.sheet_names[0]

    df = pd.read_excel(
        io.BytesIO(data),
        sheet_name=sheet_name,
        engine="openpyxl",
        header=None,
    )
    return df, sheet_name


def _compute(df: pd.DataFrame):
    if df is None or df.empty or df.shape[1] <= COL_QTY_IDX:
        raise ValueError("資料為空或欄位不足，請確認檔案內容。")

    loc = df.iloc[:, COL_LOC_IDX].astype("string")  # 上架儲位
    qty = pd.to_numeric(df.iloc[:, COL_QTY_IDX], errors="coerce").fillna(0)  # 上架數量

    # 排除（只看上架儲位）
    pattern = "|".join(map(lambda x: f"({x})", EXCLUDE_PATTERNS))
    mask_exclude = loc.str.contains(pattern, na=False)

    count_rows = int((~mask_exclude).sum())
    sum_qty = float(qty.loc[~mask_exclude].sum())

    return {
        "上架筆數": count_rows,
        "上架總數量": sum_qty,
        "排除筆數": int(mask_exclude.sum()),
    }


def main():
    set_page("每日上架分析", icon="📦", subtitle="前一日上架清單｜排除指定儲位代碼｜統計上架筆數與上架總量")

    card_open("📌 上傳『前一日上架清單.xlsx』")
    st.caption("規則：讀取工作表「前一日上架清單」（若不存在則取第一張），B欄=上架儲位、C欄=上架數量。")
    st.caption("排除條件：上架儲位包含 " + " / ".join(EXCLUDE_PATTERNS))

    uploaded = st.file_uploader(
        "選擇檔案（xlsx）",
        type=["xlsx"],
        accept_multiple_files=False,
    )
    card_close()

    if not uploaded:
        return

    try:
        with st.spinner("資料讀取中…"):
            df, sheet_name = _read_excel_from_upload(uploaded)

        with st.spinner("計算中…"):
            result = _compute(df)

        st.success(f"已讀取：{uploaded.name}（工作表：{sheet_name}｜{df.shape[0]:,} 列｜{df.shape[1]:,} 欄）")

        # ✅ 指標（清楚直觀）
        a, b, c = st.columns(3, gap="large")
        with a:
            st.metric("上架筆數（排除後）", f"{result['上架筆數']:,}")
        with b:
            st.metric("上架總數量（排除後）", f"{result['上架總數量']:,.0f}")
        with c:
            st.metric("排除筆數", f"{result['排除筆數']:,}")

        # ✅ 預覽（避免太重，給前 200 列）
        st.markdown("#### 明細預覽（前 200 列）")
        st.dataframe(df.head(200), use_container_width=True)

    except Exception as e:
        st.error(f"讀取或計算失敗：{e}")


if __name__ == "__main__":
    main()
