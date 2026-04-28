from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.keyboards.admin_catalog import build_admin_category_keyboard, build_admin_product_keyboard
from app.keyboards.cart import build_cart_keyboard, build_checkout_confirmation_keyboard
from app.keyboards.catalog import build_product_keyboard
from app.keyboards.main_menu import get_main_menu_keyboard
from app.keyboards.operator_orders import (
    build_operator_order_detail_keyboard,
    build_operator_orders_keyboard,
)
from app.keyboards.payment import build_payment_confirmation_keyboard, build_retry_payment_keyboard
from app.services.admin_catalog_text import (
    format_admin_category_text,
    format_admin_product_text,
    format_admin_root_text,
)
from app.services.cart_text import format_cart_text, format_checkout_confirmation_text
from app.services.catalog_text import (
    build_categories_text,
    build_product_text,
    build_products_text,
)
from app.services.order_text import (
    format_active_orders_text,
    format_operator_order_details_text,
    format_operator_orders_list_text,
    format_order_status,
    format_order_status_notification_text,
)
from app.ui_text import format_ui_text, get_ui_text, load_ui_texts


def test_load_ui_texts_returns_dict() -> None:
    data = load_ui_texts()

    assert isinstance(data, dict)
    assert data["main_menu"]["catalog_button"] == "🛍 Каталог"
    assert data["main_menu"]["order_status_button"] == "Статус заказа"


def test_get_ui_text_reads_nested_value() -> None:
    assert get_ui_text("checkout", "confirm_button") == "Подтвердить заказ"
    assert get_ui_text("checkout", "main_menu_prompt") == "Выберите действие в главном меню."
    assert get_ui_text("payment", "pay_button") == "Оплатить заказ"


def test_format_ui_text_applies_placeholders() -> None:
    assert (
        format_ui_text("start", "welcome", first_name="Тест")
        == "Добро пожаловать, Тест! Бот запущен."
    )


def test_get_ui_text_raises_for_missing_path() -> None:
    with pytest.raises(KeyError):
        get_ui_text("missing", "path")


def test_main_menu_keyboard_uses_json_texts() -> None:
    keyboard = get_main_menu_keyboard()
    operator_keyboard = get_main_menu_keyboard("operator")
    admin_keyboard = get_main_menu_keyboard("admin")

    assert keyboard.keyboard[0][0].text == "🛍 Каталог"
    assert keyboard.keyboard[0][1].text == "🛒 Корзина"
    assert keyboard.keyboard[1][0].text == "Статус заказа"
    assert len(keyboard.keyboard) == 2
    assert operator_keyboard.keyboard[2][0].text == "Заказы"
    assert admin_keyboard.keyboard[2][0].text == "Заказы"
    assert admin_keyboard.keyboard[3][0].text == "Админ каталог"


def test_catalog_text_builders_preserve_existing_copy() -> None:
    category = SimpleNamespace(name="Футболки")
    product = SimpleNamespace(
        name="Белая футболка",
        price=Decimal("1999.00"),
        description=None,
    )
    attribute = SimpleNamespace(name="Размер", value="M")

    assert build_categories_text([category]) == "Выберите раздел:\nФутболки"
    assert build_products_text(category, [product]) == (
        "Футболки\n\nТовары:\nБелая футболка - 1999.00 ₽"
    )
    assert build_product_text(product, [attribute]) == (
        "Белая футболка\n"
        "Цена: 1999.00 ₽\n\n"
        "Описание: Описание отсутствует.\n\n"
        "Характеристики:\n"
        "Размер: M"
    )


def test_cart_text_builder_preserves_existing_copy() -> None:
    product = SimpleNamespace(name="Белая футболка", price=Decimal("1999.00"))
    cart_item = SimpleNamespace(product=product, quantity=2)
    cart = SimpleNamespace(items=[cart_item])
    summary = SimpleNamespace(
        phone="+79991234567",
        shipping_address="Москва, Тверская 1",
        total_amount=Decimal("3998.00"),
    )

    assert format_cart_text(cart) == (
        "Корзина:\n\n"
        "1. Белая футболка\n"
        "Цена: 1999.00 ₽\n"
        "Количество: 2\n"
        "Сумма: 3998.00 ₽\n\n"
        "Итого: 3998.00 ₽"
    )
    assert format_checkout_confirmation_text(cart, summary) == (
        "Корзина:\n\n"
        "1. Белая футболка\n"
        "Цена: 1999.00 ₽\n"
        "Количество: 2\n"
        "Сумма: 3998.00 ₽\n\n"
        "Итого: 3998.00 ₽\n\n"
        "Подтвердите заказ:\n"
        "Телефон: +79991234567\n"
        "Адрес: Москва, Тверская 1\n"
        "Итого к подтверждению: 3998.00 ₽"
    )


