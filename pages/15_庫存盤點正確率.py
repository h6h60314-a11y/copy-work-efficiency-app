# pages/15_庫存盤點正確率.py
import pandas as pd
import streamlit as st
from io import BytesIO

from common_ui import inject_logistics_theme, set_page, card_open, card_close


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


def _fmt_pct(x) -> str:
    try:
        return f"{float(x) * 100:,.2f}%"
    except Exception:
        return "0.00%"


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
    need = ["商品號", "儲位", "差異"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}（目前欄位：{list(df.columns)[:30]} ...）")


def _compute(df: pd.DataFrame) -> dict:
    # 商品號去重
    unique_item_count = df["商品號"].dropna().nunique()

    # 儲位筆數（含重複）：等同有值的列數
    slot_count = df["儲位"].dropna().shape[0]

    # 差異轉數值
    diff = pd.to_numeric(df["差異"], errors="coerce").fillna(0)

    # 差異 ≠ 0 筆數
    diff_nonzero_count = (diff != 0).sum()

    # 正確率（差異=0 / 有儲位的筆數）
    # 若你想用「全列」當分母，把 denom 改成 len(df)
    denom = max(int(slot_count), 0)
    correct_count = max(denom - int(diff_nonzero_count), 0)
    accuracy = (correct_count / denom) if denom > 0 else 0.0

    # 差異 >0 總和、差異 <0 總和
    diff_positive_sum = diff[diff > 0].sum()
    diff_negative_sum = diff[diff < 0].sum()

    return {
        "商品號去重": int(unique_item_count),
        "儲位筆數": int(slot_count),
        "差異≠0筆數": int(diff_nonzero_count),
        "正確率": float(accuracy),
        "差異>0總和": float(diff_positive_sum),
        "差異<0總和": float(diff_negative_sum),
    }


def main():
    st.set_page_config(page_title="庫存盤點正確率", page_icon="🎯", layout="wide")
    inject_logistics_theme()
    set_page("庫存盤點正確率", icon="🎯", subtitle="上傳盤點結果｜自動統計正確率與差異分布")

    st.markdown(
        r"""
<style>
.kpi-wrap{
  max-width: 980px;
  width: 100%;
  background: rgba(255,255,255,.86);
  border: 1px solid rgba(15,23,42,.10);
  border-radius: 14px;
  padding: 12px 14px;
  box-shadow: 0 10px 26px rgba(15,23,42,.06);
  margin: 10px 0 6px 0;
}
.kpi-title{
  font-size: 26px;          /* 標題比數字大 */
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
.kpi-note{
  margin-top: 8px;
  font-size: 12.5px;
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

    card_open("📌 上傳檔案（XLSX / XLSM / XLSB / XLS）")
    st.caption("工作表：優先「工作表1」，沒有則取第一張。")
    st.caption("必要欄位：商品號、儲位、差異")
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

    try:
        _validate_cols(df)
        result = _compute(df)
    except Exception as e:
        st.error(f"計算失敗：{e}")
        st.write("目前欄位預覽：", list(df.columns))
        st.dataframe(df.head(50), use_container_width=True)
        st.stop()

    st.markdown(
        f"""
<div class="kpi-wrap">
  <div class="kpi-title">盤點摘要</div>
  <div class="kpi-grid">
    <div class="metric-box">
      <div class="metric-label">商品號（去重）</div>
      <div class="metric-value">{_fmt_int(result["商品號去重"])}</div>
    </div>
    <div class="metric-box">
      <div class="metric-label">儲位筆數（含重複）</div>
      <div class="metric-value">{_fmt_int(result["儲位筆數"])}</div>
    </div>
    <div class="metric-box">
      <div class="metric-label">差異 ≠ 0 筆數</div>
      <div class="metric-value">{_fmt_int(result["差異≠0筆數"])}</div>
    </div>

    <div class="metric-box">
      <div class="metric-label">盤點正確率（差異=0 / 儲位筆數）</div>
      <div class="metric-value">{_fmt_pct(result["正確率"])}</div>
    </div>
    <div class="metric-box">
      <div class="metric-label">差異 > 0（總和）</div>
      <div class="metric-value">{_fmt_num(result["差異>0總和"])}</div>
    </div>
    <div class="metric-box">
      <div class="metric-label">差異 < 0（總和）</div>
      <div class="metric-value">{_fmt_num(result["差異<0總和"])}</div>
    </div>
  </div>
  <div class="kpi-note">提示：若你希望「正確率」用全列當分母，我可以再幫你改成以總列數計算。</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### 明細預覽（前 200 列）")
    st.dataframe(df.head(200), use_container_width=True, height=420)


if __name__ == "__main__":
    main()
