import pytest

from consent_service.consent_ledger import CommerceScope, ConsentLedger


def test_revoking_receipts_keeps_fulfillment_permission() -> None:
    ledger = ConsentLedger()
    ledger.grant(
        "customer-42",
        {CommerceScope.RECEIPTS, CommerceScope.FULFILLMENT},
        "grant-1001",
    )

    remaining = ledger.revoke("customer-42", {CommerceScope.RECEIPTS})

    assert remaining == {CommerceScope.FULFILLMENT}
    assert ledger.permits("customer-42", CommerceScope.RECEIPTS) is False
    assert ledger.permits("customer-42", CommerceScope.FULFILLMENT) is True


def test_request_id_cannot_describe_two_grants() -> None:
    ledger = ConsentLedger()
    ledger.grant("customer-42", {CommerceScope.CHECKOUT}, "grant-1001")

    with pytest.raises(ValueError, match="different grant"):
        ledger.grant("customer-42", {CommerceScope.RECEIPTS}, "grant-1001")

