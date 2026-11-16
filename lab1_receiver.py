# lab1_receiver.py - Pico 2 W 專屬接收端 (MQTT Subscriber)
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 + CYW43439)
# 零外接零件：使用板載綠色 LED ("LED") 進行實體物理接收反饋
# 運作說明：本程式作為「接收端」，訂閱雲端 Broker 的配對主題。
#           當收到傳送端 (lab1_sender.py 或 網頁) 發布的封包時，即時在 Shell 顯示並觸發板載 LED 燈連動！

import time
import network
import machine
from machine import Pin
import ubinascii
import ujson
from umqtt.simple import MQTTClient

# ==========================================
# 1. Wi-Fi 連線設定 (請填入您的 2.4GHz Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請替換為您的 Wi-Fi 名稱 (僅支援 2.4GHz)
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請替換為您的 Wi-Fi 密碼

# ==========================================
# 2. 硬體引腳初始化
# ==========================================
led = Pin("LED", Pin.OUT)       # 板載綠色 LED (接收訊號連動反饋)

# ==========================================
# 3. MQTT 配對頻道與伺服器設定
# ==========================================
MQTT_BROKER = "mqttgo.io"       # 台灣在地開源免費 MQTT Broker
MQTT_PORT = 1883                # 標準 MQTT TCP 連接埠

# 取得硬體唯一 ID 作為接收端身分辨識
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
CLIENT_ID = f"pico2w_recv_{DEVICE_ID[:6]}"

# 📡 【核心配對主題】：必須與 lab1_sender.py 的 PAIR_TOPIC 完全一致！
# 課堂分組提示：可將 "pair" 改為組別，例如 "pico2w/team1/data"
PAIR_TOPIC = "pico2w/pair/data"

# 接收封包累計計數器
recv_count = 0

def blink_led(times=2, duration=0.08):
    """板載 LED 快速閃爍，提供實體物理接收反饋"""
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
        print(f"📡 [接收端] 正在連線至 Wi-Fi: {WIFI_SSID} ...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(0.5)
            timeout -= 1
            print(".", end="")
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"\n✅ [接收端] Wi-Fi 連線成功！本機 IP: {ip}")
        return True
    else:
        print("\n❌ [錯誤] Wi-Fi 連線逾時，請確認帳密與 2.4GHz 頻段！")
        return False

def on_message_received(topic, msg):
    """當 Broker 下發訂閱主題的訊息時觸發的回呼函式"""
    global recv_count
    recv_count += 1
    
    topic_str = topic.decode("utf-8")
    raw_str = msg.decode("utf-8").strip()

    print("\n" + "-" * 60)
    print(f"📥 [收到封包 #{recv_count:03d}] 主題: {topic_str}")

    # 嘗試以 JSON 解析封包
    try:
        data = ujson.loads(raw_str)
        sender = data.get("sender", "未知來源")
        seq = data.get("seq", "?")
        temp = data.get("temp", None)
        status = data.get("status", "NORMAL")

        print(f"   來源設備: {sender} | 發送序號: #{seq}")
        if temp is not None:
            print(f"   晶片溫度: {temp} °C | 狀態: {status}")

        # 實體反饋：若溫度過熱 (>30°C) 快速快閃 4 次警告，一般封包閃 2 次
        if status == "HOT" or (temp is not None and temp > 30.0):
            print("   🚨 收到晶片過熱警報！板載 LED 快閃示警！")
            blink_led(4, 0.06)
        else:
            blink_led(2, 0.08)

    except Exception:
        # 若非 JSON 格式（例如使用者從網頁直接輸入純文字指令）
        cmd = raw_str.lower()
        print(f"   文字指令內容: {raw_str}")

        if cmd in ("on", "1", "true"):
            led.on()
            print("   💡 板載 LED 切換為：開啟 (ON)")
        elif cmd in ("off", "0", "false"):
            led.off()
            print("   💤 板載 LED 切換為：關閉 (OFF)")
        elif cmd == "toggle":
            led.toggle()
            print("   🔄 板載 LED 狀態已切換")
        elif cmd == "blink":
            print("   ⚡ 執行快閃指令")
            blink_led(3, 0.12)
        else:
            # 一般未知文字，閃爍 1 次表示收到
            blink_led(1, 0.1)

    print("-" * 60)

def main():
    print("=" * 60)
    print("📥 Pico 2 W 專屬接收端 (MQTT Subscriber)")
    print(f"🆔 裝置識別: {CLIENT_ID}")
    print(f"📡 訂閱配對主題: {PAIR_TOPIC}")
    print("=" * 60)

    if not connect_wifi():
        return

    print(f"\n正在連線至 MQTT Broker ({MQTT_BROKER}:{MQTT_PORT}) ...")
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    client.set_callback(on_message_received)

    try:
        client.connect()
        print("✅ MQTT Broker 連線成功！")

        # 訂閱配對主題
        client.subscribe(PAIR_TOPIC)
        print(f"📡 已成功訂閱主題: {PAIR_TOPIC}")
        print("⏳ 正在靜默監聽中，等待傳送端資料或指令抵達...\n")

        while True:
            # 非阻塞檢查是否有來自雲端的訂閱訊息
            client.check_msg()
            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n使用者手動中斷接收。")
    except Exception as e:
        print(f"\n❌ 接收異常: {e}")
    finally:
        try:
            client.disconnect()
            print("MQTT 連線已關閉。")
        except:
            pass

if __name__ == "__main__":
    main()
