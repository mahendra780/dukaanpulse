"""Bulk database loaders for Cash & Credit Intelligence reports.

The calculation core accepts only the plain dataclasses defined in
``models.py``.  This module is the deliberately small boundary that converts
database rows into those values.  It performs a fixed six queries regardless
of customer count: customers, invoices, customer payments, suppliers,
purchases, and supplier payments.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.order import Order
from app.models.payment import Payment
from app.models.purchase import Purchase
from app.models.purchase_payment import PurchasePayment
from app.models.supplier import Supplier
from app.services.analytics.models import (
    CustomerInput,
    InvoiceInput,
    PaymentInput,
    PurchaseInput,
    SupplierInput,
    SupplierPaymentInput,
)


@dataclass(frozen=True)
class AnalyticsInputs:
    """All plain rows required by the three reports."""

    customers: tuple[CustomerInput, ...]
    invoices: tuple[InvoiceInput, ...]
    payments: tuple[PaymentInput, ...]
    suppliers: tuple[SupplierInput, ...]
    purchases: tuple[PurchaseInput, ...]
    supplier_payments: tuple[SupplierPaymentInput, ...]


def load_report_inputs(db: Session) -> AnalyticsInputs:
    """Load all report inputs with a fixed number of bulk queries.

    ``payment_method`` is intentionally selected for every customer payment:
    the calculation core must distinguish real payments from RETURN_CREDIT and
    CREDIT_APPLIED rows.  Do not replace these queries with per-customer
    relationship loads; that would make report cost grow with customer count.
    """
    customer_rows = db.execute(
        select(
            Customer.customer_id,
            Customer.customer_name,
            Customer.credit_limit,
            Customer.credit_balance,
            Customer.payment_terms_days,
        ).order_by(Customer.customer_id)
    ).all()
    invoice_rows = db.execute(
        select(
            Invoice.invoice_id,
            Invoice.invoice_date,
            Invoice.total_amount,
            Invoice.status,
            Order.customer_id,
        )
        .join(Order, Invoice.order_id == Order.order_id)
        .order_by(Invoice.invoice_id)
    ).all()
    payment_rows = db.execute(
        select(
            Payment.payment_id,
            Payment.invoice_id,
            Payment.payment_date,
            Payment.amount,
            Payment.payment_method,
        ).order_by(Payment.payment_id)
    ).all()
    supplier_rows = db.execute(
        select(
            Supplier.supplier_id,
            Supplier.supplier_name,
            Supplier.payment_terms_days,
        ).order_by(Supplier.supplier_id)
    ).all()
    purchase_rows = db.execute(
        select(
            Purchase.purchase_id,
            Purchase.supplier_id,
            Purchase.purchase_date,
            Purchase.total_amount,
            Purchase.status,
        ).order_by(Purchase.purchase_id)
    ).all()
    supplier_payment_rows = db.execute(
        select(
            PurchasePayment.purchase_payment_id,
            PurchasePayment.purchase_id,
            PurchasePayment.payment_date,
            PurchasePayment.amount,
        ).order_by(PurchasePayment.purchase_payment_id)
    ).all()

    return AnalyticsInputs(
        customers=tuple(
            CustomerInput(
                customer_id=row.customer_id,
                customer_name=row.customer_name,
                credit_limit=float(row.credit_limit),
                credit_balance=float(row.credit_balance),
                payment_terms_days=row.payment_terms_days,
            )
            for row in customer_rows
        ),
        invoices=tuple(
            InvoiceInput(
                invoice_id=row.invoice_id,
                customer_id=row.customer_id,
                invoice_date=row.invoice_date,
                total_amount=float(row.total_amount),
                status=row.status,
            )
            for row in invoice_rows
        ),
        payments=tuple(
            PaymentInput(
                payment_id=row.payment_id,
                invoice_id=row.invoice_id,
                payment_date=row.payment_date,
                amount=float(row.amount),
                payment_method=row.payment_method,
            )
            for row in payment_rows
        ),
        suppliers=tuple(
            SupplierInput(
                supplier_id=row.supplier_id,
                supplier_name=row.supplier_name,
                payment_terms_days=row.payment_terms_days,
            )
            for row in supplier_rows
        ),
        purchases=tuple(
            PurchaseInput(
                purchase_id=row.purchase_id,
                supplier_id=row.supplier_id,
                purchase_date=row.purchase_date,
                total_amount=float(row.total_amount),
                status=row.status,
            )
            for row in purchase_rows
        ),
        supplier_payments=tuple(
            SupplierPaymentInput(
                purchase_payment_id=row.purchase_payment_id,
                purchase_id=row.purchase_id,
                payment_date=row.payment_date,
                amount=float(row.amount),
            )
            for row in supplier_payment_rows
        ),
    )
