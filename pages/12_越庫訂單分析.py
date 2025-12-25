# pages/12_越庫訂單分析.py
import io
import re
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="越庫訂單分析", page_icon="🧾", layout="wide")
inject_logistics_theme()

# =========================
# Robust reader (Excel/CSV/HTML + 假 .xls: PROVIDER...)
# =========================
def _decode_text(b: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp950", "big5", "latin1"):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode("utf-8", errors="ignore")


def _read_as_html(text: str) -> pd.DataFrame:
    tables = pd.read_html(text)
    if not tables:
        raise ValueError("HTML 內沒有可辨識的表格")
    return tables[0]


def _read_as_csv(text: str) -> pd.DataFrame:
    # 先猜常見分隔（tab > comma > semicolon）
    for sep in ("\t", ",", ";"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            pass
    return pd.read_csv(io.StringIO(text), sep=None, engine="python")


def robust_read_upload(uploaded) -> pd.DataFrame:
    """
    讀取上傳檔（xls/xlsx/csv/html）
    - 先用 Excel 讀
    - 若遇到「Expected BOF record; found b'PROVIDER'」這種假 xls，
      會改用文字解析（HTML / CSV / TSV）
    """
    name = (uploaded.name or "").lower()
    raw_bytes = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()

    # xlsx / xlsm
    if name.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        return pd.read_excel(io.BytesIO(raw_bytes), engine="openpyxl")

    # xls
    if name.endswith(".xls"):
        try:
            return pd.read_excel(io.BytesIO(raw_bytes), engine="xlrd")
        except Exception:
            text = _decode_text(raw_bytes)
            low = text.lower()
            if "<html" in low or "<table" in low:
                return _read_as_html(text)
            return _read_as_csv(text)

    # csv
    if name.endswith(".csv"):
        return _read_as_csv(_decode_text(raw_bytes))

    # html
    if name.endswith((".html", ".htm")):
        return _read_as_html(_decode_text(raw_bytes))

    # 其他：用內容猜
    text = _decode_text(raw_bytes)
    low = text.lower()
    if "<html" in low or "<table" in low:
        return _read_as_html(text)
    return _read_as_csv(text)


# =========================
# Business logic
# =========================
NEED_COLS_1 = ["單號", "單據類型", "作業類型", "應作量", "實作量"]
NEED_COLS_2 = ["SONO", "CLOSE_USER"]

PATTERN_EXCLUDE = re.compile(r"FT0[3-9]|FT1[0-1]", re.IGNORECASE)


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()
    return df


def _ensure_cols(df: pd.DataFrame, need: list, who: str):
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"❌「{who}」缺少必要欄位：{missing}")


def compute_crossdock(df1: pd.DataFrame, df2: pd.DataFrame):
    """
    對齊你原本 Tkinter 腳本邏輯：
    1) df2: SONO->CLOSE_USER 映射到 df1 單號，生成 比對備註
    2) 剔除 比對備註 含 FT03~FT11
    3) 單號清理：移除 B / C
    4) 只針對 單據類型 == '越庫' 統計：
       - 零散/成箱：應作量、實作量總和
       - 訂單筆數（單號不重複）
    """
    df1 = _normalize_cols(df1)
    df2 = _normalize_cols(df2)

    _ensure_cols(df1, NEED_COLS_1, "檔案①（單據明細）")
    _ensure_cols(df2, NEED_COLS_2, "檔案②（已結案查詢）")

    # types
    df1 = df1.copy()
    df2 = df2.copy()

    df1["單號"] = df1["單號"].astype(str).str.strip()
    df2["SONO"] = df2["SONO"].astype(str).str.strip()

    # map CLOSE_USER
    close_map = df2.set_index("SONO")["CLOSE_USER"]
    df1["比對備註"] = df1["單號"].map(close_map).fillna("無對應").astype(str)

    # 剔除 FT03~FT11
    mask_ex = df1["比對備註"].str.contains(PATTERN_EXCLUDE, na=False)
    df1 = df1[~mask_ex].copy()

    # 清理 B/C（一定要在不重複前）
    df1["單號"] = df1["單號"].astype(str).str.replace("B", "", regex=False).str.replace("C", "", regex=False)

    # 數值欄位轉 numeric
    df1["應作量"] = pd.to_numeric(df1["應作量"], errors="coerce").fillna(0)
    df1["實作量"] = pd.to_numeric(df1["實作量"], errors="coerce").fillna(0)

    # 越庫篩選
    cond = df1["單據類型"].astype(str).str.strip().eq("越庫")
    dfx = df1.loc[cond].copy()

    # 統計
    scatter = dfx["作業類型"].astype(str).str.strip().eq("零散")
    box = dfx["作業類型"].astype(str).str.strip().eq("成箱")

    stats = {
        "越庫_零散_應作量": float(dfx.loc[scatter, "應作量"].sum()),
        "越庫_成箱_應作量": float(dfx.loc[box, "應作量"].sum()),
        "越庫_零散_實作量": float(dfx.loc[scatter, "實作量"].sum()),
        "越庫_成箱_實作量": float(dfx.loc[box, "實作量"].sum()),
        "訂單筆數": int(dfx["單號"].nunique()),
        "剔除筆數_FT03_FT11": int(mask_ex.sum()),
        "越庫筆數": int(len(dfx)),
    }

    # 插入「比對備註」到第18欄（0-based index 17）
    cols = list(df1.columns)
    if "比對備註" in cols:
        cols.remove("比對備註")
        insert_at = 17 if len(cols) >= 17 else len(cols)
        cols.insert(insert_at, "比對備註")
        df1 = df1[cols]

    return stats, df1, dfx


def _fmt_num(x: float) -> str:
    try:
        return f"{x:,.0f}" if abs(x - round(x)) < 1e-9 else f"{x:,.2f}"
    except Exception:
        return str(x)


def _to_excel_bytes(df: pd.DataFrame, sheet_name: str = "結果"):
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return bio.getvalue()


# =========================
# UI
# =========================
def main():
    set_page("越庫訂單分析", icon="🧾", subtitle="上傳兩份報表｜剔除 FT03~FT11｜越庫(零散/成箱) 應作/實作｜訂單筆數")

    tab_up, tab_res, tab_detail = st.tabs(["📌 上傳檔案", "📊 計算結果", "🧾 明細預覽/匯出"])

    with tab_up:
        card_open("📌 上傳檔案")
        st.caption("檔案①：單據明細（需含：單號、單據類型、作業類型、應作量、實作量）")
        f1 = st.file_uploader(
            "選擇檔案①（單據明細）",
            type=["xlsx", "xlsm", "xls", "csv", "html", "htm"],
            key="f1",
        )
        st.caption("檔案②：已結案查詢（需含：SONO、CLOSE_USER）")
        f2 = st.file_uploader(
            "選擇檔案②（已結案查詢）",
            type=["xlsx", "xlsm", "xls", "csv", "html", "htm"],
            key="f2",
        )

        st.markdown("---")
        st.info("若你的 .xls 出現「PROVIDER」錯誤，代表它是『假 xls』，此頁已支援自動改用文字/HTML 解析。")
        card_close()

    # 讀檔與計算（有檔才跑）
    stats = None
    df_out = None
    dfx = None
    err = None

    if f1 and f2:
        try:
            df1 = robust_read_upload(f1)
            df2 = robust_read_upload(f2)
            stats, df_out, dfx = compute_crossdock(df1, df2)
        except Exception as e:
            err = e

    with tab_res:
        card_open("📊 計算結果")
        if err:
            st.error(f"讀取或計算失敗：{err}")
        elif not (f1 and f2):
            st.warning("請先到「上傳檔案」上傳兩份檔案。")
        else:
            # 直向呈現（你要的：每組兩個指標直向）
            left, right = st.columns([1, 1], gap="large")

            with left:
                st.markdown("### 越庫訂單量")
                st.metric("越庫＋零散｜應作量總和", _fmt_num(stats["越庫_零散_應作量"]))
                st.metric("越庫＋成箱｜應作量總和", _fmt_num(stats["越庫_成箱_應作量"]))
                st.metric("訂單筆數（越庫/單號不重複）", _fmt_num(stats["訂單筆數"]))

            with right:
                st.markdown("### 實作/清理狀態")
                st.metric("越庫＋零散｜實作量總和", _fmt_num(stats["越庫_零散_實作量"]))
                st.metric("越庫＋成箱｜實作量總和", _fmt_num(stats["越庫_成箱_實作量"]))
                st.metric("已剔除筆數（FT03~FT11）", _fmt_num(stats["剔除筆數_FT03_FT11"]))

            st.caption(f"越庫明細筆數：{stats['越庫筆數']:,}（剔除後）")

        card_close()

    with tab_detail:
        card_open("🧾 明細預覽/匯出")
        if err:
            st.error(f"讀取或計算失敗：{err}")
        elif not (f1 and f2):
            st.warning("請先到「上傳檔案」上傳兩份檔案。")
        else:
            st.markdown("#### ✅ 剔除後明細（已加入：比對備註）")
            st.dataframe(df_out, use_container_width=True, height=420)

            c1, c2 = st.columns([1, 1], gap="large")
            with c1:
                st.markdown("#### ✅ 只看『越庫』明細")
                st.dataframe(dfx, use_container_width=True, height=420)

            with c2:
                st.markdown("#### 💾 匯出 Excel")
                excel_bytes = _to_excel_bytes(df_out, sheet_name="剔除後明細")
                st.download_button(
                    "下載：剔除後明細.xlsx",
                    data=excel_bytes,
                    file_name="越庫訂單分析_剔除後明細.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        card_close()


if __name__ == "__main__":
    main()
