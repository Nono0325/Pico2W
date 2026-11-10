# lab1_mqttgo_iot.py - 實驗 1：MQTT 物聯網雙向雲端通訊 (MQTTGO.io 台灣在地 Broker)
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 + CYW43439)
# 零外接零件：使用 RP2350 內部溫度感測器 (ADC 4) 與板載 LED ("LED")

import time
import network
import machine
from machine import Pin, ADC
import ubinascii
from umqtt.simple import MQTTClient

# ==========================================
# 1. Wi-Fi 連線設定 (單檔即跑，直接在此填寫)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請替換為您的 2.4GHz Wi-Fi 名稱
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請替換為您的 Wi-Fi 密碼

# ==========================================
# 2. 硬體引腳與感測器初始化
# ==========================================
led = Pin("LED", Pin.OUT)
temp_sensor = ADC(4)  # RP2350 內部溫度感測器通道

# ==========================================
# 3. MQTT 伺服器與主題設定 (MQTTGO.io)
# ==========================================
# 依據 Pico 2 W 硬體唯一 ID 產生唯一 Client ID 與專屬主題，保證不與他人衝突
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
MQTT_BROKER = "mqttgo.io"  # 台灣在地開源免費 MQTT Broker
MQTT_PORT = 1883           # 標準 MQTT TCP 連接埠

TOPIC_PUB_TEMP = f"pico2w/{DEVICE_ID}/temp"  # Pico 定期發布溫度的主題
TOPIC_SUB_LED  = f"pico2w/{DEVICE_ID}/led"   # Pico 訂閱接收控制指令的主題

def read_temperature():
    """讀取 RP2350 內部溫度感測器 (攝氏 °C)"""
    conversion_factor = 3.3 / 65535
    reading = temp_sensor.read_u16() * conversion_factor
    # RP2350 內部溫度計算公式：27 - (Vbe - 0.706) / 0.001721
    return 27 - (reading - 0.706) / 0.001721

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
        print("💡 提示：本實驗為 MQTT 客戶端（非 Web 伺服器），請勿在瀏覽器開啟此 IP。")
        return True
    else:
        print("\n[錯誤] Wi-Fi 連線逾時，請檢查 SSID 與密碼！")
        return False

def on_message_received(topic, msg):
    """當 MQTT Broker 下發訊息至訂閱主題時觸發的回呼函式"""
    topic_str = topic.decode("utf-8")
    msg_str = msg.decode("utf-8").strip().lower()
    print(f"\n📩 [MQTT 收到指令] 主題: {topic_str} | 內容: {msg_str}")
    
    if msg_str in ("on", "1", "true"):
        led.on()
        print("💡 板載 LED 已開啟 (ON)")
    elif msg_str in ("off", "0", "false"):
        led.off()
        print("💤 板載 LED 已關閉 (OFF)")
    elif msg_str == "toggle":
        led.toggle()
        print("🔄 板載 LED 狀態已切換")
    else:
        print(f"❓ 未知指令: {msg_str} (支援指令: on, off, toggle)")

def main():
    print("=" * 65)
    print("🚀 實驗 1：Pico 2 W - MQTT 雙向雲端通訊 (MQTTGO.io)")
    print("=" * 65)
    
    if not connect_wifi():
        return
        
    client_id = f"pico2w_{DEVICE_ID}"
    print(f"\n正在連線至 MQTT Broker: {MQTT_BROKER}:{MQTT_PORT} ...")
    print(f"裝置專屬 Client ID: {client_id}")
    
    # 建立 MQTT 客戶端
    client = MQTTClient(client_id, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    client.set_callback(on_message_received)
    
    try:
        client.connect()
        print("✅ MQTT Broker 連線成功！")
        
        # 訂閱控制主題
        client.subscribe(TOPIC_SUB_LED)
        print(f"📡 已訂閱控制主題: {TOPIC_SUB_LED}")
        
        # 輸出網頁操作指引
        print("\n" + "=" * 65)
        print("🌐 【重要：請打開 MQTTGO.io 網頁進行遠端控制】")
        print("👉 請在電腦或手機瀏覽器開啟： https://mqttgo.io/")
        print("   （⚠️ 提醒：請勿開啟 192.168.x.x，本實驗需在 MQTTGO 網頁上操作）")
        print("1. 接收溫度數據：")
        print(f"   在「訂閱主題」欄位貼上： {TOPIC_PUB_TEMP}")
        print("   點擊「訂閱」，每 5 秒即可看見 Pico 回傳之即時溫度！")
        print("2. 遠端控制 LED 燈：")
        print(f"   在「發布主題」欄位貼上： {TOPIC_SUB_LED}")
        print("   在「發布訊息」填入： on 、 off 或 toggle，點擊「發布」！")
        print("=" * 65 + "\n")
        
        last_pub_time = 0
        while True:
            # 非阻塞檢查是否有來自雲端的訂閱訊息
            client.check_msg()
            
            # 每 5 秒發布一次當前板載溫度
            now = time.time()
            if now - last_pub_time >= 5:
                temp = read_temperature()
                temp_msg = f"{temp:.2f}"
                client.publish(TOPIC_PUB_TEMP, temp_msg)
                print(f"📤 [MQTT 發布] 溫度: {temp_msg} °C -> 主題: {TOPIC_PUB_TEMP}")
                last_pub_time = now
                
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n使用者中斷程式執行。")
    except Exception as e:
        print(f"\n❌ MQTT 運行異常: {e}")
    finally:
        try:
            client.disconnect()
            print("MQTT 連線已關閉。")
        except:
            pass

if __name__ == "__main__":
    main()

