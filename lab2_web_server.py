# lab2_web_server.py - Pico 2 W 邊緣微型 Web Server：Wi-Fi 空間雷達信號探測儀
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 + CYW43439)
# 運作環境：Thonny IDE + MicroPython
# 零外接零件：使用 CYW43439 板載無線晶片 + RP2350 內部溫度感測器 (ADC 4) + 板載綠色 LED ("LED")
# 專案特色：
#   1. Pico 2 W 自主在 Port 80 架設輕量 HTTP Web Server。
#   2. 手機或電腦瀏覽器輸入 http://192.168.x.x 開啟高科技科幻雷達儀表板。
#   3. 點擊「立即掃描」或自動偵測，微控制器深入 CYW43439 底層掃描周遭所有 Wi-Fi 熱點！
#   4. 視覺化呈現：信號強度 (RSSI/dBm)、頻道佔用分析、最佳頻寬推薦、加密防護檢測。

import time
import network
import machine
from machine import Pin, ADC
import usocket as socket
import ujson
import gc
import ubinascii

# ==========================================
# 1. Wi-Fi 連線設定 (請填入您的 2.4GHz Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請填入 Wi-Fi 名稱 (僅支援 2.4GHz)
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請填入 Wi-Fi 密碼

# ==========================================
# 2. 硬體引腳與狀態初始化
# ==========================================
led = Pin("LED", Pin.OUT)       # 板載綠色 LED (雷達掃描時脈衝閃爍)
temp_sensor = ADC(4)            # RP2350 內部溫度感測器
start_time = time.time()        # 開機計時起點
scan_count = 0                  # 累計雷達掃描次數

# 建立 Wi-Fi 網路介面
wlan = network.WLAN(network.STA_IF)

# 安全加密模式對應表 (CYW43439)
AUTH_MODES = {
    0: "OPEN (開放)",
    1: "WEP",
    2: "WPA-PSK",
    3: "WPA2-PSK",
    4: "WPA/WPA2-PSK",
    5: "WPA2/WPA3",
    6: "WPA3-SAE"
}

def read_temperature():
    """讀取 RP2350 內部溫度感測器 (攝氏 °C)"""
    conversion_factor = 3.3 / 65535
    reading = temp_sensor.read_u16() * conversion_factor
    # RP2350 內部溫度物理公式：27 - (Vbe - 0.706) / 0.001721
    return 27 - (reading - 0.706) / 0.001721

def blink_led(times=2, duration=0.06):
    """板載 LED 脈衝閃爍 (雷達掃描實體反饋)"""
    for _ in range(times):
        led.on()
        time.sleep(duration)
        led.off()
        time.sleep(duration)

def rssi_to_quality(rssi):
    """將 dBm 訊號強度轉換為百分比 (0~100%)"""
    if rssi <= -100:
        return 0
    elif rssi >= -50:
        return 100
    else:
        return 2 * (rssi + 100)

def connect_wifi():
    """連線至 Wi-Fi 基地台"""
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
        print(f"\n✅ [Wi-Fi] 連線成功！Pico 2 W 本機 IP: {ip}")
        return ip
    else:
        print("\n❌ [錯誤] Wi-Fi 連線逾時！請確認帳密與 2.4GHz 頻段。")
        return None

def perform_wifi_radar_scan():
    """調用 CYW43439 底層進行 Wi-Fi 空間雷達掃描"""
    global scan_count
    scan_count += 1
    
    # 物理反饋：板載 LED 快閃兩下表示雷達波射出
    blink_led(2, 0.06)
    gc.collect()
    
    try:
        raw_scan = wlan.scan()
    except Exception as e:
        print(f"掃描異常: {e}")
        raw_scan = []
        
    ap_list = []
    channel_counts = {}
    
    for item in raw_scan:
        # 格式: (ssid, bssid, channel, RSSI, authmode, hidden)
        ssid_raw = item[0]
        try:
            ssid_str = ssid_raw.decode("utf-8").strip()
        except:
            ssid_str = str(ssid_raw)
            
        if not ssid_str:
            ssid_str = "[隱藏 SSID 網路]"
            
        bssid_bytes = item[1]
        bssid_str = ":".join([f"{b:02X}" for b in bssid_bytes])
        channel = item[2]
        rssi = item[3]
        authmode = item[4]
        hidden = True if item[5] == 1 else False
        
        # 統計頻道佔用
        channel_counts[channel] = channel_counts.get(channel, 0) + 1
        
        ap_list.append({
            "ssid": ssid_str,
            "bssid": bssid_str,
            "channel": channel,
            "rssi": rssi,
            "quality": rssi_to_quality(rssi),
            "security": AUTH_MODES.get(authmode, f"Mode {authmode}"),
            "hidden": hidden
        })
        
    # 依照訊號強度由強到弱排序
    ap_list.sort(key=lambda x: x["rssi"], reverse=True)
    
    # 評估 2.4GHz 三大互不干擾頻道 (1, 6, 11) 的壅塞度，推薦最佳頻道
    main_channels = [1, 6, 11]
    best_channel = min(main_channels, key=lambda c: channel_counts.get(c, 0))
    
    gc.collect()
    return {
        "aps": ap_list,
        "total_count": len(ap_list),
        "scan_count": scan_count,
        "best_channel": best_channel,
        "channel_stats": channel_counts,
        "temp": round(read_temperature(), 2),
        "uptime": time.time() - start_time,
        "mem_free": gc.mem_free()
    }

