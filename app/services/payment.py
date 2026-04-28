from __future__ import annotations

import base64
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from aiohttp import BasicAuth, ClientSession
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.models.order import Order
from app.models.payment_attempt import PaymentAttempt
from app.ui_text import format_ui_text

logger = logging.getLogger(__name__)
settings = get_settings()

YOOKASSA_API_URL = "https://api.yookassa.ru/v3/payments"
YOOKASSA_PROVIDER = "yookassa"
PAYMENT_STATUS_PENDING = "pending"
PAYMENT_STATUS_SUCCEEDED = "succeeded"
PAYMENT_STATUS_CANCELED = "canceled"
PAYMENT_STATUS_WAITING_FOR_CAPTURE = "waiting_for_capture"
ACTIVE_PAYMENT_STATUSES = {PAYMENT_STATUS_PENDING, PAYMENT_STATUS_WAITING_FOR_CAPTURE}
FINAL_PAYMENT_STATUSES = {PAYMENT_STATUS_SUCCEEDED, PAYMENT_STATUS_CANCELED}


class PaymentError(Exception):
    pass


class PaymentConfigurationError(PaymentError):
    pass


class PaymentAttemptNotFoundError(PaymentError):
    pass


class PaymentOrderAccessError(PaymentError):
    pass


class PaymentAlreadyCompletedError(PaymentError):
    pass


class PaymentProviderError(PaymentError):
    pass


@dataclass(slots=True)
class CreatePaymentResult:
    provider_payment_id: str
    status: str
    amount: Decimal
    currency: str
    confirmation_url: str | None
    payment_method_type: str | None
    provider_payload: dict[str, Any]


@dataclass(slots=True)
class ProcessPaymentNotificationResult:
    attempt: PaymentAttempt | None
    order: Order | None
    should_notify_buyer: bool
    buyer_text: str | None


def _is_yookassa_enabled() -> bool:
    return bool(settings.yookassa_shop_id and settings.yookassa_secret_key)


