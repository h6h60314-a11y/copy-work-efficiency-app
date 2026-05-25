# pages/4_儲位使用率.py
# -*- coding: utf-8 -*-
"""
4_儲位使用率（部署版 / Streamlit）

✅ 本版調整（依你最新要求）：
- ❌ 不再做 區(溫層) 大/中/小
- ✅ 只計算 4 類：輕型料架、重型低空、落地儲、高空儲（區碼 → 儲位類型）
- ✅ 分類唯一使用 STORAGE_TYPE_ZONES
"""

import io
import os
import re
import warnings

import pandas as pd
import streamlit as st

warnings.filterwarnings("ignore")

# ---- 套用平台風格（有就用，沒有就退回原生）----
try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close

    HAS_COMMON_UI = True
except Exception:
    HAS_COMMON_UI = False


# =========================================================
# ✅ 唯一分類邏輯：區碼 → 儲位類型（你指定）
# =========================================================
STORAGE_TYPE_ZONES = {
    "輕型料架": ["001", "002", "003", "017", "016"],
    "落地儲": ["014", "018", "019", "020", "010", "081", "401", "402", "403", "015","404"],
    "重型低空": ["011", "012", "013", "031", "032", "033", "034", "035", "036", "037", "038"],
    "高空儲": [
        "021", "022", "023",
        "041", "042", "043",
        "051", "052", "053", "054", "055", "056", "057",
        "301", "302", "303", "304", "305", "306",
    ],
}
_STORAGE_TYPE_SETS = {k: set(v) for k, v in STORAGE_TYPE_ZONES.items()}
TYPE_ORDER = ["輕型料架", "落地儲", "重型低空", "高空儲", "未知"]


# =========================
# UI：縮小版（比照 18）
# =========================
def inject_compact_css():
    st.markdown(
        r"""
<style>
html, body, [class*="css"]{ font-size: 14px !important; }
.block-container{ padding-top: .85rem !important; padding-bottom: 1.15rem !important; }
h1{ font-size: 1.50rem !important; margin: .15rem 0 .35rem !important; }
h2{ font-size: 1.12rem !important; margin: .35rem 0 .20rem !important; }
h3{ font-size: 1.00rem !important; margin: .28rem 0 .12rem !important; }
p, li{ line-height: 1.45 !important; }
div[data-testid="stMetric"]{ padding: 6px 10px !important; }
div[data-testid="stMetric"] label{ font-size: 12px !important; }
div[data-testid="stMetric"] div{ font-size: 20px !important; }
div[data-testid="stDataFrame"]{ margin-top: .15rem !important; }
</style>
""",
        unsafe_allow_html=True,
    )


def _spacer(px: int = 10):
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)


# =========================
# 讀檔：支援 xlsb
# =========================
def detect_sheet_for_column(xls: pd.ExcelFile, must_have: str, engine: str | None = None) -> str:
    for name in xls.sheet_names:
        try:
            df0 = pd.read_excel(xls, sheet_name=name, nrows=0, engine=engine)
            if must_have in df0.columns:
                return name
        except Exception:
            continue
    return xls.sheet_names[0]


def robust_read_uploaded(uploaded) -> tuple[pd.DataFrame, str]:
    filename = uploaded.name
    ext = os.path.splitext(filename)[1].lower()
    data = uploaded.getvalue()
    bio = io.BytesIO(data)

    if ext == ".csv":
        df = pd.read_csv(bio, encoding="utf-8-sig")
        return df, "CSV"

    if ext == ".xlsb":
        xls = pd.ExcelFile(bio, engine="pyxlsb")
        sheet = None
        for key in ["棚別", "區(溫層)"]:
            candidate = detect_sheet_for_column(xls, key, engine="pyxlsb")
            try:
                cols = pd.read_excel(xls, sheet_name=candidate, nrows=0, engine="pyxlsb").columns
                if key in cols:
                    sheet = candidate
                    break
            except Exception:
                pass
        if sheet is None:
            sheet = xls.sheet_names[0]
        df = pd.read_excel(xls, sheet_name=sheet, engine="pyxlsb")
        return df, sheet

    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        engine = "openpyxl"
    elif ext == ".xls":
        engine = "xlrd"
    else:
        raise ValueError(f"不支援的檔案格式：{ext}")

    xls = pd.ExcelFile(bio, engine=engine)
    sheet = None
    for key in ["棚別", "區(溫層)"]:
        candidate = detect_sheet_for_column(xls, key, engine=None)
        try:
            cols = pd.read_excel(xls, sheet_name=candidate, nrows=0).columns
            if key in cols:
                sheet = candidate
                break
        except Exception:
            pass

    if sheet is None:
        sheet = xls.sheet_names[0]

    df = pd.read_excel(xls, sheet_name=sheet)
    return df, sheet


