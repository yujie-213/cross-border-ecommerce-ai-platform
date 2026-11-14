"""S01 runtime admission: calendar demand and posting conservation are independent.

L1/L2 survive missing procurement facts; B01/B02 retain their only formulas.
The old normalizer is retained for immutable historical replay.
"""
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal,ROUND_CEILING
from commerce_hub.data.contracts import AdmittedInput,fingerprint
from commerce_hub.data.projection.stock_basis import verify_stock
from commerce_hub.data.projection import project
from commerce_hub.data.quality import capture
from commerce_hub.capabilities.forecasting import propose

VERSION='s01-runtime-v1'


def business_date(timestamp,zone='UTC+08:00'):
    offset=timedelta(0) if zone=='UTC' else timedelta(hours=int(zone[4:6]),minutes=int(zone[7:9]))*(-1 if zone[3]=='-' else 1)
    return datetime.fromisoformat(timestamp).astimezone(timezone(offset)).date()


def demand_window(entity,sales,workflows,ledger_rows,day,policy,basis,*,scope_complete=False,zero_from=None):
    start=day-timedelta(days=policy.observationDays)
    days={start+timedelta(days=i):dict(day=(start+timedelta(days=i)).isoformat(),status='UNKNOWN',quantity=None,reasons=[])
        for i in range(policy.observationDays)}
    totals={d:Decimal(0) for d in days};known=set();bad=set();seen=set();history=[];observed=[];excluded=[];issues=[];consumed=set()
    for s in sales:
        try:
            if str(s.get('tenant_id'))!=entity['sourceTenant'] or s.get('store_name')!=entity['storeName'] or s.get('shipping_warehouse')!=entity['warehouseName']:
                raise ValueError('SALES_RELATION_DRIFT')
            sid=str(s['id']);when=datetime.strptime(s['order_time'],'%Y-%m-%d %H:%M:%S').date()
            if sid in seen: raise ValueError('DUPLICATE_SALES_RECORD')
            seen.add(sid)
            lines=[x for x in s.get('item_list',[]) if x.get('sku')==entity['sku']]
            if not lines: continue
            if when>=day: excluded.append(dict(orderRef='erp-order-'+sid,reason='CURRENT_OR_FUTURE_DAY'));continue
            if len(lines)!=1: raise ValueError('SALES_ITEM_AMBIGUOUS')
            status=[s.get(k) for k in ('payment_status','fulfillment_status','refund_status')]
            if s.get('refund_status') not in {'无退款',None}:
                bad.add(when);excluded.append(dict(orderRef='erp-order-'+sid,reason='REFUND_NETTING_UNPROVEN'));continue
            if s.get('status_text') in {'已取消','已关闭'} or s.get('payment_status')=='未支付' or s.get('fulfillment_status')=='未发货':
                excluded.append(dict(orderRef='erp-order-'+sid,reason='NOT_REALIZED_FULFILLMENT'));continue
            if status!=['已支付','已发货','无退款']:
                bad.add(when);continue
            qty=Decimal(str(lines[0]['quantity']))
            if not qty.is_finite() or qty<=0 or qty!=qty.to_integral_value():raise ValueError('SALES_QUANTITY_INVALID')
            observed.append(dict(businessDate=when.isoformat(),quantity=str(qty),orderRef='erp-order-'+sid,
                basis='ERP_PAID_SHIPPED_STATUS_ONLY_NOT_STOCK_RECONCILIATION'))
            wf=workflows.get(sid,{})
            if wf.get('state')!='shipped' or wf.get('order_id')!=s['id'] or wf.get('local_only') is not True:raise ValueError('FULFILLMENT_NOT_VERIFIED')
            posted=Decimal(0);used=set()
            for shipment in wf.get('shipments',[]):
                if shipment.get('order_id')!=s['id']:raise ValueError('SHIPMENT_PARENT_DRIFT')
                own=[r for r in ledger_rows if r.get('resource')=='outbound-orders' and r.get('record_id')==shipment.get('outbound_id') and r.get('sku')==entity['sku']]
                if not own:raise ValueError('OUTBOUND_LEDGER_MISSING')
                for r in own:
                    if str(r['id']) in used or str(r['id']) in consumed:raise ValueError('DUPLICATE_FULFILLMENT_EVENT')
                    used.add(str(r['id']));posted-=Decimal(str(r['delta_quantity']))
            if posted!=qty:raise ValueError('FULFILLMENT_LEDGER_QUANTITY_MISMATCH')
            consumed.update(used)
            history.append(dict(businessDate=when.isoformat(),quantity=str(qty),orderRef='erp-order-'+sid,postedAt=wf.get('shipped_at')))
            if when in days:known.add(when);totals[when]+=qty
        except (KeyError,TypeError,ValueError,ArithmeticError) as exc:
            issues.append(str(exc) if isinstance(exc,ValueError) and str(exc) else 'SALES_FIELDS_INVALID')
            # Unknown identity/date cannot be safely confined to a single day.
            try:bad.add(datetime.strptime(s['order_time'],'%Y-%m-%d %H:%M:%S').date())
            except (KeyError,TypeError,ValueError):bad.update(days)
    cp=basis.get('checkpoint') or {}
    def after_checkpoint(row):
        return not cp.get('postedAt') or (datetime.fromisoformat(row['created_at']),int(row['id']))>(datetime.fromisoformat(cp['postedAt']),int(cp['lastEventId']))
    unclaimed={str(r['id']) for r in ledger_rows if r.get('resource')=='outbound-orders' and r.get('sku')==entity['sku'] and after_checkpoint(r)}-consumed
    if unclaimed:
        scope_complete=False;issues.append('OUTBOUND_SALES_LINK_UNPROVEN')
    censor_days={business_date(t,policy.timezone) for t in basis.get('censoredAt',[])}
    for interval in basis.get('zeroIntervals',[]):
        if interval['start'] and interval['end']:
            first,last=business_date(interval['start'],policy.timezone),business_date(interval['end'],policy.timezone)
            censor_days.update(d for d in days if first<=d<=last)
    for d,value in days.items():
        if d in bad:value['reasons']=['SALES_DAY_UNVERIFIED']
        elif d in censor_days:value.update(status='CENSORED',reasons=['HISTORICAL_STOCKOUT_DEMAND_CENSORED'])
        elif scope_complete and d in known:value.update(status='KNOWN_SALES',quantity=str(totals[d]))
        elif scope_complete and zero_from is not None and d>=zero_from and basis['status']=='VERIFIED' and Decimal(basis['available'])>0:
            value.update(status='KNOWN_ZERO',quantity='0')
        else:value['reasons']=['DAY_COVERAGE_UNPROVEN']
    valid=[v for v in days.values() if v['status'] in {'KNOWN_SALES','KNOWN_ZERO'}]
    total=sum((Decimal(v['quantity']) for v in valid),Decimal(0))
    history=sorted(history,key=lambda r:(r['businessDate'],r['orderRef']))
    reference_total=sum((Decimal(r['quantity']) for r in observed),Decimal(0))
    reference_dates={r['businessDate'] for r in observed}
    age=(day-date.fromisoformat(max(reference_dates))).days if reference_dates else None
    return dict(method='SIMPLE_MOVING_AVERAGE',policyVersion=policy.version,timezone=policy.timezone,
        windowStart=start.isoformat(),windowEnd=(day-timedelta(days=1)).isoformat(),observationDays=policy.observationDays,
        dailySales=list(days.values()),validDays=len(valid),zeroDays=sum(v['status']=='KNOWN_ZERO' for v in valid),
        missingDays=len(days)-len(valid),totalSales=str(total),averageDailyDemand=str(total/Decimal(policy.observationDays)) if len(valid)==len(days) else None,
        referenceAverage=str(reference_total/Decimal(len(reference_dates))) if reference_dates else None,
        referenceDenominator='OBSERVED_SALES_DATES_ONLY_NOT_CALENDAR_AVERAGE',referenceDays=len(reference_dates),
        referenceGrade='STALE_HISTORICAL' if age is not None and age>15 else 'OBSERVED_STATUS_ONLY' if observed else 'UNAVAILABLE',sampleAgeDays=age,
        sampleStart=min(reference_dates) if reference_dates else None,sampleEnd=max(reference_dates) if reference_dates else None,
        complete=len(valid)==len(days),history=history,observedHistory=observed,excluded=excluded,issues=sorted(set(issues)))


