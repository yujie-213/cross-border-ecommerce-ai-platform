"""TEACHING_ERP_ONLY: explicit bounded capture and fixed, unadmitted observation package."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4
from dotenv import dotenv_values
from commerce_hub.adapters.erp import ERPConfig,TeachingERPReader,ERPError,https_transport,AUTH_PATH
from commerce_hub.data.projection.observed import project_observations
from commerce_hub.data.sync import read_pages,SourceFailure
from commerce_hub.data.sync.teaching import TeachingReadSource

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/"data/private/s01-erp-20261112"


def alias(kind,value):
    return kind+"-"+hashlib.sha256(str(value).encode()).hexdigest()[:20]


def capture():
    identity=json.loads((PRIVATE/"identity.json").read_text(encoding="utf-8"))
    if not identity.get("ownerConfirmed") or identity.get("ownerConfirmationRef")!="owner-message-20261112-SKT-OL-XXL" or identity.get("sku")!="SKT-OL-XXL":
        raise ERPError("PILOT_IDENTITY_NOT_CONFIRMED")
    values=dotenv_values(ROOT/".env.erp",interpolate=False)
    config=ERPConfig(base_url=values.get("ERP_BASE_URL") or "https://47.107.76.124/lingxing-erp",
        username=values.get("ERP_USERNAME") or "",password=values.get("ERP_PASSWORD") or "",access_token=values.get("ERP_ACCESS_TOKEN") or "",timeout=15,max_requests=24)
    PRIVATE.mkdir(parents=True,exist_ok=True)
    serial=[0]
    run_dir=PRIVATE/("capture-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid4().hex[:8])
    run_dir.mkdir()
    def transport(method,path,headers,body,settings):
        status,raw=https_transport(method,path,headers,body,settings)
        if not path.startswith(AUTH_PATH):
            serial[0]+=1;(run_dir/f"response-{serial[0]}.json").write_bytes(raw)
        return status,raw
    reader=TeachingERPReader(config,transport=transport)
    queries=[
        ("inventory","/api/v1/inventory",dict(wid=identity["warehouseId"],store_id=identity["storeId"],field="sku",q=identity["sku"],match="exact"),"GET"),
        ("product","/api/v1/products",dict(field="sku",q=identity["sku"],match="exact"),"GET"),
        ("store","/api/v1/store-authorizations",dict(ids=identity["storeId"]),"GET"),
        ("warehouse","/api/v1/warehouses",dict(ids=identity["warehouseId"]),"GET"),
        ("listing","/api/v1/listings",dict(field="sku",q=identity["sku"],match="exact",store_name=identity["storeName"]),"GET"),
        ("sales","/api/v1/sales-orders",dict(store_name=identity["storeName"],shipping_warehouse=identity["warehouseName"]),"GET"),
        ("purchases","/api/v1/purchase-orders",dict(field="warehouse_name",q=identity["warehouseName"],match="exact"),"GET"),
        ("quotes","/api/v1/supplier-quotes",dict(sku=identity["sku"]),"GET"),
        ("buckets","/erp/sc/routing/data/local_inventory/inventoryDetails",dict(wid=str(identity["warehouseId"]),sku=identity["sku"]),"POST"),
        ("voice_day","/api/v1/customer-voice",dict(store_id=identity["storeId"],kind="reviews",date_from="2026-09-16",date_to="2026-09-17"),"GET"),
        ("inbound_day","/api/v1/inbound-orders",dict(warehouse_name=identity["warehouseName"],date_from="2026-09-16",date_to="2026-09-17"),"GET")]
    results={}
    for name,path,params,method in queries:
        try:
            source=TeachingReadSource(reader,path,params,method=method,page_size=20,max_pages=5)
            read_pages(source,max_pages=1,max_records=100)
            batch=source.batch
            results[name]=dict(rows=list(batch.records),complete=batch.complete,total=batch.total,
                observedAt=batch.observed_at,fingerprint=batch.fingerprint,path=path,method=method,parameters=params)
        except (ERPError,SourceFailure) as error:
            results[name]=dict(error=error.code,status=getattr(error,"status",None),path=path,method=method,parameters=params)
    result=dict(data=results,events=reader.events,privateRunRef=run_dir.relative_to(ROOT).as_posix())
    (run_dir/"capture.json").write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+"\n").encode())
    (PRIVATE/"latest-capture.json").write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+"\n").encode())
    return result


def build_package(captured,identity,*,scope=None):
    data=captured["data"]
    inv=data.get("inventory",{}).get("rows",[])
    products=data.get("product",{}).get("rows",[])
    stores=data.get("store",{}).get("rows",[])
    warehouses=data.get("warehouse",{}).get("rows",[])
    listings=data.get("listing",{}).get("rows",[])
    if (not inv or len(products)!=1 or len(stores)!=1 or len(warehouses)!=1 or not listings
        or not all(x.get("sku")==identity["sku"] and str(x.get("wid"))==str(identity["warehouseId"])
            and str(x.get("store_id"))==str(identity["storeId"]) and x.get("tenant_id")==identity["tenantId"] for x in inv)
        or products[0].get("sku")!=identity["sku"]
        or str(stores[0].get("id"))!=str(identity["storeId"]) or str(warehouses[0].get("id"))!=str(identity["warehouseId"])
        or any(x.get("tenant_id")!=identity["tenantId"] for x in [products[0],stores[0],warehouses[0],*listings])
        or any(x.get("sku")!=identity["sku"] or x.get("store_name")!=identity["storeName"] for x in listings)
        or any(data[x].get("complete") is not True for x in ["inventory","product","store","warehouse","listing"])):
        raise ERPError("ERP_IDENTITY_MAPPING_NOT_VERIFIED")
    scope=scope or dict(tenantId="teaching-"+uuid4().hex,canonicalSkuIds=[alias("sku",identity["sku"])],
        storeIds=[alias("store",identity["storeId"])],warehouseIds=[alias("warehouse",identity["warehouseId"])],fields=["quantity"])
    def refs(*names):
        return ["read-"+data[n]["fingerprint"] for n in names if data.get(n,{}).get("fingerprint")]
    def measurement(key,value,unit):
        return dict(field=key,value=None if value is None else str(value),unit=unit)
    def domain(name,state,names,measurements=(),times=()):
        return dict(domain=name,state=state,measurements=list(measurements),sourceTimes=list(times),sourceRefs=refs(*names))
    product=products[0]
    inventory_values=[]
    for row in inv:
        for key in ["quantity","available"]:
            inventory_values.append(measurement("physical" if key=="quantity" else "available",row.get(key),"SOURCE_PIECE"))
    moq=[measurement("moq",product.get("moq"),"SOURCE_PIECE")]
    for quote in data.get("quotes",{}).get("rows",[]):
        # Monetary constraints stay private; quantity-only G01 scope cannot expose amounts.
        moq += [measurement("quote_moq",quote.get("minimum_quantity"),"SOURCE_PIECE")]
    domains=[domain("identity","OBSERVED",["inventory","product","store","warehouse","listing"]),
        domain("inventory","OBSERVED",["inventory","buckets"],inventory_values,[r["updated_at"] for r in inv if r.get("updated_at")]),
        domain("demand","ERROR" if data.get("sales",{}).get("error") else "INCOMPLETE",["sales"]),domain("supply","INCOMPLETE",["purchases"]),
        domain("availability","MISSING",["product","purchases"],[measurement("lead_days",product.get("procurement_lead_days"),"DAYS")]),
        domain("moq","OBSERVED",["product","quotes"],moq),
        domain("orderMultiple","MISSING",["product"],[measurement("carton_quantity",product.get("default_carton_qty"),"SOURCE_PIECE")]),
        domain("quality","INCOMPLETE",["inbound_day","voice_day","product"])]
    return project_observations(dict(sourceSynthetic=identity.get("sourceSynthetic") is True,
        ownerConfirmed=identity.get("ownerConfirmed") is True,scope=scope,
        revalidationFailed=captured.get("revalidationFailed",False),
        observedAt=max(datetime.fromisoformat(x["observedAt"]) for x in data.values() if x.get("observedAt")),domains=domains)).model_dump(mode="json")


def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group();group.add_argument("--capture",action="store_true");group.add_argument("--input-capture",type=Path);args=parser.parse_args()
    try:
        if args.input_capture:
            path=args.input_capture.resolve()
            if not path.is_relative_to(PRIVATE.resolve()):
                raise ERPError("CONTROLLED_CAPTURE_PATH_REJECTED")
            captured=json.loads(path.read_text(encoding="utf-8"))
        else:
            captured=capture() if args.capture else json.loads((PRIVATE/"latest-capture.json").read_text(encoding="utf-8"))
        identity=json.loads((PRIVATE/"identity.json").read_text(encoding="utf-8"))
        projection=build_package(captured,identity)
        (PRIVATE/"projection.json").write_bytes((json.dumps(projection,ensure_ascii=False,indent=2)+"\n").encode())
        print(json.dumps(dict(result="OBSERVATIONS_CAPTURED_ADMISSION_BLOCKED",sourceNature=projection["sourceNature"],
            packageRef=projection["revision"],realBusinessAdmission="BLOCKED",erpCalls=len(captured["events"]) if args.capture else 0)))
        return 0
    except Exception as error:
        print(json.dumps(dict(result="FAIL",code=error.code if isinstance(error,(ERPError,SourceFailure)) else "CONTROLLED_PACKAGE_NOT_AVAILABLE")))
        return 1


if __name__=="__main__":raise SystemExit(main())
