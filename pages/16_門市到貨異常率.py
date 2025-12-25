# pages/16_門市到貨異常率.py
import pandas as pd
import streamlit as st
from io import BytesIO

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ---------------------------
# format helpers
# ---------------------------
def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return "0"


def _fmt_num(x) -> str:
    try:
        # 保留整數（你原本就是數量）
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
    # 依你上傳檔案：優先「明細」
    preferred = ["明細", "工作表1", "Sheet1"]
    for p in preferred:
        if p in xls.sheet_names:
            return p
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
    # 依你原始邏輯會用到的欄位
    need = ["箱號", "應到數量", "實到數量", "異常原因"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}（目前欄位：{list(df.columns)[:30]} ...）")


def _parse_year_mmdd_from_box(df: pd.DataFrame, col_box: str = "箱號") -> pd.DataFrame:
    df = df.copy()
    s = df[col_box].astype(str)
    df["年"] = s.str[:4]
    df["日期"] = s.str[4:8]
    return df


def _to_num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    df = df.copy()
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df


def _compute(df_raw: pd.DataFrame, year_filter: str, date_filter: str) -> tuple[pd.DataFrame, dict]:
    """
    回傳：處理後 df + 指標
    """
    df = df_raw.copy()

    # 解析 年/日期
    df = _parse_year_mmdd_from_box(df, "箱號")

    # 篩選 年/日期（允許「全部」）
    before_filter = len(df)
    if year_filter != "全部":
        df = df[df["年"] == year_filter]
    if date_filter != "全部":
        df = df[df["日期"] == date_filter]
    after_filter = len(df)
    filtered_out = before_filter - after_filter

    # 數值欄位轉數值
    df = _to_num(df, ["應到數量", "實到數量", "差異", "數量"])

    # 排除 異常原因 含 供應商
    before_supplier = len(df)
    df = df[~df["異常原因"].astype(str).str.contains("供應商", na=False)]
    supplier_removed = before_supplier - len(df)

    # 計算差異 = 實到 - 應到（若原本有差異欄位也直接覆蓋，避免舊值）
    df["差異"] = df["實到數量"] - df["應到數量"]

    # 指標
    count_box_rows = int(df["箱號"].dropna().shape[0])  # 含重複：列數
    sum_excess = float(df.loc[df["異常原因"] == "到貨多貨", "差異"].sum())
    sum_shortage = float(df.loc[df["異常原因"] == "到貨短少", "差異"].sum())
    sum_defect = 0.0
    if "數量" in df.columns:
        sum_defect = float(df.loc[df["異常原因"].isin(["到貨凹損", "到貨破損", "到貨漏液"]), "數量"].sum())

    metrics = {
        "箱號總筆數": count_box_rows,
        "到貨多貨總差異": sum_excess,
        "到貨短少總差異": sum_shortage,
        "到貨凹損破損漏液總數量": sum_defect,
        "年日期剔除筆數": int(filtered_out),
        "供應商剔除筆數": int(supplier_removed),
    }

    return df, metrics


def _to_excel_bytes(df: pd.DataFrame, sheet_name: str = "門市到貨異常") -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return bio.getvalue()


