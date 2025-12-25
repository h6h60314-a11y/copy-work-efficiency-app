# pages/11_出貨訂單應出量分析.py
import io
import os
from pathlib import Path
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ----------------------------
# Page config / Theme
# ----------------------------
st.set_page_config(page_title="出貨訂單應出量分析", page_icon="📦", layout="wide")
inject_logistics_theme()


# ----------------------------
# Helpers
# ----------------------------
def _fmt_qty(x):
    try:
        v = float(x)
    except Exception:
        return str(x)
    # 兩位小數，但尾端 .00 會去掉
    s = f"{v:,.2f}"
    return s[:-3] if s.endswith(".00") else s


def _fmt_int(x):
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)


def _read_csv_best_effort(b: bytes) -> pd.DataFrame:
    # 先 UTF-8，再 BIG5，再 CP950
    for enc in ("utf-8", "utf-8-sig", "big5", "cp950"):
        try:
            return pd.read_csv(io.BytesIO(b), encoding=enc)
        except Exception:
            pass
    # 最後用 latin-1 兜底
    return pd.read_csv(io.BytesIO(b), encoding="latin-1")


def _read_html_best_effort(b: bytes) -> pd.DataFrame:
    # pandas.read_html 需要 text 或檔案路徑/類檔案
    text = None
    for enc in ("utf-8", "utf-8-sig", "big5", "cp950", "latin-1"):
        try:
            text = b.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = b.decode("utf-8", errors="ignore")

    tables = pd.read_html(text)
    if not tables:
        raise ValueError("HTML 內找不到表格")
    return tables[0]


def _excel_engines_for_ext(ext: str):
    ext = ext.lower()
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return ["openpyxl", "xlrd"]
    if ext == ".xls":
        return ["xlrd", "openpyxl"]
    if ext == ".xlsb":
        return ["pyxlsb"]
    return []


def _load_dataframe(uploaded_file) -> tuple[pd.DataFrame, str]:
    """
    回傳 (df,讀取方式描述)
    """
    name = uploaded_file.name
    ext = Path(name).suffix.lower()
    b = uploaded_file.getvalue()

    # CSV / HTML
    if ext == ".csv":
        df = _read_csv_best_effort(b)
        return df, "CSV"
    if ext in (".html", ".htm"):
        df = _read_html_best_effort(b)
        return df, "HTML"

    # Excel
    engines = _excel_engines_for_ext(ext)
    if not engines:
        raise ValueError("不支援的檔案格式，請使用 Excel/CSV/HTML")

    # 先嘗試取 sheet 名稱（若失敗就直接讀第一張）
    last_err = None
    for eng in engines:
        try:
            xf = pd.ExcelFile(io.BytesIO(b), engine=eng)
            sheet_names = xf.sheet_names
            sheet = sheet_names[0] if sheet_names else 0

            # 讓使用者可選 sheet（如果多張）
            if len(sheet_names) > 1:
                chosen = st.selectbox("選擇工作表", sheet_names, index=0)
                sheet = chosen

            df = pd.read_excel(io.BytesIO(b), engine=eng, sheet_name=sheet)
            return df, f"Excel({ext}, engine={eng}, sheet={sheet})"
        except Exception as e:
            last_err = e
            continue

    # xlsb 沒裝 pyxlsb 常見
    raise ValueError(f"Excel 讀取失敗：{last_err}")


