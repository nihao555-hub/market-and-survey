"""用 SeleniumBase UC Mode（Undetected Chrome）尝试突破 Walmart PerimeterX"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from seleniumbase import SB

URL = "https://www.walmart.com/search?q=yoga+mat"

with SB(uc=True, headless=True, proxy="127.0.0.1:10808",
         locale_code="en-US", incognito=True) as sb:
    sb.uc_open_with_reconnect(URL, 5)  # UC mode 自带 reconnect 绕过验证
    sb.sleep(3)
    # 检测是否触发了 hold 验证
    if sb.is_text_visible("Press & Hold"):
        print("⚠️ Press & Hold 触发，尝试 click_and_hold...")
        try:
            sb.uc_click("button[id='px-captcha']", reconnect_time=4)
        except Exception as e:
            print(f"  click 失败: {e}")
    sb.sleep(5)
    html = sb.get_page_source()
    print(f"len: {len(html)}")
    Path("walmart_uc.html").write_text(html[:300000], encoding="utf-8")
    print(f"  has 'data-item-id': {'data-item-id' in html}")
    print(f"  has 'data-testid': {'data-testid' in html}")
    print(f"  has 'press & hold': {'press & hold' in html.lower()}")
    print(f"  has 'robot or human': {'robot or human' in html.lower()}")
