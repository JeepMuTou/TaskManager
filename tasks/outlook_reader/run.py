import json
import os
from datetime import datetime, timedelta
import traceback
import difflib

def get_sender_address(item):
    try:
        sender_name = getattr(item, 'SenderName', 'Unknown')
        sender_email = getattr(item, 'SenderEmailAddress', '')
        sender_type = getattr(item, 'SenderEmailType', '')
        
        if sender_type == "EX":
            try:
                sender_email = item.Sender.GetExchangeUser().PrimarySmtpAddress
            except:
                pass
                
        if sender_email:
            return f"{sender_name} <{sender_email}>"
        return sender_name
    except:
        return "Unknown"

def get_receivers_address(item):
    try:
        receivers = []
        for r in item.Recipients:
            name = r.Name
            addr = getattr(r, 'Address', '')
            if addr.lower().startswith('/o='):
                try:
                    addr = r.AddressEntry.GetExchangeUser().PrimarySmtpAddress
                except:
                    pass
            if addr:
                receivers.append(f"{name} <{addr}>")
            else:
                receivers.append(name)
        if receivers:
            return "; ".join(receivers)
        return getattr(item, 'To', 'Unknown')
    except:
        return getattr(item, 'To', 'Unknown')

def is_employee(email_str, exclude_list):
    if not exclude_list or not email_str:
        return False
    email_str_lower = email_str.lower()
    for ex in exclude_list:
        if ex.lower() in email_str_lower:
            return True
    return False

def clean_subject(subject):
    s = subject.lower()
    prefixes = ['re:', 'fw:', 'fwd:', '回复:', '答复:', '转发:']
    for p in prefixes:
        s = s.replace(p, '')
    return s.strip()

def process_folder(folder, cutoff_date, max_emails, sent_folder_id, account_smtp_address, account_name, current_count=0):
    """递归处理文件夹，返回提取的邮件列表 (不写入 Excel)"""
    emails = []
    try:
        items = folder.Items
        items.Sort("[ReceivedTime]", True)
        
        for item in items:
            if getattr(item, 'Class', 0) == 43: # MailItem
                received_time = item.ReceivedTime
                if hasattr(received_time, 'replace'):
                    dt = received_time.replace(tzinfo=None)
                else:
                    dt = datetime(received_time.year, received_time.month, received_time.day, 
                                  received_time.hour, received_time.minute, received_time.second)
                
                if dt < cutoff_date:
                    break
                    
                sender_str = get_sender_address(item)
                receiver_str = get_receivers_address(item)
                subject = getattr(item, 'Subject', 'No Subject')
                mail_time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                log_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                is_sent = False
                if getattr(folder, 'EntryID', '') == sent_folder_id:
                    is_sent = True
                elif account_smtp_address and account_smtp_address in sender_str:
                    is_sent = True
                elif account_name in sender_str:
                    is_sent = True
                    
                direction = "发送" if is_sent else "接收"
                folder_name = getattr(folder, 'Name', 'Unknown')
                
                email_dict = {
                    "log_time": log_time_str,
                    "mail_time": mail_time_str,
                    "direction": direction,
                    "sender": sender_str,
                    "receiver": receiver_str,
                    "subject": subject,
                    "folder": folder_name,
                    "reply_time": ""
                }
                emails.append(email_dict)
                
                current_count += 1
                if current_count >= max_emails:
                    return emails, current_count
    except Exception as e:
        pass
        
    try:
        for subfolder in folder.Folders:
            if current_count >= max_emails:
                break
            sub_emails, current_count = process_folder(subfolder, cutoff_date, max_emails, sent_folder_id, account_smtp_address, account_name, current_count)
            emails.extend(sub_emails)
    except:
        pass
        
    return emails, current_count

