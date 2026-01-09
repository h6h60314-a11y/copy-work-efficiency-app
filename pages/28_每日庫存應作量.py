# -*- coding: utf-8 -*-
# pages/28_每日庫存應作量.py

import io
import inspect
import pandas as pd
import streamlit as st

# ---- 套用平台風格（有就用，沒有就退回原生）----
try:
    from common_ui import (
        inject_logistics_theme,
        set_page,
        card_open,
        card_close,
        download_excel_card,  # 你平台常用的一行下載按鈕（可用就用）
    )
    HAS_COMMON_UI = True
except Exception:
    HAS_COMMON_UI = False


# =============================
# helpers
# =============================
def format_code(x, length: int) -> str:
    """處理空值、去除小數點、補足前導 0 (如 255 -> 000255)"""
    if pd.isna(x) or str(x).strip() == "":
        return ""
    s = str(x).strip()
    s = s.split(".")[0].strip()  # 去除 Excel 常見 .0
    return s.zfill(length)


def read_order_file(uploaded) -> pd.DataFrame:
    """讀取訂單檔（csv / xlsx / xls / xlsm）"""
    name = (uploaded.name or "").lower()
    raw = uploaded.getvalue()

    if name.endswith(".csv"):
        try:
            return pd.read_csv(io.BytesIO(raw), encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(io.BytesIO(raw), encoding="big5", errors="replace")
    return pd.read_excel(io.BytesIO(raw))


def read_master_file(uploaded) -> tuple[pd.DataFrame, pd.DataFrame]:
    """讀取商品主檔（需含：商品主檔 / 大類加權）"""
    raw = uploaded.getvalue()
    try:
        df_master = pd.read_excel(io.BytesIO(raw), sheet_name="商品主檔")
        df_weight = pd.read_excel(io.BytesIO(raw), sheet_name="大類加權")
        return df_master, df_weight
    except Exception as e:
        raise ValueError("找不到『商品主檔』或『大類加權』分頁，請檢查 Excel 工作表名稱。") from e


def build_result(
    df_order: pd.DataFrame, df_master: pd.DataFrame, df_weight: pd.DataFrame
) -> tuple[pd.DataFrame, list[str]]:
    """主流程：清理 → 補碼 → join → 計算"""
    msgs: list[str] = []

    # --- 排除特殊儲位 ---
    exclude_list = ["CGS", "JCPL", "QC99", "PD99", "GX010", "GREAT0001X"]
    if "儲位" in df_order.columns:
        before = len(df_order)
        df_order = df_order.copy()
        df_order["儲位"] = df_order["儲位"].astype(str).str.strip()
        pattern = "|".join(exclude_list)
        df_order = df_order[~df_order["儲位"].str.contains(pattern, case=False, na=False)]
        after = len(df_order)
        msgs.append(f"已排除特殊儲位：{before - after:,} 筆（剩餘 {after:,} 筆）")
    else:
        msgs.append("訂單檔找不到欄位『儲位』：略過排除特殊儲位")

    # --- 成箱箱號清空 ---
    if "成箱箱號" in df_order.columns:
        df_order = df_order.copy()
        df_order["成箱箱號"] = " "
        msgs.append("已將『成箱箱號』全數改為空白(空格)")

    # --- 必要欄位檢查 ---
    if "商品" not in df_order.columns:
        raise ValueError("訂單檔缺少欄位『商品』")
    if "商品代號" not in df_master.columns:
        raise ValueError("商品主檔缺少欄位『商品代號』")
    if "大類" not in df_master.columns:
        raise ValueError("商品主檔缺少欄位『大類』")
    if "PA" not in df_weight.columns:
        raise ValueError("大類加權分頁缺少欄位『PA』")
    if "PARM_VALUE2" not in df_weight.columns:
        raise ValueError("大類加權分頁缺少欄位『PARM_VALUE2』")

    # --- 補碼 ---
    df_order = df_order.copy()
    df_master = df_master.copy()
    df_weight = df_weight.copy()

    df_order["商品"] = df_order["商品"].apply(lambda x: format_code(x, 6))
    df_master["商品代號"] = df_master["商品代號"].apply(lambda x: format_code(x, 6))

    df_master["大類"] = df_master["大類"].apply(lambda x: format_code(x, 2))
    df_weight["PA"] = df_weight["PA"].apply(lambda x: format_code(x, 2))

    # --- 二次比對 ---
    master_cols = ["商品代號", "大類"]
    if "類別" in df_master.columns:
        master_cols.append("類別")
    df_master_sub = df_master[master_cols].drop_duplicates(subset=["商品代號"])

    step1_df = pd.merge(df_order, df_master_sub, left_on="商品", right_on="商品代號", how="left")

    df_weight_sub = df_weight[["PA", "PARM_VALUE2"]].drop_duplicates(subset=["PA"])
    final_df = pd.merge(step1_df, df_weight_sub, left_on="大類", right_on="PA", how="left")

    final_df = final_df.rename(columns={"PARM_VALUE2": "大類加權值"})

    # --- 計算加權結果 ---
    qty_col = "計量單位數量"
    weight_col = "大類加權值"

    if qty_col in final_df.columns and weight_col in final_df.columns:
        final_df[qty_col] = pd.to_numeric(final_df[qty_col], errors="coerce").fillna(0)
        final_df[weight_col] = pd.to_numeric(final_df[weight_col], errors="coerce").fillna(0)
        final_df["加權計算結果"] = final_df[weight_col] * final_df[qty_col]
        msgs.append("已完成計算：加權計算結果 = 大類加權值 * 計量單位數量")
    else:
        msgs.append(f"⚠️ 找不到欄位『{qty_col}』或『{weight_col}』，無法計算加權計算結果")

    # --- 清理輔助欄位 ---
    final_df = final_df.drop(columns=["商品代號", "PA"], errors="ignore")
    return final_df, msgs


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def safe_download_card(label: str, data: bytes, filename: str, mime: str = "text/csv"):
    """
    ✅ 相容不同版本 common_ui.download_excel_card 的參數命名
    - 會先用 signature 偵測參數
    - 再做位置參數 fallback
    - 最後退回 st.download_button（永遠不會炸）
    """
    if HAS_COMMON_UI and "download_excel_card" in globals():
        fn = download_excel_card
        try:
            sig = inspect.signature(fn)
            params = set(sig.parameters.keys())

            kwargs = {}

            # 標題/文字參數：title / label / text (擇一)
            if "title" in params:
                kwargs["title"] = label
            elif "label" in params:
                kwargs["label"] = label
            elif "text" in params:
                kwargs["text"] = label

            # 資料參數：data / xlsx_bytes / bytes_data (擇一)
            if "data" in params:
                kwargs["data"] = data
            elif "xlsx_bytes" in params:
                kwargs["xlsx_bytes"] = data
            elif "bytes_data" in params:
                kwargs["bytes_data"] = data

            # 檔名參數：filename / file_name (擇一)
            if "filename" in params:
                kwargs["filename"] = filename
            elif "file_name" in params:
                kwargs["file_name"] = filename

            # mime 若支援就帶
            if "mime" in params:
                kwargs["mime"] = mime

            # 若 kwargs 太少（例如此版本只吃位置參數），會進 except 做 fallback
            if kwargs:
                return fn(**kwargs)

        except TypeError:
            pass
        except Exception:
            pass

        # 位置參數 fallback（嘗試幾種常見順序）
        for args in [
            (label, data, filename),
            (data, filename, label),
            (data, filename),
            (label, data),
        ]:
            try:
                return fn(*args)
            except Exception:
                continue

    # 最終保底：原生下載按鈕
    return st.download_button(
        label,
        data=data,
        file_name=filename,
        mime=mime,
        use_container_width=True,
    )


# =============================
# UI
# =============================
def main():
    st.set_page_config(page_title="每日庫存應作量", page_icon="📦", layout="wide")

    if HAS_COMMON_UI:
        inject_logistics_theme()
        set_page("📦 每日庫存應作量", "上傳訂單檔 + 商品主檔 → 自動加權計算 → 匯出 CSV")
    else:
        st.title("📦 每日庫存應作量")
        st.caption("上傳訂單檔 + 商品主檔 → 自動加權計算 → 匯出 CSV")

    if HAS_COMMON_UI:
        card_open("📥 1) 上傳檔案")

    st.markdown(
        """
- 訂單資料檔：支援 `.csv / .xlsx / .xls / .xlsm`
- 商品主檔：Excel，需包含工作表：`商品主檔`、`大類加權`
        """.strip()
    )

    c1, c2 = st.columns(2)
    with c1:
        order_file = st.file_uploader(
            "訂單資料檔（例如：0108.csv）",
            type=["csv", "xlsx", "xls", "xlsm"],
            key="order",
        )
    with c2:
        master_file = st.file_uploader(
            "商品主檔（含：商品主檔 / 大類加權）",
            type=["xlsx", "xls", "xlsm"],
            key="master",
        )

    if HAS_COMMON_UI:
        card_close()

    st.divider()

    run = st.button("✅ 開始處理", type="primary", disabled=not (order_file and master_file))
    if not run:
        return

    try:
        with st.spinner("讀取檔案中..."):
            df_order = read_order_file(order_file)
            df_master, df_weight = read_master_file(master_file)

        with st.spinner("處理中（排除 / 補碼 / Join / 計算）..."):
            final_df, msgs = build_result(df_order, df_master, df_weight)

        # 摘要 KPI
        total_rows = len(final_df)
        uniq_sku = final_df["商品"].nunique() if "商品" in final_df.columns else 0
        sum_weighted = float(final_df["加權計算結果"].sum()) if "加權計算結果" in final_df.columns else 0.0

        if HAS_COMMON_UI:
            card_open("📊 2) 結果摘要")
        k1, k2, k3 = st.columns(3)
        k1.metric("筆數", f"{total_rows:,}")
        k2.metric("商品數(不重複)", f"{uniq_sku:,}")
        k3.metric("加權計算結果總和", f"{sum_weighted:,.2f}")
        if HAS_COMMON_UI:
            card_close()

        if msgs:
            st.info(" \n".join([f"- {m}" for m in msgs]))

        # 預覽
        if HAS_COMMON_UI:
            card_open("🔎 3) 明細預覽")
        st.dataframe(final_df, use_container_width=True, height=520)
        if HAS_COMMON_UI:
            card_close()

        # 下載
        csv_bytes = to_csv_bytes(final_df)
        filename = "處理完成_加權計算結果.csv"
        safe_download_card("✅ 下載 CSV（加權計算結果）", csv_bytes, filename, mime="text/csv")

        st.success("完成 ✅")

    except Exception as e:
        st.error(f"執行中發生問題：{e}")


if __name__ == "__main__":
    main()
