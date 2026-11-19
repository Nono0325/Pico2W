# lab2_web_server.py - Pico 2 W 專屬邊緣微型 Web Server (Edge Web Server)
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 + CYW43439)
# 運作環境：Thonny IDE + MicroPython
# 零外接零件：使用 RP2350 內部溫度感測器 (ADC 4) 與板載綠色 LED ("LED")
# 核心功能：Pico 2 W 自主在 Port 80 架設 HTTP Web 伺服器！
#           手機與電腦只要在同一個 Wi-Fi 區域網路，輸入 Pico 的 IP 即可開啟現代化儀表板，
#           即時讀取板載晶片溫度、監看系統狀態，並用網頁按鈕無線遙控實體板載 LED！

import time
import network
import machine
from machine import Pin, ADC
import usocket as socket
import ujson
import gc

# ==========================================
# 1. Wi-Fi 連線設定 (請替換為您的 Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請填入 2.4GHz Wi-Fi 名稱
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請填入 Wi-Fi 密碼

# ==========================================
# 2. 硬體引腳與狀態初始化
# ==========================================
led = Pin("LED", Pin.OUT)       # 板載綠色 LED
temp_sensor = ADC(4)            # RP2350 內部溫度感測器通道
start_time = time.time()        # 開機計時起點
request_count = 0               # 伺服器請求處理累計

def read_temperature():
    """讀取 RP2350 內部溫度感測器 (攝氏 °C)"""
    conversion_factor = 3.3 / 65535
    reading = temp_sensor.read_u16() * conversion_factor
    # RP2350 物理轉換公式：27 - (Vbe - 0.706) / 0.001721
    return 27 - (reading - 0.706) / 0.001721

def blink_led(times=3, duration=0.1):
    """板載 LED 快閃反饋"""
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
        return ip
    else:
        print("\n❌ [錯誤] Wi-Fi 連線逾時！請確認帳密與 2.4GHz 頻段。")
        return None

