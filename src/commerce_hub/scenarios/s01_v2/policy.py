"""Explicit business read authorization; independently narrow purchase authorization."""
from .handler import collection_scope


class V2Policy:
    def __init__(self,app_tenant,source_tenant,*,owned_mappings=(),owned_provider=None,requisition_enabled=False):
        self.app_tenant,self.source_tenant=app_tenant,str(source_tenant)
        self.owned_mappings=owned_mappings
        self.owned_provider=owned_provider
        self.requisition_enabled=requisition_enabled
    def opening_binding(self,entity):
        return next((m for m in self.owned_mappings if (m.sourceTenant,m.sourceStore,m.sourceWarehouse,m.monitor.productId)==
            (entity['sourceTenant'],entity['storeId'],entity['warehouseId'],entity['productId'])),None)
    def can_write(self,entity):
        current=self.owned_provider() if self.owned_provider else self.owned_mappings
        return self.requisition_enabled and any((m.sourceTenant,m.sourceStore,m.sourceWarehouse,m.monitor.productId)==
            (entity['sourceTenant'],entity['storeId'],entity['warehouseId'],entity['productId']) for m in current)
    def require_scope(self,scope):
        if scope!=collection_scope(self.app_tenant):raise ValueError('V2_COLLECTION_SCOPE_INVALID')