def _compute(df: pd.DataFrame) -> dict:
    need_cols = ["原始配庫存量", "出貨入數", "計量單位"]
    missing = [c for c in need_cols if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}")

    out = df.copy()

    # 型別處理
    out["原始配庫存量"] = pd.to_numeric(out["原始配庫存量"], errors="coerce").fillna(0)
    out["出貨入數"] = pd.to_numeric(out["出貨入數"], errors="coerce").replace(0, pd.NA)
    out["計量單位"] = pd.to_numeric(out["計量單位"], errors="coerce")

    # 原始配庫存出貨單位量
    out["原始配庫存出貨單位量"] = (out["原始配庫存量"] / out["出貨入數"]).fillna(0)

    # === 你原本的邏輯 ===
    mask1 = (out["原始配庫存出貨單位量"] == 1) & (out["計量單位"] == 2)
    total1 = out.loc[mask1, "原始配庫存量"].sum()

    mask2 = (out["原始配庫存出貨單位量"] != 1) & (out["計量單位"] == 2)
    total2 = out.loc[mask2, "原始配庫存出貨單位量"].sum()

    mask3 = out["計量單位"].isin([3, 6])
    total3 = out.loc[mask3, "原始配庫存出貨單位量"].sum()

    成箱 = total1 + total2
    零散 = total3

    # 儲位 / 商品（可選）
    儲位數 = out["儲位"].nunique() if "儲位" in out.columns else None
    品項數 = out["商品"].nunique() if "商品" in out.columns else None

    return {
        "df": out,
        "零散應出": 零散,
        "成箱應出": 成箱,
        "儲位數": 儲位數,
        "品項數": 品項數,
    }


def _download_xlsx(df: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="明細")
    return bio.getvalue()


# ----------------------------
# UI
# ----------------------------
set_page(
    "出貨訂單應出量分析",
    icon="📦",
    subtitle="自動讀檔｜計算零散/成箱應出｜輸出處理後明細",
)

card_open("📌 上傳明細檔")
uploaded = st.file_uploader(
    "請上傳明細檔（Excel / CSV / HTML）",
    type=["xlsx", "xls", "xlsb", "xlsm", "csv", "html", "htm"],
    accept_multiple_files=False,
)
card_close()

if not uploaded:
    st.info("請先上傳檔案後，系統會自動計算「零散/成箱應出」與「儲位數/品項數」。")
    st.stop()

# 讀檔
try:
    df, read_note = _load_dataframe(uploaded)
except Exception as e:
    st.error(f"讀檔失敗：{e}")
    st.stop()

st.success(f"已讀取：{uploaded.name}（{len(df):,} 筆 / {len(df.columns):,} 欄）")
st.caption(f"讀取方式：{read_note}")

# 計算
try:
    result = _compute(df)
except Exception as e:
    st.error(f"計算失敗：{e}")
    st.stop()

# ----------------------------
# ✅ 指標呈現：兩大區塊 + 直向 metrics
# ----------------------------
left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("### 庫存出貨訂單量")
    # ✅ 直向：零散在上、成箱在下
    st.metric("出貨訂單庫存零散應出", _fmt_qty(result["零散應出"]))
    st.metric("出貨訂單庫存成箱應出", _fmt_qty(result["成箱應出"]))

with right:
    st.markdown("### 總揀")
    # ✅ 直向：儲位數在上、品項數在下
    if result["儲位數"] is None:
        st.metric("儲位數", "—")
        st.caption("（明細未提供「儲位」欄位）")
    else:
        st.metric("儲位數", _fmt_int(result["儲位數"]))

    if result["品項數"] is None:
        st.metric("品項數", "—")
        st.caption("（明細未提供「商品」欄位）")
    else:
        st.metric("品項數", _fmt_int(result["品項數"]))

# ----------------------------
# 明細預覽 + 下載
# ----------------------------
card_open("📄 明細預覽（已加入：原始配庫存出貨單位量）")

# 顯示部分欄位優先（有就排前面）
preferred = [
    "原始配庫存量",
    "出貨入數",
    "計量單位",
    "原始配庫存出貨單位量",
    "儲位",
    "商品",
]
cols = list(result["df"].columns)
ordered = [c for c in preferred if c in cols] + [c for c in cols if c not in preferred]

st.dataframe(
    result["df"][ordered].head(300),
    use_container_width=True,
    height=420,
)

xlsx_bytes = _download_xlsx(result["df"][ordered])
st.download_button(
    label="⬇️ 下載處理後明細（Excel）",
    data=xlsx_bytes,
    file_name=f"{Path(uploaded.name).stem}_出貨應出量分析_處理後.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
card_close()
