import os
import json
import csv
import win32com.client as win32
from pathlib import Path

# 預設參數
default_config = {
    "json_folder": "output",  # 預設為 output 資料夾
    "csv_folder": "CSVs",
    "mail_to": "george.ho@zerone.com.tw;guing88@gmail.com",
    "mail_subject": "解析憑證CSV",
    "mail_body": "請查收附件所有CSV檔案，謝謝"
}

# 嘗試讀取 config.json
config = default_config.copy()
if os.path.exists('config.json'):
    with open('config.json', 'r', encoding='utf-8') as f:
        file_config = json.load(f)
        config.update(file_config)

# 取得 Import.py 所在目錄
BASE_DIR = Path(__file__).parent.resolve()

# 取得 json_folder 路徑（自動判斷絕對/相對）
json_folder = Path(config['json_folder'])
if not json_folder.is_absolute():
    json_folder = BASE_DIR / json_folder
json_folder = json_folder.resolve()

csv_folder = Path(config['csv_folder'])
if not csv_folder.is_absolute():
    csv_folder = BASE_DIR / csv_folder
csv_folder = csv_folder.resolve()

mail_to = config['mail_to']
mail_subject = config['mail_subject']
mail_body = config['mail_body']

os.makedirs(json_folder, exist_ok=True)
os.makedirs(csv_folder, exist_ok=True)
csv_files = []

# 1. 讀取所有 JSON 檔案
for filename in os.listdir(json_folder):
    if filename.endswith('.json'):
        json_path = json_folder / filename
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        if not data:
            continue
        # 判斷 data 是 list 還是 dict
        if isinstance(data, dict):
            data = [data]  # 轉成 list 方便後續處理
        # 2. 動態取得所有欄位（收集所有資料的 key，並依第一筆順序排序）
        all_keys = []
        for row in data:
            for k in row.keys():
                if k not in all_keys:
                    all_keys.append(k)
        # 3. 寫入 CSV
        csv_name = filename.replace('.json', '.csv')
        csv_path = csv_folder / csv_name
        with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=all_keys, extrasaction='ignore')
            writer.writeheader()
            for row in data:
                # 若有缺漏欄位自動補空
                writer.writerow({k: row.get(k, "") for k in all_keys})
        csv_files.append(str(csv_path))

# 4. 用 Outlook 發送所有 CSV
outlook = win32.Dispatch('outlook.application')
mail = outlook.CreateItem(0)
mail.To = mail_to
mail.Subject = mail_subject
mail.Body = mail_body
for csv_file in csv_files:
    mail.Attachments.Add(csv_file)
mail.Send()