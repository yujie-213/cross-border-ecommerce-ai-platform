"""D01 read-only source port and explicitly simulated inline adapter."""
from dataclasses import dataclass
from typing import Protocol

from commerce_hub.data.contracts import FixtureInput, fingerprint


class SourceFailure(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class SourcePage:
    records: tuple[dict, ...]
    next_cursor: str | None
    complete: bool


class SourceConnector(Protocol):
    def read_page(self, cursor: str | None) -> SourcePage: ...


def read_pages(connector: SourceConnector, *, max_pages=10, max_records=1000):
    """No fallback connector. Failed/incomplete batches are never returned as complete."""
    cursor, seen, records = None, set(), []
    for _ in range(max_pages):
        for attempt in range(2):
            try:
                page = connector.read_page(cursor)
                break
            except SourceFailure as exc:
                if exc.code not in {"SOURCE_TIMEOUT", "SOURCE_503"} or attempt == 1:
                    raise
        records.extend(page.records)
        if len(records) > max_records:
            raise SourceFailure("SOURCE_LIMIT")
        if page.next_cursor is None:
            if not page.complete:
                raise SourceFailure("SOURCE_INCOMPLETE")
            return tuple(records)
        if page.next_cursor in seen:
            raise SourceFailure("SOURCE_CURSOR_LOOP")
        seen.add(page.next_cursor)
        cursor = page.next_cursor
    raise SourceFailure("SOURCE_PAGE_LIMIT")


class FixtureConnector:
    """Receives an inline bounded DTO, never opens a path, URL or ERP connection."""
    def read(self, parameters):
        value = FixtureInput.model_validate(parameters)
        digest = fingerprint(value.model_dump(mode="json"))
        return value, "fixture-batch-" + digest
