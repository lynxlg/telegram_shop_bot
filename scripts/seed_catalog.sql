DO $$
DECLARE
    clothing_id BIGINT;
    tshirts_id BIGINT;
    hoodies_id BIGINT;
    pants_id BIGINT;
    white_tshirt_id BIGINT;
    black_tshirt_id BIGINT;
    gray_hoodie_id BIGINT;
    blue_jeans_id BIGINT;
BEGIN
    SELECT id INTO clothing_id
    FROM categories
    WHERE name = 'Одежда' AND parent_id IS NULL
    LIMIT 1;

    IF clothing_id IS NULL THEN
        INSERT INTO categories (name, parent_id)
        VALUES ('Одежда', NULL)
        RETURNING id INTO clothing_id;
    END IF;

    SELECT id INTO tshirts_id
    FROM categories
    WHERE name = 'Футболки' AND parent_id = clothing_id
    LIMIT 1;

    IF tshirts_id IS NULL THEN
        INSERT INTO categories (name, parent_id)
        VALUES ('Футболки', clothing_id)
        RETURNING id INTO tshirts_id;
    END IF;

    SELECT id INTO hoodies_id
    FROM categories
    WHERE name = 'Худи' AND parent_id = clothing_id
    LIMIT 1;

    IF hoodies_id IS NULL THEN
        INSERT INTO categories (name, parent_id)
        VALUES ('Худи', clothing_id)
        RETURNING id INTO hoodies_id;
    END IF;

    SELECT id INTO pants_id
    FROM categories
    WHERE name = 'Брюки' AND parent_id = clothing_id
    LIMIT 1;

    IF pants_id IS NULL THEN
        INSERT INTO categories (name, parent_id)
        VALUES ('Брюки', clothing_id)
        RETURNING id INTO pants_id;
    END IF;

    SELECT id INTO white_tshirt_id
    FROM products
    WHERE category_id = tshirts_id AND name = 'Белая базовая футболка'
    LIMIT 1;

    IF white_tshirt_id IS NULL THEN
        INSERT INTO products (category_id, name, price, description, is_active)
        VALUES (
            tshirts_id,
            'Белая базовая футболка',
            1999.00,
            'Хлопковая футболка прямого кроя на каждый день.',
            TRUE
        )
        RETURNING id INTO white_tshirt_id;
    END IF;

    SELECT id INTO black_tshirt_id
    FROM products
    WHERE category_id = tshirts_id AND name = 'Черная футболка oversized'
    LIMIT 1;

    IF black_tshirt_id IS NULL THEN
        INSERT INTO products (category_id, name, price, description, is_active)
        VALUES (
            tshirts_id,
            'Черная футболка oversized',
            2490.00,
            'Свободная футболка из плотного хлопка.',
            TRUE
        )
        RETURNING id INTO black_tshirt_id;
    END IF;

    SELECT id INTO gray_hoodie_id
    FROM products
    WHERE category_id = hoodies_id AND name = 'Серое худи на молнии'
    LIMIT 1;

    IF gray_hoodie_id IS NULL THEN
        INSERT INTO products (category_id, name, price, description, is_active)
        VALUES (
            hoodies_id,
            'Серое худи на молнии',
            4590.00,
            'Теплое худи с начесом и металлической молнией.',
            TRUE
        )
        RETURNING id INTO gray_hoodie_id;
    END IF;

    SELECT id INTO blue_jeans_id
    FROM products
    WHERE category_id = pants_id AND name = 'Синие джинсы regular fit'
    LIMIT 1;

    IF blue_jeans_id IS NULL THEN
        INSERT INTO products (category_id, name, price, description, is_active)
        VALUES (
            pants_id,
            'Синие джинсы regular fit',
            3990.00,
            'Классические джинсы средней посадки на каждый день.',
            TRUE
        )
        RETURNING id INTO blue_jeans_id;
    END IF;

    INSERT INTO product_attributes (product_id, name, value)
    SELECT white_tshirt_id, 'Размер', 'M'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = white_tshirt_id AND name = 'Размер' AND value = 'M'
    );

    INSERT INTO product_attributes (product_id, name, value)
    SELECT white_tshirt_id, 'Материал', '100% хлопок'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = white_tshirt_id AND name = 'Материал' AND value = '100% хлопок'
    );

    INSERT INTO product_attributes (product_id, name, value)
    SELECT black_tshirt_id, 'Размер', 'L'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = black_tshirt_id AND name = 'Размер' AND value = 'L'
    );

    INSERT INTO product_attributes (product_id, name, value)
    SELECT black_tshirt_id, 'Цвет', 'Черный'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = black_tshirt_id AND name = 'Цвет' AND value = 'Черный'
    );

    INSERT INTO product_attributes (product_id, name, value)
    SELECT gray_hoodie_id, 'Размер', 'L'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = gray_hoodie_id AND name = 'Размер' AND value = 'L'
    );

    INSERT INTO product_attributes (product_id, name, value)
    SELECT gray_hoodie_id, 'Материал', 'Хлопок, полиэстер'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = gray_hoodie_id AND name = 'Материал' AND value = 'Хлопок, полиэстер'
    );

    INSERT INTO product_attributes (product_id, name, value)
    SELECT blue_jeans_id, 'Размер', '32'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = blue_jeans_id AND name = 'Размер' AND value = '32'
    );

    INSERT INTO product_attributes (product_id, name, value)
    SELECT blue_jeans_id, 'Цвет', 'Синий'
    WHERE NOT EXISTS (
        SELECT 1
        FROM product_attributes
        WHERE product_id = blue_jeans_id AND name = 'Цвет' AND value = 'Синий'
    );
END $$;
