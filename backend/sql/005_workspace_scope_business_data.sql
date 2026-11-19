-- DukaanPulse database-enforced workspace ownership for every business row.
-- Prerequisites: run 004_auth_workspace_foundation.sql first, after 001-003.
-- Safety: this migration FAILS if business data exists. It does not delete,
-- truncate, or overwrite records. The global business-identifier constraints
-- listed below are replaced with workspace-scoped versions; the empty-table
-- precondition makes that narrow compatibility correction safe.
-- Rollback/recovery: take a schema backup first. Do not remove constraints or
-- columns without a separately reviewed rollback plan.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM categories LIMIT 1)
       OR EXISTS (SELECT 1 FROM products LIMIT 1)
       OR EXISTS (SELECT 1 FROM product_packaging LIMIT 1)
       OR EXISTS (SELECT 1 FROM customers LIMIT 1)
       OR EXISTS (SELECT 1 FROM suppliers LIMIT 1)
       OR EXISTS (SELECT 1 FROM purchases LIMIT 1)
       OR EXISTS (SELECT 1 FROM purchase_items LIMIT 1)
       OR EXISTS (SELECT 1 FROM purchase_payments LIMIT 1)
       OR EXISTS (SELECT 1 FROM orders LIMIT 1)
       OR EXISTS (SELECT 1 FROM order_items LIMIT 1)
       OR EXISTS (SELECT 1 FROM invoices LIMIT 1)
       OR EXISTS (SELECT 1 FROM invoice_items LIMIT 1)
       OR EXISTS (SELECT 1 FROM deliveries LIMIT 1)
       OR EXISTS (SELECT 1 FROM payments LIMIT 1)
       OR EXISTS (SELECT 1 FROM returns LIMIT 1)
       OR EXISTS (SELECT 1 FROM return_items LIMIT 1)
       OR EXISTS (SELECT 1 FROM inventory_movements LIMIT 1) THEN
        RAISE EXCEPTION
            '005_workspace_scope_business_data requires empty business tables; no data was changed.';
    END IF;
END $$;

ALTER TABLE categories ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE products ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE product_packaging ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE customers ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE suppliers ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE purchases ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE purchase_items ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE purchase_payments ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE orders ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE order_items ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE invoices ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE invoice_items ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE deliveries ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE payments ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE returns ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE return_items ADD COLUMN workspace_id BIGINT NOT NULL;
ALTER TABLE inventory_movements ADD COLUMN workspace_id BIGINT NOT NULL;

ALTER TABLE categories DROP CONSTRAINT uq_category_name;
ALTER TABLE products DROP CONSTRAINT uq_product_sku;
ALTER TABLE suppliers DROP CONSTRAINT uq_supplier_gst;
ALTER TABLE invoices DROP CONSTRAINT uq_invoice_number;
ALTER TABLE payments DROP CONSTRAINT uq_payment_reference;

ALTER TABLE categories ADD CONSTRAINT uq_categories_workspace_name UNIQUE (workspace_id, category_name);
ALTER TABLE products ADD CONSTRAINT uq_products_workspace_sku UNIQUE (workspace_id, sku);
ALTER TABLE suppliers ADD CONSTRAINT uq_suppliers_workspace_gst UNIQUE (workspace_id, gst_number);
ALTER TABLE invoices ADD CONSTRAINT uq_invoices_workspace_number UNIQUE (workspace_id, invoice_number);
ALTER TABLE payments ADD CONSTRAINT uq_payments_workspace_reference UNIQUE (workspace_id, reference_number);

ALTER TABLE categories ADD CONSTRAINT fk_categories_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE products ADD CONSTRAINT fk_products_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE product_packaging ADD CONSTRAINT fk_product_packaging_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE customers ADD CONSTRAINT fk_customers_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE suppliers ADD CONSTRAINT fk_suppliers_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE purchases ADD CONSTRAINT fk_purchases_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE purchase_items ADD CONSTRAINT fk_purchase_items_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE purchase_payments ADD CONSTRAINT fk_purchase_payments_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE orders ADD CONSTRAINT fk_orders_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE order_items ADD CONSTRAINT fk_order_items_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE invoices ADD CONSTRAINT fk_invoices_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE invoice_items ADD CONSTRAINT fk_invoice_items_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE deliveries ADD CONSTRAINT fk_deliveries_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE payments ADD CONSTRAINT fk_payments_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE returns ADD CONSTRAINT fk_returns_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE return_items ADD CONSTRAINT fk_return_items_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);
ALTER TABLE inventory_movements ADD CONSTRAINT fk_inventory_movements_workspace FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id);