def test_keyboards_preserve_existing_button_copy() -> None:
    product = SimpleNamespace(id=1, name="Белая футболка", price=Decimal("1999.00"))
    cart_item = SimpleNamespace(id=5, product=product)

    product_keyboard = build_product_keyboard(product_id=1, category_id=2, parent_category_id=3)
    cart_keyboard = build_cart_keyboard([cart_item])
    checkout_keyboard = build_checkout_confirmation_keyboard()
    payment_keyboard = build_payment_confirmation_keyboard("https://pay.example/1")
    retry_keyboard = build_retry_payment_keyboard(order_id=7)

    assert [row[0].text for row in product_keyboard.inline_keyboard] == ["В корзину", "Назад"]
    assert [button.text for button in cart_keyboard.inline_keyboard[0]] == [
        "+",
        "-",
        "Удалить Белая футболка",
    ]
    assert cart_keyboard.inline_keyboard[1][0].text == "Очистить корзину"
    assert cart_keyboard.inline_keyboard[2][0].text == "Оформить заказ"
    assert checkout_keyboard.inline_keyboard[0][0].text == "Подтвердить заказ"
    assert checkout_keyboard.inline_keyboard[1][0].text == "Отменить"
    assert payment_keyboard.inline_keyboard[0][0].text == "Оплатить заказ"
    assert retry_keyboard.inline_keyboard[0][0].text == "Оплатить снова"


def test_order_status_text_builder_maps_known_and_unknown_statuses() -> None:
    orders = [
        SimpleNamespace(order_number="ORD-000001", status="new"),
        SimpleNamespace(order_number="ORD-000002", status="paid"),
        SimpleNamespace(order_number="ORD-000003", status="assembling"),
        SimpleNamespace(order_number="ORD-000004", status="accepted"),
        SimpleNamespace(order_number="ORD-000005", status="mystery"),
    ]
    operator_orders = [
        SimpleNamespace(
            id=1,
            order_number="ORD-100001",
            status="paid",
            phone="+79991234567",
            shipping_address="Москва, Тверская 1",
            total_amount=Decimal("3998.00"),
            payment_attempts=[
                SimpleNamespace(
                    status="succeeded",
                    provider_payment_id="pay_100001",
                    payment_method_type="bank_card",
                    failure_reason=None,
                )
            ],
            user=SimpleNamespace(first_name="Анна"),
        )
    ]

    keyboard = build_operator_orders_keyboard(operator_orders)
    detail_keyboard = build_operator_order_detail_keyboard(order_id=1, current_status="paid")

    assert format_order_status("new") == "Создан"
    assert format_order_status("accepted") == "Создан"
    assert format_order_status("paid") == "Оплачен"
    assert format_order_status("mystery") == "Статус: mystery"
    assert format_active_orders_text(orders) == (
        "Активные заказы:\n\n"
        "1. ORD-000001 - Создан\n"
        "2. ORD-000002 - Оплачен\n"
        "3. ORD-000003 - Собран\n"
        "4. ORD-000004 - Создан\n"
        "5. ORD-000005 - Статус: mystery"
    )
    assert format_operator_orders_list_text(operator_orders) == (
        "Активные заказы для обработки:\n\n1. ORD-100001 - Анна - Оплачен"
    )
    assert format_operator_order_details_text(operator_orders[0]) == (
        "Заказ: ORD-100001\n"
        "Покупатель: Анна\n"
        "Статус: Оплачен\n"
        "Телефон: +79991234567\n"
        "Адрес: Москва, Тверская 1\n"
        "Сумма: 3998.00 ₽\n\n"
        "Оплата:\n"
        "Попыток оплаты: 1\n"
        "Статус оплаты: оплачен\n"
        "Payment ID: pay_100001\n"
        "Метод: bank_card\n"
        "Причина ошибки: нет"
    )
    assert format_order_status_notification_text(operator_orders[0]) == (
        "Статус заказа ORD-100001 обновлен: Оплачен."
    )
    assert keyboard.inline_keyboard[0][0].text == "ORD-100001"
    assert any(
        button.text == "• Оплачен" for row in detail_keyboard.inline_keyboard for button in row
    )


def test_admin_catalog_text_and_keyboards() -> None:
    root_categories = [SimpleNamespace(name="Одежда")]
    child_category = SimpleNamespace(id=2, name="Футболки")
    product = SimpleNamespace(
        id=3,
        name="Белая футболка",
        price=Decimal("1999.00"),
        description=None,
        image_url=None,
        is_active=True,
    )

    category_keyboard = build_admin_category_keyboard(
        categories=[child_category],
        products=[product],
        current_category_id=1,
        parent_category_id=None,
        can_add_product=True,
    )
    product_keyboard = build_admin_product_keyboard(product_id=3, category_id=1, is_active=True)

    assert format_admin_root_text(root_categories) == "Админ каталог\n\nПодразделы:\n1. Одежда"
    assert format_admin_category_text(
        SimpleNamespace(name="Одежда"),
        [child_category],
        [product],
        can_add_product=True,
    ) == (
        "Раздел: Одежда\n\n"
        "Подразделы:\n"
        "1. Футболки\n\n"
        "Товары:\n"
        "1. Белая футболка - 1999.00 ₽ (активен)\n\n"
        "В этот раздел можно добавлять товары."
    )
    assert format_admin_product_text(product) == (
        "Товар: Белая футболка\n"
        "Цена: 1999.00 ₽\n"
        "Статус: активен\n"
        "Описание: Описание отсутствует.\n"
        "Image URL: Не указан."
    )
    assert category_keyboard.inline_keyboard[0][0].text == "Футболки"
    assert category_keyboard.inline_keyboard[1][0].text == "Белая футболка - 1999.00 ₽"
    assert any(
        button.text == "Добавить товар"
        for row in category_keyboard.inline_keyboard
        for button in row
    )
    assert any(
        button.text == "Скрыть товар" for row in product_keyboard.inline_keyboard for button in row
    )
