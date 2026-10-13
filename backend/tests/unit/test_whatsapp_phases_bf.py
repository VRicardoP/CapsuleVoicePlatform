"""
Unit tests for WhatsApp Pydantic schemas — Phases B through F.

Tests verify field constraints, validation, defaults, and serialization.
No database required.
"""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.whatsapp import (
    # Phase D: Campaigns
    WACampaignCreateRequest,
    WACampaignRecipientResponse,
    WACampaignResponse,
    WACampaignUpdateRequest,
    # Phase F: Commerce
    WACatalogItemCreateRequest,
    WACatalogItemResponse,
    WACatalogItemUpdateRequest,
    # Phase B: Contacts
    WAContactCreateRequest,
    WAContactDetailResponse,
    WAContactListResponse,
    # Phase E: Pipeline
    WADealCreateRequest,
    WADealMoveRequest,
    WADealResponse,
    WADealUpdateRequest,
    WAOrderCreateRequest,
    WAOrderItemResponse,
    WAOrderListResponse,
    WAOrderResponse,
    WAOrderUpdateRequest,
    WAPipelineAnalyticsResponse,
    WAPipelineStageCreateRequest,
    WAPipelineStageResponse,
    WAPipelineStageUpdateRequest,
    # Phase C: Templates
    WATemplateCreateRequest,
    WATemplateResponse,
    WATemplateSendRequest,
    WATemplateUpdateRequest,
)

# =============================================================================
# Phase B: Contacts
# =============================================================================


class TestWAContactCreateRequest:
    def test_valid_minimal(self):
        req = WAContactCreateRequest(phone_e164="+34612345678")
        assert req.phone_e164 == "+34612345678"
        assert req.source == "manual"

    def test_valid_full(self):
        req = WAContactCreateRequest(
            phone_e164="+34612345678",
            display_name="Maria Garcia",
            email="maria@example.com",
            notes="VIP client",
            source="csv_import",
        )
        assert req.display_name == "Maria Garcia"
        assert req.email == "maria@example.com"
        assert req.source == "csv_import"

    def test_empty_phone_rejected(self):
        with pytest.raises(ValidationError):
            WAContactCreateRequest(phone_e164="")

    def test_phone_max_length(self):
        with pytest.raises(ValidationError):
            WAContactCreateRequest(phone_e164="+" + "1" * 20)

    def test_optional_fields_default_none(self):
        req = WAContactCreateRequest(phone_e164="+1234567890")
        assert req.display_name is None
        assert req.email is None
        assert req.notes is None


class TestWAContactDetailResponse:
    def test_full_contact(self):
        now = datetime.now(UTC)
        resp = WAContactDetailResponse(
            id=uuid4(),
            phone_e164="+34612345678",
            display_name="Test",
            opt_in_status="opted_in",
            source="inbound",
            created_at=now,
            updated_at=now,
        )
        assert resp.display_name == "Test"
        assert resp.opt_in_status == "opted_in"

    def test_optional_fields(self):
        now = datetime.now(UTC)
        resp = WAContactDetailResponse(
            id=uuid4(),
            phone_e164="+34612345678",
            created_at=now,
            updated_at=now,
        )
        assert resp.email is None
        assert resp.segments == []
        assert resp.tags == []
        assert resp.opt_in_status == "unknown"


class TestWAContactListResponse:
    def test_empty_list(self):
        resp = WAContactListResponse(items=[], total=0)
        assert resp.total == 0


# =============================================================================
# Phase C: Templates
# =============================================================================


