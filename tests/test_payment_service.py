from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.models.user import User
from app.services.payment import (
    CreatePaymentResult,
    create_payment_attempt_for_order,
    process_yookassa_notification,
    retry_payment_for_order,
)


class FakeYookassaClient:
    def __init__(self, payment_id: str = "pay_1001", status: str = "pending") -> None:
        self.payment_id = payment_id
        self.status = status

    async def create_payment(self, *, order, idempotence_key: str) -> CreatePaymentResult:
        return CreatePaymentResult(
            provider_payment_id=self.payment_id,
            status=self.status,
            amount=Decimal(str(order.total_amount)),
            currency="RUB",
            confirmation_url=f"https://pay.example/{self.payment_id}",
            payment_method_type="bank_card",
            provider_payload={"id": self.payment_id, "status": self.status},
        )


@pytest.mark.asyncio
async def test_create_payment_attempt_for_order_persists_provider_payment(db_session) -> None:
    user = User(telegram_id=661001, username="buyer", first_name="Buyer", last_name="One")
    db_session.add(user)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        order_number="ORD-661001",
        status="new",
        phone="+79990000001",
        shipping_address="Москва, Арбат 1",
        total_amount=Decimal("1500.00"),
    )
    db_session.add(order)
    await db_session.commit()

    attempt = await create_payment_attempt_for_order(
        db_session,
        order.id,
        client=FakeYookassaClient(),
    )

    persisted = await db_session.execute(
        select(PaymentAttempt).where(PaymentAttempt.id == attempt.id)
    )
    saved_attempt = persisted.scalar_one()
    assert saved_attempt.provider_payment_id == "pay_1001"
    assert saved_attempt.confirmation_url == "https://pay.example/pay_1001"
    assert saved_attempt.status == "pending"


@pytest.mark.asyncio
async def test_retry_payment_for_order_reuses_active_attempt(db_session) -> None:
    user = User(telegram_id=661002, username="buyer2", first_name="Buyer", last_name="Two")
    db_session.add(user)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        order_number="ORD-661002",
        status="new",
        phone="+79990000002",
        shipping_address="Москва, Арбат 2",
        total_amount=Decimal("2500.00"),
    )
    db_session.add(order)
    await db_session.flush()
    attempt = PaymentAttempt(
        order_id=order.id,
        provider="yookassa",
        provider_payment_id="pay_1002",
        idempotence_key="idem_1002",
        status="pending",
        amount=Decimal("2500.00"),
        currency="RUB",
        confirmation_url="https://pay.example/pay_1002",
    )
    db_session.add(attempt)
    await db_session.commit()

    reused_attempt = await retry_payment_for_order(
        db_session,
        order_id=order.id,
        telegram_id=user.telegram_id,
        client=FakeYookassaClient(payment_id="pay_other"),
    )

    assert reused_attempt.id == attempt.id


@pytest.mark.asyncio
async def test_process_yookassa_notification_marks_order_paid(db_session) -> None:
    user = User(telegram_id=661003, username="buyer3", first_name="Buyer", last_name="Three")
    db_session.add(user)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        order_number="ORD-661003",
        status="new",
        phone="+79990000003",
        shipping_address="Москва, Арбат 3",
        total_amount=Decimal("3500.00"),
    )
    db_session.add(order)
    await db_session.flush()
    attempt = PaymentAttempt(
        order_id=order.id,
        provider="yookassa",
        provider_payment_id="pay_1003",
        idempotence_key="idem_1003",
        status="pending",
        amount=Decimal("3500.00"),
        currency="RUB",
        confirmation_url="https://pay.example/pay_1003",
    )
    db_session.add(attempt)
    await db_session.commit()

    result = await process_yookassa_notification(
        db_session,
        {
            "event": "payment.succeeded",
            "object": {
                "id": "pay_1003",
                "status": "succeeded",
                "payment_method": {"type": "bank_card"},
            },
        },
    )

    refreshed_order = await db_session.execute(select(Order).where(Order.id == order.id))
    saved_order = refreshed_order.scalar_one()
    refreshed_attempt = await db_session.execute(
        select(PaymentAttempt).where(PaymentAttempt.id == attempt.id)
    )
    saved_attempt = refreshed_attempt.scalar_one()
    assert result.should_notify_buyer is True
    assert result.buyer_text == "Оплата заказа ORD-661003 подтверждена."
    assert saved_order.status == "paid"
    assert saved_attempt.status == "succeeded"
    assert saved_attempt.payment_method_type == "bank_card"


@pytest.mark.asyncio
async def test_process_yookassa_notification_marks_attempt_canceled(db_session) -> None:
    user = User(telegram_id=661004, username="buyer4", first_name="Buyer", last_name="Four")
    db_session.add(user)
    await db_session.flush()
    order = Order(
        user_id=user.id,
        order_number="ORD-661004",
        status="new",
        phone="+79990000004",
        shipping_address="Москва, Арбат 4",
        total_amount=Decimal("4500.00"),
    )
    db_session.add(order)
    await db_session.flush()
    attempt = PaymentAttempt(
        order_id=order.id,
        provider="yookassa",
        provider_payment_id="pay_1004",
        idempotence_key="idem_1004",
        status="pending",
        amount=Decimal("4500.00"),
        currency="RUB",
        confirmation_url="https://pay.example/pay_1004",
    )
    db_session.add(attempt)
    await db_session.commit()

    result = await process_yookassa_notification(
        db_session,
        {
            "event": "payment.canceled",
            "object": {
                "id": "pay_1004",
                "status": "canceled",
                "cancellation_details": {"reason": "expired_on_confirmation", "party": "yookassa"},
            },
        },
    )

    refreshed_attempt = await db_session.execute(
        select(PaymentAttempt).where(PaymentAttempt.id == attempt.id)
    )
    saved_attempt = refreshed_attempt.scalar_one()
    assert result.should_notify_buyer is True
    assert result.buyer_text == "Оплата заказа ORD-661004 не завершена. Можно попробовать еще раз."
    assert saved_attempt.status == "canceled"
    assert saved_attempt.failure_reason == "expired_on_confirmation, yookassa"
