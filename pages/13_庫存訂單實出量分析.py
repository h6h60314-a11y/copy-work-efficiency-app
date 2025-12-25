# pages/13_庫存訂單實出量分析.py
import io
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="庫存訂單實出量分析", page_icon="📦", layout="wide")
inject_logistics_theme()


# =========================
# Robust reader (Excel/CSV/HTML/TXT + 假 .xls: PROVIDER...)
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


def _read_as_csv_flexible(text: str) -> pd.DataFrame:
    # 依常見分隔符嘗試：Tab、逗號、分號、pipe、再退回「任意空白」
    for sep in ("\t", ",", ";", "|"):
        try:
            df = pd.read_csv(io.StringIO(text), sep=sep, engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            pass
    # whitespace fallback
    return pd.read_csv(io.StringIO(text), sep=r"\s+", engine="python")


def _read_txt(text: str) -> pd.DataFrame:
    low = text.lower()
    if "<html" in low or "<table" in low:
        return _read_as_html(text)
    return _read_as_csv_flexible(text)


def robust_read_upload(uploaded) -> pd.DataFrame:
    name = (uploaded.name or "").lower()
    raw_bytes = uploaded.getvalue() if hasattr(uploaded, "getvalue") else uploaded.read()

    if name.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        return pd.read_excel(io.BytesIO(raw_bytes), engine="openpyxl")

    if name.endswith(".xls"):
        # 真的 xls → xlrd；若失敗，當成假 xls（文字/HTML/CSV）
        try:
            return pd.read_excel(io.BytesIO(raw_bytes), engine="xlrd")
        except Exception:
            text = _decode_text(raw_bytes)
            low = text.lower()
            if "<html" in low or "<table" in low:
                return _read_as_html(text)
            return _read_as_csv_flexible(text)

    if name.endswith(".csv"):
        return _read_as_csv_flexible(_decode_text(raw_bytes))

    if name.endswith((".html", ".htm")):
        return _read_as_html(_decode_text(raw_bytes))

    if name.endswith(".txt"):
        return _read_txt(_decode_text(raw_bytes))

    # fallback
    text = _decode_text(raw_bytes)
    low = text.lower()
    if "<html" in low or "<table" in low:
        return _read_as_html(text)
    return _read_as_csv_flexible(text)


# =========================
# Convert (TXT -> XLSX/XLSM/XLS) then re-read for compute
# =========================
def _df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return bio.getvalue()


def _df_to_xlsm_bytes(df: pd.DataFrame, sheet_name: str = "Sheet1") -> bytes:
    # 內容仍是 OpenXML（無巨集），但副檔名可用 .xlsm
    return _df_to_xlsx_bytes(df, sheet_name=sheet_name)


def _df_to_xls_html_bytes(df: pd.DataFrame, title: str = "Sheet1") -> bytes:
    # Excel 可開啟的 HTML Table（存成 .xls）
    html = df.to_html(index=False, border=0)
    doc = f"""<html><head><meta charset="utf-8"></head><body>
<h3>{title}</h3>
{html}
</body></html>"""
    return doc.encode("utf-8-sig")


def _as_converted_excel_then_read(df_from_txt: pd.DataFrame) -> pd.DataFrame:
    # ✅ 先轉成 XLSX，再用 openpyxl 讀回來（符合你的「先轉再計算」要求）
    xlsx_bytes = _df_to_xlsx_bytes(df_from_txt, sheet_name="TXT_Converted")
    df = pd.read_excel(io.BytesIO(xlsx_bytes), engine="openpyxl", sheet_name="TXT_Converted")
    return df


# =========================
# Business logic
# =========================
REQUIRED_COLS = [
    "箱類型", "packqty", "入數",
    "buyersreference", "BOXTYPE",
    "externorderkey", "SKU", "boxid"
]


def _ensure_cols(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise KeyError(f"❌ 缺少必要欄位：{missing}")


def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)


def _fmt_num(x) -> str:
    try:
        xf = float(x)
        return f"{xf:,.2f}" if abs(xf - round(xf)) > 1e-9 else f"{xf:,.0f}"
    except Exception:
        return str(x)


def compute(df: pd.DataFrame):
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    _ensure_cols(df)

    # 排除「箱類型」含「站所」
    df = df[~df["箱類型"].astype(str).str.contains("站所", na=False)].copy()

    # 型別整理
    df["packqty"] = pd.to_numeric(df["packqty"], errors="coerce").fillna(0)
    df["入數"] = pd.to_numeric(df["入數"], errors="coerce").fillna(0)
    df["BOXTYPE"] = pd.to_numeric(df["BOXTYPE"], errors="coerce")

    # 新增「出貨單位數量」（放在 入數 後方）
    new_col = "出貨單位數量"
    if new_col not in df.columns:
        idx = df.columns.get_loc("入數")
        df.insert(loc=idx + 1, column=new_col, value=0.0)

    # 避免除以 0
    df[new_col] = df["packqty"] / df["入數"].replace(0, pd.NA)
    df[new_col] = pd.to_numeric(df[new_col], errors="coerce").fillna(0)

    # A. 實際出貨量（PTL）
    is_ptl = df["buyersreference"].isin(["GSO", "GCOR"])

    mask0 = is_ptl & (df["BOXTYPE"] == 0)
    total_packqty_box0 = df.loc[mask0, "packqty"].sum()

    mask1_eq = is_ptl & (df["BOXTYPE"] == 1) & (df[new_col] == 1)
    total_packqty_box1_eq = df.loc[mask1_eq, "packqty"].sum()

    mask1_neq = is_ptl & (df["BOXTYPE"] == 1) & (df[new_col] != 1)
    total_units_box1_neq = df.loc[mask1_neq, new_col].sum()

    total_combined = total_packqty_box1_eq + total_units_box1_neq

    filtered = df[is_ptl].copy()
    pivot = (
        filtered
        .pivot_table(index=["externorderkey", "SKU"], aggfunc="size")
        .reset_index(name="count")
    )
    total_groups = int(pivot.shape[0])

    # B. 混庫出貨件數（全表 BOXTYPE 的 boxid 不重複）
    df_box0 = df[df["BOXTYPE"] == 0]
    df_box1 = df[df["BOXTYPE"] == 1]
    count_box0 = int(df_box0["boxid"].nunique())
    count_box1 = int(df_box1["boxid"].nunique())

    result = {
        "實際出貨量PTL-訂單筆數": total_groups,
        "實際出貨量庫存零散PCS": total_packqty_box0,
        "實際出貨量庫存成箱PCS": total_combined,
        "混庫零散出貨件數": count_box0,
        "混庫成箱出貨件數": count_box1,
    }
    return result, df, pivot


def _to_excel_bytes(df: pd.DataFrame, sheet_name: str = "結果"):
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return bio.getvalue()


# =========================
# UI (單頁)
# =========================
def main():
    set_page("庫存訂單實出量分析", icon="📦", subtitle="支援 TXT 先轉 Excel 再計算｜排除箱類型=站所｜實際出貨量（PTL）｜混庫出貨件數")

    card_open("📌 上傳明細檔")
    up = st.file_uploader(
        "請上傳明細檔（XLSX / XLSM / XLS / CSV / HTML / TXT）",
        type=["xlsx", "xlsm", "xls", "csv", "html", "htm", "txt"],
    )
    st.caption("必要欄位：箱類型、packqty、入數、buyersreference、BOXTYPE、externorderkey、SKU、boxid")
    st.info("TXT 會先轉成 XLSX / XLSM / XLS（.xls 為 Excel 可開啟的 HTML 表格格式），再使用轉換後檔案進行計算。")
    st.info("若你的 .xls 出現「PROVIDER」錯誤，代表它是『假 xls』，本頁也已支援自動改用文字/HTML 解析。")
    card_close()

    st.markdown("---")

    if not up:
        return

    # 讀取 + TXT 轉檔流程
    try:
        filename = (up.name or "").lower()
        df_in = robust_read_upload(up)

        converted_pack = None
        if filename.endswith(".txt"):
            # ✅ 先轉成 Excel，再讀回來計算
            df_for_compute = _as_converted_excel_then_read(df_in)

            # 準備三種轉檔供下載
            base = (up.name or "uploaded").rsplit(".", 1)[0]
            converted_pack = {
                "xlsx": (f"{base}_converted.xlsx", _df_to_xlsx_bytes(df_in, "TXT_Converted")),
                "xlsm": (f"{base}_converted.xlsm", _df_to_xlsm_bytes(df_in, "TXT_Converted")),
                "xls": (f"{base}_converted.xls", _df_to_xls_html_bytes(df_in, "TXT_Converted")),
            }
        else:
            df_for_compute = df_in

    except Exception as e:
        st.error(f"讀取失敗：{e}")
        return

    # TXT 轉檔下載區
    if converted_pack:
        card_open("🧩 TXT 轉檔（已完成）")
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            name, data = converted_pack["xlsx"]
            st.download_button(
                "下載：轉檔 XLSX",
                data=data,
                file_name=name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c2:
            name, data = converted_pack["xlsm"]
            st.download_button(
                "下載：轉檔 XLSM",
                data=data,
                file_name=name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with c3:
            name, data = converted_pack["xls"]
            st.download_button(
                "下載：轉檔 XLS（Excel可開）",
                data=data,
                file_name=name,
                mime="application/vnd.ms-excel",
                use_container_width=True,
            )
        st.success("TXT 已完成轉檔，系統已改用「轉換後的 Excel」進行計算。")
        card_close()

        st.markdown("---")

    # 計算
    card_open("📊 計算結果")
    try:
        result, df_after, pivot = compute(df_for_compute)
    except Exception as e:
        st.error(f"計算失敗：{e}")
        card_close()
        return

    left, right = st.columns([2, 1], gap="large")
    with left:
        st.markdown("#### 實際出貨量（PTL）")
        st.metric("實際出貨量PTL-訂單筆數", _fmt_int(result["實際出貨量PTL-訂單筆數"]))
        st.metric("實際出貨量庫存零散PCS", _fmt_num(result["實際出貨量庫存零散PCS"]))
        st.metric("實際出貨量庫存成箱PCS", _fmt_num(result["實際出貨量庫存成箱PCS"]))

    with right:
        st.markdown("#### 混庫出貨件數")
        st.metric("混庫零散出貨件數", _fmt_int(result["混庫零散出貨件數"]))
        st.metric("混庫成箱出貨件數", _fmt_int(result["混庫成箱出貨件數"]))
    card_close()

    st.markdown("---")

    # 明細 / 下載
    card_open("🧾 明細預覽 / 匯出")
    st.markdown("#### ✅ 明細（已新增：出貨單位數量，並排除箱類型含站所）")
    st.dataframe(df_after, use_container_width=True, height=420)

    st.markdown("#### ✅ PTL 訂單筆數明細（externorderkey + SKU）")
    st.dataframe(pivot, use_container_width=True, height=260)

    st.markdown("#### 💾 下載結果")
    out1 = _to_excel_bytes(df_after, sheet_name="明細_處理後")
    st.download_button(
        "下載：庫存訂單實出量分析_明細.xlsx",
        data=out1,
        file_name="庫存訂單實出量分析_明細.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    out2 = _to_excel_bytes(pivot, sheet_name="PTL_訂單筆數明細")
    st.download_button(
        "下載：庫存訂單實出量分析_PTL訂單筆數明細.xlsx",
        data=out2,
        file_name="庫存訂單實出量分析_PTL訂單筆數明細.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    card_close()


if __name__ == "__main__":
    main()
