# pages/14_每日上架分析.py
import re
from io import BytesIO

import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

# ================== 固定規則 ==================
EXCLUDE_PATTERNS = ["PD99", "QC99", "GRP", "CGS", "999", "GX010", "JCPL", "GREAT0001X"]

# Excel 欄位位置（0-based）
COL_LOC_IDX = 1  # B 欄 → 上架儲位
COL_QTY_IDX = 2  # C 欄 → 上架數量
# =============================================


def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return "0"


def _fmt_qty(x) -> str:
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"


def _is_fake_xls_provider(raw: bytes) -> bool:
    # 常見「假 xls」會以 PROVIDER 開頭（實際是 HTML/文字表格）
    head = raw[:64].upper()
    return b"PROVIDER" in head


def _read_fake_xls_text_or_html(raw: bytes) -> pd.DataFrame:
    # 先嘗試 HTML table
    text = raw.decode("utf-8", errors="ignore")
    try:
        tables = pd.read_html(text)
        if tables:
            return tables[0]
    except Exception:
        pass

    # 再嘗試用分隔符猜測（tab / comma）
    # 很多系統匯出是 tab-separated
    for sep in ["\t", ",", ";", "|"]:
        try:
            df = pd.read_csv(BytesIO(raw), sep=sep, encoding="utf-8", engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            continue

    raise ValueError("無法以 HTML/文字表格解析此『假 xls』檔案。")


def _pick_sheet_name(xls: pd.ExcelFile) -> str:
    preferred = "前一日上架清單"
    if preferred in xls.sheet_names:
        return preferred
    # 有些檔名可能多了空白
    for s in xls.sheet_names:
        if str(s).strip() == preferred:
            return s
    return xls.sheet_names[0]


def _detect_header(df_head: pd.DataFrame) -> bool:
    """判斷第一列是否像表頭（含 '上架儲位' 或 '上架數量'）"""
    if df_head is None or df_head.empty:
        return False
    first_row = df_head.iloc[0].astype("string").fillna("")
    tokens = "".join(first_row.tolist())
    return ("上架儲位" in tokens) or ("上架數量" in tokens)


def _read_uploaded_table(uploaded) -> tuple[pd.DataFrame, dict]:
    raw = uploaded.getvalue()
    name = uploaded.name
    ext = name.split(".")[-1].lower().strip()

    info = {"engine": "", "sheet": "", "note": ""}

    # ---- Excel family ----
    if ext in {"xlsx", "xlsm", "xltx", "xltm"}:
        engine = "openpyxl"
        info["engine"] = engine
        bio = BytesIO(raw)
        xls = pd.ExcelFile(bio, engine=engine)
        sheet = _pick_sheet_name(xls)
        info["sheet"] = sheet

        # 先讀頭幾列判斷表頭
        df_head = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine, nrows=5, header=None)
        has_header = _detect_header(df_head)

        df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine, header=0 if has_header else None)
        return df, info

    if ext == "xlsb":
        engine = "pyxlsb"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheet = _pick_sheet_name(xls)
        info["sheet"] = sheet

        df_head = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine, nrows=5, header=None)
        has_header = _detect_header(df_head)

        df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine, header=0 if has_header else None)
        return df, info

    if ext == "xls":
        # 先判斷是否為假 xls
        if _is_fake_xls_provider(raw):
            info["engine"] = "text/html"
            info["note"] = "偵測到『假 xls』（PROVIDER）→ 已改用文字/HTML 解析"
            df = _read_fake_xls_text_or_html(raw)
            return df, info

        # 真 xls 用 xlrd
        engine = "xlrd"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheet = _pick_sheet_name(xls)
        info["sheet"] = sheet

        df_head = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine, nrows=5, header=None)
        has_header = _detect_header(df_head)

        df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine, header=0 if has_header else None)
        return df, info

    raise ValueError("不支援的檔案格式。請上傳 XLSX / XLSM / XLSB / XLS。")


