import base64
import json
import mimetypes
import requests
from pathlib import Path
from datetime import datetime
import time
import logging
import argparse
import os
import re

# 自動偵測執行檔所在目錄
try:
    BASE_DIR = Path(__file__).parent.resolve()
except NameError:
    BASE_DIR = Path.cwd().resolve()

# === 設定區（集中管理） ===
CONFIG = {
    "API_KEY": "AIzaSyBNBaQjcuNmnrGsoIXTHhgPxN9GFV-i0JE",  # ⚠️ 請替換為你的 Gemini API 金鑰
    "API_URL": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent",
    "INPUT_FOLDER": BASE_DIR / "input",
    "OUTPUT_FOLDER": BASE_DIR / "output",
    "SUPPORTED_EXTS": [".jpg", ".jpeg", ".png", ".pdf", ".bmp"],
    "PROMPT_DIR": BASE_DIR / "prompt",  # 多個 prompt 對應目錄
    "PROMPT_FILE": str(BASE_DIR / "prompt.txt"),  # fallback 預設 prompt
    "LOG_LEVEL": logging.INFO,
    "LOG_FILE": str(BASE_DIR / "extract_log.txt"),  # log 檔案路徑
    "LOG_TO_FILE": False,  # True=寫入檔案，False=只顯示在 console
    "MOVE_PROCESSED_FILE": True,  # 處理完是否搬移 input 檔案
    "OLD_FOLDER": BASE_DIR / "old",  # 搬移目標資料夾
    "ERROR_FOLDER": BASE_DIR / "error",  # 失敗檔案搬移資料夾
    "SHOW_GEMINI_RESPONSE": False,  # 是否顯示 Gemini 回傳內容於執行時
}

# 預設 prompt 內容（可改為讀取外部檔案）
PROMPT_TEXT = (
    "請提取出所有核對需知，**完整列出**所有資訊並解析為 JSON 格式，欄位表示為：\n"
    "- 交易日期起訖\n"
    "- 付款方式，請抓取結帳方式如:信用卡、linepoint、一卡通\n"
    "- 金額，不要顯示任何千分位**,**。\n"
    "請直接回傳 JSON 結果，若無法辨識請填 \"未識別\"，不要包含其他說明文字。請列出完整資料，直到明確結束為止"
    "範例格式：\n"
    "[\n"
    "  {\n"
    "    \"日期起\": \"2023/08/25/11:00\",\n"
    "    \"日期訖\": \"2023/08/25/23:59\",\n"
    "    \"付款方式\": \"LinePay\",\n"
    "    \"金額\": \"168\",\n"
    "  },\n"
    "  ...\n"
    "]"
)

def parse_args():
    parser = argparse.ArgumentParser(description="Extract and process files with Gemini API.")
    parser.add_argument('--input_folder', type=str, help='Input folder path')
    parser.add_argument('--output_folder', type=str, help='Output folder path')
    parser.add_argument('--old_folder', type=str, help='Old folder path')
    parser.add_argument('--error_folder', type=str, help='Error folder path')
    parser.add_argument('--prompt_file', type=str, help='Prompt file path')
    parser.add_argument('--log_file', type=str, help='Log file path')
    parser.add_argument('--move_processed_file', action='store_true', help='Move processed files to old folder')
    parser.add_argument('--no_move_processed_file', action='store_true', help='Do not move processed files')
    parser.add_argument('--log_to_file', action='store_true', help='Enable log to file')
    parser.add_argument('--no_log_to_file', action='store_true', help='Disable log to file')
    return parser.parse_args()