def run_task():
    os.makedirs("data", exist_ok=True)
    os.makedirs("Log", exist_ok=True)
    config_file = "config.json"
    
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            full_config = json.load(f)
            params = full_config.get("params", {})
    else:
        print("本地不存在 config.json。无法执行。")
        return
            
    target_accounts_raw = params.get('target_account', "")
    if isinstance(target_accounts_raw, str):
        target_accounts = [acc.strip() for acc in target_accounts_raw.replace(';', ',').split(',') if acc.strip()]
    elif isinstance(target_accounts_raw, list):
        target_accounts = target_accounts_raw
    else:
        target_accounts = [str(target_accounts_raw)]
        
    exclude_emails_raw = params.get('exclude_emails', [])
    if isinstance(exclude_emails_raw, str):
        exclude_emails = [acc.strip() for acc in exclude_emails_raw.replace(';', ',').split(',') if acc.strip()]
    elif isinstance(exclude_emails_raw, list):
        exclude_emails = exclude_emails_raw
    else:
        exclude_emails = [str(exclude_emails_raw)]
        
    past_hours = params.get('past_hours', 24)
    max_emails = params.get('max_emails', 500)
    retention_hours = params.get('retention_hours', 720)
    
    excel_file = "data/OriginalMail.xlsx"
    log_file = "Log/emails.log"
    widths_file = "data/widths.json"
    
    try:
        import openpyxl
    except ImportError:
        print("未安装 openpyxl 库。请执行 pip install openpyxl")
        return
        
    wb = None
    if not os.path.exists(excel_file):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Mails"
        ws.append(["录入时间", "邮件时间", "收发类型", "发件人", "收件人", "邮件标题", "所属文件夹", "回复时间"])
        
        widths = {'A': 21.5, 'C': 8.875, 'D': 48.25, 'F': 129.75, 'G': 14.0, 'H': 20.0}
        if os.path.exists(widths_file):
            try:
                with open(widths_file, "r", encoding="utf-8") as wf:
                    widths.update(json.load(wf))
            except:
                pass
        for col, w in widths.items():
            ws.column_dimensions[col].width = w
        wb.save(excel_file)
        
    wb = openpyxl.load_workbook(excel_file)
    ws = wb.active
    
    # 确保最后一列名称是 "回复时间"
    if ws.cell(row=1, column=8).value != "回复时间":
        ws.cell(row=1, column=8).value = "回复时间"
    
    current_widths = {}
    for col_letter, dim in ws.column_dimensions.items():
        if dim.width:
            current_widths[col_letter] = dim.width
    if current_widths:
        try:
            with open(widths_file, "w", encoding="utf-8") as wf:
                json.dump(current_widths, wf)
        except:
            pass

    # 读取全部现有邮件
    all_emails = []
    seen_keys = set()
    
    for row in ws.iter_rows(min_row=2, values_only=True):
        if len(row) >= 6:
            t = str(row[1]) if row[1] else ""
            sender = str(row[3]) if row[3] else ""
            receiver = str(row[4]) if row[4] else ""
            subject = str(row[5]) if row[5] else ""
            
            email_dict = {
                "log_time": str(row[0]) if row[0] else "",
                "mail_time": t,
                "direction": str(row[2]) if row[2] else "",
                "sender": sender,
                "receiver": receiver,
                "subject": subject,
                "folder": str(row[6]) if len(row) > 6 and row[6] else "",
                "reply_time": str(row[7]) if len(row) > 7 and row[7] else ""
            }
            key = (receiver, sender, subject, t)
            if key not in seen_keys:
                seen_keys.add(key)
                all_emails.append(email_dict)
    
    with open(log_file, "a", encoding="utf-8") as f:
        try:
            import win32com.client
            outlook = win32com.client.Dispatch("Outlook.Application")
            namespace = outlook.GetNamespace("MAPI")
            
            new_emails_fetched = []
            
            for target_account_name in target_accounts:
                msg = f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始读取邮箱 [{target_account_name}] 全目录 ..."
                print(msg)
                f.write(msg + "\n")
                
                target_account = None
                for account in namespace.Accounts:
                    if account.DisplayName == target_account_name:
                        target_account = account
                        break
                        
                if not target_account:
                    err = f"  -> 未找到该邮箱账户，跳过。"
                    print(err)
                    f.write(err + "\n")
                    continue
                    
                try:
                    sent_folder = target_account.DeliveryStore.GetDefaultFolder(5)
                    sent_folder_id = sent_folder.EntryID
                except:
                    sent_folder_id = ""
                    
                account_smtp_address = ""
                try:
                    account_smtp_address = target_account.SmtpAddress
                except:
                    pass
                
                try:
                    root_folder = target_account.DeliveryStore.GetRootFolder()
                except:
                    err = "无法获取该账号的根文件夹，跳过。"
                    print(err)
                    f.write(err + "\n")
                    continue
                    
                cutoff_date = datetime.now() - timedelta(hours=past_hours)
                
                fetched_emails, total_count = process_folder(root_folder, cutoff_date, max_emails, sent_folder_id, account_smtp_address, target_account_name, 0)
                
                summary = f"  -> [{target_account_name}] 读取完成，共拉取 {total_count} 封。\n"
                print(summary)
                f.write(summary)
                
                new_emails_fetched.extend(fetched_emails)
                
            # 合并新邮件
            for email in new_emails_fetched:
                key = (email["receiver"], email["sender"], email["subject"], email["mail_time"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_emails.append(email)
                    
            # 按时间排序 (旧的在前)
            all_emails.sort(key=lambda x: x["mail_time"])
            
            # 清理超期的邮件
            cutoff_retention_str = (datetime.now() - timedelta(hours=retention_hours)).strftime('%Y-%m-%d %H:%M:%S')
            all_emails = [e for e in all_emails if e["mail_time"] >= cutoff_retention_str]
            
            # 回复状态机处理
            unanswered_customer_emails = [] # list of dicts reference
            
            for e in all_emails:
                sender = e["sender"]
                if not is_employee(sender, exclude_emails):
                    # 客户发来的邮件
                    e["reply_time"] = "No Response"
                    unanswered_customer_emails.append(e)
                else:
                    # 员工发送的邮件
                    receivers_str = e["receiver"]
                    emp_subject = clean_subject(e["subject"])
                    
                    matched_customer_email = None
                    
                    for cust_e in unanswered_customer_emails:
                        # 检查员工邮件的收件人中是否包含该客户的发件人
                        cust_sender_cleaned = cust_e["sender"].split("<")[-1].replace(">", "").strip() if "<" in cust_e["sender"] else cust_e["sender"].strip()
                        if not cust_sender_cleaned:
                            cust_sender_cleaned = cust_e["sender"]
                            
                        # 如果是粗略匹配，只要客户的名字或邮箱在收件人字符串里即可
                        if cust_sender_cleaned.lower() in receivers_str.lower():
                            # 进一步检查标题相似度
                            cust_subject = clean_subject(cust_e["subject"])
                            similarity = difflib.SequenceMatcher(None, emp_subject, cust_subject).ratio()
                            if similarity >= 0.8:
                                matched_customer_email = cust_e
                                break
                    
                    if matched_customer_email:
                        # 匹配成功，这是回复邮件
                        matched_customer_email["reply_time"] = e["mail_time"]
                        unanswered_customer_emails.remove(matched_customer_email)
                        e["reply_time"] = "Reply Mail"
                    else:
                        # 未匹配，或者是主动发送的邮件
                        e["reply_time"] = "Normal Mail"
            
            # 覆写 Excel
            ws.delete_rows(2, ws.max_row)
            for e in all_emails:
                ws.append([
                    e["log_time"], 
                    e["mail_time"], 
                    e["direction"], 
                    e["sender"], 
                    e["receiver"], 
                    e["subject"], 
                    e["folder"], 
                    e["reply_time"]
                ])
                
            wb.save(excel_file)
            print(f"\\n[完毕] 成功应用回复匹配状态机，共写入 {len(all_emails)} 条记录。")
            f.write(f"\\n[完毕] 成功应用回复匹配状态机，共写入 {len(all_emails)} 条记录。\\n")
            
        except Exception as e:
            err = f"读取邮件时发生严重异常:\n{traceback.format_exc()}"
            print(err)
            f.write(err + "\n")
            if wb:
                wb.save(excel_file)

if __name__ == "__main__":
    try:
        run_task()
    except Exception as e:
        print(f"任务执行失败: {e}")
