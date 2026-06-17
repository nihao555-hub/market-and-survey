import importlib.util, sys
sys.stdout.reconfigure(encoding="utf-8")
pkgs = ['scrapling','curl_cffi','pydoll','botasaurus','botasaurus_driver','camoufox',
        'patchright','pytrends','thefuzz','apscheduler','tenacity','crawl4ai','markitdown',
        'scrapegraphai','prefect','seleniumbase']
for p in pkgs:
    s = importlib.util.find_spec(p)
    print(f"  {p:<22} {'OK' if s else 'MISSING'}")
