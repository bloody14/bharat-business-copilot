# Bharat Business Copilot — Product Requirements Document

**Status:** Proposed — implementation awaits approval  
**Product:** AI operations copilot for Indian MSMEs  
**Primary users:** Business owners, managers, sales/billing staff, inventory staff, and support agents.

## 1. Product vision

Bharat Business Copilot is a secure, multi-tenant operating dashboard for Indian small and medium businesses. It brings products, stock, invoices, customers, support conversations, performance reporting, and marketing work into one place. Its AI employee turns business data into answers, recommendations, and controlled actions.

The first release should help a proprietor answer questions such as: *What is low in stock? Which customers have overdue invoices? What sold best this month? Draft a WhatsApp campaign for inactive customers.* The system must show the evidence behind AI responses and require confirmation before consequential actions.

### Business goals

- Reduce time spent on routine business operations.
- Improve stock availability and cash collection.
- Give non-technical owners understandable daily business insight.
- Establish a reliable foundation for future integrations (WhatsApp, payment gateways, GST/e-invoicing, accounting, marketplaces).

### Success metrics

- At least 70% of pilot businesses complete onboarding and add/import their catalogue.
- A billing flow creates a finalized invoice in under two minutes.
- Low-stock alerts are generated from an auditable stock ledger.
- Dashboard responses meet a p95 API latency target of 500 ms excluding AI jobs.
- AI action proposals are logged, attributable, and user-approved where required.

## 2. Scope

### MVP in scope

- Multi-tenant business workspaces, Clerk authentication, and role-based access.
- Product catalogue, suppliers, locations, stock movements, and low-stock alerts.
- Customers, quotations, invoices, invoice line items, payments, and PDF invoice export.
- Unified support inbox data model with manual/customer-message intake; AI reply drafts.
- KPI dashboard, date filters, sales/customer/product reports, and CSV export.
- Marketing audiences and AI-generated campaign drafts; approval before sending.
- A chat-style copilot with grounded read access and explicit, permissioned action tools.
- Audit log, observability, automated tests, and Vercel/Render deployment configuration.

### Explicitly deferred after MVP

- Direct WhatsApp Business, SMS, email, UPI/payment-gateway, GST/e-invoice, accounting and marketplace integrations.
- Full double-entry accounting, payroll, purchase-order workflow, multi-currency, native mobile apps, and autonomous outbound communication.
- High-risk financial/tax advice or automatic pricing/payment changes.

## 3. Personas and core journeys

| Persona | Need | Core journey |
|---|---|---|
| Owner | One dependable view of operations | Onboards business → views KPI dashboard → asks Copilot a business question → approves a recommended action. |
| Billing staff | Fast, correct billing | Finds customer → adds products → reviews GST/totals → issues invoice → records payment. |
| Inventory manager | Avoid stock-outs | Records receipt/adjustment → receives low-stock alert → reviews supplier and suggested reorder. |
| Support agent | Reply consistently | Opens customer conversation → uses AI draft grounded in customer/order history → edits and sends through a future channel adapter. |
| Marketing user | Reactivate and retain customers | Chooses an audience → generates localized draft → reviews compliance/consent → approves a campaign. |

## 4. Functional requirements

### Platform and access

- Clerk handles sign-in, sign-up, sessions, and organization membership.
- Every business-owned record is tenant-scoped by `organization_id` and never cross-readable.
- Roles: `owner`, `admin`, `manager`, `billing`, `inventory`, `support`, `marketing`, `viewer`; permissions are enforced by the API, not just the UI.
- Onboarding captures business identity, address, GSTIN (optional/validated when supplied), fiscal settings, invoice prefix, industry, and default currency INR.

### Inventory

- Manage products/services, SKUs, HSN/SAC, units, tax rates, sale price, cost price, categories, suppliers, and active status.
- Maintain stock by location using immutable receipt, sale, return, transfer, and adjustment movements.
- Calculate available quantity from the ledger; prevent negative stock unless an authorized setting enables it.
- Configurable reorder point; alerts appear in dashboard and notification center.
- CSV imports/exports include validation errors and an import audit record.

### Billing and collections

- Manage customers, addresses, GSTIN, contact details, credit limits, and consent status.
- Create draft quotations and invoices; add line items, discounts, CGST/SGST/IGST, shipping/round-off, and notes.
- Finalizing an invoice creates sale stock movements atomically and locks financial fields; corrections use credit notes/cancel status rather than destructive edits.
- Issue sequential, organization-scoped invoice numbers. Generate printable/downloadable invoices.
- Record full/partial payments with method and reference; calculate invoice balance and overdue status.

