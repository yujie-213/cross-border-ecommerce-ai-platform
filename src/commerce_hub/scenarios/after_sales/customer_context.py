"""Versioned, supplemental fictional claims for an explicitly imported ERP batch.

Never inferred from a title or SKU prefix; the live ERP record and exact owned
order/product relation must already have been independently resolved by D01.
This is customer narrative, never proof of a refund, receipt or quality defect.
"""
import json
from pathlib import Path
from .common import require,digest,timestamp,redacted

NATURE='SIMULATED_BUSINESS_DATA_IN_TEACHING_ERP'


def supplemental_messages(path,ticket,identities,store,expected):
    if path is None or not Path(path).is_file():return []
    raw=Path(path).read_bytes();require(len(raw)<=256000,'CUSTOMER_CONTEXT_LIMIT')
    manifest=json.loads(raw)
    require(manifest.get('schemaVersion')=='1.0.0' and manifest.get('sourceNature')==NATURE
        and manifest.get('version') and manifest.get('datasetId') and isinstance(manifest.get('items'),list)
        and len(manifest['items'])<=100,'CUSTOMER_CONTEXT_INVALID')
    matches=[i for i in manifest['items'] if i.get('erpTicketId')==str(ticket['id']) and i.get('erpStoreName')==store
        and i.get('sourceTenant')==expected['sourceTenant'] and i.get('storeId')==expected['storeId']]
    require(len(matches)<=1,'CUSTOMER_CONTEXT_AMBIGUOUS')
    if not matches:return []
    item=matches[0]
    require(item.get('orderNumber')==ticket.get('order_sn') and any(
        all(str(i.get(k))==str(item.get(k)) for k in ('orderId','productId','sku','storeId')) for i in identities),'CUSTOMER_CONTEXT_RELATION_MISMATCH')
    require(item.get('provenance')=='SUPPLEMENTAL_SIMULATED_CUSTOMER_STATEMENT'
        and isinstance(item.get('text'),str) and 0<len(item['text'])<=6000,'CUSTOMER_CONTEXT_INVALID')
    timestamp(item.get('at'))
    return [dict(role='CUSTOMER',text=redacted(item['text']),source='SIMULATED',sourceNature=NATURE,
        at=item['at'],sourceRef='customer-context:'+manifest['datasetId']+':'+manifest['version']+':'+str(ticket['id']),
        manifestHash=digest(manifest))]
