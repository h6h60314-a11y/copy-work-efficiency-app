# pages/11_出貨訂單應出量分析.py
import io
from pathlib import Path

import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ----------------------------
# Page config / Theme
# ----------------------------
st.set_page_config(page_title="庫存訂單應出量分析", page_icon="📦", layout="wide")
inject_logistics_theme()


# ----------------------------
# Helpers
# ----------------------------
def _fmt_qty(x):
    try:
        v = float(x)
    except Exception:
        return str(x)
    s = f"{v:,.2f}"
    return s[:-3] if s.endswith(".00") else s


def _fmt_int(x):
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)


def _read_csv_best_effort(b: bytes) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "big5", "cp950"):
        try:
            return pd.read_csv(io.BytesIO(b), encoding=enc)
        except Exception:
            pass
    return pd.read_csv(io.BytesIO(b), encoding="latin-1")


def _read_html_best_effort(b: bytes) -> pd.DataFrame:
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


def _resolve_col(df: pd.DataFrame, want: str) -> str | None:
    """
    欄位名稱容錯：支援前後空白差異（例如「商品 」）
    - 先找完全相同
    - 再找 strip 後相同
    """
    if want in df.columns:
        return want
    w = want.strip()
    if w in df.columns:
        return w
    for c in df.columns:
        if isinstance(c, str) and c.strip() == w:
            return c
    return None


