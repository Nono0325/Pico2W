# Raspberry Pi Pico 2 W - 物聯網核心實戰課程指南

本專案專為 **Raspberry Pi Pico 2 W (RP2350 + CYW43439)** 打造，精選兩大現代物聯網核心實務課程與實驗：
1. **課程與實驗 1：MQTT 物聯網雙向雲端通訊 (使用台灣在地 [MQTTGO.io](https://mqttgo.io/) 平台)**
2. **課程與實驗 2：台灣政府開放資料 (data.gov.tw) API 串接與智慧燈號警報**

> 💡 **零外接硬體門檻 & 單檔即跑設計 (All-in-One Standalone)**：  
> 全系列實驗完全不需要外接麵包板或感測器模組，直接善用 Pico 2 W 板載 CYW43439 無線晶片、板載 LED 與 RP2350 內部溫度感測器即可完整執行！所有 Wi-Fi 連線設定直接寫在腳本頂部，開啟檔案填入帳密即可一鍵執行。

---

## 快速設定步驟

### 1. 準備 Thonny IDE 與 Pico 2 W
1. 下載並安裝 [Thonny IDE](https://thonny.org/)。
2. 按住 Pico 2 W 板上的 **BOOTSEL** 按鈕不放，插入 USB 線連接至電腦，隨後放開按鈕。
3. 在 Thonny 右下角直譯器選單選擇 **MicroPython (Raspberry Pi Pico)**，若初次使用點擊「Install」自動刷入最新韌體。
4. 將本專案資料夾中的 `umqtt/` 目錄複製到 Pico 2 W 的根目錄（提供輕量 MQTT 通訊支援）。

### 2. 設定 Wi-Fi 帳號密碼
在實驗檔案（如 [lab1_mqttgo_iot.py](file:///c:/Nono/Pico2%20W/lab1_mqttgo_iot.py) 或 [lab2_gov_opendata.py](file:///c:/Nono/Pico2%20W/lab2_gov_opendata.py)）開頭填入 Wi-Fi 資訊：
```python
WIFI_SSID = "您的Wi-Fi名稱"       # 注意：Pico 2 W 支援 2.4GHz Wi-Fi
WIFI_PASSWORD = "您的Wi-Fi密碼"
```

---

## 實驗清單與技術地圖

| 實驗編號 | 程式檔案 | 課程與實作核心 | 核心通訊技術 | 互動與實驗亮點 |
| :--- | :--- | :--- | :--- | :--- |
| **實驗 1** | [lab1_mqttgo_iot.py](file:///c:/Nono/Pico2%20W/lab1_mqttgo_iot.py) | **MQTT 物聯網雙向雲端通訊** | MQTT Pub/Sub (TCP 1883) | 連線台灣在地 [MQTTGO.io](https://mqttgo.io/) 免費 Broker。每 5 秒發布內部溫度，並訂閱控制主題；學員直接用手機或電腦瀏覽器打開網頁即時雙向遙控板載 LED！ |
| **實驗 2** | [lab2_gov_opendata.py](file:///c:/Nono/Pico2%20W/lab2_gov_opendata.py) | **台灣政府開放資料 API 串接** | HTTPS GET / RESTful / JSON 解析 | 串接 [data.gov.tw](https://data.gov.tw/) 政府開放資料平臺 (氣象署測站 API)。以 StationId 精準過濾取得 2KB 輕量 JSON，解析即時天氣與降雨，下雨自動觸發板載 LED 快閃警報！ |

---

### 📡 實驗 1：MQTTGO.io 雙向通訊操作流程
1. 執行 [lab1_mqttgo_iot.py](file:///c:/Nono/Pico2%20W/lab1_mqttgo_iot.py)，終端機將印出裝置專屬的：
   - 溫度發布主題：`pico2w/<DEVICE_ID>/temp`
   - LED 控制主題：`pico2w/<DEVICE_ID>/led`
2. 打開瀏覽器前往 [https://mqttgo.io/](https://mqttgo.io/)：
   - 在**訂閱主題**輸入 `pico2w/<DEVICE_ID>/temp`，即可每 5 秒看到板載溫度更新。
   - 在**發布主題**輸入 `pico2w/<DEVICE_ID>/led`，訊息填入 `on`、`off` 或 `toggle`，點擊發布即可遠端即時操控 Pico！

---

### 🏛️ 實驗 2：台灣政府開放資料 (data.gov.tw) 操作流程
1. 執行 [lab2_gov_opendata.py](file:///c:/Nono/Pico2%20W/lab2_gov_opendata.py)。
2. Pico 2 W 連上 Wi-Fi 後，自動呼叫政府開放資料平臺觀測站 RESTful API：
   - 預設測站為臺北 (`466920`)，亦可自由切換為臺中 (`467490`)、高雄 (`467440`)、基隆 (`466940`)、花蓮 (`466990`) 等。
3. 取得即時氣溫、濕度、當日降雨量：
   - 若偵測到降雨（累積雨量 > 0 或天氣含雨），板載 LED 自動連續快閃示警！
   - 天氣良好無降雨時，LED 恆亮 1.5 秒表示正常。

---

## 🖥️ 互動式教學網頁 (Interactive Web Handbook)
專案附帶現代化長頁式技術教學網頁：
* **檔案路徑**：[index.html](file:///c:/Nono/Pico2%20W/index.html) (或 [presentation.html](file:///c:/Nono/Pico2%20W/presentation.html))
* **開啟方式**：雙擊檔案或在 Chrome / Edge 中開啟。
* **特色功能**：
  1. 📘 **MQTT 深入理論**：HTTP vs. MQTT 比較表、Pub/Sub 三重解耦、主題階層與萬用字元（`+` 與 `#`）、QoS 0/1/2 差異、Retain/Keepalive/LWT 原理。
  2. 📘 **政府開放資料深入理論**：data.gov.tw 生態、RESTful GET 語意、URL 結構、JSON 防禦性解析 (`.get()`)、微控制器記憶體 5 大挑戰（650KB vs 2KB）。
  3. 🎮 **虛擬 Pico 2 W 互動模擬器**：可在瀏覽器直接切換虛擬 LED 燈與監看 MQTT 通訊日誌。
  4. ⚡ **中央氣象署 API Live Fetch**：點擊測站即可由瀏覽器即時呼叫氣象署公開端點，展示即時天氣與雨量警報。
  5. 📑 **完整原始碼一鍵複製**：所有實驗檔案代碼隨點即複製。
