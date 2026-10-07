#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
38_Handover_實際完成line.py

功能：
1. 一次選擇多個 Excel 檔案（.xlsx / .xls）
2. 每個檔案讀取第一個工作表
3. 將所有 Excel 直接上下合併
4. 不去重、不排除任何有效資料列
5. 計算合併後總行數（不含 Excel 欄位標題列）
6. 顯示各檔案行數與合併總行數
7. 可將合併結果另存成 Excel

目前 14919.xlsx + 14920.xlsx：
14919 = 6,641 行
14920 = 4,081 行
合計 = 10,722 行
"""

import os
import sys
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox


def read_excel_first_sheet(file_path):
    """讀取 Excel 第一個工作表，並移除真正的整列空白資料。"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext not in (".xlsx", ".xls"):
        raise ValueError(f"不支援的檔案格式：{ext}")

    # sheet_name=0：只讀第一個工作表
    df = pd.read_excel(file_path, sheet_name=0)

    # 欄名去除前後空白，避免不同檔案欄名只差空格
    df.columns = [str(col).strip() for col in df.columns]

    # 僅排除整列完全空白的資料；其他有值的列全部保留
    df = df.dropna(how="all").reset_index(drop=True)

    return df


def main():
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_paths = filedialog.askopenfilenames(
        title="請選擇要合併的 Excel 檔案",
        filetypes=[
            ("Excel 檔案", "*.xlsx *.xls"),
            ("Excel 2007+", "*.xlsx"),
            ("Excel 97-2003", "*.xls"),
            ("所有檔案", "*.*"),
        ],
    )

    if not file_paths:
        messagebox.showinfo("未選擇檔案", "沒有選擇任何 Excel 檔案，程式結束。")
        return

    dataframes = []
    detail_lines = []
    base_columns = None

    try:
        for file_path in file_paths:
            df = read_excel_first_sheet(file_path)

            # 第一份檔案作為欄位基準
            if base_columns is None:
                base_columns = list(df.columns)
            else:
                # 欄位集合不同時直接提醒，避免錯誤合併
                if set(df.columns) != set(base_columns):
                    missing = [c for c in base_columns if c not in df.columns]
                    extra = [c for c in df.columns if c not in base_columns]
                    raise ValueError(
                        f"檔案欄位不一致：{os.path.basename(file_path)}\n"
                        f"缺少欄位：{missing or '無'}\n"
                        f"多出欄位：{extra or '無'}"
                    )

                # 若欄位順序不同，依第一份檔案欄位順序重新排列
                df = df[base_columns]

            row_count = len(df)
            detail_lines.append(f"{os.path.basename(file_path)}：{row_count:,} 行")
            dataframes.append(df)

        # 直接上下合併，不做去重
        merged_df = pd.concat(dataframes, ignore_index=True)
        total_rows = len(merged_df)

        result_text = (
            "各檔案行數：\n"
            + "\n".join(detail_lines)
            + f"\n\n合併後總行數：{total_rows:,} 行"
            + "\n\n計算方式：不去重、不排除有值資料列，僅不計 Excel 標題列與整列完全空白資料。"
        )

        print("=" * 60)
        print(result_text)
        print("=" * 60)

        # 詢問是否儲存合併後 Excel
        save_choice = messagebox.askyesno(
            "合併完成",
            result_text + "\n\n是否要儲存合併後的 Excel？",
        )

        if save_choice:
            default_dir = os.path.dirname(file_paths[0])
            save_path = filedialog.asksaveasfilename(
                title="儲存合併後 Excel",
                initialdir=default_dir,
                initialfile="Handover_實際完成line_合併.xlsx",
                defaultextension=".xlsx",
                filetypes=[("Excel 檔案", "*.xlsx")],
            )

            if save_path:
                merged_df.to_excel(save_path, index=False)
                messagebox.showinfo(
                    "完成",
                    f"合併檔已儲存：\n{save_path}\n\n總行數：{total_rows:,} 行",
                )
            else:
                messagebox.showinfo("完成", f"未另存檔案。\n合併總行數：{total_rows:,} 行")

    except Exception as e:
        messagebox.showerror("執行失敗", f"處理檔案時發生錯誤：\n\n{e}")
        raise
    finally:
        root.destroy()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"執行失敗：{exc}", file=sys.stderr)
        sys.exit(1)
