# Cash & Credit Intelligence methodology

This document describes the rule-based analytics implemented in
backend/app/services/analytics. It is an explanation of the current code, not
an accounting standard and not an automated decision engine. The report API
also returns the formula inputs and plain-language reasons for each result.

Reports use the business date in BUSINESS_TIMEZONE (Asia/Kolkata by default).
Their endpoints are GET /reports/receivables, GET /reports/customer-risk, and
GET /reports/cash-flow. All require reports:read, which is currently granted
to ADMIN and ACCOUNTS.

## Definitions

### Invoice and payment treatment

- Cancelled invoices, invoices dated after the report date, and payments dated
  after the report date are excluded.
- Due date = invoice date + the customer's payment-terms days.
- Real customer payments are CASH, UPI, BANK_TRANSFER, and CHEQUE.
- Credit rows are RETURN_CREDIT and CREDIT_APPLIED. They reduce the open
  invoice balance, but are not evidence of payment behaviour.
- Behaviour owed = max(0, invoice total - credit rows).
- A non-credit invoice is settled on the payment date when cumulative real
  payments first reach behaviour owed. If credit rows cover the full invoice,
  it is excluded from payment-behaviour lateness.
- Open remaining = max(0, invoice total - all payment rows), including credit
  rows. An invoice is open when its remaining amount is positive.
- Days late for a settled invoice = max(0, settlement date - due date).
- Overdue days for an open invoice = max(0, report date - due date).

Payment dates must be the date money actually arrived. Incorrect dates change
the settlement date, lateness, risk score, trend, and expected-cash timing.

### Receivables and aging

Receivables use only open remaining balances. Each open balance is assigned to
one bucket:

| Bucket | Rule |
| --- | --- |
| Not yet due | 0 overdue days |
| 1-30 | 1 through 30 overdue days |
| 31-60 | 31 through 60 overdue days |
| 61-90 | 61 through 90 overdue days |
| 90+ | More than 90 overdue days |

Total receivable is the sum of all five buckets. Overdue receivable is the sum
of every bucket except Not yet due.

Customer credit balance is credit the business owes the customer. It is
reported separately as total_customer_credit_balance and is never subtracted
from receivables, overdue amounts, aging, or risk inputs.

### Risk score and bands

The score is a transparent 0-100 measure where higher means riskier. Only
invoices settled during the last 180 days form the behaviour history. At least
three settled invoices are required. Otherwise the customer is
INSUFFICIENT_HISTORY: score and credit-limit suggestion are null, while open
receivables, overdue balance, and aging remain available.

For an eligible customer:

    lateness points
      = 40 x min(average days late, 45) / 45

    frequency points
      = 20 x share of eligible settled invoices paid late

    overdue-now points
      = 25 x min(oldest open overdue days, 60) / 60

    utilisation points
      = 15 x clamp((outstanding / credit limit - 0.70) / 0.30, 0, 1)

    score
      = clamp(lateness + frequency + overdue-now + utilisation, 0, 100)

If the credit limit is zero, utilisation is unavailable and contributes zero
points. The score bands are:

| Score | Band |
| --- | --- |
| Below 25 | RELIABLE |
| 25 up to, but not including, 50 | WATCH |
| 50 or more | RISKY |

Trend is calculated independently by comparing average days late in the last
90 days with the preceding 90 days. Each period needs at least two settled
invoices. A lower recent average is IMPROVING, an equal average is STABLE, and
a higher recent average is WORSENING. Otherwise trend is null.

### Suggested credit limit

The suggestion is display-only. The application never applies it, blocks an
order, or changes a customer record automatically.

The peak outstanding amount is the highest end-of-day outstanding balance over
the last 180 days. The result is rounded upward to the nearest 1,000 where a
rounding rule applies.

| Band | Formula |
| --- | --- |
| RELIABLE | max(current limit, 1.20 x peak outstanding), rounded up to 1,000 |
| WATCH | Current limit unchanged |
| RISKY | max(current outstanding, 0.50 x current limit), rounded up to 1,000 and never below current outstanding |
| INSUFFICIENT_HISTORY | No suggestion |

### Next 5 weeks cash projection

The cash-flow report has five consecutive seven-day buckets starting on the
report date. It projects movement, not money already in the bank.

For each open invoice:

    expected receipt date
      = max(invoice due date, report date) + scheduled median days late

Median days late is the median of that customer's eligible settled invoices.
It is zero when the customer has fewer than three settled invoices in the last
180 days, is capped at 30 days, and is rounded up to a whole day for scheduling.
Expected IN is the invoice's open remaining amount.

For each non-cancelled purchase dated on or before the report date:

    purchase remaining = max(0, purchase total - supplier payments to date)
    expected outflow date = max(purchase date + supplier payment terms, report date)

Expected OUT is the purchase remaining amount. A purchase with no remaining
amount is excluded.

For each weekly bucket:

    net movement = expected IN - expected OUT
    cumulative net = prior cumulative net + net movement

The conservative series excludes expected IN from RISKY customers and leaves
expected OUT unchanged. It has its own net movement and cumulative net.

The optional opening balance in the Cash & Credit page remains only in browser
component state. The page displays opening balance + cumulative net, and
opening balance + conservative cumulative net; it does not save or send that
value while it is typed.

## Current thresholds

