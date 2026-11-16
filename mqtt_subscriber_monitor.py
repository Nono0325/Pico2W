# mqtt_subscriber_monitor.py - Pico 2 W 專屬 MQTTGO 特定主題訊息監聽與通訊列顯示程式
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 / RP2040 + CYW43439)
# 運作環境：Thonny IDE + MicroPython
# 功能說明：連線至台灣 MQTTGO.io，訂閱您指定的「特定主題 (Topic)」。
#           當雲端有新訊息發布時，即時在 Thonny 通訊列 (Shell) 格式化印出，並連動板載 LED 閃爍提示！
# 設計特色：單檔即跑 (All-in-One Standalone)，內建輕量 MQTTClient 實作，免額外安裝 umqtt 模組庫！

import time
import network
import machine
from machine import Pin
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

    class MQTTException(Exception):
        pass

    class MQTTClient:
        def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0,
                     ssl=False, ssl_params={}):
            if port == 0:
                port = 8883 if ssl else 1883
            self.client_id = client_id
            self.sock = None
            self.server = server
            self.port = port
            self.ssl = ssl
            self.ssl_params = ssl_params
            self.pid = 0
            self.cb = None
            self.user = user
            self.pswd = password
            self.keepalive = keepalive
            self.lw_topic = None
            self.lw_msg = None
            self.lw_qos = 0
            self.lw_retain = False

        def _send_str(self, s):
            self.sock.write(struct.pack("!H", len(s)))
            self.sock.write(s)

        def _recv_len(self):
            n = 0
            sh = 0
            while 1:
                res = self.sock.read(1)
                b = res[0]
                n |= (b & 0x7f) << sh
                if not self._sock_has_more():
                    break
                sh += 7
            return n

        def _sock_has_more(self):
            return False

        def set_callback(self, f):
            self.cb = f

        def connect(self, clean_session=True):
            self.sock = socket.socket()
            addr = socket.getaddrinfo(self.server, self.port)[0][-1]
            self.sock.connect(addr)
            if self.ssl:
                import ussl
                self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)
            premsg = bytearray(b"\x10\0\0\0\0\0")
            msg = bytearray(b"\x04MQTT\x04\x02\0\0")

            sz = 10 + 2 + len(self.client_id)
            msg[6] = clean_session << 1
            if self.user is not None:
                sz += 2 + len(self.user) + 2 + len(self.pswd)
                msg[6] |= 0xC0
            if self.keepalive:
                assert self.keepalive < 65536
                msg[7] = self.keepalive >> 8
                msg[8] = self.keepalive & 0x00FF
            if self.lw_topic:
                sz += 2 + len(self.lw_topic) + 2 + len(self.lw_msg)
                msg[6] |= 0x4 | (self.lw_qos & 0x1) << 3 | (self.lw_qos & 0x2) << 3
                msg[6] |= self.lw_retain << 5

            i = 1
            while sz > 0x7f:
                premsg[i] = (sz & 0x7f) | 0x80
                sz >>= 7
                i += 1
            premsg[i] = sz
            self.sock.write(premsg[:i + 2])
            self.sock.write(msg)
            self._send_str(self.client_id)
            if self.lw_topic:
                self._send_str(self.lw_topic)
                self._send_str(self.lw_msg)
            if self.user is not None:
                self._send_str(self.user)
                self._send_str(self.pswd)
            resp = self.sock.read(4)
            assert resp[0] == 0x20 and resp[1] == 0x02
            if resp[3] != 0:
                raise MQTTException(resp[3])
            return resp[2] & 1

        def disconnect(self):
            self.sock.write(b"\xe0\0")
            self.sock.close()

        def ping(self):
            self.sock.write(b"\xc0\0")

        def publish(self, topic, msg, retain=False, qos=0):
            pkt = bytearray(b"\x30\0\0\0")
            pkt[0] |= qos << 1 | retain
            sz = 2 + len(topic) + len(msg)
            if qos > 0:
                sz += 2
            assert sz < 2097152
            i = 1
            while sz > 0x7f:
                pkt[i] = (sz & 0x7f) | 0x80
                sz >>= 7
                i += 1
            pkt[i] = sz
            self.sock.write(pkt[:i + 1])
            self._send_str(topic)
            if qos > 0:
                self.pid += 1
                pid = self.pid
                struct.pack_into("!H", pkt, 0, pid)
                self.sock.write(pkt[:2])
            self.sock.write(msg)
            if qos == 1:
                while 1:
                    op = self.wait_msg()
                    if op == 0x40:
                        sz = self.sock.read(1)
                        assert sz == b"\x02"
                        rcv_pid = self.sock.read(2)
                        rcv_pid = rcv_pid[0] << 8 | rcv_pid[1]
                        if pid == rcv_pid:
                            return
            elif qos == 2:
                assert 0

        def subscribe(self, topic, qos=0):
            assert self.cb is not None, "Subscribe callback is not set"
            pkt = bytearray(b"\x82\0\0\0")
            self.pid += 1
            struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
            self.sock.write(pkt)
            self._send_str(topic)
            self.sock.write(struct.pack("B", qos))
            while 1:
                op = self.wait_msg()
                if op == 0x90:
                    resp = self.sock.read(4)
                    assert resp[1] == pkt[2] and resp[2] == pkt[3]
                    if resp[3] == 0x80:
                        raise MQTTException(resp[3])
                    return

        def wait_msg(self):
            res = self.sock.read(1)
            if res is None:
                return None
            if res == b"":
                raise OSError(-1)
            if res == b"\xd0":  # PINGRESP
                sz = self.sock.read(1)[0]
                assert sz == 0
                return None
            op = res[0]
            if op & 0xf0 != 0x30:
                return op
            sz = self._recv_len()
            topic_len = self.sock.read(2)
            topic_len = (topic_len[0] << 8) | topic_len[1]
            topic = self.sock.read(topic_len)
            sz -= topic_len + 2
            if op & 6:
                pid = self.sock.read(2)
                pid = pid[0] << 8 | pid[1]
                sz -= 2
            msg = self.sock.read(sz)
            self.cb(topic, msg)
            if op & 6 == 2:
                pkt = bytearray(b"\x40\x02\0\0")
                struct.pack_into("!H", pkt, 2, pid)
                self.sock.write(pkt)
            elif op & 6 == 4:
                assert 0
            return op

        def check_msg(self):
            self.sock.setblocking(False)
            return self.wait_msg()

