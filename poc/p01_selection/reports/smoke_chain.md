## 1. discover_bsr_url (LLM 给关键词，工具自动发现真实子类目)
- search_url: https://www.amazon.com/s?k=wireless%20earbuds
- 候选数: 0

## 2. get_bestsellers_by_url 抓真品
- ⚠ 没发现 BSR 候选 URL

## 3. 真实评论 + 关键词云

## 4. 1688 采购成本（真实抓取，失败时返回 error）
```json
{
  "category": "蓝牙耳机",
  "source_url": "https://s.1688.com/selloffer/offer_search.htm?keywords=%E8%93%9D%E7%89%99%E8%80%B3%E6%9C%BA",
  "real_data": false,
  "error": "no items parsed",
  "alternative_data_sources": [
    "Amazon BSR 商品的同款 1688 反查（输入 ASIN/标题搜 1688）",
    "Made-in-China.com（有些品类反爬较弱）",
    "AliExpress B2B（通过 dropship 供应商页）",
    "采购方人工录入（最准确）"
  ],
  "next_step": "候选品确定后，把 ASIN 标题翻译成中文，调用 search_1688 用具体型号搜，命中率更高"
}
```

## 5. 真实成本参数（关税+佣金+FBA+汇率）
```json
{
  "amazon_referral_rate": 0.08,
  "fba_fulfillment_fee": 3.06,
  "duty_rate": 0.045,
  "exchange_loss": 0.05,
  "_metadata": {
    "category": "headphones",
    "weight_oz": 4,
    "longest_in": 5,
    "hs_code": "8518.30",
    "fx_rate_usd_cny": 6.786741,
    "data_sources": [
      "Amazon Referral Fee 2026",
      "Amazon FBA Standard Size 2026",
      "USITC HTS 2026",
      "open.er-api.com 实时汇率"
    ]
  }
}
```

## 6. 完整 14 项成本测算（真实参数）
- 净利: $16.77 毛利率: 23.96%
- 决策: ✅ 推荐（毛利充足且销量覆盖盈亏点）
- 14 项成本：
  - 01_procurement: $18.0
  - 02_shipping_to_fba: $4.5
  - 03_duty(关税): $0.81
  - 04_test_cert(检测均摊): $0.3
  - 05_fba_fulfillment: $3.06
  - 06_fba_storage_monthly: $0.18
  - 07_amazon_referral(佣金): $5.6
  - 08_ad_cost(广告): $14.0
  - 09_return_loss(退货损失): $2.04
  - 10_return_handling: $0.12
  - 11_vat: $0.0
  - 12_payment_fee(收款): $0.91
  - 13_fx_loss(汇率): $3.5
  - 14_misc(杂项): $0.2

## 7. 证据截图