def evaluate_runtime(entity,product,inventory,movements,sales,workflows,policy,receipt,constraints,*,opening_binding=None,scope_complete=False,inbound_proofs=()):
    cp=getattr(getattr(opening_binding,'monitor',None),'stockCheckpoint',None)
    basis=verify_stock(entity,inventory,movements,opening_binding=opening_binding,checkpoint=cp,inbound_proofs=inbound_proofs)
    day=date.fromisoformat(receipt['businessDate']);zero_from=None
    checkpoint=basis.get('checkpoint') or {}
    if checkpoint.get('observedAt'):
        zero_from=business_date(checkpoint['observedAt'],policy.timezone)+timedelta(days=1)
    window=demand_window(entity,sales,workflows,movements.get('rows',[]),day,policy,basis,scope_complete=scope_complete,zero_from=zero_from)
    valid=entity['identityVerified'] and product.get('unit') in {'piece','EA','件'}
    failures=[]
    if not valid:failures.append('IDENTITY_OR_UNIT_UNVERIFIED')
    failures+=basis['issues']
    if not window['complete']:failures.append('DEMAND_DAY_COVERAGE_INCOMPLETE')
    started=datetime.fromisoformat(receipt['startedAt']);completed=datetime.fromisoformat(receipt['completedAt'])
    if completed<started or completed-started>timedelta(hours=24) or business_date(receipt['completedAt'],policy.timezone)!=day:
        failures.append('ACQUISITION_TIME_BOUNDARY_EXPIRED')
    rules=None;planning=False
    if not failures:
        average=Decimal(window['averageDailyDemand']);daily=average.quantize(Decimal('.00000001'),rounding=ROUND_CEILING)
        lead=constraints.get('leadDays');planning=not constraints['hardBlocks'] and type(lead) is int and 0<=lead<=14
        horizon=lead+policy.coverageDays if planning else policy.coverageDays
        moq=Decimal(constraints['moq']) if planning else None;multiple=Decimal(constraints['orderMultiple']) if planning else None
        canonical=dict(sku=entity['sku'],store=entity['storeId'],warehouse=entity['warehouseId'])
        value=AdmittedInput(sourceNature='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP',fixtureId='runtime-'+fingerprint(receipt)[:24],
            provenanceRef='runtime-'+fingerprint([receipt,basis,window])[:32],rulesRef=VERSION,asOf=receipt['completedAt'],businessDate=day,coverageComplete=True,
            mapping=dict(version=VERSION,sourceSku=entity['sku'],sourceStore=entity['storeId'],sourceWarehouse=entity['warehouseId'],
                canonicalSkuId=entity['sku'],storeId=entity['storeId'],warehouseId=entity['warehouseId'],sourceUnit='EA',unit='EA',unitsPerSourceUnit='1'),
            inventory=[dict(recordId='stock-'+entity['inventoryIds'][0],**canonical,unit='EA',availableQty=basis['available'],reservedQty=None,
                semantics='NET_AVAILABLE',sourceUpdatedAt=inventory.get('observedAt') or receipt['completedAt'])],
            demand=[dict(recordId='demand-'+str(i),**canonical,unit='EA',day=day+timedelta(days=i),quantity=str(daily),semantics='INCREMENTAL_EXCLUDES_RESERVED') for i in range(1,horizon+1)],
            supply=[],policy=dict(version=VERSION,horizonDays=horizon,bufferDays=0,maxAgeHours=24,moq=moq,orderMultiple=multiple,
                maxOrderQty=str(((daily*horizon+moq)/multiple).to_integral_value(rounding=ROUND_CEILING)*multiple) if planning else None,
                candidateDates=[day+timedelta(days=max(1,lead))] if planning else [],otherConstraints='UNCONFIRMED',qualityDisposition='UNKNOWN',advisoryOnly=True))
        snapshot=capture(project(value,'runtime-'+fingerprint(receipt)[:24]))
        if snapshot.calculation_allowed:
            rules=dict(supplyDemand=propose(snapshot),forecast=window,input=value.model_dump(mode='json'),fieldProvenance=[],snapshotId=snapshot.snapshotId,
                quality=[i.model_dump() for i in snapshot.issues])
        else:failures.extend(i.code for i in snapshot.issues if i.severity=='BLOCK')
    identity=entity['identityVerified']
    quality=dict(identity=dict(status='VERIFIED' if identity else 'UNKNOWN',reasons=[] if identity else ['IDENTITY_OR_UNIT_UNVERIFIED']),
        demand=dict(status='VERIFIED' if window['complete'] else 'REFERENCE' if window['observedHistory'] else 'UNKNOWN',reasons=[] if window['complete'] else ['DEMAND_DAY_COVERAGE_INCOMPLETE']),
        inventory=dict(status=basis['status'],reasons=basis['issues']),procurement=dict(status='READY_FOR_REVALIDATION' if not constraints['hardBlocks'] else 'BLOCKED',reasons=constraints['hardBlocks']))
    return dict(admissionVersion=VERSION,dataQuality=quality,demandWindow=window,inventoryBasis=basis,
        ruleResult=rules,ruleFailureCodes=sorted(set(failures)),riskOnly=bool(rules and not planning))