def build_dashboard_html(ip):
    """產生高科技科幻風格的 Wi-Fi 空間雷達儀表板"""
    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico 2 W - Wi-Fi 空間雷達探測儀</title>
    <style>
        :root {{
            --bg: #030712;
            --card-bg: rgba(17, 24, 39, 0.85);
            --card-border: rgba(31, 41, 55, 0.8);
            --radar-green: #10b981;
            --radar-cyan: #38bdf8;
            --radar-glow: rgba(16, 185, 129, 0.25);
            --text-main: #f9fafb;
            --text-sub: #9ca3af;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }}
        body {{
            background: radial-gradient(circle at 50% 20%, #111827 0%, var(--bg) 100%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .header {{
            text-align: center;
            max-width: 600px;
            width: 100%;
            margin-bottom: 24px;
        }}
        .radar-badge {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(16, 185, 129, 0.15);
            color: var(--radar-green);
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 9999px;
            padding: 4px 14px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 12px;
            box-shadow: 0 0 15px var(--radar-glow);
        }}
        .pulse-dot {{
            width: 8px; height: 8px; border-radius: 50%;
            background: var(--radar-green);
            box-shadow: 0 0 8px var(--radar-green);
            animation: pulse 1.5s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: 0.4; transform: scale(0.8); }}
        }}
        h1 {{ font-size: 1.7rem; font-weight: 900; letter-spacing: -0.5px; margin-bottom: 6px; }}
        .subtitle {{ font-size: 0.85rem; color: var(--text-sub); }}

        /* 雷達掃描盤 */
        .radar-box {{
            width: 190px;
            height: 190px;
            border-radius: 50%;
            border: 2px solid rgba(16, 185, 129, 0.4);
            margin: 0 auto 24px auto;
            position: relative;
            background: radial-gradient(circle, rgba(16, 185, 129, 0.05) 0%, rgba(3, 7, 18, 0.9) 70%);
            box-shadow: 0 0 30px rgba(16, 185, 129, 0.15), inset 0 0 20px rgba(16, 185, 129, 0.1);
            overflow: hidden;
        }}
        .radar-grid-circle {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            border: 1px dashed rgba(16, 185, 129, 0.25);
        }}
        .radar-axis-h {{
            position: absolute; top: 50%; left: 0; right: 0;
            height: 1px; background: rgba(16, 185, 129, 0.25);
        }}
        .radar-axis-v {{
            position: absolute; left: 50%; top: 0; bottom: 0;
            width: 1px; background: rgba(16, 185, 129, 0.25);
        }}
        .radar-sweep {{
            position: absolute;
            width: 100%; height: 100%;
            border-radius: 50%;
            background: conic-gradient(from 0deg, rgba(16, 185, 129, 0.4) 0deg, transparent 60deg);
            animation: sweep 3s linear infinite;
        }}
        @keyframes sweep {{
            from {{ transform: rotate(0deg); }}
            to {{ transform: rotate(360deg); }}
        }}

        /* 操作控制區 */
        .controls-card {{
            max-width: 600px;
            width: 100%;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 18px 20px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
        }}
        .btn-scan {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: linear-gradient(135deg, #10b981, #059669);
            color: #022c22;
            font-size: 0.95rem;
            font-weight: 800;
            padding: 12px 24px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            transition: all 0.2s;
        }}
        .btn-scan:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.5);
        }}
        .btn-scan:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}

        /* 統計資訊條 */
        .meta-stats {{
            display: flex;
            gap: 16px;
            font-size: 0.8rem;
            color: var(--text-sub);
        }}
        .meta-val {{ font-weight: 700; color: var(--radar-cyan); }}

        /* 頻道推薦卡 */
        .channel-tip-box {{
            max-width: 600px;
            width: 100%;
            background: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 12px;
            padding: 12px 16px;
            margin-bottom: 20px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .best-chan-badge {{
            background: #0284c7;
            color: #f0f9ff;
            font-weight: 800;
            padding: 3px 10px;
            border-radius: 6px;
        }}

        /* 熱點信號清單 */
        .ap-list-container {{
            max-width: 600px;
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .ap-card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 16px;
            transition: all 0.2s;
        }}
        .ap-card:hover {{
            border-color: rgba(56, 189, 248, 0.4);
            transform: translateY(-2px);
        }}
        .ap-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }}
        .ap-ssid {{
            font-weight: 800;
            font-size: 1.05rem;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .ap-meta {{
            display: flex;
            gap: 8px;
            align-items: center;
            font-size: 0.75rem;
            color: var(--text-sub);
        }}
        .tag {{
            padding: 2px 8px;
            border-radius: 6px;
            font-weight: 700;
            font-size: 0.72rem;
        }}
        .tag-chan {{ background: #1e293b; color: #94a3b8; border: 1px solid #334155; }}
        .tag-sec {{ background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }}
        
        /* 訊號強弱進度條 */
        .signal-bar-box {{
            margin-top: 10px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .signal-track {{
            flex: 1;
            height: 8px;
            background: #1f2937;
            border-radius: 9999px;
            overflow: hidden;
        }}
        .signal-fill {{
            height: 100%;
            border-radius: 9999px;
            transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        .rssi-val {{
            font-weight: 800;
            font-size: 0.85rem;
            width: 75px;
            text-align: right;
        }}
        .status-good {{ color: #34d399; background: #10b981; }}
        .status-fair {{ color: #38bdf8; background: #0284c7; }}
        .status-weak {{ color: #fbbf24; background: #f59e0b; }}
        .status-bad {{ color: #f87171; background: #ef4444; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="radar-badge">
            <span class="pulse-dot"></span>
            CYW43439 邊緣無線射頻雷達
        </div>
        <h1>Pico 2 W 空間信號探測儀</h1>
        <div class="subtitle">區網 IP: <strong>{ip}</strong> | Port 80 邊緣伺服器</div>
    </div>

    <!-- 動態雷達掃描盤 -->
    <div class="radar-box">
        <div class="radar-sweep"></div>
        <div class="radar-grid-circle" style="width: 50px; height: 50px;"></div>
        <div class="radar-grid-circle" style="width: 110px; height: 110px;"></div>
        <div class="radar-grid-circle" style="width: 170px; height: 170px;"></div>
        <div class="radar-axis-h"></div>
        <div class="radar-axis-v"></div>
    </div>

    <!-- 控制面板 -->
    <div class="controls-card">
        <button class="btn-scan" id="scanBtn" onclick="triggerScan()">
            <span>📡 啟動空間雷達掃描</span>
        </button>
        <div class="meta-stats">
            <div>熱點總數: <span class="meta-val" id="totalAps">0</span> 個</div>
            <div>晶片溫度: <span class="meta-val" id="chipTemp">--</span> °C</div>
            <div>可用記憶體: <span class="meta-val" id="memFree">--</span> KB</div>
        </div>
    </div>

    <!-- 最佳頻道推薦 -->
    <div class="channel-tip-box" id="channelTip" style="display: none;">
        <span>🌟 <strong>2.4GHz 最佳推薦頻道</strong>（最不擁擠）：</span>
        <span class="best-chan-badge" id="bestChanText">CH 11</span>
    </div>

    <!-- 探測到的熱點清單 -->
    <div class="ap-list-container" id="apList">
        <div style="text-align: center; padding: 40px 0; color: #64748b;">
            請點擊上方「啟動空間雷達掃描」按鈕，探測空氣中的無線電信號...
        </div>
    </div>

    <script>
        function getSignalClass(rssi) {{
            if (rssi >= -65) return 'status-good';
            if (rssi >= -75) return 'status-fair';
            if (rssi >= -85) return 'status-weak';
            return 'status-bad';
        }}

        function triggerScan() {{
            const btn = document.getElementById('scanBtn');
            btn.disabled = true;
            btn.innerHTML = '<span>⏳ 雷達射束掃描中...</span>';
            
            fetch('/api/scan')
                .then(r => r.json())
                .then(data => {{
                    document.getElementById('totalAps').innerText = data.total_count;
                    document.getElementById('chipTemp').innerText = data.temp;
                    document.getElementById('memFree').innerText = Math.round(data.mem_free / 1024);
                    
                    // 顯示推薦頻道
                    document.getElementById('channelTip').style.display = 'flex';
                    document.getElementById('bestChanText').innerText = '頻道 ' + data.best_channel;

                    const listContainer = document.getElementById('apList');
                    if (data.aps.length === 0) {{
                        listContainer.innerHTML = '<div style="text-align: center; padding: 30px; color: #64748b;">周遭未探測到任何公開 Wi-Fi 訊號</div>';
                    }} else {{
                        let html = '';
                        data.aps.forEach(ap => {{
                            const cls = getSignalClass(ap.rssi);
                            html += `
                                <div class="ap-card">
                                    <div class="ap-header">
                                        <div class="ap-ssid">
                                            📶 ${{ap.ssid}}
                                        </div>
                                        <div class="ap-meta">
                                            <span class="tag tag-chan">CH ${{ap.channel}}</span>
                                            <span class="tag tag-sec">${{ap.security}}</span>
                                        </div>
                                    </div>
                                    <div style="font-size: 0.72rem; color: #6b7280; margin-bottom: 6px;">
                                        MAC: ${{ap.bssid}}
                                    </div>
                                    <div class="signal-bar-box">
                                        <div class="signal-track">
                                            <div class="signal-fill ${{cls}}" style="width: ${{ap.quality}}%;"></div>
                                        </div>
                                        <div class="rssi-val ${{cls}}">${{ap.rssi}} dBm (${{ap.quality}}%)</div>
                                    </div>
                                </div>
                            `;
                        }});
                        listContainer.innerHTML = html;
                    }}
                }})
                .catch(err => {{
                    alert('掃描失敗或連線逾時: ' + err);
                }})
                .finally(() => {{
                    btn.disabled = false;
                    btn.innerHTML = '<span>📡 啟動空間雷達掃描</span>';
                }});
        }}

        // 初次載入自動觸發一次雷達掃描
        window.onload = () => {{
            setTimeout(triggerScan, 800);
        }};
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
        parts = lines[0].split(" ")
        return parts[0], parts[1] if len(parts) > 1 else "/"
    except:
        return "GET", "/"

def main():
    print("\n" + "=" * 65)
    print("📡 方案 10：Pico 2 W 空間 Wi-Fi 雷達信號探測儀 (Web Server)")
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
    print("║ 🛸 【Wi-Fi 空間雷達 Web 伺服器已就緒！】")
    print("╠" + "═" * 63 + "╣")
    print(f"║ 🔗 請用電腦或手機開啟雷達儀表板：")
    print(f"║    http://{ip}")
    print("║")
    print("║ 💡 玩法亮點：")
    print("║    1. 點擊「啟動空間雷達掃描」，板載 LED 脈衝閃爍！")
    print("║    2. 網頁即時解析周遭 Wi-Fi 信號 (dBm) 與最佳推薦頻道。")
    print("║    3. 手指捏緊 RP2350 晶片，親眼觀察晶片溫度與射頻熱度！")
    print("╚" + "═" * 63 + "╝\n")
    print("⏳ 伺服器監聽中 (等待 HTTP Request 連線)...\n")
    
    try:
        while True:
            client_sock, client_addr = server_sock.accept()
            client_ip = client_addr[0]
            
            raw_req = client_sock.recv(1024).decode("utf-8", "ignore")
            method, path = parse_http_request(raw_req)
            
            print(f"📥 [HTTP 請求] 來源: {client_ip} | {method} {path}")
            
            # 路由 1：RESTful API 空間雷達掃描端點 (/api/scan)
            if path == "/api/scan":
                scan_data = perform_wifi_radar_scan()
                body = ujson.dumps(scan_data)
                resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json; charset=utf-8\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                    "Connection: close\r\n\r\n"
                    f"{body}"
                )
                client_sock.sendall(resp.encode("utf-8"))
                
            # 路由 2：快速狀態端點 (/api/status)
            elif path == "/api/status":
                status_data = {
                    "temp": round(read_temperature(), 2),
                    "uptime": time.time() - start_time,
                    "mem_free": gc.mem_free()
                }
                body = ujson.dumps(status_data)
                resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json; charset=utf-8\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n\r\n"
                    f"{body}"
                )
                client_sock.sendall(resp.encode("utf-8"))
                
            # 路由 3：根目錄首頁儀表板 (/)
            else:
                html_page = build_dashboard_html(ip)
                body_bytes = html_page.encode("utf-8")
                resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: text/html; charset=utf-8\r\n"
                    f"Content-Length: {len(body_bytes)}\r\n"
                    "Connection: close\r\n\r\n"
                )
                client_sock.sendall(resp.encode("utf-8") + body_bytes)
                
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