class TestWATemplateCreateRequest:
    def test_valid_minimal(self):
        req = WATemplateCreateRequest(name="promo_enero", body_text="Feliz ano nuevo!")
        assert req.name == "promo_enero"
        assert req.language == "es"
        assert req.category == "MARKETING"

    def test_valid_full(self):
        req = WATemplateCreateRequest(
            name="auth_code",
            language="en",
            category="AUTHENTICATION",
            body_text="Your code is {{1}}",
            footer="Do not share",
            buttons={"type": "QUICK_REPLY", "text": "OK"},
            variables={"1": "code"},
        )
        assert req.category == "AUTHENTICATION"
        assert req.footer == "Do not share"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            WATemplateCreateRequest(name="", body_text="test")

    def test_empty_body_rejected(self):
        with pytest.raises(ValidationError):
            WATemplateCreateRequest(name="test", body_text="")

    def test_footer_max_60(self):
        req = WATemplateCreateRequest(name="t", body_text="b", footer="A" * 60)
        assert len(req.footer) == 60
        with pytest.raises(ValidationError):
            WATemplateCreateRequest(name="t", body_text="b", footer="A" * 61)


class TestWATemplateUpdateRequest:
    def test_partial_update(self):
        req = WATemplateUpdateRequest(name="new_name")
        assert req.name == "new_name"
        assert req.body_text is None

    def test_empty_update(self):
        req = WATemplateUpdateRequest()
        assert req.name is None


class TestWATemplateSendRequest:
    def test_valid(self):
        uid = uuid4()
        req = WATemplateSendRequest(template_id=uid)
        assert req.template_id == uid

    def test_missing_template_id_rejected(self):
        with pytest.raises(ValidationError):
            WATemplateSendRequest()

    def test_invalid_uuid_rejected(self):
        with pytest.raises(ValidationError):
            WATemplateSendRequest(template_id="not-a-uuid")


class TestWATemplateResponse:
    def test_full_response(self):
        now = datetime.now(UTC)
        resp = WATemplateResponse(
            id=uuid4(),
            name="test_template",
            language="es",
            category="MARKETING",
            status="approved",
            body_text="Hello {{1}}!",
            created_at=now,
            updated_at=now,
        )
        assert resp.status == "approved"
        assert resp.header_type is None


# =============================================================================
# Phase D: Campaigns
# =============================================================================


class TestWACampaignCreateRequest:
    def test_valid_minimal(self):
        req = WACampaignCreateRequest(name="Black Friday")
        assert req.name == "Black Friday"
        assert req.is_ab_test is False

    def test_valid_full(self):
        uid = uuid4()
        now = datetime.now(UTC)
        req = WACampaignCreateRequest(
            name="Promo",
            template_id=uid,
            audience_filter={"segment_ids": ["abc"]},
            scheduled_at=now,
            is_ab_test=True,
        )
        assert req.template_id == uid
        assert req.audience_filter == {"segment_ids": ["abc"]}

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            WACampaignCreateRequest(name="")

    def test_name_max_length(self):
        with pytest.raises(ValidationError):
            WACampaignCreateRequest(name="A" * 256)


class TestWACampaignUpdateRequest:
    def test_partial_update(self):
        req = WACampaignUpdateRequest(name="Updated")
        assert req.name == "Updated"
        assert req.template_id is None


class TestWACampaignResponse:
    def test_full_response(self):
        now = datetime.now(UTC)
        resp = WACampaignResponse(
            id=uuid4(),
            name="Test Campaign",
            status="sending",
            total_recipients=100,
            sent_count=50,
            delivered_count=45,
            read_count=20,
            failed_count=5,
            created_at=now,
            updated_at=now,
        )
        assert resp.sent_count == 50
        assert resp.is_ab_test is False

    def test_defaults(self):
        now = datetime.now(UTC)
        resp = WACampaignResponse(
            id=uuid4(),
            name="Test",
            status="draft",
            created_at=now,
            updated_at=now,
        )
        assert resp.total_recipients == 0
        assert resp.template_name is None


class TestWACampaignRecipientResponse:
    def test_full(self):
        now = datetime.now(UTC)
        resp = WACampaignRecipientResponse(
            id=uuid4(),
            contact_id=uuid4(),
            contact_name="Maria",
            contact_phone="+34612345678",
            status="delivered",
            sent_at=now,
            delivered_at=now,
        )
        assert resp.status == "delivered"

    def test_failed(self):
        resp = WACampaignRecipientResponse(
            id=uuid4(),
            contact_id=uuid4(),
            status="failed",
            error_detail="Rate limited",
        )
        assert resp.error_detail == "Rate limited"


