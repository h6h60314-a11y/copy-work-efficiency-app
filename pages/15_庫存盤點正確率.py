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


def _fmt_num0(x) -> str:
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


def _normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    欄位標準化：
    1. 去除前後空白
    2. 移除換行，例如「芷\\n差異」→「芷差異」
    """
    df = df.copy()
    df.columns = [str(c).replace("\n", "").replace("\r", "").strip() for c in df.columns]
    return df


def _pick_sheet_names(xls: pd.ExcelFile) -> list[str]:
    """
    自動判斷要讀哪些工作表。

    舊格式：
    - 優先讀「工作表1」

    新格式：
    - 若有「高空」或「低空」，就讀這兩張並合併計算
    """
    sheet_names = xls.sheet_names

    inventory_sheets = [s for s in ["高空", "低空"] if s in sheet_names]
    if inventory_sheets:
        return inventory_sheets

    if "工作表1" in sheet_names:
        return ["工作表1"]

    return [sheet_names[0]]


def _read_uploaded_tables(uploaded) -> tuple[list[pd.DataFrame], dict]:
    raw = uploaded.getvalue()
    name = uploaded.name
    ext = name.split(".")[-1].lower().strip()

    info = {
        "engine": "",
        "sheets": [],
        "note": "",
    }

    dfs: list[pd.DataFrame] = []

    if ext in {"xlsx", "xlsm", "xltx", "xltm"}:
        engine = "openpyxl"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheets = _pick_sheet_names(xls)
        info["sheets"] = sheets

        for sheet in sheets:
            df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine)
            df = _normalize_cols(df)
            df.insert(0, "來源工作表", sheet)
            dfs.append(df)

        return dfs, info

    if ext == "xlsb":
        engine = "pyxlsb"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheets = _pick_sheet_names(xls)
        info["sheets"] = sheets

        for sheet in sheets:
            df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine)
            df = _normalize_cols(df)
            df.insert(0, "來源工作表", sheet)
            dfs.append(df)

        return dfs, info

    if ext == "xls":
        if _is_fake_xls_provider(raw):
            info["engine"] = "text/html"
            info["note"] = "偵測到『假 xls』（PROVIDER）→ 已改用文字/HTML 解析"
            df = _read_fake_xls_text_or_html(raw)
            df = _normalize_cols(df)
            df.insert(0, "來源工作表", "文字/HTML")
            dfs.append(df)
            info["sheets"] = ["文字/HTML"]
            return dfs, info

        engine = "xlrd"
        info["engine"] = engine
        xls = pd.ExcelFile(BytesIO(raw), engine=engine)
        sheets = _pick_sheet_names(xls)
        info["sheets"] = sheets

        for sheet in sheets:
            df = pd.read_excel(BytesIO(raw), sheet_name=sheet, engine=engine)
            df = _normalize_cols(df)
            df.insert(0, "來源工作表", sheet)
            dfs.append(df)

        return dfs, info

    raise ValueError("不支援的檔案格式。請上傳 XLSX / XLSM / XLSB / XLS。")


def _find_diff_series(df: pd.DataFrame) -> tuple[pd.Series, str]:
    """
    自動抓差異欄位。

    舊格式 / 高空：
    - 使用「差異」

    新格式低空：
    - 優先使用人員差異欄，例如「芷差異」、「旻差異」
    - 不優先使用「兩人差異」，因為那是兩位盤點人員互相比對，不是跟庫存帳比對
    """

    if "差異" in df.columns:
        return pd.to_numeric(df["差異"], errors="coerce").fillna(0), "差異"

    person_diff_cols = [
        c for c in df.columns
        if c.endswith("差異") and c != "兩人差異"
    ]

    if person_diff_cols:
        # 優先使用第一個人員差異欄位
        # 若之後你想固定用「旻差異」，可以把這裡改成指定欄位
        col = person_diff_cols[0]
        return pd.to_numeric(df[col], errors="coerce").fillna(0), col

    if "兩人差異" in df.columns:
        return pd.to_numeric(df["兩人差異"], errors="coerce").fillna(0), "兩人差異"

    raise KeyError(
        f"找不到可用的差異欄位。需要「差異」或「芷差異 / 旻差異」等欄位。"
        f"目前欄位：{list(df.columns)[:40]} ..."
    )


def _validate_cols(df: pd.DataFrame) -> None:
    need = ["商品號", "儲位"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}（目前欄位：{list(df.columns)[:40]} ...）")

    # 另外確認有沒有可用差異欄位
    _find_diff_series(df)


def _compute_one(df: pd.DataFrame) -> dict:
    """
    計算單一 DataFrame 的盤點正確率。
    """
    _validate_cols(df)

    # 以「儲位有值的列」為基準
    base = df["儲位"].notna()

    # 商品號去重
    unique_item_count = int(df.loc[base, "商品號"].dropna().nunique())

    # 儲位筆數，含重複
    slot_count = int(base.sum())

    # 差異欄位自動判斷
    diff, diff_col = _find_diff_series(df)

    # 只在 base 範圍內統計
    diff_nonzero_count = int(((diff != 0) & base).sum())
    correct_count = int(((diff == 0) & base).sum())

    accuracy = (correct_count / slot_count) if slot_count > 0 else 0.0

    diff_positive_sum = float(diff[(diff > 0) & base].sum())
    diff_negative_sum_abs = float(abs(diff[(diff < 0) & base].sum()))

    return {
        "使用差異欄位": diff_col,
        "盤點商品號去重": unique_item_count,
        "盤點儲位數": slot_count,
        "盤點正確筆數": correct_count,
        "盤點≠0筆數": diff_nonzero_count,
        "差異>0總和": diff_positive_sum,
        "差異<0缺少總和": diff_negative_sum_abs,
        "盤點正確率": float(accuracy),
    }


def _compute_all(dfs: list[pd.DataFrame]) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """
    多工作表合併計算。
    回傳：
    1. total_result：總計
    2. detail_df：合併後明細
    3. summary_df：各工作表統計
    """
    computed_dfs = []
    summary_rows = []

    for df in dfs:
        df = df.copy()
        sheet_name = str(df["來源工作表"].iloc[0]) if "來源工作表" in df.columns and len(df) else "-"

        result = _compute_one(df)
        summary_rows.append({
            "來源工作表": sheet_name,
            "使用差異欄位": result["使用差異欄位"],
            "盤點商品號去重": result["盤點商品號去重"],
            "盤點儲位數": result["盤點儲位數"],
            "盤點正確筆數": result["盤點正確筆數"],
            "盤點≠0筆數": result["盤點≠0筆數"],
            "差異>0總和": result["差異>0總和"],
            "差異<0缺少總和": result["差異<0缺少總和"],
            "盤點正確率": result["盤點正確率"],
        })

        diff, diff_col = _find_diff_series(df)
        df["計算用差異"] = diff
        df["計算用差異欄位"] = diff_col
        computed_dfs.append(df)

    detail_df = pd.concat(computed_dfs, ignore_index=True, sort=False)

    base = detail_df["儲位"].notna()
    diff = pd.to_numeric(detail_df["計算用差異"], errors="coerce").fillna(0)

    unique_item_count = int(detail_df.loc[base, "商品號"].dropna().nunique())
    slot_count = int(base.sum())
    correct_count = int(((diff == 0) & base).sum())
    diff_nonzero_count = int(((diff != 0) & base).sum())
    accuracy = (correct_count / slot_count) if slot_count > 0 else 0.0
    diff_positive_sum = float(diff[(diff > 0) & base].sum())
    diff_negative_sum_abs = float(abs(diff[(diff < 0) & base].sum()))

    total_result = {
        "盤點商品號去重": unique_item_count,
        "盤點儲位數": slot_count,
        "盤點正確筆數": correct_count,
        "盤點≠0筆數": diff_nonzero_count,
        "差異>0總和": diff_positive_sum,
        "差異<0缺少總和": diff_negative_sum_abs,
        "盤點正確率": float(accuracy),
    }

    summary_df = pd.DataFrame(summary_rows)
    return total_result, detail_df, summary_df


def _kpi_html(result: dict) -> str:
    return (
        '<div class="kpi-wrap">'
        '<div class="kpi-title">盤點正確率</div>'
        '<div class="kpi-grid">'

        '<div class="metric-box">'
        '<div class="metric-label">盤點商品號去重</div>'
        f'<div class="metric-value">{_fmt_int(result["盤點商品號去重"])}</div>'
        '</div>'

        '<div class="metric-box">'
        '<div class="metric-label">盤點儲位數（含重複）</div>'
        f'<div class="metric-value">{_fmt_int(result["盤點儲位數"])}</div>'
        '</div>'

        '<div class="metric-box">'
        '<div class="metric-label">盤點正確筆數</div>'
        f'<div class="metric-value">{_fmt_int(result["盤點正確筆數"])}</div>'
        '</div>'

        '<div class="metric-box">'
        '<div class="metric-label">盤點 ≠ 0 筆數</div>'
        f'<div class="metric-value">{_fmt_int(result["盤點≠0筆數"])}</div>'
        '</div>'

        '<div class="metric-box">'
        '<div class="metric-label">差異 &gt; 0（多出總和）</div>'
        f'<div class="metric-value">{_fmt_num0(result["差異>0總和"])}</div>'
        '</div>'

        '<div class="metric-box">'
        '<div class="metric-label">差異 &lt; 0（缺少總和）</div>'
        f'<div class="metric-value">{_fmt_num0(result["差異<0缺少總和"])}</div>'
        '</div>'

        '<div class="metric-box metric-box-main">'
        '<div class="metric-label">盤點正確率（差異=0 / 儲位筆數）</div>'
        f'<div class="metric-value metric-value-main">{_fmt_pct(result["盤點正確率"])}</div>'
        '</div>'

        '</div>'
        '<div class="kpi-note">'
        '提示：統計基準為「儲位欄有值的列」。新格式會自動讀取「高空、低空」並合併計算。'
        '</div>'
        '</div>'
    )


def main():
    st.set_page_config(page_title="庫存盤點正確率", page_icon="🎯", layout="wide")
    inject_logistics_theme()
    set_page("庫存盤點正確率", icon="🎯", subtitle="上傳盤點結果｜自動統計正確率與差異分布")

    st.markdown(
        """
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
  font-size: 22px;
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
.metric-box-main{
  background: rgba(240,253,244,.95);
  border-color: rgba(22,163,74,.25);
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
.metric-value-main{
  font-size: 24px;
  color: #15803d;
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
    st.caption("支援兩種格式：")
    st.caption("① 舊格式：工作表1，欄位需有 商品號、儲位、差異")
    st.caption("② 新格式：高空 / 低空，程式會自動合併計算")
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
            dfs, info = _read_uploaded_tables(uploaded)
        except Exception as e:
            st.error(f"讀取失敗：{e}")
            st.stop()

    total_rows = sum(len(df) for df in dfs)
    total_cols = max([df.shape[1] for df in dfs], default=0)
    sheets_text = "、".join(info.get("sheets", []))

    st.success(
        f"已讀取：{uploaded.name}"
        f"（工作表：{sheets_text}｜engine：{info.get('engine','')}｜"
        f"{total_rows:,} 列｜最多 {total_cols:,} 欄）"
    )

    if info.get("note"):
        st.info(info["note"])

    try:
        result, detail_df, summary_df = _compute_all(dfs)
    except Exception as e:
        st.error(f"計算失敗：{e}")
        for i, df in enumerate(dfs, start=1):
            st.write(f"第 {i} 張資料欄位預覽：", list(df.columns))
            st.dataframe(df.head(30), use_container_width=True)
        st.stop()

    st.markdown(_kpi_html(result), unsafe_allow_html=True)

    st.markdown("### 各工作表統計")
    show_summary = summary_df.copy()
    if "盤點正確率" in show_summary.columns:
        show_summary["盤點正確率"] = show_summary["盤點正確率"].map(_fmt_pct)
    st.dataframe(show_summary, use_container_width=True, height=220)

    st.markdown("### 明細預覽（前 200 列）")
    st.dataframe(detail_df.head(200), use_container_width=True, height=420)


if __name__ == "__main__":
    main()
