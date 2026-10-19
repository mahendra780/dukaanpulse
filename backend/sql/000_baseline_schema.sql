--
-- PostgreSQL database dump
--

\restrict tKkqlg6NJA5OcHgFGIHEIOsBpH6geoYGVe3hgXwibB83RYA1FCa0ZmdtUfak9P0

-- Dumped from database version 18.6 (653b019)
-- Dumped by pg_dump version 18.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: categories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categories (
    category_id bigint NOT NULL,
    category_name character varying(100) NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_category_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: categories_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.categories ALTER COLUMN category_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.categories_category_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: customers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.customers (
    customer_id bigint NOT NULL,
    customer_name character varying(150) NOT NULL,
    phone character varying(20),
    address text NOT NULL,
    area character varying(100) NOT NULL,
    credit_limit numeric(12,2) DEFAULT 0 NOT NULL,
    payment_terms_days integer DEFAULT 0 NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    credit_balance numeric(14,2) DEFAULT 0 NOT NULL,
    CONSTRAINT chk_customer_credit_balance CHECK ((credit_balance >= (0)::numeric)),
    CONSTRAINT chk_customer_credit_limit CHECK ((credit_limit >= (0)::numeric)),
    CONSTRAINT chk_customer_payment_terms CHECK ((payment_terms_days >= 0)),
    CONSTRAINT chk_customer_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: customers_customer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.customers ALTER COLUMN customer_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.customers_customer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: deliveries; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deliveries (
    delivery_id bigint NOT NULL,
    invoice_id bigint NOT NULL,
    delivery_date date,
    status character varying(30) DEFAULT 'PENDING'::character varying NOT NULL,
    delivery_address text NOT NULL,
    vehicle_number character varying(30),
    driver_name character varying(100),
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_delivery_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'DISPATCHED'::character varying, 'OUT_FOR_DELIVERY'::character varying, 'DELIVERED'::character varying, 'FAILED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: deliveries_delivery_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.deliveries ALTER COLUMN delivery_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.deliveries_delivery_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: inventory_movements; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inventory_movements (
    movement_id bigint NOT NULL,
    product_id bigint NOT NULL,
    base_quantity numeric(14,3) NOT NULL,
    movement_type character varying(30) NOT NULL,
    movement_date timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    purchase_item_id bigint,
    invoice_item_id bigint,
    return_item_id bigint,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_inventory_base_quantity CHECK ((base_quantity <> (0)::numeric)),
    CONSTRAINT chk_inventory_movement_type CHECK (((movement_type)::text = ANY ((ARRAY['OPENING'::character varying, 'PURCHASE'::character varying, 'SALE'::character varying, 'RETURN'::character varying, 'DAMAGE'::character varying, 'ADJUSTMENT'::character varying])::text[]))),
    CONSTRAINT chk_inventory_reference CHECK (((((movement_type)::text = 'PURCHASE'::text) AND (purchase_item_id IS NOT NULL) AND (invoice_item_id IS NULL) AND (return_item_id IS NULL) AND (base_quantity > (0)::numeric)) OR (((movement_type)::text = 'SALE'::text) AND (invoice_item_id IS NOT NULL) AND (purchase_item_id IS NULL) AND (return_item_id IS NULL) AND (base_quantity < (0)::numeric)) OR (((movement_type)::text = 'RETURN'::text) AND (return_item_id IS NOT NULL) AND (purchase_item_id IS NULL) AND (invoice_item_id IS NULL) AND (base_quantity > (0)::numeric)) OR (((movement_type)::text = 'DAMAGE'::text) AND (purchase_item_id IS NULL) AND (invoice_item_id IS NULL) AND (return_item_id IS NULL) AND (base_quantity < (0)::numeric)) OR (((movement_type)::text = 'OPENING'::text) AND (purchase_item_id IS NULL) AND (invoice_item_id IS NULL) AND (return_item_id IS NULL)) OR (((movement_type)::text = 'ADJUSTMENT'::text) AND (purchase_item_id IS NULL) AND (invoice_item_id IS NULL) AND (return_item_id IS NULL))))
);


--
-- Name: inventory_movements_movement_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.inventory_movements ALTER COLUMN movement_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.inventory_movements_movement_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: invoice_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_items (
    invoice_item_id bigint NOT NULL,
    invoice_id bigint NOT NULL,
    product_id bigint NOT NULL,
    packaging_id bigint NOT NULL,
    quantity numeric(12,3) NOT NULL,
    unit_price numeric(14,2) NOT NULL,
    discount numeric(14,2) DEFAULT 0 NOT NULL,
    tax numeric(14,2) DEFAULT 0 NOT NULL,
    line_total numeric(14,2) NOT NULL,
    CONSTRAINT chk_invoice_item_discount CHECK ((discount >= (0)::numeric)),
    CONSTRAINT chk_invoice_item_quantity CHECK ((quantity > (0)::numeric)),
    CONSTRAINT chk_invoice_item_tax CHECK ((tax >= (0)::numeric)),
    CONSTRAINT chk_invoice_line_total CHECK ((line_total >= (0)::numeric)),
    CONSTRAINT chk_invoice_unit_price CHECK ((unit_price >= (0)::numeric))
);


--
-- Name: invoice_items_invoice_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.invoice_items ALTER COLUMN invoice_item_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.invoice_items_invoice_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoices (
    invoice_id bigint NOT NULL,
    order_id bigint NOT NULL,
    invoice_number character varying(100) NOT NULL,
    invoice_date date NOT NULL,
    subtotal numeric(14,2) DEFAULT 0 NOT NULL,
    discount numeric(14,2) DEFAULT 0 NOT NULL,
    tax numeric(14,2) DEFAULT 0 NOT NULL,
    total_amount numeric(14,2) DEFAULT 0 NOT NULL,
    status character varying(30) DEFAULT 'UNPAID'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_invoice_discount CHECK ((discount >= (0)::numeric)),
    CONSTRAINT chk_invoice_status CHECK (((status)::text = ANY ((ARRAY['UNPAID'::character varying, 'PARTIALLY_PAID'::character varying, 'PAID'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT chk_invoice_subtotal CHECK ((subtotal >= (0)::numeric)),
    CONSTRAINT chk_invoice_tax CHECK ((tax >= (0)::numeric)),
    CONSTRAINT chk_invoice_total CHECK ((total_amount >= (0)::numeric))
);


--
-- Name: invoices_invoice_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.invoices ALTER COLUMN invoice_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.invoices_invoice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.order_items (
    order_item_id bigint NOT NULL,
    order_id bigint NOT NULL,
    product_id bigint NOT NULL,
    packaging_id bigint NOT NULL,
    quantity numeric(12,3) NOT NULL,
    CONSTRAINT chk_order_item_quantity CHECK ((quantity > (0)::numeric))
);


--
-- Name: order_items_order_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.order_items ALTER COLUMN order_item_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.order_items_order_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: orders; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.orders (
    order_id bigint NOT NULL,
    customer_id bigint NOT NULL,
    order_date date NOT NULL,
    status character varying(30) DEFAULT 'PENDING'::character varying NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_order_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'CONFIRMED'::character varying, 'PARTIALLY_FULFILLED'::character varying, 'COMPLETED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: orders_order_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.orders ALTER COLUMN order_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.orders_order_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    payment_id bigint NOT NULL,
    invoice_id bigint NOT NULL,
    payment_date date NOT NULL,
    amount numeric(14,2) NOT NULL,
    payment_method character varying(30) NOT NULL,
    reference_number character varying(100),
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_payment_amount CHECK ((amount > (0)::numeric)),
    CONSTRAINT chk_payment_method CHECK (((payment_method)::text = ANY ((ARRAY['CASH'::character varying, 'UPI'::character varying, 'BANK_TRANSFER'::character varying, 'CHEQUE'::character varying, 'RETURN_CREDIT'::character varying, 'CREDIT_APPLIED'::character varying])::text[])))
);


--
-- Name: payments_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.payments ALTER COLUMN payment_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.payments_payment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: product_packaging; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.product_packaging (
    packaging_id bigint NOT NULL,
    product_id bigint NOT NULL,
    unit_name character varying(50) NOT NULL,
    conversion_to_base numeric(12,4) NOT NULL,
    is_base_unit boolean DEFAULT false NOT NULL,
    is_purchase_unit boolean DEFAULT false NOT NULL,
    is_sale_unit boolean DEFAULT false NOT NULL,
    CONSTRAINT chk_conversion CHECK ((conversion_to_base > (0)::numeric))
);


--
-- Name: product_packaging_packaging_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.product_packaging ALTER COLUMN packaging_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.product_packaging_packaging_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    product_id bigint NOT NULL,
    product_name character varying(200) NOT NULL,
    category_id bigint NOT NULL,
    brand_name character varying(100),
    sku character varying(50) NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_product_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: products_product_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.products ALTER COLUMN product_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.products_product_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: purchase_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchase_items (
    purchase_item_id bigint NOT NULL,
    purchase_id bigint NOT NULL,
    product_id bigint NOT NULL,
    packaging_id bigint NOT NULL,
    quantity numeric(12,3) NOT NULL,
    received_quantity numeric(12,3) DEFAULT 0 NOT NULL,
    unit_price numeric(14,2) NOT NULL,
    discount numeric(14,2) DEFAULT 0 NOT NULL,
    tax numeric(14,2) DEFAULT 0 NOT NULL,
    line_total numeric(14,2) NOT NULL,
    CONSTRAINT chk_purchase_item_discount CHECK ((discount >= (0)::numeric)),
    CONSTRAINT chk_purchase_item_tax CHECK ((tax >= (0)::numeric)),
    CONSTRAINT chk_purchase_line_total CHECK ((line_total >= (0)::numeric)),
    CONSTRAINT chk_purchase_quantity CHECK ((quantity > (0)::numeric)),
    CONSTRAINT chk_purchase_unit_price CHECK ((unit_price >= (0)::numeric)),
    CONSTRAINT chk_received_quantity CHECK (((received_quantity >= (0)::numeric) AND (received_quantity <= quantity)))
);


--
-- Name: purchase_items_purchase_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.purchase_items ALTER COLUMN purchase_item_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.purchase_items_purchase_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: purchase_payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchase_payments (
    purchase_payment_id bigint NOT NULL,
    purchase_id bigint NOT NULL,
    payment_date date NOT NULL,
    amount numeric(14,2) NOT NULL,
    payment_method character varying(30) NOT NULL,
    reference_number character varying(100),
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_purchase_payment_amount CHECK ((amount > (0)::numeric)),
    CONSTRAINT chk_purchase_payment_method CHECK (((payment_method)::text = ANY ((ARRAY['CASH'::character varying, 'UPI'::character varying, 'BANK_TRANSFER'::character varying, 'CHEQUE'::character varying])::text[])))
);


--
-- Name: purchase_payments_purchase_payment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.purchase_payments_purchase_payment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: purchase_payments_purchase_payment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.purchase_payments_purchase_payment_id_seq OWNED BY public.purchase_payments.purchase_payment_id;


--
-- Name: purchases; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.purchases (
    purchase_id bigint NOT NULL,
    supplier_id bigint NOT NULL,
    purchase_date date NOT NULL,
    supplier_invoice_no character varying(100) NOT NULL,
    subtotal numeric(14,2) DEFAULT 0 NOT NULL,
    discount numeric(14,2) DEFAULT 0 NOT NULL,
    tax numeric(14,2) DEFAULT 0 NOT NULL,
    total_amount numeric(14,2) DEFAULT 0 NOT NULL,
    status character varying(30) DEFAULT 'PENDING'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_purchase_discount CHECK ((discount >= (0)::numeric)),
    CONSTRAINT chk_purchase_status CHECK (((status)::text = ANY ((ARRAY['PENDING'::character varying, 'RECEIVED'::character varying, 'PARTIALLY_RECEIVED'::character varying, 'CANCELLED'::character varying])::text[]))),
    CONSTRAINT chk_purchase_subtotal CHECK ((subtotal >= (0)::numeric)),
    CONSTRAINT chk_purchase_tax CHECK ((tax >= (0)::numeric)),
    CONSTRAINT chk_purchase_total CHECK ((total_amount >= (0)::numeric))
);


--
-- Name: purchases_purchase_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.purchases ALTER COLUMN purchase_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.purchases_purchase_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: return_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.return_items (
    return_item_id bigint NOT NULL,
    return_id bigint NOT NULL,
    product_id bigint NOT NULL,
    packaging_id bigint NOT NULL,
    quantity numeric(12,3) NOT NULL,
    condition character varying(30) NOT NULL,
    CONSTRAINT chk_return_condition CHECK (((condition)::text = ANY ((ARRAY['RESELLABLE'::character varying, 'DAMAGED'::character varying, 'EXPIRED'::character varying, 'SUPPLIER_RETURN'::character varying])::text[]))),
    CONSTRAINT chk_return_quantity CHECK ((quantity > (0)::numeric))
);


--
-- Name: return_items_return_item_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.return_items ALTER COLUMN return_item_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.return_items_return_item_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: returns; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.returns (
    return_id bigint NOT NULL,
    invoice_id bigint NOT NULL,
    return_date date NOT NULL,
    reason character varying(30) NOT NULL,
    status character varying(30) DEFAULT 'REQUESTED'::character varying NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_return_reason CHECK (((reason)::text = ANY ((ARRAY['DAMAGED'::character varying, 'EXPIRED'::character varying, 'WRONG_PRODUCT'::character varying, 'QUALITY_ISSUE'::character varying, 'EXCESS_QUANTITY'::character varying, 'OTHER'::character varying])::text[]))),
    CONSTRAINT chk_return_status CHECK (((status)::text = ANY ((ARRAY['REQUESTED'::character varying, 'APPROVED'::character varying, 'RECEIVED'::character varying, 'REJECTED'::character varying, 'CANCELLED'::character varying])::text[])))
);


--
-- Name: returns_return_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.returns ALTER COLUMN return_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.returns_return_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: suppliers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.suppliers (
    supplier_id bigint NOT NULL,
    supplier_name character varying(150) NOT NULL,
    phone character varying(20),
    address text NOT NULL,
    gst_number character varying(15),
    payment_terms_days integer DEFAULT 0 NOT NULL,
    status character varying(20) DEFAULT 'ACTIVE'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_supplier_gst CHECK (((gst_number IS NULL) OR ((gst_number)::text ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'::text))),
    CONSTRAINT chk_supplier_payment_terms CHECK ((payment_terms_days >= 0)),
    CONSTRAINT chk_supplier_status CHECK (((status)::text = ANY ((ARRAY['ACTIVE'::character varying, 'INACTIVE'::character varying])::text[])))
);


--
-- Name: suppliers_supplier_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.suppliers ALTER COLUMN supplier_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.suppliers_supplier_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: purchase_payments purchase_payment_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_payments ALTER COLUMN purchase_payment_id SET DEFAULT nextval('public.purchase_payments_purchase_payment_id_seq'::regclass);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (category_id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (customer_id);


--
-- Name: deliveries deliveries_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deliveries
    ADD CONSTRAINT deliveries_pkey PRIMARY KEY (delivery_id);


--
-- Name: inventory_movements inventory_movements_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_movements
    ADD CONSTRAINT inventory_movements_pkey PRIMARY KEY (movement_id);


--
-- Name: invoice_items invoice_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT invoice_items_pkey PRIMARY KEY (invoice_item_id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (invoice_id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (order_item_id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (payment_id);


--
-- Name: product_packaging product_packaging_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_packaging
    ADD CONSTRAINT product_packaging_pkey PRIMARY KEY (packaging_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_id);


--
-- Name: purchase_items purchase_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_items
    ADD CONSTRAINT purchase_items_pkey PRIMARY KEY (purchase_item_id);


--
-- Name: purchase_payments purchase_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_payments
    ADD CONSTRAINT purchase_payments_pkey PRIMARY KEY (purchase_payment_id);


--
-- Name: purchases purchases_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchases
    ADD CONSTRAINT purchases_pkey PRIMARY KEY (purchase_id);


--
-- Name: return_items return_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT return_items_pkey PRIMARY KEY (return_item_id);


--
-- Name: returns returns_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.returns
    ADD CONSTRAINT returns_pkey PRIMARY KEY (return_id);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (supplier_id);


--
-- Name: categories uq_category_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT uq_category_name UNIQUE (category_name);


--
-- Name: invoices uq_invoice_number; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT uq_invoice_number UNIQUE (invoice_number);


--
-- Name: product_packaging uq_packaging_product_pair; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_packaging
    ADD CONSTRAINT uq_packaging_product_pair UNIQUE (packaging_id, product_id);


--
-- Name: payments uq_payment_reference; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT uq_payment_reference UNIQUE (reference_number);


--
-- Name: products uq_product_sku; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT uq_product_sku UNIQUE (sku);


--
-- Name: product_packaging uq_product_unit; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_packaging
    ADD CONSTRAINT uq_product_unit UNIQUE (product_id, unit_name);


--
-- Name: suppliers uq_supplier_gst; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT uq_supplier_gst UNIQUE (gst_number);


--
-- Name: purchases uq_supplier_invoice; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchases
    ADD CONSTRAINT uq_supplier_invoice UNIQUE (supplier_id, supplier_invoice_no);


--
-- Name: idx_deliveries_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_deliveries_status ON public.deliveries USING btree (status);


--
-- Name: idx_inventory_product_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inventory_product_date ON public.inventory_movements USING btree (product_id, movement_date);


--
-- Name: idx_invoice_items_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_items_invoice ON public.invoice_items USING btree (invoice_id);


--
-- Name: idx_invoice_items_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_items_product ON public.invoice_items USING btree (product_id);


--
-- Name: idx_invoices_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_date ON public.invoices USING btree (invoice_date);


--
-- Name: idx_invoices_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_order ON public.invoices USING btree (order_id);


--
-- Name: idx_order_items_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_items_order ON public.order_items USING btree (order_id);


--
-- Name: idx_order_items_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_order_items_product ON public.order_items USING btree (product_id);


--
-- Name: idx_orders_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_customer ON public.orders USING btree (customer_id);


--
-- Name: idx_orders_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_orders_date ON public.orders USING btree (order_date);


--
-- Name: idx_packaging_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_packaging_product ON public.product_packaging USING btree (product_id);


--
-- Name: idx_payments_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_date ON public.payments USING btree (payment_date);


--
-- Name: idx_payments_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_invoice ON public.payments USING btree (invoice_id);


--
-- Name: idx_products_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_products_category ON public.products USING btree (category_id);


--
-- Name: idx_purchase_items_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_purchase_items_product ON public.purchase_items USING btree (product_id);


--
-- Name: idx_purchase_items_purchase; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_purchase_items_purchase ON public.purchase_items USING btree (purchase_id);


--
-- Name: idx_purchases_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_purchases_date ON public.purchases USING btree (purchase_date);


--
-- Name: idx_purchases_supplier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_purchases_supplier ON public.purchases USING btree (supplier_id);


--
-- Name: idx_return_items_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_return_items_product ON public.return_items USING btree (product_id);


--
-- Name: idx_return_items_return; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_return_items_return ON public.return_items USING btree (return_id);


--
-- Name: idx_returns_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_returns_date ON public.returns USING btree (return_date);


--
-- Name: idx_returns_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_returns_invoice ON public.returns USING btree (invoice_id);


--
-- Name: uq_delivery_invoice_active; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_delivery_invoice_active ON public.deliveries USING btree (invoice_id) WHERE ((status)::text <> 'CANCELLED'::text);


--
-- Name: uq_one_base_unit_per_product; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_one_base_unit_per_product ON public.product_packaging USING btree (product_id) WHERE (is_base_unit = true);


--
-- Name: deliveries fk_delivery_invoice; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deliveries
    ADD CONSTRAINT fk_delivery_invoice FOREIGN KEY (invoice_id) REFERENCES public.invoices(invoice_id);


--
-- Name: inventory_movements fk_inventory_invoice_item; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_movements
    ADD CONSTRAINT fk_inventory_invoice_item FOREIGN KEY (invoice_item_id) REFERENCES public.invoice_items(invoice_item_id);


--
-- Name: inventory_movements fk_inventory_product; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_movements
    ADD CONSTRAINT fk_inventory_product FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- Name: inventory_movements fk_inventory_purchase_item; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_movements
    ADD CONSTRAINT fk_inventory_purchase_item FOREIGN KEY (purchase_item_id) REFERENCES public.purchase_items(purchase_item_id);


--
-- Name: inventory_movements fk_inventory_return_item; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inventory_movements
    ADD CONSTRAINT fk_inventory_return_item FOREIGN KEY (return_item_id) REFERENCES public.return_items(return_item_id);


--
-- Name: invoice_items fk_invoice_item_invoice; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT fk_invoice_item_invoice FOREIGN KEY (invoice_id) REFERENCES public.invoices(invoice_id) ON DELETE CASCADE;


--
-- Name: invoice_items fk_invoice_item_packaging; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT fk_invoice_item_packaging FOREIGN KEY (packaging_id, product_id) REFERENCES public.product_packaging(packaging_id, product_id);


--
-- Name: invoice_items fk_invoice_item_product; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_items
    ADD CONSTRAINT fk_invoice_item_product FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- Name: invoices fk_invoice_order; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT fk_invoice_order FOREIGN KEY (order_id) REFERENCES public.orders(order_id);


--
-- Name: orders fk_order_customer; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT fk_order_customer FOREIGN KEY (customer_id) REFERENCES public.customers(customer_id);


--
-- Name: order_items fk_order_item_order; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_item_order FOREIGN KEY (order_id) REFERENCES public.orders(order_id) ON DELETE CASCADE;


--
-- Name: order_items fk_order_item_packaging; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_item_packaging FOREIGN KEY (packaging_id, product_id) REFERENCES public.product_packaging(packaging_id, product_id);


--
-- Name: order_items fk_order_item_product; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT fk_order_item_product FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- Name: product_packaging fk_packaging_product; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.product_packaging
    ADD CONSTRAINT fk_packaging_product FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- Name: payments fk_payment_invoice; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT fk_payment_invoice FOREIGN KEY (invoice_id) REFERENCES public.invoices(invoice_id);


--
-- Name: products fk_product_category; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES public.categories(category_id);


--
-- Name: purchase_items fk_purchase_item_packaging; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_items
    ADD CONSTRAINT fk_purchase_item_packaging FOREIGN KEY (packaging_id, product_id) REFERENCES public.product_packaging(packaging_id, product_id);


--
-- Name: purchase_items fk_purchase_item_product; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_items
    ADD CONSTRAINT fk_purchase_item_product FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- Name: purchase_items fk_purchase_item_purchase; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_items
    ADD CONSTRAINT fk_purchase_item_purchase FOREIGN KEY (purchase_id) REFERENCES public.purchases(purchase_id) ON DELETE CASCADE;


--
-- Name: purchases fk_purchase_supplier; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchases
    ADD CONSTRAINT fk_purchase_supplier FOREIGN KEY (supplier_id) REFERENCES public.suppliers(supplier_id);


--
-- Name: returns fk_return_invoice; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.returns
    ADD CONSTRAINT fk_return_invoice FOREIGN KEY (invoice_id) REFERENCES public.invoices(invoice_id);


--
-- Name: return_items fk_return_item_packaging; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT fk_return_item_packaging FOREIGN KEY (packaging_id, product_id) REFERENCES public.product_packaging(packaging_id, product_id);


--
-- Name: return_items fk_return_item_product; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT fk_return_item_product FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- Name: return_items fk_return_item_return; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.return_items
    ADD CONSTRAINT fk_return_item_return FOREIGN KEY (return_id) REFERENCES public.returns(return_id) ON DELETE CASCADE;


--
-- Name: purchase_payments purchase_payments_purchase_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.purchase_payments
    ADD CONSTRAINT purchase_payments_purchase_id_fkey FOREIGN KEY (purchase_id) REFERENCES public.purchases(purchase_id);


--
-- PostgreSQL database dump complete
--

\unrestrict tKkqlg6NJA5OcHgFGIHEIOsBpH6geoYGVe3hgXwibB83RYA1FCa0ZmdtUfak9P0

