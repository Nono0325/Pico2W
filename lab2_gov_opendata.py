# lab2_gov_opendata.py - 實驗 2：台灣政府開放資料 (data.gov.tw) API 串接與智慧實體警報
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 + CYW43439)
# 零外接零件：使用板載 LED ("LED") 作為智慧天候燈號警報器
# 資料來源：政府資料開放平臺 (data.gov.tw) / 中央氣象署開放資料 API (資料集 O-A0003-001)

import time
import network
import urequests
import gc
from machine import Pin

# ==========================================
# 1. Wi-Fi 連線設定 (單檔即跑，直接在此填寫)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請替換為您的 2.4GHz Wi-Fi 名稱
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請替換為您的 Wi-Fi 密碼

# ==========================================
# 2. 硬體引腳初始化
# ==========================================
led = Pin("LED", Pin.OUT)

# ==========================================
# 3. 台灣政府資料開放平臺 API 設定
# ==========================================
# 常用氣象測站代碼 (StationId)：
# 466920: 臺北 | 466940: 基隆 | 467490: 臺中 | 467410: 臺南 | 467440: 高雄 | 466990: 花蓮
STATION_ID = "466920"  # 預設：臺北測站
STATION_NAME_DESC = "臺北"

# 政府開放資料平臺標準通用授權金鑰 (免個人註冊即可公開調用)
GOV_AUTH_KEY = "rdec-key-123-45678-011121314"

# 透過 StationId 進行精準過濾，回傳僅約 2KB 輕量 JSON，徹底避免 MicroPython 記憶體溢位 (MemoryError)
API_URL = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001?Authorization={GOV_AUTH_KEY}&StationId={STATION_ID}"

def connect_wifi():
    """連線至 Wi-Fi 基地台"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"正在連線至 Wi-Fi: {WIFI_SSID} ...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(0.5)
            timeout -= 1
            print(".", end="")
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"\n[成功] Wi-Fi 已連線！本機 IP: {ip}")
        print("💡 提示：本實驗為政府 API 客戶端（非 Web 伺服器），請勿在瀏覽器開啟此 IP。")
        return True
    else:
        print("\n[錯誤] Wi-Fi 連線逾時，請檢查 SSID 與密碼！")
        return False

def flash_led(times=3, delay=0.15):
    """LED 告警快閃 (下雨或惡劣天候提示)"""
    for _ in range(times):
        led.on()
        time.sleep(delay)
        led.off()
        time.sleep(delay)

def fetch_taiwan_opendata():
    """向政府開放資料 API 發送 HTTP GET 請求並解析即時天氣"""
    gc.collect()  # 請求前主動回收記憶體
    print(f"\n🌐 發送 HTTPS GET 至政府開放資料平臺...")
    print(f"🔗 測站代號: {STATION_ID} ({STATION_NAME_DESC})")
    
    response = None
    try:
        headers = {"User-Agent": "Pico2W-OpenDataClient/1.0"}
        response = urequests.get(API_URL, headers=headers)
        
        if response.status_code == 200:
            print("✅ 成功取得 API 回應 (HTTP 200 OK)！解析 JSON 中...")
            data = response.json()
            
            # 解析 CWA Datastore 結構
            records = data.get("records", {}).get("Station", [])
            if not records:
                print("⚠️ 未找到該測站資料，請確認測站代碼。")
                return
                
            station = records[0]
            station_name = station.get("StationName", STATION_NAME_DESC)
            obs_time = station.get("ObsTime", {}).get("DateTime", "未知")
            
            weather_elem = station.get("WeatherElement", {})
            weather_desc = weather_elem.get("Weather", "未知")
            temp = float(weather_elem.get("AirTemperature", 0.0))
            humidity = weather_elem.get("RelativeHumidity", "未知")
            
            # 取得即時降雨量
            precip = 0.0
            now_elem = weather_elem.get("Now", {})
            if isinstance(now_elem, dict) and "Precipitation" in now_elem:
                try:
                    precip = float(now_elem.get("Precipitation", 0.0))
                except:
                    precip = 0.0
                    
            # 顯示解析後的即時開放資料
            print("-" * 50)
            print(f"🏛️ 【政府開放資料即時天氣觀測】")
            print(f"📍 觀測地點：{station_name} (測站: {STATION_ID})")
            print(f"🕒 觀測時間：{obs_time}")
            print(f"🌤️ 天氣狀況：{weather_desc}")
            print(f"🌡️ 目前氣溫：{temp:.1f} °C")
            print(f"💧 相對濕度：{humidity} %")
            print(f"🌧️ 累積降雨：{precip} mm")
            print("-" * 50)
            
            # ==========================================
            # 4. 硬體實體連動邏輯 (智慧燈號提示)
            # ==========================================
            is_raining = ("雨" in weather_desc) or (precip > 0.0)
            
            if is_raining:
                print("🚨 [天候警報] 偵測到目前有降雨！出門請攜帶雨具 ☔")
                print("💡 板載 LED 連續快閃警示...")
                flash_led(times=6, delay=0.1)
            else:
                print("✨ [天候良好] 目前無雨，天氣舒適！")
                # 天氣良好時，LED 恆亮 1.5 秒表示正常運行
                led.on()
                time.sleep(1.5)
                led.off()
                
        else:
            print(f"❌ API 請求失敗，狀態碼: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 擷取開放資料時發生錯誤: {e}")
    finally:
        if response:
            response.close()
        gc.collect()

def main():
    print("=" * 65)
    print("🚀 實驗 2：Pico 2 W - 台灣政府開放資料 (data.gov.tw) API 串接")
    print("=" * 65)
    
    if not connect_wifi():
        return
        
    print("\n系統初始化完成，將每 60 秒自動向政府開放資料平臺更新一次天候資料...")
    
    # 執行第一次查詢
    fetch_taiwan_opendata()
    
    while True:
        try:
            # 每 60 秒定期向政府 API 輪詢更新 (符合開放資料建議呼叫間隔)
            for i in range(60, 0, -10):
                time.sleep(10)
                print(f"⏳ 距離下次政府資料更新尚餘: {i-10} 秒...")
            fetch_taiwan_opendata()
        except KeyboardInterrupt:
            print("\n使用者停止程式執行。")
            led.off()
            break

if __name__ == "__main__":
    main()

