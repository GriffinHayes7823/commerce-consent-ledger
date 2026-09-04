from dataclasses import dataclass, field
from enum import StrEnum


class CommerceScope(StrEnum):
    CHECKOUT = "checkout"
    FULFILLMENT = "fulfillment"
    RECEIPTS = "receipts"
    ORDER_UPDATES = "order_updates"


@dataclass(frozen=True)
class ConsentGrant:
    user_id: str
    scopes: frozenset[CommerceScope]
    request_id: str


@dataclass
class ConsentLedger:
    """Small in-memory ledger; replace this boundary with durable storage in deployment."""

    _grants: dict[str, set[CommerceScope]] = field(default_factory=dict)
    _requests: dict[str, ConsentGrant] = field(default_factory=dict)

    def grant(
        self, user_id: str, scopes: set[CommerceScope], request_id: str
    ) -> ConsentGrant:
        previous = self._requests.get(request_id)
        candidate = ConsentGrant(user_id, frozenset(scopes), request_id)
        if previous is not None:
            if previous != candidate:
                raise ValueError("request_id was already used for a different grant")
            return previous

        self._grants.setdefault(user_id, set()).update(scopes)
        self._requests[request_id] = candidate
        return candidate

    def revoke(self, user_id: str, scopes: set[CommerceScope]) -> set[CommerceScope]:
        active = self._grants.setdefault(user_id, set())
        active.difference_update(scopes)
        return set(active)

    def active_scopes(self, user_id: str) -> set[CommerceScope]:
        return set(self._grants.get(user_id, set()))

    def permits(self, user_id: str, scope: CommerceScope) -> bool:
        return scope in self._grants.get(user_id, set())

