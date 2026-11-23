# lab2_wifi_radar.py - Pico 2 W 邊緣 Web Server：Wi-Fi 訊號強度探測儀
# 適用硬體：Raspberry Pi Pico 2 W (RP2350 + CYW43439)
# 運作環境：Thonny IDE + MicroPython
# 零外接零件：使用板載 CYW43439 無線晶片與板載綠色 LED ("LED")
# 功能說明：
#   1. 啟動 Web Server (Port 80)，瀏覽器輸入 Pico IP 即可查看周遭 Wi-Fi 訊號與強度清單。
#   2. 同步在 Thonny 通訊列 (Shell) 格式化印出周遭 Wi-Fi 熱點名稱與 dBm 訊號強弱。
#   3. 支援一鍵重新掃描，直觀觀察訊號強度與手掌物理遮蔽衰減！

import time
import network
from machine import Pin
import usocket as socket
import gc

# ==========================================
# 1. Wi-Fi 連線設定 (請填入您的 2.4GHz Wi-Fi)
# ==========================================
WIFI_SSID = "YOUR_WIFI_SSID"          # 請填入 Wi-Fi 名稱 (僅支援 2.4GHz)
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"  # 請填入 Wi-Fi 密碼

# ==========================================
# 2. 硬體與網路初始化
# ==========================================
led = Pin("LED", Pin.OUT)       # 板載綠色 LED (掃描時閃爍反饋)
wlan = network.WLAN(network.STA_IF)

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

def rssi_to_quality(rssi):
    """將 dBm 訊號強度轉換為百分比 (0~100%)"""
    if rssi <= -100:
        return 0
    elif rssi >= -50:
        return 100
    else:
        return 2 * (rssi + 100)

def rssi_to_level(rssi):
    """評估訊號等級與顯示顏色"""
    if rssi >= -60:
        return "極佳", "#10b981"   # 綠色
    elif rssi >= -70:
        return "良好", "#38bdf8"   # 藍色
    elif rssi >= -80:
        return "普通", "#facc15"   # 黃色
    else:
        return "微弱", "#f87171"   # 紅色

def scan_nearby_wifi():
    """掃描周遭 Wi-Fi 並在 Shell 印出結果"""
    # 掃描時閃燈提示
    led.on()
    print("\n🔍 正在掃描周遭 Wi-Fi 訊號...")
    try:
        raw_list = wlan.scan()
    except Exception as e:
        print(f"❌ 掃描失敗: {e}")
        raw_list = []
    led.off()
    
    wifi_list = []
    for item in raw_list:
        # 格式: (ssid, bssid, channel, RSSI, authmode, hidden)
        try:
            ssid = item[0].decode("utf-8").strip()
        except:
            ssid = str(item[0])
            
        if not ssid:
            ssid = "[隱藏 SSID]"
            
        rssi = item[3]
        channel = item[2]
        quality = rssi_to_quality(rssi)
        level_str, level_color = rssi_to_level(rssi)
        
        wifi_list.append({
            "ssid": ssid,
            "channel": channel,
            "rssi": rssi,
            "quality": quality,
            "level": level_str,
            "color": level_color
        })
        
    # 依照訊號強度 (RSSI 由大到小) 排序
    wifi_list.sort(key=lambda x: x["rssi"], reverse=True)
    
    # 在 Thonny Shell 終端機格式化輸出
    print("-" * 65)
    print(f"📊 掃描完成！共偵測到 {len(wifi_list)} 個 Wi-Fi 熱點 (由強至弱排序)：")
    for i, ap in enumerate(wifi_list, 1):
        bar_len = ap["quality"] // 10
        bar_str = "█" * bar_len + "░" * (10 - bar_len)
        print(f" {i:2d}. [{ap['ssid']:<24}]  訊號: {ap['rssi']:3d} dBm  [{bar_str}] ({ap['level']})  CH:{ap['channel']}")
    print("-" * 65)
    
    gc.collect()
    return wifi_list

