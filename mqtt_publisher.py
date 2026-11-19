# mqtt_publisher.py - Pico 2 W 專屬 MQTTGO 特定主題訊息發布程式
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 / RP2040 + CYW43439)
# 運作環境：Thonny IDE + MicroPython
# 功能說明：連線至台灣 MQTTGO.io，向您指定的「特定主題 (Topic)」發布訊息。
#           支援「互動手動輸入發布」與「定時自動感測發布」兩種模式！
# 設計特色：單檔即跑 (All-in-One Standalone)，內建輕量 MQTTClient 實作，免額外安裝 umqtt 模組庫！

import time
import network
import machine
from machine import Pin, ADC
import ubinascii
import ujson

# ==========================================
# 0. 內建輕量 MQTTClient (若無安裝 umqtt 自動切換，保證絕不報錯)
# ==========================================
try:
    from umqtt.simple import MQTTClient
except ImportError:
    import usocket as socket
    import ustruct as struct

    class MQTTException(Exception): pass
    class MQTTClient:
        def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0, ssl=False, ssl_params={}):
            if port == 0: port = 8883 if ssl else 1883
            self.client_id = client_id; self.sock = None; self.server = server; self.port = port
            self.ssl = ssl; self.ssl_params = ssl_params; self.pid = 0; self.cb = None
            self.user = user; self.pswd = password; self.keepalive = keepalive
            self.lw_topic = None; self.lw_msg = None; self.lw_qos = 0; self.lw_retain = False
        def _send_str(self, s):
            self.sock.write(struct.pack("!H", len(s))); self.sock.write(s)
        def _recv_len(self):
            n = 0; sh = 0
            while 1:
                res = self.sock.read(1); b = res[0]; n |= (b & 0x7f) << sh
                if not (b & 0x80): break
                sh += 7
            return n
        def set_callback(self, f): self.cb = f
        def connect(self, clean_session=True):
            self.sock = socket.socket()
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            if self.ssl:
                import ussl; self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)
            premsg = bytearray(b"\x10\0\0\0\0\0"); msg = bytearray(b"\x04MQTT\x04\x02\0\0")
            sz = 10 + 2 + len(self.client_id); msg[6] = clean_session << 1
            if self.user is not None: sz += 2 + len(self.user) + 2 + len(self.pswd); msg[6] |= 0xC0
            if self.keepalive:
                assert self.keepalive < 65536; msg[7] = self.keepalive >> 8; msg[8] = self.keepalive & 0x00FF
            i = 1
            while sz > 0x7f: premsg[i] = (sz & 0x7f) | 0x80; sz >>= 7; i += 1
            premsg[i] = sz; self.sock.write(premsg[:i + 2]); self.sock.write(msg)
            self._send_str(self.client_id)
            if self.user is not None: self._send_str(self.user); self._send_str(self.pswd)
            resp = self.sock.read(4)
            assert resp[0] == 0x20 and resp[1] == 0x02
            if resp[3] != 0: raise MQTTException(resp[3])
            return resp[2] & 1
        def disconnect(self): self.sock.write(b"\xe0\0"); self.sock.close()
        def ping(self): self.sock.write(b"\xc0\0")
        def publish(self, topic, msg, retain=False, qos=0):
            pkt = bytearray(b"\x30\0\0\0"); pkt[0] |= qos << 1 | retain
            sz = 2 + len(topic) + len(msg)
            i = 1
            while sz > 0x7f: pkt[i] = (sz & 0x7f) | 0x80; sz >>= 7; i += 1
            pkt[i] = sz; self.sock.write(pkt[:i + 1]); self._send_str(topic); self.sock.write(msg)

# ==========================================
# 1. Wi-Fi 連線設定 (請替換為您的 Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請填入 2.4GHz Wi-Fi 名稱
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請填入 Wi-Fi 密碼

# ==========================================
# 2. MQTT 伺服器與「特定發布主題」設定
# ==========================================
MQTT_BROKER = "mqttgo.io"       # 台灣在地開源免費 Broker
MQTT_PORT = 1883                # 標準 TCP 連接埠

# 🎯 【您要發布的特定主題】（請與接收端或監聽程式設定一致）
# 例如: "pico2w/my_topic"、"myhome/sensor/temp"、"school/notice"
TARGET_TOPIC = "pico2w/my_topic"

# ==========================================
# 3. 發布模式設定
# ==========================================
# "interactive"：互動鍵盤模式（在 Thonny 通訊列輸入文字，按 Enter 發送）
# "auto"        ：定時自動模式（每隔 X 秒自動讀取晶片溫度並發布）
PUBLISH_MODE = "interactive"