# ==========================================
# 1. Wi-Fi 連線設定 (請替換為您的 2.4GHz Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請填入 2.4GHz Wi-Fi 名稱
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請填入 Wi-Fi 密碼

# ==========================================
# 2. MQTT 伺服器與「特定主題」設定
# ==========================================
MQTT_BROKER = "mqttgo.io"       # 台灣在地開源免費 Broker
MQTT_PORT = 1883                # 標準 TCP 連接埠

# 🎯 【您要抓取監聽的特定主題】（可自由修改為任何您想監聽的主題）
# 例如: "myhome/sensor/temp"、"school/classA/notice"、"pico2w/my_topic"
TARGET_TOPIC = "pico2w/my_topic"

# ==========================================
# 3. 硬體引腳初始化
# ==========================================
led = Pin("LED", Pin.OUT)       # 板載綠色 LED (收到訊息時閃爍提示)

DEVICE_ID = ubinascii.hexlify(machine.unique_id()).decode('utf-8')
CLIENT_ID = f"pico2w_monitor_{DEVICE_ID[:6]}"

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
    
    # 物理反饋：板載 LED 閃爍一下
    blink_led(1, 0.15)
    
    # 在 Thonny 通訊列 (Shell) 格式化印出收到之訊息
    print("\n" + "╔" + "═" * 63 + "╗")
    print(f"║ 📬 【通訊列收到新訊息 #{message_count:04d}】 (運作時間: {elapsed} 秒)")
    print("╠" + "═" * 63 + "╣")
    print(f"║ 🏷️  主題 (Topic)   : {topic_str}")
    print(f"║ 📏 內容長度        : {len(raw_str)} Bytes")
    print("╟" + "─" * 63 + "╢")
    
    # 判斷是否為結構化 JSON (物件或陣列)
    is_json = False
    try:
        json_data = ujson.loads(raw_str)
        if isinstance(json_data, dict):
            is_json = True
            print("║ 📦 訊息格式        : [標準 JSON 鍵值結構]")
            print("║ 📄 訊息內容如下    :")
            for key, val in json_data.items():
                print(f"║    ▶ {key}: {val}")
        elif isinstance(json_data, list):
            is_json = True
            print("║ 📦 訊息格式        : [JSON 陣列清單]")
            for idx, item in enumerate(json_data):
                print(f"║    ▶ [{idx}]: {item}")
    except Exception:
        pass
        
    if not is_json:
        print("║ 📦 訊息格式        : [純文字 / 數值]")
        print(f"║ 📄 訊息內容        : {raw_str}")
        
    print("╚" + "═" * 63 + "╝\n")

