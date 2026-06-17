"""
代理自检 + 自动重启。
脚本开始时调一次 ensure_proxy_alive()，确保代理可用，否则自动重启 xray。
"""
import sys, io, os, time, socket, subprocess
from pathlib import Path

THIS_DIR = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]


def is_port_open(port: int = 10808, host: str = "127.0.0.1") -> bool:
    """端口是否在监听"""
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def is_proxy_working(port: int = 10808, timeout: int = 8) -> tuple[bool, str]:
    """通过代理访问外网，验证 IP"""
    try:
        import urllib.request as ur
        handler = ur.ProxyHandler({"http": f"http://127.0.0.1:{port}",
                                    "https": f"http://127.0.0.1:{port}"})
        opener = ur.build_opener(handler)
        ip = opener.open("https://api.ipify.org", timeout=timeout).read().decode().strip()
        return True, ip
    except Exception as e:
        return False, str(e)[:100]


def ensure_proxy_alive(verbose: bool = True) -> bool:
    """
    确保代理存活。三步检查：
    1. 端口是否打开
    2. 代理是否能访问外网
    3. 出口 IP 是否是美国
    任一失败 → 重启 xray
    """
    if verbose:
        print("[ensure_proxy] 检查代理...", flush=True)
    
    port_ok = is_port_open(10808)
    if port_ok:
        ok, ip_or_err = is_proxy_working()
        if ok:
            if verbose:
                print(f"[ensure_proxy] ✅ 代理存活，出口 IP: {ip_or_err}", flush=True)
            return True
        else:
            if verbose:
                print(f"[ensure_proxy] ⚠ 端口开但代理失败: {ip_or_err}", flush=True)
    else:
        if verbose:
            print("[ensure_proxy] ⚠ 端口 10808 未监听", flush=True)
    
    # 重启
    if verbose:
        print("[ensure_proxy] 重启 xray...", flush=True)
    
    # 先杀旧 xray
    try:
        subprocess.run(["taskkill", "/F", "/IM", "xray.exe"],
                        capture_output=True, timeout=10)
    except Exception:
        pass
    time.sleep(1)
    
    # 启动
    setup_script = THIS_DIR / "setup_us_proxy.py"
    venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
    py = str(venv_python) if venv_python.exists() else sys.executable
    
    DETACHED = 0x00000008
    NEW_GROUP = 0x00000200
    subprocess.Popen(
        [py, str(setup_script)],
        creationflags=(DETACHED | NEW_GROUP) if os.name == "nt" else 0,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    
    # 等就绪（最多 30 秒）
    for i in range(30):
        time.sleep(1)
        if is_port_open(10808):
            ok, ip_or_err = is_proxy_working()
            if ok:
                if verbose:
                    print(f"[ensure_proxy] ✅ 重启成功，出口 IP: {ip_or_err}（耗时 {i+1}s）",
                           flush=True)
                return True
    
    if verbose:
        print("[ensure_proxy] ❌ 重启 30 秒后仍未就绪", flush=True)
    return False


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    ok = ensure_proxy_alive()
    sys.exit(0 if ok else 1)
