# pages/14_每日上架分析.py
import io
import re
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

COL_LOC_IDX = 1   # B 欄（0-based）
COL_QTY_IDX = 2   # C 欄（0-based）
# ============================================


def _pick_engine_by_ext(ext: str):
    ext = (ext or "").lower()
    if ext in (".xlsx", ".xlsm"):
        return ["openpyxl"]
    if ext == ".xlsb":
        return ["pyxlsb"]  # 需要 requirements.txt 安裝 pyxlsb
    if ext == ".xls":
        return ["xlrd"]    # 需要安裝 xlrd
    return ["openpyxl", "pyxlsb", "xlrd"]


def _read_excel_bytes(uploaded, sheet_prefer="前一日上架清單"):
    """
    支援 xlsx/xlsm/xlsb/xls，依副檔名選 engine，並自動挑工作表：
    優先用「前一日上架清單」，沒有就用第一張。
    """
    name = uploaded.name
    ext = "." + name.split(".")[-1].lower() if "." in name else ""
    data = uploaded.getvalue()

    engines = _pick_engine_by_ext(ext)
    last_err = None

    for eng in engines:
        try:
            xf = pd.ExcelFile(io.BytesIO(data), engine=eng)
            sheet_name = sheet_prefer if sheet_prefer in xf.sheet_names else xf.sheet_names[0]

            df = pd.read_excel(
                io.BytesIO(data),
                sheet_name=sheet_name,
                engine=eng,
                header=None,
            )
            return df, sheet_name, eng

        except ImportError as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            continue

    # 走到這裡表示所有 engine 都失敗
    msg = f"Excel 讀取失敗：{last_err}"
    # 特別針對 xlsb 給提示
    if ext == ".xlsb":
        msg += "\n\n⚠️ 你上傳的是 .xlsb，請確認 requirements.txt 有加入：pyxlsb"
    if ext == ".xls":
        msg += "\n\n⚠️ 你上傳的是 .xls，請確認 requirements.txt 有加入：xlrd"
    raise RuntimeError(msg)


def _compute(df: pd.DataFrame):
    if df is None or df.empty or df.shape[1] <= COL_QTY_IDX:
        raise ValueError("資料為空或欄位不足，請確認檔案內容（至少要有 B/C 欄）。")

    loc = df.iloc[:, COL_LOC_IDX].astype("string")  # 上架儲位
    qty = pd.to_numeric(df.iloc[:, COL_QTY_IDX], errors="coerce").fillna(0)  # 上架數量

    # 排除規則（只看上架儲位）
    pattern = "|".join(re.escape(x) for x in EXCLUDE_PATTERNS)
    mask_exclude = loc.str.contains(pattern, na=False)

    count_rows = int((~mask_exclude).sum())
    sum_qty = float(qty.loc[~mask_exclude].sum())
    excluded_rows = int(mask_exclude.sum())

    return count_rows, sum_qty, excluded_rows


def main():
    set_page("每日上架分析", icon="📦", subtitle="前一日上架清單｜支援 XLSB｜排除指定儲位代碼｜統計上架筆數與上架總量")

    card_open("📌 上傳檔案（XLSX / XLSM / XLSB / XLS）")
    st.caption("讀取工作表：優先「前一日上架清單」，沒有則取第一張。")
    st.caption("欄位規則：B欄=上架儲位、C欄=上架數量（從第 1 列開始依檔案實際內容）。")
    st.caption("排除條件：上架儲位包含 " + " / ".join(EXCLUDE_PATTERNS))

    uploaded = st.file_uploader(
        "選擇檔案",
        type=["xlsx", "xlsm", "xlsb", "xls"],
        accept_multiple_files=False,
    )
    card_close()

    if not uploaded:
        return

    try:
        with st.spinner("資料讀取中…"):
            df, sheet_name, engine_used = _read_excel_bytes(uploaded)

        with st.spinner("計算中…"):
            count_rows, sum_qty, excluded_rows = _compute(df)

        st.success(
            f"已讀取：{uploaded.name}（工作表：{sheet_name}｜engine：{engine_used}｜{df.shape[0]:,} 列｜{df.shape[1]:,} 欄）"
        )

        a, b, c = st.columns(3, gap="large")
        with a:
            st.metric("上架筆數（排除後）", f"{count_rows:,}")
        with b:
            st.metric("上架總數量（排除後）", f"{sum_qty:,.0f}")
        with c:
            st.metric("排除筆數", f"{excluded_rows:,}")

        st.markdown("#### 明細預覽（前 200 列）")
        st.dataframe(df.head(200), use_container_width=True)

    except Exception as e:
        st.error(str(e))


if __name__ == "__main__":
    main()