ALTER TABLE categories ADD CONSTRAINT uq_categories_workspace_id UNIQUE (workspace_id, category_id);
ALTER TABLE products ADD CONSTRAINT uq_products_workspace_id UNIQUE (workspace_id, product_id);
ALTER TABLE product_packaging ADD CONSTRAINT uq_packaging_workspace_product_id UNIQUE (workspace_id, packaging_id, product_id);
ALTER TABLE customers ADD CONSTRAINT uq_customers_workspace_id UNIQUE (workspace_id, customer_id);
ALTER TABLE suppliers ADD CONSTRAINT uq_suppliers_workspace_id UNIQUE (workspace_id, supplier_id);
ALTER TABLE purchases ADD CONSTRAINT uq_purchases_workspace_id UNIQUE (workspace_id, purchase_id);
ALTER TABLE purchase_items ADD CONSTRAINT uq_purchase_items_workspace_id UNIQUE (workspace_id, purchase_item_id);
ALTER TABLE purchase_payments ADD CONSTRAINT uq_purchase_payments_workspace_id UNIQUE (workspace_id, purchase_payment_id);
ALTER TABLE orders ADD CONSTRAINT uq_orders_workspace_id UNIQUE (workspace_id, order_id);
ALTER TABLE order_items ADD CONSTRAINT uq_order_items_workspace_id UNIQUE (workspace_id, order_item_id);
ALTER TABLE invoices ADD CONSTRAINT uq_invoices_workspace_id UNIQUE (workspace_id, invoice_id);
ALTER TABLE invoice_items ADD CONSTRAINT uq_invoice_items_workspace_id UNIQUE (workspace_id, invoice_item_id);
ALTER TABLE deliveries ADD CONSTRAINT uq_deliveries_workspace_id UNIQUE (workspace_id, delivery_id);
ALTER TABLE payments ADD CONSTRAINT uq_payments_workspace_id UNIQUE (workspace_id, payment_id);
ALTER TABLE returns ADD CONSTRAINT uq_returns_workspace_id UNIQUE (workspace_id, return_id);
ALTER TABLE return_items ADD CONSTRAINT uq_return_items_workspace_id UNIQUE (workspace_id, return_item_id);

ALTER TABLE products ADD CONSTRAINT fk_products_workspace_category
    FOREIGN KEY (workspace_id, category_id) REFERENCES categories(workspace_id, category_id);
ALTER TABLE product_packaging ADD CONSTRAINT fk_packaging_workspace_product
    FOREIGN KEY (workspace_id, product_id) REFERENCES products(workspace_id, product_id);
ALTER TABLE purchases ADD CONSTRAINT fk_purchases_workspace_supplier
    FOREIGN KEY (workspace_id, supplier_id) REFERENCES suppliers(workspace_id, supplier_id);
ALTER TABLE purchase_items ADD CONSTRAINT fk_purchase_items_workspace_purchase
    FOREIGN KEY (workspace_id, purchase_id) REFERENCES purchases(workspace_id, purchase_id);
ALTER TABLE purchase_items ADD CONSTRAINT fk_purchase_items_workspace_product
    FOREIGN KEY (workspace_id, product_id) REFERENCES products(workspace_id, product_id);
ALTER TABLE purchase_items ADD CONSTRAINT fk_purchase_items_workspace_packaging
    FOREIGN KEY (workspace_id, packaging_id, product_id)
    REFERENCES product_packaging(workspace_id, packaging_id, product_id);
ALTER TABLE purchase_payments ADD CONSTRAINT fk_purchase_payments_workspace_purchase
    FOREIGN KEY (workspace_id, purchase_id) REFERENCES purchases(workspace_id, purchase_id);
ALTER TABLE orders ADD CONSTRAINT fk_orders_workspace_customer
    FOREIGN KEY (workspace_id, customer_id) REFERENCES customers(workspace_id, customer_id);
