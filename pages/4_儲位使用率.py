# pages/4_儲位使用率.py
# -*- coding: utf-8 -*-
"""
4_儲位使用率（部署版 / Streamlit）
✅ 特色：
- 支援 xlsx / xls / xlsm / xlsb / csv
- 左欄：區(溫層) 使用率明細（兩欄換列：大/中｜小/總計）
- 右欄：棚別分類統計（兩欄換列：輕型料架/落地儲｜重型低空/高空儲；未知另列 + 明細）
- 「棚別統計 Top50」一定全寬
- 未知明細全寬
- 整體字體/間距縮小（比照 18_各類儲區使用率）
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


# =========================
# ✅ 區(溫層)分區清單（大/中/小）
# =========================
輕型料架 =  ["001", "002", "003", "017", "016"],
落地儲: ["014", "018", "019", "020", "010", "081", "401", "402", "403", "015"]
重型低空: ["011", "012", "013", "031", "032", "033", "034", "035", "036", "037", "038"]
高空儲: [
        "021", "022", "023",
        "041", "042", "043",
        "051", "052", "053", "054", "055", "056", "057",
        "301", "302", "303", "304", "305", "306",
        "311", "312", "313", "314",
        "061"]

輕型料架 = set(輕型料架_ZONES)
落地儲 = set(落地儲_ZONES)
重型低空 = set(重型低空_ZONES)
高空儲 = set(高空儲_ZONES)

# =========================
# ✅ 棚別分類（同步你指定的新邏輯）
# =========================
SHELF_BUCKETS = {
    "輕型料架": ["001", "002", "003", "017", "016"],
    "落地儲": ["014", "018", "019", "020", "010", "081", "401", "402", "403", "015"],
    "重型低空": ["011", "012", "013", "031", "032", "033", "034", "035", "036", "037", "038"],
    "高空儲": [
        "021", "022", "023",
        "041", "042", "043",
        "051", "052", "053", "054", "055", "056", "057",
        "301", "302", "303", "304", "305", "306",
        "311", "312", "313", "314",
        "061",
    ],
}
SHELF_BUCKET_SETS = {k: set(v) for k, v in SHELF_BUCKETS.items()}
SHELF_ORDER = ["輕型料架", "落地儲", "重型低空", "高空儲", "未知"]


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

    # CSV
    if ext == ".csv":
        df = pd.read_csv(bio, encoding="utf-8-sig")
        return df, "CSV"

    # XLSB
    if ext == ".xlsb":
        xls = pd.ExcelFile(bio, engine="pyxlsb")
        sheet = None
        for key in ["區(溫層)", "棚別"]:
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

    # XLS / XLSX
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        engine = "openpyxl"
    elif ext == ".xls":
        engine = "xlrd"
    else:
        raise ValueError(f"不支援的檔案格式：{ext}")

    xls = pd.ExcelFile(bio, engine=engine)

    sheet = None
    for key in ["區(溫層)", "棚別"]:
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
# 計算：區(溫層)使用率
# =========================
def _safe_sum(s: pd.Series) -> float:
    return pd.to_numeric(s, errors="coerce").fillna(0).sum()


def calc_util_by_zone(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    df2["區(溫層)"] = (
        df2["區(溫層)"].astype(str).str.strip().replace({"nan": "", "None": "", "": ""}).str.zfill(3)
    )

    if "有效貨位" not in df2.columns:
        df2["有效貨位"] = 0
    if "已使用貨位" not in df2.columns:
        df2["已使用貨位"] = 0

    def _row(kind: str, zones: set) -> dict:
        part = df2[df2["區(溫層)"].isin(zones)]
        eff = float(_safe_sum(part["有效貨位"]))
        used = float(_safe_sum(part["已使用貨位"]))
        unused = max(eff - used, 0.0)
        rate = (used / eff * 100.0) if eff else 0.0
        return {
            "儲區": kind,
            "有效貨位": int(round(eff)),
            "已使用貨位": int(round(used)),
            "未使用貨位": int(round(unused)),
            "使用率(%)": round(rate, 2),
        }

    rows = [
        _row("大儲位", LARGE),
        _row("中儲位", MID),
        _row("小儲位", SMALL),
    ]

    eff_total = sum(r["有效貨位"] for r in rows)
    used_total = sum(r["已使用貨位"] for r in rows)
    unused_total = max(eff_total - used_total, 0)
    rate_total = (used_total / eff_total * 100.0) if eff_total else 0.0

    rows.append(
        {
            "儲區": "總計",
            "有效貨位": int(eff_total),
            "已使用貨位": int(used_total),
            "未使用貨位": int(unused_total),
            "使用率(%)": round(rate_total, 2),
        }
    )
    return pd.DataFrame(rows)


def render_util_block(title: str, r: dict):
    st.markdown(f"### {title}")
    st.markdown(f"**有效貨位：** {int(r.get('有效貨位', 0)):,}")
    st.markdown(f"**已使用貨位：** {int(r.get('已使用貨位', 0)):,}")
    st.markdown(f"**未使用貨位：** {int(r.get('未使用貨位', 0)):,}")
    st.markdown(f"**使用率(%)：** {float(r.get('使用率(%)', 0)):.2f}")


# =========================
# 計算：棚別分類
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


def classify_from_shelf_bucket(x) -> str:
    z = _to_zone3(x)
    if not z:
        return "未知"
    for bucket, zset in SHELF_BUCKET_SETS.items():
        if z in zset:
            return bucket
    return "未知"


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
        df_util.to_excel(writer, sheet_name="區(溫層)使用率", index=False)
        df_detail.to_excel(writer, sheet_name="明細(含棚別分類)", index=False)
        df_shelf.to_excel(writer, sheet_name="棚別統計", index=False)
        df_type.to_excel(writer, sheet_name="棚別分類統計", index=False)
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
        set_page("儲位使用率", icon="🧊", subtitle="區(溫層)使用率 + 棚別分類（支援 xlsb）")
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

    # 兩欄
    left, right = st.columns(2, gap="large")

    # -------------------------
    # 左欄：區(溫層)分類
    # -------------------------
    with left:
        if HAS_COMMON_UI:
            card_open("📌 區(溫層)分類（KPI + 卡片 + 圖表）")

        need_cols = ["區(溫層)", "有效貨位", "已使用貨位"]
        missing = [c for c in need_cols if c not in df.columns]

        if missing:
            st.warning("⚠️ 此檔案缺少『區(溫層)分類』必要欄位，已跳過此段。")
            st.write("缺少欄位：")
            st.code(missing, language="python")
            df_util = pd.DataFrame()
        else:
            df_util = calc_util_by_zone(df)
            util_rows = {r["儲區"]: r for _, r in df_util.iterrows()}

            r1c1, r1c2 = st.columns(2, gap="large")
            with r1c1:
                render_util_block("大儲位", util_rows.get("大儲位", {}))
            with r1c2:
                render_util_block("中儲位", util_rows.get("中儲位", {}))

            _spacer(6)

            r2c1, r2c2 = st.columns(2, gap="large")
            with r2c1:
                render_util_block("小儲位", util_rows.get("小儲位", {}))
            with r2c2:
                render_util_block("總計", util_rows.get("總計", {}))

        if HAS_COMMON_UI:
            card_close()

    # -------------------------
    # 右欄：棚別分類統計（同步新邏輯）
    # -------------------------
    with right:
        if HAS_COMMON_UI:
            card_open("🏷️ 棚別分類統計（輕型料架/落地儲/重型低空/高空儲/未知）")

        if "棚別" not in df.columns:
            st.error("❌ 找不到欄位『棚別』，無法進行棚別分類。")
            df_detail = df.copy()
            df_detail["儲位類型"] = "未知"
            df_shelf = pd.DataFrame()
            df_type = pd.DataFrame()
            df_unknown = df_detail.copy()
            type_map = {k: 0 for k in SHELF_ORDER}
            type_map["未知"] = len(df_unknown)
        else:
            df_detail = df.copy()
            df_detail["儲位類型"] = df_detail["棚別"].apply(classify_from_shelf_bucket)

            df_shelf = (
                df_detail.groupby(["棚別"], dropna=False)
                .size()
                .reset_index(name="筆數")
                .sort_values(["筆數", "棚別"], ascending=[False, True])
            )

            df_type = (
                df_detail.groupby(["儲位類型"], dropna=False)
                .size()
                .reset_index(name="筆數")
            )

            # 固定排序
            df_type["__ord"] = df_type["儲位類型"].apply(
                lambda x: SHELF_ORDER.index(x) if x in SHELF_ORDER else 999
            )
            df_type = df_type.sort_values(["__ord", "儲位類型"]).drop(columns="__ord")

            type_map = {k: 0 for k in SHELF_ORDER}
            for _, r in df_type.iterrows():
                type_map[str(r["儲位類型"])] = int(r["筆數"])

            df_unknown = df_detail[df_detail["儲位類型"] == "未知"].copy()

            # ✅ 兩欄換列（輕型/落地｜重型/高空）
            r1c1, r1c2 = st.columns(2, gap="large")
            with r1c1:
                st.markdown("### 輕型料架")
                st.markdown(f"**{type_map.get('輕型料架', 0):,} 筆**")
            with r1c2:
                st.markdown("### 落地儲")
                st.markdown(f"**{type_map.get('落地儲', 0):,} 筆**")

            _spacer(6)

            r2c1, r2c2 = st.columns(2, gap="large")
            with r2c1:
                st.markdown("### 重型低空")
                st.markdown(f"**{type_map.get('重型低空', 0):,} 筆**")
            with r2c2:
                st.markdown("### 高空儲")
                st.markdown(f"**{type_map.get('高空儲', 0):,} 筆**")

            _spacer(6)

            # 未知（單獨列）
            st.markdown("### 未知")
            st.markdown(f"**{type_map.get('未知', 0):,} 筆**")

        # 匯出按鈕（在右欄底部）
        base = os.path.splitext(uploaded.name)[0]
        df_util_export = (
            df_util
            if isinstance(df_util, pd.DataFrame) and (not df_util.empty)
            else pd.DataFrame(
                [
                    {
                        "儲區": "（缺少區(溫層)欄位）",
                        "有效貨位": 0,
                        "已使用貨位": 0,
                        "未使用貨位": 0,
                        "使用率(%)": 0.0,
                    }
                ]
            )
        )

        out_name, out_bytes = build_output_excel_bytes(
            base_name=base,
            df_util=df_util_export,
            df_detail=df_detail,
            df_shelf=df_shelf if isinstance(df_shelf, pd.DataFrame) else pd.DataFrame(),
            df_type=df_type if isinstance(df_type, pd.DataFrame) else pd.DataFrame(),
            df_unknown=df_unknown if isinstance(df_unknown, pd.DataFrame) else pd.DataFrame(),
        )

        _spacer(10)
        st.download_button(
            "⬇️ 匯出（棚別分類統計 Excel）",
            data=out_bytes,
            file_name=out_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        if HAS_COMMON_UI:
            card_close()

    # =========================
    # ✅ 下方：全寬（Top50 一定要全寬）
    # =========================
    if "棚別" in df.columns and isinstance(df_shelf, pd.DataFrame) and (not df_shelf.empty):
        _spacer(10)
        if HAS_COMMON_UI:
            card_open("📋 棚別統計（Top 50）")
        st.dataframe(df_shelf.head(50), use_container_width=True, hide_index=True)
        if HAS_COMMON_UI:
            card_close()

    # =========================
    # ✅ 下方：未知明細（全寬）
    # =========================
    if "棚別" in df.columns and isinstance(df_unknown, pd.DataFrame):
        unknown_cnt = int(type_map.get("未知", 0)) if isinstance(type_map, dict) else 0
        _spacer(8)
        with st.expander(f"📌 未知明細（{unknown_cnt:,} 筆）", expanded=False):
            if unknown_cnt == 0:
                st.success("未知：0 筆")
            else:
                st.dataframe(df_unknown, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