# =============================================================================
# Phase E: Pipeline
# =============================================================================


class TestWAPipelineStageCreateRequest:
    def test_valid_minimal(self):
        req = WAPipelineStageCreateRequest(name="Nuevo Lead")
        assert req.color == "#6B7280"
        assert req.sort_order == 0

    def test_valid_full(self):
        req = WAPipelineStageCreateRequest(
            name="Ganado",
            color="#10B981",
            sort_order=5,
            is_won=True,
        )
        assert req.is_won is True

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            WAPipelineStageCreateRequest(name="")

    def test_invalid_color_rejected(self):
        with pytest.raises(ValidationError):
            WAPipelineStageCreateRequest(name="Test", color="red")

    def test_valid_color_pattern(self):
        req = WAPipelineStageCreateRequest(name="Test", color="#FF00AA")
        assert req.color == "#FF00AA"

    def test_lowercase_hex_accepted(self):
        req = WAPipelineStageCreateRequest(name="Test", color="#ff00aa")
        assert req.color == "#ff00aa"


class TestWAPipelineStageUpdateRequest:
    def test_partial(self):
        req = WAPipelineStageUpdateRequest(name="Renamed")
        assert req.name == "Renamed"
        assert req.color is None

    def test_invalid_color_rejected(self):
        with pytest.raises(ValidationError):
            WAPipelineStageUpdateRequest(color="not-hex")


class TestWAPipelineStageResponse:
    def test_full(self):
        resp = WAPipelineStageResponse(
            id=uuid4(),
            name="Contactado",
            color="#3B82F6",
            sort_order=1,
            deal_count=5,
            deal_value=Decimal("15000"),
        )
        assert resp.deal_count == 5
        assert resp.deal_value == Decimal("15000")


class TestWADealCreateRequest:
    def test_valid_minimal(self):
        sid = uuid4()
        req = WADealCreateRequest(stage_id=sid, title="Venta grande")
        assert req.value == Decimal("0")
        assert req.currency == "EUR"

    def test_valid_full(self):
        req = WADealCreateRequest(
            stage_id=uuid4(),
            title="Enterprise deal",
            contact_id=uuid4(),
            value=Decimal("50000"),
            currency="USD",
            expected_close_date=date(2026, 3, 15),
            notes="Important client",
        )
        assert req.expected_close_date == date(2026, 3, 15)

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            WADealCreateRequest(stage_id=uuid4(), title="")

    def test_missing_stage_rejected(self):
        with pytest.raises(ValidationError):
            WADealCreateRequest(title="Test")


class TestWADealUpdateRequest:
    def test_partial_update(self):
        req = WADealUpdateRequest(value=Decimal("1000"))
        assert req.value == Decimal("1000")
        assert req.title is None


class TestWADealMoveRequest:
    def test_valid(self):
        sid = uuid4()
        req = WADealMoveRequest(stage_id=sid)
        assert req.stage_id == sid

    def test_missing_stage_rejected(self):
        with pytest.raises(ValidationError):
            WADealMoveRequest()


class TestWADealResponse:
    def test_full(self):
        now = datetime.now(UTC)
        resp = WADealResponse(
            id=uuid4(),
            stage_id=uuid4(),
            stage_name="Interesado",
            title="Big deal",
            value=Decimal("25000"),
            created_at=now,
            updated_at=now,
        )
        assert resp.stage_name == "Interesado"

    def test_defaults(self):
        now = datetime.now(UTC)
        resp = WADealResponse(
            id=uuid4(),
            stage_id=uuid4(),
            title="Test",
            created_at=now,
            updated_at=now,
        )
        assert resp.value == Decimal("0")
        assert resp.currency == "EUR"
        assert resp.contact_name is None


