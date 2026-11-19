import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleHelp,
  Info,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import {
  getCashFlowReport,
  getCustomerRiskReport,
  getReceivablesReport,
} from "../api/endpoints";
import { clearApiCache, extractErrorMessage } from "../api/client";
import { EmptyState, ErrorBanner, Spinner } from "../components/Feedback";
import "./CashCredit.css";

/* ---------- Formatting ---------- */

const currency = (value) => new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
}).format(Number(value || 0));

const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });

const percent = (value) => `${(Number(value || 0) * 100).toFixed(0)}%`;

const parseDate = (value) => new Date(`${value}T00:00:00`);

const formatDate = (value) => new Intl.DateTimeFormat("en-IN", {
  day: "numeric",
  month: "short",
  year: "numeric",
}).format(parseDate(value));

const dayMonth = new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" });
const shortRange = (start, end) => `${dayMonth.format(parseDate(start))} – ${dayMonth.format(parseDate(end))}`;

const formatKey = (key) => key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

/* ---------- Count-up for the big number ---------- */

function useCountUp(target, duration = 800) {
  const [value, setValue] = useState(0);
  const current = useRef(0);

  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      current.current = target;
      setValue(target);
      return undefined;
    }
    const from = current.current;
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      const next = progress === 1 ? target : from + (target - from) * (1 - (1 - progress) ** 3);
      current.current = next;
      setValue(next);
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return value;
}

function Amount({ value }) {
  const shown = useCountUp(Number(value || 0));
  return <>{currency(shown)}</>;
}

/* ---------- Plain-language labels ---------- */

const BANDS = {
  RELIABLE: { label: "Reliable", tone: "green", Icon: ShieldCheck },
  WATCH: { label: "Keep an eye", tone: "amber", Icon: CircleHelp },
  RISKY: { label: "High risk", tone: "red", Icon: AlertTriangle },
  INSUFFICIENT_HISTORY: { label: "Too new to rate", tone: "gray", Icon: Info },
};

const BAND_ORDER = ["RISKY", "WATCH", "RELIABLE", "INSUFFICIENT_HISTORY"];
const bandOf = (band) => BANDS[band] || BANDS.INSUFFICIENT_HISTORY;

function BandBadge({ band }) {
  const { label, tone, Icon } = bandOf(band);
  return (
    <span className={`badge badge-${tone} cc-badge`}>
      <Icon size={14} aria-hidden="true" />
      {label}
    </span>
  );
}

// 0 is safest, 100 is riskiest. The colour follows the band thresholds.
function RiskMeter({ score, thresholds }) {
  if (score === null || score === undefined) {
    return <span className="muted">Not rated yet</span>;
  }
  const watchFrom = thresholds?.reliable_score_upper_bound ?? 25;
  const riskyFrom = thresholds?.watch_score_upper_bound ?? 50;
  const tone = score < watchFrom ? "green" : score < riskyFrom ? "amber" : "red";
  return (
    <div
      className="cc-meter"
      role="img"
      aria-label={`Risk score ${Math.round(score)} out of 100. Lower is safer.`}
    >
      <div className="cc-meter-track">
        <span
          className={`cc-meter-fill cc-tone-${tone}`}
          style={{ width: `${Math.max(3, Math.min(100, score))}%` }}
        />
      </div>
      <span className="cc-meter-num">{Math.round(score)}</span>
    </div>
  );
}

function Trend({ trend }) {
  if (trend === "IMPROVING") return <span className="cc-trend"><i className="cc-dot cc-tone-green" />Paying faster</span>;
  if (trend === "WORSENING") return <span className="cc-trend"><i className="cc-dot cc-tone-red" />Paying slower</span>;
  if (trend === "STABLE") return <span className="cc-trend"><i className="cc-dot cc-tone-gray" />About the same</span>;
  return <span className="cc-trend muted">Not enough data</span>;
}