def build_html_page(ip):
    """產出響應式深色現代化 Web 儀表板 HTML"""
    temp = read_temperature()
    uptime = time.time() - start_time
    mem_free = gc.mem_free()
    led_state = "ON" if led.value() else "OFF"
    
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico 2 W 邊緣伺服器儀表板</title>
    <style>
        :root {{
            --bg: #090d16;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(148, 163, 184, 0.15);
            --primary: #38bdf8;
            --accent: #10b981;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{
            background: radial-gradient(circle at top, #1e293b 0%, var(--bg) 100%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px 16px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .container {{
            max-width: 480px;
            width: 100%;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 28px 24px;
            backdrop-filter: blur(12px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.5);
        }}
        .badge {{
            display: inline-block;
            background: rgba(56, 189, 248, 0.15);
            color: var(--primary);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 9999px;
            padding: 4px 12px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 12px;
        }}
        h1 {{ font-size: 1.5rem; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.5px; }}
        .subtitle {{ color: var(--text-sub); font-size: 0.85rem; margin-bottom: 24px; }}
        
        /* 數據卡片區 */
        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }}
        .stat-card {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 14px;
            text-align: center;
        }}
        .stat-label {{ font-size: 0.75rem; color: var(--text-sub); margin-bottom: 4px; }}
        .stat-value {{ font-size: 1.4rem; font-weight: 900; color: var(--primary); }}
        .stat-unit {{ font-size: 0.8rem; font-weight: 400; color: var(--text-sub); }}
        
        /* LED 狀態指示器 */
        .led-indicator-box {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 14px 18px;
            margin-bottom: 24px;
        }}
        .led-status-tag {{ font-weight: 800; font-size: 1.1rem; }}
        .led-dot {{
            width: 18px; height: 18px; border-radius: 50%;
            background: {("#10b981" if led_state == "ON" else "#475569")};
            box-shadow: {("0 0 12px #10b981" if led_state == "ON" else "none")};
            transition: all 0.3s;
        }}
        
        /* 控制按鈕群 */
        .btn-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }}
        button, a.btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            padding: 12px 16px;
            border-radius: 12px;
            font-weight: 700;
            font-size: 0.95rem;
            cursor: pointer;
            text-decoration: none;
            transition: all 0.2s;
            border: none;
        }}
        .btn-on {{ background: #10b981; color: #022c22; }}
        .btn-on:hover {{ background: #34d399; transform: translateY(-2px); }}
        .btn-off {{ background: #334155; color: #f8fafc; border: 1px solid #475569; }}
        .btn-off:hover {{ background: #475569; transform: translateY(-2px); }}
        .btn-toggle {{ background: #0284c7; color: #f0f9ff; }}
        .btn-toggle:hover {{ background: #38bdf8; transform: translateY(-2px); }}
        .btn-blink {{ background: #7c3aed; color: #f5f3ff; }}
        .btn-blink:hover {{ background: #a855f7; transform: translateY(-2px); }}
        
        /* 即時輪詢動態小字 */
        .auto-refresh-tip {{
            font-size: 0.75rem;
            color: #64748b;
            text-align: center;
            margin-top: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">RP2350 邊緣伺服器</div>
        <h1>Pico 2 W Web 儀表板</h1>
        <div class="subtitle">區網 IP: <strong>{ip}</strong> | 獨立本地運作</div>

        <!-- 數據監控 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">RP2350 晶片溫度</div>
                <div class="stat-value" id="temp-val">{temp:.2f}<span class="stat-unit"> °C</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">運行時間 (Uptime)</div>
                <div class="stat-value" id="uptime-val">{uptime}<span class="stat-unit"> 秒</span></div>
            </div>
        </div>

        <!-- 板載 LED 狀態 -->
        <div class="led-indicator-box">
            <div>
                <div style="font-size: 0.8rem; color: var(--text-sub);">板載綠色 LED</div>
                <div class="led-status-tag" id="led-text" style="color: {("#34d399" if led_state == "ON" else "#94a3b8")};">{led_state}</div>
            </div>
            <div class="led-dot" id="led-dot"></div>
        </div>

        <!-- 實體遙控按鈕群 -->
        <div class="btn-grid">
            <a href="/api/led?state=on" class="btn btn-on">💡 開燈 (ON)</a>
            <a href="/api/led?state=off" class="btn btn-off">💤 關燈 (OFF)</a>
            <a href="/api/led?state=toggle" class="btn btn-toggle">🔄 切換 (TOGGLE)</a>
            <a href="/api/led?state=blink" class="btn btn-blink">⚡ 快閃 3 次</a>
        </div>

        <div class="auto-refresh-tip">
            ⚡ 頁面內建 AJAX 非阻塞非同步輪詢，每 2 秒無感刷新溫度數據
        </div>
    </div>

    <script>
        // 每 2 秒透過 RESTful API 拉取最新狀態，實現無重新整理動態更新
        setInterval(() => {{
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {{
                    document.getElementById('temp-val').innerHTML = data.temp.toFixed(2) + '<span class="stat-unit"> °C</span>';
                    document.getElementById('uptime-val').innerHTML = data.uptime + '<span class="stat-unit"> 秒</span>';
                    const isLedOn = data.led === 1;
                    document.getElementById('led-text').innerText = isLedOn ? "ON" : "OFF";
                    document.getElementById('led-text').style.color = isLedOn ? "#34d399" : "#94a3b8";
                    document.getElementById('led-dot').style.background = isLedOn ? "#10b981" : "#475569";
                    document.getElementById('led-dot').style.boxShadow = isLedOn ? "0 0 12px #10b981" : "none";
                }})
                .catch(err => console.log('輪詢暫時中斷:', err));
        }}, 2000);
    </script>
</body>
</html>"""
    return html

def parse_http_request(raw_request):
    """解析 HTTP 請求方法與路由路徑"""
    try:
        lines = raw_request.split("\r\n")
        if not lines or not lines[0]:
            return "GET", "/"
        first_line = lines[0].split(" ")
        method = first_line[0]
        path = first_line[1] if len(first_line) > 1 else "/"
        return method, path
    except Exception:
        return "GET", "/"

def main():
    global request_count
    print("\n" + "=" * 65)
    print("🌐 實驗 2：Pico 2 W 邊緣微型 Web Server (Edge Web Server)")
    print("=" * 65)
    
    ip = connect_wifi()
    if not ip:
        return
        
    # 建立 TCP Socket 伺服器並綁定 Port 80
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", 80))
    server_sock.listen(5)
    
    print("\n" + "╔" + "═" * 63 + "╗")
    print("║ 🎉 【Pico 2 W 邊緣 Web 伺服器啟動成功！】")
    print("╠" + "═" * 63 + "╣")
    print(f"║ 🔗 請打開電腦或手機瀏覽器輸入：")
    print(f"║    http://{ip}")
    print("║")
    print("║ 💡 提示：本實驗 Pico 扮演 Web Server，您可以在瀏覽器直接輸入 IP！")
    print("║    支援點擊按鈕遙控 LED、手指按壓晶片實時升溫儀表板。")
    print("╚" + "═" * 63 + "╝\n")
    print("⏳ 伺服器監聽中 (等待 HTTP Request 連線)...\n")
    
    try:
        while True:
            client_sock, client_addr = server_sock.accept()
            request_count += 1
            client_ip = client_addr[0]
            
            # 讀取客戶端傳入之 HTTP 請求字串
            raw_req = client_sock.recv(1024).decode("utf-8", "ignore")
            method, path = parse_http_request(raw_req)
            
            # 在 Thonny 通訊列輸出訪問日誌
            print(f"📥 [HTTP 請求 #{request_count:04d}] 來源: {client_ip} | {method} {path}")
            
            # 路由 1：RESTful API 狀態端點 (/api/status)
            if path == "/api/status":
                temp = read_temperature()
                uptime = time.time() - start_time
                payload = {
                    "temp": round(temp, 2),
                    "led": led.value(),
                    "uptime": uptime,
                    "mem_free": gc.mem_free()
                }
                body = ujson.dumps(payload)
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json; charset=utf-8\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n\r\n"
                    f"{body}"
                )
                client_sock.sendall(response.encode("utf-8"))
                
            # 路由 2：LED 控制端點 (/api/led?state=...)
            elif path.startswith("/api/led"):
                if "state=on" in path:
                    led.on()
                    print("   💡 板載 LED 已開啟 (ON)")
                elif "state=off" in path:
                    led.off()
                    print("   💤 板載 LED 已關閉 (OFF)")
                elif "state=toggle" in path:
                    led.toggle()
                    print("   🔄 板載 LED 狀態已切換")
                elif "state=blink" in path:
                    print("   ⚡ 執行快閃 3 次")
                    blink_led(3, 0.12)
                    
                # 重新導向回首頁，無縫刷新畫面
                redirect = (
                    "HTTP/1.1 303 See Other\r\n"
                    "Location: /\r\n"
                    "Connection: close\r\n\r\n"
                )
                client_sock.sendall(redirect.encode("utf-8"))
                
            # 路由 3：根目錄首頁儀表板 (/)
            else:
                html_body = build_html_page(ip)
                response = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(html_body.encode('utf-8'))}\r\n"
                    "Connection: close\r\n\r\n"
                    f"{html_body}"
                )
                client_sock.sendall(response.encode("utf-8"))
                
            # 關閉客戶端 Socket 連線並主動回收記憶體
            client_sock.close()
            gc.collect()
            
    except KeyboardInterrupt:
        print("\n🛑 使用者手動中斷伺服器。")
    except Exception as e:
        print(f"\n❌ 伺服器異常: {e}")
    finally:
        try:
            server_sock.close()
            print("Web Server 已正常關閉。")
        except:
            pass

if __name__ == "__main__":
    main()