def _load_dataframe(uploaded_file, key_prefix: str = "") -> tuple[pd.DataFrame, str]:
    """
    回傳 (df, 讀取方式描述)
    key_prefix：用於多檔時，避免 selectbox key 衝突
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

    last_err = None
    for eng in engines:
        try:
            xf = pd.ExcelFile(io.BytesIO(b), engine=eng)
            sheet_names = xf.sheet_names
            sheet = sheet_names[0] if sheet_names else 0

            if len(sheet_names) > 1:
                chosen = st.selectbox(
                    f"選擇工作表：{name}",
                    sheet_names,
                    index=0,
                    key=f"{key_prefix}__sheet__{name}__{eng}",
                )
                sheet = chosen

            df = pd.read_excel(io.BytesIO(b), engine=eng, sheet_name=sheet)
            return df, f"Excel({ext}, engine={eng}, sheet={sheet})"
        except Exception as e:
            last_err = e
            continue

    raise ValueError(f"Excel 讀取失敗：{last_err}")


def _compute(df: pd.DataFrame) -> dict:
    """
    ✅ 最終邏輯：
    - 計量單位=3、6 → 零散：加總「計量單位數量」
    - 計量單位=2 → 成箱 PCS：套用與「實作量」相同邏輯
        1. 出貨單位數量 = 數量 / 出貨入數
        2. 出貨單位數量 = 1 → 計「數量」
        3. 出貨單位數量 != 1 且為整數 → 計「出貨單位數量」
        4. 出貨單位數量 != 1 且為小數 → 計「數量」
    - 品項數：不重複的「商品 」(含尾端空白的欄位名)，若不存在才退回商品
    """
    unit_col = _resolve_col(df, "計量單位")
    qty_col = _resolve_col(df, "數量")
    unitqty_col = _resolve_col(df, "計量單位數量")
    ship_in_col = _resolve_col(df, "出貨入數")

    required = [
        ("計量單位", unit_col),
        ("數量", qty_col),
        ("計量單位數量", unitqty_col),
        ("出貨入數", ship_in_col),
    ]
    missing = [n for n, c in required if c is None]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}")

    out = df.copy()

    # 型別處理
    out[unit_col] = pd.to_numeric(out[unit_col], errors="coerce")
    out[qty_col] = pd.to_numeric(out[qty_col], errors="coerce").fillna(0)
    out[unitqty_col] = pd.to_numeric(out[unitqty_col], errors="coerce").fillna(0)
    out[ship_in_col] = pd.to_numeric(out[ship_in_col], errors="coerce")

    # 分類欄位（方便檢核）
    def _type(u):
        if pd.isna(u):
            return ""
        try:
            u = int(u)
        except Exception:
            return ""
        if u == 2:
            return "成箱"
        if u in (3, 6):
            return "零散"
        return ""

    out["應出類型"] = out[unit_col].apply(_type)

    # 新增「出貨單位數量」= 數量 / 出貨入數
    # 入數為 0 或空值時，結果設為 NA，避免除以 0
    out["出貨單位數量"] = pd.NA
    valid_in = out[ship_in_col].notna() & (out[ship_in_col] != 0)
    out.loc[valid_in, "出貨單位數量"] = (
        out.loc[valid_in, qty_col] / out.loc[valid_in, ship_in_col]
    )
    out["出貨單位數量"] = pd.to_numeric(out["出貨單位數量"], errors="coerce")

    # 零散：維持原邏輯
    零散 = out.loc[out[unit_col].isin([3, 6]), unitqty_col].sum()

    # 成箱 PCS：套用「實作量」相同邏輯
    mask_box = out[unit_col] == 2
    units = out["出貨單位數量"]

    # 1) 出貨單位數量 = 1 → 計數量
    mask_eq1 = mask_box & units.notna() & (units == 1)
    box_eq1 = out.loc[mask_eq1, qty_col].sum()

    # 2) 出貨單位數量 != 1 且為整數 → 計出貨單位數量
    mask_integer = (
        mask_box
        & units.notna()
        & (units != 1)
        & (units % 1 == 0)
    )
    box_integer = out.loc[mask_integer, "出貨單位數量"].sum()

    # 3) 出貨單位數量 != 1 且為小數 → 計數量
    mask_decimal = (
        mask_box
        & units.notna()
        & (units != 1)
        & (units % 1 != 0)
    )
    box_decimal = out.loc[mask_decimal, qty_col].sum()

    成箱 = box_eq1 + box_integer + box_decimal

    # 額外新增每筆「成箱PCS計入值」，方便直接檢核
    out["成箱PCS計入值"] = 0.0
    out.loc[mask_eq1, "成箱PCS計入值"] = out.loc[mask_eq1, qty_col]
    out.loc[mask_integer, "成箱PCS計入值"] = out.loc[mask_integer, "出貨單位數量"]
    out.loc[mask_decimal, "成箱PCS計入值"] = out.loc[mask_decimal, qty_col]

    slot_col = _resolve_col(out, "儲位")
    儲位數 = out[slot_col].nunique() if slot_col else None

    # 品項數 = 不重複「商品 」(優先)
    prod_col = _resolve_col(out, "商品 ")
    if not prod_col:
        prod_col = _resolve_col(out, "商品")

    if prod_col:
        prod = out[prod_col].astype(str).str.strip()
        prod = prod.replace({
            "": pd.NA,
            "nan": pd.NA,
            "None": pd.NA,
            "NULL": pd.NA,
            "NaN": pd.NA,
        })
        品項數 = prod.dropna().nunique()
    else:
        品項數 = None

    return {
        "df": out,
        "零散應出": float(零散) if pd.notna(零散) else 0.0,
        "成箱應出": float(成箱) if pd.notna(成箱) else 0.0,
        "儲位數": 儲位數,
        "品項數": 品項數,
    }

def _download_xlsx(summary_df: pd.DataFrame, combined_df: pd.DataFrame, per_file_dfs: list[tuple[str, pd.DataFrame]]) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="彙總")
        combined_df.to_excel(writer, index=False, sheet_name="明細_合併")

        for name, df in per_file_dfs:
            safe = Path(name).stem[:31]
            base = safe
            i = 1
            while safe in writer.book.sheetnames:
                suffix = f"_{i}"
                safe = (base[: max(0, 31 - len(suffix))] + suffix)[:31]
                i += 1
            df.to_excel(writer, index=False, sheet_name=safe)

    return bio.getvalue()


# ----------------------------
# UI
# ----------------------------
set_page(
    "庫存訂單應出量分析",
    icon="📦",
    subtitle="支援多檔上傳｜成箱PCS套用數量÷出貨入數判斷｜零散(計量單位=3,6)加總『計量單位數量』｜品項數=不重複『商品 』｜可🧹清除",
)

# uploader 清除機制
if "uploader_key_11" not in st.session_state:
    st.session_state["uploader_key_11"] = 0

card_open("📌 上傳明細檔（可多檔）")

u1, u2 = st.columns([1, 0.08], gap="small")
with u1:
    uploaded_files = st.file_uploader(
        "請上傳明細檔（Excel / CSV / HTML，可一次多個）",
        type=["xlsx", "xls", "xlsb", "xlsm", "csv", "html", "htm"],
        accept_multiple_files=True,
        key=f"uploader_11_{st.session_state['uploader_key_11']}",
    )
with u2:
    st.markdown(" ")
    if st.button("🧹", help="清除已上傳檔案", use_container_width=True):
        st.session_state["uploader_key_11"] += 1
        st.rerun()

card_close()

if not uploaded_files:
    st.info("請先上傳檔案後，系統會自動計算「零散/成箱應出」與「儲位數/品項數」。")
    st.stop()

items = []
errors = []

for i, uf in enumerate(uploaded_files, start=1):
    try:
        df, read_note = _load_dataframe(uf, key_prefix=f"f{i}")
        res = _compute(df)

        df_out = res["df"].copy()
        df_out.insert(0, "來源檔名", uf.name)
        res["df"] = df_out

        items.append(
            {
                "name": uf.name,
                "read_note": read_note,
                "rows": len(df),
                "cols": len(df.columns),
                "res": res,
            }
        )
    except Exception as e:
        errors.append((uf.name, str(e)))

if errors:
    with st.expander("⚠️ 部分檔案讀取/計算失敗（點開查看）", expanded=True):
        for fn, msg in errors:
            st.error(f"{fn}：{msg}")

if not items:
    st.error("沒有任何檔案可成功計算，請確認欄位是否包含：計量單位、數量、計量單位數量、出貨入數。")
    st.stop()

combined_df = pd.concat([it["res"]["df"] for it in items], ignore_index=True)

total_loose = sum(it["res"]["零散應出"] for it in items)
total_box = sum(it["res"]["成箱應出"] for it in items)

slot_col_all = _resolve_col(combined_df, "儲位")
combined_slots = combined_df[slot_col_all].nunique() if slot_col_all else None

# ✅ 合併品項數：不重複「商品 」(優先)
prod_col_all = _resolve_col(combined_df, "商品 ")
if not prod_col_all:
    prod_col_all = _resolve_col(combined_df, "商品")

if prod_col_all:
    prod_all = combined_df[prod_col_all].astype(str).str.strip()
    prod_all = prod_all.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NULL": pd.NA, "NaN": pd.NA})
    combined_items = prod_all.dropna().nunique()
else:
    combined_items = None

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown("### 庫存出貨訂單量（彙總）")
    st.metric("出貨訂單庫存零散應出（計量單位數量加總）", _fmt_qty(total_loose))
    st.metric("出貨訂單庫存成箱 PCS", _fmt_qty(total_box))

with right:
    st.markdown("### 總揀（彙總）")
    if combined_slots is None:
        st.metric("儲位數", "—")
        st.caption("（所有檔案都未提供「儲位」欄位）")
    else:
        st.metric("儲位數", _fmt_int(combined_slots))

    if combined_items is None:
        st.metric("品項數", "—")
        st.caption("（所有檔案都未提供「商品 」欄位）")
    else:
        st.metric("品項數", _fmt_int(combined_items))

summary_rows = []
for it in items:
    r = it["res"]
    summary_rows.append(
        {
            "檔名": it["name"],
            "讀取方式": it["read_note"],
            "筆數": it["rows"],
            "欄數": it["cols"],
            "零散應出": r["零散應出"],
            "成箱應出": r["成箱應出"],
            "儲位數": r["儲位數"] if r["儲位數"] is not None else "",
            "品項數": r["品項數"] if r["品項數"] is not None else "",
        }
    )
summary_df = pd.DataFrame(summary_rows)

card_open("📊 多檔彙總")
st.dataframe(summary_df, use_container_width=True, height=260)
card_close()

# 明細預覽 + 下載（同時兼容 商品 / 商品 ）
preferred = [
    "來源檔名",
    "計量單位",
    "應出類型",
    "數量",
    "計量單位數量",
    "出貨入數",
    "出貨單位數量",
    "成箱PCS計入值",
    "儲位",
    "商品 ",
    "商品",
]
cols = list(combined_df.columns)
ordered = [c for c in preferred if c in cols] + [c for c in cols if c not in preferred]

card_open("📄 明細預覽（合併）")
st.dataframe(combined_df[ordered].head(300), use_container_width=True, height=420)
card_close()

with st.expander("🔎 各檔明細預覽（點開）", expanded=False):
    tabs = st.tabs([f"{i+1}. {it['name']}" for i, it in enumerate(items)])
    for tab, it in zip(tabs, items):
        with tab:
            dfp = it["res"]["df"]
            cols2 = list(dfp.columns)
            ordered2 = [c for c in preferred if c in cols2] + [c for c in cols2 if c not in preferred]
            st.caption(f"讀取方式：{it['read_note']}｜{it['rows']:,} 筆 / {it['cols']:,} 欄")
            st.dataframe(dfp[ordered2].head(300), use_container_width=True, height=380)

xlsx_bytes = _download_xlsx(
    summary_df=summary_df,
    combined_df=combined_df[ordered],
    per_file_dfs=[(it["name"], it["res"]["df"][ordered]) for it in items],
)

st.download_button(
    label="⬇️ 下載結果（Excel：彙總 + 合併明細 + 各檔明細）",
    data=xlsx_bytes,
    file_name="多檔_出貨應出量分析_結果.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
