# lab1_sender.py - Pico 2 W 專屬傳送端 (MQTT Publisher)
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 + CYW43439)
# 零外接零件：使用 RP2350 內部溫度感測器 (ADC 4) 與板載 LED ("LED")
# 運作說明：本程式作為「發送端」，每 3 秒將晶片溫度與傳輸序號發布至雲端 Broker。
#           另一塊執行 lab1_receiver.py 的 Pico 2 W (或 MQTTGO 網頁) 即可即時接收！

import time
import network
import machine
from machine import Pin, ADC
import ubinascii
import ujson

# 內建輕量 MQTTClient 備援 (免手動安裝 umqtt 模組庫)
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
                if not self._sock_has_more(): break
                sh += 7
            return n
        def _sock_has_more(self): return False
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
# 1. Wi-Fi 連線設定 (請填入您的 2.4GHz Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請替換為您的 Wi-Fi 名稱 (僅支援 2.4GHz)
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請替換為您的 Wi-Fi 密碼

# ==========================================
# 2. 硬體引腳與感測器初始化
# ==========================================
led = Pin("LED", Pin.OUT)       # 板載綠色 LED (發送時閃爍反饋)
temp_sensor = ADC(4)            # RP2350 內部溫度感測器通道

# ==========================================
# 3. MQTT 配對頻道與伺服器設定
# ==========================================
MQTT_BROKER = "mqttgo.io"       # 台灣在地開源免費 MQTT Broker
MQTT_PORT = 1883                # 標準 MQTT TCP 連接埠

# 取得硬體唯一 ID 作為發送端身分辨識
DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
CLIENT_ID = f"pico2w_sender_{DEVICE_ID[:6]}"

# 📡 【核心配對主題】：傳送端發布、接收端訂閱必須使用相同主題！
# 課堂分組提示：可將 "pair" 改為組別，例如 "pico2w/team1/data"
PAIR_TOPIC = "pico2w/pair/data"

# 發送週期 (秒)
SEND_INTERVAL = 3

def read_temperature():
    """讀取 RP2350 內部溫度感測器 (攝氏 °C)"""
    conversion_factor = 3.3 / 65535
    reading = temp_sensor.read_u16() * conversion_factor
    # RP2350 內部溫度計算公式：27 - (Vbe - 0.706) / 0.001721
    return 27 - (reading - 0.706) / 0.001721

def blink_led(times=1, duration=0.08):
    """板載 LED 快速閃爍，提供實體物理發送反饋"""
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
        print(f"📡 [傳送端] 正在連線至 Wi-Fi: {WIFI_SSID} ...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 20
        while not wlan.isconnected() and timeout > 0:
            time.sleep(0.5)
            timeout -= 1
            print(".", end="")
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"\n✅ [傳送端] Wi-Fi 連線成功！本機 IP: {ip}")
        return True
    else:
        print("\n❌ [錯誤] Wi-Fi 連線逾時，請確認帳密與 2.4GHz 頻段！")
        return False

def main():
    print("=" * 60)
    print("📤 Pico 2 W 專屬傳送端 (MQTT Publisher)")
    print(f"🆔 裝置識別: {CLIENT_ID}")
    print(f"📡 配對發送主題: {PAIR_TOPIC}")
    print("=" * 60)

    if not connect_wifi():
        return

    print(f"\n正在連線至 MQTT Broker ({MQTT_BROKER}:{MQTT_PORT}) ...")
    client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)

    try:
        client.connect()
        print("✅ MQTT Broker 連線成功！")
        print(f"🚀 開始定期發送數據至: {PAIR_TOPIC} (每 {SEND_INTERVAL} 秒一筆)\n")
        print("-" * 60)

        seq = 0
        while True:
            seq += 1
            temp = read_temperature()

            # 封裝為標準 JSON 格式封包
            payload = {
                "seq": seq,
                "sender": CLIENT_ID,
                "temp": round(temp, 2),
                "status": "HOT" if temp > 30.0 else "NORMAL"
            }
            msg_str = ujson.dumps(payload)

            # 發布至 MQTT 主題
            client.publish(PAIR_TOPIC, msg_str)

            # 實體物理反饋：板載綠色 LED 快閃一下
            blink_led(1, 0.1)

            print(f"📤 [已送出 #{seq:03d}] 溫度: {temp:.2f} °C | 狀態: {payload['status']} | 主題: {PAIR_TOPIC}")
            if temp > 30.0:
                print("   ⚠️ 晶片升溫偵測中（手指按壓加熱實證生效）！")

            time.sleep(SEND_INTERVAL)

    except KeyboardInterrupt:
        print("\n使用者手動中斷傳送。")
    except Exception as e:
        print(f"\n❌ 傳送異常: {e}")
    finally:
        try:
            client.disconnect()
            print("MQTT 連線已關閉。")
        except:
            pass

if __name__ == "__main__":
    main()