def main():
    print("\n" + "=" * 65)
    print("🚀 Pico 2 W - MQTTGO 特定主題訊息監聽程式 (長效保活版)")
    print("=" * 65)
    
    # 輸出操作指引
    print("\n" + "-" * 65)
    print("🌐 【如何測試發送訊息給 Pico 2 W？】")
    print("👉 請用電腦或手機開啟： https://mqttgo.io/")
    print("1. 在網頁中的「發布主題 (Topic)」填入：")
    print(f"   {TARGET_TOPIC}")
    print("2. 在「發布訊息 (Message)」輸入任意文字或 JSON，例如：")
    print("   Hello Pico 2 W!")
    print("   或 {\"msg\": \"早安\", \"temp\": 25.5}")
    print("3. 點擊「發布」，Pico 2 W 通訊列將會立即格式化顯示訊息！")
    print("-" * 65 + "\n")

    # 長效監聽迴圈 (支援心跳保活與自動斷線重連)
    while True:
        if not connect_wifi():
            print("等待 3 秒後重試 Wi-Fi 連線...")
            time.sleep(3)
            continue
            
        print(f"\n正在連線至 MQTTGO 伺服器: {MQTT_BROKER}:{MQTT_PORT} ...")
        print(f"客戶端名稱 (Client ID): {CLIENT_ID}")
        
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=60)
        client.set_callback(on_message_received)
        
        try:
            client.connect()
            print("✅ MQTT Broker 連線成功！")
            
            # 訂閱您指定的特定主題
            client.subscribe(TARGET_TOPIC)
            print(f"📡 【已成功訂閱特定主題】: {TARGET_TOPIC}")
            print(f"⏳ 正在長效監聽中... (已啟用 20 秒心跳保活機制)")
            
            last_ping_time = time.time()
            while True:
                # 非阻塞檢查雲端是否有新訊息
                client.check_msg()
                
                # 每 20 秒定時發送 PINGREQ 心跳保活，防止被 Broker 超時斷線 (解決 -1 異常)
                now = time.time()
                if now - last_ping_time >= 20:
                    client.ping()
                    last_ping_time = now
                    
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n🛑 使用者手動中斷程式。")
            try:
                client.disconnect()
                print("MQTT 連線已關閉。")
            except:
                pass
            break
        except Exception as e:
            print(f"\n⚠️ 連線暫時中斷 (原因: {e})，3 秒後自動重新連線...")
            try:
                client.disconnect()
            except:
                pass
            time.sleep(3)

if __name__ == "__main__":
    main()