def _extract_loc_qty(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    # 1) 優先用欄名（若有表頭）
    cols = [str(c).strip() for c in df.columns]
    df.columns = cols

    if "上架儲位" in df.columns:
        loc = df["上架儲位"].astype("string")
    else:
        if df.shape[1] <= COL_LOC_IDX:
            raise KeyError("欄位不足：找不到 B 欄（上架儲位）。")
        loc = df.iloc[:, COL_LOC_IDX].astype("string")

    if "上架數量" in df.columns:
        qty = pd.to_numeric(df["上架數量"], errors="coerce").fillna(0)
    else:
        if df.shape[1] <= COL_QTY_IDX:
            raise KeyError("欄位不足：找不到 C 欄（上架數量）。")
        qty = pd.to_numeric(df.iloc[:, COL_QTY_IDX], errors="coerce").fillna(0)

    return loc, qty


def _compute(loc: pd.Series, qty: pd.Series) -> dict:
    pattern = "|".join(re.escape(x) for x in EXCLUDE_PATTERNS)
    mask_exclude = loc.fillna("").str.contains(pattern, na=False)

    # 只計算「非排除」的筆數/數量
    keep = ~mask_exclude
    count_rows = int(keep.sum())
    sum_qty = float(qty.loc[keep].sum())
    exclude_count = int(mask_exclude.sum())

    return {
        "上架筆數": count_rows,
        "上架總數量": sum_qty,
        "排除筆數": exclude_count,
        "mask_exclude": mask_exclude,
    }


def _to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="每日上架分析_剔除後")
    return out.getvalue()


def main():
    st.set_page_config(page_title="每日上架分析", page_icon="📦", layout="wide")
    inject_logistics_theme()

    set_page(
        "每日上架分析",
        icon="📦",
        subtitle="前一日上架清單｜支援 XLSB｜排除指定儲位代碼｜統計上架筆數與上架總量",
    )

    card_open("📌 上傳檔案（XLSX / XLSM / XLSB / XLS）")

    st.caption("讀取工作表：優先「前一日上架清單」，沒有則取第一張。")
    st.caption("欄位規則：B 欄＝上架儲位、C 欄＝上架數量（若有表頭會優先用欄名）。")
    st.caption("排除條件：上架儲位包含 " + " / ".join(EXCLUDE_PATTERNS))

    uploaded = st.file_uploader(
        "選擇檔案",
        type=["xlsx", "xlsm", "xlsb", "xls"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )
    card_close()

    if not uploaded:
        st.stop()

    with st.spinner("資料讀取中…"):
        try:
            df, info = _read_uploaded_table(uploaded)
        except Exception as e:
            st.error(f"讀取失敗：{e}")
            st.stop()

    rows, cols = df.shape
    msg = f"已讀取：{uploaded.name}"
    if info.get("sheet"):
        msg += f"（工作表：{info['sheet']}｜engine：{info.get('engine','')}｜{rows:,} 列｜{cols:,} 欄）"
    else:
        msg += f"（engine：{info.get('engine','')}｜{rows:,} 列｜{cols:,} 欄）"
    st.success(msg)

    if info.get("note"):
        st.info(info["note"])

    # --- 計算 ---
    try:
        loc, qty = _extract_loc_qty(df)
        result = _compute(loc, qty)
    except Exception as e:
        st.error(f"計算失敗：{e}")
        st.stop()

    # ✅ 上架分析：不要大框框，直向呈現且更順眼
    st.markdown("### 上架分析")
    st.markdown(
        """
<style>
div[data-testid="stMetric"]{ padding: 2px 0 !important; }
div[data-testid="stMetric"] label{
  font-size: 14px !important;
  font-weight: 750 !important;
  color: rgba(15,23,42,.76) !important;
}
div[data-testid="stMetricValue"]{
  font-size: 26px !important;
  font-weight: 900 !important;
  letter-spacing: .2px !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

    st.metric("上架筆數", _fmt_int(result["上架筆數"]))
    st.metric("上架總數量", _fmt_qty(result["上架總數量"]))
    st.caption(f"排除筆數：{_fmt_int(result['排除筆數'])}（儲位命中排除代碼）")

    # --- 匯出（剔除後）---
    df_keep = df.loc[~result["mask_exclude"]].copy()
    xlsx_bytes = _to_xlsx_bytes(df_keep)
    st.download_button(
        "⬇️ 匯出（剔除後）Excel",
        data=xlsx_bytes,
        file_name=f"{uploaded.name.rsplit('.',1)[0]}_每日上架分析_剔除後.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )

    # --- 預覽 ---
    st.markdown("### 明細預覽（前 200 列）")
    st.dataframe(df.head(200), use_container_width=True, height=420)


if __name__ == "__main__":
    main()
