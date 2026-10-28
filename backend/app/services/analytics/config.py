"""Named analytics rules shared by every Cash & Credit Intelligence metric.

The values below implement D24--D27.  Keeping the business thresholds here
makes the calculations inspectable and prevents silent drift between reports.
"""

# D24: open receivables are grouped by these inclusive days-past-due limits.
AGING_1_30_MAX_DAYS = 30
AGING_31_60_MAX_DAYS = 60
AGING_61_90_MAX_DAYS = 90

# D25: use only recently settled invoices for payment-behaviour scoring.
RISK_HISTORY_WINDOW_DAYS = 180
RISK_MIN_SETTLED_INVOICES = 3

# D25: lateness contributes at most 40 of the 100 risk-score points.
LATENESS_MAX_POINTS = 40.0
LATENESS_CAP_DAYS = 45

# D25: the share of settled invoices paid late contributes at most 20 points.
LATE_FREQUENCY_MAX_POINTS = 20.0

# D25: the oldest currently overdue invoice contributes at most 25 points.
OVERDUE_NOW_MAX_POINTS = 25.0
OLDEST_OVERDUE_CAP_DAYS = 60

# D25: utilisation starts adding risk above 70% and reaches its maximum at 100%.
UTILISATION_MAX_POINTS = 15.0
UTILISATION_START_RATIO = 0.70
UTILISATION_FULL_RATIO = 1.00

# D25: total score bands.  The upper bounds are exclusive.
RELIABLE_SCORE_UPPER_BOUND = 25.0
WATCH_SCORE_UPPER_BOUND = 50.0
RISK_SCORE_MIN = 0.0
RISK_SCORE_MAX = 100.0

# D25: compare these two consecutive payment-behaviour windows for trend.
TREND_WINDOW_DAYS = 90
TREND_MIN_SETTLED_INVOICES_PER_WINDOW = 2

# D26: suggested credit-limit rules.  Suggestions are never applied automatically.
RELIABLE_PEAK_OUTSTANDING_MULTIPLIER = 1.20
RISKY_CURRENT_LIMIT_MULTIPLIER = 0.50
CREDIT_LIMIT_ROUNDING_INCREMENT = 1_000.0

# D27: five seven-day buckets make up the cash projection.  Median lateness is
# capped so an old payment history cannot push an expected receipt indefinitely.
CASH_PROJECTION_WEEKS = 5
CASH_PROJECTION_DAYS_PER_WEEK = 7
PROJECTION_MEDIAN_DAYS_LATE_CAP = 30
