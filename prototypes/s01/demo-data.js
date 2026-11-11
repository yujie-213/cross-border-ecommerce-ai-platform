/* Frozen illustrative artifacts. No ERP, authoritative calculation, model or API. */
window.DEMO = {
  asOf: '2026-11-11 08:00 UTC+08:00',
  rows: [
    {id:'RP-001',sku:'CB-1001',name:'旅行收纳包 · 雾灰',category:'出行收纳',store:'Amazon 美国站',warehouse:'美西仓',available:55,shortage:'11-18',qty:20,status:'ready',risk:'缓冲不足',supplier:'供应商 A（示例）'},
    {id:'RP-002',sku:'BT-2003',name:'保温随行杯 · 松绿',category:'家居日用',store:'Amazon 美国站',warehouse:'美西仓',available:48,shortage:'11-16',qty:null,status:'quality',risk:'质量调查',supplier:'供应商 B（示例）'},
    {id:'RP-003',sku:'LT-3012',name:'便携阅读灯 · 米白',category:'家居日用',store:'Shopify 独立站',warehouse:'美东仓',available:null,shortage:null,qty:null,status:'stale',risk:'库存已过期',supplier:'供应商 C（示例）'},
    {id:'RP-004',sku:'CB-1008',name:'数码配件包 · 深蓝',category:'出行收纳',store:'Amazon 美国站',warehouse:'美西仓',available:72,shortage:'11-19',qty:30,status:'ready',risk:'缓冲不足',supplier:'供应商 A（示例）'},
    {id:'RP-005',sku:'KT-4010',name:'硅胶折叠碗 · 沙色',category:'户外用品',store:'Shopify 独立站',warehouse:'美东仓',available:36,shortage:null,qty:null,status:'missing',risk:'缺少质量信号',supplier:'供应商 D（示例）'},
    {id:'RP-006',sku:'CB-1015',name:'鞋履收纳袋 · 炭灰',category:'出行收纳',store:'Amazon 美国站',warehouse:'美西仓',available:95,shortage:'11-20',qty:40,status:'ready',risk:'缓冲不足',supplier:'供应商 A（示例）'},
    {id:'RP-007',sku:'BT-2020',name:'轻量运动瓶 · 岩白',category:'户外用品',store:'Amazon 美国站',warehouse:'美东仓',available:64,shortage:'11-19',qty:20,status:'ready',risk:'缓冲不足',supplier:'供应商 B（示例）'},
    {id:'RP-008',sku:'LT-3021',name:'折叠桌面灯 · 墨黑',category:'家居日用',store:'Shopify 独立站',warehouse:'美东仓',available:27,shortage:null,qty:null,status:'duplicate',risk:'供给疑似重复',supplier:'供应商 C（示例）'}
  ],
  // AC-02/03 fixture values; the browser only plots saved values.
  daily: {
    base:[45,35,25,35,25,15,5,-5,-15],
    normal:[45,35,25,35,25,35,25,15,5],
    late:[45,35,25,15,5,-5,-15,15,5]
  },
  states:{ready:['候选可复核','success'],quality:['质量阻断','danger'],stale:['数据阻断','warning'],missing:['数据阻断','warning'],duplicate:['数据阻断','warning']},
  blockers:{
    quality:['投诉信号触发调查','成熟签收群组 100 单，去重投诉订单 12 单；12% 为投诉占比，不能解释为缺陷率。阈值仅为演示设定，待业务冻结。','采购负责人 · 核查质量证据与调查结论'],
    stale:['库存覆盖已过期','WMS 覆盖至 11-09 08:00，未满足演示时效策略；可售与缺货日期不展示为有效结果。','数据负责人 · 恢复库存读取并重新分析'],
    missing:['必需质量信号缺失','S03 已发布结果不可用；缺失不能解释为质量安全。仅展示已有库存事实。','质量负责人 · 补齐兼容且在有效期内的质量结果'],
    duplicate:['未收供给存在重复映射','同一来源采购行出现两条未收供给投影；当前不累计供给、不生成采购候选。','数据负责人 · 复核来源行映射后重新分析']
  }
};