class TestWAPipelineAnalyticsResponse:
    def test_defaults(self):
        resp = WAPipelineAnalyticsResponse()
        assert resp.total_deals == 0
        assert resp.conversion_rate == 0.0
        assert resp.stages == []

    def test_with_data(self):
        stage = WAPipelineStageResponse(
            id=uuid4(),
            name="Won",
            color="#10B981",
            sort_order=5,
            deal_count=10,
            deal_value=Decimal("100000"),
        )
        resp = WAPipelineAnalyticsResponse(
            total_deals=50,
            total_value=Decimal("500000"),
            won_deals=10,
            won_value=Decimal("100000"),
            conversion_rate=0.2,
            stages=[stage],
        )
        assert len(resp.stages) == 1
        assert resp.won_value == Decimal("100000")


# =============================================================================
# Phase F: Commerce
# =============================================================================


class TestWACatalogItemCreateRequest:
    def test_valid_minimal(self):
        req = WACatalogItemCreateRequest(name="Widget", price=Decimal("9.99"))
        assert req.currency == "EUR"
        assert req.stock is None

    def test_valid_full(self):
        req = WACatalogItemCreateRequest(
            name="Premium Widget",
            description="Best widget ever",
            price=Decimal("29.99"),
            currency="USD",
            image_url="https://example.com/img.jpg",
            category="Electronics",
            sku="WDG-001",
            stock=100,
        )
        assert req.sku == "WDG-001"
        assert req.stock == 100

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            WACatalogItemCreateRequest(name="", price=Decimal("1"))

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            WACatalogItemCreateRequest(name="Test", price=Decimal("-1"))

    def test_zero_price_allowed(self):
        req = WACatalogItemCreateRequest(name="Free", price=Decimal("0"))
        assert req.price == Decimal("0")


class TestWACatalogItemUpdateRequest:
    def test_partial(self):
        req = WACatalogItemUpdateRequest(stock=50)
        assert req.stock == 50
        assert req.name is None

    def test_status_update(self):
        req = WACatalogItemUpdateRequest(status="inactive")
        assert req.status == "inactive"


class TestWACatalogItemResponse:
    def test_full(self):
        now = datetime.now(UTC)
        resp = WACatalogItemResponse(
            id=uuid4(),
            name="Widget",
            price=Decimal("9.99"),
            status="active",
            created_at=now,
            updated_at=now,
        )
        assert resp.status == "active"


class TestWAOrderCreateRequest:
    def test_valid(self):
        req = WAOrderCreateRequest(
            contact_id=uuid4(),
            items=[{"name": "Widget", "quantity": 2, "unit_price": 9.99}],
        )
        assert len(req.items) == 1

    def test_empty_items_rejected(self):
        with pytest.raises(ValidationError):
            WAOrderCreateRequest(items=[])

    def test_missing_items_rejected(self):
        with pytest.raises(ValidationError):
            WAOrderCreateRequest()


class TestWAOrderUpdateRequest:
    def test_status_update(self):
        req = WAOrderUpdateRequest(status="shipped")
        assert req.status == "shipped"


class TestWAOrderItemResponse:
    def test_full(self):
        resp = WAOrderItemResponse(
            id=uuid4(),
            catalog_item_id=uuid4(),
            name="Widget",
            quantity=3,
            unit_price=Decimal("9.99"),
        )
        assert resp.quantity == 3


class TestWAOrderResponse:
    def test_full(self):
        now = datetime.now(UTC)
        item = WAOrderItemResponse(
            id=uuid4(),
            name="Widget",
            quantity=2,
            unit_price=Decimal("9.99"),
        )
        resp = WAOrderResponse(
            id=uuid4(),
            status="confirmed",
            total=Decimal("19.98"),
            items=[item],
            created_at=now,
            updated_at=now,
        )
        assert len(resp.items) == 1
        assert resp.total == Decimal("19.98")

    def test_empty_order(self):
        now = datetime.now(UTC)
        resp = WAOrderResponse(
            id=uuid4(),
            status="pending",
            total=Decimal("0"),
            created_at=now,
            updated_at=now,
        )
        assert resp.items == []
        assert resp.contact_name is None


class TestWAOrderListResponse:
    def test_empty(self):
        resp = WAOrderListResponse(items=[], total=0)
        assert resp.total == 0
