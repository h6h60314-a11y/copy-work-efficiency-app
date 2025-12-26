# -*- coding: utf-8 -*-
import pandas as pd
import streamlit as st
from io import BytesIO

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ----------------------------
# helpers
# ----------------------------
REQUIRED_COLS = [
    "提供日期",
    "驗收日",
    "採購單號",
    "供應商代號",
    "廠商名",
    "商品碼",
    "數量",
    "門市代碼",
    "門市名",
    "未配出原因",
    "備註",
]


def _as_text(x):
    if x is None:
        return ""
    # 避免 NaN
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x)


def _read_excel(uploaded_file, sheet_name=0) -> pd.DataFrame:
    # uploaded_file: streamlit UploadedFile
    return pd.read_excel(uploaded_file, sheet_name=sheet_name, engine="openpyxl")


def _read_excel_all_sheets(uploaded_file) -> dict:
    return pd.read_excel(uploaded_file, sheet_name=None, engine="openpyxl")


def _ensure_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    # 依指定欄位順序排前面（其餘欄位保留在後面）
    front = [c for c in cols if c in df.columns]
    tail = [c for c in df.columns if c not in front]
    return df[front + tail]


def _build_output_bytes(sheets: dict) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets.items():
            # Excel 分頁名限制 31 字，保險處理
            safe_name = str(name)[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    bio.seek(0)
    return bio.getvalue()


# ----------------------------
# page
# ----------------------------
st.set_page_config(page_title="大豐物流｜採品門市差異量", page_icon="📄", layout="wide")
inject_logistics_theme()
set_page("📄 採品門市差異量（依未配出原因回填分頁）", "出貨課｜採品／門市差異彙整")

card_open("操作說明")
st.markdown(
    """
- 上傳 **2 個 Excel 檔**：  
  1) **採品明細**（含欄位：`未配出原因` 等）  
  2) **採品門市差異量**（多分頁，分頁名稱 = 未配出原因）
- 系統會把「採品明細」逐筆依 `未配出原因` 追加到對應分頁。
- 僅當 `未配出原因` **有對應分頁名稱** 時才會寫入；找不到分頁的會列在「未對應清單」。
"""
)
card_close()

col1, col2 = st.columns(2)
with col1:
    f_detail = st.file_uploader("① 上傳：採品明細（.xlsx）", type=["xlsx"], accept_multiple_files=False)
with col2:
    f_book = st.file_uploader("② 上傳：採品門市差異量（多分頁 .xlsx）", type=["xlsx"], accept_multiple_files=False)

st.divider()

if not f_detail or not f_book:
    st.info("請先完成兩個檔案上傳。")
    st.stop()

# 讀檔
try:
    df_detail = _read_excel(f_detail, sheet_name=0)
except Exception as e:
    st.error(f"採品明細讀取失敗：{e}")
    st.stop()

try:
    sheets = _read_excel_all_sheets(f_book)  # dict[sheet_name] = DataFrame
except Exception as e:
    st.error(f"採品門市差異量（多分頁）讀取失敗：{e}")
    st.stop()

# 檢查必要欄位（至少要有 未配出原因）
if "未配出原因" not in df_detail.columns:
    st.error("採品明細缺少必要欄位：未配出原因")
    st.stop()

# 若採品明細沒有「備註」，也先補一個空欄
if "備註" not in df_detail.columns:
    df_detail["備註"] = ""

# 統一欄位
df_detail = _ensure_cols(df_detail, REQUIRED_COLS)

# 先把各分頁也補齊欄位（避免原本分頁缺欄導致輸出不一致）
for k in list(sheets.keys()):
    try:
        sheets[k] = _ensure_cols(sheets[k].copy(), REQUIRED_COLS)
    except Exception:
        # 若某分頁是空或異常，也給一個空表
        sheets[k] = pd.DataFrame(columns=REQUIRED_COLS)

# 主邏輯：依未配出原因回填
matched = 0
skipped = 0
missing_reasons = []

for _, row in df_detail.iterrows():
    reason = _as_text(row.get("未配出原因")).strip()
    if not reason:
        skipped += 1
        continue

    if reason in sheets:
        new_row = pd.DataFrame([{c: row.get(c, "") for c in REQUIRED_COLS}])
        sheets[reason] = pd.concat([sheets[reason], new_row], ignore_index=True)
        matched += 1
    else:
        missing_reasons.append(reason)
        skipped += 1

# 統計展示
card_open("處理結果")
c1, c2, c3 = st.columns(3)
c1.metric("寫入筆數", f"{matched:,}")
c2.metric("略過筆數", f"{skipped:,}")
c3.metric("分頁總數", f"{len(sheets):,}")
card_close()

if missing_reasons:
    uniq_missing = sorted(set([x for x in missing_reasons if x]))
    with st.expander(f"未對應分頁的 未配出原因（{len(uniq_missing)} 種）", expanded=False):
        st.write(uniq_missing)

# 下載
out_bytes = _build_output_bytes(sheets)
out_name = "更新後的採品門市差異量.xlsx"

st.download_button(
    label="⬇️ 下載：更新後的採品門市差異量.xlsx",
    data=out_bytes,
    file_name=out_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# 預覽（可收合）
with st.expander("預覽：採品明細（前 200 筆）", expanded=False):
    st.dataframe(df_detail.head(200), use_container_width=True)

with st.expander("預覽：分頁內容（選一張）", expanded=False):
    sheet_names = list(sheets.keys())
    pick = st.selectbox("分頁", sheet_names, index=0 if sheet_names else None)
    if pick:
        st.dataframe(sheets[pick].head(200), use_container_width=True)