### Customer support

- View customer conversations and messages with assigned owner, state, tags, priority, and internal notes.
- Support staff can create/reply/close conversations in MVP; channel delivery is stored behind a provider abstraction.
- AI proposes a reply, cites relevant customer/order data, and never sends without a human.

### Analytics

- Dashboard: sales, paid amount, receivables, invoice count, gross margin (when cost data exists), low-stock count, and open support count.
- Reports: sales trends, top products, customer performance, aging receivables, stock valuation, and low-stock list.
- All KPI definitions state their date/timezone treatment. Default timezone: Asia/Kolkata.

### Marketing

- Build saved audiences (e.g., inactive 90 days, top customers, overdue customers) from parameterized rules.
- Generate campaign copies in English/Hinglish/local-language where supported, with editable content and channel target.
- Enforce customer consent, review status, and a send log. MVP can simulate/queue sending until a delivery provider is integrated.

### Copilot

- Chat accepts business questions in natural language. It uses tenant-scoped tools to retrieve structured facts; it does not depend on raw model memory for business truth.
- Responses cite source records/report ranges and clearly distinguish facts, estimates, and recommendations.
- Read tools: sales summary, inventory status, customer/invoice search, support summaries, campaign metrics.
- Write tools: create draft invoice, draft reply, create alert/task, create draft campaign—each requires a review/confirm step. Only roles with the equivalent UI permission can authorize the action.
- Store conversations, tool calls, approvals, outcomes, and feedback for audit/evaluation. Provide a graceful unavailable/error state.

## 5. Non-functional requirements

- **Security:** HTTPS, Clerk JWT verification, organization scoping, server-side RBAC, input validation, rate limiting, secrets only in environment variables, encrypted managed database/storage, and audit trails.
- **Reliability:** idempotency keys for invoice finalization/payments/imports; database transactions for stock and billing state; retries and dead-letter handling for jobs.
- **Performance:** paginated lists; indexed organization/date/status keys; aggregate/report queries designed for large tenants; background workers for PDFs, imports, campaigns, and long AI tasks.
- **Accessibility/localization:** responsive Indian-English first interface, WCAG 2.1 AA target, locale-ready currencies/dates/languages.
- **Privacy/compliance:** minimize PII sent to models, redact sensitive fields from logs, retention/deletion workflow, consent records, and legal review before handling GST or regulated advice.
- **Quality:** unit, integration, contract, end-to-end, and authorization-isolation tests. CI gates lint/type checks/tests/migrations.

## 6. Milestones and implementation tasks

### M0 — Product foundation and decisions

1. Confirm MVP users, business vertical(s), launch market/languages, and billing/GST policy.
2. Write UX flows, acceptance criteria, permission matrix, KPI definitions, and data-retention policy.
3. Select AI provider/model, transactional email/PDF/storage provider, and future channel providers.
4. Define environments, secrets ownership, error tracking, analytics, and release process.

### M1 — Platform skeleton and identity

1. Create separate Next.js and FastAPI applications with shared API contract conventions.
2. Configure Tailwind, shadcn/ui, linting, formatting, TypeScript strict mode, and test harnesses.
3. Configure PostgreSQL, SQLAlchemy/Alembic, configuration management, health checks, and structured logs.
4. Integrate Clerk frontend session handling and backend JWT verification.
5. Implement organization onboarding, roles, permissions, tenant middleware, audit events, and CI.

### M2 — Catalogue and inventory

1. Implement product/category/supplier/location schemas and CRUD APIs/UI.
2. Implement immutable stock-ledger commands and balance projection queries.
3. Add stock adjustment/receipt/transfer UI, validation, and authorization.
4. Add reorder thresholds, alert generation, dashboard cards, import/export, and tests.

### M3 — Customers, billing, and collections

1. Implement customer CRUD, search, tags, GST data, and consent fields.
2. Implement quotations and invoice drafts with tax/discount/rounding calculation service.
3. Implement transaction-safe invoice finalization, number allocation, stock reservation/movement, and idempotency.
4. Add payment recording, receivables aging, status transitions, cancellation/credit-note policy, and invoice PDF job.
5. Add billing screens and tests for taxes, permissions, duplicate requests, and concurrent stock changes.

### M4 — Dashboard and reporting

1. Define versioned KPI/report query services and indexes.
2. Build dashboard widgets, filters, drill-down links, empty/loading/error states.
3. Implement sales, products, customers, receivables, and inventory reports plus CSV exports.
4. Add snapshot/aggregation jobs if production query volume requires them; validate totals against source data.

### M5 — Support and marketing workflows

