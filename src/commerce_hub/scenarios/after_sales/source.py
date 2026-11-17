"""D01/D02 bounded source projection, with exact local sourceRead scope.

Raw teaching ERP replies stay in ignored private artifacts. Titles remain titles;
missing conversation, delivery, RMA and product attributes stay unknown.
"""
from pathlib import Path
from decimal import Decimal
import json
from .common import require,now,redacted


class SourceReader:
    def __init__(self,factory,allowed_stores,private_root,*,owned_provider=None,supplemental_context=None):
        self.factory=factory;self.stores=allowed_stores;self.root=Path(private_root)
        self.owned_provider=owned_provider
        self.supplemental_context=supplemental_context

    def members(self,store=None):
        if self.owned_provider is None:return None  # Explicit synthetic test adapters.
        return [m for m in self.owned_provider() if m.monitor and (store is None or m.storeName==store)]

    def allows_identity(self,identity,*,order=False):
        members=self.members()
        if members is None:return True
        if not identity:return False
        return any(str(identity.get('sourceTenant'))==m.sourceTenant and str(identity.get('storeId'))==m.sourceStore
            and str(identity.get('productId'))==m.monitor.productId and identity.get('sku')==m.sku
            and (not order or str(identity.get('orderId')) in m.monitor.salesIds)
            and (identity.get('warehouseId') in (None,'UNKNOWN') or str(identity['warehouseId'])==m.sourceWarehouse)
            and (not identity.get('warehouseIds') or all(str(w)==m.sourceWarehouse for w in identity['warehouseIds'])) for m in members)

    def allows_case(self,body):
        if self.owned_provider is None:return True
        candidates=([body['identity']] if body.get('identity') else [])+(body.get('sourceMembership') or [])+(body.get('evidence') or {}).get('identityCandidates',[])
        order=bool(body.get('erpTicketId') or body.get('erpReturnId')) or body.get('erpVoiceKind')=='feedback'
        return any(self.allows_identity(i,order=order) for i in candidates)

    def _owned_orders(self,reader,store,check):
        members=self.members(store)
        if members is None:return None
        ids=sorted({sid for m in members for sid in m.monitor.salesIds})
        orders=[]
        for start in range(0,len(ids),40):
            check();batch=reader.read('/api/v1/sales-orders',dict(ids=','.join(ids[start:start+40])),page_size=50,max_pages=2)
            require(batch.complete,'OWNED_ORDER_COVERAGE_INCOMPLETE')
            expected=self._store(store)
            orders.extend(o for o in batch.records if str(o.get('id')) in ids and str(o.get('tenant_id'))==expected['sourceTenant'] and o.get('store_name')==store)
        return orders

    def _store(self,name):
        require(name in self.stores,'SOURCE_SCOPE_DENIED',403)
        require(self.members(name) is None or bool(self.members(name)),'SOURCE_SCOPE_DENIED',403)
        return self.stores[name]

    def discover(self,store,check,*,full=False):
        expected=self._store(store);check();reader=self.factory()
        batch=(reader.read('/api/v1/customer-tickets',dict(store_name=store),page_size=50,max_pages=5) if full
            else reader.discover('/api/v1/customer-tickets',dict(store_name=store),page_size=20))
        owned=self._owned_orders(reader,store,check)
        order_numbers=None if owned is None else {o.get('order_sn') for o in owned if o.get('order_sn')}
        return dict(items=[dict(ticketId=str(r['id']),ticketNumber=r.get('ticket_no'),title=redacted(r.get('subject','')),
            storeName=store,sourceTenant=str(r['tenant_id']),orderLinked=bool(r.get('order_sn')))
            for r in batch.records if str(r.get('tenant_id'))==expected['sourceTenant'] and r.get('store_name')==store
                and (order_numbers is None or r.get('order_sn') in order_numbers)],
            complete=batch.complete,observedAt=batch.observed_at,sourceNature='TEACHING_ERP_OBSERVED')

    @staticmethod
    def product_attributes(product):
        # Explicit source vocabulary only. A title/SKU never supplies a category.
        category=product.get('category') or ''
        normalized=('APPAREL' if category=='APPAREL' or category.startswith('服装/') else
            'ELECTRONICS' if category=='ELECTRONICS' or category.startswith(('电子/','数码/')) else 'UNKNOWN')
        attributes={k:product[k] for k in ('size','color','material','model') if product.get(k)}
        return normalized,attributes

    def inbox(self,store,kind,check,date_from=None,date_to=None,*,full=False):
        expected=self._store(store);require(kind in {'tickets','reviews','feedback'},'SOURCE_KIND_INVALID')
        if kind=='tickets':return self.discover(store,check,full=full)
        reader=self.factory();check()
        params=dict(kind=kind,store_id=expected['storeId'],visibility='active')
        if date_from:params['date_from']=date_from
        if date_to:params['date_to']=date_to
        batch=(reader.read('/api/v1/customer-voice',params,page_size=50,max_pages=5) if full
            else reader.discover('/api/v1/customer-voice',params,page_size=10))
        items=[];products={}
        members=self.members(store)
        owned_skus=None if members is None else {m.sku for m in members}
        owned_orders=None if members is None else {sid for m in members for sid in m.monitor.salesIds}
        for r in batch.records:
            require(str(r.get('store_id'))==expected['storeId'] and r.get('store_name')==store,'SOURCE_IDENTITY_MISMATCH')
            if owned_skus is not None and (kind=='reviews' and r.get('sku') not in owned_skus or kind=='feedback' and str(r.get('order_id')) not in owned_orders):continue
            sku=r.get('sku') if kind=='reviews' else None
            identity=None;association='评价未提供可核实商品，需补证'
            if sku:
                if sku not in products:
                    check()
                    try:
                        pb=reader.read('/api/v1/products',dict(field='sku',q=sku),page_size=20,max_pages=2)
                        products[sku]=[p for p in pb.records if pb.complete and p.get('sku')==sku and str(p.get('tenant_id'))==expected['sourceTenant']]
                    except Exception:products[sku]=[]
                matches=products[sku]
                if len(matches)==1:
                    product=matches[0];category,attributes=self.product_attributes(product)
                    identity=dict(productId=str(product['id']),sku=sku,name=product.get('name') or sku,category=category,attributes=attributes,
                        storeId=expected['storeId'],sourceTenant=expected['sourceTenant'],warehouseId='UNKNOWN',orderId='UNKNOWN',
                        lineId='voice:'+kind+':'+str(r['id']),source='OBSERVED')
                    association='已按店铺、SKU与唯一商品记录关联；订单未核实'
                else:association='商品记录缺失或不唯一，需补证'
            if kind=='feedback':association='订单反馈；需独立核实订单及受影响商品'
            if identity and not self.allows_identity(identity):continue
            items.append(dict(recordId=str(r['id']),kind=kind,title=redacted(r.get('title') or '客户反馈'),text=redacted(r.get('body') or ''),
                rating=r.get('rating'),businessDate=r.get('business_date'),platform=r.get('platform'),storeName=store,
                handlingStatus=r.get('handling_status'),handlingVersion=r.get('version'),
                identity=identity,association=association,orderId='UNKNOWN',sourceRef='customer-voice:'+kind+':'+str(r['id'])))
        return dict(items=items,complete=batch.complete,observedAt=batch.observed_at,sourceNature='TEACHING_ERP_OBSERVED',
            limitation='当前有界读取的反馈；不是完整评价总体，也不提供退货率分母')

    @staticmethod
    def _day(record):
        from datetime import date
        for key in ('business_date','order_date','order_time','created_at','created_time'):
            value=record.get(key)
            if isinstance(value,str) and len(value)>=10:
                try:return date.fromisoformat(value[:10])
                except ValueError:pass
        return None

    def return_analysis(self,store,check,*,end_date=None,window_days=7):
        """Read returns only through project-owned orders and compare shipped cohorts."""
        from datetime import date,timedelta,datetime,timezone
        require(type(window_days) is int and 3<=window_days<=30,'WINDOW_INVALID')
        try:end=date.fromisoformat(end_date) if end_date else datetime.now(timezone(timedelta(hours=8))).date()
        except ValueError:require(False,'WINDOW_INVALID')
        current_start=end-timedelta(days=window_days-1)
        previous_start=current_start-timedelta(days=window_days)
        expected=self._store(store);members=self.members(store)
        require(members is not None,'OWNED_SCOPE_REQUIRED',503)
        reader=self.factory();orders=self._owned_orders(reader,store,check)
        product_info={}
        for product_id in sorted({m.monitor.productId for m in members}):
            check();page=reader.read('/api/v1/products',dict(ids=product_id),page_size=20,max_pages=2)
            matches=[p for p in page.records if page.complete and str(p.get('id'))==product_id and str(p.get('tenant_id'))==expected['sourceTenant']]
            if len(matches)==1:
                product=matches[0];category,attributes=self.product_attributes(product)
                product_info[product_id]=dict(name=product.get('product_name') or product.get('name'),category=category,attributes=attributes)
        owned={str(o['id']):o for o in orders}
        member_by_order={}
        for member in members:
            for order_id in member.monitor.salesIds:
                member_by_order.setdefault(str(order_id),[]).append(member)
        def exact_members(order_id,sku,order):
            matches=[m for m in member_by_order.get(str(order_id),[]) if m.sku==sku]
            if len(matches)>1:
                warehouse=order.get('shipping_warehouse')
                matches=[m for m in matches if warehouse and getattr(m,'warehouseName',None)==warehouse]
            return matches
        returns=[];complete=len(product_info)==len({m.monitor.productId for m in members})
        if any(len({m.monitor.productId for m in members if m.sku==sku})!=1 for sku in {m.sku for m in members}):complete=False
        expected_orders={str(sid) for m in members for sid in m.monitor.salesIds}
        if set(owned)!=expected_orders:complete=False
        for order_id,order in owned.items():
            if not member_by_order.get(order_id):continue
            check();page=reader.read('/api/v1/sales-returns',dict(order_id=int(order_id)),page_size=20,max_pages=2)
            if not page.complete:complete=False;continue
            for row in page.records:
                if str(row.get('order_id'))!=order_id:continue
                check();detail=reader.detail('sales-returns',row['id'])
                record=detail.get('data',detail)
                if str(record.get('id'))!=str(row.get('id')) or str(record.get('order_id'))!=order_id:
                    complete=False;continue
                items=record.get('item_list') or []
                for line in items:
                    sku=line.get('sku');matches=[m for m in exact_members(order_id,sku,order)
                        if m.monitor.productId and m.sourceTenant==expected['sourceTenant'] and m.sourceStore==expected['storeId']]
                    if len(matches)!=1:
                        if any(m.sku==sku for m in member_by_order.get(order_id,[])):complete=False
                        continue
                    member=matches[0]
                    order_lines=[(index,line_order) for index,line_order in enumerate(order.get('item_list',[])) if line_order.get('sku')==sku]
                    if len(order_lines)!=1:
                        complete=False
                        continue
                    line_index=order_lines[0][0]
                    info=product_info.get(member.monitor.productId,{})
                    returns.append(dict(id=str(record['id']),returnNo=record.get('return_no'),orderId=order_id,
                        orderNumber=order.get('order_sn'),productId=member.monitor.productId,sku=sku,
                        productName=info.get('name') or sku,
                        quantity=int(line.get('quantity',0)),reason=record.get('reason') or '',state=record.get('state'),
                        createdAt=record.get('created_at'),authorizedAt=record.get('authorized_at'),receivedAt=record.get('received_at'),
                        refundedAt=record.get('refunded_at'),hasReceived=bool(record.get('received_at')) or record.get('state')=='received',
                        quality=record.get('quality_list') or [],
                        identity=dict(sourceTenant=member.sourceTenant,productId=member.monitor.productId,sku=sku,storeId=member.sourceStore,
                            warehouseId=member.sourceWarehouse,orderId=order_id,lineId=order_id+':'+str(line_index),category=info.get('category','UNKNOWN'),attributes=info.get('attributes',{})),
                        sourceRef='sales-returns:'+str(record['id']),
                        orderDate=self._day(order).isoformat() if self._day(order) else None))
        products={}
        for member in members:
            info=product_info.get(member.monitor.productId,{})
            products.setdefault(member.sku,dict(productId=member.monitor.productId,sku=member.sku,
                name=info.get('name') or member.sku,category=info.get('category','UNKNOWN'),
                attributes=info.get('attributes',{})))
        shipped_by_sku={}
        for order_id,order in owned.items():
            day=self._day(order)
            if day is None or not previous_start<=day<=end:continue
            if str(order.get('fulfillment_status','')).lower() not in {'shipped','已发货'}:continue
            for line in order.get('item_list') or []:
                sku=line.get('sku');matching=exact_members(order_id,sku,order)
                if len(matching)!=1:
                    if any(m.sku==sku for m in member_by_order.get(order_id,[])):complete=False
                    continue
                bucket=shipped_by_sku.setdefault(sku,{'previousOrders':set(),'currentOrders':set(),'previousUnits':0,'currentUnits':0,'evidenceRefs':[]})
                if previous_start<=day<current_start:
                    bucket['previousOrders'].add(order_id);bucket['previousUnits']+=int(line.get('quantity',0))
                else:
                    bucket['currentOrders'].add(order_id);bucket['currentUnits']+=int(line.get('quantity',0))
                bucket['evidenceRefs'].append('sales-orders:'+order_id)
                info=product_info.get(matching[0].monitor.productId,{})
                products[sku]=dict(productId=matching[0].monitor.productId,sku=sku,name=info.get('name') or sku,
                    category=info.get('category','UNKNOWN'),attributes=info.get('attributes',{}))
        reviewed=self.inbox(store,'reviews',check,previous_start.isoformat(),end.isoformat(),full=True)
        reviews_by_sku={};review_evidence_by_sku={}
        for row in reviewed['items']:
            sku=(row.get('identity') or {}).get('sku')
            if not sku:continue
            bucket=reviews_by_sku.setdefault(sku,{'previousCount':0,'currentCount':0,'previousLow':0,'currentLow':0,'items':[]})
            day=None
            try:day=date.fromisoformat(str(row.get('businessDate'))[:10])
            except (ValueError,TypeError):pass
            if day is None:
                complete=False
                continue
            if not previous_start<=day<=end:continue
            period='previous' if day<current_start else 'current'
            bucket[period+'Count']+=1
            if isinstance(row.get('rating'),int) and row['rating']<=2:bucket[period+'Low']+=1
            bucket['items'].append(row)
            shipped_by_sku.setdefault(sku,{'previousOrders':set(),'currentOrders':set(),'previousUnits':0,'currentUnits':0,'evidenceRefs':[]})['evidenceRefs'].append(row['sourceRef'])
            review_evidence_by_sku.setdefault(sku,[]).append(dict(sourceRef=row['sourceRef'],kind='REVIEW',
                text=f"{row.get('rating') if row.get('rating') is not None else '未评分'} 星评价：{row.get('text') or row.get('title') or '无正文'}",
                businessDate=row.get('businessDate')))
        return_periods={};return_evidence_by_sku={}
        for item in returns:
            day=date.fromisoformat(item['orderDate']) if item.get('orderDate') else None
            if day is None:
                if item['hasReceived']:complete=False
                continue
            if not previous_start<=day<=end:continue
            order=owned[item['orderId']]
            if str(order.get('fulfillment_status','')).lower() not in {'shipped','已发货'}:
                if item['hasReceived']:complete=False
                continue
            period='previous' if day<current_start else 'current'
            bucket=return_periods.setdefault(item['sku'],{'previous':0,'current':0,'previousActual':0,'currentActual':0})
            bucket[period]+=item['quantity']
            received_day=None
            if item['hasReceived']:
                try:received_day=date.fromisoformat(str(item.get('receivedAt'))[:10])
                except (ValueError,TypeError):complete=False
            count_received=bool(received_day and received_day<=end)
            if count_received:bucket[period+'Actual']+=item['quantity']
            if count_received:
                shipped_by_sku.setdefault(item['sku'],{'previousOrders':set(),'currentOrders':set(),'previousUnits':0,'currentUnits':0,'evidenceRefs':[]})['evidenceRefs'].append(item['sourceRef'])
                return_evidence_by_sku.setdefault(item['sku'],[]).append(dict(sourceRef=item['sourceRef'],kind='RETURN',
                    text=f"{item['state']} · {item['quantity']} 件 · {item['reason'] or '未填写原因'}",businessDate=item['orderDate']))
        monitor=[]
        for sku,shipped in shipped_by_sku.items():
            returned=return_periods.get(sku,{})
            review=reviews_by_sku.get(sku,{})
            prev=shipped['previousUnits'];cur=shipped['currentUnits']
            prev_ret=returned.get('previousActual',0);cur_ret=returned.get('currentActual',0)
            prev_rate=round(prev_ret/prev*100,1) if prev else None
            cur_rate=round(cur_ret/cur*100,1) if cur else None
            prev_reviews=review.get('previousCount',0);cur_reviews=review.get('currentCount',0)
            prev_low=review.get('previousLow',0);cur_low=review.get('currentLow',0)
            prev_low_rate=round(prev_low/prev_reviews*100,1) if prev_reviews else None
            cur_low_rate=round(cur_low/cur_reviews*100,1) if cur_reviews else None
            if prev_ret>prev or cur_ret>cur:complete=False
            evaluated=prev>=20 and cur>=20 and reviewed.get('complete') and complete
            reasons=[]
            if evaluated and prev_rate is not None and cur_rate is not None and cur_rate-prev_rate>=10 and cur_ret>=3:
                reasons.append('实收退货率明显上升')
            if (evaluated and prev_low_rate is not None and cur_low_rate is not None and prev_reviews>=3 and cur_reviews>=3
                and cur_low-prev_low>=2 and cur_low_rate-prev_low_rate>=20):
                reasons.append('低星评价占比明显上升')
            monitor.append(dict(**products[sku],previous=prev,current=cur,previousOrders=len(shipped['previousOrders']),
                currentOrders=len(shipped['currentOrders']),previousReturns=prev_ret,currentReturns=cur_ret,
                previousReturnRate=prev_rate,currentReturnRate=cur_rate,
                previousReviews=prev_reviews,currentReviews=cur_reviews,
                previousLowReviews=prev_low,currentLowReviews=cur_low,
                previousLowReviewRate=prev_low_rate,currentLowReviewRate=cur_low_rate,
                previousStart=previous_start.isoformat(),currentStart=current_start.isoformat(),endDate=end.isoformat(),windowDays=window_days,
                evaluated=evaluated,anomalyReasons=reasons,
                evidenceRefs=sorted(set(shipped['evidenceRefs'])),
                evidenceItems=return_evidence_by_sku.get(sku,[])+review_evidence_by_sku.get(sku,[]),
                reviewSampleComplete=reviewed.get('complete')))
        if not complete:
            for row in monitor:row.update(evaluated=False,anomalyReasons=[])
        return dict(items=returns,monitor=sorted(monitor,key=lambda r:(r.get('currentReturnRate') or 0),reverse=True),
            complete=complete and reviewed.get('complete',False),observedAt=now(),sourceNature='TEACHING_ERP_OBSERVED',
            window=dict(previousStart=previous_start.isoformat(),currentStart=current_start.isoformat(),endDate=end.isoformat(),days=window_days),
            limitation='退货率按原销售发货批次归组；仅有ERP实收记录的退货计入分子；评价样本独立统计。')

    def voice_evidence(self,record_id,kind,store,check,task_id):
        expected=self._store(store);require(kind in {'reviews','feedback'},'SOURCE_KIND_INVALID')
        reader=self.factory();check()
        batch=reader.read('/api/v1/customer-voice',dict(kind=kind,store_id=expected['storeId'],record_id=record_id,visibility='active'),page_size=10,max_pages=1)
        require(batch.complete and len(batch.records)==1,'SOURCE_RECORD_UNAVAILABLE')
        r=batch.records[0]
        require(str(r.get('id'))==record_id and str(r.get('store_id'))==expected['storeId'] and r.get('store_name')==store,'SOURCE_IDENTITY_MISMATCH')
        members=self.members(store)
        require(members is None or any(r.get('sku')==m.sku if kind=='reviews' else str(r.get('order_id')) in m.monitor.salesIds for m in members),'SOURCE_NOT_OWNED',403)
        root=self.root/task_id;root.mkdir(parents=True,exist_ok=True)
        (root/'voice.json').write_text(json.dumps(r,ensure_ascii=False),encoding='utf-8')
        text=redacted(r.get('body') or '')
        facts=[dict(id='voice-'+kind+'-'+record_id,domain='feedback',kind='OBSERVED',text=text,sourceRef='customer-voice:'+kind+':'+record_id,observedAt=batch.observed_at)]
        identities=[];missing=['未取得完整退货与退款事实；不能据评价推断退货率']
        if kind=='reviews' and r.get('sku'):
            check()
            try:
                pb=reader.read('/api/v1/products',dict(field='sku',q=r['sku']),page_size=20,max_pages=2)
                products=[p for p in pb.records if pb.complete and p.get('sku')==r['sku'] and str(p.get('tenant_id'))==expected['sourceTenant']]
            except Exception:
                products=[];missing.append('商品域未读取成功；反馈原文保留，关联待核实')
            if len(products)==1:
                p=products[0];category,attributes=self.product_attributes(p)
                identities=[dict(productId=str(p['id']),sku=p['sku'],name=p.get('name') or p['sku'],category=category,attributes=attributes,
                    storeId=expected['storeId'],sourceTenant=expected['sourceTenant'],warehouseId='UNKNOWN',orderId='UNKNOWN',
                    lineId='voice:'+kind+':'+record_id,source='OBSERVED')]
            missing.append('评价未证明关联订单与发货仓；不从相关编号猜测')
        elif kind=='feedback' and r.get('order_id'):
            check();ob=reader.read('/api/v1/sales-orders',dict(ids=str(r['order_id'])),page_size=20,max_pages=1)
            orders=[o for o in ob.records if ob.complete and str(o.get('id'))==str(r['order_id']) and o.get('store_name')==store and str(o.get('tenant_id'))==expected['sourceTenant']]
            if len(orders)==1:
                o=orders[0]
                facts.append(dict(id='feedback-order',domain='ORDER',kind='OBSERVED',text='已独立核实反馈所属订单；商品诉求仍需按明细核实',sourceRef='sales-orders:'+str(o['id']),observedAt=ob.observed_at))
                for index,line in enumerate((o.get('item_list') or [])[:10]):
                    if not line.get('sku'):continue
                    check();pb=reader.read('/api/v1/products',dict(field='sku',q=line['sku']),page_size=20,max_pages=2)
                    products=[p for p in pb.records if pb.complete and p.get('sku')==line['sku'] and str(p.get('tenant_id'))==expected['sourceTenant']]
                    if len(products)!=1:continue
                    p=products[0];category,attributes=self.product_attributes(p)
                    identities.append(dict(lineId=str(o['id'])+':'+str(index),orderId=str(o['id']),productId=str(p['id']),sku=p['sku'],name=p.get('name') or p['sku'],
                        category=category,attributes=attributes,storeId=expected['storeId'],sourceTenant=expected['sourceTenant'],warehouseId='UNKNOWN',source='OBSERVED'))
                # A multi-line order does not identify the subject of a complaint.
                if len(o.get('item_list') or [])!=1:missing.append('订单包含多件商品，请核实受影响明细；仅列本次核实的前10行')
            else:missing.append('反馈订单无法唯一核实')
        else:missing.append('来源缺少可靠商品或订单关联')
        identities=[i for i in identities if self.allows_identity(i,order=kind!='reviews')]
        require(members is None or identities,'SOURCE_NOT_OWNED',403)
        automatic=identities[0] if len(identities)==1 and (kind=='reviews' or len(orders[0].get('item_list') or [])==1) else None
        return dict(facts=facts,missing=missing,identityCandidates=identities,identity=automatic,businessDate=r.get('business_date'),
            title=redacted(r.get('title') or '客户反馈'),customerText=text,platform=r.get('platform'),observedAt=batch.observed_at,
            sourceNature='TEACHING_ERP_OBSERVED',sourceRef=dict(voiceId=record_id,kind=kind,sourceTenant=expected['sourceTenant'],storeId=expected['storeId']))

    def verify_mapping(self,identity,check):
        require(self.allows_identity(identity),'SOURCE_NOT_OWNED',403)
        store=next((v for v in self.stores.values() if v['storeId']==identity['storeId'] and v['sourceTenant']==identity['sourceTenant']),None)
        require(store is not None and identity['warehouseMode']=='EXPLICIT_IDS','SOURCE_SCOPE_DENIED',403)
        reader=self.factory();check()
        products=reader.read('/api/v1/products',dict(ids=identity['productId']),page_size=20,max_pages=2)
        require(len(products.records)==1 and str(products.records[0].get('id'))==identity['productId'] and products.records[0].get('sku')==identity['sku']
            and str(products.records[0].get('tenant_id'))==identity['sourceTenant'],'MAPPING_IDENTITY_MISMATCH')
        for wid in identity['warehouseIds']:
            check();wh=reader.read('/api/v1/warehouses',dict(ids=wid),page_size=20,max_pages=2)
            require(len(wh.records)==1 and str(wh.records[0].get('id'))==wid and str(wh.records[0].get('tenant_id'))==identity['sourceTenant'],'MAPPING_WAREHOUSE_MISMATCH')
            check();inventory=reader.read('/api/v1/inventory',dict(field='sku',q=identity['sku'],match='exact',store_id=identity['storeId']),page_size=50,max_pages=2)
            require(inventory.complete and any(str(r.get('product_id'))==identity['productId'] and r.get('sku')==identity['sku']
                and str(r.get('tenant_id'))==identity['sourceTenant'] and str(r.get('store_id'))==identity['storeId']
                and str(r.get('wid'))==wid for r in inventory.records),'MAPPING_RELATION_UNVERIFIED')
        return dict(independentReadback=True,productHash=products.fingerprint,relationVerified=True,observedAt=now())

    def order_warehouse(self,reader,store,order,identity,workflow,check):
        """Prove the case warehouse through registered inventory IDs and postings.

        A warehouse name, catalog permission or SKU alone never supplies identity.
        Missing, ambiguous, partial or reversed evidence leaves the case unknown.
        """
        members=self.members(store)
        if (members is None or workflow.get('local_only') is not True
            or workflow.get('order_id')!=order['id'] or workflow.get('state')!='shipped'):
            return None
        candidates=[m for m in members if m.sku==identity['sku'] and m.monitor.productId==identity['productId']
            and m.sourceTenant==identity['sourceTenant'] and m.sourceStore==identity['storeId']
            and str(order['id']) in m.monitor.salesIds and getattr(m,'warehouseName',None)==order.get('shipping_warehouse')]
        if len(candidates)!=1:return None
        member=candidates[0];inventory_ids=set(getattr(member.monitor,'inventoryIds',()))
        shipments=workflow.get('shipments') or []
        if not inventory_ids or not 0<len(shipments)<=20:return None
        lines=[r for r in order.get('item_list',[]) if r.get('sku')==identity['sku']]
        if len(lines)!=1:return None
        quantity=Decimal(0);events=set();outbounds=set()
        for shipment in shipments:
            oid=shipment.get('outbound_id')
            if type(oid) is not int or oid<=0 or oid in outbounds or shipment.get('order_id')!=order['id']:return None
            outbounds.add(oid);check()
            batch=reader.read('/api/v1/stock/ledger',dict(resource='outbound-orders',record_id=oid),page_size=50,max_pages=2)
            if not batch.complete:return None
            rows=[r for r in batch.records if r.get('sku')==identity['sku']]
            if not rows:return None
            for r in rows:
                if (not r.get('id') or r['id'] in events or r.get('resource')!='outbound-orders' or r.get('record_id')!=oid
                    or str(r.get('inventory_id')) not in inventory_ids or r.get('warehouse_name')!=member.warehouseName
                    or r.get('operation')!='post' or r.get('reverses_id') is not None):return None
                delta=Decimal(str(r['delta_quantity']))
                if (delta>=0 or Decimal(str(r['delta_available']))!=delta
                    or Decimal(str(r['after_quantity']))-Decimal(str(r['before_quantity']))!=delta
                    or Decimal(str(r['after_available']))-Decimal(str(r['before_available']))!=delta):return None
                quantity-=delta;events.add(r['id'])
        if quantity!=Decimal(str(lines[0].get('quantity'))):return None
        check()
        proof=self.verify_mapping(dict(sourceTenant=member.sourceTenant,productId=member.monitor.productId,sku=member.sku,
            storeId=member.sourceStore,warehouseMode='EXPLICIT_IDS',warehouseIds=[member.sourceWarehouse]),check)
        return dict(warehouseId=member.sourceWarehouse,inventoryIds=sorted(inventory_ids),ledgerEventIds=sorted(events),
            outboundIds=sorted(outbounds),**proof)

    def evidence(self,ticket_id,store,check,task_id):
        expected=self._store(store);reader=self.factory();check()
        response=reader.detail('customer-tickets',ticket_id)
        ticket=response.get('data',response)
        if isinstance(ticket,dict) and 'record' in ticket:ticket=ticket['record']
        require(isinstance(ticket,dict) and str(ticket.get('id'))==str(ticket_id) and ticket.get('store_name')==store
            and str(ticket.get('tenant_id'))==expected['sourceTenant'],'SOURCE_IDENTITY_MISMATCH')
        owned=self._owned_orders(reader,store,check)
        require(owned is None or any(o.get('order_sn') and o.get('order_sn')==ticket.get('order_sn') for o in owned),'SOURCE_NOT_OWNED',403)
        root=self.root/task_id;root.mkdir(parents=True,exist_ok=True)
        (root/'ticket.json').write_text(json.dumps(response,ensure_ascii=False),encoding='utf-8')
        facts=[dict(id='ticket-title',domain='TICKET',kind='OBSERVED',text=redacted(ticket.get('subject','')),sourceRef='customer-tickets:'+str(ticket_id),observedAt=now())]
        missing=['完整客户会话未由工单标题证明','退货申请、实收和退款事实未由工单状态证明','物流追踪号不证明签收']
        # A ticket timestamp is the complaint business time, never the sale or
        # observation time. Ambiguous timezone-less ERP timestamps stay unknown.
        from .common import timestamp
        business_date=None
        if ticket.get('created_time'):
            try:business_date=timestamp(ticket['created_time']).isoformat()
            except Exception:missing.append('客户问题日期的时区待核实')
        order_sn=ticket.get('order_sn');identities=[];region=None;association_complete=False
        if order_sn:
            check();batch=reader.read('/api/v1/sales-orders',dict(field='order_sn',q=order_sn),page_size=20,max_pages=2)
            require(batch.complete,'OWNED_ORDER_COVERAGE_INCOMPLETE')
            orders=[r for r in batch.records if r.get('order_sn')==order_sn and r.get('store_name')==store and str(r.get('tenant_id'))==expected['sourceTenant']
                and (owned is None or str(r.get('id')) in {str(o['id']) for o in owned})]
            require(len(orders)<=1,'ORDER_AMBIGUOUS')
            (root/'orders.json').write_text(json.dumps(orders,ensure_ascii=False),encoding='utf-8')
            if orders:
                order=orders[0]
                # Only a source country code is evidence; store names are not.
                country=order.get('country')
                if isinstance(country,str) and len(country)==2 and country.isascii() and country.isalpha():region=country.upper()
                for k in ['payment_status','fulfillment_status','refund_status']:
                    if order.get(k) is not None:facts.append(dict(id='order-'+k,domain=k,kind='OBSERVED',value=order[k],sourceRef='sales-orders:'+str(order['id']),observedAt=now()))
                lines=order.get('item_list') or [];require(isinstance(lines,list),'ORDER_LINES_INVALID')
                association_complete=len(lines)==1
                if len(lines)>10:missing.append('订单超过本次10行取证范围；其余明细未读取，不自动确定受影响商品')
                products_by_sku={}
                for index,line in enumerate(lines[:10]):
                    if not line.get('sku'):continue
                    if line['sku'] not in products_by_sku:
                        try:
                            check();pb=reader.read('/api/v1/products',dict(field='sku',q=line['sku']),page_size=20,max_pages=2)
                            require(pb.complete,'PRODUCT_COVERAGE_INCOMPLETE')
                        except Exception as error:
                            missing.append('商品域未完成核实：'+getattr(error,'code','PRODUCT_READ_FAILED'));break
                        products_by_sku[line['sku']]=[p for p in pb.records if p.get('sku')==line['sku'] and str(p.get('tenant_id'))==expected['sourceTenant']]
                    products=products_by_sku[line['sku']]
                    if len(products)!=1:missing.append('商品真实ID无法唯一核实：'+line['sku']);continue
                    product=products[0]
                    identities.append(dict(lineId=str(order['id'])+':'+str(index),orderId=str(order['id']),orderNumber=order_sn,productId=str(product['id']),sku=line['sku'],
                        storeId=expected['storeId'],warehouseId=str(expected.get('warehouseId','UNKNOWN')),name=product.get('product_name') or product.get('name') or line['sku'],
                        category=self.product_attributes(product)[0],attributes=self.product_attributes(product)[1],source='OBSERVED',sourceTenant=expected['sourceTenant']))
                try:
                    check();workflow=reader.detail('sales-workflow',order['id']);w=workflow.get('data',{})
                    (root/'workflow.json').write_text(json.dumps(workflow,ensure_ascii=False),encoding='utf-8')
                    if w.get('paid_at') and w.get('paid_amount') is not None:
                        facts.append(dict(id='paid',domain='PAYMENT',kind='OBSERVED',value=dict(at=w['paid_at'],amount=w['paid_amount'],currency=w.get('currency')),sourceRef='sales-workflow:'+str(order['id']),observedAt=now()))
                    if w.get('shipments'):facts.append(dict(id='shipments',domain='SHIPMENT',kind='OBSERVED',value=[dict(quantity=s.get('item_list'),at=s.get('created_at')) for s in w['shipments']],sourceRef='sales-workflow:'+str(order['id']),observedAt=now()))
                    warehouse_proofs=[]
                    for identity in identities:
                        identity['warehouseId']='UNKNOWN'
                        proof=self.order_warehouse(reader,store,order,identity,w,check)
                        if proof:
                            identity['warehouseId']=proof['warehouseId'];warehouse_proofs.append(proof)
                            facts.append(dict(id='warehouse-'+identity['lineId'],domain='WAREHOUSE',kind='OBSERVED',value=proof,
                                sourceRef='sales-workflow:'+str(order['id']),observedAt=proof['observedAt']))
                    if warehouse_proofs:(root/'warehouse-proofs.json').write_text(json.dumps(warehouse_proofs,ensure_ascii=False),encoding='utf-8')
                except Exception as error:missing.append('履约域不可用：'+getattr(error,'code','READ_FAILED'))
            else:missing.append('订单精确匹配未找到')
        else:missing.append('工单缺订单号')
        identities=[i for i in identities if self.allows_identity(i,order=True)]
        require(owned is None or identities,'SOURCE_NOT_OWNED',403)
        from .customer_context import supplemental_messages
        supplements=supplemental_messages(self.supplemental_context,ticket,identities,store,expected)
        for item in supplements:
            facts.append(dict(id='customer-statement-'+str(ticket_id),domain='CUSTOMER_STATEMENT',kind='SIMULATED',text=item['text'],
                sourceRef=item['sourceRef'],sourceNature=item['sourceNature'],observedAt=now(),manifestHash=item['manifestHash']))
        if supplements:missing=[m for m in missing if m!='完整客户会话未由工单标题证明']
        return dict(facts=facts,missing=missing,identityCandidates=identities,identity=identities[0] if association_complete and len(identities)==1 else None,
            supplementalMessages=supplements,businessDate=business_date,region=region,title=redacted(ticket.get('subject','')),platform=ticket.get('platform'),observedAt=now(),sourceNature='TEACHING_ERP_OBSERVED',
            sourceRef=dict(ticketId=str(ticket_id),sourceTenant=expected['sourceTenant'],storeId=expected['storeId']))
