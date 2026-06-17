# 真实数据修复验证

## 1. 真实关税（HTS）
- headphones: HS=8518.30, duty_rate=4.50%
- wireless-earbuds: HS=8518.30, duty_rate=4.50%
- smartwatch: HS=9102.12, duty_rate=5.80%
- kitchen: HS=3924.10, duty_rate=3.40%

## 2. Amazon Referral 真实费率
- electronics: 8.0%
- headphones: 8.0%
- kitchen: 15.0%
- jewelry: 20.0%

## 3. FBA Fulfillment Fee 真实计算
- 重量 2oz / 最长边 5in → $3.06
- 重量 8oz / 最长边 10in → $3.34
- 重量 16oz / 最长边 14in → $4.4
- 重量 40oz / 最长边 20in → $7.2
- 重量 80oz / 最长边 30in → $7.2

## 4. 实时汇率
- USD/CNY = 6.786741

## 5. 综合 build_real_cost_params (耳机, $70, 4oz, 5in)
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

## 6. 1688 真实采购成本（蓝牙耳机）
```json
{
  "category": "蓝牙耳机",
  "error": null,
  "fallback_used": true,
  "fallback_reason": "1688 抓取失败，退回 'sale_price × 30%' 经验估算",
  "estimated_cost_usd": 21.0
}
```

## 7. ASIN 池机制（先空，抓 BSR 后入池）
- 池初始 size: 0
- 抓耳机子类目 BSR 后池 size: 10
- 池子摘要：
```
## 当前 ASIN 池（共 10 个真实商品，候选品必须从此选择）
- B0C3HCD34R  $44.99  ★4.6  reviews=64538  BSR=1  Soundcore by Anker Q20i Hybrid Active Noise Cancelling Headp
- B09LYF2ST7  $19.99  ★4.5  reviews=54790  BSR=2  BERIBES Bluetooth Headphones Over Ear, 65H Playtime and 6 EQ
- B0C8PR4W22  $229.0  ★4.5  reviews=27839  BSR=3  Beats Studio Pro Premium Wireless Over-Ear Headphones- Up to
- B0CCZ26B5V  $229.0  ★4.6  reviews=19958  BSR=4  Bose QuietComfort Headphones - Wireless Bluetooth Headphones
- B0BS1QCFHX  $91.46  ★4.4  reviews=15535  BSR=5  Sony WH-CH720N Noise Canceling Wireless Headphones Bluetooth
- B09BF64J55  $18.99  ★4.5  reviews=33322  BSR=6  KVIDIO Bluetooth Headphones Over Ear, 65 Hours Playtime Wire
- B088Z22VYF  $10.99  ★4.6  reviews=14674  BSR=7  iClever Kids Headphones for School Travel, Safe Volume Limit
- B0CTBCDD6D  $89.95  ★4.6  reviews=13708  BSR=8  JBL Tune 720BT - Wireless Over-Ear Headphones with JBL Pure 
- B0CRLXZ5J6  $49.95  ★4.6  reviews=7451  BSR=9  JLab JBuds Lux ANC, Over Ear Headphones, Active Noise Cancel
- B0CFV9XR2Q  $16.19  ★4.6  reviews=12920  BSR=10  Picun B8 Bluetooth Headphones, 120H Playtime Headphone Wirel
```