// One or two plain sentences about a customer.
function describeCustomer(risk, thresholds) {
  if (risk.band === "INSUFFICIENT_HISTORY") {
    const need = thresholds?.risk_min_settled_invoices ?? 3;
    const months = Math.round((thresholds?.risk_history_window_days ?? 180) / 30);
    return `Too new to rate. We need at least ${need} paid invoices from the last ${months} months.`;
  }
  const c = risk.components || {};
  const parts = [];
  if (c.settled_invoice_count > 0) {
    if (c.late_invoice_count > 0) {
      const days = c.average_days_late ? `, about ${Math.round(c.average_days_late)} days late on average` : "";
      parts.push(`Paid ${c.late_invoice_count} of ${c.settled_invoice_count} invoices late${days}`);
    } else {
      parts.push("Has paid every invoice on time");
    }
  }
  if (Number(risk.open_overdue) > 0) {
    const oldest = c.oldest_overdue_days ? `, the oldest ${c.oldest_overdue_days} days past due` : "";
    parts.push(`${currency(risk.open_overdue)} is overdue now${oldest}`);
  }
  if (c.utilisation_ratio !== null && c.utilisation_ratio !== undefined && c.utilisation_ratio >= 0.9) {
    parts.push(`${percent(c.utilisation_ratio)} of their credit limit is used`);
  }
  return parts.length ? `${parts.join(". ")}.` : "Nothing unusual.";
}

// What to actually do about it.
function suggestedAction(risk) {
  const suggestion = risk.suggested_credit_limit || {};
  if (risk.band === "RISKY") {
    if (suggestion.suggested_limit !== null && suggestion.suggested_limit !== undefined
      && suggestion.suggested_limit < suggestion.current_limit) {
      return `Consider lowering their credit limit from ${currency(suggestion.current_limit)} to ${currency(suggestion.suggested_limit)}.`;
    }
    return "Collect the overdue amount before giving more credit.";
  }
  return "Follow up on payment before giving more credit.";
}

/* ---------- Summary at the top ---------- */

function Summary({ totals, attentionCount }) {
  const outstanding = Number(totals.total_outstanding || 0);
  const overdue = Number(totals.total_overdue || 0);
  const share = outstanding > 0 ? overdue / outstanding : 0;
  const creditWeOwe = Number(totals.total_customer_credit_balance || 0);

  return (
    <section className="cc-hero" aria-labelledby="cc-hero-title">
      <div className="cc-hero-main">
        <p className="cc-hero-label" id="cc-hero-title">Customers owe you</p>
        <p className="cc-hero-amount"><Amount value={outstanding} /></p>
        <p className="cc-hero-sub">
          {overdue > 0
            ? <><strong>{currency(overdue)}</strong> of this is overdue ({percent(share)})</>
            : "Nothing is overdue right now."}
        </p>
        <div
          className="cc-hero-bar"
          role="img"
          aria-label={`${percent(share)} of the money owed to you is overdue`}
        >
          <span style={{ width: `${Math.min(100, share * 100)}%` }} />
        </div>
      </div>
      <div className="cc-hero-side">
        <div className="cc-hero-fact">
          <span>Customers needing attention</span>
          <strong>{attentionCount}</strong>
        </div>
        <div className="cc-hero-fact">
          <span>You owe customers</span>
          <strong>{currency(creditWeOwe)}</strong>
          <small>Store credit, for example from returns</small>
        </div>
      </div>
    </section>
  );
}

/* ---------- Who needs attention ---------- */

function AttentionList({ items, total, thresholds, onOpen }) {
  if (items.length === 0) {
    return (
      <div className="cc-allgood">
        <CheckCircle2 size={22} aria-hidden="true" />
        <div>
          <strong>No one needs chasing right now.</strong>
          <p>Every customer is paying on time, or is too new to rate.</p>
        </div>
      </div>
    );
  }
  return (
    <>
      <ul className="cc-attention">
        {items.map((risk) => (
          <li key={risk.customer_id} className={`cc-att cc-att-${bandOf(risk.band).tone}`}>
            <div className="cc-att-main">
              <div className="cc-att-top">
                <strong>{risk.customer_name}</strong>
                <BandBadge band={risk.band} />
              </div>
              <p>{describeCustomer(risk, thresholds)}</p>
              <p className="cc-att-action">
                <ArrowRight size={16} aria-hidden="true" />
                {suggestedAction(risk)}
              </p>
            </div>
            <div className="cc-att-money">
              <span>Overdue</span>
              <strong>{currency(risk.open_overdue)}</strong>
            </div>
            <button className="btn btn-secondary" type="button" onClick={() => onOpen(risk.customer_id)}>
              See why
            </button>
          </li>
        ))}
      </ul>
      {total > items.length && (
        <p className="cc-more">Showing the {items.length} most urgent of {total}. The full list is below.</p>
      )}
    </>
  );
}

