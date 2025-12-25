# pages/16_門市到貨異常率.py
import pandas as pd
import streamlit as st
from io import BytesIO

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ----------------------------
# format helpers
# ----------------------------
def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return "0"


def _fmt_num(x) -> str:
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return "0"


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
    for s in ["明細", "工作表1", "Sheet1"]:
        if s in xls.sheet_names:
            return s
    return xls.sheet_names[0]


def _read_uploaded_excel(uploaded) -> tuple[pd.DataFrame, dict]:
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


def _require_cols(df: pd.DataFrame, need: list[str]) -> None:
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}（目前欄位前 30：{list(df.columns)[:30]} ...）")


def _derive_year_mmdd_from_box(df: pd.DataFrame, col_box: str) -> pd.DataFrame:
    df = df.copy()
    s = df[col_box].astype(str).fillna("").str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)

    df["年"] = s.str[:4]
    df["日期"] = s.str[4:8]

    # 僅保留 4 碼數字格式
    df.loc[~df["年"].str.fullmatch(r"\d{4}", na=False), "年"] = ""
    df.loc[~df["日期"].str.fullmatch(r"\d{4}", na=False), "日期"] = ""
    return df


def _to_num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def _compute_metrics(df: pd.DataFrame, col_box: str, col_reason: str) -> dict:
    count_box_rows = int(df[col_box].dropna().shape[0])

    sum_excess = float(df.loc[df[col_reason] == "到貨多貨", "差異"].sum())
    sum_shortage = float(df.loc[df[col_reason] == "到貨短少", "差異"].sum())

    if "數量" in df.columns:
        sum_defect = float(
            df.loc[df[col_reason].isin(["到貨凹損", "到貨破損", "到貨漏液"]), "數量"].sum()
        )
    else:
        sum_defect = float(
            df.loc[df[col_reason].isin(["到貨凹損", "到貨破損", "到貨漏液"]), "差異"].abs().sum()
        )

    return {
        "箱號總筆數": count_box_rows,
        "到貨多貨總差異": sum_excess,
        "到貨短少總差異": sum_shortage,
        "到貨凹損破損漏液總數量": sum_defect,
    }


def _download_xlsx_bytes(df: pd.DataFrame) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="處理後明細")
    bio.seek(0)
    return bio.getvalue()


def main():
    st.set_page_config(page_title="門市到貨異常率", page_icon="🏪", layout="wide")
    inject_logistics_theme()
    set_page("門市到貨異常率", icon="🏪", subtitle="上傳異常彙整｜依箱號年/日期篩選｜統計多貨/短少/凹損破損漏液")

    st.markdown(
        r"""
<style>
.kpi-wrap{
  width: 100%;
  max-width: none;
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(15,23,42,.10);
  border-radius: 14px;
  padding: 14px 14px 12px 14px;
  box-shadow: 0 10px 26px rgba(15,23,42,.06);
  margin: 10px 0 8px 0;
}
.kpi-title{
  font-size: 18px;
  font-weight: 950;
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
  font-size: 12.5px;
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
.metric-span-3{ grid-column: 1 / span 3; }
.kpi-note{
  margin-top: 8px;
  font-size: 12.5px;
  color: rgba(15,23,42,.62);
  font-weight: 650;
}
@media (max-width: 900px){
  .kpi-grid{ grid-template-columns: 1fr; }
  .metric-span-3{ grid-column: auto; }
}
</style>
""",
        unsafe_allow_html=True,
    )

    card_open("📌 上傳檔案（XLSX / XLSM / XLSB / XLS）")
    st.caption("工作表：優先「明細」，沒有則取第一張。")
    st.caption("必要欄位：箱號、異常原因、應到數量、實到數量（凹損/破損/漏液建議有「數量」欄）")
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
            df, info = _read_uploaded_excel(uploaded)
            df = _normalize_cols(df)
        except Exception as e:
            st.error(f"讀取失敗：{e}")
            st.stop()

    rows, cols = df.shape
    msg = f"已讀取：{uploaded.name}"
    msg += f"（工作表：{info.get('sheet','')}｜engine：{info.get('engine','')}｜{rows:,} 列｜{cols:,} 欄）"
    st.success(msg)
    if info.get("note"):
        st.info(info["note"])

    col_box = "箱號"
    col_reason = "異常原因"
    _require_cols(df, [col_box, col_reason])

    df = _derive_year_mmdd_from_box(df, col_box)

    years = sorted([y for y in df["年"].dropna().unique().tolist() if str(y).strip() != ""])
    dates = sorted([d for d in df["日期"].dropna().unique().tolist() if str(d).strip() != ""])

    left, right = st.columns(2, gap="large")
    with left:
        year_sel = st.selectbox("保留 年（箱號前 4 碼）", options=years if years else [""])
    with right:
        date_sel = st.selectbox("保留 日期（箱號第5-8碼 MMDD）", options=dates if dates else [""])

    if year_sel and date_sel:
        df = df[(df["年"] == str(year_sel)) & (df["日期"] == str(date_sel))].copy()

    # 排除供應商原因
    df = df[~df[col_reason].astype(str).str.contains("供應商", na=False)].copy()

    # 轉數值 + 計算差異
    df = _to_num(df, ["應到數量", "實到數量", "數量"])
    _require_cols(df, ["應到數量", "實到數量"])
    df["差異"] = df["實到數量"] - df["應到數量"]

    metrics = _compute_metrics(df, col_box, col_reason)

    # ✅✅ 這裡一定要用 st.markdown + unsafe_allow_html=True，才能渲染卡片
    kpi_html = f"""
<div class="kpi-wrap">
  <div class="kpi-title">門市到貨異常統計</div>
  <div class="kpi-grid">
    <div class="metric-box">
      <div class="metric-label">箱號總筆數（含重複）</div>
      <div class="metric-value">{_fmt_int(metrics["箱號總筆數"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨多貨總差異（差異加總）</div>
      <div class="metric-value">{_fmt_num(metrics["到貨多貨總差異"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨短少總差異（差異加總）</div>
      <div class="metric-value">{_fmt_num(metrics["到貨短少總差異"])}</div>
    </div>

    <div class="metric-box metric-span-3">
      <div class="metric-label">到貨凹損 / 破損 / 漏液總數量（數量加總）</div>
      <div class="metric-value">{_fmt_num(metrics["到貨凹損破損漏液總數量"])}</div>
    </div>
  </div>

  <div class="kpi-note">已自動計算：差異 = 實到數量 - 應到數量（並排除「異常原因」含「供應商」）。</div>
</div>
"""
    st.markdown(kpi_html, unsafe_allow_html=True)

    out_bytes = _download_xlsx_bytes(df)
    st.download_button(
        "⬇️ 匯出（處理後）Excel",
        data=out_bytes,
        file_name="門市到貨異常_處理後.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("### 明細預覽（前 200 列）")
    st.dataframe(df.head(200), use_container_width=True, height=420)


if __name__ == "__main__":
    main()