def build_html_page(wifi_list, ip):
    """產生查看 Wi-Fi 訊號與強度的簡潔網頁"""
    # 動態產生熱點表格內容
    rows = ""
    for i, ap in enumerate(wifi_list, 1):
        rows += f"""
        <tr>
            <td style="color:#94a3b8;">#{i}</td>
            <td><strong>{ap['ssid']}</strong></td>
            <td><span class="badge" style="background:#1e293b; color:#94a3b8;">CH {ap['channel']}</span></td>
            <td style="color:{ap['color']}; font-weight:bold;">{ap['rssi']} dBm</td>
            <td style="width: 140px;">
                <div class="progress-bg">
                    <div class="progress-bar" style="width:{ap['quality']}%; background:{ap['color']};"></div>
                </div>
            </td>
            <td><span class="badge" style="background:{ap['color']}22; color:{ap['color']}; border: 1px solid {ap['color']}44;">{ap['level']} ({ap['quality']}%)</span></td>
        </tr>
        """
        
    if not rows:
        rows = "<tr><td colspan='6' style='text-align:center; padding:20px; color:#94a3b8;'>未偵測到任何 Wi-Fi 熱點</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico 2 W - Wi-Fi 訊號強度探測儀</title>
    <style>
        body {{
            background: #0b0f19;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 24px 16px;
            display: flex;
            justify-content: center;
        }}
        .container {{
            max-width: 720px;
            width: 100%;
        }}
        .header {{
            text-align: center;
            margin-bottom: 24px;
        }}
        h1 {{
            font-size: 1.5rem;
            color: #38bdf8;
            margin-bottom: 6px;
        }}
        .meta {{
            color: #94a3b8;
            font-size: 0.88rem;
        }}
        .card {{
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 18px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        }}
        .toolbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 10px;
        }}
        .btn {{
            display: inline-block;
            background: #2563eb;
            color: white;
            text-decoration: none;
            padding: 8px 18px;
            border-radius: 8px;
            font-weight: 500;
            font-size: 0.9rem;
            border: none;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .btn:hover {{ background: #1d4ed8; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #1e293b;
        }}
        th {{
            color: #94a3b8;
            font-size: 0.82rem;
            text-transform: uppercase;
        }}
        .progress-bg {{
            background: #1e293b;
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-bar {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }}
        .badge {{
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            display: inline-block;
        }}
        .tip {{
            margin-top: 18px;
            background: rgba(56, 189, 248, 0.08);
            border-left: 3px solid #38bdf8;
            padding: 12px;
            border-radius: 0 8px 8px 0;
            font-size: 0.84rem;
            color: #cbd5e1;
            line-height: 1.5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📡 Pico 2 W - Wi-Fi 訊號強度探測儀</h1>
            <div class="meta">Pico 本機 IP: <strong>{ip}</strong> | 零外接零件 (板載 CYW43439 晶片)</div>
        </div>
        
        <div class="card">
            <div class="toolbar">
                <span style="font-weight: bold; color: #f8fafc;">周遭 Wi-Fi 訊號清單 (共 {len(wifi_list)} 個)</span>
                <a href="/" class="btn">🔄 重新掃描訊號</a>
            </div>
            
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Wi-Fi 名稱 (SSID)</th>
                            <th>頻道</th>
                            <th>訊號強度</th>
                            <th>強度指標</th>
                            <th>等級 (品質)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>

            <div class="tip">
                💡 <strong>物理實證挑戰</strong>：用手掌用力捏住 Pico 2 W 金屬天線罩，點擊「🔄 重新掃描訊號」，觀察上方 dBm 數值是否明顯下降 15 ~ 25 dBm！
            </div>
        </div>
    </div>
</body>
</html>
"""
    return html

def main():
    # 1. 連線 Wi-Fi
    ip = connect_wifi()
    if not ip:
        return
        
    # 2. 建立 Web Server
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", 80))
    server_sock.listen(3)
    
    print("\n" + "=" * 65)
    print("🚀 【Wi-Fi 訊號強度探測儀已啟動！】")
    print(f"👉 請在電腦或手機瀏覽器輸入： http://{ip}")
    print("=" * 65)

    # 3. 初始掃描一次
    current_wifi_list = scan_nearby_wifi()

    while True:
        try:
            client_sock, client_addr = server_sock.accept()
            req_raw = client_sock.recv(512).decode("utf-8", "ignore")
            
            # 每次瀏覽器開啟或點擊重新整理，即時重新掃描周遭 Wi-Fi
            current_wifi_list = scan_nearby_wifi()
            
            # 回傳 HTML 網頁
            html_content = build_html_page(current_wifi_list, ip)
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n" + html_content
            client_sock.sendall(response.encode("utf-8"))
            client_sock.close()
            
        except Exception as e:
            print(f"連線處理異常: {e}")
            
        gc.collect()

if __name__ == "__main__":
    main()
