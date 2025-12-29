# pages/23_採品門市差異量.py
# -*- coding: utf-8 -*-
import os
import pandas as pd
import streamlit as st
from io import BytesIO, StringIO

from common_ui import inject_logistics_theme, set_page, card_open, card_close


# ============================
# 你指定的模板檔（預設）
# ============================
DEFAULT_TEMPLATE_PATH = r"C:\Users\User\Desktop\2採品門市差異量.xlsx"
TEMPLATE_FILENAME = "2採品門市差異量.xlsx"

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


# ============================
# helpers
# ============================
def _as_text(x):
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x)


def _ensure_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    front = [c for c in cols if c in df.columns]
    tail = [c for c in df.columns if c not in front]
    return df[front + tail]


def _build_output_bytes(sheets: dict) -> bytes:
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe_name = str(name)[:31]
            df.to_excel(writer, sheet_name=safe_name, index=False)
    bio.seek(0)
    return bio.getvalue()


def _desktop_candidates(filename: str) -> list[str]:
    """
    同時嘗試：
    - 一般 Desktop
    - OneDrive Desktop
    - 使用者主目錄推算
    """
    candidates = []

    userprofile = os.environ.get("USERPROFILE", "")
    onedrive = os.environ.get("OneDrive", "") or os.environ.get("ONEDRIVE", "")

    # 1) 使用者桌面（常見）
    if userprofile:
        candidates.append(os.path.join(userprofile, "Desktop", filename))

    # 2) OneDrive 桌面（超常見）
    if onedrive:
        candidates.append(os.path.join(onedrive, "Desktop", filename))

    # 3) expanduser 推算
    home = os.path.expanduser("~")
    if home:
        candidates.append(os.path.join(home, "Desktop", filename))
        candidates.append(os.path.join(home, "OneDrive", "Desktop", filename))

    # 去重但保留順序
    seen = set()
    out = []
    for p in candidates:
        if p not in seen:
            out.append(p)
            seen.add(p)
    return out


def _find_template_path(manual_path: str | None) -> tuple[str | None, list[str]]:
    """
    回傳：(找到的路徑 or None, 嘗試過的路徑清單)
    """
    tried = []

    # 先試使用者手動指定的
    if manual_path:
        tried.append(manual_path)
        if os.path.exists(manual_path):
            return manual_path, tried

    # 再試預設路徑
    tried.append(DEFAULT_TEMPLATE_PATH)
    if os.path.exists(DEFAULT_TEMPLATE_PATH):
        return DEFAULT_TEMPLATE_PATH, tried

    # 再試各種 Desktop / OneDrive Desktop 推算
    for p in _desktop_candidates(TEMPLATE_FILENAME):
        tried.append(p)
        if os.path.exists(p):
            return p, tried

    # 最後試專案相對路徑（若你後面決定丟到專案內）
    rels = [
        os.path.join("assets", "templates", TEMPLATE_FILENAME),
        os.path.join("templates", TEMPLATE_FILENAME),
        TEMPLATE_FILENAME,
    ]
    for p in rels:
        tried.append(p)
        if os.path.exists(p):
            return p, tried

    return None, tried


@st.cache_data(show_spinner=False)
def _load_template_sheets_cached(template_path: str, mtime: float) -> dict:
    sheets = pd.read_excel(template_path, sheet_name=None, engine="openpyxl")
    fixed = {}
    for k, df in sheets.items():
        try:
            fixed[k] = _ensure_cols(df.copy(), REQUIRED_COLS)
        except Exception:
            fixed[k] = pd.DataFrame(columns=REQUIRED_COLS)
    return fixed


def _load_template_sheets(template_path: str) -> dict:
    mtime = os.path.getmtime(template_path)
    return _load_template_sheets_cached(template_path, mtime)


