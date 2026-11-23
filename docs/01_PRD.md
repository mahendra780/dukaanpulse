
# DukaanPulse: Product Requirements Document (PRD)

|                             |                                                                                                                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Product**           | DukaanPulse                                                                                                                                                               |
| **One line**          | A web app that runs a wholesale business from one place, and tells the owner who will pay late.                                                                           |
| **Document type**     | PRD: what we are building and why, in plain language                                                                                                                      |
| **Related documents** | [TRD](02-TRD.md), [App Flow](03-APP-FLOW.md), [UI/UX Brief](04-UIUX-DESIGN-BRIEF.md), [Backend Schema](05-BACKEND-SCHEMA.md), [Implementation Plan](06-IMPLEMENTATION-PLAN.md) |

---

## 1. What is DukaanPulse?

DukaanPulse is a website for **wholesale distributors**: the people who buy goods in bulk from suppliers and sell them in smaller lots to shops and retailers.

It replaces the paper registers (*bahi-khata*), the spreadsheets and the phone messages with one system that keeps every step of the business in order:

**Buy goods → Keep stock → Sell to customers → Deliver → Collect money → Handle returns**

On top of that, it has one feature that most small tools do not have: **Cash & Credit Intelligence**. It looks at how each customer has paid in the past and tells the owner:

- how much money customers owe right now,
- how much of it is already late,
- which customers are likely to pay late next time,
- how much credit it is safe to give each customer,
- and whether the business will run short of cash in the next five weeks.

It works in any browser, on a computer or a phone. Nothing needs to be installed.

---

## 2. The problem we are solving

A wholesale owner in a small town usually has these problems:

| Problem                                  | What it looks like in real life                                                                                            |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Credit is scattered**            | *Udhaar* is written in three registers and a few WhatsApp chats. Nobody knows exactly who owes how much, and since when. |
| **Stock does not match the bills** | The godown shows one number, the bills show another. Purchases, sales and returns are not recorded in one place.           |
| **Bad payers are found too late**  | The owner learns that a customer is a risk only after a lot of money is already stuck.                                     |
| **No warning about cash shortage** | Money coming in and money going out are never looked at together, so a shortage is a surprise.                             |
| **No control over staff**          | Everyone uses the same register or the same login. The owner cannot limit who sees or changes what.                        |
| **One business only**              | A paper system cannot safely handle more than one shop or firm.                                                            |

**Result:** money gets locked up in late payments, stock is wasted or runs out, and the owner makes decisions by guesswork.

---

## 3. Who is it for?

### Primary customer

**The owner of a small or medium wholesale business** (food grains, FMCG, hardware, stationery and similar trades) who sells goods on credit to many retail customers.

### The people who use it every day

| Role                | Who they are                                                         | What they mainly do in the app                                                   |
| ------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **Owner**     | The person who started the business account                          | Sees everything, manages staff, decides credit limits                            |
| **Admin**     | A trusted manager                                                    | Same as the Owner, except ownership cannot be changed                            |
| **Sales**     | Counter or field sales person                                        | Adds customers, takes orders, makes invoices, records payments, requests returns |
| **Warehouse** | Godown or stock person                                               | Manages products, suppliers, purchases, deliveries and received returns          |
| **Accounts**  | The person who handles money                                         | Records customer and supplier payments, approves returns, studies Cash & Credit  |
| **Viewer**    | Someone who only needs to look (for example an auditor or a partner) | Reads screens. Cannot change anything                                            |

### What we assume about these users

- They are comfortable with a phone, WhatsApp and basic web pages, but **not with technical words**.
- Many will use the app on a **phone**, in a shop or godown, often with a slow connection.
- The owner cares about two things above all: **"Where is my money?"** and **"Who should I be careful with?"**

---

## 4. Goals

### Product goals

1. **One true record.** Every purchase, sale, payment and return is entered once and everyone sees the same numbers.
2. **Always-correct stock.** Stock can always be explained: every increase and decrease has a record behind it.
3. **Clear view of money.** The owner can see, in plain words, who owes what and how late it is.
4. **Better credit decisions.** Every customer gets a simple rating (Reliable, Keep an eye, High risk) with the reasons shown, plus a suggested credit limit.
5. **Early cash warning.** A five-week view of money in and money out, so a shortage is seen before it arrives.
6. **Safe teamwork.** Each person gets only the access their job needs.
7. **Safe for many businesses.** One business can never see another business's data.

### What success looks like

