"""
全球主流电商平台清单（26 个）— 跨境卖家覆盖全球主要市场的真实平台库

每个平台含：
- name        平台中文名
- search_url  搜索 URL 模板（{kw} 替换关键词）
- region      主要市场
- needs_proxy 是否需要特定地区代理
- card_sel / title_sel / price_sel  解析选择器
- status      实测状态（verified/blocked/untested）

注意：站点 URL 和选择器可能随平台升级变化，需要定期复测。
"""
from __future__ import annotations

PLATFORMS = {
    # ════ 北美（美国/加拿大）════
    "amazon": {
        "name": "Amazon US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.amazon.com/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-05",
    },
    "walmart": {
        "name": "Walmart", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.walmart.com/search?q={kw}",
        "card_sel": "div[data-item-id]",
        "title_sel": "span[data-automation-id='product-title']",
        "price_sel": "div[data-automation-id='product-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "PerimeterX (px-captcha) 商业反爬，需 CapSolver 打码",
    },
    "bestbuy": {
        "name": "Best Buy", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.bestbuy.com/site/searchpage.jsp?st={kw}",
        "card_sel": "li.product-list-item",
        "title_sel": "a.product-list-item-link",
        "price_sel": "div[data-testid='price-block-customer-price'] span",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "target": {        "name": "Target", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.target.com/s?searchTerm={kw}",
        "card_sel": "div[data-test='@web/site-top-of-funnel/ProductCardWrapper']",
        "title_sel": "a[data-test='product-title']",
        "price_sel": "span[data-test='current-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
        "note": "2026-06 实测 3/3（yoga mat/kitchen organizer/earbuds 各 20 件），响应较慢 18-25s",
    },
    "ebay": {
        "name": "eBay US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.ebay.com/sch/i.html?_nkw={kw}",
        "card_sel": "li.s-item, li.s-item__pl-on-bp", "title_sel": ".s-item__title",
        "price_sel": ".s-item__price", "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "ebay 商业反爬，需 BrightData 等住宅代理",
    },
    "etsy": {
        "name": "Etsy", "region": "US/Global", "needs_proxy": "US",
        "search_url": "https://www.etsy.com/search?q={kw}",
        "card_sel": "li[data-search-product-id]", "title_sel": "h3",
        "price_sel": "span.currency-value", "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "DataDome 商业反爬，需 CapSolver 打码",
    },
    "newegg": {
        "name": "Newegg", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.newegg.com/p/pl?d={kw}",
        "card_sel": "div.item-cell", "title_sel": "a.item-title",
        "price_sel": "li.price-current", "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-05",
    },
    "wayfair": {
        "name": "Wayfair", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.wayfair.com/keyword.php?keyword={kw}",
        "card_sel": "div[data-hb-id='ProductCard']",
        "title_sel": "h3", "price_sel": "div[data-test='PriceDisplay']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "Wayfair 反爬墙，全引擎拒绝",
    },

    # ════ 拉美 ════
    "mercadolibre_mx": {
        "name": "MercadoLibre MX", "region": "MX", "needs_proxy": "MX",
        "search_url": "https://listado.mercadolibre.com.mx/{kw}",
        "card_sel": "li.ui-search-layout__item",
        "title_sel": "h2.poly-component__title-wrapper",
        "price_sel": "span.andes-money-amount__fraction",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-05",
    },
    "mercadolibre_br": {
        "name": "MercadoLibre BR", "region": "BR", "needs_proxy": "BR",
        "search_url": "https://lista.mercadolivre.com.br/{kw}",
        "card_sel": "li.ui-search-layout__item",
        "title_sel": "h2.poly-component__title-wrapper",
        "price_sel": "span.andes-money-amount__fraction",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-05",
    },

    # ════ 欧洲 ════
    "amazon_uk": {
        "name": "Amazon UK", "region": "UK", "needs_proxy": "UK",
        "search_url": "https://www.amazon.co.uk/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
        "note": "走英国出口节点（multi_country UK 端口 10820）实测 20 件/1 次成功",
    },
    "amazon_de": {
        "name": "Amazon DE", "region": "DE", "needs_proxy": "DE",
        "search_url": "https://www.amazon.de/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
        "note": "走德国出口节点（multi_country DE 端口 10821）实测 20 件/1 次成功",
    },
    "amazon_fr": {
        "name": "Amazon FR", "region": "FR", "needs_proxy": "FR",
        "search_url": "https://www.amazon.fr/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
        "note": "订阅无 FR 节点，走德国邻近节点实测 20 件/1 次成功（EU 同区）",
    },
    "amazon_jp": {
        "name": "Amazon JP", "region": "JP", "needs_proxy": "JP",
        "search_url": "https://www.amazon.co.jp/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-05",
    },
    "cdiscount": {
        "name": "Cdiscount FR", "region": "FR", "needs_proxy": "FR",
        "search_url": "https://www.cdiscount.com/search/10/{kw}.html",
        "card_sel": "article", "title_sel": "h2, h3",
        "price_sel": "[class*='price'], span.price", "rating_sel": None, "asin_in_url": False,
        "status": "partial", "evidence_date": "2026-06",
        "blocker": "间歇：有时返回 14KB 拦截页（0 件），有时正常返回 20 件，需 FR 代理才稳定；已加重试",
    },
    "otto": {
        "name": "Otto DE", "region": "DE", "needs_proxy": "DE",
        "search_url": "https://www.otto.de/suche/{kw}/",
        "card_sel": "[data-product-id]",
        "title_sel": "p.product_title, h2", "price_sel": "p.product_price, [class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-05",
        "note": "需走 botasaurus 引擎绕过反爬",
    },

    # ════ 东南亚 ════
    "shopee_sg": {
        "name": "Shopee SG", "region": "SG", "needs_proxy": "SG",
        "search_url": "https://shopee.sg/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "evidence_date": "2026-06",
        "blocker": "Shopee SPA + 嵌入式 JSON（同 temu/shein），SG 代理过反爬拿到 HTML 但商品数据"
                   "在 WebSocket/嵌入式 state 里，selector + LLM 文本均解析 0 件。反复重试浪费时间，"
                   "已降级 blocked。东南亚选品建议用 Amazon US/JP 对标 + 本地数据需付费 API",
    },
    "shopee_my": {
        "name": "Shopee MY", "region": "MY", "needs_proxy": "MY",
        "search_url": "https://shopee.com.my/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "Shopee SPA 反爬，需登录态 + 马来西亚住宅 IP",
    },
    "lazada_sg": {
        "name": "Lazada SG", "region": "SG", "needs_proxy": "SG",
        "search_url": "https://www.lazada.sg/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
        "note": "2026-06 实测 2/2（yoga mat 20件 + power bank 20件），走 SG 节点 + 浏览器引擎稳定",
    },
    "tokopedia": {
        "name": "Tokopedia ID", "region": "ID", "needs_proxy": "ID",
        "search_url": "https://www.tokopedia.com/search?q={kw}",
        "card_sel": "div.css-llwpbs",
        "title_sel": "span.css-3ahup3", "price_sel": "div.css-h66vau",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "HTTP/2 协议错误 + 印尼地理拦截",
    },

    # ════ 中国跨境 / 全球电商 ════
    "temu": {
        "name": "Temu", "region": "Global", "needs_proxy": None,
        "search_url": "https://www.temu.com/search_result.html?search_key={kw}",
        "card_sel": "[class*='listItem-']", "title_sel": "h2, h3",
        "price_sel": None, "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "evidence_date": "2026-06",
        "blocker": "商品数据嵌在 window.rawData 的 JS 状态里（goodsName/goodsId），不在可见 DOM。"
                   "CSS selector 和 LLM 文本提取都拿不到，需写 JS 状态 JSON 解析器（待开发）",
    },
    "shein": {
        "name": "SHEIN", "region": "Global", "needs_proxy": None,
        "search_url": "https://us.shein.com/pdsearch/{kw}/",
        "card_sel": "li[class*='item']",
        "title_sel": "a[class*='title'], a[aria-label]", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "evidence_date": "2026-06",
        "blocker": "HTML 1.7M chars 但商品数据在嵌入式 JSON 状态里，可见 DOM 无商品卡，"
                   "selector + LLM 文本都 0 件，需写 JSON 状态解析器（待开发）",
    },
    "aliexpress": {
        "name": "AliExpress", "region": "Global", "needs_proxy": "US",
        "search_url": "https://www.aliexpress.com/w/wholesale-{kw}.html",
        "card_sel": "a[href*='/item/']",
        "title_sel": "h3", "price_sel": "[class*='Price--currentPrice']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
        "note": "2026-06 加重试后实测稳定（earbuds 20 件/1 次成功）",
    },
    "alibaba": {
        "name": "Alibaba B2B", "region": "Global", "needs_proxy": None,
        "search_url": "https://www.alibaba.com/trade/search?SearchText={kw}",
        "card_sel": "[data-pid]",
        "title_sel": "h2, [class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "evidence_date": "2026-06",
        "blocker": "重试 3 次均触发 captcha interception（NC 验证码），需打码服务才能稳定突破",
    },
    "1688": {
        "name": "1688 (中国 B2B)", "region": "CN", "needs_proxy": None,
        "search_url": "https://s.1688.com/selloffer/offer_search.htm?keywords={kw}",
        "card_sel": "div.offer-card-box",
        "title_sel": "[class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "阿里 NC 验证码，需打码服务",
    },
    "tiktok_shop": {
        "name": "TikTok Shop US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.tiktok.com/shop/s/{kw}",
        "card_sel": "div[data-e2e='product-card']",
        "title_sel": "div[data-e2e='product-card-title']",
        "price_sel": "span[data-e2e='product-card-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "TikTok Shop 仅 28KB HTML，需 TikTok 登录态",
    },

    # ════ 其他重要市场 ════
    "rakuten": {
        "name": "Rakuten JP", "region": "JP", "needs_proxy": "JP",
        "search_url": "https://search.rakuten.co.jp/search/mall/{kw}/",
        "card_sel": "div.searchresultitem",
        "title_sel": "h2.title", "price_sel": "span.price--3zUvK",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-05",
    },
    "coupang": {
        "name": "Coupang KR", "region": "KR", "needs_proxy": "KR",
        "search_url": "https://www.coupang.com/np/search?q={kw}",
        "card_sel": "li.search-product",
        "title_sel": "div.name", "price_sel": "strong.price-value",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "Coupang access denied，需付费住宅 IP",
    },
    "trendyol": {
        "name": "Trendyol TR", "region": "TR", "needs_proxy": "TR",
        "search_url": "https://www.trendyol.com/sr?q={kw}",
        "card_sel": "div.p-card-wrppr",
        "title_sel": "span.prdct-desc-cntnr-name", "price_sel": "div.prc-box-dscntd",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "Trendyol SPA + 土耳其地理拦截，需 TR 代理",
    },

    # ════ 俄罗斯 + 独联体 ════
    "ozon": {
        "name": "Ozon RU", "region": "RU", "needs_proxy": None,
        "search_url": "https://www.ozon.ru/search/?text={kw}",
        "card_sel": "[data-widget='searchResultsV2'] > div",
        "title_sel": "a", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "Ozon 商业反爬，全引擎拒绝",
    },
    "amazon_in": {
        "name": "Amazon IN", "region": "IN", "needs_proxy": "IN",
        "search_url": "https://www.amazon.in/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
        "note": "走印度出口节点（multi_country IN 端口 10822）实测 20 件/1.9s 极快",
    },
    "wildberries": {
        "name": "Wildberries RU", "region": "RU", "needs_proxy": None,
        "search_url": "https://www.wildberries.ru/catalog/0/search.aspx?search={kw}",
        "card_sel": "article[class*='product']",
        "title_sel": "span.product-card__name, [class*='name']",
        "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "partial", "evidence_date": "2026-06",
        "blocker": "并发场景下不稳定：L1 curl_cffi 拿到 2MB HTML 但 selector 解析 0 件，"
                    "L3 patchright/L6 botasaurus 都 net::ERR_TIMED_OUT 或 Document not ready；"
                    "单 case 偶尔成功但 ProcessPool 并发时 100% 失败。建议俄罗斯只用 yandex_market。",
    },
    "yandex_market": {
        "name": "Yandex Market RU", "region": "RU", "needs_proxy": None,
        "search_url": "https://market.yandex.ru/search?text={kw}",
        "card_sel": "article",
        "title_sel": "span, h3", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-05",
    },

    # ════ 印度 ════
    "flipkart": {
        "name": "Flipkart IN", "region": "IN", "needs_proxy": None,
        "search_url": "https://www.flipkart.com/search?q={kw}",
        "card_sel": "div[data-id]",
        "title_sel": "a.s1Q9rs, div._4rR01T, div.KzDlHZ, a.IRpwTa, div.nZIRY7",
        "price_sel": "div._30jeq3, div.Nx9bqj",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-05",
    },

    # ════ 中东 ════
    "amazon_ae": {
        "name": "Amazon AE", "region": "AE", "needs_proxy": "AE",
        "search_url": "https://www.amazon.ae/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "blocked", "blocker": "需阿联酋本地代理，US IP 仅返回 3.4KB 错误页",
    },
    "noon": {
        "name": "Noon AE/SA", "region": "AE", "needs_proxy": None,
        "search_url": "https://www.noon.com/uae-en/search/?q={kw}",
        "card_sel": "div.productContainer",
        "title_sel": "h2", "price_sel": "strong.amount",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "Noon HTTP/2 协议错误 + 中东地理拦截",
    },

    # ════ 澳大利亚 ════
    "amazon_au": {
        "name": "Amazon AU", "region": "AU", "needs_proxy": "AU",
        "search_url": "https://www.amazon.com.au/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-05",
    },

    # ════ 中国（本土电商，给"卖到中国/国内对标"用）════
    "jd": {
        "name": "京东 JD", "region": "CN", "needs_proxy": None,
        "search_url": "https://search.jd.com/Search?keyword={kw}",
        "card_sel": "li.gl-item",
        "title_sel": "div.p-name em", "price_sel": "div.p-price i",
        "rating_sel": None, "asin_in_url": False,
        "status": "untested", "evidence_date": "2026-06",
        "note": "京东搜索页公开可访问（国内直连，无需代理）；selector 随改版需复测",
    },
    "tmall": {
        "name": "天猫 Tmall", "region": "CN", "needs_proxy": None,
        "search_url": "https://list.tmall.com/search_product.htm?q={kw}",
        "card_sel": "div.product",
        "title_sel": "p.productTitle a", "price_sel": "p.productPrice em",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "阿里系 NC 验证码 + 登录墙，需打码服务",
    },
    "taobao": {
        "name": "淘宝 Taobao", "region": "CN", "needs_proxy": None,
        "search_url": "https://s.taobao.com/search?q={kw}",
        "card_sel": "div[class*='item']",
        "title_sel": "[class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "阿里系 NC 验证码 + 强登录态，需打码服务",
    },
    "pinduoduo": {
        "name": "拼多多 PDD", "region": "CN", "needs_proxy": None,
        "search_url": "https://mobile.yangkeduo.com/search_result.html?search_key={kw}",
        "card_sel": "[class*='goods']",
        "title_sel": "[class*='goodsName'], [class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "PDD 反爬 + 嵌入式 JSON 状态，需专用解析器",
    },
}


# 按地区分组（方便 LLM 决策）
REGIONS = {
    "US": ["amazon", "walmart", "bestbuy", "target", "ebay", "etsy", "newegg", "wayfair", "tiktok_shop"],
    "CA": ["amazon"],  # 加拿大用 amazon.ca（amazon 工具按 geo 切站）
    "UK": ["amazon_uk"],
    "EU": ["amazon_de", "amazon_fr", "cdiscount", "otto"],
    "JP": ["amazon_jp", "rakuten"],
    "KR": ["coupang"],
    "SEA": ["shopee_sg", "shopee_my", "lazada_sg", "tokopedia"],
    "LATAM": ["mercadolibre_mx", "mercadolibre_br"],
    "TR": ["trendyol"],
    "RU": ["ozon", "wildberries", "yandex_market"],
    "IN": ["amazon_in", "flipkart"],
    "AE": ["amazon_ae", "noon"],
    "AU": ["amazon_au"],
    "CN": ["jd", "tmall", "taobao", "pinduoduo"],
    "Global": ["temu", "shein", "aliexpress", "alibaba"],
    "CN_B2B": ["1688", "alibaba"],
}

# 大洲聚合（用户按大洲选时展开为下面的子地区）
CONTINENTS = {
    "North America": ["US", "CA"],
    "South America": ["LATAM"],
    "Europe": ["UK", "EU", "RU", "TR"],
    "Asia": ["JP", "KR", "SEA", "IN", "CN"],
    "Middle East": ["AE"],
    "Oceania": ["AU"],
}


def get_platform(name: str) -> dict | None:
    return PLATFORMS.get(name.lower())


def list_platforms_by_region(region: str = None) -> list[dict]:
    """按地区列平台。region 为空时返回全部"""
    if region and region in REGIONS:
        return [{**PLATFORMS[k], "key": k} for k in REGIONS[region] if k in PLATFORMS]
    return [{**v, "key": k} for k, v in PLATFORMS.items()]


def status_summary() -> dict:
    """返回各状态的平台数量"""
    s = {"verified": [], "untested": [], "blocked": [], "partial": []}
    for k, v in PLATFORMS.items():
        st = v.get("status", "untested")
        s.setdefault(st, []).append(k)
    return {st: {"count": len(ks), "platforms": ks} for st, ks in s.items() if ks}


if __name__ == "__main__":
    import json
    print(f"总平台数: {len(PLATFORMS)}")
    print(json.dumps(status_summary(), ensure_ascii=False, indent=2))
