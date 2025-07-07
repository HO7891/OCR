import requests
import re
import os
import json
import time
from datetime import datetime

API_KEY = "AIzaSyBNBaQjcuNmnrGsoIXTHhgPxN9GFV-i0JE"
API_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent"

# 中文字型設定片段
FONT_PATCH = '''\nimport matplotlib\nmatplotlib.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS', 'sans-serif']\nmatplotlib.rcParams['axes.unicode_minus'] = False\n'''

DEFAULT_BATCH_CHART_TYPE = 'bar'  # 長條圖
# DEFAULT_BATCH_CHART_TYPE = 'pie'    # 圓餅圖
# DEFAULT_BATCH_CHART_TYPE = 'line'   # 折線圖
# DEFAULT_BATCH_CHART_TYPE = 'scatter'# 散點圖
# DEFAULT_BATCH_CHART_TYPE = 'hist'   # 直方圖
# DEFAULT_BATCH_CHART_TYPE = 'box'    # 箱型圖
# DEFAULT_BATCH_CHART_TYPE = 'area'   # 區域圖
# DEFAULT_BATCH_CHART_TYPE = 'network'# 網路圖
# DEFAULT_BATCH_CHART_TYPE = 'radar'  # 雷達圖

def generate_python_code(prompt, chart_type=None):
    """呼叫 Gemini API，將自然語言 prompt 轉為 Python 繪圖程式碼"""
    headers = {
        "Content-Type": "application/json"
    }
    # 指定 AI 只能回傳 Python 程式碼區塊
    if chart_type:
        ai_prompt = f"""
請根據以下需求產生 Python 程式碼，並**只回傳程式碼區塊**，不要有任何說明文字：
- 需求：{prompt}
- 請用 {chart_type} 呈現
- 請用 matplotlib、networkx、pandas 等原生套件繪圖
- 程式碼區塊請用 ```python ... ``` 包起來
- 請用繁體中文註解
"""
    else:
        ai_prompt = f"""
請根據以下需求產生 Python 程式碼，並**只回傳程式碼區塊**，不要有任何說明文字：
- 需求：{prompt}
- 請用 matplotlib、networkx、pandas 等原生套件繪圖
- 程式碼區塊請用 ```python ... ``` 包起來
- 請用繁體中文註解
"""
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": ai_prompt}]
        }]
    }
    api_url_with_key = f"{API_URL_BASE}?key={API_KEY}"
    try:
        response = requests.post(api_url_with_key, headers=headers, json=payload, timeout=90)
        if response.status_code == 200:
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            # 只取出 ```python ... ``` 區塊
            match = re.search(r'```python\s*([\s\S]*?)\s*```', text)
            if match:
                return match.group(1).strip()
            return text.strip()
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ API 請求時發生錯誤: {e}")
        return None

def patch_code(code, save_path=None):
    """插入中文字型設定，並自動儲存圖檔到 save_path（若有），自動移除 plt.show()"""
    patched = FONT_PATCH + code
    save_path_fixed = save_path.replace('\\', '/') if save_path else None
    # 先移除所有 plt.show()
    patched = re.sub(r'plt\.show\s*\(\s*\)', '', patched)
    # 自動將 plt.savefig 插入
    if save_path_fixed:
        patched += f"\nimport matplotlib.pyplot as plt\nplt.savefig(r'{save_path_fixed}', bbox_inches='tight')\n"
    return patched

def run_code(code, extra_globals=None):
    """執行 AI 回傳的 Python 程式碼，可傳入額外全域變數"""
    try:
        exec(code, extra_globals if extra_globals else globals())
    except Exception as e:
        print(f"❌ 執行程式碼時發生錯誤: {e}")

def auto_process_json_files():
    """自動讀取 output 資料夾下所有 .json 檔案並產生圖表"""
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    figures_dir = os.path.join(output_dir, 'figures')
    os.makedirs(figures_dir, exist_ok=True)
    if not os.path.exists(output_dir):
        print(f"output 資料夾不存在：{output_dir}")
        return
    json_files = [f for f in os.listdir(output_dir) if f.lower().endswith('.json')]
    if not json_files:
        print("output 資料夾內無 .json 檔案，自動化批次處理略過。")
        return
    for fname in json_files:
        fpath = os.path.join(output_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                data = f.read()
            print(f"\n--- 自動處理檔案：{fname} ---")
            prompt = f"請根據以下 JSON 資料自動產生最適合的圖表，並用 Python 程式碼繪製：\n{data}"
            code = generate_python_code(prompt, chart_type=DEFAULT_BATCH_CHART_TYPE)
            if code:
                print("\n--- 產生的 Python 程式碼 ---")
                print(code)
                print("--------------------------")
                print("\n正在執行程式碼並繪圖...")
                # 儲存圖檔路徑
                img_name = os.path.splitext(fname)[0] + '.png'
                save_path = os.path.join(figures_dir, img_name)
                patched_code = patch_code(code, save_path=save_path)
                run_code(patched_code, {"json_data": data})
                print(f"✅ 圖檔已儲存至 {save_path}")
            else:
                print("❌ 產生程式碼失敗，請重試")
        except Exception as e:
            print(f"❌ 處理 {fname} 時發生錯誤: {e}")

if __name__ == "__main__":
    print("--- 啟動自動化批次處理 output 內所有 .json 檔案 ---")
    auto_process_json_files()
    print("--- 手動輸入模式 ---")
    print("請輸入圖表需求（輸入 'exit' 結束程式）")
    while True:
        user_input = input("\n請輸入圖表需求: ").strip()
        if user_input.lower() == 'exit':
            break
        if not user_input:
            print("請輸入有效的圖表需求！")
            continue
        print("\n正在請 AI 產生 Python 繪圖程式碼...")
        code = generate_python_code(user_input)
        if code:
            print("\n--- 產生的 Python 程式碼 ---")
            print(code)
            print("--------------------------")
            print("\n正在執行程式碼並繪圖...")
            # 手動模式下自動儲存圖檔
            figures_dir = os.path.join(os.path.dirname(__file__), 'output', 'figures')
            os.makedirs(figures_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            save_path = os.path.join(figures_dir, f'prompt_{timestamp}.png')
            patched_code = patch_code(code, save_path=save_path)
            run_code(patched_code)
            print(f"✅ 圖檔已儲存至 {save_path}")
        else:
            print("❌ 產生程式碼失敗，請重試")