1. Implement conversations, messages, assignments, tags, notes, SLA fields, and inbox UI.
2. Establish outbound provider adapter interfaces and provider-event/webhook verification patterns.
3. Implement saved audience rules, consent filtering, campaign drafts, approval state, and delivery-log model.
4. Add UI and API permission/integration tests; ship simulated delivery only until provider integration is approved.

### M6 — AI employee

1. Define tool schemas, read/write permissions, source-citation format, approval workflow, and evaluation dataset.
2. Implement tenant-scoped retrieval/query tools and conversation persistence.
3. Implement orchestrator, policy guardrails, draft/action confirmation UI, and audit records.
4. Add prompt-injection tests, hallucination/evidence checks, cost/latency telemetry, feedback capture, and fallback behavior.

### M7 — Production hardening and launch

1. Configure Vercel frontend, Render API/worker, managed PostgreSQL, domains, CORS, secrets, migrations, backups, and rollback.
2. Add monitoring, alerts, tracing, rate limits, security headers, dependency scanning, and load tests.
3. Conduct accessibility, security, tenant-isolation, UAT, and disaster-recovery tests.
4. Prepare runbooks, support procedures, release checklist, product analytics, pilot onboarding, and post-launch backlog.

## 7. Recommended repository structure

```text
bharat-business-copilot/
  frontend/
    app/                    # Next.js routes, layouts, server components
    components/             # feature and shared UI components
    features/               # domain-oriented UI, hooks, schemas, API clients
    lib/                    # Clerk, API client, utilities
    public/
    tests/
  backend/
    app/
      api/v1/               # FastAPI routers and dependency wiring
      core/                 # config, security, logging, errors
      domain/               # entities, value objects, repository ports
      application/          # use cases, DTOs, policy services
      infrastructure/       # SQLAlchemy, Clerk, AI, storage, provider adapters
      workers/              # asynchronous job entrypoints
    alembic/
    tests/
  contracts/                # OpenAPI snapshot/generated TypeScript client (optional)
  docs/                     # ADRs, API standards, operational runbooks
  infra/                    # deployment and environment configuration
  .github/workflows/
```

Use domain modules (identity, inventory, billing, CRM, support, marketing, analytics, copilot) rather than a single technical-layer-only module. Keep the `domain` and `application` layers independent of FastAPI/SQLAlchemy where practical.

## 8. Recommended data entities

All tenant records include `id`, `organization_id`, `created_at`, `updated_at`; operational records also carry an actor/source where applicable.

| Domain | Core entities |
|---|---|
| Identity | Organization, OrganizationProfile, UserProfile, Membership/Role, AuditLog |
| Catalogue & inventory | Product, ProductCategory, Supplier, InventoryLocation, StockMovement, StockBalanceProjection, ReorderRule, InventoryAlert, ImportJob |
| CRM | Customer, CustomerAddress, CustomerTag, CustomerConsent |
| Billing | Quote, QuoteLine, Invoice, InvoiceLine, Payment, CreditNote, TaxRate, InvoiceSequence, Document |
| Support | Conversation, ConversationParticipant, Message, InternalNote, SupportAssignment, SupportTag |
| Marketing | Audience, AudienceRule, Campaign, CampaignMessage, CampaignApproval, DeliveryAttempt |
| Analytics | ReportSnapshot (optional), MetricDefinition, ExportJob |
| Copilot | CopilotConversation, CopilotMessage, AgentRun, ToolCall, ActionProposal, Approval, AgentFeedback |
| Platform | Notification, FileAsset, WebhookEvent, IdempotencyKey, OutboxEvent, BackgroundJob |

Key relationships: an Organization owns every business entity; Customer owns invoices/conversations/consents; Invoice owns lines/payments and causes StockMovements; Product has ledger movements per InventoryLocation; Campaign targets Customer members derived from Audience; Copilot runs reference records and tool calls but must never bypass domain services.

## 9. API design and endpoint groups

Version all routes under `/api/v1`, return a stable error envelope, accept/emit ISO-8601 timestamps, paginate list endpoints, and derive organization/user from Clerk claims—not client-provided IDs. Important mutation endpoints accept `Idempotency-Key`.

