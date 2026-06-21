"""
全球主流电商平台清单（80+ 个）— 跨境卖家覆盖全球所有主要市场的真实平台库

每个平台含：
- name        平台中文名
- search_url  搜索 URL 模板（{kw} 替换关键词）
- region      主要市场（ISO 国家码）
- needs_proxy 是否需要特定地区代理
- card_sel / title_sel / price_sel  解析选择器
- status      实测状态（verified/blocked/untested/scraperapi）
  - scraperapi: 未直接验证，但可通过 ScraperAPI 代理访问

注意：站点 URL 和选择器可能随平台升级变化，需要定期复测。
更新日期：2026-06
"""
from __future__ import annotations

PLATFORMS = {
    # ══════════════════════════════════════════════════════════════════════
    # 北美（美国 / 加拿大）
    # ══════════════════════════════════════════════════════════════════════
    "amazon": {
        "name": "Amazon US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.amazon.com/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
    },
    "amazon_ca": {
        "name": "Amazon CA", "region": "CA", "needs_proxy": "CA",
        "search_url": "https://www.amazon.ca/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "walmart": {
        "name": "Walmart US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.walmart.com/search?q={kw}",
        "card_sel": "div[data-item-id]",
        "title_sel": "span[data-automation-id='product-title']",
        "price_sel": "div[data-automation-id='product-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "walmart_ca": {
        "name": "Walmart CA", "region": "CA", "needs_proxy": "CA",
        "search_url": "https://www.walmart.ca/search?q={kw}",
        "card_sel": "div[data-item-id]",
        "title_sel": "[data-automation='product-title']",
        "price_sel": "[data-automation='current-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "bestbuy": {
        "name": "Best Buy US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.bestbuy.com/site/searchpage.jsp?st={kw}",
        "card_sel": "li.product-list-item",
        "title_sel": "a.product-list-item-link",
        "price_sel": "div[data-testid='price-block-customer-price'] span",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "target": {
        "name": "Target US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.target.com/s?searchTerm={kw}",
        "card_sel": "div[data-test='@web/site-top-of-funnel/ProductCardWrapper']",
        "title_sel": "a[data-test='product-title']",
        "price_sel": "span[data-test='current-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "ebay": {
        "name": "eBay US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.ebay.com/sch/i.html?_nkw={kw}",
        "card_sel": "li.s-item, li.s-item__pl-on-bp", "title_sel": ".s-item__title",
        "price_sel": ".s-item__price", "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "etsy": {
        "name": "Etsy", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.etsy.com/search?q={kw}",
        "card_sel": "li[data-search-product-id]", "title_sel": "h3",
        "price_sel": "span.currency-value", "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "newegg": {
        "name": "Newegg US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.newegg.com/p/pl?d={kw}",
        "card_sel": "div.item-cell", "title_sel": "a.item-title",
        "price_sel": "li.price-current", "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "wayfair": {
        "name": "Wayfair US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.wayfair.com/keyword.php?keyword={kw}",
        "card_sel": "div[data-hb-id='ProductCard']",
        "title_sel": "h3", "price_sel": "div[data-test='PriceDisplay']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "costco": {
        "name": "Costco US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.costco.com/CatalogSearch?dept=All&keyword={kw}",
        "card_sel": "div.product-tile",
        "title_sel": "span.description", "price_sel": "div.price",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "homedepot": {
        "name": "Home Depot US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.homedepot.com/s/{kw}",
        "card_sel": "div[data-testid='product-pod']",
        "title_sel": "span[data-testid='product-header']", "price_sel": "span[data-testid='product-pod-price-value']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "tiktok_shop": {
        "name": "TikTok Shop US", "region": "US", "needs_proxy": "US",
        "search_url": "https://www.tiktok.com/shop/s/{kw}",
        "card_sel": "div[data-e2e='product-card']",
        "title_sel": "div[data-e2e='product-card-title']",
        "price_sel": "span[data-e2e='product-card-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "blocked", "blocker": "TikTok Shop 需登录态，通过 TikHub API 获取数据",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 拉丁美洲（墨西哥 / 巴西 / 阿根廷 / 哥伦比亚 / 智利）
    # ══════════════════════════════════════════════════════════════════════
    "mercadolibre_mx": {
        "name": "MercadoLibre MX", "region": "MX", "needs_proxy": "MX",
        "search_url": "https://listado.mercadolibre.com.mx/{kw}",
        "card_sel": "li.ui-search-layout__item",
        "title_sel": "h2.poly-component__title-wrapper",
        "price_sel": "span.andes-money-amount__fraction",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "mercadolibre_br": {
        "name": "MercadoLivre BR", "region": "BR", "needs_proxy": "BR",
        "search_url": "https://lista.mercadolivre.com.br/{kw}",
        "card_sel": "li.ui-search-layout__item",
        "title_sel": "h2.poly-component__title-wrapper",
        "price_sel": "span.andes-money-amount__fraction",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "mercadolibre_ar": {
        "name": "MercadoLibre AR", "region": "AR", "needs_proxy": "AR",
        "search_url": "https://listado.mercadolibre.com.ar/{kw}",
        "card_sel": "li.ui-search-layout__item",
        "title_sel": "h2.poly-component__title-wrapper",
        "price_sel": "span.andes-money-amount__fraction",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "mercadolibre_co": {
        "name": "MercadoLibre CO", "region": "CO", "needs_proxy": "CO",
        "search_url": "https://listado.mercadolibre.com.co/{kw}",
        "card_sel": "li.ui-search-layout__item",
        "title_sel": "h2.poly-component__title-wrapper",
        "price_sel": "span.andes-money-amount__fraction",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "mercadolibre_cl": {
        "name": "MercadoLibre CL", "region": "CL", "needs_proxy": "CL",
        "search_url": "https://listado.mercadolibre.cl/{kw}",
        "card_sel": "li.ui-search-layout__item",
        "title_sel": "h2.poly-component__title-wrapper",
        "price_sel": "span.andes-money-amount__fraction",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "amazon_br": {
        "name": "Amazon BR", "region": "BR", "needs_proxy": "BR",
        "search_url": "https://www.amazon.com.br/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "amazon_mx": {
        "name": "Amazon MX", "region": "MX", "needs_proxy": "MX",
        "search_url": "https://www.amazon.com.mx/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "falabella": {
        "name": "Falabella CL/CO/PE", "region": "CL", "needs_proxy": "CL",
        "search_url": "https://www.falabella.com/falabella-cl/search?Ntt={kw}",
        "card_sel": "div.pod-4_GRID",
        "title_sel": "b.pod-subTitle", "price_sel": "li.prices-0 span",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 欧洲（英国 / 德国 / 法国 / 意大利 / 西班牙 / 荷兰 / 波兰 / 瑞典）
    # ══════════════════════════════════════════════════════════════════════
    "amazon_uk": {
        "name": "Amazon UK", "region": "UK", "needs_proxy": "UK",
        "search_url": "https://www.amazon.co.uk/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
    },
    "amazon_de": {
        "name": "Amazon DE", "region": "DE", "needs_proxy": "DE",
        "search_url": "https://www.amazon.de/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
    },
    "amazon_fr": {
        "name": "Amazon FR", "region": "FR", "needs_proxy": "FR",
        "search_url": "https://www.amazon.fr/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
    },
    "amazon_it": {
        "name": "Amazon IT", "region": "IT", "needs_proxy": "IT",
        "search_url": "https://www.amazon.it/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "amazon_es": {
        "name": "Amazon ES", "region": "ES", "needs_proxy": "ES",
        "search_url": "https://www.amazon.es/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "amazon_nl": {
        "name": "Amazon NL", "region": "NL", "needs_proxy": "NL",
        "search_url": "https://www.amazon.nl/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "amazon_pl": {
        "name": "Amazon PL", "region": "PL", "needs_proxy": "PL",
        "search_url": "https://www.amazon.pl/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "amazon_se": {
        "name": "Amazon SE", "region": "SE", "needs_proxy": "SE",
        "search_url": "https://www.amazon.se/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "otto": {
        "name": "Otto DE", "region": "DE", "needs_proxy": "DE",
        "search_url": "https://www.otto.de/suche/{kw}/",
        "card_sel": "[data-product-id]",
        "title_sel": "p.product_title, h2", "price_sel": "p.product_price, [class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "zalando": {
        "name": "Zalando EU", "region": "DE", "needs_proxy": "DE",
        "search_url": "https://www.zalando.de/katalog/?q={kw}",
        "card_sel": "article[class*='product']",
        "title_sel": "h3", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "欧洲最大时尚电商，覆盖 DE/FR/IT/ES/NL/PL/SE 等 25 国",
    },
    "cdiscount": {
        "name": "Cdiscount FR", "region": "FR", "needs_proxy": "FR",
        "search_url": "https://www.cdiscount.com/search/10/{kw}.html",
        "card_sel": "article", "title_sel": "h2, h3",
        "price_sel": "[class*='price'], span.price", "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "bol_com": {
        "name": "Bol.com NL/BE", "region": "NL", "needs_proxy": "NL",
        "search_url": "https://www.bol.com/nl/nl/s/?searchtext={kw}",
        "card_sel": "li[data-test='product-item']",
        "title_sel": "a[data-test='product-title']", "price_sel": "span[data-test='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "荷兰+比利时最大电商",
    },
    "allegro": {
        "name": "Allegro PL", "region": "PL", "needs_proxy": "PL",
        "search_url": "https://allegro.pl/listing?string={kw}",
        "card_sel": "article[data-role='offer']",
        "title_sel": "h2 a", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "波兰最大电商，东欧市场核心平台",
    },
    "emag": {
        "name": "eMAG RO/HU/BG", "region": "RO", "needs_proxy": "RO",
        "search_url": "https://www.emag.ro/search/{kw}",
        "card_sel": "div.card-item",
        "title_sel": "a.product-title", "price_sel": "p.product-new-price",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "罗马尼亚/匈牙利/保加利亚最大电商",
    },
    "ebay_uk": {
        "name": "eBay UK", "region": "UK", "needs_proxy": "UK",
        "search_url": "https://www.ebay.co.uk/sch/i.html?_nkw={kw}",
        "card_sel": "li.s-item", "title_sel": ".s-item__title",
        "price_sel": ".s-item__price", "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "ebay_de": {
        "name": "eBay DE", "region": "DE", "needs_proxy": "DE",
        "search_url": "https://www.ebay.de/sch/i.html?_nkw={kw}",
        "card_sel": "li.s-item", "title_sel": ".s-item__title",
        "price_sel": ".s-item__price", "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 东南亚（新加坡 / 马来西亚 / 印尼 / 泰国 / 越南 / 菲律宾）
    # ══════════════════════════════════════════════════════════════════════
    "shopee_sg": {
        "name": "Shopee SG", "region": "SG", "needs_proxy": "SG",
        "search_url": "https://shopee.sg/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "shopee_my": {
        "name": "Shopee MY", "region": "MY", "needs_proxy": "MY",
        "search_url": "https://shopee.com.my/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "shopee_th": {
        "name": "Shopee TH", "region": "TH", "needs_proxy": "TH",
        "search_url": "https://shopee.co.th/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "shopee_vn": {
        "name": "Shopee VN", "region": "VN", "needs_proxy": "VN",
        "search_url": "https://shopee.vn/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "shopee_ph": {
        "name": "Shopee PH", "region": "PH", "needs_proxy": "PH",
        "search_url": "https://shopee.ph/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "shopee_id": {
        "name": "Shopee ID", "region": "ID", "needs_proxy": "ID",
        "search_url": "https://shopee.co.id/search?keyword={kw}",
        "card_sel": "li.shopee-search-item-result__item",
        "title_sel": "div[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "lazada_sg": {
        "name": "Lazada SG", "region": "SG", "needs_proxy": "SG",
        "search_url": "https://www.lazada.sg/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "lazada_my": {
        "name": "Lazada MY", "region": "MY", "needs_proxy": "MY",
        "search_url": "https://www.lazada.com.my/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "lazada_th": {
        "name": "Lazada TH", "region": "TH", "needs_proxy": "TH",
        "search_url": "https://www.lazada.co.th/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "lazada_vn": {
        "name": "Lazada VN", "region": "VN", "needs_proxy": "VN",
        "search_url": "https://www.lazada.vn/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "lazada_ph": {
        "name": "Lazada PH", "region": "PH", "needs_proxy": "PH",
        "search_url": "https://www.lazada.com.ph/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "lazada_id": {
        "name": "Lazada ID", "region": "ID", "needs_proxy": "ID",
        "search_url": "https://www.lazada.co.id/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "tokopedia": {
        "name": "Tokopedia ID", "region": "ID", "needs_proxy": "ID",
        "search_url": "https://www.tokopedia.com/search?q={kw}",
        "card_sel": "div.css-llwpbs",
        "title_sel": "span.css-3ahup3", "price_sel": "div.css-h66vau",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "tiki_vn": {
        "name": "Tiki VN", "region": "VN", "needs_proxy": "VN",
        "search_url": "https://tiki.vn/search?q={kw}",
        "card_sel": "a[data-view-id='product_list_item']",
        "title_sel": "div.name h3", "price_sel": "div.price-discount__price",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "越南第二大电商平台",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 日本 / 韩国
    # ══════════════════════════════════════════════════════════════════════
    "amazon_jp": {
        "name": "Amazon JP", "region": "JP", "needs_proxy": "JP",
        "search_url": "https://www.amazon.co.jp/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
    },
    "rakuten": {
        "name": "Rakuten JP", "region": "JP", "needs_proxy": "JP",
        "search_url": "https://search.rakuten.co.jp/search/mall/{kw}/",
        "card_sel": "div.searchresultitem",
        "title_sel": "h2.title", "price_sel": "span.price--3zUvK",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "yahoo_shopping_jp": {
        "name": "Yahoo Shopping JP", "region": "JP", "needs_proxy": "JP",
        "search_url": "https://shopping.yahoo.co.jp/search?p={kw}",
        "card_sel": "div[class*='ProductItem']",
        "title_sel": "a[class*='title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "coupang": {
        "name": "Coupang KR", "region": "KR", "needs_proxy": "KR",
        "search_url": "https://www.coupang.com/np/search?q={kw}",
        "card_sel": "li.search-product",
        "title_sel": "div.name", "price_sel": "strong.price-value",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "gmarket_kr": {
        "name": "Gmarket KR", "region": "KR", "needs_proxy": "KR",
        "search_url": "https://browse.gmarket.co.kr/search?keyword={kw}",
        "card_sel": "div.box__item-container",
        "title_sel": "span.text__item", "price_sel": "strong.text__value",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "韩国第二大综合电商",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 俄罗斯 + 独联体
    # ══════════════════════════════════════════════════════════════════════
    "ozon": {
        "name": "Ozon RU", "region": "RU", "needs_proxy": "RU",
        "search_url": "https://www.ozon.ru/search/?text={kw}",
        "card_sel": "[data-widget='searchResultsV2'] > div",
        "title_sel": "a", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "wildberries": {
        "name": "Wildberries RU", "region": "RU", "needs_proxy": "RU",
        "search_url": "https://www.wildberries.ru/catalog/0/search.aspx?search={kw}",
        "card_sel": "article[class*='product']",
        "title_sel": "span.product-card__name, [class*='name']",
        "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "俄罗斯最大电商（月访问量超 Ozon），ScraperAPI 可绕过反爬",
    },
    "yandex_market": {
        "name": "Yandex Market RU", "region": "RU", "needs_proxy": "RU",
        "search_url": "https://market.yandex.ru/search?text={kw}",
        "card_sel": "article",
        "title_sel": "span, h3", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "kaspi_kz": {
        "name": "Kaspi KZ", "region": "KZ", "needs_proxy": "KZ",
        "search_url": "https://kaspi.kz/shop/search/?text={kw}",
        "card_sel": "div[class*='item-card']",
        "title_sel": "a.item-card__name", "price_sel": "span.item-card__prices-price",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "哈萨克斯坦最大电商",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 印度 / 南亚
    # ══════════════════════════════════════════════════════════════════════
    "amazon_in": {
        "name": "Amazon IN", "region": "IN", "needs_proxy": "IN",
        "search_url": "https://www.amazon.in/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
    },
    "flipkart": {
        "name": "Flipkart IN", "region": "IN", "needs_proxy": "IN",
        "search_url": "https://www.flipkart.com/search?q={kw}",
        "card_sel": "div[data-id]",
        "title_sel": "a.s1Q9rs, div._4rR01T, div.KzDlHZ, a.IRpwTa, div.nZIRY7",
        "price_sel": "div._30jeq3, div.Nx9bqj",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "myntra": {
        "name": "Myntra IN", "region": "IN", "needs_proxy": "IN",
        "search_url": "https://www.myntra.com/{kw}",
        "card_sel": "li.product-base",
        "title_sel": "h3.product-brand", "price_sel": "span.product-discountedPrice",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "印度最大时尚电商",
    },
    "daraz_pk": {
        "name": "Daraz PK", "region": "PK", "needs_proxy": "PK",
        "search_url": "https://www.daraz.pk/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "巴基斯坦/孟加拉最大电商（Lazada 系）",
    },
    "daraz_bd": {
        "name": "Daraz BD", "region": "BD", "needs_proxy": "BD",
        "search_url": "https://www.daraz.com.bd/catalog/?q={kw}",
        "card_sel": "div[data-qa-locator='product-item']",
        "title_sel": "div.RfADt a", "price_sel": "span.ooOxS",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 中东（阿联酋 / 沙特 / 土耳其）
    # ══════════════════════════════════════════════════════════════════════
    "amazon_ae": {
        "name": "Amazon AE", "region": "AE", "needs_proxy": "AE",
        "search_url": "https://www.amazon.ae/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "amazon_sa": {
        "name": "Amazon SA", "region": "SA", "needs_proxy": "SA",
        "search_url": "https://www.amazon.sa/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "noon": {
        "name": "Noon AE/SA", "region": "AE", "needs_proxy": "AE",
        "search_url": "https://www.noon.com/uae-en/search/?q={kw}",
        "card_sel": "div.productContainer",
        "title_sel": "h2", "price_sel": "strong.amount",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "中东本土最大电商（阿联酋+沙特+埃及）",
    },
    "noon_sa": {
        "name": "Noon SA", "region": "SA", "needs_proxy": "SA",
        "search_url": "https://www.noon.com/saudi-en/search/?q={kw}",
        "card_sel": "div.productContainer",
        "title_sel": "h2", "price_sel": "strong.amount",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "trendyol": {
        "name": "Trendyol TR", "region": "TR", "needs_proxy": "TR",
        "search_url": "https://www.trendyol.com/sr?q={kw}",
        "card_sel": "div.p-card-wrppr",
        "title_sel": "span.prdct-desc-cntnr-name", "price_sel": "div.prc-box-dscntd",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "土耳其最大电商，月活超 3000 万",
    },
    "hepsiburada": {
        "name": "Hepsiburada TR", "region": "TR", "needs_proxy": "TR",
        "search_url": "https://www.hepsiburada.com/ara?q={kw}",
        "card_sel": "li[class*='productListContent']",
        "title_sel": "h3[data-test-id='product-card-name']", "price_sel": "div[data-test-id='price-current-price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "土耳其第二大电商",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 澳大利亚 / 新西兰
    # ══════════════════════════════════════════════════════════════════════
    "amazon_au": {
        "name": "Amazon AU", "region": "AU", "needs_proxy": "AU",
        "search_url": "https://www.amazon.com.au/s?k={kw}",
        "card_sel": "div[data-component-type='s-search-result']",
        "title_sel": "h2 span", "price_sel": "span.a-price span.a-offscreen",
        "rating_sel": "span.a-icon-alt", "asin_in_url": True,
        "status": "verified", "evidence_date": "2026-06",
    },
    "catch_au": {
        "name": "Catch AU", "region": "AU", "needs_proxy": "AU",
        "search_url": "https://www.catch.com.au/search?q={kw}",
        "card_sel": "div[class*='product-card']",
        "title_sel": "h3", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "澳洲第二大综合电商",
    },
    "trademe_nz": {
        "name": "TradeMe NZ", "region": "NZ", "needs_proxy": "NZ",
        "search_url": "https://www.trademe.co.nz/a/search?search_string={kw}",
        "card_sel": "div[class*='listing-card']",
        "title_sel": "div[class*='title']", "price_sel": "div[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "新西兰最大电商/拍卖平台",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 非洲（尼日利亚 / 肯尼亚 / 埃及 / 南非 / 加纳）
    # ══════════════════════════════════════════════════════════════════════
    "jumia_ng": {
        "name": "Jumia NG", "region": "NG", "needs_proxy": "NG",
        "search_url": "https://www.jumia.com.ng/catalog/?q={kw}",
        "card_sel": "article.prd",
        "title_sel": "h3.name", "price_sel": "div.prc",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "非洲最大电商，覆盖 11 国",
    },
    "jumia_ke": {
        "name": "Jumia KE", "region": "KE", "needs_proxy": "KE",
        "search_url": "https://www.jumia.co.ke/catalog/?q={kw}",
        "card_sel": "article.prd",
        "title_sel": "h3.name", "price_sel": "div.prc",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "jumia_eg": {
        "name": "Jumia EG", "region": "EG", "needs_proxy": "EG",
        "search_url": "https://www.jumia.com.eg/catalog/?q={kw}",
        "card_sel": "article.prd",
        "title_sel": "h3.name", "price_sel": "div.prc",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "jumia_gh": {
        "name": "Jumia GH", "region": "GH", "needs_proxy": "GH",
        "search_url": "https://www.jumia.com.gh/catalog/?q={kw}",
        "card_sel": "article.prd",
        "title_sel": "h3.name", "price_sel": "div.prc",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "takealot": {
        "name": "Takealot ZA", "region": "ZA", "needs_proxy": "ZA",
        "search_url": "https://www.takealot.com/all?qsearch={kw}",
        "card_sel": "div[class*='product-card']",
        "title_sel": "h4[class*='product-title']", "price_sel": "span[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "南非最大电商",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 中国跨境 / 全球电商
    # ══════════════════════════════════════════════════════════════════════
    "aliexpress": {
        "name": "AliExpress", "region": "Global", "needs_proxy": "US",
        "search_url": "https://www.aliexpress.com/w/wholesale-{kw}.html",
        "card_sel": "a[href*='/item/']",
        "title_sel": "h3", "price_sel": "[class*='Price--currentPrice']",
        "rating_sel": None, "asin_in_url": False,
        "status": "verified", "evidence_date": "2026-06",
    },
    "temu": {
        "name": "Temu", "region": "Global", "needs_proxy": "US",
        "search_url": "https://www.temu.com/search_result.html?search_key={kw}",
        "card_sel": "[class*='listItem-']", "title_sel": "h2, h3",
        "price_sel": None, "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "全球增长最快的跨境电商（拼多多旗下），覆盖 50+ 国家",
    },
    "shein": {
        "name": "SHEIN", "region": "Global", "needs_proxy": "US",
        "search_url": "https://us.shein.com/pdsearch/{kw}/",
        "card_sel": "li[class*='item']",
        "title_sel": "a[class*='title'], a[aria-label]", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
        "note": "全球快时尚电商巨头，覆盖 150+ 国家",
    },
    "alibaba": {
        "name": "Alibaba B2B", "region": "Global", "needs_proxy": "US",
        "search_url": "https://www.alibaba.com/trade/search?SearchText={kw}",
        "card_sel": "[data-pid]",
        "title_sel": "h2, [class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },

    # ══════════════════════════════════════════════════════════════════════
    # 中国本土电商（国内对标/货源查找）
    # ══════════════════════════════════════════════════════════════════════
    "jd": {
        "name": "京东 JD", "region": "CN", "needs_proxy": "CN",
        "search_url": "https://search.jd.com/Search?keyword={kw}",
        "card_sel": "li.gl-item",
        "title_sel": "div.p-name em", "price_sel": "div.p-price i",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "tmall": {
        "name": "天猫 Tmall", "region": "CN", "needs_proxy": "CN",
        "search_url": "https://list.tmall.com/search_product.htm?q={kw}",
        "card_sel": "div.product",
        "title_sel": "p.productTitle a", "price_sel": "p.productPrice em",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "taobao": {
        "name": "淘宝 Taobao", "region": "CN", "needs_proxy": "CN",
        "search_url": "https://s.taobao.com/search?q={kw}",
        "card_sel": "div[class*='item']",
        "title_sel": "[class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "pinduoduo": {
        "name": "拼多多 PDD", "region": "CN", "needs_proxy": "CN",
        "search_url": "https://mobile.yangkeduo.com/search_result.html?search_key={kw}",
        "card_sel": "[class*='goods']",
        "title_sel": "[class*='goodsName'], [class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
    "1688": {
        "name": "1688 (中国 B2B)", "region": "CN", "needs_proxy": "CN",
        "search_url": "https://s.1688.com/selloffer/offer_search.htm?keywords={kw}",
        "card_sel": "div.offer-card-box",
        "title_sel": "[class*='title']", "price_sel": "[class*='price']",
        "rating_sel": None, "asin_in_url": False,
        "status": "scraperapi", "evidence_date": "2026-06",
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# 按国家分组 — Agent 根据用户选择的国家自动挑选该国主流电商平台
# ═══════════════════════════════════════════════════════════════════════════
COUNTRY_PLATFORMS = {
    # 北美
    "US": ["amazon", "walmart", "bestbuy", "target", "ebay", "etsy", "newegg", "wayfair", "costco", "homedepot", "tiktok_shop"],
    "CA": ["amazon_ca", "walmart_ca", "ebay"],
    # 拉丁美洲
    "MX": ["mercadolibre_mx", "amazon_mx"],
    "BR": ["mercadolibre_br", "amazon_br"],
    "AR": ["mercadolibre_ar"],
    "CO": ["mercadolibre_co", "falabella"],
    "CL": ["mercadolibre_cl", "falabella"],
    # 欧洲
    "UK": ["amazon_uk", "ebay_uk"],
    "DE": ["amazon_de", "otto", "zalando", "ebay_de"],
    "FR": ["amazon_fr", "cdiscount"],
    "IT": ["amazon_it"],
    "ES": ["amazon_es"],
    "NL": ["amazon_nl", "bol_com"],
    "PL": ["amazon_pl", "allegro"],
    "SE": ["amazon_se"],
    "RO": ["emag"],
    # 俄罗斯 + 独联体
    "RU": ["ozon", "wildberries", "yandex_market"],
    "KZ": ["kaspi_kz"],
    # 日韩
    "JP": ["amazon_jp", "rakuten", "yahoo_shopping_jp"],
    "KR": ["coupang", "gmarket_kr"],
    # 东南亚
    "SG": ["shopee_sg", "lazada_sg"],
    "MY": ["shopee_my", "lazada_my"],
    "TH": ["shopee_th", "lazada_th"],
    "VN": ["shopee_vn", "lazada_vn", "tiki_vn"],
    "PH": ["shopee_ph", "lazada_ph"],
    "ID": ["shopee_id", "lazada_id", "tokopedia"],
    # 南亚
    "IN": ["amazon_in", "flipkart", "myntra"],
    "PK": ["daraz_pk"],
    "BD": ["daraz_bd"],
    # 中东
    "AE": ["amazon_ae", "noon"],
    "SA": ["amazon_sa", "noon_sa"],
    "TR": ["trendyol", "hepsiburada"],
    # 大洋洲
    "AU": ["amazon_au", "catch_au"],
    "NZ": ["trademe_nz"],
    # 非洲
    "NG": ["jumia_ng"],
    "KE": ["jumia_ke"],
    "EG": ["jumia_eg"],
    "GH": ["jumia_gh"],
    "ZA": ["takealot"],
    # 中国
    "CN": ["jd", "tmall", "taobao", "pinduoduo", "1688"],
    # 全球跨境
    "Global": ["aliexpress", "temu", "shein", "alibaba"],
}

# 兼容旧的 REGIONS 接口
REGIONS = COUNTRY_PLATFORMS

# 大洲聚合（用户按大洲选时展开为下面的子地区）
CONTINENTS = {
    "North America": ["US", "CA"],
    "South America": ["MX", "BR", "AR", "CO", "CL"],
    "Europe": ["UK", "DE", "FR", "IT", "ES", "NL", "PL", "SE", "RO"],
    "Russia & CIS": ["RU", "KZ"],
    "East Asia": ["JP", "KR", "CN"],
    "Southeast Asia": ["SG", "MY", "TH", "VN", "PH", "ID"],
    "South Asia": ["IN", "PK", "BD"],
    "Middle East": ["AE", "SA", "TR"],
    "Oceania": ["AU", "NZ"],
    "Africa": ["NG", "KE", "EG", "GH", "ZA"],
}

# 国家名称映射（中文）
COUNTRY_NAMES = {
    "US": "美国", "CA": "加拿大", "MX": "墨西哥", "BR": "巴西", "AR": "阿根廷",
    "CO": "哥伦比亚", "CL": "智利", "UK": "英国", "DE": "德国", "FR": "法国",
    "IT": "意大利", "ES": "西班牙", "NL": "荷兰", "PL": "波兰", "SE": "瑞典",
    "RO": "罗马尼亚", "RU": "俄罗斯", "KZ": "哈萨克斯坦", "JP": "日本", "KR": "韩国",
    "SG": "新加坡", "MY": "马来西亚", "TH": "泰国", "VN": "越南", "PH": "菲律宾",
    "ID": "印尼", "IN": "印度", "PK": "巴基斯坦", "BD": "孟加拉", "AE": "阿联酋",
    "SA": "沙特", "TR": "土耳其", "AU": "澳大利亚", "NZ": "新西兰", "NG": "尼日利亚",
    "KE": "肯尼亚", "EG": "埃及", "GH": "加纳", "ZA": "南非", "CN": "中国",
}


def get_platform(name: str) -> dict | None:
    return PLATFORMS.get(name.lower())


def list_platforms_by_region(region: str = None) -> list[dict]:
    """按地区列平台。region 为空时返回全部"""
    if region and region in REGIONS:
        return [{**PLATFORMS[k], "key": k} for k in REGIONS[region] if k in PLATFORMS]
    return [{**v, "key": k} for k, v in PLATFORMS.items()]


def list_platforms_by_countries(countries: list[str]) -> list[dict]:
    """
    按国家代码列表获取对应的主流电商平台。
    支持多选国家（如 ["US", "JP", "DE"]），自动去重。
    返回带 country 字段的平台列表。
    """
    seen = set()
    result = []
    for country in countries:
        code = country.upper()
        platforms = COUNTRY_PLATFORMS.get(code, [])
        for key in platforms:
            if key not in seen and key in PLATFORMS:
                seen.add(key)
                result.append({
                    **PLATFORMS[key],
                    "key": key,
                    "country": code,
                    "country_name": COUNTRY_NAMES.get(code, code),
                })
    return result


def list_available_countries() -> list[dict]:
    """返回所有支持的国家列表（含中文名和平台数）"""
    return [
        {
            "code": code,
            "name": COUNTRY_NAMES.get(code, code),
            "platform_count": len(platforms),
            "platforms": platforms,
        }
        for code, platforms in COUNTRY_PLATFORMS.items()
        if code != "Global"
    ]


def status_summary() -> dict:
    """返回各状态的平台数量"""
    s = {"verified": [], "untested": [], "blocked": [], "partial": [], "scraperapi": []}
    for k, v in PLATFORMS.items():
        st = v.get("status", "untested")
        s.setdefault(st, []).append(k)
    return {st: {"count": len(ks), "platforms": ks} for st, ks in s.items() if ks}


if __name__ == "__main__":
    import json
    print(f"总平台数: {len(PLATFORMS)}")
    print(f"覆盖国家数: {len(COUNTRY_PLATFORMS)}")
    print(f"覆盖大洲数: {len(CONTINENTS)}")
    print(json.dumps(status_summary(), ensure_ascii=False, indent=2))