| Configuration value | Current value | Used for |
| --- | ---: | --- |
| AGING_1_30_MAX_DAYS | 30 | Upper inclusive aging bound |
| AGING_31_60_MAX_DAYS | 60 | Upper inclusive aging bound |
| AGING_61_90_MAX_DAYS | 90 | Upper inclusive aging bound |
| RISK_HISTORY_WINDOW_DAYS | 180 | Risk and median-lateness history |
| RISK_MIN_SETTLED_INVOICES | 3 | Minimum history for score and median lateness |
| LATENESS_MAX_POINTS | 40 | Lateness component cap |
| LATENESS_CAP_DAYS | 45 | Lateness days cap |
| LATE_FREQUENCY_MAX_POINTS | 20 | Late-frequency component cap |
| OVERDUE_NOW_MAX_POINTS | 25 | Oldest-overdue component cap |
| OLDEST_OVERDUE_CAP_DAYS | 60 | Oldest-overdue days cap |
| UTILISATION_MAX_POINTS | 15 | Utilisation component cap |
| UTILISATION_START_RATIO | 0.70 | Utilisation begins adding points above 70% |
| UTILISATION_FULL_RATIO | 1.00 | Utilisation reaches its cap at 100% |
| RELIABLE_SCORE_UPPER_BOUND | 25 | Exclusive upper bound for RELIABLE |
| WATCH_SCORE_UPPER_BOUND | 50 | Exclusive upper bound for WATCH |
| RISK_SCORE_MIN / RISK_SCORE_MAX | 0 / 100 | Final score clamp |
| TREND_WINDOW_DAYS | 90 | Size of each trend window |
| TREND_MIN_SETTLED_INVOICES_PER_WINDOW | 2 | Minimum settled invoices per trend window |
| RELIABLE_PEAK_OUTSTANDING_MULTIPLIER | 1.20 | RELIABLE suggestion multiplier |
| RISKY_CURRENT_LIMIT_MULTIPLIER | 0.50 | RISKY suggestion multiplier |
| CREDIT_LIMIT_ROUNDING_INCREMENT | 1,000 | Suggestion rounding increment |
| CASH_PROJECTION_WEEKS | 5 | Number of cash-flow buckets |
| CASH_PROJECTION_DAYS_PER_WEEK | 7 | Days in each bucket |
| PROJECTION_MEDIAN_DAYS_LATE_CAP | 30 | Maximum scheduled median lateness |

## Worked examples

These examples are illustrative calculations, not data from a customer
database.

### 1. Settlement versus open balance

An invoice for 10,000 has 14 payment-term days. It is due on 15 January. A
RETURN_CREDIT row for 2,000 and a CASH payment for 8,000 are recorded.

    behaviour owed = 10,000 - 2,000 = 8,000
    settlement date = date cumulative real payments reach 8,000
    days late = 20 January - 15 January = 5
    open remaining = 10,000 - (2,000 + 8,000) = 0

The credit row reduced the balance but did not count as behaviour. If the
credit rows instead totalled 10,000, behaviour owed would be zero and the
invoice would be excluded from lateness.

### 2. Aging and separate store credit

An invoice has a total of 12,000, all payments total 2,000, and it is 35 days
past due on the report date.

    open remaining = 12,000 - 2,000 = 10,000

The 10,000 is in the 31-60 bucket and is overdue. If the same customer also
has a 1,500 credit balance, the portfolio reports that 1,500 separately; it
does not turn the overdue amount into 8,500.

### 3. Risk score and suggestion

Suppose an eligible customer has average lateness of 15 days, three late
invoices out of four settled invoices, an oldest open overdue invoice of 30
days, outstanding of 9,000, and a 10,000 credit limit.

    lateness       = 40 x 15 / 45                 = 13.33
    frequency      = 20 x (3 / 4)                 = 15.00
    overdue-now    = 25 x 30 / 60                 = 12.50
    utilisation    = 15 x ((0.90 - 0.70) / 0.30)  = 10.00
    score          = 50.83

The score is RISKY. Its suggested limit is:

    max(9,000 outstanding, 0.50 x 10,000 current limit)
      = 9,000
    rounded up to the nearest 1,000
      = 9,000

This is a suggestion for review, not a change to the customer's credit limit.

### 4. One cash-flow bucket

On a report date of 10 January, an open invoice has 10,000 remaining, is due
12 January, and the customer's median lateness is 1.5 days. The scheduled
lateness is rounded up to two days, so the receipt is expected on 14 January.
A supplier purchase has 6,000 remaining and was due before 10 January, so its
outflow is expected on 10 January.

    expected IN  = 10,000
    expected OUT = 6,000
    net movement = 4,000
    cumulative net, if this is week 1 = 4,000

If the invoice belongs to a RISKY customer, the conservative expected IN is
zero. The conservative week-1 net is then -6,000. With an optional opening
balance of 100,000, the displayed balances would be 104,000 and 94,000
respectively. The opening balance is not persisted.

## Limitations and appropriate use

- These are deterministic rules, not machine learning. They do not learn from
  outcomes or claim to predict a customer's intent.
- A score and median lateness need at least three recently settled invoices.
  The UI intentionally says not enough history instead of inventing a score.
- Receipt scheduling assumes a customer will pay near its historical median
  delay. A changed relationship, dispute, seasonality, or a new payment plan
  can make that assumption wrong.
- The projection does not track cash on hand, bank balances, credit facilities,
  taxes, payroll, or expenses outside unpaid purchases. It is expected movement
  only.
- Expected IN and OUT are not commitments. They depend on invoice, purchase,
  payment, term, and status data being correct.
- Credit-limit values are suggestions only. No report result automatically
  changes a limit, blocks an order, or triggers a collection action.
- The report has no automated data-quality repair. In particular, payment_date
  must record when money actually arrived.
