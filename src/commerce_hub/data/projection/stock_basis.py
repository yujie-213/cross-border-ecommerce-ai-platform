"""Bounded inventory conservation, independent of the demand observation window.

The seed is registered evidence or the first independently collected ledger's
before value. Never derive it by adding demand to today's inventory.
"""
from datetime import datetime
from decimal import Decimal
from commerce_hub.data.contracts import fingerprint


class StockError(ValueError):
    pass


def number(value):
    if isinstance(value, bool): raise StockError('STOCK_NUMBER_INVALID')
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0: raise ValueError()
        return result
    except (ValueError, ArithmeticError): raise StockError('STOCK_NUMBER_INVALID') from None


def verify_stock(entity, inventory, movements, *, opening_binding=None, checkpoint=None, inbound_proofs=()):
    """One verified bucket. Full scope read required even with a new checkpoint.

    New checkpoints isolate earlier historical gaps but must include a source
    posting watermark; future movements cannot be hidden by resetting a seed.
    Inbound support requires independently read posted source document evidence.
    Returns a public projection only; raw source rows remain in D01.
    """
    basis = dict(status='UNKNOWN', checkpoint=None, physical=None, available=None,
        observedAt=inventory.get('observedAt'), rowUpdatedAt=None, residual=None,
        historyStatus='UNVERIFIED', unsupportedEvents=[], issues=[])
    def require(ok, code):
        if not ok: raise StockError(code)
    try:
        require(entity['identityVerified'] and inventory.get('complete') and len(inventory['rows']) == 1, 'INVENTORY_SCOPE_UNPROVEN')
        row=inventory['rows'][0]
        require(str(row.get('id')) in entity['inventoryIds'] and str(row.get('product_id'))==entity['productId']
            and str(row.get('tenant_id'))==entity['sourceTenant'] and str(row.get('store_id'))==entity['storeId']
            and str(row.get('wid'))==entity['warehouseId'] and row.get('sku')==entity['sku'], 'INVENTORY_RELATION_DRIFT')
        physical, available=number(row['quantity']),number(row['available'])
        basis.update(physical=str(physical),available=str(available),rowUpdatedAt=row.get('updated_at'))
        # Reservation semantics have not yet been proved for this ERP slice.
        require(physical==available, 'RESERVATION_OR_STOCK_SEMANTICS_UNCONFIRMED')
        require(movements.get('complete') and not movements.get('error'), 'STOCK_MOVEMENT_COVERAGE_INCOMPLETE')
        events=movements['rows'];ids=[str(r['id']) for r in events]
        require(len(set(ids))==len(ids), 'DUPLICATE_STOCK_EVENT')
        for r in events:
            require(r.get('sku')==entity['sku'] and str(r.get('inventory_id'))==str(row['id'])
                and r.get('warehouse_name')==entity['warehouseName'], 'FOREIGN_STOCK_EVENT')
            require(datetime.fromisoformat(r['created_at']).tzinfo is not None, 'STOCK_EVENT_TIME_INVALID')
            if inventory.get('observedAt'):
                require(datetime.fromisoformat(r['created_at'])<=datetime.fromisoformat(inventory['observedAt']), 'STOCK_EVENT_AFTER_INVENTORY_OBSERVATION')
        events=sorted(events,key=lambda r:(datetime.fromisoformat(r['created_at']),int(r['id'])))
        if checkpoint is not None:
            cp=checkpoint.model_dump(mode='json') if hasattr(checkpoint,'model_dump') else dict(checkpoint)
            require(cp['inventoryId']==str(row['id']), 'CHECKPOINT_SCOPE_DRIFT')
            require(number(cp['quantity'])==number(cp['available']), 'CHECKPOINT_RESERVATION_UNKNOWN')
            require(bool(cp['evidenceDigest']) and cp['version']>=1, 'CHECKPOINT_EVIDENCE_REQUIRED')
            watermark=(datetime.fromisoformat(cp['postedAt']),int(cp['lastEventId']))
            require(watermark[0].tzinfo is not None, 'CHECKPOINT_TIME_INVALID')
            witness=[r for r in events if (datetime.fromisoformat(r['created_at']),int(r['id']))==watermark]
            require(len(witness)==1 and number(witness[0]['after_quantity'])==number(cp['quantity']), 'CHECKPOINT_WATERMARK_UNPROVEN')
            require(datetime.fromisoformat(cp['observedAt'])<=datetime.fromisoformat(inventory['observedAt']), 'CHECKPOINT_AFTER_CURRENT_OBSERVATION')
            require(not any((datetime.fromisoformat(r['created_at']),int(r['id']))>watermark
                and datetime.fromisoformat(r['created_at'])<=datetime.fromisoformat(cp['observedAt']) for r in events), 'CHECKPOINT_WATERMARK_NOT_CURRENT')
            events=[r for r in events if (datetime.fromisoformat(r['created_at']),int(r['id']))>watermark]
            start=number(cp['quantity']); basis['historyStatus']='ISOLATED_BEFORE_CHECKPOINT'
        elif opening_binding is not None and hasattr(opening_binding.monitor,'openingQuantity'):
            b=opening_binding.monitor; start=number(b.openingQuantity)
            cp=dict(version=b.scopeVersion,quantity=str(start),available=str(start),inventoryId=str(row['id']),
                evidenceDigest=b.evidenceDigest,source='REGISTERED_OPENING',postedAt=None,lastEventId=None,
                originAt=events[0]['created_at'] if events else None,observedAt=inventory.get('observedAt'))
        else:
            require(bool(events), 'STOCK_CHECKPOINT_UNPROVEN')
            start=number(events[0]['before_quantity'])
            cp=dict(version=1,quantity=str(start),available=str(start),inventoryId=str(row['id']),
                evidenceDigest=fingerprint(events[0]),source='ERP_FIRST_LEDGER_BEFORE',
                postedAt=None,lastEventId=None,originAt=events[0]['created_at'],observedAt=inventory.get('observedAt'))
        basis['checkpoint']=cp; running=start; censored=[];zero_intervals=[]
        zero_start=(cp.get('originAt') or cp.get('observedAt')) if start==0 else None
        inbound={str(p['id']):p for p in inbound_proofs}
        for r in events:
            require(r.get('operation')=='post' and not r.get('reverses_id'), 'STOCK_EVENT_REVERSAL_UNSUPPORTED')
            before,after=number(r['before_quantity']),number(r['after_quantity'])
            delta=Decimal(str(r['delta_quantity']))
            require(delta.is_finite() and after-before==delta and Decimal(str(r['delta_available']))==delta
                and number(r['after_available'])-number(r['before_available'])==delta
                and number(r['before_available'])==before and number(r['after_available'])==after,'LEDGER_ARITHMETIC_MISMATCH')
            require(before==running,'STOCK_EVENT_CHAIN_GAP')
            if r.get('resource')=='outbound-orders': require(delta<0,'OUTBOUND_DIRECTION_INVALID')
            elif r.get('resource')=='inbound-orders':
                proof=inbound.get(str(r.get('record_id')))
                require(proof is not None,'INBOUND_POSTING_PROOF_MISSING')
                require(proof.get('verified') is True and proof.get('sku')==entity['sku']
                    and proof.get('inventoryId')==str(row['id']) and number(proof['postedQuantity'])==delta
                    and proof.get('ledgerId')==str(r['id']), 'INBOUND_POSTING_PROOF_INVALID')
                require(delta>0,'INBOUND_DIRECTION_INVALID')
            else:
                basis['unsupportedEvents'].append(str(r.get('resource')))
                raise StockError('STOCK_EVENT_TYPE_UNSUPPORTED')
            running=after
            if running==0 or before==0: censored.append(r['created_at'])
            if before>0 and after==0:zero_start=r['created_at']
            if before==0 and after>0 and zero_start:
                zero_intervals.append(dict(start=zero_start,end=r['created_at']));zero_start=None
        if zero_start:zero_intervals.append(dict(start=zero_start,end=inventory.get('observedAt')))
        basis.update(expectedPhysical=str(running),residual=str(running-physical),censoredAt=censored,zeroIntervals=zero_intervals)
        require(running==physical,'STOCK_MOVEMENT_RECONCILIATION_FAILED')
        basis.update(status='VERIFIED',eventCount=len(events),lastEventId=str(events[-1]['id']) if events else cp.get('lastEventId'),
            lastPostedAt=events[-1]['created_at'] if events else cp.get('postedAt'))
        if basis['historyStatus']=='UNVERIFIED': basis['historyStatus']='FULL_SOURCE_CHAIN_VERIFIED'
    except (StockError,KeyError,TypeError,ValueError,ArithmeticError) as exc:
        basis['issues'].append(str(exc) if isinstance(exc,StockError) else 'STOCK_FIELDS_INVALID')
    return basis