ALTER TABLE order_items ADD CONSTRAINT fk_order_items_workspace_order
    FOREIGN KEY (workspace_id, order_id) REFERENCES orders(workspace_id, order_id);
ALTER TABLE order_items ADD CONSTRAINT fk_order_items_workspace_product
    FOREIGN KEY (workspace_id, product_id) REFERENCES products(workspace_id, product_id);
ALTER TABLE order_items ADD CONSTRAINT fk_order_items_workspace_packaging
    FOREIGN KEY (workspace_id, packaging_id, product_id)
    REFERENCES product_packaging(workspace_id, packaging_id, product_id);
ALTER TABLE invoices ADD CONSTRAINT fk_invoices_workspace_order
    FOREIGN KEY (workspace_id, order_id) REFERENCES orders(workspace_id, order_id);
ALTER TABLE invoice_items ADD CONSTRAINT fk_invoice_items_workspace_invoice
    FOREIGN KEY (workspace_id, invoice_id) REFERENCES invoices(workspace_id, invoice_id);
ALTER TABLE invoice_items ADD CONSTRAINT fk_invoice_items_workspace_product
    FOREIGN KEY (workspace_id, product_id) REFERENCES products(workspace_id, product_id);
ALTER TABLE invoice_items ADD CONSTRAINT fk_invoice_items_workspace_packaging
    FOREIGN KEY (workspace_id, packaging_id, product_id)
    REFERENCES product_packaging(workspace_id, packaging_id, product_id);
ALTER TABLE deliveries ADD CONSTRAINT fk_deliveries_workspace_invoice
    FOREIGN KEY (workspace_id, invoice_id) REFERENCES invoices(workspace_id, invoice_id);
ALTER TABLE payments ADD CONSTRAINT fk_payments_workspace_invoice
    FOREIGN KEY (workspace_id, invoice_id) REFERENCES invoices(workspace_id, invoice_id);
ALTER TABLE returns ADD CONSTRAINT fk_returns_workspace_invoice
    FOREIGN KEY (workspace_id, invoice_id) REFERENCES invoices(workspace_id, invoice_id);
ALTER TABLE return_items ADD CONSTRAINT fk_return_items_workspace_return
    FOREIGN KEY (workspace_id, return_id) REFERENCES returns(workspace_id, return_id);
ALTER TABLE return_items ADD CONSTRAINT fk_return_items_workspace_product
    FOREIGN KEY (workspace_id, product_id) REFERENCES products(workspace_id, product_id);
ALTER TABLE return_items ADD CONSTRAINT fk_return_items_workspace_packaging
    FOREIGN KEY (workspace_id, packaging_id, product_id)
    REFERENCES product_packaging(workspace_id, packaging_id, product_id);
ALTER TABLE inventory_movements ADD CONSTRAINT fk_inventory_workspace_product
    FOREIGN KEY (workspace_id, product_id) REFERENCES products(workspace_id, product_id);
ALTER TABLE inventory_movements ADD CONSTRAINT fk_inventory_workspace_purchase_item
    FOREIGN KEY (workspace_id, purchase_item_id) REFERENCES purchase_items(workspace_id, purchase_item_id);
ALTER TABLE inventory_movements ADD CONSTRAINT fk_inventory_workspace_invoice_item
    FOREIGN KEY (workspace_id, invoice_item_id) REFERENCES invoice_items(workspace_id, invoice_item_id);
ALTER TABLE inventory_movements ADD CONSTRAINT fk_inventory_workspace_return_item
    FOREIGN KEY (workspace_id, return_item_id) REFERENCES return_items(workspace_id, return_item_id);

CREATE INDEX idx_categories_workspace ON categories(workspace_id);
CREATE INDEX idx_products_workspace ON products(workspace_id);
CREATE INDEX idx_customers_workspace ON customers(workspace_id);
CREATE INDEX idx_suppliers_workspace ON suppliers(workspace_id);
CREATE INDEX idx_purchases_workspace ON purchases(workspace_id);
CREATE INDEX idx_orders_workspace ON orders(workspace_id);
CREATE INDEX idx_invoices_workspace ON invoices(workspace_id);
CREATE INDEX idx_payments_workspace ON payments(workspace_id);
CREATE INDEX idx_inventory_movements_workspace ON inventory_movements(workspace_id);
