# mqtt_subscriber_monitor.py - Pico 2 W 專屬 MQTTGO 特定主題訊息監聽與通訊列顯示程式
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 / RP2040 + CYW43439)
# 運作環境：Thonny IDE + MicroPython
# 功能說明：連線至台灣 MQTTGO.io，訂閱您指定的「特定主題 (Topic)」。
#           當雲端有新訊息發布時，即時在 Thonny 通訊列 (Shell) 格式化印出，並連動板載 LED 閃爍提示！

import time
import network
import machine
from machine import Pin
import ubinascii
import ujson
from umqtt.simple import MQTTClient

# ==========================================
# 1. Wi-Fi 連線設定 (請替換為您的 Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請填入 2.4GHz Wi-Fi 名稱
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請填入 Wi-Fi 密碼

# ==========================================
# 2. MQTT 伺服器與「特定主題」設定
# ==========================================
MQTT_BROKER = "mqttgo.io"       # 台灣在地開源免費 Broker
MQTT_PORT = 1883                # 標準 TCP 連接埠

# 🎯 【您要抓取監聽的特定主題】（可自由修改為任何您想監聽的主題）
# 例如: "myhome/sensor/temp"、"school/classA/notice"、"pico2w/demo/msg"
TARGET_TOPIC = "pico2w/my_topic"

# ==========================================
# 3. 硬體引腳初始化
# ==========================================
# Pico 2 W 板載綠色 LED (收到訊息時閃爍提示)
led = Pin("LED", Pin.OUT)

# 依硬體晶片序號生成唯一的 Client ID，確保連線不被擠下線
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
CLIENT_ID = f"pico2w_monitor_{DEVICE_ID[:6]}"

# 全域統計變數
message_count = 0
start_time = time.time()

def blink_led(times=1, duration=0.15):
    """板載 LED 閃爍反饋"""
    for _ in range(times):
        led.on()
        time.sleep(duration)
        led.off()
        time.sleep(duration)

def connect_wifi():
    """連線至 Wi-Fi 基地台"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("=" * 65)
        print(f"📡 [Wi-Fi] 正在連線至: {WIFI_SSID} ...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 25
        while not wlan.isconnected() and timeout > 0:
            time.sleep(0.5)
            timeout -= 1
            print(".", end="")
    
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"\n✅ [Wi-Fi] 連線成功！本機 IP: {ip}")
        return True
    else:
        print("\n❌ [錯誤] Wi-Fi 連線逾時！請確認：")
        print("   1. SSID 與密碼是否正確")
        print("   2. 是否為 2.4GHz 頻段 (Pico 2 W 不支援 5GHz Wi-Fi)")
        return False

def on_message_received(topic, msg):
    """當 MQTT Broker 下發訊息至特定主題時，觸發此回呼函式在通訊列印出"""
    global message_count
    message_count += 1
    
    topic_str = topic.decode("utf-8")
    raw_str = msg.decode("utf-8").strip()
    elapsed = time.time() - start_time
    
    # 物理反饋：板載 LED 亮起閃爍，表示抓到新訊息
    blink_led(1, 0.15)
    
    # 在 Thonny 通訊列 (Shell) 格式化印出收到之訊息
    print("\n" + "╔" + "═" * 63 + "╗")
    print(f"║ 📬 【通訊列收到新訊息 #{message_count:04d}】 (運作時間: {elapsed} 秒)")
    print("╠" + "═" * 63 + "╣")
    print(f"║ 🏷️  主題 (Topic)   : {topic_str}")
    print(f"║ 📏 內容長度        : {len(raw_str)} Bytes")
    print("╟" + "─" * 63 + "╢")
    
    # 嘗試判斷是否為 JSON 格式，若是則排版展示，若否則直接顯示純文字
    try:
        json_data = ujson.loads(raw_str)
        print("║ 📦 訊息格式        : [標準 JSON 結構]")
        print("║ 📄 訊息內容如下    :")
        for key, val in json_data.items():
            print(f"║    ▶ {key}: {val}")
    except Exception:
        print("║ 📦 訊息格式        : [純文字 / 字串]")
        print(f"║ 📄 訊息內容        : {raw_str}")
        
    print("╚" + "═" * 63 + "╝\n")

def main():
    print("\n" + "=" * 65)
    print("🚀 Pico 2 W - MQTTGO 特定主題訊息監聽程式")
    print("=" * 65)
    
    # 1. 連線 Wi-Fi
    if not connect_wifi():
        return
        
    # 2. 建立 MQTT 客戶端
    print(f"\n正在連線至 MQTTGO 伺服器: {MQTT_BROKER}:{MQTT_PORT} ...")
    print(f"客戶端名稱 (Client ID): {CLIENT_ID}")
    
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    # 綁定接收訊息時的回呼函式
    client.set_callback(on_message_received)
    
    try:
        client.connect()
        print("✅ MQTT Broker 連線成功！")
        
        # 3. 訂閱使用者指定的特定主題
        client.subscribe(TARGET_TOPIC)
        print(f"📡 【已成功訂閱特定主題】: {TARGET_TOPIC}")
        
        # 4. 印出操作指引，方便使用者立刻用瀏覽器或手機發送測試
        print("\n" + "-" * 65)
        print("🌐 【如何測試發送訊息給 Pico 2 W？】")
        print("👉 請用電腦或手機瀏覽器開啟： https://mqttgo.io/")
        print("1. 在網頁中的「發布主題 (Topic)」填入：")
        print(f"   {TARGET_TOPIC}")
        print("2. 在「發布訊息 (Message)」輸入任何想傳送的文字或 JSON，例如：")
        print("   Hello Pico 2 W!")
        print("   或 {\"msg\": \"早安\", \"temp\": 25.5}")
        print("3. 點擊「發布」，Pico 2 W 通訊列將會立即格式化顯示訊息！")
        print("-" * 65 + "\n")
        print(f"⏳ 正在監聽中... (隨時等待來自 [{TARGET_TOPIC}] 的新訊息)")
        
        # 5. 主迴圈：非阻塞監聽 Broker 訊息
        while True:
            # 檢查是否有來自雲端主題的訊息抵達 (Non-blocking)
            client.check_msg()
            time.sleep(0.05)  # 稍微休眠，釋放 CPU 資源
            
    except KeyboardInterrupt:
        print("\n🛑 使用者手動中斷程式。")
    except Exception as e:
        print(f"\n❌ 監聽過程發生異常: {e}")
    finally:
        try:
            client.disconnect()
            print("MQTT 連線已正常釋放。")
        except:
            pass

if __name__ == "__main__":
    main()
