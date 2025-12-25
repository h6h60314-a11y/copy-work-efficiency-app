# pages/16_門市到貨異常率.py
import pandas as pd
import streamlit as st
from io import BytesIO

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# -------------------------
# Format helpers
# -------------------------
def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return "0"


def _fmt_num(x) -> str:
    try:
        return f"{float(x):,}"
    except Exception:
        return "0"


# -------------------------
# Robust reading helpers (XLSX/XLSM/XLSB/XLS + fake xls PROVIDER)
# -------------------------
def _is_fake_xls_provider(raw: bytes) -> bool:
    return b"PROVIDER" in raw[:256].upper()


def _read_fake_xls_text_or_html(raw: bytes) -> pd.DataFrame:
    text = raw.decode("utf-8", errors="ignore")

    # 1) HTML table
    try:
        tables = pd.read_html(text)
        if tables:
            return tables[0]
    except Exception:
        pass

    # 2) CSV/TSV fallback
    for sep in ["\t", ",", ";", "|"]:
        try:
            df = pd.read_csv(BytesIO(raw), sep=sep, encoding="utf-8", engine="python")
            if df.shape[1] >= 2:
                return df
        except Exception:
            continue

    raise ValueError("無法以 HTML/文字表格解析此『假 xls』（PROVIDER）檔案。")


def _pick_sheet_name(xls: pd.ExcelFile) -> str:
    # 優先「工作表1」，沒有就第一張
    preferred = "工作表1"
    if preferred in xls.sheet_names:
        return preferred
    return xls.sheet_names[0]


def _read_uploaded_table(uploaded) -> tuple[pd.DataFrame, dict]:
    raw = uploaded.getvalue()
    name = uploaded.name
    ext = name.split(".")[-1].lower().strip()

    info = {"engine": "", "sheet": "", "note": ""}

    if ext in {"xlsx", "xlsm", "xltx", "xltm"}:
        engine = "openpyxl"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheet = _pick_sheet_name(xls)
        info["sheet"] = sheet
        df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine)
        return df, info

    if ext == "xlsb":
        engine = "pyxlsb"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheet = _pick_sheet_name(xls)
        info["sheet"] = sheet
        df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine)
        return df, info

    if ext == "xls":
        # 假 xls（PROVIDER）
        if _is_fake_xls_provider(raw):
            info["engine"] = "text/html"
            info["note"] = "偵測到『假 xls』（PROVIDER）→ 已改用文字/HTML 解析"
            df = _read_fake_xls_text_or_html(raw)
            return df, info

        engine = "xlrd"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheet = _pick_sheet_name(xls)
        info["sheet"] = sheet
        df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine)
        return df, info

    raise ValueError("不支援的檔案格式。請上傳 XLSX / XLSM / XLSB / XLS。")


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _validate_cols(df: pd.DataFrame) -> None:
    need = ["箱號", "異常原因", "應到數量", "實到數量"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}（目前欄位：{list(df.columns)[:30]} ...）")


