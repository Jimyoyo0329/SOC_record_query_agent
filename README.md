## 說明
### 功能
1. 建立一個SOC事件問答AI
2. 支援自然語言查詢
3. 用戶可上傳xlsx檔案，並一鍵產出事件備註及相似事件摘要
4. 可進行多倫問答

### 程式碼說明
1. main.py
- 前端主要畫面，使用steamlit套件編寫

2. embedding.py
- 可直接修改模型名稱，所有embedding的部分模型就會變成新套用的

3. query.py
- 根據前端使用者選擇的特定過濾欄位進行查詢
- 例如:使用者選擇alert.signature，那他就會去後端資料庫，找出與上傳xlsx資料相同alert.signature相同的資料出來

4. llm_utils.py
- 就是把query.py抓出來的原始資料丟給LLM進行摘要，不是問答的

5. rag_model資料夾
這是自然語言查詢摘要與問答的主要程式碼資料夾
- call_api.py 就是call LLM，如果要改地端要手動修改
- need_retrieval.py 會判斷是否需要進行查詢
- rag_core.py 是查詢主程式，會把問題轉sql，然後將查出來的內容進行摘要

6. data_ingestion 資料夾
- ingest.py 可以把文件embedding後存到Chroma向量資料庫，可以改資料庫
    - 用法: python3 ingest.pt --file <csv or xlxs file>
- xlsx_to_database.py 可以把文件直接做處理後存到sqlite資料庫
    - 用法 : 手動改 EXCEL_FILE DB_FILE TABLE_NAME
- 以上都要手動執行，前端沒有提供一鍵儲存

### 目前採用模型
- 語言模型 : gpt-4o
- embedding : all-mpnet-base-v2

### 資料庫
- SQLite
- 也可以使用其他資料庫只是程式碼就需要更改

### 環境安裝
1. 使用Anaconda Prompt 輸入以下指令
conda env create -f environment.yml --name <my_custom_env>

2. 用requirements.txt
- python 3.11
- pip install -r requirements.txt

### 啟動方式
1. 使用Anacanda Prompt，開啟虛擬環境 conda activate <your_environment_name>
2. 切到main.py所在的資料夾目錄
3. streamlit run main.py

### 注意 ! ! !
如果要部署在開放網域上，API 記得要改掉，放在環境變數。
