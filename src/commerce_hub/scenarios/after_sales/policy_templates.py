"""Unpublished policy templates; publication remains a human decision."""

def policy_starters(region='CN',platform='TEACHING'):
    """Unpublished teaching drafts. A human publishes applicable versions explicitly."""
    return [dict(id=key,title=title,category=category,topics=topics,sections=[dict(id='s1',text=text)],
        region=region,platform=platform,language='zh',effectiveFrom='2026-01-01T00:00:00Z',
        effectiveUntil='2027-01-01T00:00:00Z',source='中台教学政策（非企业政策）',
        terms=['CLARIFY','MANUAL_REVIEW','SAFETY_ESCALATE'] if key=='safety' else ['CLARIFY','MANUAL_REVIEW']) for key,title,category,topics,text in [
        ('size','尺码与描述核实','APPAREL',['SIZE','DESCRIPTION'],'尺码不合适时，先核对订单、履约和现有退货进度。服装在适用退换货期限内、吊牌完整、未穿洗且不影响再次销售，可以申请换货或退货退款；客户未说明的条件用条件句并询问确认。若已提交退货申请，则按当前申请继续跟进，不能重复引导申请或称已退款。商品尺码表或测量缺失时请客户提供实际差异照片，不直接认定质量缺陷。'),
        ('safety','3C安全优先升级','ELECTRONICS',['SAFETY','FUNCTION','COMPATIBILITY'],'冒烟、起火、漏电、异常发热先升级人工安全专员；不指导拆机，不作安全认证或退款承诺。'),
        ('returns','退货资格、时限与费用例外','ALL',['RETURN'],'先核对实际履约和退货申请阶段，避免重复申请。政策条件符合时可申请退货或换货；服装还需吊牌完整、未穿洗、不影响再次销售。退款需退货验收及后续审核完成后依流程办理；申请或退货草稿不代表已退款。具体期限、费用和例外未给定时应询问或核实，不自行编造、不承诺金额或到账日期。'),
        ('replies','回复承诺与证据适用','ALL',['REPLY'],'直接用客户能理解的语气回应诉求，结合系统已核事实和适用政策给出选项与必要条件。已知订单、商品或客户已提供的信息不重复索取，未知事项只问必要问题；不输出给客服的操作指令，不编造已经执行的退款或补发。客服确认保存只留处理记录，不代表已向客户发送。'),
        ('shipping','发货进度与物流查询','ALL',['LOGISTICS'],'以已核订单状态和运单事件为准。等待发货时说明当前状态；已经发货时只说明已核查到的进度。没有承运商交接或预计送达证据时，说明待核实，不承诺时点，不把生成运单当成揽收。'),
        ('delivery','未收到与显示已签收','ALL',['NOT_RECEIVED'],'区分未出库、运输中和运单显示签收。已显示签收但客户未收到时，可请客户核对代收处、同住人或门口，必要时核查承运商签收凭证。客户已核对过的事项不重复追问；不凭状态判定丢件或承诺赔付。'),
        ('order-change','收货地址、修改与取消','ALL',['ORDER_CHANGE'],'先核对当前履约状态。订单尚未发货时可核实是否支持修改或取消；已发货时只能核实可用的拦截或改派渠道。不承诺操作成功，不在公开评价或回复中请求完整地址、电话或付款资料。'),
        ('product-info','材质、使用与清洁保养','ALL',['PRODUCT_INFO'],'已核商品说明或洗护标签写明的材料与用法可直接回答。缺少说明时可请客户查看实物标签，或说明要进一步核实；不自行猜测材质、洗护参数或兼容性。'),
        ('compatibility','兼容性与商品功能核实','ELECTRONICS',['COMPATIBILITY','FUNCTION'],'先比对已核商品型号、接口和适用条件，只向客户询问尚缺的设备型号或现象。确认条件前不承诺兼容或给出维修结论。涉及冒烟、异常发热或漏电时按安全流程升级。'),
        ('item-issue','破损、错发、漏发与缺件','ALL',['ITEM_ISSUE'],'先回应客户描述，再核对订购明细、包裹和出库证据。必要时只请客户提供能区分问题的商品或包装照片、缺失部件名称；已提供的证据不重复索取。不凭描述认定责任，也不承诺未经核实的补发或费用。'),
        ('billing','付款、发票与优惠咨询','ALL',['PAYMENT'],'先核对订单付款状态、活动条件或可用的开票入口。仅对当前问题说明已核事实，无法核实时只询问优惠名称或开票类型，不索取支付验证码或完整卡号，不承诺差价、开票资格或费用。'),
        ('sizing-help','尺码与规格咨询','APPAREL',['SIZE'],'使用已核的商品尺码表或尺寸说明回答选码问题。缺少尺寸依据时，只询问与选择相关的测量值或穿着偏好；不凭模糊描述承诺合身。')]]
