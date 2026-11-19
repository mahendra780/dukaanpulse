import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  Boxes,
  Building2,
  FileText,
  KeyRound,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  UserCog,
  Users,
  Wallet,
} from "lucide-react";
import Logo from "../components/Logo";
import "./Landing.css";

/* ---------- Small helpers ---------- */

// True once the element has scrolled into view (and stays true).
function useInView(options) {
  const ref = useRef(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    if (!("IntersectionObserver" in window)) {
      setInView(true);
      return undefined;
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true);
        observer.disconnect();
      }
    }, { threshold: 0.15, ...options });
    observer.observe(element);
    return () => observer.disconnect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return [ref, inView];
}

// Fades and lifts its content into place when it scrolls into view.
function Reveal({ as: Tag = "div", delay = 0, className = "", children, ...rest }) {
  const [ref, inView] = useInView({ rootMargin: "0px 0px -8% 0px" });
  return (
    <Tag
      ref={ref}
      className={`lp-reveal${inView ? " is-visible" : ""}${className ? ` ${className}` : ""}`}
      style={{ "--d": delay }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

// A number that counts up the first time it is seen.
function CountUp({ to, prefix = "", duration = 900 }) {
  const [ref, inView] = useInView();
  const [value, setValue] = useState(0);

  useEffect(() => {
    if (!inView) return undefined;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setValue(to);
      return undefined;
    }
    const start = performance.now();
    let frame;
    const tick = (now) => {
      const progress = Math.min(1, (now - start) / duration);
      setValue(to * (1 - (1 - progress) ** 3));
      if (progress < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [inView, to, duration]);

  return (
    <span ref={ref}>
      {prefix}
      {Math.round(value).toLocaleString("en-IN")}
    </span>
  );
}

/* ---------- Content ---------- */

const PAINS = [
  {
    icon: FileText,
    title: "Credit scattered across notebooks",
    text: "Who owes what, and since when, lives in three registers and a few phone chats.",
  },
  {
    icon: Boxes,
    title: "Stock that never matches the bills",
    text: "The shelf says one number, the bill says another, and nobody knows which is right.",
  },
  {
    icon: Users,
    title: "No idea who will actually pay",
    text: "You find out a customer is a bad risk only after the money is already stuck.",
  },
];

const STEPS = [
  {
    icon: ShoppingCart,
    title: "Buy",
    text: "Raise purchases with your suppliers and record what you owe them.",
  },
  {
    icon: Boxes,
    title: "Stock",
    text: "Every purchase, sale and return becomes a stock entry with a trail.",
  },
  {
    icon: FileText,
    title: "Sell",
    text: "Take orders, invoice them in parts, and follow each delivery.",
  },
  {
    icon: Wallet,
    title: "Collect",
    text: "Record payments, handle returns and apply credit to the next invoice.",
  },
];

const FEATURES = [
  {
    icon: FileText,
    title: "Orders and invoices",
    text: "Invoice an order in parts as stock goes out, and track every delivery to the door.",
  },
  {
    icon: Boxes,
    title: "Stock you can trust",
    text: "Stock is the sum of recorded movements, so every number on screen can be explained.",
  },
  {
    icon: RotateCcw,
    title: "Payments and returns",
    text: "Part-payments, supplier payments and returns. Credit from a return is applied for you.",
  },
  {
    icon: UserCog,
    title: "Roles for your team",
    text: "Owner, Admin, Sales, Warehouse, Accounts and Viewer. Everyone sees only what they need.",
  },
  {
    icon: Building2,
    title: "More than one business",
    text: "Keep separate businesses under one login and switch between them in a click.",
  },
  {
    icon: BarChart3,
    title: "Cash and credit insight",
    text: "Know who pays late before you extend more credit.",
    href: "#credit",
  },
];

const CREDIT_POINTS = [
  "A risk score from 0 to 100 for every customer, built from real payment history, with the reasons shown",
  "Receivables aging, so you see what is 30, 60 and 90 days late",
  "A suggested credit limit for each customer",
  "A five-week cash outlook, so you spot a gap before it arrives",
];

const SAMPLE_CUSTOMERS = [
  { name: "Reliable Retailers", owed: 48200, score: 8, band: "Reliable", tone: "green" },
  { name: "Worsening Wholesale", owed: 112500, score: 38, band: "Keep an eye", tone: "amber" },
  { name: "Chronic Late Stores", owed: 236000, score: 71, band: "High risk", tone: "red" },
];

const CASH_WEEKS = [42, 18, 9, -21, 33]; // thousands of rupees, net per week
const CHART_HEIGHT = 140;
const BASELINE = 92;
const PX_PER_THOUSAND = 2;

const SALES_BARS = [38, 52, 44, 61, 58, 72, 66, 80, 74, 88, 70, 96];
const MONTH_LABELS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

const TRUST = [
  {
    icon: KeyRound,
    title: "Sign in with your mobile",
    text: "One-time codes to your phone and strongly hashed passwords keep accounts yours.",
  },
  {
    icon: UserCog,
    title: "Access by role",
    text: "What each person can see or change is enforced on the server, not just hidden on screen.",
  },
  {
    icon: ShieldCheck,
    title: "Your business, kept separate",
    text: "Each business's data is walled off from every other business on the platform.",
  },
];

/* ---------- Page ---------- */

export default function Landing() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div className="lp">
      <a className="lp-skip" href="#main">Skip to content</a>

      <header className={`lp-nav${scrolled ? " is-scrolled" : ""}`}>
        <div className="lp-container lp-nav-inner">
          <Link to="/" className="lp-nav-logo" aria-label="DukaanPulse home">
            <Logo onDark />
          </Link>
          <nav className="lp-nav-links" aria-label="Sections">
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <a href="#credit">Cash and credit</a>
            <a href="#security">Security</a>
          </nav>
          <div className="lp-nav-actions">
            <Link className="lp-btn lp-btn-line lp-btn-sm" to="/login">Login</Link>
            <Link className="lp-btn lp-btn-brass lp-btn-sm" to="/signup">Get started</Link>
          </div>
        </div>
      </header>

      <main id="main" tabIndex={-1}>
        {/* ---------- Hero ---------- */}
        <section className="lp-hero lp-awning-edge" aria-labelledby="hero-title">
          <div className="lp-container lp-hero-grid">
            <div className="lp-hero-copy">
              <p className="lp-eyebrow lp-in" style={{ "--d": 0 }}>Wholesale ERP for distributors</p>
              <h1 id="hero-title" className="lp-in" style={{ "--d": 80 }}>
                Run your wholesale business from <em>one place.</em>
              </h1>
              <p className="lp-hindi lp-in" style={{ "--d": 160 }}>Dukaan ka poora hisaab, ek jagah.</p>
              <p className="lp-lede lp-in" style={{ "--d": 240 }}>
                Orders, stock, payments and credit on one clear screen. Know who will pay
                before you give them more credit.
              </p>
              <div className="lp-cta lp-in" style={{ "--d": 320 }}>
                <Link className="lp-btn lp-btn-brass" to="/signup">
                  Get started
                  <ArrowRight size={18} aria-hidden="true" />
                </Link>
                <Link className="lp-btn lp-btn-line" to="/login">Login</Link>
              </div>
            </div>

            <figure
              className="lp-preview lp-in"
              style={{ "--d": 300 }}
              role="img"
              aria-label="Sample dashboard with sales, outstanding payments, low stock and a monthly sales chart"
            >
              <div className="lp-window" aria-hidden="true">
                <div className="lp-window-title">Dashboard</div>
                <div className="lp-mini-stats">
                  <div className="lp-mini"><span>Sales</span><strong>₹12.4L</strong></div>
                  <div className="lp-mini"><span>Outstanding</span><strong>₹2.3L</strong></div>
                  <div className="lp-mini"><span>Low stock</span><strong>7 items</strong></div>
                </div>
                <div className="lp-bars">
                  {SALES_BARS.map((height, index) => (
                    <span key={index} style={{ "--h": `${height}%`, "--i": index }} />
                  ))}
                </div>
                <div className="lp-bar-labels">
                  {MONTH_LABELS.map((label, index) => <span key={index}>{label}</span>)}
                </div>
              </div>
              <div className="lp-float lp-float-a" aria-hidden="true">
                <Wallet size={16} />
                Payment received <strong>₹8,400</strong>
              </div>
              <div className="lp-float lp-float-b" aria-hidden="true">
                <span className="lp-pill lp-pill-green">Reliable</span>
                Sharma Traders
              </div>
              <figcaption className="lp-sample">Sample data</figcaption>
            </figure>
          </div>
        </section>

        {/* ---------- Problems ---------- */}
        <section className="lp-section" aria-labelledby="pain-title">
          <div className="lp-container">
            <Reveal className="lp-section-head">
              <p className="lp-kicker">Sound familiar?</p>
              <h2 id="pain-title">Running a wholesale business is mostly keeping track.</h2>
            </Reveal>
            <div className="lp-grid lp-grid-3">
              {PAINS.map(({ icon: Icon, title, text }, index) => (
                <Reveal className="lp-card" delay={index * 90} key={title}>
                  <span className="lp-icon"><Icon size={20} aria-hidden="true" /></span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ---------- How it works ---------- */}
        <section className="lp-section lp-section-tight" id="how" aria-labelledby="how-title">
          <div className="lp-container">
            <Reveal className="lp-section-head">
              <p className="lp-kicker">How it works</p>
              <h2 id="how-title">From buying to getting paid, in one flow.</h2>
            </Reveal>
            <Reveal className="lp-steps">
              {STEPS.map(({ icon: Icon, title, text }, index) => (
                <div className="lp-step" key={title} style={{ "--s": index }}>
                  <span className="lp-step-dot"><Icon size={18} aria-hidden="true" /></span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </div>
              ))}
            </Reveal>
          </div>
        </section>

        {/* ---------- Features ---------- */}
        <section className="lp-section" id="features" aria-labelledby="features-title">
          <div className="lp-container">
            <Reveal className="lp-section-head">
              <p className="lp-kicker">Features</p>
              <h2 id="features-title">Everything the business needs, nothing it does not.</h2>
            </Reveal>
            <div className="lp-grid lp-grid-3">
              {FEATURES.map(({ icon: Icon, title, text, href }, index) => (
                <Reveal className="lp-card lp-card-hover" delay={(index % 3) * 90} key={title}>
                  <span className="lp-icon"><Icon size={20} aria-hidden="true" /></span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  {href && (
                    <a className="lp-more" href={href}>
                      See how <ArrowRight size={16} aria-hidden="true" />
                    </a>
                  )}
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ---------- Cash and credit ---------- */}
        <section className="lp-credit lp-awning-edge" id="credit" aria-labelledby="credit-title">
          <div className="lp-container lp-credit-grid">
            <Reveal className="lp-credit-copy">
              <p className="lp-kicker lp-kicker-brass">Cash and credit</p>
              <h2 id="credit-title">See who will pay before you give credit.</h2>
              <p className="lp-credit-lede">
                Most tools tell you what happened. This one helps you decide what to do next.
              </p>
              <ul className="lp-checks">
                {CREDIT_POINTS.map((point) => (
                  <li key={point}>
                    <span className="lp-check" aria-hidden="true" />
                    {point}
                  </li>
                ))}
              </ul>
            </Reveal>

            <Reveal delay={120}>
              <figure
                className="lp-preview lp-preview-static"
                role="img"
                aria-label="Sample table of customers with risk scores where lower is safer, and a five-week cash outlook with a gap in week four"
              >
                <div className="lp-window" aria-hidden="true">
                  <div className="lp-window-title">Customers by risk score (lower is safer)</div>
                  <div className="lp-rows">
                    {SAMPLE_CUSTOMERS.map((customer) => (
                      <div className="lp-row" key={customer.name}>
                        <div className="lp-row-name">
                          {customer.name}
                          <span>Owes ₹<CountUp to={customer.owed} /></span>
                        </div>
                        <div className="lp-row-score"><CountUp to={customer.score} /></div>
                        <span className={`lp-pill lp-pill-${customer.tone}`}>{customer.band}</span>
                      </div>
                    ))}
                  </div>

                  <div className="lp-window-title lp-window-title-gap">Cash outlook, next 5 weeks</div>
                  <div className="lp-cash" style={{ height: CHART_HEIGHT }}>
                    <span className="lp-cash-line" style={{ top: BASELINE }} />
                    {CASH_WEEKS.map((value, index) => {
                      const barHeight = Math.abs(value) * PX_PER_THOUSAND;
                      const position = value >= 0
                        ? { bottom: CHART_HEIGHT - BASELINE, height: barHeight }
                        : { top: BASELINE, height: barHeight };
                      return (
                        <span
                          key={index}
                          className={`lp-cash-bar${value < 0 ? " is-negative" : ""}`}
                          style={{ ...position, left: `${index * 20 + 4}%`, "--i": index }}
                        />
                      );
                    })}
                  </div>
                  <div className="lp-cash-labels">
                    {CASH_WEEKS.map((value, index) => (
                      <span key={index}>Wk {index + 1}</span>
                    ))}
                  </div>
                  <p className="lp-gap">Cash gap in week 4: <strong>₹21,000</strong></p>
                </div>
                <figcaption className="lp-sample">Sample data</figcaption>
              </figure>
            </Reveal>
          </div>
        </section>

        {/* ---------- Security ---------- */}
        <section className="lp-section" id="security" aria-labelledby="security-title">
          <div className="lp-container">
            <Reveal className="lp-section-head">
              <p className="lp-kicker">Security</p>
              <h2 id="security-title">Your data stays yours.</h2>
            </Reveal>
            <div className="lp-grid lp-grid-3">
              {TRUST.map(({ icon: Icon, title, text }, index) => (
                <Reveal className="lp-card" delay={index * 90} key={title}>
                  <span className="lp-icon"><Icon size={20} aria-hidden="true" /></span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </Reveal>
              ))}
            </div>
          </div>
        </section>

        {/* ---------- Final call to action ---------- */}
        <section className="lp-final" aria-labelledby="final-title">
          <Reveal className="lp-container lp-final-inner">
            <h2 id="final-title">Dukaan ka poora hisaab, ek jagah.</h2>
            <p>Create your workspace and start recording your first order today.</p>
            <div className="lp-cta lp-cta-center">
              <Link className="lp-btn lp-btn-brass" to="/signup">
                Get started
                <ArrowRight size={18} aria-hidden="true" />
              </Link>
              <Link className="lp-btn lp-btn-line" to="/login">Login</Link>
            </div>
          </Reveal>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-container lp-footer-inner">
          <div>
            <Logo onDark />
            <p>A wholesale ERP for distributors.</p>
          </div>
          <nav aria-label="Footer">
            <a href="#features">Features</a>
            <a href="#credit">Cash and credit</a>
            <Link to="/login">Login</Link>
            <Link to="/signup">Get started</Link>
          </nav>
        </div>
        <div className="lp-container lp-copyright">© 2026 DukaanPulse</div>
      </footer>
    </div>
  );
}
