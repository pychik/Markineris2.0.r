BEGIN;

CREATE TABLE IF NOT EXISTS public.cosmetics (
    id BIGSERIAL PRIMARY KEY,
    type VARCHAR(100),
    article_price DOUBLE PRECISION DEFAULT 0,
    tnved_code VARCHAR(50) DEFAULT '',
    country VARCHAR(58) DEFAULT '',
    tax INTEGER DEFAULT 0,
    trademark VARCHAR(100),
    rd_type VARCHAR(50),
    rd_name VARCHAR(100),
    rd_date DATE,
    rd_date_to DATE,
    subcategory VARCHAR(64) NOT NULL,
    full_name_extra VARCHAR(255) DEFAULT '',
    nominal_quantity INTEGER,
    nominal_quantity_type VARCHAR(20),
    quantity INTEGER,
    blade_count INTEGER,
    complectation VARCHAR(500) NOT NULL DEFAULT '',
    layers_characteristic VARCHAR(50),
    for_children BOOLEAN NOT NULL DEFAULT FALSE,
    usage_term_type VARCHAR(100),
    content_type VARCHAR(20),
    content TEXT,
    service_life INTEGER,
    sl_date_from DATE,
    sl_date_to DATE,
    order_id INTEGER,
    is_approved BOOLEAN NOT NULL DEFAULT FALSE,
    card_id INTEGER
);

ALTER TABLE public.cosmetics
    ADD COLUMN IF NOT EXISTS type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS article_price DOUBLE PRECISION DEFAULT 0,
    ADD COLUMN IF NOT EXISTS tnved_code VARCHAR(50) DEFAULT '',
    ADD COLUMN IF NOT EXISTS country VARCHAR(58) DEFAULT '',
    ADD COLUMN IF NOT EXISTS tax INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS trademark VARCHAR(100),
    ADD COLUMN IF NOT EXISTS rd_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS rd_name VARCHAR(100),
    ADD COLUMN IF NOT EXISTS rd_date DATE,
    ADD COLUMN IF NOT EXISTS rd_date_to DATE,
    ADD COLUMN IF NOT EXISTS subcategory VARCHAR(64),
    ADD COLUMN IF NOT EXISTS full_name_extra VARCHAR(255) DEFAULT '',
    ADD COLUMN IF NOT EXISTS nominal_quantity INTEGER,
    ADD COLUMN IF NOT EXISTS nominal_quantity_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS quantity INTEGER,
    ADD COLUMN IF NOT EXISTS blade_count INTEGER,
    ADD COLUMN IF NOT EXISTS complectation VARCHAR(500) DEFAULT '',
    ADD COLUMN IF NOT EXISTS layers_characteristic VARCHAR(50),
    ADD COLUMN IF NOT EXISTS for_children BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS usage_term_type VARCHAR(100),
    ADD COLUMN IF NOT EXISTS content_type VARCHAR(20),
    ADD COLUMN IF NOT EXISTS content TEXT,
    ADD COLUMN IF NOT EXISTS service_life INTEGER,
    ADD COLUMN IF NOT EXISTS sl_date_from DATE,
    ADD COLUMN IF NOT EXISTS sl_date_to DATE,
    ADD COLUMN IF NOT EXISTS order_id INTEGER,
    ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS card_id INTEGER;

ALTER TABLE public.cosmetics
    ALTER COLUMN subcategory SET NOT NULL,
    ALTER COLUMN complectation SET DEFAULT '',
    ALTER COLUMN complectation SET NOT NULL,
    ALTER COLUMN for_children SET DEFAULT FALSE,
    ALTER COLUMN for_children SET NOT NULL,
    ALTER COLUMN is_approved SET DEFAULT FALSE,
    ALTER COLUMN is_approved SET NOT NULL;

CREATE INDEX IF NOT EXISTS ix_cosmetics_subcategory ON public.cosmetics (subcategory);
CREATE INDEX IF NOT EXISTS ix_cosmetics_order_id ON public.cosmetics (order_id);
CREATE INDEX IF NOT EXISTS ix_cosmetics_card_id ON public.cosmetics (card_id);
CREATE INDEX IF NOT EXISTS ix_cosmetics_rd_date_to ON public.cosmetics (rd_date_to);
CREATE INDEX IF NOT EXISTS ix_cosmetics_sl_date_to ON public.cosmetics (sl_date_to);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_cosmetics_order_id_orders'
    ) THEN
        ALTER TABLE public.cosmetics
            ADD CONSTRAINT fk_cosmetics_order_id_orders
            FOREIGN KEY (order_id)
            REFERENCES public.orders(id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_cosmetics_card_id_product_cards'
    ) THEN
        ALTER TABLE public.cosmetics
            ADD CONSTRAINT fk_cosmetics_card_id_product_cards
            FOREIGN KEY (card_id)
            REFERENCES public.product_cards(id)
            ON DELETE CASCADE;
    END IF;
END
$$;

COMMIT;
