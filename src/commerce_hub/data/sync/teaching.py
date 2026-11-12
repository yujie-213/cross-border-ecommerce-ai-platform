"""D01 public SourceConnector bridge for a bounded, complete teaching read batch."""
from commerce_hub.adapters.erp import ERPError
from commerce_hub.data.sync import SourcePage, SourceFailure

class TeachingReadSource:
    def __init__(self,reader,path,parameters,*,method="GET",page_size=20,max_pages=5):
        self.reader,self.path,self.parameters=reader,path,parameters
        self.method,self.page_size,self.max_pages=method,page_size,max_pages
        self.batch=None

    def read_page(self,cursor):
        if cursor is not None:
            raise SourceFailure("ERP_UNSUPPORTED_BATCH_CURSOR")
        try:
            self.batch=self.reader.read(self.path,self.parameters,method=self.method,page_size=self.page_size,max_pages=self.max_pages)
        except ERPError as exc:
            error=SourceFailure(exc.code);error.status=exc.status
            # Original ERP codes deliberately do not trigger a second D01 retry layer.
            raise error from None
        if not self.batch.complete:
            raise SourceFailure("ERP_PAGINATION_INCOMPLETE")
        return SourcePage(self.batch.records,None,True)