def _normalize_amount(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _extract_payment_method_type(payment_object: dict[str, Any]) -> str | None:
    payment_method = payment_object.get("payment_method")
    if not isinstance(payment_method, dict):
        return None
    method_type = payment_method.get("type")
    if isinstance(method_type, str) and method_type:
        return method_type
    return None


def _extract_confirmation_url(payment_object: dict[str, Any]) -> str | None:
    confirmation = payment_object.get("confirmation")
    if not isinstance(confirmation, dict):
        return None
    confirmation_url = confirmation.get("confirmation_url")
    if isinstance(confirmation_url, str) and confirmation_url:
        return confirmation_url
    return None


def _extract_failure_reason(payment_object: dict[str, Any]) -> str | None:
    cancellation_details = payment_object.get("cancellation_details")
    if not isinstance(cancellation_details, dict):
        return None

    reason = cancellation_details.get("reason")
    party = cancellation_details.get("party")
    parts = [value for value in (reason, party) if isinstance(value, str) and value]
    return ", ".join(parts) if parts else None


class YookassaClient:
    async def create_payment(
        self,
        *,
        order: Order,
        idempotence_key: str,
    ) -> CreatePaymentResult:
        if not _is_yookassa_enabled():
            raise PaymentConfigurationError("yookassa credentials are not configured")

        payload = {
            "amount": {
                "value": f"{Decimal(str(order.total_amount)):.2f}",
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": settings.yookassa_return_url,
            },
            "description": f"Оплата заказа {order.order_number}",
            "metadata": {
                "order_id": str(order.id),
                "order_number": order.order_number,
            },
        }

        auth = BasicAuth(
            login=settings.yookassa_shop_id or "", password=settings.yookassa_secret_key or ""
        )
        headers = {
            "Idempotence-Key": idempotence_key,
        }

        async with ClientSession(auth=auth) as session:
            async with session.post(YOOKASSA_API_URL, json=payload, headers=headers) as response:
                response_payload = await response.json(content_type=None)
                if response.status >= 400:
                    raise PaymentProviderError(str(response_payload))

        payment_id = response_payload.get("id")
        status = response_payload.get("status")
        amount = response_payload.get("amount", {})
        value = amount.get("value")
        currency = amount.get("currency", "RUB")
        if not isinstance(payment_id, str) or not payment_id:
            raise PaymentProviderError("missing payment id in provider response")
        if not isinstance(status, str) or not status:
            raise PaymentProviderError("missing payment status in provider response")
        if value is None:
            raise PaymentProviderError("missing payment amount in provider response")

        return CreatePaymentResult(
            provider_payment_id=payment_id,
            status=status,
            amount=_normalize_amount(value),
            currency=str(currency),
            confirmation_url=_extract_confirmation_url(response_payload),
            payment_method_type=_extract_payment_method_type(response_payload),
            provider_payload=response_payload,
        )


def _build_payment_notification_text(order_number: str) -> str:
    return format_ui_text("payment", "failed_notification", order_number=order_number)


def _build_payment_success_text(order_number: str) -> str:
    return format_ui_text("payment", "success_notification", order_number=order_number)


async def get_order_with_payment_attempts(session: AsyncSession, order_id: int) -> Order | None:
    result = await session.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.payment_attempts),
        )
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_latest_payment_attempt(session: AsyncSession, order_id: int) -> PaymentAttempt | None:
    result = await session.execute(
        select(PaymentAttempt)
        .where(PaymentAttempt.order_id == order_id)
        .order_by(PaymentAttempt.created_at.desc(), PaymentAttempt.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_payment_attempt_by_provider_payment_id(
    session: AsyncSession,
    provider_payment_id: str,
) -> PaymentAttempt | None:
    result = await session.execute(
        select(PaymentAttempt)
        .options(selectinload(PaymentAttempt.order).selectinload(Order.user))
        .where(PaymentAttempt.provider == YOOKASSA_PROVIDER)
        .where(PaymentAttempt.provider_payment_id == provider_payment_id)
    )
    return result.scalar_one_or_none()


async def _count_payment_attempts(session: AsyncSession, order_id: int) -> int:
    result = await session.execute(
        select(func.count(PaymentAttempt.id)).where(PaymentAttempt.order_id == order_id)
    )
    return int(result.scalar_one())


async def create_payment_attempt_for_order(
    session: AsyncSession,
    order_id: int,
    *,
    client: YookassaClient | None = None,
) -> PaymentAttempt:
    order = await get_order_with_payment_attempts(session, order_id)
    if order is None:
        raise PaymentAttemptNotFoundError(f"order {order_id} not found")
    if order.status == "paid":
        raise PaymentAlreadyCompletedError(f"order {order_id} already paid")

    latest_attempt = order.payment_attempts[0] if order.payment_attempts else None
    if latest_attempt is not None and latest_attempt.status in ACTIVE_PAYMENT_STATUSES:
        return latest_attempt

    provider_client = client or YookassaClient()
    idempotence_key = str(uuid.uuid4())

    create_result = await provider_client.create_payment(
        order=order, idempotence_key=idempotence_key
    )

    try:
        attempt = PaymentAttempt(
            order_id=order.id,
            provider=YOOKASSA_PROVIDER,
            provider_payment_id=create_result.provider_payment_id,
            idempotence_key=idempotence_key,
            status=create_result.status,
            amount=create_result.amount,
            currency=create_result.currency,
            confirmation_url=create_result.confirmation_url,
            payment_method_type=create_result.payment_method_type,
            provider_payload=create_result.provider_payload,
        )
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)
        return attempt
    except SQLAlchemyError:
        await session.rollback()
        logger.exception("Failed to persist payment attempt order_id=%s", order_id)
        raise


async def retry_payment_for_order(
    session: AsyncSession,
    *,
    order_id: int,
    telegram_id: int,
    client: YookassaClient | None = None,
) -> PaymentAttempt:
    order = await get_order_with_payment_attempts(session, order_id)
    if order is None:
        raise PaymentAttemptNotFoundError(f"order {order_id} not found")
    if order.user is None or order.user.telegram_id != telegram_id:
        raise PaymentOrderAccessError(f"order {order_id} is not доступен")
    if order.status == "paid":
        raise PaymentAlreadyCompletedError(f"order {order_id} already paid")

    latest_attempt = order.payment_attempts[0] if order.payment_attempts else None
    if latest_attempt is not None and latest_attempt.status in ACTIVE_PAYMENT_STATUSES:
        return latest_attempt

    return await create_payment_attempt_for_order(session, order_id, client=client)


async def process_yookassa_notification(
    session: AsyncSession,
    payload: dict[str, Any],
) -> ProcessPaymentNotificationResult:
    event = payload.get("event")
    payment_object = payload.get("object")
    if not isinstance(event, str) or not isinstance(payment_object, dict):
        return ProcessPaymentNotificationResult(
            attempt=None,
            order=None,
            should_notify_buyer=False,
            buyer_text=None,
        )

    provider_payment_id = payment_object.get("id")
    if not isinstance(provider_payment_id, str) or not provider_payment_id:
        return ProcessPaymentNotificationResult(
            attempt=None,
            order=None,
            should_notify_buyer=False,
            buyer_text=None,
        )

    attempt = await get_payment_attempt_by_provider_payment_id(session, provider_payment_id)
    if attempt is None:
        return ProcessPaymentNotificationResult(
            attempt=None,
            order=None,
            should_notify_buyer=False,
            buyer_text=None,
        )

    order = attempt.order
    if order is None:
        raise PaymentAttemptNotFoundError(
            f"order for provider payment {provider_payment_id} not found"
        )

    status = payment_object.get("status")
    if not isinstance(status, str) or not status:
        status = attempt.status

    attempt.status = status
    attempt.confirmation_url = _extract_confirmation_url(payment_object) or attempt.confirmation_url
    attempt.payment_method_type = (
        _extract_payment_method_type(payment_object) or attempt.payment_method_type
    )
    attempt.failure_reason = _extract_failure_reason(payment_object)
    attempt.provider_payload = payload

    should_notify_buyer = False
    buyer_text: str | None = None
    if event == "payment.succeeded":
        attempt.confirmed_at = datetime.now(timezone.utc)
        if order.status != "paid":
            order.status = "paid"
            should_notify_buyer = True
            buyer_text = _build_payment_success_text(order.order_number)
    elif event == "payment.canceled":
        should_notify_buyer = True
        buyer_text = _build_payment_notification_text(order.order_number)

    try:
        await session.commit()
        await session.refresh(attempt)
        if order is not None:
            await session.refresh(order)
        return ProcessPaymentNotificationResult(
            attempt=attempt,
            order=order,
            should_notify_buyer=should_notify_buyer and order.user is not None,
            buyer_text=buyer_text,
        )
    except SQLAlchemyError:
        await session.rollback()
        logger.exception(
            "Failed to process YooKassa notification payment_id=%s", provider_payment_id
        )
        raise


def is_yookassa_enabled() -> bool:
    return _is_yookassa_enabled()


def build_yookassa_webhook_auth_header() -> str | None:
    if not _is_yookassa_enabled():
        return None
    token = f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}"
    encoded = base64.b64encode(token.encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"