| Measure                                                    | Target                                                                            |
| ---------------------------------------------------------- | --------------------------------------------------------------------------------- |
| A new owner can sign up and create the first order         | Within **15 minutes**, with no help                                         |
| Time to find "who owes me the most?"                       | **Under 30 seconds** from login                                             |
| Stock mismatch between app and godown after a month of use | Close to **zero** (every difference has a recorded reason)                  |
| A person with the Viewer role can change data              | **Never**                                                                   |
| One business sees another business's data                  | **Never**                                                                   |
| Main screens load                                          | Feel instant on a normal phone connection (skeleton screens appear straight away) |

---

## 5. What is in the product

### 5.1 Must have (the product is not usable without these)

| #  | Feature                                        | In simple words                                                                         |
| -- | ---------------------------------------------- | --------------------------------------------------------------------------------------- |
| 1  | **Sign up and login with mobile number** | A one-time code (OTP) is sent to the phone. No email needed.                            |
| 2  | **Business workspace**                   | Each business gets its own private space.                                               |
| 3  | **Staff and roles**                      | The owner invites staff by mobile number and gives each person a role.                  |
| 4  | **Products and packaging**               | Products with units like Piece, Box, Carton and how many pieces are in each.            |
| 5  | **Customers and suppliers**              | Contact details, credit limit and payment days.                                         |
| 6  | **Purchases**                            | Record goods bought from suppliers and mark them received.                              |
| 7  | **Stock**                                | Stock goes up on purchase and return, and goes down on sale. Always traceable.          |
| 8  | **Orders**                               | Customers' orders with products and quantities.                                         |
| 9  | **Invoices**                             | Bills made from orders. An order can be billed in parts.                                |
| 10 | **Deliveries**                           | Track a delivery from dispatched to delivered.                                          |
| 11 | **Customer payments**                    | Cash, UPI, bank transfer or cheque, with the invoice status updating by itself.         |
| 12 | **Supplier payments**                    | Track what is paid against each purchase.                                               |
| 13 | **Returns and credit**                   | Customer returns are approved, received back into stock, and turned into credit.        |
| 14 | **Dashboard**                            | Sales, purchases, low stock and payment summary at a glance.                            |
| 15 | **Cash & Credit Intelligence**           | Money owed, how late, who needs attention, risk ratings and the five-week cash outlook. |

### 5.2 Should have (makes the product pleasant and trustworthy)

- A **landing page** that explains the product, and a short **logo intro** when the site opens.
- **Skeleton loading** screens instead of blank pages, and quick page-to-page navigation.
- A **phone-friendly** layout, with a slide-in menu.
- **Clear messages** for errors, empty lists and success.
- **Password reset** with an OTP, and a list of active login sessions.

### 5.3 Later (not in the first release)

- Printable or PDF invoices and reports, and Excel export.
- WhatsApp or SMS payment reminders sent to customers.
- GST-ready invoice format and tax reports.
- Barcode scanning for stock entry and delivery.
- Multiple godowns or branches under one business.
- Offline mode for weak networks.
- Hindi and other language screens.

### 5.4 Not planned

- Online payment collection inside the app.
- Accounting software features such as a full ledger, balance sheet or profit-and-loss.
- Retail point-of-sale billing for walk-in customers.

---

## 6. How the main features work (in plain language)

### 6.1 Cash & Credit Intelligence

This is the feature that makes DukaanPulse different. It never changes any data. It only reads what has been recorded and explains it.

1. **Who owes me?** Total money owed, and how much of it is overdue.
2. **How late is the money?** Unpaid amounts grouped as *not due yet*, *1 to 30 days late*, *31 to 60*, *61 to 90* and *more than 90 days late*.
3. **How risky is each customer?** A score from **0 to 100**. **Lower is safer.**
   - Below 25: **Reliable**
   - 25 to 49: **Keep an eye**
   - 50 and above: **High risk**
   - Fewer than 3 paid invoices in the last 6 months: **Too new to rate**
4. **Why that score?** The score is built from four simple things: how late the customer usually pays, how often they pay late, whether something is overdue right now, and how much of their credit limit they are using. Every rating shows its reasons.
5. **Who needs attention?** A short list of the customers the owner should call first, each with one suggested action.
6. **How much credit is safe?** A suggested credit limit for each customer. It is only a suggestion. Nothing changes unless the owner changes it.
7. **Will I have enough cash?** A five-week view of money expected in (timed by how late each customer usually pays) and money going out to suppliers. A "be cautious" switch ignores money from high-risk customers.

### 6.2 Stock that can always be explained

Stock is never typed in as a loose number. Every change is a record:

