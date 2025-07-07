Extract.py
使用說明
功能簡介
主要用於批次處理 input 資料夾內的圖片或 PDF 檔案，透過AI進行資料萃取，並將結果以 JSON 格式輸出至 output 資料夾。支援自動搬移處理後的檔案、錯誤檔案管理、日誌記錄、動態 prompt 對應等。
支援檔案格式
-	圖片：.jpg, .jpeg, .png, .bmp
-	PDF：.pdf
主要流程
1.	掃描 input 資料夾（含子資料夾）所有支援的檔案
2.	依據檔案類型自動選擇 prompt（可依子資料夾對應不同 prompt）
3.	呼叫  API 進行資料萃取
4.	將結果以 JSON 格式輸出至 output 資料夾（保留原有子資料夾結構）
5.	處理成功的檔案自動搬移至 old 資料夾，失敗則搬移至 error 資料夾
6.	產生 summary log
參數與設定
-	API_KEY： API 金鑰（由開發者設定）
-	API_URL： API 端點（由開發者設定）
-	INPUT_FOLDER：輸入檔案資料夾（預設 input）
-	OUTPUT_FOLDER：輸出 JSON 資料夾（預設 output）
-	OLD_FOLDER：成功處理後檔案搬移資料夾（預設 old）
-	ERROR_FOLDER：失敗檔案搬移資料夾（預設 error）
-	PROMPT_DIR：prompt 對應目錄（可依子資料夾自訂 prompt）
-	PROMPT_FILE：預設 prompt 檔案
-	LOG_FILE：日誌檔案路徑
-	LOG_TO_FILE：是否寫入日誌檔
-	MOVE_PROCESSED_FILE：是否自動搬移處理後檔案
執行方式
python Extract
支援參數（可選）
-	--input_folder 指定輸入資料夾
-	--output_folder 指定輸出資料夾
-	--old_folder 指定 old 資料夾
-	--error_folder 指定 error 資料夾
-	--prompt_file 指定 prompt 檔案
-	--log_file 指定 log 檔案
-	--move_processed_file / --no_move_processed_file 控制是否搬移檔案
-	--log_to_file / --no_log_to_file 控制是否寫入日誌檔

範例：

python --input_folder ./input --output_folder ./output --move_processed_file
資料夾結構建議
AI/

  input/           # 原始檔案（可有多層子資料夾）

  output/          # 萃取結果 JSON（保留子資料夾結構）

  old/             # 處理成功後搬移的檔案

  error/           # 處理失敗搬移的檔案

  prompt/          # 可依 input 子資料夾自訂 prompt.txt

  prompt.txt       # 預設 prompt

  extract_log.txt  # 日誌檔
常見問題
-	API 金鑰錯誤或配額不足：請確認 API_KEY 正確且有配額
-	** 回傳格式非 JSON**：程式會嘗試自動去除 markdown 標記，若仍無法解析，會寫入空陣列
-	檔案搬移失敗：請確認 old/error 資料夾有寫入權限
-	prompt 對應：可在 prompt/ 下建立與 input 子資料夾同名的 .txt 以自訂 prompt
其他
-	執行時會自動產生 config.json（若不存在）
-	產生 summary log 記錄成功與失敗檔案
-	支援 logging 記錄詳細處理過程

Generate.py

AI 自然語言圖表產生器
功能簡介
本程式可將自然語言描述的圖表需求，透過 AI 轉換為 Python 原生繪圖程式碼（如 matplotlib、networkx 等），並自動執行產生圖表。
支援圖表類型
-	折線圖、長條圖、圓餅圖、散點圖、直方圖、箱型圖、雷達圖、熱力圖等（matplotlib）
-	流程圖、組織圖、網路圖（networkx）
-	其他常見 Python 視覺化套件（如 pandas、seaborn、plotly）
使用方式
1.	執行 Genrate.py
2.	輸入圖表需求（如：「畫一個圓餅圖，A 50%，B 30%，C 20%」）
3.	程式會自動呼叫 AI 產生 Python 程式碼，並自動執行繪圖
4.	若要結束，輸入 exit
自動化 JSON 轉圖表
-	程式會自動讀取 output 資料夾下所有 .json 檔案
-	針對每個 JSON 檔案，AI 會自動產生對應的 Python 繪圖程式碼並執行
-	支援多種 JSON 結構，只要在 prompt 中描述需求即可
範例
1. 直接輸入需求
請根據以下 JSON 資料畫出每個來源的銷售金額長條圖：

[{"來源": "A店", "金額": 1000}, {"來源": "B店", "金額": 1500}, {"來源": "C店", "金額": 800}]
2. 自動化批次處理
-	將多個 JSON 檔案放入 output 資料夾
-	執行程式，會自動批次轉換為圖表
注意事項
-	本程式需連網並設定 API key
-	執行 AI 產生的程式碼有一定風險，請勿輸入不信任的內容
-	支援的圖表類型取決於 AI 及 Python 套件能力

