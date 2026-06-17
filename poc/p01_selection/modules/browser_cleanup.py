"""
浏览器进程看门狗 — 防止僵尸 chrome/chromedriver 累计拖垮机器。

用法：
- kill_orphan_browsers(): 杀掉运行超过 max_age_sec 的孤儿浏览器
- BrowserGuard 上下文管理器: with 块退出时清理
- start_watchdog(): 后台线程每 N 秒清一次
"""
from __future__ import annotations
import time, threading
from loguru import logger

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


BROWSER_NAMES = {"chromedriver.exe", "camoufox.exe", "headless_shell.exe"}
# 注意：不含 chrome.exe/msedge.exe/firefox.exe 通用名 —— 那些可能是用户日常浏览器。
# 爬虫的 chrome 由 patchright 启动，进程名也是 chrome.exe，无法区分。
# 因此默认只清理明确的爬虫专用进程（chromedriver/camoufox/headless_shell）。
# 如需清理爬虫 chrome，用 kill_playwright_chrome()（按命令行参数过滤）。


def kill_playwright_chrome(max_age_sec: int = 300, dry_run: bool = False) -> dict:
    """
    精确清理 playwright/patchright 启动的 chrome（按命令行含 --remote-debugging 或
    --headless 且含 ms-playwright 路径来识别），不误杀用户日常 chrome。
    """
    if not _HAS_PSUTIL:
        return {"method": "no_psutil"}
    now = time.time()
    killed = []
    for proc in psutil.process_iter(["name", "create_time", "pid", "cmdline"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if "chrome" not in name and "headless" not in name:
                continue
            cmdline = " ".join(proc.info.get("cmdline") or []).lower()
            # 爬虫 chrome 特征：playwright 缓存路径 / 自动化标志
            is_automation = ("ms-playwright" in cmdline or "patchright" in cmdline
                              or "--remote-debugging-port" in cmdline
                              or "--headless" in cmdline)
            if not is_automation:
                continue
            age = now - proc.info.get("create_time", now)
            if age > max_age_sec:
                if not dry_run:
                    proc.kill()
                killed.append({"pid": proc.info["pid"], "age_sec": int(age)})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    if killed and not dry_run:
        logger.warning(f"[browser_cleanup] 清理 {len(killed)} 个孤儿爬虫 chrome (>{max_age_sec}s)")
    return {"killed_count": len(killed), "killed": killed, "dry_run": dry_run}


def kill_orphan_browsers(max_age_sec: int = 300, dry_run: bool = False) -> dict:
    """
    杀掉运行时间超过 max_age_sec 的爬虫浏览器进程（chromedriver/camoufox + playwright chrome）。
    只杀爬虫启动的，不误杀用户日常浏览器。
    """
    if not _HAS_PSUTIL:
        return {"method": "no_psutil", "note": "建议 pip install psutil 做精确清理"}
    
    now = time.time()
    killed = []
    # 1) 明确的爬虫专用进程
    for proc in psutil.process_iter(["name", "create_time", "pid"]):
        try:
            name = (proc.info.get("name") or "").lower()
            if name not in BROWSER_NAMES:
                continue
            age = now - proc.info.get("create_time", now)
            if age > max_age_sec:
                if not dry_run:
                    proc.kill()
                killed.append({"pid": proc.info["pid"], "name": name, "age_sec": int(age)})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    # 2) playwright chrome（按命令行过滤）
    pw_result = kill_playwright_chrome(max_age_sec=max_age_sec, dry_run=dry_run)
    
    total = len(killed) + pw_result.get("killed_count", 0)
    if total and not dry_run:
        logger.warning(f"[browser_cleanup] 清理 {total} 个孤儿浏览器 (>{max_age_sec}s)")
    return {"killed_count": total, "spawned_browsers": killed,
            "playwright_chrome": pw_result.get("killed_count", 0),
            "max_age_sec": max_age_sec, "dry_run": dry_run}


def kill_all_browsers() -> dict:
    """强制杀所有爬虫浏览器（任务结束时调用）。"""
    if not _HAS_PSUTIL:
        import subprocess
        for n in ["chrome.exe", "chromedriver.exe", "camoufox.exe"]:
            try:
                subprocess.run(["taskkill", "/F", "/IM", n],
                               capture_output=True, timeout=10)
            except Exception:
                pass
        return {"method": "taskkill_all"}
    
    killed = 0
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if (proc.info.get("name") or "").lower() in BROWSER_NAMES:
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {"killed_count": killed}


_watchdog_thread = None
_watchdog_stop = threading.Event()


def start_watchdog(interval_sec: int = 120, max_age_sec: int = 300):
    """启动后台看门狗线程，每 interval_sec 秒清理一次孤儿浏览器。"""
    global _watchdog_thread
    if _watchdog_thread and _watchdog_thread.is_alive():
        return  # 已启动
    
    def _loop():
        while not _watchdog_stop.is_set():
            try:
                kill_orphan_browsers(max_age_sec=max_age_sec)
            except Exception as e:
                logger.debug(f"[watchdog] {e}")
            _watchdog_stop.wait(interval_sec)
    
    _watchdog_thread = threading.Thread(target=_loop, daemon=True, name="browser-watchdog")
    _watchdog_thread.start()
    logger.info(f"[browser_cleanup] 看门狗已启动（每 {interval_sec}s 清理 >{max_age_sec}s 的孤儿浏览器）")


def stop_watchdog():
    _watchdog_stop.set()


if __name__ == "__main__":
    import json
    print(json.dumps(kill_orphan_browsers(max_age_sec=0, dry_run=True), ensure_ascii=False, indent=2))
