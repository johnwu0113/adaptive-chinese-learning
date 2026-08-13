# MAS 語言學習多代理人系統

這個專案是一個以多代理人（Multi-Agent System, MAS）為核心設計的語言學習原型系統，旨在模擬真實語言學習場景中，學生、診斷代理、規劃代理與教師代理之間的協作流程。系統將學生的兩輪語言輸入轉換為診斷結果，再進一步推導學習路徑與教學策略，最終在教師介入與全局監控機制下完成更完整的學習陪伴。

本系統的核心目標包括：
- 讓學生在語言練習中獲得即時、具體、情緒友善的回饋
- 讓教師能了解學生的診斷狀態與高風險情境
- 讓系統具備從診斷、規劃、教學到監控的完整 MAS 流程
- 讓原型適合展示、教學、測試與後續擴展

## 專案特點

- SA（Student Agent）：負責學生資料整理、作答紀錄收集、表現特徵抽取
- DA（Diagnostic Agent）：負責分析語法、詞彙與流暢度，產出診斷報告
- PA（Planning Agent）：負責產生學習目標與教學策略，轉成適性化建議
- TA（Teacher Agent）：負責監控全局狀態與判斷是否需要真人介入
- FastAPI 後端：提供 API 供前端或外部系統呼叫
- HTML 前端原型：提供簡易互動介面，方便展示 MAS 流程
- pytest 測試：驗證後端流程、API 行為與前端互動流程
- Mock / fallback LLM：在未設定真實 API 金鑰時，仍可維持本地演示

## 六步 MAS 流程

### 第一步：學習啟動與前端陪伴
- 啟動系統、建立學習會話、讓學生輸入兩輪語句，完成登入與陪伴入口初始化。

### 第二步：資料攔截與回傳（SA ➜ DA）
- SA 收集學生發言內容、錯誤特徵、字數長度、挫折程度，並將這些資訊傳給 DA。

### 第三步：診斷與錯誤溯源（DA 認知層）
- DA 分析文法、詞彙、流暢度與錯誤型態，並掃描潛在知識斷層。

### 第四步：動態路徑規劃與優化（DA ➜ PA）
- PA 接收診斷結果，鎖定學習目標、擴展學習策略、選擇適合的教學路徑。

### 第五步：適性化教學執行與情緒調節（PA ➜ SA）
- PA 將規劃結果轉成更自然、鼓勵式的語言，修正語氣與節奏，降低學習挫敗感。

### 第六步：全局監控與真人介入（TA 儀表板）
- TA 彙整整體表現、偵測高風險案例，必要時發出警報並提醒教師介入。

## 專案結構

```text
.
├── mas_app/
│   ├── __init__.py
│   ├── agents.py
│   ├── api.py
│   ├── config.py
│   └── llm_service.py
├── tests/
│   ├── conftest.py
│   └── test_mas_flow.py
├── language-agent-prototype.html
├── mas_backend.py
├── functional_test_runner.py
├── README.md
├── requirements.txt
├── pytest.ini
└── .gitignore
```

## 環境需求

- Python 3.10 或以上
- pip
- 可用的網路環境（若要使用真實 LLM API）
- Chromium（用於 Playwright 前端測試）

## 安裝說明

### 1) 建立虛擬環境

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux / macOS:

```bash
source .venv/bin/activate
```

### 2) 安裝依賴套件

```bash
pip install -r requirements.txt
```

若要讓前端自動化測試跟 Playwright 瀏覽器執行正常，請額外安裝 Chromium：

```bash
python -m playwright install chromium
```

## 啟動方式

### 啟動後端

在專案根目錄執行：

```bash
python mas_backend.py
```

啟動後可在瀏覽器中開啟：
- http://127.0.0.1:8000

### 啟動前端

直接開啟 `language-agent-prototype.html` 或使用後端根路徑。

## 程式使用說明

### 1) 使用前端並執行 MAS 流程

1. 打開前端原型頁面
2. 在 `turn1` 與 `turn2` 欄位輸入學生的兩輪語句
3. 點擊提交按鈕
4. 系統會依序產生：
   - 學生上下文
   - 診斷結果
   - 學習建議
   - 教師介入狀態

### 2) 直接呼叫後端 API

#### 健康檢查

```bash
curl http://127.0.0.1:8000/health
```

#### 執行 MAS 流程

```bash
curl -X POST "http://127.0.0.1:8000/api/run-pipeline" \
  -H "Content-Type: application/json" \
  -d '{
    "turn1": "I think traveling is important because it help you to know different culture.",
    "turn2": "Yesterday I go to the museum with my friend, it was very fun."
  }'
```

#### 產生教師補充建議

```bash
curl -X POST "http://127.0.0.1:8000/api/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "diagnosis": {
      "level": 2,
      "confidence": 0.8,
      "breakdown": {"vocab": 60, "grammar": 45, "fluency": 50},
      "notes": "文法結構仍較不穩定。"
    },
    "teacher_input": "請加強過去式動詞與連接詞。"
  }'
```

## LLM 設定

如果你希望接上真實的 OpenAI 相容 API，請設定以下環境變數：

```bash
set OPENAI_API_KEY=your_key
set OPENAI_BASE_URL=https://api.openai.com/v1
set OPENAI_MODEL=gpt-4o-mini
set USE_MOCK_LLM=false
```

若未設定，系統會自動啟用 mock 邏輯。

## 測試說明

```bash
python -m pytest tests -q
```

## 使用場景

這個專案適合：
- 教學示範：教導 MAS 概念與多代理合作模式
- 語言學習系統原型：用於文法、字彙與流暢度診斷
- 教師介入演練：觀察高風險學習情境並觸發介入
- 原型驗證：驗證前後端整合與自動化測試流程

## 注意事項

- 本專案目前偏向原型展示與教學用途，不是完整商業級語言學習平台
- 若要接入正式 LLM、資料庫與認證系統，需進一步補足架構與部署環境
- 若學生表現出高風險狀態，系統會提示教師介入，確保「人」仍保留在學習回路中

## 總結

MAS 語言學習多代理人系統透過 SA、DA、PA、TA 四個角色，將語言學習診斷、學習規劃與教師協作整合為一個完整循環。它不僅能展示多代理人設計理念，也為後續擴展到更真實的教育科技平台提供了良好基礎。