| Group | Representative endpoints |
|---|---|
| System/auth | `GET /health`, `GET /me`, `GET /organizations/current`, `PATCH /organizations/current`, `GET /roles` |
| Dashboard | `GET /dashboard/summary`, `GET /dashboard/activity` |
| Products | `GET/POST /products`, `GET/PATCH /products/{id}`, `POST /products/imports`, `GET /products/export` |
| Inventory | `GET /inventory/balances`, `POST /inventory/movements`, `GET /inventory/movements`, `GET/PATCH /inventory/reorder-rules`, `GET /inventory/alerts` |
| Suppliers/locations | `GET/POST /suppliers`, `GET/PATCH /suppliers/{id}`, `GET/POST /locations` |
| Customers | `GET/POST /customers`, `GET/PATCH /customers/{id}`, `GET /customers/{id}/timeline`, `PATCH /customers/{id}/consents` |
| Quotes/invoices | `GET/POST /quotes`, `POST /quotes/{id}/convert`, `GET/POST /invoices`, `GET/PATCH /invoices/{id}`, `POST /invoices/{id}/finalize`, `POST /invoices/{id}/cancel`, `GET /invoices/{id}/document` |
| Payments | `POST /invoices/{id}/payments`, `GET /payments`, `GET /reports/receivables-aging` |
| Support | `GET/POST /conversations`, `GET /conversations/{id}`, `POST /conversations/{id}/messages`, `PATCH /conversations/{id}`, `POST /webhooks/{provider}` |
| Marketing | `GET/POST /audiences`, `GET/POST /campaigns`, `POST /campaigns/{id}/generate-draft`, `POST /campaigns/{id}/approve`, `POST /campaigns/{id}/schedule`, `GET /campaigns/{id}/deliveries` |
| Reports/jobs | `GET /reports/sales`, `GET /reports/products`, `GET /reports/customers`, `GET /reports/inventory`, `POST /exports`, `GET /jobs/{id}` |
| Copilot | `GET/POST /copilot/conversations`, `POST /copilot/conversations/{id}/messages`, `GET /copilot/runs/{id}`, `POST /copilot/proposals/{id}/approve`, `POST /copilot/proposals/{id}/reject` |

## 10. AI employee architecture

```text
User → Next.js Copilot UI → FastAPI Copilot API
                                ↓
                    Auth/RBAC + tenant policy gate
                                ↓
                       Agent orchestrator
               ↙                 ↓                 ↘
     Structured read tools   Policy engine   Draft/action tools
               ↓                 ↓                 ↓
          PostgreSQL/query    Approval gate → Domain use cases
               ↓                                  ↓
      Evidence/citations                  Audit + outbox/job queue
```

1. The API authenticates the Clerk user and obtains their organization and permissions.
2. The orchestrator classifies the request, invokes only allow-listed typed tools, and supplies minimal tenant-scoped data to the model.
3. Read tools return typed facts plus record identifiers/ranges used for visible citations. Write tools create proposals/drafts, never direct state changes from model text.
4. The policy engine blocks unsupported actions, sensitive-data leakage, cross-tenant access, and actions outside the user’s role. A human confirmation supplies the final authorization.
5. Domain application services execute approved proposals transactionally, emitting audit and outbox events. Worker processes PDFs, campaigns, imports, and long-running tasks.
6. Store traces without unnecessary PII, monitor latency/token cost/tool failures, and run a curated regression suite before model or prompt changes.

## 11. Principal risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Cross-tenant data exposure | Critical privacy/security failure | Enforce organization filtering in repositories, test isolation, use Clerk claims server-side, and audit access. |
| Incorrect stock or invoice totals | Financial/operational loss | Immutable ledger, transactions, idempotency, locked finalized invoices, and reconciliation tests. |
| GST/legal complexity | Compliance risk | Treat calculations as configurable, validate with an Indian tax professional, and defer e-invoicing until certified. |
| AI hallucination or unsafe action | Loss of trust/data errors | Typed retrieval, citations, least-privilege tools, human approval, test/evaluation suite, and no autonomous financial actions. |
| WhatsApp/provider policy changes | Delivery failures/compliance | Provider adapter boundary, consent ledger, template review, webhook verification, and delivery observability. |
| Growing report cost/latency | Slow dashboard | Proper indexes, pagination, query limits, aggregates/snapshots, and performance monitoring. |
| Clerk/API deployment mismatch | Authentication outages | Explicit CORS/JWT audience configuration, staging environment, health checks, and end-to-end auth tests. |
| Scope expansion | Delayed MVP | Enforce M0 acceptance criteria and defer integrations/accounting/mobile until core workflows validate. |

## 12. Approval gates before implementation

1. Approve this MVP scope and deferred features.
2. Confirm target business vertical(s) and whether GST-ready invoicing is required for the first pilot.
3. Confirm the initial support/marketing channel priority (or simulated workflows first).
4. Approve the AI guardrail policy: human review for every write or outbound action in MVP.
5. Approve chosen third-party services and deployment accounts before credentials/integration work begins.