def update_config_from_args(args):
    if args.input_folder:
        CONFIG["INPUT_FOLDER"] = Path(args.input_folder)
    if args.output_folder:
        CONFIG["OUTPUT_FOLDER"] = Path(args.output_folder)
    if args.old_folder:
        CONFIG["OLD_FOLDER"] = Path(args.old_folder)
    if args.error_folder:
        CONFIG["ERROR_FOLDER"] = Path(args.error_folder)
    if args.prompt_file:
        CONFIG["PROMPT_FILE"] = args.prompt_file
    if args.log_file:
        CONFIG["LOG_FILE"] = args.log_file
    if args.move_processed_file:
        CONFIG["MOVE_PROCESSED_FILE"] = True
    if args.no_move_processed_file:
        CONFIG["MOVE_PROCESSED_FILE"] = False
    if args.log_to_file:
        CONFIG["LOG_TO_FILE"] = True
    if args.no_log_to_file:
        CONFIG["LOG_TO_FILE"] = False

def load_prompt_for_file(file_path, input_folder):
    """根據 input 子資料夾自動對應 prompt/子資料夾名.txt，找不到則 fallback 預設 prompt。"""
    try:
        relative_path = file_path.relative_to(input_folder)
        # 取第一層子資料夾名稱
        if len(relative_path.parts) > 1:
            subfolder = relative_path.parts[0]
            prompt_file = CONFIG["PROMPT_DIR"] / f"{subfolder}.txt"
            if prompt_file.exists():
                with open(prompt_file, "r", encoding="utf-8") as f:
                    return f.read()
    except Exception as e:
        logging.warning(f"自動對應 prompt 失敗: {e}")
    # fallback: 單一預設 prompt
    if CONFIG["PROMPT_FILE"] and Path(CONFIG["PROMPT_FILE"]).exists():
        try:
            with open(CONFIG["PROMPT_FILE"], "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logging.warning(f"讀取 fallback prompt 檔案失敗，改用內建內容: {e}")
    return PROMPT_TEXT

def get_mime_type(file_path):
    mime_type = mimetypes.guess_type(file_path)[0]
    return mime_type or "application/octet-stream"

def file_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8-sig")

def generate_output_filename(file_path, suffix="_George"):
    """產生輸出檔名，可自訂規則。"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return f"{file_path.stem}{suffix}_{timestamp}.json"

def move_file_with_rename(src, dst_folder):
    """搬移檔案到 dst_folder，若同名自動加時間戳避免覆蓋。"""
    dst_folder = Path(dst_folder)
    dst_folder.mkdir(parents=True, exist_ok=True)
    target_path = dst_folder / src.name
    if target_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        target_path = dst_folder / f"{src.stem}_{timestamp}{src.suffix}"
    src.rename(target_path)
    return target_path

def send_to_gemini(file_path, input_folder, retries=3):
    mime_type = get_mime_type(file_path)
    encoded_data = file_to_base64(file_path)
    prompt = load_prompt_for_file(file_path, input_folder)

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": encoded_data
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    api_url = f"{CONFIG['API_URL']}?key={CONFIG['API_KEY']}"
    headers = {"Content-Type": "application/json"}

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
                char_count = len(text)
                estimated_tokens = int(char_count / 4)
                logging.info(f"回傳字元數：{char_count}，估算 token 數：約 {estimated_tokens} tokens")
                if CONFIG.get("SHOW_GEMINI_RESPONSE", False):
                    print("Gemini 回傳內容：", repr(text))
                # 去除 markdown 標記
                match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                else:
                    json_str = text
                return json_str, True
            else:
                logging.warning(f"第 {attempt} 次請求失敗 - {response.status_code}: {response.text}")
        except Exception as e:
            logging.error(f"錯誤於第 {attempt} 次請求: {e}")
        time.sleep(3)
    return "❌ 最終重試仍失敗", False

def process_all_files():
    results = []
    failed = []
    input_folder = CONFIG["INPUT_FOLDER"]
    output_folder = CONFIG["OUTPUT_FOLDER"]
    old_folder = CONFIG["OLD_FOLDER"]
    error_folder = CONFIG["ERROR_FOLDER"]
    supported_exts = CONFIG["SUPPORTED_EXTS"]
    # 自動建立所有資料夾
    for folder in [input_folder, output_folder, old_folder, error_folder]:
        folder.mkdir(parents=True, exist_ok=True)

    all_files = [f for f in input_folder.rglob("*") if f.is_file() and f.suffix.lower() in supported_exts]
    for idx, file_path in enumerate(all_files):
        # 取得 input_folder 下的相對路徑（含子資料夾）
        relative_path = file_path.relative_to(input_folder)
        relative_folder = relative_path.parent
        logging.info(f"處理中 ({idx+1}): {file_path}")
        result, success = send_to_gemini(file_path, input_folder)
        filename = generate_output_filename(file_path)
        # 輸出到 output 對應子資料夾
        output_subfolder = output_folder / relative_folder
        output_subfolder.mkdir(parents=True, exist_ok=True)
        output_path = output_subfolder / filename
        # 將 Gemini 回傳的 result 內容（字串）解析為 list，若失敗則寫入空陣列
        try:
            data = json.loads(result)
            if isinstance(data, dict):
                data = [data]  # 單一物件自動包成 list
            elif not isinstance(data, list):
                data = []
        except Exception:
            data = []
        with open(output_path, "w", encoding="utf-8-sig") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if success:
            results.append(str(relative_path))
            # 處理完搬移 input 檔案到 old 對應子資料夾（若啟用）
            if CONFIG.get("MOVE_PROCESSED_FILE", False):
                try:
                    old_subfolder = old_folder / relative_folder
                    old_subfolder.mkdir(parents=True, exist_ok=True)
                    moved_path = move_file_with_rename(file_path, old_subfolder)
                    logging.info(f"已搬移 {file_path} 至 {moved_path}")
                except Exception as e:
                    logging.error(f"搬移檔案失敗: {file_path} -> {old_subfolder}，錯誤: {e}")
        else:
            failed.append(str(relative_path))
            # 失敗搬移到 error 對應子資料夾
            try:
                error_subfolder = error_folder / relative_folder
                error_subfolder.mkdir(parents=True, exist_ok=True)
                moved_path = move_file_with_rename(file_path, error_subfolder)
                logging.info(f"失敗檔案已搬移 {file_path} 至 {moved_path}")
            except Exception as e:
                logging.error(f"搬移失敗檔案失敗: {file_path} -> {error_subfolder}，錯誤: {e}")
        time.sleep(2)
    logging.info(f"共處理 {len(results)} 筆檔案，失敗 {len(failed)} 筆。")
    # summary log
    summary_path = output_folder / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(summary_path, "w", encoding="utf-8-sig") as f:
        f.write(f"成功檔案 ({len(results)}):\n" + "\n".join(results) + "\n\n")
        f.write(f"失敗檔案 ({len(failed)}):\n" + "\n".join(failed) + "\n")
    logging.info(f"已產生 summary log: {summary_path}")
    return results, failed

if __name__ == "__main__":
    # 產生 config.json（若不存在）
    config_json_path = BASE_DIR / "config.json"
    config_data = {
        "json_folder": str(CONFIG["OUTPUT_FOLDER"].name),
        "csv_folder": "CSVs",
        "mail_to": "george.ho@zerone.com.tw;guing88@gmail.com",
        "mail_subject": "解析憑證CSV",
        "mail_body": "請查收附件所有CSV檔案，謝謝"
    }
    if not config_json_path.exists():
        with open(config_json_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        print(f"已產生 config.json 於 {config_json_path}")
    else:
        print(f"config.json 已存在於 {config_json_path}")
    args = parse_args()
    update_config_from_args(args)
    logging.basicConfig(level=CONFIG["LOG_LEVEL"], format="%(asctime)s [%(levelname)s] %(message)s")
    if CONFIG.get("LOG_TO_FILE", True):
        file_handler = logging.FileHandler(CONFIG["LOG_FILE"], encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logging.getLogger().addHandler(file_handler)
    process_all_files()