def _read_pasted_table(text: str) -> pd.DataFrame:
    raw = (text or "").strip("\n").strip()
    if not raw:
        raise ValueError("貼上的內容是空的。請從 Excel 複製整段（含表頭）再貼上。")

    # Excel 複製通常是 TAB
    try:
        df = pd.read_csv(StringIO(raw), sep="\t", dtype=str)
        if df.shape[1] <= 1:
            raise ValueError("not tab")
        return df
    except Exception:
        pass

    # CSV
    try:
        df = pd.read_csv(StringIO(raw), sep=",", dtype=str)
        if df.shape[1] <= 1:
            raise ValueError("not csv")
        return df
    except Exception:
        pass

    # 空白分隔
    df = pd.read_csv(StringIO(raw), sep=r"\s+", dtype=str)
    if df.shape[1] <= 1:
        raise ValueError("無法解析貼上內容：請確認是 Excel 複製（通常 TAB 分隔）且包含表頭。")
    return df


# ============================
# page
# ============================
st.set_page_config(page_title="大豐物流｜採品門市差異量", page_icon="📄", layout="wide")
inject_logistics_theme()
set_page("📄 採品門市差異量（貼上即更新匯出檔）", "出貨課｜採品／門市差異彙整")

# 讓你可在平台上直接改模板路徑（不用改程式）
with st.sidebar:
    st.caption("模板路徑（可直接改）")
    manual_template_path = st.text_input("Template Path", value=DEFAULT_TEMPLATE_PATH)

template_path, tried_paths = _find_template_path(manual_template_path)

card_open("模板來源（不需上傳）")
if template_path:
    st.success("模板已找到。")
    st.code(template_path)
else:
    st.error("找不到模板檔（Streamlit 執行環境無法存取此路徑）。")
    with st.expander("我嘗試過的路徑（請用這份清單比對你實際檔案位置）", expanded=False):
        for p in tried_paths:
            st.code(p)
    st.info(
        "✅ 最常見是 Desktop 在 OneDrive：請到檔案『內容/位置』確認路徑，常見會是：\n"
        r"C:\Users\User\OneDrive\Desktop\2採品門市差異量.xlsx"
    )
card_close()

if not template_path:
    st.stop()

card_open("貼上採品明細（含表頭）")
pasted = st.text_area(
    "從 Excel 複製整段（含表頭）→ 直接貼上。內容一變就會自動更新匯出檔（下載按鈕即時刷新）。",
    height=260,
    placeholder="Excel：選取含表頭資料 → Ctrl+C → 這裡 Ctrl+V",
)
card_close()

st.divider()

# 沒內容就不產生
if not (pasted or "").strip():
    st.info("請先貼上採品明細資料（含表頭）。")
    st.stop()

# 解析貼上資料：解析失敗時不要整頁掛（你還在貼的時候很常發生）
try:
    df_detail = _read_pasted_table(pasted)
except Exception as e:
    st.warning(f"尚未能解析貼上內容：{e}")
    st.stop()

if "未配出原因" not in df_detail.columns:
    st.error("採品明細缺少必要欄位：未配出原因（請確認貼上資料的表頭名稱一致）")
    st.stop()

if "備註" not in df_detail.columns:
    df_detail["備註"] = ""

df_detail = _ensure_cols(df_detail.copy(), REQUIRED_COLS)

# 讀模板（多分頁）
try:
    sheets = _load_template_sheets(template_path)
except Exception as e:
    st.error(f"模板讀取失敗：{e}")
    st.stop()

# 回填
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

# 每次 rerun 都重算 → 貼上內容一變就更新
out_bytes = _build_output_bytes(sheets)
out_name = "更新後的採品門市差異量.xlsx"

card_open("處理結果（即時更新）")
c1, c2, c3 = st.columns(3)
c1.metric("寫入筆數", f"{matched:,}")
c2.metric("略過筆數", f"{skipped:,}")
c3.metric("模板分頁數", f"{len(sheets):,}")
card_close()

if missing_reasons:
    uniq_missing = sorted(set([x for x in missing_reasons if x]))
    with st.expander(f"未對應模板分頁的 未配出原因（{len(uniq_missing)} 種）", expanded=False):
        st.write(uniq_missing)

st.download_button(
    label="⬇️ 下載：更新後的採品門市差異量.xlsx（即時）",
    data=out_bytes,
    file_name=out_name,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

with st.expander("預覽：採品明細（前 200 筆）", expanded=False):
    st.dataframe(df_detail.head(200), use_container_width=True)