| Event                          | Stock change        |
| ------------------------------ | ------------------- |
| Goods received from a supplier | Goes **up**   |
| Goods delivered to a customer  | Goes **down** |
| Returned goods received back   | Goes **up**   |

Current stock is simply the total of these records. So if the number looks wrong, the owner can look at the records and see why.

### 6.3 Payments and credit

- A payment can never be more than what is still unpaid on the invoice.
- Invoice status (Unpaid, Partly paid, Paid) updates by itself.
- When a customer returns goods, the money value becomes **credit**. It is first used against what the customer still owes on that invoice, and any extra is kept as the customer's **credit balance**, which can be applied to a later invoice.

### 6.4 Roles and privacy

- Each person logs in with their own mobile number and password.
- The app shows only the screens and buttons their role allows, and the server enforces the same rules.
- Each business's data is completely separate from every other business.

---

## 7. User stories

**Owner**

- As an owner, I want to see how much money customers owe me and how much is late, so I know how my business is doing.
- As an owner, I want to be told which customers to call first, so I can collect money sooner.
- As an owner, I want to give each staff member only the access they need, so mistakes and misuse are limited.
- As an owner, I want to know if I will run short of cash soon, so I can plan payments.

**Sales**

- As a sales person, I want to create an order and an invoice quickly, so the customer is not kept waiting.
- As a sales person, I want to see a customer's credit limit and how much they owe, so I know whether to give more credit.

**Warehouse**

- As a warehouse person, I want to record goods received and goods delivered, so stock stays correct.
- As a warehouse person, I want to be stopped from delivering more than we have, so we never oversell.

**Accounts**

- As an accounts person, I want to record a payment against an invoice, so the invoice status stays correct.
- As an accounts person, I want to approve returns and apply credit, so refunds and credit are handled properly.

**Viewer**

- As a viewer, I want to see the business numbers without being able to change them.

---

## 8. Rules the product must always follow

1. A payment can never be larger than the unpaid balance of its invoice.
2. An invoice can never bill more of a product than was ordered.
3. Stock can never go below zero through a sale or delivery.
4. A cancelled invoice cannot take payments or credit.
5. A returned quantity can never be more than what was sold.
6. A return adds stock back and creates credit only once, even if the button is clicked twice.
7. One business can never read or change another business's data.
8. A Viewer can never change anything.
9. The last Owner of a business cannot be removed or demoted.
10. Scores and credit limits are **suggestions only**. The system never blocks a sale on its own because of them.

---

## 9. Out of scope for now, and assumptions

**Assumptions**

- Users have a smartphone or computer with internet.
- Customers and suppliers are entered by the business; there is no customer login.
- Money is in Indian Rupees (INR). Dates use the Indian business timezone.
- The SMS provider for OTP is configured by whoever hosts the app.

**Out of scope for the first release:** items in 5.3 and 5.4.

---

## 10. Risks and how we handle them

| Risk                            | Why it matters                              | How we handle it                                                                                |
| ------------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Staff enter wrong data          | Wrong numbers lead to wrong decisions       | Validation on every form, and rules in section 8 enforced on the server                         |
| Two people act at the same time | Could oversell stock or double-apply credit | The server locks the affected records while it works (see TRD)                                  |
| Slow internet                   | App feels broken                            | Skeleton screens, short-lived caching and a light page size                                     |
| Owners do not trust a score     | They ignore the feature                     | Every score shows its reasons in plain words, and is never automatic                            |
| SMS codes do not arrive         | Nobody can sign up or log in                | Resend with a wait time, and a configurable SMS provider                                        |
| Data leak between businesses    | Serious trust and legal problem             | Layered separation: filters in code, plus database-level key rules (see TRD and Backend Schema) |

---

## 11. Glossary

| Word                               | Meaning                                                                             |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| **Wholesaler / distributor** | A business that buys in bulk and sells to shops                                     |
| **Udhaar / credit**          | Goods given now, with payment promised later                                        |
| **Receivable**               | Money that customers owe the business                                               |
| **Overdue**                  | Past the date the customer promised to pay                                          |
| **Aging**                    | Grouping unpaid money by how many days it is late                                   |
| **Credit limit**             | The most a customer is allowed to owe at one time                                   |
| **Credit balance**           | Money the business owes a customer (for example from a return)                      |
| **Workspace**                | One business's private space inside DukaanPulse                                     |
| **OTP**                      | One-time password sent by SMS                                                       |
| **Risk score**               | A number from 0 to 100 showing how likely a customer is to pay late. Lower is safer |