# -------------------------
# Logic
# -------------------------
def _build_year_date(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["箱號"] = df["箱號"].astype(str)

    # 若原本就有年/日期欄位，先移除避免重複
    if "年" in df.columns:
        df.drop(columns=["年"], inplace=True, errors="ignore")
    if "日期" in df.columns:
        df.drop(columns=["日期"], inplace=True, errors="ignore")

    df.insert(df.columns.get_loc("箱號") + 1, "年", df["箱號"].str[:4])
    df.insert(df.columns.get_loc("箱號") + 2, "日期", df["箱號"].str[4:8])

    return df


def _to_numeric(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ["應到數量", "實到數量", "差異", "數量"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def _compute(df: pd.DataFrame) -> dict:
    # 差異 = 實到 - 應到
    if "差異" in df.columns:
        df = df.drop(columns=["差異"], errors="ignore")
    idx_actual = df.columns.get_loc("實到數量")
    df.insert(idx_actual + 1, "差異", 0)
    df["差異"] = df["實到數量"] - df["應到數量"]

    count_box = int(df["箱號"].dropna().shape[0])

    # 多貨 / 短少 依異常原因統計差異
    sum_excess = float(df.loc[df["異常原因"] == "到貨多貨", "差異"].sum())
    sum_shortage = float(df.loc[df["異常原因"] == "到貨短少", "差異"].sum())

    # 凹損/破損/漏液：以「數量」加總（若沒有數量欄位就視為 0）
    if "數量" in df.columns:
        sum_defect = float(df.loc[df["異常原因"].isin(["到貨凹損", "到貨破損", "到貨漏液"]), "數量"].sum())
    else:
        sum_defect = 0.0

    return {
        "箱號總筆數": count_box,
        "到貨多貨總差異": sum_excess,
        "到貨短少總差異": sum_shortage,
        "到貨凹損/破損/漏液總數量": sum_defect,
        "df": df,
    }


def _to_xlsx_bytes(df: pd.DataFrame) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="處理後明細")
    bio.seek(0)
    return bio.getvalue()


# -------------------------
# UI
# -------------------------
def main():
    st.set_page_config(page_title="門市到貨異常率", page_icon="🏪", layout="wide")
    inject_logistics_theme()
    set_page("門市到貨異常率", icon="🏪", subtitle="箱號年月日篩選｜排除供應商｜多貨/短少/凹破漏統計｜匯出處理後明細")

    st.markdown(
        r"""
<style>
.kpi-wrap{
  width: 100%;
  max-width: none;
  box-sizing: border-box;
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(15,23,42,.10);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 10px 26px rgba(15,23,42,.06);
  margin: 10px 0 6px 0;
}
.kpi-title{
  font-size: 18px;          /* 標題 > 數字：你若要更大可調 19~20 */
  font-weight: 900;
  color: rgba(15,23,42,.92);
  margin: 0 0 10px 0;
}
.kpi-grid{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.metric-box{
  background: rgba(248,250,252,.92);
  border: 1px solid rgba(15,23,42,.10);
  border-radius: 12px;
  padding: 10px 12px;
}
.metric-label{
  font-size: 12px;
  font-weight: 850;
  color: rgba(15,23,42,.70);
  margin-bottom: 4px;
}
.metric-value{
  font-size: 20px;
  font-weight: 950;
  line-height: 1.12;
  color: rgba(15,23,42,.94);
}
@media (max-width: 900px){
  .kpi-grid{ grid-template-columns: 1fr; }
}
</style>
""",
        unsafe_allow_html=True,
    )

    card_open("📌 上傳檔案（XLSX / XLSM / XLSB / XLS）")
    st.caption("箱號：前 4 碼 = 年(YYYY)、第 5~8 碼 = 日期(MMDD)。")
    st.caption("會排除：異常原因含「供應商」的列。")
    st.caption("必要欄位：箱號、異常原因、應到數量、實到數量（如有「數量」會用於凹損/破損/漏液統計）")

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
            df = _normalize_cols(df)
            _validate_cols(df)
            df = _build_year_date(df)
        except Exception as e:
            st.error(f"讀取/檢核失敗：{e}")
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

    # 年/日期下拉（避免你再手打）
    years = sorted([y for y in df["年"].dropna().astype(str).unique().tolist() if y.strip() != ""])
    dates = sorted([d for d in df["日期"].dropna().astype(str).unique().tolist() if d.strip() != ""])

    ctrl = st.container()
    with ctrl:
        c1, c2, c3 = st.columns([1, 1, 1], gap="medium")
        with c1:
            year_sel = st.selectbox("保留年（YYYY）", options=years if years else ["(無法解析)"], index=0)
        with c2:
            date_sel = st.selectbox("保留日期（MMDD）", options=dates if dates else ["(無法解析)"], index=0)
        with c3:
            run = st.button("開始計算", type="primary", use_container_width=True)

    if not run:
        st.stop()

    with st.spinner("計算中…"):
        # 篩選 年/日期
        df2 = df.copy()
        if years and dates:
            df2 = df2[(df2["年"].astype(str) == str(year_sel)) & (df2["日期"].astype(str) == str(date_sel))].copy()

        # 排除「異常原因」含「供應商」
        df2 = df2[~df2["異常原因"].astype(str).str.contains("供應商", na=False)].copy()

        # 數值化
        df2 = _to_numeric(df2)

        # 統計 + 差異
        result = _compute(df2)

    # KPI 卡（同寬、3欄一列、再換下一列）
    st.markdown(
        f"""
<div class="kpi-wrap">
  <div class="kpi-title">門市到貨異常摘要</div>
  <div class="kpi-grid">
    <div class="metric-box">
      <div class="metric-label">箱號總筆數（含重複）</div>
      <div class="metric-value">{_fmt_int(result["箱號總筆數"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨多貨總差異</div>
      <div class="metric-value">{_fmt_num(result["到貨多貨總差異"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨短少總差異</div>
      <div class="metric-value">{_fmt_num(result["到貨短少總差異"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨凹損/破損/漏液總數量</div>
      <div class="metric-value">{_fmt_num(result["到貨凹損/破損/漏液總數量"])}</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # 匯出
    out_df = result["df"]
    xlsx_bytes = _to_xlsx_bytes(out_df)
    st.download_button(
        "⬇️ 匯出（處理後）Excel",
        data=xlsx_bytes,
        file_name="門市到貨異常_處理後.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )

    st.markdown("### 明細預覽（前 200 列）")
    st.dataframe(out_df.head(200), use_container_width=True, height=420)


if __name__ == "__main__":
    main()
