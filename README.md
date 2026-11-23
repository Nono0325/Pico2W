# Raspberry Pi Pico 2 W - 物聯網核心實戰課程指南

> 🌐 **線上互動教材網頁**：[https://nono0325.github.io/Pico2W/](https://nono0325.github.io/Pico2W/)（免安裝，手機與電腦瀏覽器隨開即學）

本專案專為 **Raspberry Pi Pico 2 W (RP2350 + CYW43439)** 打造，精選現代物聯網核心實務課程與實驗：
1. **課程 1：MQTT 物聯網雙向雲端通訊 (使用台灣在地 [MQTTGO.io](https://mqttgo.io/) 平台)**
   * ⏱️ **專用課堂教案**：[LESSON_PLAN_MQTT_1HR.md](file:///c:/Nono/Pico2%20W/LESSON_PLAN_MQTT_1HR.md)（專為 60 分鐘工作坊規劃的極速上手實戰教案）
2. **課程 2A：Pico 2 W 邊緣微型 Web Server (RP2350 內部溫度監控與板載 LED 雙向無線控制)**
   * ⏱️ **專用課堂教案**：[LESSON_PLAN_WEBSERVER_1HR.md](file:///c:/Nono/Pico2%20W/LESSON_PLAN_WEBSERVER_1HR.md)（專為 60 分鐘規劃的邊緣伺服器與無重整 AJAX 實戰教案）
3. **課程 2B：Pico 2 W 邊緣 Web Server：Wi-Fi 空間雷達探測儀 (CYW43439 射頻掃描與頻譜分析)**
   * ⏱️ **專用課堂教案**：[LESSON_PLAN_WIFI_RADAR_1HR.md](file:///c:/Nono/Pico2%20W/LESSON_PLAN_WIFI_RADAR_1HR.md)（專為 60 分鐘規劃的「Wi-Fi 空間雷達」極速上手實戰教案，動手率 > 90%）
4. **課程 3：台灣政府開放資料 (data.gov.tw) API 串接與智慧燈號警報**

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
| **雙機配對** | [lab1_sender.py](file:///c:/Nono/Pico2%20W/lab1_sender.py)<br>[lab1_receiver.py](file:///c:/Nono/Pico2%20W/lab1_receiver.py) | **Pico 2 W 專屬傳送端與接收端** | MQTT 雙機配對互聯 (JSON) | 專為兩塊 Pico 2 W（或兩組學員）打造！傳送端定時將晶片溫度以 JSON 封包射出，發送時 LED 閃爍；接收端訂閱後即時解析，收到數據閃燈，溫度過熱自動狂閃示警！ |
| **主題監聽** | [mqtt_subscriber_monitor.py](file:///c:/Nono/Pico2%20W/mqtt_subscriber_monitor.py) | **特定主題訊息監聽與通訊列顯示** | MQTT 訂閱監聽 (MicroPython) | 專為抓取 MQTTGO 特定主題所設計！只要雲端有新訊息發布，Pico 2 W 立刻在 Thonny 通訊列（Shell）格式化排版顯示，板載 LED 同步閃爍提示！ |
| **主題發布** | [mqtt_publisher.py](file:///c:/Nono/Pico2%20W/mqtt_publisher.py) | **向特定主題發布訊息程式** | MQTT 訊息發布 (互動/自動) | 專為向 MQTTGO 特定主題發布訊息設計！支援在 Thonny 通訊列直接輸入任意文字/JSON 即時發送，亦可切換為定時自動感測發布！ |
| **邊緣伺服器** | [lab2_web_server.py](file:///c:/Nono/Pico2%20W/lab2_web_server.py) | **Pico 2 W 邊緣微型 Web Server** | HTTP / RESTful API / AJAX | Pico 2 W 自主在 Port 80 架設 Web Server！手機或電腦瀏覽器輸入 Pico IP 即可開啟現代深色儀表板，即時監控晶片溫度與 Uptime，點擊按鈕無線遙控實體板載綠燈！ |
| **Wi-Fi雷達** | [lab2_wifi_radar.py](file:///c:/Nono/Pico2%20W/lab2_wifi_radar.py) | **Pico 2 W 邊緣 Web Server：Wi-Fi 空間雷達探測儀** | HTTP / RESTful / CYW43439 射頻掃描 | 方案 10 核心實作！Pico 2 W 在 Port 80 架設雷達伺服器，手機或電腦開啟科幻旋轉雷達盤，即時掃描空氣中所有 Wi-Fi 熱點、dBm 強度、2.4GHz 頻譜擁塞度並推薦最佳連線頻道！ |
| **實驗 2** | [lab2_gov_opendata.py](file:///c:/Nono/Pico2%20W/lab2_gov_opendata.py) | **台灣政府開放資料 API 串接** | HTTPS GET / RESTful / JSON 解析 | 串接 [data.gov.tw](https://data.gov.tw/) 政府開放資料平臺 (氣象署測站 API)。以 StationId 精準過濾取得 2KB 輕量 JSON，解析即時天氣與降雨，下雨自動觸發板載 LED 快閃警報！ |

---

### 🌐 邊緣微型 Web Server (lab2_web_server.py) 操作流程
專為 1 小時實作設計，讓 Pico 2 W 搖身一變成為微型 Edge Server：
1. **執行程式**：在 Thonny 執行 [`lab2_web_server.py`](file:///c:/Nono/Pico2%20W/lab2_web_server.py)。
2. **開啟網頁**：連上 Wi-Fi 後，Shell 印出 `http://192.168.x.x`，用電腦或手機瀏覽器開啟該 IP 網址。
3. **即時儀表板**：
   - 瀏覽器呈現深色質感儀表板，顯示 RP2350 內部溫度與運行時間。
   - 手指用力捏住 RP2350 晶片 10 秒，頁面透過 AJAX 每 2 秒自動刷新，親眼見證數值飆升！
4. **雙向無線點燈**：
   - 點擊網頁上的「💡 開燈 (ON)」、「💤 關燈 (OFF)」、「🔄 切換 (TOGGLE)」或「⚡ 快閃 3 次」，實體板載綠色 LED 即刻精準響應！
5. **RESTful API 支援**：手動輸入 `http://192.168.x.x/api/status` 可直接取得純 JSON 格式設備狀態。

---

### 📡 邊緣 Web Server：Wi-Fi 空間雷達探測儀 (lab2_wifi_radar.py) 操作流程
專為 1 小時實作設計 (方案 10)，挖掘板載 CYW43439 無線射頻晶片底層掃描能力：
1. **執行程式**：在 Thonny 執行 [`lab2_wifi_radar.py`](file:///c:/Nono/Pico2%20W/lab2_wifi_radar.py)。
2. **開啟雷達儀表板**：連上 Wi-Fi 後，Shell 印出 `http://192.168.x.x`，用電腦或手機瀏覽器開啟該 IP 網址。
3. **即時雷達與空間掃描**：
   - 瀏覽器呈現高科技科幻旋轉雷達盤，自動調用 CYW43439 底層進行空間 Wi-Fi 掃描。
   - 列出四周所有熱點名稱 (SSID)、MAC 地址 (BSSID)、信號強度 (RSSI/dBm)、訊號品質長條圖與加密模式。
4. **手掌物理遮蔽實證**：
   - 用手掌緊緊包覆 Pico 2 W 天線端再次掃描，親眼見證數值衰減 15 ~ 25 dBm，實證人體水分對 2.4GHz 電磁波的吸收！
5. **2.4GHz 頻譜壅塞分析與最佳頻道推薦**：
   - 即時運算 Channel 1 ~ 13 佔用率，演算法自動評估 1/6/11 三大互不干擾頻道，推薦全場最順暢頻段！
6. **RESTful API 支援**：手動輸入 `http://192.168.x.x/api/scan` 可直接取得純 JSON 格式空間掃描數據。

---

### 📡 實驗 1：MQTTGO.io 雙向通訊操作流程
1. 執行 [lab1_mqttgo_iot.py](file:///c:/Nono/Pico2%20W/lab1_mqttgo_iot.py)，終端機將印出裝置專屬的：
   - 溫度發布主題：`pico2w/<DEVICE_ID>/temp`
   - LED 控制主題：`pico2w/<DEVICE_ID>/led`
2. 打開瀏覽器前往 [https://mqttgo.io/](https://mqttgo.io/)：
   - 在**訂閱主題**輸入 `pico2w/<DEVICE_ID>/temp`，即可每 5 秒看到板載溫度更新。
   - 在**發布主題**輸入 `pico2w/<DEVICE_ID>/led`，訊息填入 `on`、`off` 或 `toggle`，點擊發布即可遠端即時操控 Pico！

---

### 📡 雙機配對：Pico 2 W 傳送端與接收端實戰流程
專為兩塊 Pico 2 W（或兩組學員分工）設計的獨立收發程式：
1. **傳送端 (Pico A)**：
   - 執行 [`lab1_sender.py`](file:///c:/Nono/Pico2%20W/lab1_sender.py)
   - 每 3 秒讀取 RP2350 內部溫度，封裝為 JSON 格式（`seq`, `temp`, `status`）發布到 `pico2w/pair/data`。
   - 每發送一筆資料，板載 LED 快速閃爍 1 次，提供直覺的「資料射出」反饋！
2. **接收端 (Pico B)**：
   - 執行 [`lab1_receiver.py`](file:///c:/Nono/Pico2%20W/lab1_receiver.py)
   - 訂閱相同主題 `pico2w/pair/data`，非阻塞靜默監聽。
   - 一收到封包，Shell 即時印出來源設備與溫度，並觸發板載 LED 閃爍連動！
   - 當傳送端被手指加熱（溫度 > 30°C），接收端板載 LED 自動連續快閃示警！
   - 亦支援接收 `on`、`off`、`toggle`、`blink` 等指令。

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
  6. ⏱️ **MQTT 1 小時課堂規劃專區**：完整收錄 60 分鐘課堂時間軸 (00-10m 破冰、10-20m Wi-Fi唯一識別、20-35m 溫度發布升溫實證、35-50m 雙向遙控LED、50-55m 跨組互控大挑戰、55-60m 防呆與Rubric評量檢核)。