/* ---------- How late is the money ---------- */

const AGING_ROWS = [
  { key: "not_yet_due", label: "Not due yet", hint: "Still within the payment time", tone: "green" },
  { key: "days_1_30", label: "1–30 days late", hint: "Just past the due date", tone: "yellow" },
  { key: "days_31_60", label: "31–60 days late", hint: "Worth a phone call", tone: "amber" },
  { key: "days_61_90", label: "61–90 days late", hint: "Getting risky", tone: "orange" },
  { key: "days_90_plus", label: "More than 90 days late", hint: "May never come back", tone: "red" },
];

function AgingRows({ aging }) {
  const total = Number(aging?.total_open ?? 0);
  const rows = AGING_ROWS.map((row) => ({ ...row, amount: Number(aging?.[row.key] || 0) }));
  const largest = Math.max(...rows.map((row) => row.amount), 0);

  if (total === 0) {
    return <EmptyState label="No customer owes you anything right now." />;
  }

  return (
    <ul className="cc-aging">
      {rows.map((row) => (
        <li key={row.key}>
          <div className="cc-aging-label">
            <strong>{row.label}</strong>
            <span>{row.hint}</span>
          </div>
          <div className="cc-aging-track" aria-hidden="true">
            <span
              className={`cc-aging-fill cc-tone-${row.tone}`}
              style={{ width: row.amount > 0 ? `${Math.max(2, (row.amount / largest) * 100)}%` : 0 }}
            />
          </div>
          <div className="cc-aging-amount">{currency(row.amount)}</div>
          <div className="cc-aging-share">{percent(total ? row.amount / total : 0)}</div>
        </li>
      ))}
    </ul>
  );
}

/* ---------- Customer details ---------- */

