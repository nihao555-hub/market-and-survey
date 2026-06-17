"""直接 raw 看 amazon UK 响应"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

from curl_cffi import requests as cc

r = cc.get("https://www.amazon.co.uk/s?k=kitchen+gadgets",
           impersonate="chrome120",
           proxies={"http": "http://127.0.0.1:10808", "https": "http://127.0.0.1:10808"},
           timeout=20,
           headers={"Accept-Language": "en-GB,en;q=0.9"})
print(f"status={r.status_code}, len={len(r.text)}")
print("---")
print(r.text[:3000])
