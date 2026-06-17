"""看 Amazon UK 返回的 2252 chars 到底是什么"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules.scraper import fetch_with_curl_cffi

html = fetch_with_curl_cffi("https://www.amazon.co.uk/s?k=kitchen+gadgets",
                              proxy="http://127.0.0.1:10808")
print(f"len: {len(html) if html else 0}")
print(html[:2300] if html else "None")