def main():
    st.set_page_config(page_title="門市到貨異常率", page_icon="🚨", layout="wide")
    inject_logistics_theme()
    set_page("門市到貨異常率", icon="🚨", subtitle="上傳異常彙整｜篩選箱號年/日期｜排除供應商｜自動統計異常差異")

    st.markdown(
        r"""
<style>
/* 讓結果區塊與上傳卡片同寬（不要縮窄） */
.fullw-wrap{
  width: 100%;
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(15,23,42,.10);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 10px 26px rgba(15,23,42,.06);
  margin: 10px 0 6px 0;
}
.fullw-title{
  font-size: 18px;
  font-weight: 950;
  color: rgba(15,23,42,.92);
  margin: 0 0 10px 0;
}

/* 3 欄 → 自動換列 */
.kpi-grid{
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

/* 小一點、不要整列滿版的感覺：卡片本身剛好 */
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
  font-size: 18px;
  font-weight: 950;
  line-height: 1.12;
  color: rgba(15,23,42,.94);
}
.metric-value-main{
  font-size: 20px;
}
.note{
  margin-top: 8px;
  font-size: 12px;
  color: rgba(15,23,42,.62);
  font-weight: 650;
}
@media (max-width: 900px){
  .kpi-grid{ grid-template-columns: 1fr; }
}
</style>
""",
        unsafe_allow_html=True,
    )

    # 上傳
    card_open("📌 上傳檔案（XLSX / XLSM / XLSB / XLS）")
    st.caption("工作表：優先「明細」，沒有則取第一張。")
    st.caption("必要欄位：箱號、應到數量、實到數量、異常原因（數量欄位用於凹損/破損/漏液統計）")
    uploaded = st.file_uploader(
        "選擇檔案",
        type=["xlsx", "xlsm", "xlsb", "xls"],
        accept_multiple_files=False,
        label_visibility="collapsed",
    )
    card_close()

    if not uploaded:
        st.stop()

    # 讀取中
    with st.spinner("資料讀取中…"):
        try:
            df, info = _read_uploaded_table(uploaded)
            df = _normalize_cols(df)
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

    # 欄位檢查
    try:
        _validate_cols(df)
    except Exception as e:
        st.error(f"欄位檢查失敗：{e}")
        st.write("目前欄位：", list(df.columns))
        st.dataframe(df.head(50), use_container_width=True)
        st.stop()

    # 篩選條件（年 / 日期）
    temp = _parse_year_mmdd_from_box(df, "箱號")
    years = sorted([y for y in temp["年"].dropna().astype(str).unique().tolist() if len(y) == 4])
    dates = sorted([d for d in temp["日期"].dropna().astype(str).unique().tolist() if len(d) == 4])

    c1, c2 = st.columns([1, 1], gap="medium")
    with c1:
        year_filter = st.selectbox("保留 年（箱號前 4 碼）", ["全部"] + years, index=0)
    with c2:
        date_filter = st.selectbox("保留 日期（箱號第 5-8 碼 MMDD）", ["全部"] + dates, index=0)

    # 計算
    with st.spinner("統計計算中…"):
        df_out, m = _compute(df, year_filter, date_filter)

    # 結果 KPI（同寬 + 3 欄換列）
    st.markdown(
        f"""
<div class="fullw-wrap">
  <div class="fullw-title">門市到貨異常統計</div>
  <div class="kpi-grid">
    <div class="metric-box">
      <div class="metric-label">箱號總筆數（含重複）</div>
      <div class="metric-value metric-value-main">{_fmt_int(m["箱號總筆數"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨多貨總差異（差異加總）</div>
      <div class="metric-value">{_fmt_num(m["到貨多貨總差異"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨短少總差異（差異加總）</div>
      <div class="metric-value">{_fmt_num(m["到貨短少總差異"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">到貨凹損/破損/漏液總數量（數量加總）</div>
      <div class="metric-value">{_fmt_num(m["到貨凹損破損漏液總數量"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">年/日期剔除筆數</div>
      <div class="metric-value">{_fmt_int(m["年日期剔除筆數"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">供應商原因剔除筆數</div>
      <div class="metric-value">{_fmt_int(m["供應商剔除筆數"])}</div>
    </div>
  </div>
  <div class="note">已自動計算：差異 = 實到數量 - 應到數量（並排除「異常原因」含「供應商」）。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # 匯出
    out_bytes = _to_excel_bytes(df_out, sheet_name="門市到貨異常_結果")
    st.download_button(
        "⬇️ 匯出（處理後）Excel",
        data=out_bytes,
        file_name="門市到貨異常_處理後.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=False,
    )

    st.markdown("### 明細預覽（前 200 列）")
    st.dataframe(df_out.head(200), use_container_width=True, height=420)


if __name__ == "__main__":
    main()
