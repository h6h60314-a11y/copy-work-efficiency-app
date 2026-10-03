# -*- coding: utf-8 -*-
"""
35_報工稼動 | 揀貨成箱

計算規則
1. 僅「成箱箱號」有值的資料視為成箱作業。
2. Line = 不重複的「儲位 + 商品」。同一儲位 2 個不同商品 = 2 Line。
3. 同一 Line 內，只要任一筆「原始配庫存量 != 數量」，該 Line 即為未完成。
4. 完成 Line = 成箱 Line - 未完成 Line。
5. 應作業 PCS：以「原始配庫存量」套用既有成箱 PCS 換算邏輯。
6. 實際作業 PCS：以「數量」套用既有成箱 PCS 換算邏輯。
7. 支援一次選擇多個檔案，並提供各檔與合併彙總。
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

try:
    from common_ui import inject_logistics_theme, set_page, card_open, card_close
except Exception:
    # 讓此頁在沒有 common_ui 時仍可單獨執行
    def inject_logistics_theme():
        return None

    def set_page(title: str, icon: str = "", subtitle: str = ""):
        st.title(f"{icon} {title}".strip())
        if subtitle:
            st.caption(subtitle)

    def card_open(_title: str):
        st.markdown(f"### {_title}")

    def card_close():
        return None


# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="報工稼動 | 揀貨成箱",
    page_icon="📦",
    layout="wide",
)
inject_logistics_theme()


# --------------------------------------------------
# 基本工具
# --------------------------------------------------
def _fmt_qty(x) -> str:
    try:
        v = float(x)
    except Exception:
        return str(x)
    s = f"{v:,.2f}"
    return s[:-3] if s.endswith(".00") else s


def _fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return str(x)


def _clean_text_series(s: pd.Series) -> pd.Series:
    out = s.fillna("").astype(str).str.strip()
    return out.replace({"nan": "", "None": "", "NULL": "", "NaN": "", "<NA>": ""})


def _resolve_col(df: pd.DataFrame, want: str) -> Optional[str]:
    """欄名容錯：忽略欄名前後空白。"""
    if want in df.columns:
        return want
    w = str(want).strip()
    for c in df.columns:
        if str(c).strip() == w:
            return c
    return None


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


def _excel_engines_for_ext(ext: str) -> list[str]:
    ext = ext.lower()
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return ["openpyxl"]
    if ext == ".xls":
        return ["xlrd", "openpyxl"]
    if ext == ".xlsb":
        return ["pyxlsb"]
    return []


def _load_dataframe(uploaded_file, key_prefix: str = "") -> tuple[pd.DataFrame, str]:
    """讀取單一上傳檔案；多工作表時可選擇工作表。"""
    name = uploaded_file.name
    ext = Path(name).suffix.lower()
    b = uploaded_file.getvalue()

    if ext == ".csv":
        return _read_csv_best_effort(b), "CSV"
    if ext in (".html", ".htm"):
        return _read_html_best_effort(b), "HTML"

    engines = _excel_engines_for_ext(ext)
    if not engines:
        raise ValueError("不支援的檔案格式，請使用 Excel / CSV / HTML")

    last_err = None
    for eng in engines:
        try:
            xf = pd.ExcelFile(io.BytesIO(b), engine=eng)
            sheet_names = xf.sheet_names
            sheet = sheet_names[0] if sheet_names else 0

            if len(sheet_names) > 1:
                sheet = st.selectbox(
                    f"選擇工作表：{name}",
                    sheet_names,
                    index=0,
                    key=f"{key_prefix}__sheet__{name}__{eng}",
                )

            df = pd.read_excel(io.BytesIO(b), engine=eng, sheet_name=sheet)
            return df, f"Excel({ext}, engine={eng}, sheet={sheet})"
        except Exception as e:
            last_err = e

    # 某些副檔名為 xls 的來源實際內容可能是 HTML
    if ext == ".xls":
        try:
            return _read_html_best_effort(b), "HTML(偽 xls)"
        except Exception:
            pass

    raise ValueError(f"Excel 讀取失敗：{last_err}")


# --------------------------------------------------
# 成箱 PCS 邏輯
# --------------------------------------------------
def _box_pcs_value(qty: pd.Series, ship_in: pd.Series) -> pd.Series:
    """
    沿用既有成箱 PCS 邏輯：
    - 出貨單位數量 = 作業量 / 出貨入數
    - = 1              → 計作業量
    - != 1 且為整數    → 計出貨單位數量
    - != 1 且為小數    → 計作業量

    qty 可分別傳入：
    - 原始配庫存量 → 應作業 PCS
    - 數量         → 實際作業 PCS
    """
    q = pd.to_numeric(qty, errors="coerce").fillna(0.0)
    si = pd.to_numeric(ship_in, errors="coerce")

    units = q / si
    valid = si.notna() & (si != 0) & units.notna()

    # 浮點容錯
    eq1 = valid & ((units - 1).abs() < 1e-9)
    is_integer = valid & (~eq1) & ((units - units.round()).abs() < 1e-9)
    is_decimal = valid & (~eq1) & (~is_integer)

    result = pd.Series(0.0, index=q.index)
    result.loc[eq1] = q.loc[eq1]
    result.loc[is_integer] = units.loc[is_integer]
    result.loc[is_decimal] = q.loc[is_decimal]

    # 出貨入數缺失/0：無法換算時，以原作業量保留，不讓 PCS 遺失
    invalid = ~valid
    result.loc[invalid] = q.loc[invalid]
    return result


# --------------------------------------------------
# 核心計算
# --------------------------------------------------
def _prepare_box_rows(df: pd.DataFrame, source_name: str = "") -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]

    required_names = [
        "成箱箱號",
        "儲位",
        "商品",
        "原始配庫存量",
        "數量",
        "出貨入數",
    ]

    col_map = {name: _resolve_col(out, name) for name in required_names}
    missing = [name for name, col in col_map.items() if col is None]
    if missing:
        raise KeyError(f"缺少必要欄位：{missing}")

    # 轉成標準欄名，避免來源欄名前後空白
    rename_map = {col: name for name, col in col_map.items() if col != name}
    if rename_map:
        out = out.rename(columns=rename_map)

    # 僅成箱箱號有值的資料
    box_no = _clean_text_series(out["成箱箱號"])
    out = out.loc[box_no.ne("")].copy()

    if out.empty:
        # 保留計算欄位，方便後續 concat
        out["來源檔名"] = source_name
        out["LineKey"] = ""
        out["Line完成"] = False
        out["應作業PCS計入值"] = 0.0
        out["實際作業PCS計入值"] = 0.0
        return out

    # 文字欄清理
    out["儲位"] = _clean_text_series(out["儲位"])
    out["商品"] = _clean_text_series(out["商品"])

    # 數值欄
    for c in ("原始配庫存量", "數量", "出貨入數"):
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # Line key：同儲位不同商品分開計 Line
    out["LineKey"] = out["儲位"] + "｜" + out["商品"]

    # 每筆完成判斷：原始配庫存量 == 數量
    expected_raw = out["原始配庫存量"].fillna(0.0)
    actual_raw = out["數量"].fillna(0.0)
    out["筆完成"] = (expected_raw - actual_raw).abs() < 1e-9

    # PCS 計入值
    out["應作業PCS計入值"] = _box_pcs_value(out["原始配庫存量"], out["出貨入數"])
    out["實際作業PCS計入值"] = _box_pcs_value(out["數量"], out["出貨入數"])

    # 同一 Line 任一筆不完成，整條 Line 就不完成
    line_complete_map = out.groupby("LineKey", dropna=False)["筆完成"].all()
    out["Line完成"] = out["LineKey"].map(line_complete_map).fillna(False)
    out["來源檔名"] = source_name

    return out


def _line_summary(box_df: pd.DataFrame) -> pd.DataFrame:
    """產出 Line 層級明細。"""
    cols = [
        "來源檔名",
        "儲位",
        "商品",
        "LineKey",
        "Line完成",
        "應作業PCS",
        "實際作業PCS",
        "PCS差異",
        "成箱筆數",
        "成箱箱數",
    ]
    if box_df.empty:
        return pd.DataFrame(columns=cols)

    group_cols = ["來源檔名", "儲位", "商品", "LineKey"]
    line = (
        box_df.groupby(group_cols, dropna=False)
        .agg(
            Line完成=("筆完成", "all"),
            應作業PCS=("應作業PCS計入值", "sum"),
            實際作業PCS=("實際作業PCS計入值", "sum"),
            成箱筆數=("LineKey", "size"),
            成箱箱數=("成箱箱號", "nunique"),
        )
        .reset_index()
    )
    line["PCS差異"] = line["應作業PCS"] - line["實際作業PCS"]
    return line[cols]


def _metrics_from_box_rows(box_df: pd.DataFrame) -> dict:
    if box_df.empty:
        return {
            "成箱Line": 0,
            "完成Line": 0,
            "未完成Line": 0,
            "Line完成率": 0.0,
            "應作業PCS": 0.0,
            "實際作業PCS": 0.0,
            "PCS完成率": 0.0,
            "成箱資料筆數": 0,
            "成箱箱數": 0,
        }

    line_status = box_df.groupby("LineKey", dropna=False)["筆完成"].all()
    total_line = int(line_status.shape[0])
    completed_line = int(line_status.sum())
    unfinished_line = total_line - completed_line

    expected_pcs = float(box_df["應作業PCS計入值"].sum())
    actual_pcs = float(box_df["實際作業PCS計入值"].sum())

    return {
        "成箱Line": total_line,
        "完成Line": completed_line,
        "未完成Line": unfinished_line,
        "Line完成率": (completed_line / total_line) if total_line else 0.0,
        "應作業PCS": expected_pcs,
        "實際作業PCS": actual_pcs,
        "PCS完成率": (actual_pcs / expected_pcs) if expected_pcs else 0.0,
        "成箱資料筆數": int(len(box_df)),
        "成箱箱數": int(box_df["成箱箱號"].nunique()),
    }


def _combined_metrics(all_box_df: pd.DataFrame) -> dict:
    """
    多檔合併後，以「儲位 + 商品」重新去重計 Line。
    同一 Line 若跨檔出現，仍只算 1 Line；任一檔有不完成則整體未完成。
    """
    return _metrics_from_box_rows(all_box_df)


def _download_xlsx(
    summary_df: pd.DataFrame,
    combined_line_df: pd.DataFrame,
    combined_detail_df: pd.DataFrame,
    per_file_line_dfs: list[tuple[str, pd.DataFrame]],
) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="彙總")
        combined_line_df.to_excel(writer, index=False, sheet_name="Line明細_合併")
        combined_detail_df.to_excel(writer, index=False, sheet_name="原始明細_合併")

        used_names = set(writer.book.sheetnames)
        for name, line_df in per_file_line_dfs:
            base = (Path(name).stem + "_Line")[:31]
            safe = base
            n = 1
            while safe in used_names:
                suffix = f"_{n}"
                safe = (base[: 31 - len(suffix)] + suffix)[:31]
                n += 1
            used_names.add(safe)
            line_df.to_excel(writer, index=False, sheet_name=safe)

    return bio.getvalue()


# --------------------------------------------------
# UI
# --------------------------------------------------
set_page(
    "報工稼動 | 揀貨成箱",
    icon="📦",
    subtitle=(
        "支援多檔上傳｜成箱箱號有值才計入｜Line=儲位+商品｜"
        "原始配庫存量≠數量則該 Line 未完成｜計算應作業 PCS / 實際作業 PCS"
    ),
)

if "uploader_key_35_box" not in st.session_state:
    st.session_state["uploader_key_35_box"] = 0

card_open("📌 上傳揀貨成箱明細（可一次多檔）")
u1, u2 = st.columns([1, 0.08], gap="small")
with u1:
    uploaded_files = st.file_uploader(
        "請選擇一個或多個檔案",
        type=["xlsx", "xls", "xlsb", "xlsm", "csv", "html", "htm"],
        accept_multiple_files=True,
        key=f"uploader_35_box_{st.session_state['uploader_key_35_box']}",
    )
with u2:
    st.markdown(" ")
    if st.button("🧹", help="清除已上傳檔案", use_container_width=True):
        st.session_state["uploader_key_35_box"] += 1
        st.rerun()
card_close()

if not uploaded_files:
    st.info(
        "請上傳檔案。必要欄位：成箱箱號、儲位、商品、原始配庫存量、數量、出貨入數。"
    )
    st.stop()

items = []
errors = []

for i, uf in enumerate(uploaded_files, start=1):
    try:
        raw_df, read_note = _load_dataframe(uf, key_prefix=f"box_f{i}")
        box_df = _prepare_box_rows(raw_df, source_name=uf.name)
        metrics = _metrics_from_box_rows(box_df)
        line_df = _line_summary(box_df)

        items.append(
            {
                "name": uf.name,
                "read_note": read_note,
                "raw_rows": len(raw_df),
                "box_df": box_df,
                "line_df": line_df,
                "metrics": metrics,
            }
        )
    except Exception as e:
        errors.append((uf.name, str(e)))

if errors:
    with st.expander("⚠️ 部分檔案讀取 / 計算失敗", expanded=True):
        for fn, msg in errors:
            st.error(f"{fn}：{msg}")

if not items:
    st.error("沒有任何檔案成功計算，請確認必要欄位是否完整。")
    st.stop()

# 合併所有成功檔案
combined_box_df = pd.concat([it["box_df"] for it in items], ignore_index=True)

# 合併總覽 Line 必須跨檔重新以 儲位+商品 判斷
combined_line_base = combined_box_df.copy()
combined_line_base["來源檔名"] = "全部檔案"
combined_line_df = _line_summary(combined_line_base)
combined_metrics = _combined_metrics(combined_box_df)

# --------------------------------------------------
# 總覽 KPI
# --------------------------------------------------
st.markdown("### 📊 合併結果")

c1, c2, c3, c4 = st.columns(4)
c1.metric("成箱 Line", _fmt_int(combined_metrics["成箱Line"]))
c2.metric("完成 Line", _fmt_int(combined_metrics["完成Line"]))
c3.metric("未完成 Line", _fmt_int(combined_metrics["未完成Line"]))
c4.metric("Line 完成率", f"{combined_metrics['Line完成率']:.1%}")

p1, p2, p3, p4 = st.columns(4)
p1.metric("應作業 PCS", _fmt_qty(combined_metrics["應作業PCS"]))
p2.metric("實際作業 PCS", _fmt_qty(combined_metrics["實際作業PCS"]))
p3.metric(
    "PCS 差異",
    _fmt_qty(combined_metrics["應作業PCS"] - combined_metrics["實際作業PCS"]),
)
p4.metric("PCS 完成率", f"{combined_metrics['PCS完成率']:.1%}")

st.caption(
    f"成箱資料筆數：{combined_metrics['成箱資料筆數']:,}｜"
    f"不重複成箱箱號：{combined_metrics['成箱箱數']:,}"
)

# --------------------------------------------------
# 各檔彙總
# --------------------------------------------------
summary_rows = []
for it in items:
    m = it["metrics"]
    summary_rows.append(
        {
            "檔名": it["name"],
            "讀取方式": it["read_note"],
            "原始筆數": it["raw_rows"],
            "成箱資料筆數": m["成箱資料筆數"],
            "成箱箱數": m["成箱箱數"],
            "成箱Line": m["成箱Line"],
            "完成Line": m["完成Line"],
            "未完成Line": m["未完成Line"],
            "Line完成率": m["Line完成率"],
            "應作業PCS": m["應作業PCS"],
            "實際作業PCS": m["實際作業PCS"],
            "PCS差異": m["應作業PCS"] - m["實際作業PCS"],
            "PCS完成率": m["PCS完成率"],
        }
    )
summary_df = pd.DataFrame(summary_rows)

card_open("📋 各檔彙總")
st.dataframe(
    summary_df,
    use_container_width=True,
    height=min(430, 90 + len(summary_df) * 38),
    column_config={
        "Line完成率": st.column_config.NumberColumn(format="%.1f%%"),
        "PCS完成率": st.column_config.NumberColumn(format="%.1f%%"),
    },
)
card_close()

# --------------------------------------------------
# Line 明細
# --------------------------------------------------
card_open("🧾 Line 明細（合併）")
show_line = combined_line_df.copy()
show_line["完成狀態"] = show_line["Line完成"].map({True: "完成", False: "未完成"})
line_display_cols = [
    "儲位",
    "商品",
    "完成狀態",
    "應作業PCS",
    "實際作業PCS",
    "PCS差異",
    "成箱筆數",
    "成箱箱數",
]
st.dataframe(show_line[line_display_cols], use_container_width=True, height=430)
card_close()

with st.expander("🔎 各檔 Line 明細", expanded=False):
    tabs = st.tabs([f"{i+1}. {it['name']}" for i, it in enumerate(items)])
    for tab, it in zip(tabs, items):
        with tab:
            dfp = it["line_df"].copy()
            dfp["完成狀態"] = dfp["Line完成"].map({True: "完成", False: "未完成"})
            st.caption(
                f"讀取方式：{it['read_note']}｜成箱 Line：{it['metrics']['成箱Line']:,}｜"
                f"完成：{it['metrics']['完成Line']:,}｜未完成：{it['metrics']['未完成Line']:,}"
            )
            st.dataframe(
                dfp[[
                    "儲位",
                    "商品",
                    "完成狀態",
                    "應作業PCS",
                    "實際作業PCS",
                    "PCS差異",
                    "成箱筆數",
                    "成箱箱數",
                ]],
                use_container_width=True,
                height=380,
            )

# --------------------------------------------------
# 原始成箱明細預覽
# --------------------------------------------------
preferred = [
    "來源檔名",
    "成箱箱號",
    "儲位",
    "商品",
    "原始配庫存量",
    "數量",
    "出貨入數",
    "應作業PCS計入值",
    "實際作業PCS計入值",
    "筆完成",
    "Line完成",
    "LineKey",
]
ordered_cols = [c for c in preferred if c in combined_box_df.columns] + [
    c for c in combined_box_df.columns if c not in preferred
]

with st.expander("📄 原始成箱明細預覽", expanded=False):
    st.dataframe(
        combined_box_df[ordered_cols].head(1000),
        use_container_width=True,
        height=430,
    )

# --------------------------------------------------
# 下載
# --------------------------------------------------
xlsx_bytes = _download_xlsx(
    summary_df=summary_df,
    combined_line_df=combined_line_df,
    combined_detail_df=combined_box_df[ordered_cols],
    per_file_line_dfs=[(it["name"], it["line_df"]) for it in items],
)

st.download_button(
    label="⬇️ 下載計算結果 Excel",
    data=xlsx_bytes,
    file_name="揀貨成箱_多檔計算結果.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
