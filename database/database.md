create table public.customers (
  id uuid not null default gen_random_uuid (),
  email text not null,
  full_name text not null,
  phone_number text not null,
  phone_prefix text not null default '+57'::text,
  legal_id text not null,
  legal_id_type text not null,
  created_at timestamp with time zone not null default now(),
  constraint customers_pkey primary key (id)
) TABLESPACE pg_default;

create table public.order_items (
  id uuid not null default gen_random_uuid (),
  order_id uuid not null,
  product_id uuid not null,
  product_name text not null,
  size text not null,
  unit_price_cents integer not null,
  quantity integer not null default 1,
  line_total_cents integer not null,
  constraint order_items_pkey primary key (id),
  constraint order_items_order_id_fkey foreign KEY (order_id) references orders (id) on delete CASCADE,
  constraint order_items_product_id_fkey foreign KEY (product_id) references products (id)
) TABLESPACE pg_default;

create table public.orders (
  id uuid not null default gen_random_uuid (),
  customer_id uuid not null,
  shipping_address_id uuid not null,
  payment_method text not null,
  subtotal_cents integer not null,
  shipping_cents integer not null default 0,
  total_cents integer not null,
  status text not null default 'PENDING'::text,
  created_at timestamp with time zone not null default now(),
  constraint orders_pkey primary key (id),
  constraint orders_customer_id_fkey foreign KEY (customer_id) references customers (id),
  constraint orders_shipping_address_id_fkey foreign KEY (shipping_address_id) references shipping_addresses (id)
) TABLESPACE pg_default;

create table public.product_features (
  id uuid not null default gen_random_uuid (),
  product_id uuid not null,
  title text not null,
  description text not null,
  position integer not null default 0,
  constraint product_features_pkey primary key (id),
  constraint product_features_product_id_fkey foreign KEY (product_id) references products (id) on delete CASCADE
) TABLESPACE pg_default;

create table public.product_images (
  id uuid not null default gen_random_uuid (),
  product_id uuid not null,
  image_url text not null,
  alt_text text null,
  position integer not null default 0,
  constraint product_images_pkey primary key (id),
  constraint product_images_product_id_fkey foreign KEY (product_id) references products (id) on delete CASCADE
) TABLESPACE pg_default;

create table public.products (
  id uuid not null default gen_random_uuid (),
  slug text not null,
  ref text null,
  name text not null,
  description text null,
  price_cents integer not null,
  availability text null,
  image_url text not null,
  alt_text text null,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  sizes jsonb null default '[]'::jsonb,
  categoria text null,
  tipo text null,
  constraint products_pkey primary key (id),
  constraint products_slug_key unique (slug)
) TABLESPACE pg_default;

create table public.shipping_addresses (
  id uuid not null default gen_random_uuid (),
  customer_id uuid not null,
  address_line_1 text not null,
  city text not null,
  region text not null,
  country text not null default 'CO'::text,
  phone_number text not null,
  created_at timestamp with time zone not null default now(),
  constraint shipping_addresses_pkey primary key (id),
  constraint shipping_addresses_customer_id_fkey foreign KEY (customer_id) references customers (id) on delete CASCADE
) TABLESPACE pg_default;