# =========================
# 通用：抓 3 碼區碼 + 分類
# =========================
def _to_zone3(x) -> str:
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    s = str(x).strip()
    m = re.search(r"\d{3}", s)
    if m:
        return m.group(0)
    s = re.sub(r"\D", "", s)
    return s.zfill(3) if s else ""


def classify_storage_type(zone_like_value) -> str:
    """區碼 → 儲位類型（唯一邏輯：STORAGE_TYPE_ZONES）"""
    z = _to_zone3(zone_like_value)
    if not z:
        return "未知"
    for k in ["輕型料架", "落地儲", "重型低空", "高空儲"]:
        if z in _STORAGE_TYPE_SETS[k]:
            return k
    return "未知"


# =========================
# 計算：依 4 類儲位類型彙總（有效/已用/未用/使用率）
# =========================
def _safe_sum(s: pd.Series) -> float:
    return pd.to_numeric(s, errors="coerce").fillna(0).sum()


def calc_util_by_storage_type(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    回傳：
    - df_util：四類 + 總計（有效貨位/已使用/未使用/使用率）
    - df_detail：明細 + 區碼3 + 儲位類型
    - df_unknown：未知明細
    """
    df2 = df.copy()

    # 來源欄位：優先棚別，其次區(溫層)
    src_col = None
    if "棚別" in df2.columns:
        src_col = "棚別"
    elif "區(溫層)" in df2.columns:
        src_col = "區(溫層)"
    else:
        raise KeyError("缺少『棚別』或『區(溫層)』欄位，無法做儲位類型分類。")

    df2[src_col] = df2[src_col].astype(str).str.strip()
    df2["區碼3"] = df2[src_col].apply(_to_zone3)
    df2["儲位類型"] = df2["區碼3"].apply(classify_storage_type)

    if "有效貨位" not in df2.columns:
        df2["有效貨位"] = 0
    if "已使用貨位" not in df2.columns:
        df2["已使用貨位"] = 0

    def _row(kind: str) -> dict:
        part = df2[df2["儲位類型"] == kind]
        eff = float(_safe_sum(part["有效貨位"]))
        used = float(_safe_sum(part["已使用貨位"]))
        unused = max(eff - used, 0.0)
        rate = (used / eff * 100.0) if eff else 0.0
        return {
            "儲位類型": kind,
            "有效貨位": int(round(eff)),
            "已使用貨位": int(round(used)),
            "未使用貨位": int(round(unused)),
            "使用率(%)": round(rate, 2),
        }

    rows = [
        _row("輕型料架"),
        _row("落地儲"),
        _row("重型低空"),
        _row("高空儲"),
    ]

    eff_total = float(_safe_sum(df2["有效貨位"]))
    used_total = float(_safe_sum(df2["已使用貨位"]))
    unused_total = max(eff_total - used_total, 0.0)
    rate_total = (used_total / eff_total * 100.0) if eff_total else 0.0

    rows.append(
        {
            "儲位類型": "總計",
            "有效貨位": int(round(eff_total)),
            "已使用貨位": int(round(used_total)),
            "未使用貨位": int(round(unused_total)),
            "使用率(%)": round(rate_total, 2),
        }
    )

    df_util = pd.DataFrame(rows)

    df_unknown = df2[df2["儲位類型"] == "未知"].copy()
    return df_util, df2, df_unknown


def render_util_block(title: str, r: dict):
    st.markdown(f"### {title}")
    st.markdown(f"**有效貨位：** {int(r.get('有效貨位', 0)):,}")
    st.markdown(f"**已使用貨位：** {int(r.get('已使用貨位', 0)):,}")
    st.markdown(f"**未使用貨位：** {int(r.get('未使用貨位', 0)):,}")
    st.markdown(f"**使用率(%)：** {float(r.get('使用率(%)', 0)):.2f}")


# =========================
# 匯出 Excel
# =========================
def build_output_excel_bytes(
    base_name: str,
    df_util: pd.DataFrame,
    df_detail: pd.DataFrame,
    df_shelf: pd.DataFrame,
    df_type: pd.DataFrame,
    df_unknown: pd.DataFrame,
) -> tuple[str, bytes]:
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df_util.to_excel(writer, sheet_name="儲位類型使用率", index=False)
        df_detail.to_excel(writer, sheet_name="明細(含儲位類型)", index=False)
        df_shelf.to_excel(writer, sheet_name="棚別統計", index=False)
        df_type.to_excel(writer, sheet_name="儲位類型統計", index=False)
        df_unknown.to_excel(writer, sheet_name="未知明細", index=False)
    out.seek(0)
    return f"{base_name}_4_儲位使用率_輸出.xlsx", out.getvalue()


# =========================
# Main
# =========================
def main():
    st.set_page_config(page_title="儲位使用率", page_icon="🧊", layout="wide")

    if HAS_COMMON_UI:
        inject_logistics_theme()
        set_page("儲位使用率", icon="🧊", subtitle="依區碼分類：輕型料架/落地儲/重型低空/高空儲（支援 xlsb）")
    else:
        st.title("🧊 儲位使用率")

    inject_compact_css()

    if HAS_COMMON_UI:
        card_open("📤 上傳 Excel（儲位明細）")
    uploaded = st.file_uploader(
        "請上傳檔案（xlsx/xls/xlsm/xlsb/csv）",
        type=["xlsx", "xls", "xlsm", "xlsb", "csv"],
        label_visibility="collapsed",
    )
    if HAS_COMMON_UI:
        card_close()

    if not uploaded:
        st.info("請先上傳儲位明細檔案。")
        return

    # 讀檔
    try:
        df, sheet_used = robust_read_uploaded(uploaded)
    except Exception as e:
        st.error(f"讀取失敗：{e}")
        return

    df.columns = df.columns.astype(str).str.strip()
    st.caption(f"使用分頁：{sheet_used}")

    # 計算（四類 + 總計）
    try:
        df_util, df_detail, df_unknown = calc_util_by_storage_type(df)
    except Exception as e:
        st.error(f"計算失敗：{e}")
        return

    util_rows = {r["儲位類型"]: r for _, r in df_util.iterrows()}

    # -------------------------
    # 上方：四類卡片（兩列兩欄）+ 總計
    # -------------------------
    left, right = st.columns(2, gap="large")

    with left:
        if HAS_COMMON_UI:
            card_open("📌 儲位類型使用率（KPI）")

        r1c1, r1c2 = st.columns(2, gap="large")
        with r1c1:
            render_util_block("輕型料架", util_rows.get("輕型料架", {}))
        with r1c2:
            render_util_block("落地儲", util_rows.get("落地儲", {}))

        _spacer(6)

        r2c1, r2c2 = st.columns(2, gap="large")
        with r2c1:
            render_util_block("重型低空", util_rows.get("重型低空", {}))
        with r2c2:
            render_util_block("高空儲", util_rows.get("高空儲", {}))

        _spacer(6)
        render_util_block("總計", util_rows.get("總計", {}))

        if HAS_COMMON_UI:
            card_close()

    # -------------------------
    # 右欄：統計表 + 匯出
    # -------------------------
    with right:
        if HAS_COMMON_UI:
            card_open("📊 統計")

        # 儲位類型統計（筆數）
        df_type = (
            df_detail.groupby(["儲位類型"], dropna=False)
            .size()
            .reset_index(name="筆數")
        )
        df_type["__ord"] = df_type["儲位類型"].apply(lambda x: TYPE_ORDER.index(x) if x in TYPE_ORDER else 999)
        df_type = df_type.sort_values(["__ord", "儲位類型"]).drop(columns="__ord")

        st.markdown("### 儲位類型統計（筆數）")
        st.dataframe(df_type, use_container_width=True, hide_index=True, height=220)

        # 棚別統計 Top50（若有棚別）
        if "棚別" in df_detail.columns:
            df_shelf = (
                df_detail.groupby(["棚別"], dropna=False)
                .size()
                .reset_index(name="筆數")
                .sort_values(["筆數", "棚別"], ascending=[False, True])
            )
        else:
            df_shelf = pd.DataFrame(columns=["棚別", "筆數"])

        base = os.path.splitext(uploaded.name)[0]
        out_name, out_bytes = build_output_excel_bytes(
            base_name=base,
            df_util=df_util,
            df_detail=df_detail,
            df_shelf=df_shelf,
            df_type=df_type,
            df_unknown=df_unknown,
        )

        _spacer(8)
        st.download_button(
            "⬇️ 匯出（儲位使用率 Excel）",
            data=out_bytes,
            file_name=out_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        if HAS_COMMON_UI:
            card_close()

    # -------------------------
    # 下方：棚別統計 Top50（全寬）
    # -------------------------
    if "棚別" in df_detail.columns and not df_shelf.empty:
        _spacer(10)
        if HAS_COMMON_UI:
            card_open("📋 棚別統計（Top 50）")
        st.dataframe(df_shelf.head(50), use_container_width=True, hide_index=True)
        if HAS_COMMON_UI:
            card_close()

    # -------------------------
    # 下方：未知明細（全寬）
    # -------------------------
    unknown_cnt = len(df_unknown)
    _spacer(8)
    with st.expander(f"📌 未知明細（{unknown_cnt:,} 筆）", expanded=False):
        if unknown_cnt == 0:
            st.success("未知：0 筆")
        else:
            st.dataframe(df_unknown, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
