# pages/12_越庫訂單分析.py
import io
import re
import pandas as pd
import streamlit as st

from common_ui import inject_logistics_theme, set_page, card_open, card_close

st.set_page_config(page_title="越庫訂單分析", page_icon="🔁", layout="wide")
inject_logistics_theme()


def _read_uploaded(uploaded) -> pd.DataFrame:
    """讀取上傳檔（xls/xlsx/csv/html）"""
    name = (uploaded.name or "").lower()

    if name.endswith((".xlsx", ".xlsm", ".xltx", ".xltm")):
        return pd.read_excel(uploaded, engine="openpyxl")
    if name.endswith(".xls"):
        # 需要 xlrd==2.0.1
        return pd.read_excel(uploaded, engine="xlrd")
    if name.endswith(".csv"):
        return pd.read_csv(uploaded, encoding="utf-8", sep=",")
    if name.endswith((".html", ".htm")):
        tables = pd.read_html(uploaded)
        if not tables:
            raise ValueError("HTML 內沒有可辨識的表格")
        return tables[0]

    raise ValueError("不支援的檔案格式，請上傳 xls/xlsx/csv/html")


def _fmt_num(x):
    try:
        return f"{float(x):,.0f}"
    except Exception:
        return str(x)


def _fmt_float(x):
    try:
        return f"{float(x):,.2f}"
    except Exception:
        return str(x)


def _to_excel_bytes(df: pd.DataFrame, sheet_name="結果"):
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    bio.seek(0)
    return bio.read()


def main():
    set_page("越庫訂單分析", icon="🔁", subtitle="雙檔比對｜排除特定結案人員｜越庫零散/成箱統計｜匯出結果")

    card_open("📌 上傳檔案")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        f1 = st.file_uploader(
            "導入-單據明細查看（Excel）",
            type=["xlsx", "xls", "xlsm", "csv", "html", "htm"],
            key="f1",
        )
    with c2:
        f2 = st.file_uploader(
            "製單-已結案單據查詢（Excel）",
            type=["xlsx", "xls", "xlsm", "csv", "html", "htm"],
            key="f2",
        )

    st.markdown("")

    # 可調參數（你原本固定 FT03~FT11）
    pattern = st.text_input("排除 CLOSE_USER（正則）", value=r"FT0[3-9]|FT1[0-1]")
    card_close()

    if not f1 or not f2:
        st.info("請先上傳兩個檔案。")
        return

    # 讀檔
    try:
        df1 = _read_uploaded(f1)
        df2 = _read_uploaded(f2)
    except Exception as e:
        st.error(f"讀取失敗：{e}")
        st.caption("若你上傳的是 .xls，請確認 requirements.txt 有加 xlrd==2.0.1")
        return

    # 去空白欄名
    df1.columns = df1.columns.astype(str).str.strip()
    df2.columns = df2.columns.astype(str).str.strip()

    # 欄位檢查
    need_1 = ["單號", "單據類型", "作業類型", "應作量", "實作量"]
    need_2 = ["SONO", "CLOSE_USER"]
    miss1 = [c for c in need_1 if c not in df1.columns]
    miss2 = [c for c in need_2 if c not in df2.columns]
    if miss1 or miss2:
        st.error(
            "欄位不足，無法計算：\n"
            f"- 明細檔缺：{miss1}\n"
            f"- 已結案檔缺：{miss2}"
        )
        return

    # 產出比對備註
    close_map = df2.set_index("SONO")["CLOSE_USER"]
    df1["比對備註"] = df1["單號"].map(close_map).fillna("無對應")

    # 剔除 CLOSE_USER 含 FT03~FT11
    try:
        mask_bad = df1["比對備註"].astype(str).str.contains(pattern, regex=True, na=False)
    except re.error:
        st.error("你輸入的正則表達式有誤，請修正後再試。")
        return
    df1 = df1[~mask_bad].copy()

    # B/C 清理（在計算不重複之前）
    df1["單號"] = df1["單號"].astype(str).str.replace("B", "", regex=False).str.replace("C", "", regex=False)

    # 越庫統計
    cond = df1["單據類型"].astype(str) == "越庫"
    df_cond = df1.loc[cond].copy()

    # 轉數字避免文字
    for col in ["應作量", "實作量"]:
        df1[col] = pd.to_numeric(df1[col], errors="coerce").fillna(0)

    total_scatter_expected = df1.loc[cond & (df1["作業類型"].astype(str) == "零散"), "應作量"].sum()
    total_box_expected = df1.loc[cond & (df1["作業類型"].astype(str) == "成箱"), "應作量"].sum()
    total_scatter_actual = df1.loc[cond & (df1["作業類型"].astype(str) == "零散"), "實作量"].sum()
    total_box_actual = df1.loc[cond & (df1["作業類型"].astype(str) == "成箱"), "實作量"].sum()
    unique_count = df1.loc[cond, "單號"].nunique()

    # 插入「比對備註」到第18欄（index=17）
    cols = list(df1.columns)
    if "比對備註" in cols:
        cols.remove("比對備註")
        insert_at = 17 if len(cols) >= 17 else len(cols)
        cols.insert(insert_at, "比對備註")
        df1 = df1[cols]

    # 顯示 KPI（直向）
    card_open("📊 越庫訂單統計（直向）")
    left, right = st.columns([1, 1], gap="large")

    with left:
        st.markdown("#### 應作量")
        st.metric("越庫｜零散（應作）", _fmt_float(total_scatter_expected))
        st.metric("越庫｜成箱（應作）", _fmt_float(total_box_expected))
        st.metric("訂單筆數（不重複單號）", _fmt_num(unique_count))

    with right:
        st.markdown("#### 實作量")
        st.metric("越庫｜零散（實作）", _fmt_float(total_scatter_actual))
        st.metric("越庫｜成箱（實作）", _fmt_float(total_box_actual))

    card_close()

    # 下載
    card_open("📦 匯出結果")
    out_name = st.text_input("匯出檔名（不含副檔名）", value="越庫訂單分析_結果")
    xbytes = _to_excel_bytes(df1, sheet_name="越庫訂單分析")
    st.download_button(
        "⬇️ 下載 Excel（.xlsx）",
        data=xbytes,
        file_name=f"{out_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    card_close()

    # 明細預覽
    with st.expander("🔎 檢視處理後明細（前 5000 筆）", expanded=True):
        st.dataframe(df1.head(5000), use_container_width=True)


if __name__ == "__main__":
    main()
