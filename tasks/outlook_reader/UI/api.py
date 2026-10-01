import sys
import json
import os
import argparse

def get_excel_row_count():
    excel_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "OriginalMail.xlsx")
    if not os.path.exists(excel_file):
        return ["尚未生成 Excel 数据文件。"]
    try:
        import openpyxl
        wb = openpyxl.load_workbook(excel_file, read_only=True)
        ws = wb.active
        count = ws.max_row - 1
        if count < 0: count = 0
        return [f"本地 Excel 现已记录了 {count} 封邮件。"]
    except Exception as e:
        return [f"读取 Excel 失败: {e}"]

def get_outlook_accounts():
    """动态获取本地 Outlook 账户列表"""
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        accounts = []
        for account in namespace.Accounts:
            accounts.append(account.DisplayName)
        
        if not accounts:
            return ["没有检测到邮箱账户，请确认您使用的是经典版 Outlook 并已登录。"]
        return accounts
    except Exception as e:
        return [f"获取失败 (请检查 Outlook 是否卡住或使用了不支持COM的新版): {e}"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--get-options", type=str, help="动态获取某参数的可选项")
    args, unknown = parser.parse_known_args()
    
    if args.get_options:
        if args.get_options == "target_account":
            print(json.dumps(get_outlook_accounts()))
        elif args.get_options == "excel_row_count":
            print(json.dumps(get_excel_row_count()))
        else:
            print("[]")
        sys.exit(0)