# 定時自動模式的發送間隔 (秒)
AUTO_INTERVAL = 3

# ==========================================
# 4. 硬體引腳初始化
# ==========================================
led = Pin("LED", Pin.OUT)       # 發送時快閃反饋
temp_sensor = ADC(4)            # RP2350 內部溫度感測器

DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
CLIENT_ID = f"pico2w_pub_{DEVICE_ID[:6]}"

def blink_led(times=1, duration=0.1):
    """板載 LED 閃爍反饋"""
    for _ in range(times):
        led.on()
        time.sleep(duration)
        led.off()
        time.sleep(duration)

def read_temperature():
    """讀取 RP2350 內部溫度感測器 (°C)"""
    conversion_factor = 3.3 / 65535
    reading = temp_sensor.read_u16() * conversion_factor
    return 27 - (reading - 0.706) / 0.001721

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
        print("\n❌ [錯誤] Wi-Fi 連線逾時！請確認帳密與 2.4GHz 頻段。")
        return False

def interactive_mode(client):
    """【模式 1】互動輸入模式：在 Thonny 通訊列輸入訊息，按 Enter 發布"""
    print("\n" + "═" * 65)
    print("⌨️  【進入互動鍵盤發布模式】")
    print(f"🎯 目標發布主題: {TARGET_TOPIC}")
    print("💡 使用方式：在下方直接輸入任何文字或 JSON，按 Enter 立即發送！")
    print("   (輸入 'q' 或 'exit' 可結束程式)")
    print("═" * 65 + "\n")
    
    pub_count = 0
    while True:
        try:
            # 從 Thonny 通訊列讀取使用者輸入
            user_msg = input("👉 請輸入要發布的訊息: ").strip()
            
            if not user_msg:
                continue
                
            if user_msg.lower() in ("q", "exit", "quit"):
                print("👋 離開互動發布模式。")
                break
                
            pub_count += 1
            
            # 發布訊息到 MQTTGO 特定主題
            client.publish(TARGET_TOPIC, user_msg)
            
            # 實體物理反饋：板載 LED 快閃一下
            blink_led(1, 0.12)
            
            print(f"   ✅ [第 #{pub_count:03d} 筆發送成功]")
            print(f"      主題: {TARGET_TOPIC}")
            print(f"      內容: {user_msg}\n")
            
        except KeyboardInterrupt:
            print("\n🛑 使用者中斷輸入。")
            break

def auto_mode(client):
    """【模式 2】定時自動發布模式：每隔 AUTO_INTERVAL 秒自動發布"""
    print("\n" + "═" * 65)
    print("⏱️  【進入定時自動感測發布模式】")
    print(f"🎯 目標發布主題: {TARGET_TOPIC}")
    print(f"⏳ 每隔 {AUTO_INTERVAL} 秒自動讀取板載溫度並發布...")
    print("   (按 Ctrl+C 可停止發布)")
    print("═" * 65 + "\n")
    
    seq = 0
    while True:
        try:
            seq += 1
            temp = read_temperature()
            
            # 封裝為標準 JSON 格式
            payload = {
                "seq": seq,
                "sender": CLIENT_ID,
                "temp": round(temp, 2),
                "timestamp": time.time()
            }
            msg_str = ujson.dumps(payload)
            
            # 發布訊息
            client.publish(TARGET_TOPIC, msg_str)
            blink_led(1, 0.08)
            
            print(f"📤 [已送出 #{seq:03d}] 溫度: {temp:.2f} °C -> 主題: {TARGET_TOPIC}")
            time.sleep(AUTO_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n🛑 定時發布已停止。")
            break

def main():
    print("\n" + "=" * 65)
    print("🚀 Pico 2 W - MQTTGO 特定主題訊息發布程式")
    print("=" * 65)
    
    # 1. 連線 Wi-Fi
    if not connect_wifi():
        return
        
    # 2. 建立 MQTT 客戶端
    print(f"\n正在連線至 MQTTGO 伺服器: {MQTT_BROKER}:{MQTT_PORT} ...")
    print(f"客戶端名稱 (Client ID): {CLIENT_ID}")
    
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
    
    try:
        client.connect()
        print("✅ MQTT Broker 連線成功！")
        
        # 3. 根據設定進入相應模式
        if PUBLISH_MODE == "interactive":
            interactive_mode(client)
        else:
            auto_mode(client)
            
    except KeyboardInterrupt:
        print("\n🛑 程式已停止。")
    except Exception as e:
        print(f"\n❌ 發布過程異常: {e}")
    finally:
        try:
            client.disconnect()
            print("MQTT 連線已關閉。")
        except:
            pass

if __name__ == "__main__":
    main()