function RiskDetails({ risk, thresholds }) {
  const c = risk.components || {};
  const suggestion = risk.suggested_credit_limit || {};
  const tooNew = risk.band === "INSUFFICIENT_HISTORY";

  const parts = [
    { label: "How late they usually pay", points: c.lateness_points, max: thresholds?.lateness_max_points ?? 40 },
    { label: "How often they pay late", points: c.frequency_points, max: thresholds?.late_frequency_max_points ?? 20 },
    { label: "Overdue right now", points: c.overdue_now_points, max: thresholds?.overdue_now_max_points ?? 25 },
    { label: "How much of their limit is used", points: c.utilisation_points, max: thresholds?.utilisation_max_points ?? 15 },
  ];

  return (
    <div className="cc-detail">
      {tooNew ? (
        <p className="cc-detail-note">
          <Info size={16} aria-hidden="true" />
          {describeCustomer(risk, thresholds)}
        </p>
      ) : (
        <div className="cc-detail-grid">
          <div>
            <h4>Why this rating</h4>
            <p className="cc-detail-sub">
              The risk score is these four parts added together, out of 100. Lower is safer.
            </p>
            <ul className="cc-parts">
              {parts.map((part) => {
                const points = Number(part.points || 0);
                return (
                  <li key={part.label}>
                    <div className="cc-part-head">
                      <span>{part.label}</span>
                      <span>{points.toFixed(0)} of {part.max}</span>
                    </div>
                    <div className="cc-meter-track">
                      <span
                        className="cc-meter-fill cc-tone-amber"
                        style={{ width: `${Math.min(100, (points / part.max) * 100)}%` }}
                      />
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>

          <div>
            <h4>Their numbers</h4>
            <dl className="cc-facts">
              <div><dt>Invoices paid (last 6 months)</dt><dd>{c.settled_invoice_count ?? "n/a"}</dd></div>
              <div><dt>Of those, paid late</dt><dd>{c.late_invoice_count ?? "n/a"}</dd></div>
              <div><dt>Average delay</dt><dd>{c.average_days_late != null ? `${Math.round(c.average_days_late)} days` : "n/a"}</dd></div>
              <div><dt>Oldest overdue invoice</dt><dd>{c.oldest_overdue_days ? `${c.oldest_overdue_days} days` : "None"}</dd></div>
              <div><dt>Credit limit</dt><dd>{currency(c.credit_limit)}</dd></div>
              <div><dt>Credit used</dt><dd>{c.utilisation_ratio != null ? percent(c.utilisation_ratio) : "n/a"}</dd></div>
            </dl>

            {suggestion.suggested_limit != null && (
              <div className="cc-suggest">
                <span>Suggested credit limit</span>
                <strong>{currency(suggestion.suggested_limit)}</strong>
                <small>Their limit now is {currency(suggestion.current_limit)}. This is a suggestion only. Nothing changes unless you change it.</small>
              </div>
            )}
          </div>
        </div>
      )}

      {(risk.reasons?.length > 0 || suggestion.reasons?.length > 0) && (
        <details className="cc-tech">
          <summary>Show the calculation details</summary>
          <ul>
            {[...(risk.reasons || []), ...(suggestion.reasons || [])].map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </details>
      )}
    </div>
  );
}

/* ---------- Customer table ---------- */

function CustomerTable({ risks, thresholds, expandedId, setExpandedId, focusRequest }) {
  const [bandFilter, setBandFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState("RISK");

  const counts = useMemo(() => risks.reduce(
    (result, risk) => ({ ...result, [risk.band]: (result[risk.band] || 0) + 1 }),
    {},
  ), [risks]);

  const rows = useMemo(() => {
    const filtered = bandFilter === "ALL" ? risks : risks.filter((risk) => risk.band === bandFilter);
    return [...filtered].sort((left, right) => {
      if (sortBy === "NAME") return left.customer_name.localeCompare(right.customer_name);
      if (sortBy === "OWES") return Number(right.open_outstanding) - Number(left.open_outstanding);
      return (right.score ?? -1) - (left.score ?? -1);
    });
  }, [bandFilter, risks, sortBy]);

  // "See why" in the attention list shows everyone again, so the row is there to open.
  useEffect(() => {
    if (focusRequest) setBandFilter("ALL");
  }, [focusRequest]);

  return (
    <>
      <div className="cc-toolbar">
        <div className="cc-chips" role="group" aria-label="Filter customers by rating">
          <button
            type="button"
            className={`cc-chip${bandFilter === "ALL" ? " is-active" : ""}`}
            aria-pressed={bandFilter === "ALL"}
            onClick={() => setBandFilter("ALL")}
          >
            All <span>{risks.length}</span>
          </button>
          {BAND_ORDER.map((band) => (
            <button
              key={band}
              type="button"
              className={`cc-chip${bandFilter === band ? " is-active" : ""}`}
              aria-pressed={bandFilter === band}
              onClick={() => setBandFilter(band)}
            >
              {bandOf(band).label} <span>{counts[band] || 0}</span>
            </button>
          ))}
        </div>
        <div className="cc-sort">
          <label htmlFor="cc-sort">Sort by</label>
          <select id="cc-sort" value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
            <option value="RISK">Riskiest first</option>
            <option value="OWES">Owes the most</option>
            <option value="NAME">Name, A to Z</option>
          </select>
        </div>
      </div>

      {rows.length === 0 ? <EmptyState label="No customers in this group." /> : (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Customers with their credit rating, risk score and amounts owed</caption>
            <thead>
              <tr>
                <th>Customer</th>
                <th>Rating</th>
                <th>Risk score (0 to 100)</th>
                <th>Payment habit</th>
                <th className="num">Owes you</th>
                <th className="num">Overdue</th>
                <th><span className="sr-only">Details</span></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((risk) => {
                const expanded = expandedId === risk.customer_id;
                return (
                  <Fragment key={risk.customer_id}>
                    <tr id={`risk-row-${risk.customer_id}`} className={expanded ? "cc-row-open" : ""}>
                      <td><strong>{risk.customer_name}</strong></td>
                      <td><BandBadge band={risk.band} /></td>
                      <td><RiskMeter score={risk.score} thresholds={thresholds} /></td>
                      <td><Trend trend={risk.trend} /></td>
                      <td className="num">{currency(risk.open_outstanding)}</td>
                      <td className={`num${Number(risk.open_overdue) > 0 ? " cc-overdue" : ""}`}>{currency(risk.open_overdue)}</td>
                      <td>
                        <button
                          className="btn btn-ghost"
                          type="button"
                          aria-expanded={expanded}
                          aria-controls={`risk-${risk.customer_id}`}
                          onClick={() => setExpandedId(expanded ? null : risk.customer_id)}
                        >
                          {expanded ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}
                          {expanded ? "Hide" : "Why?"}
                        </button>
                      </td>
                    </tr>
                    {expanded && (
                      <tr className="risk-detail-row">
                        <td id={`risk-${risk.customer_id}`} colSpan="7">
                          <RiskDetails risk={risk} thresholds={thresholds} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

/* ---------- Cash outlook ---------- */

function CashOutlook({ cashFlow }) {
  const [openingBalance, setOpeningBalance] = useState("");
  const [cautious, setCautious] = useState(false);

  const opening = Number(openingBalance);
  const hasOpening = openingBalance.trim() !== "" && Number.isFinite(opening);

  const weeks = useMemo(() => (cashFlow?.next_5_weeks?.weeks || []).map((week) => {
    const moneyIn = Number(cautious ? week.conservative_expected_in : week.expected_in);
    const moneyOut = Number(week.expected_out || 0);
    const net = Number(cautious ? week.conservative_net_movement : week.net_movement);
    const total = Number(cautious ? week.conservative_cumulative_net : week.cumulative_net);
    return {
      number: week.week_number,
      label: `Week ${week.week_number}`,
      range: shortRange(week.start_date, week.end_date),
      moneyIn,
      moneyOut,
      outBar: -moneyOut,
      net,
      total,
      balance: hasOpening ? opening + total : null,
    };
  }), [cashFlow, cautious, hasOpening, opening]);

  if (weeks.length === 0) return <EmptyState label="No cash outlook is available yet." />;

  const gapWeek = hasOpening
    ? weeks.find((week) => week.balance < 0)
    : weeks.find((week) => week.net < 0);

  let headline;
  let headlineTone = "good";
  if (hasOpening) {
    if (gapWeek) {
      headline = `You may run out of cash in week ${gapWeek.number} (${gapWeek.range}).`;
      headlineTone = "bad";
    } else {
      headline = "Your cash looks fine for the next 5 weeks.";
    }
  } else if (gapWeek) {
    headline = `In week ${gapWeek.number}, more money goes out than comes in.`;
    headlineTone = "warn";
  } else {
    headline = "Every week, more money comes in than goes out.";
  }

  const chartData = weeks.map((week) => ({
    label: week.label,
    in: week.moneyIn,
    out: week.outBar,
    line: hasOpening ? week.balance : week.total,
  }));

  return (
    <>
      <div className={`cc-headline cc-headline-${headlineTone}`} role="status">
        {headlineTone === "good" ? <CheckCircle2 size={20} aria-hidden="true" /> : <AlertTriangle size={20} aria-hidden="true" />}
        <strong>{headline}</strong>
      </div>

      <div className="cc-controls">
        <div className="field cc-balance">
          <label htmlFor="cc-opening">Cash you have right now (optional)</label>
          <input
            id="cc-opening"
            type="number"
            min="-1000000000000"
            max="1000000000000"
            step="0.01"
            inputMode="decimal"
            placeholder="For example 50000"
            value={openingBalance}
            onChange={(event) => setOpeningBalance(event.target.value)}
          />
          <p className="field-help">Add it to see your balance week by week. It is used on this screen only and is not saved.</p>
        </div>

        <label className="cc-switch">
          <input
            className="cc-switch-input"
            type="checkbox"
            role="switch"
            checked={cautious}
            onChange={(event) => setCautious(event.target.checked)}
          />
          <span className="cc-switch-track" aria-hidden="true" />
          <span className="cc-switch-text">
            <strong>Be cautious</strong>
            <small>Do not count money from high-risk customers</small>
          </span>
        </label>
      </div>

      <div
        className="cc-chart"
        role="img"
        aria-label="Chart of money coming in and going out for each of the next five weeks"
      >
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 8, bottom: 4 }}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: "var(--text-muted)" }} axisLine={{ stroke: "var(--line)" }} tickLine={false} />
            <YAxis
              tick={{ fontSize: 12, fill: "var(--text-muted)" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(value) => `₹${compact.format(value)}`}
            />
            <Tooltip formatter={(value, name) => [currency(name === "Money going out" ? Math.abs(value) : value), name]} />
            <Legend />
            <Bar dataKey="in" name="Money coming in" fill="var(--success-500)" radius={[4, 4, 0, 0]} />
            <Bar dataKey="out" name="Money going out" fill="var(--error-500)" radius={[0, 0, 4, 4]} />
            <Line
              type="monotone"
              dataKey="line"
              name={hasOpening ? "Your cash balance" : "Running total"}
              stroke="var(--primary-500)"
              strokeWidth={2}
              dot
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <ul className="cc-weeks">
        {weeks.map((week) => {
          const short = hasOpening ? week.balance < 0 : week.net < 0;
          return (
            <li key={week.number} className={`cc-week${short ? " is-short" : ""}`}>
              <div className="cc-week-head">
                <strong>{week.label}</strong>
                <span>{week.range}</span>
              </div>
              <dl>
                <div><dt>Coming in</dt><dd className="cc-in">{currency(week.moneyIn)}</dd></div>
                <div><dt>Going out</dt><dd className="cc-out">{currency(week.moneyOut)}</dd></div>
                <div className="cc-week-net">
                  <dt>{week.net >= 0 ? "Left over" : "Short by"}</dt>
                  <dd>{currency(Math.abs(week.net))}</dd>
                </div>
                {hasOpening && (
                  <div><dt>Your balance</dt><dd className={week.balance < 0 ? "cc-out" : ""}>{currency(week.balance)}</dd></div>
                )}
              </dl>
              {short && <p className="cc-week-flag">{hasOpening ? "Cash gap" : "More out than in"}</p>}
            </li>
          );
        })}
      </ul>
    </>
  );
}

/* ---------- How it is worked out ---------- */

function Methodology({ methodology }) {
  if (!methodology) return null;
  return (
    <details className="panel methodology-panel">
      <summary>How these numbers are worked out</summary>
      <ul className="cc-howto">
        <li><strong>Risk score:</strong> 0 is safest and 100 is riskiest. It looks at how late a customer pays, how often, whether anything is overdue right now, and how much of their credit limit they use.</li>
        <li><strong>Rating:</strong> below {methodology.thresholds?.reliable_score_upper_bound ?? 25} is Reliable, up to {(methodology.thresholds?.watch_score_upper_bound ?? 50) - 1} is Keep an eye, and {methodology.thresholds?.watch_score_upper_bound ?? 50} or more is High risk.</li>
        <li><strong>Cash outlook:</strong> money expected from open invoices, based on how late each customer usually pays, and money you owe suppliers on their due dates.</li>
        <li><strong>Nothing changes by itself.</strong> Scores and credit limits are suggestions for you to decide on.</li>
      </ul>
      <p className="payment-date-note"><Info size={16} aria-hidden="true" />Record each payment with the day the money really arrived. {methodology.data_quality_note}</p>
      <details className="cc-tech">
        <summary>Technical details</summary>
        <p className="methodology-defaults">{methodology.defaults_note}</p>
        <p>{methodology.median_lateness_rule}</p>
        <h3>Formulas</h3>
        <dl className="methodology-list">
          {Object.entries(methodology.formulas || {}).map(([key, value]) => (
            <div key={key}><dt>{formatKey(key)}</dt><dd>{value}</dd></div>
          ))}
        </dl>
        <h3>Settings</h3>
        <dl className="methodology-list">
          {Object.entries(methodology.thresholds || {}).map(([key, value]) => (
            <div key={key}><dt>{formatKey(key)}</dt><dd>{String(value)}</dd></div>
          ))}
        </dl>
      </details>
    </details>
  );
}

/* ---------- Page ---------- */

const bandRank = (band) => BAND_ORDER.indexOf(band);

export default function CashCredit() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [receivables, setReceivables] = useState(null);
  const [riskReport, setRiskReport] = useState(null);
  const [cashFlow, setCashFlow] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [focusRequest, setFocusRequest] = useState(null);

  const loadReports = useCallback((force = false) => {
    if (force) clearApiCache();
    setError("");
    setRefreshing(true);
    return Promise.all([getReceivablesReport(), getCustomerRiskReport(), getCashFlowReport()])
      .then(([receivablesData, riskData, cashFlowData]) => {
        setReceivables(receivablesData);
        setRiskReport(riskData);
        setCashFlow(cashFlowData);
      })
      .catch((requestError) => setError(extractErrorMessage(requestError)))
      .finally(() => {
        setLoading(false);
        setRefreshing(false);
      });
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const methodology = receivables?.methodology || riskReport?.methodology || cashFlow?.methodology;
  const thresholds = methodology?.thresholds;
  const risks = useMemo(() => riskReport?.customers || [], [riskReport]);

  // Customers worth a phone call: high risk, or "keep an eye" and slipping or overdue.
  const attention = useMemo(() => risks
    .filter((risk) => risk.band === "RISKY"
      || (risk.band === "WATCH" && (risk.trend === "WORSENING" || Number(risk.open_overdue) > 0)))
    .sort((left, right) => bandRank(left.band) - bandRank(right.band)
      || Number(right.open_overdue) - Number(left.open_overdue)), [risks]);

  const openCustomer = (customerId) => {
    setExpandedId(customerId);
    setFocusRequest({ id: customerId });
    window.setTimeout(() => {
      document.getElementById(`risk-row-${customerId}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
    }, 120);
  };

  if (loading) return <Spinner label="Loading Cash & Credit…" variant="page" />;

  if (error && !receivables) {
    return (
      <div>
        <div className="page-header"><div><h1>Cash &amp; Credit</h1></div></div>
        <ErrorBanner message={error} />
        <button className="btn btn-secondary" type="button" onClick={() => loadReports(true)}>Try again</button>
      </div>
    );
  }

  const totals = receivables?.totals;

  return (
    <div className="cc">
      <div className="page-header">
        <div>
          <h1>Cash &amp; Credit</h1>
          <p>
            Who owes you money, who may pay late, and whether you will have enough cash.
            {cashFlow?.as_of_date ? ` Updated ${formatDate(cashFlow.as_of_date)}.` : ""}
          </p>
        </div>
        <button className="btn btn-secondary" type="button" onClick={() => loadReports(true)} disabled={refreshing}>
          <RefreshCw size={16} className={refreshing ? "cc-spin" : ""} aria-hidden="true" />
          {refreshing ? "Refreshing" : "Refresh"}
        </button>
      </div>

      {import.meta.env.VITE_DEMO_BANNER === "true" && (
        <div className="demo-banner"><Info size={18} aria-hidden="true" />Demo data</div>
      )}
      <ErrorBanner message={error} />

      {!totals ? <EmptyState label="No receivables data is available yet." /> : (
        <>
          <Summary totals={totals} attentionCount={attention.length} />

          <section className="panel" aria-labelledby="cc-attention-title">
            <div className="cc-panel-head">
              <h2 className="panel-title" id="cc-attention-title">Who needs attention</h2>
              <p>Customers who are paying late or likely to. Start here.</p>
            </div>
            <AttentionList
              items={attention.slice(0, 5)}
              total={attention.length}
              thresholds={thresholds}
              onOpen={openCustomer}
            />
          </section>

          <section className="panel" aria-labelledby="cc-aging-title">
            <div className="cc-panel-head">
              <h2 className="panel-title" id="cc-aging-title">How late is the money?</h2>
              <p>What customers still owe you, grouped by how many days past the due date.</p>
            </div>
            <AgingRows aging={totals.aging} />
          </section>

          <section className="panel" aria-labelledby="cc-customers-title">
            <div className="cc-panel-head">
              <h2 className="panel-title" id="cc-customers-title">All customers</h2>
              <p>
                Each customer gets a risk score from 0 to 100. <strong>Lower is safer.</strong>{" "}
                These are suggestions to help you decide, never automatic decisions.
              </p>
            </div>
            {risks.length === 0 ? (
              <EmptyState label="No customer ratings are available yet." />
            ) : (
              <CustomerTable
                risks={risks}
                thresholds={thresholds}
                expandedId={expandedId}
                setExpandedId={setExpandedId}
                focusRequest={focusRequest}
              />
            )}
          </section>

          <section className="panel" aria-labelledby="cc-cash-title">
            <div className="cc-panel-head">
              <h2 className="panel-title" id="cc-cash-title">Will you have enough cash?</h2>
              <p>
                What you can expect to receive and pay over the next 5 weeks.
                Money from customers is timed by how late each one usually pays.
              </p>
            </div>
            <CashOutlook cashFlow={cashFlow} />
          </section>

          <Methodology methodology={methodology} />
        </>
      )}
    </div>
  );
}