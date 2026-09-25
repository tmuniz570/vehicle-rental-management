# 🏍️ FF Motors — Motorcycle Fleet, Rental & Sales Operations System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask&logoColor=white)
![Version](https://img.shields.io/badge/Version-1.9.8--Active%20Fleet%20Controls%20%26%20Tracker%20Protection-success?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14-336791?style=for-the-badge&logo=postgresql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Ready-orange?style=for-the-badge&logo=pwa&logoColor=white)
![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red?style=for-the-badge)
![Location](https://img.shields.io/badge/Location-Birmingham%2C%20UK-red?style=for-the-badge)

**A modern, mobile-first Fleet Operations, Rental & Sales Agreements, and Financial Management platform tailored for motorcycle businesses in the UK.**

</div>

---

## 📌 Overview

**FF Motors Management System** is an end-to-end web application developed to automate and streamline motorcycle rental operations. Built specifically to handle day-to-day motorcycle fleet management, client agreements, security deposit accounting, and digital vehicle inspections directly from the rental yard using smartphones or desktop computers.

The system features an installable **PWA (Progressive Web App)** interface with a custom **mobile bottom navigation bar**, client-side image compression for mobile cameras, automated recurring weekly rent generation, multi-payment split methods with partial settlements, multi-page V5C logbook uploads, and instant receipt printing.

---

## ✨ Key Features

### 📊 1. Executive Dashboard & Fleet Allocation
* **Live KPI Counters:** Real-time visibility into total fleet, available bikes, active rentals, motorcycles in maintenance, registered customers, and expected weekly revenue.
* **Out-of-Operation Visibility:** Total Fleet card shows active bikes in operation alongside an interactive out-of-operation badge (`🏛️ [N] OUT OF OP`) with 1-click navigation to `/motos?status=Pound`.
* **Interactive Fleet Allocation Bar:** Visual percentage breakdown of available, rented, workshop-held, and impounded (`Pound`) motorbikes.
* **Instant Overdue Alerts:** Immediate notification of late payments and actionable shortcuts.
* **Missing V5C Logbook Alarm:** Real-time dashboard alert listing all fleet vehicles without an attached V5C logbook document with 1-click links to upload documents.

### 🛵 2. Fleet & Vehicle Lifecycle
* **Default Active Fleet View:** Fleet table (`/motos`) defaults to `⚡ Active Fleet (In Operation)` excluding sold and impounded vehicles, with an explicit `All Statuses` dropdown option for full historical audit.
* **UK Registration Plate Standardization:** Dedicated plate badges (e.g., `XX10YYY`) with space-free input sanitization and status management (`Available`, `Rented`, `Maintenance`, `Pound`, `Sold`).
* **Pound Status & MOT/Tax Exemption:** Dedicated status (`Pound`) for motorbikes outside operation (e.g., impounded by police or held in external compounds). Motorbikes in this status are strictly exempt from MOT and Road Tax alerts on the executive dashboard and display `Exempt (Pound)` in fleet tables.
* **UK MOT & Road Tax (VED) Compliance:** Annual MOT test and DVLA Road Tax expiry date tracking with proactive warning badges (🟢 Valid, 🟡 Expiring within 30 days, 🔴 Expired).
* **DVLA SORN (Statutory Off Road Notification) Support:** Native toggle for vehicles officially declared off-road (SORN) with DVLA. Automatically disables Road Tax expiry dates, displays a distinctive `🛡️ SORN` badge in the fleet list, supports quick search (`search=sorn`), and excludes off-road bikes from false-positive Road Tax dashboard alerts.
* **Missing V5C Tracking & Alerts:** Fleet vehicles without V5C registration logbooks feature an eye-catching `⚠️ No V5C` badge in the fleet table, quick filtering (`/motos?v5c=missing`), and an amber alert badge on contract cards.
* **Maintenance Workflow:** One-click dispatch of motorbikes to the workshop with maintenance reason logging and quick release back to the active fleet.
* **V5C Logbook Multi-Page Management & Mobile Multi-Shot Camera:**
  - Dedicated multi-shot camera accumulator (`capture="environment"` and gallery picker) allowing operators to photograph multi-page V5C logbooks (Page 1, Page 2, Page 3...) consecutively on iPhone/Safari without reloading or uploading one-by-one.
  - Interactive preview grid with thumbnail, file size, and per-page discard button before batch uploading.
  - Single-click batch upload (`POST /api/motos/<placa>/v5c`) supporting image and digital PDF formats.
* **GPS Telematics & Tracker Duplicate Protection:**
  - Multiple GPS trackers per motorbike with ownership classification (`Company` vs `Customer`).
  - **Fleet-Wide Serial/IMEI Uniqueness:** Prevents duplicate tracker registration across vehicles, returning a descriptive error informing which plate currently holds the hardware.
  - **Mobile Numeric Keypad:** Input field equipped with `inputmode="numeric"` and `pattern="[0-9]*"` for effortless IMEI typing on iPhone and touchscreen devices.
  - Serial / IMEI tracking and dedicated camera capture for device stickers and wiring installations.

### 👥 3. Customer Relationship Management
* **Driver Records & UK Compliance:** Full tracking of client contact info, residential address, DVLA Driving Licence (dedicated Front & Back uploads), Compulsory Basic Training (CBT) certificate tracking, and utility proof uploads.
* **Deep-Link Customer Search & ID Match:** Direct URL parameter filtering (`/clientes?search=...`) with exact ID match prioritization (`db.case`), enabling instant customer discovery when clicking "View Client" from any contract detail screen.
* **1-Tap WhatsApp Integration:** Automatic normalization and international formatting of UK phone numbers (`+447...`) allowing instant WhatsApp chat links from any contract or customer card.

### 📁 4. Claims & Storage Management (Accident & Insurance Referrals)
* **Accident Claim Lifecycle:** Comprehensive tracking of insurance claims referred to specialist accident management partners, from approval date to final settlement.
* **Referral Fee Deadlines (14 Days):** Automatic calculation of the 14-day referral commission deadline following claim approval, with overdue alerts and settlement logging.
* **Yard Storage Limits (28 Days):** Automated monitoring of bikes stored on the yard awaiting insurer inspection, with 28-day release threshold alerts.
* **Storage Invoicing (14 Days):** Instant calculation of storage duration `(Days × £15/day)` upon bike release, dedicated printable and branded Storage Invoices, and 14-day insurer payment due dates.
* **Server-Side Pagination, Sorting & Date Period Filters:** Fast pagination (20 items/page), multi-column sorting, and multi-field date range filtering (Accident, Approval, Storage In, Release, Invoice Sent, Created).

### 📋 5. Contract Agreements & Lifecycle (Rentals & Vehicle Sales)
* **Dual Contract Modes (Rentals & Vehicle Sales):**
  - **Rental Agreements (`Rent`):** Provisions Week 1 collection rent and Week 2 recurring rent scheduled for the client's chosen weekday payment cycle, with security deposit holding.
  - **Full Vehicle Sales (`Sale_Full`):** Outright vehicle sale provisioned with pending transaction and immediate transition of motorcycle status to `Sold`. Automatically completes (`Completed`) upon total payment quittance.
  - **Instalment Vehicle Sales (`Sale_Installment`):** Financed purchase provisioned with segregated down payment (`Sale_Deposit`), administrative fee, itemized accessories, and scheduled instalment payment dates (`Sale_Installment`). Automatically completes (`Completed`) once down payment and all scheduled instalments are paid in full (£0.00 outstanding).
* **Sales Contract Lifecycle & Reopening:**
  - Automatic status transition to `Completed` when all sales transactions are settled.
  - Automatic reversal and reopening back to `Active` with audit trail tracking if a completed sale payment is cancelled or reverted.
  - Removal of "Return Mileage" and "Miles driven" rows on vehicle cards for sales contracts, displaying clean "Sale Mileage".
* **Interactive Itemized Accessories & Extras Builder:** Real-time selector and custom accessory adder (e.g., security trackers, locks, heated grips, weather covers) with dynamic cost summation applied directly to the agreement total.
* **Printable Formal Agreements & Legal Compliance (UK GDPR Clause 4.12):**
  - Dedicated print templates for rental agreements and vehicle sales agreements with fixed seller authorization signature, instalment schedule tables, UK vehicle history categorization (`Clear`, `Cat N`), and strict zero-blank-page pagination across iOS Safari (AirPrint) and desktop browsers.
  - Clause 4.12 Telematics/GPS tracking consent incorporated into rental and sales print agreements.
* **Smart Insurance Compliance & Exemption:** 15-day recurring government database verification (askMID) for active rentals, with automatic exemption for sold vehicles while preserving the collected insurance policy on file.
* **Pre-Delivery Compliance & Physical Release Checklist:**
  - Contracts can be completed immediately in `/contratos/novo` without mandatory photos or insurance documents, allowing operators to formalize deals while motorcycles are still being accessorised or customer insurance policies are being finalized.
  - Strict physical vehicle release safeguards: contracts with pending check-out inspections or insurance certificates display an urgent amber warning banner with 1-click action shortcuts (`Record Check-out Inspection`, `Upload Insurance Document`).
  - Contracts table features dedicated status badges (`⚠️ Needs Insp + Ins`, `⚠️ Needs Insp`, `⚠️ Needs Ins`) and a quick filter (`⚠️ Pre-Delivery Pending`).
  - Executive dashboard raises an alert highlighting all motorbikes on the premises awaiting pre-delivery checklist completion.
* **Protection Against Incompatible Operations:** Sold motorbikes are automatically protected against rental return inspections (`Check-in`) and excluded from recurring rental billing batches, while allowing warranty and damage logs (`Incident`).
* **Deposit Accounting & Settlement:** Security deposit holding, balance calculation, automated deductions when damages or fines occur, and deposit refund processing.

### 🔍 6. Digital Mobile Inspections & Incident Logging
* **Multi-Angle Camera Capture:** Tailored for yard operators using smartphones to snap vehicle photos at check-out, return check-in, or road incidents.
* **Client-Side Image Compression:** Automatic compression via `browser-image-compression` converting high-res smartphone captures to lightweight WebP formats before upload, saving bandwidth and cloud storage.
* **High-Definition Gallery:** Inspection modals with zoomable image grids and timestamped condition logs.

### 💳 7. Financial Statements, Multi-Payment (Split) & Partial Settlements
* **Full Contract Ledger:** Itemized breakdown of Rent, Security Deposits, Fines, and Repair charges with status tracking (`Pending`, `Paid`, `Overdue`).
* **Multi-Payment Methods (Split Payments & Part-Exchange):** Seamless division of any charge across multiple simultaneous payment forms (Cash, Card, Bank Transfer, Exchange (Vehicle Trade-in), Deposit, Other).
* **Intelligent Partial Settlement:** Clients can pay partial amounts towards any charge; the paid portion is receipted and the outstanding remainder is automatically spun off into a linked child balance transaction with the original due date.
* **Reversal with Auto-Merge:** Reverting a partial payment automatically re-merges child balance transactions back into the parent, maintaining immaculate ledger accuracy.
* **Overdue Report:** Dedicated centralized page (`/relatorios/vencidos`) aggregating all late payments across the fleet, direct customer contact links, and inline settlement actions. Charges due today remain pending for the entire day and strictly transition to overdue at 00:00:00 of the following day if unpaid.
* **Receipt Printing & Payment Notes:** Optional payment note and reference field captured upon marking charges as paid (e.g. part-exchange bike details, bank transfer reference, discount authorizations). Notes appear on printable payment receipts, transaction ledgers, and audit logs.
* **Automated Recurring Billing:** Integrated background scheduler (`APScheduler`) generating recurring rental invoices at **01:00 AM Europe/London** on designated weekly payment days.

### 📱 8. UI, Mobile-First & PWA Experience
* **Collapsible Slim Sidebar (Desktop):** Flexible desktop sidebar toggle button (`#sidebarToggleBtn`) with `Shift + S` shortcut. Operators can collapse the sidebar into a slim icon bar (`74px`) displaying centered vector SVG icons, dynamic FF logo monogram, and floating glassmorphism tooltips, maximizing horizontal data table real estate. State persists across pages via `localStorage` with zero-flicker preloading.
* **Native-Style Bottom Navigation:** High-usability bottom navigation bar enabled exclusively on mobile viewports (`<= 768px`) with iOS Safe Area Insets support.
* **Installable App:** Manifest configuration (`manifest.json`) and app icons allowing home screen installation on iOS (Safari) and Android (Chrome).

### 🔐 9. Authentication, Modular Permissions, Web Hardening & Audit Trail
* **Granular Modular Access Control:** True role separation allowing individual per-user permission toggles:
  - **Rental Module (`perm_alugueis`):** Access to fleet, customers, contracts, inspections, financial transactions, and overdue reports. Non-rental users are strictly blocked at route and API levels.
  - **Claims Module (`perm_claims`):** Access to accident claims, yard storage monitoring, referral fees, and storage invoices.
  - **Administrator (`is_admin`):** Full privileges to manage accounts, audit logs, and system operations.
* **Comprehensive Audit Trail:** 100% coverage of state-modifying actions (Login/Logout, Client updates, Transaction deletions, Contract alterations) capturing User, Timestamp, IP, and exact action details.
* **Brute-force Protection & Rate Limiting:** Built-in IP-based login rate limiting, blocking users after consecutive failed attempts.
* **Storage Optimization Script:** Standalone cleanup script to prune orphan file uploads generated from aborted registrations, preventing server bloat.
* **Role-Based Access Control (RBAC):** Distinct permissions (`admin`, `operador`, `financeiro`, `alugueis`) providing granular control over sensitive financial data and system configurations.
* **Secure Session Auth, Idle Timeout & Brute-Force Rate Limiting:** Protected dashboard and API endpoints powered by `Flask-Login` and hashed passwords (`werkzeug.security`). Configured with a 60-minute idle inactivity timeout (`check_authentication` hook), 12-hour session lifetime cap, and opt-in "Keep me signed in" checkbox. Built-in thread-safe IP rate limiter restricting failed login attempts to a maximum of 10 within 15 minutes (HTTP 429 on abuse).
* **CSRF Protection & Secure POST Logout:** Universal CSRF protection intercepting all state-altering requests (`POST`, `PUT`, `DELETE`, `PATCH`). Logout upgraded to CSRF-protected `POST` with public route isolation to prevent redirect loops.
* **Strict Upload Whitelist & Sandboxed Delivery:** File uploads strictly limited to safe image and document extensions (`.jpg`, `.jpeg`, `.png`, `.webp`, `.pdf`). Static file delivery `/static/uploads/...` enforces `Content-Security-Policy: default-src 'none'; sandbox` and `X-Content-Type-Options: nosniff`.
* **Complete XSS Neutralization:** Dynamic table rendering and modal DOM construction across all frontend modules implement HTML entity escaping (`escapeHtml`).
* **Staff & Operator Management with Self-Service Password Change:** Full administrative panel (`/usuarios`) for administrators to manage accounts and credentials. In addition, all authenticated operators have direct access to a dedicated self-service "Change Password" modal (`/api/perfil/alterar-senha`) directly from the sidebar and mobile header.
* **Internal Accountability & Audit Trail:** Automatic tracking of which staff member created contracts, marked payments as received, cancelled transactions, conducted vehicle inspections, or deleted user accounts.

### 🛡️ 10. Production WSGI Architecture, Concurrency & High Performance
* **Zero N+1 Query Architecture:** Dashboard metrics and financial aggregations execute via direct SQL aggregates (`func.sum`, `func.count`) and strategic `joinedload` eager-loading for blazing fast response times.
* **SQLite WAL Mode & Concurrency:** Database connection configured with `PRAGMA journal_mode = WAL;`, `PRAGMA synchronous = NORMAL;`, 30s busy timeout, and enforced relational integrity (`foreign_keys = ON`) for lock-free concurrent reads during background writes.
* **Strategic Database Indexes:** Foreign keys, filter columns (`id_cliente`, `placa`, `status`, `data_vencimento`, `vencimento_mot`, `vencimento_tax`), and claim indexes (`claim_number`, `empresa_parceira`, `placa`) are pre-indexed for high scalability.
* **Multi-Worker Concurrency & Scheduler Isolation:** Multi-worker process isolation via `fcntl.flock` on `.scheduler.lock` combined with database-backed atomic conditional update locks (`JobExecutionLock`) ensuring background billing executes exactly once per day across multiple WSGI workers at **01:00 AM London Time**.
* **Financial Deduplication & Audit Tool:** Standalone CLI tool (`cleanup_duplicate_charges.py`) and administrative endpoint to detect, inspect (dry-run), and safely clean up duplicate pending weekly charges without ever affecting paid transactions or deposits.
* **Dual WSGI Production Server:** Configured with `Waitress` for multi-threaded Windows/Local deployment and `Gunicorn` with `Procfile` and `gunicorn_config.py` for cloud Linux deployments (GCP, AWS, Render, Railway).
* **Point-in-Time Backups & Disaster Recovery:** Automated utilities for snapshot archives (`backup.py`), database restore (`restore.py`), and demo data seeding (`seed_data.py`).

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, Flask 3.0, Flask-Login, Flask-SQLAlchemy, SQLAlchemy 2.0 |
| **WSGI Servers** | Waitress (Windows/Local Multi-Threaded) & Gunicorn (Linux/Cloud Multi-Worker) |
| **Databases** | PostgreSQL (Production) & SQLite 3 (Development/Local) |
| **Scheduler** | APScheduler (Background task runner for automated rent billing) |
| **Security** | CSRF Protection, HTTP Hardening Headers, Werkzeug Password Hashing |
| **Frontend** | Vanilla HTML5, Modern CSS (Glassmorphism design system), JavaScript ES6+ |
| **Client Compression** | Browser Image Compression (HTML5 Canvas & Web Workers) |
| **Image Processing** | Pillow (PIL) |
| **PWA** | Web App Manifest, Apple Mobile Web App tags, Touch Icons |

---

## 🚀 Getting Started

### Prerequisites
* Python 3.10 or higher installed.
* Git installed.

### 1. Clone the Repository
```bash
git clone https://github.com/tmuniz570/vehicle-rental-management.git
cd vehicle-rental-management
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment (.env)
Copy the example environment file:
```bash
copy .env.example .env
```
*(Optionally adjust `SECRET_KEY` or `DATABASE_URL` in `.env`)*

### 5. Populate Demo / Seed Data (Optional)
To test the platform with realistic sample motorbikes, customers, and active agreements:
```bash
python seed_data.py
```

### 6. Run the Application

**Development Mode:**
```bash
python app.py
```

**Production Mode (Waitress Multi-Threaded WSGI):**
```bash
python wsgi.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

### 🔑 Default Credentials (Initial Master Admin)
* **Email:** `tmuniz570@gmail.com`
* **Password:** `Admin123!`

---

## 📱 Testing Remotely on Mobile (4G / 5G)

To access and test the app on your mobile device outside the local Wi-Fi network using Cloudflare Tunnel (HTTPS is required for mobile camera permissions and PWA):

1. Install `cloudflared` (Windows):
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. Start the tunnel while the server is running:
   ```powershell
   cloudflared tunnel --url http://127.0.0.1:5000
   ```
3. Open the generated `https://xxxx.trycloudflare.com` URL in your smartphone's browser.
4. **Install as App:**
   - **iOS (Safari):** Tap Share -> *Add to Home Screen*.
   - **Android (Chrome):** Tap Menu (3 dots) -> *Install App* or *Add to Home Screen*.

---

## 📂 Project Structure

```text
FF Motors APP/
├── app.py                     # Main Flask application, routes & API endpoints
├── wsgi.py                    # Production WSGI server runner (Waitress / Multi-threaded)
├── gunicorn_config.py         # Production Gunicorn server config for Linux cloud deployment
├── Procfile                   # Cloud PaaS entrypoint (Render, Railway, Heroku)
├── cleanup_duplicate_charges.py# CLI audit and cleanup tool for duplicate pending weekly charges
├── cleanup_uploads.py         # Automated media orphan purger and disk space cleanup
├── database.py                # Database models (User, Clients, Motos, Contracts, Inspections, Claims, Transactions)
├── backup.py                  # Automated database & asset backup utility
├── restore.py                 # Restoration utility for backup archives
├── reset_data.py              # Development data wipe utility
├── seed_data.py               # Demo data seeder for immediate testing
├── requirements.txt           # Production Python dependencies
├── .env.example               # Template environment configuration
├── CHANGELOG.md               # Detailed history of releases and changes
├── docs/                      # Architectural and operational documentation
│   ├── DEPLOY_E_BANCO_DE_DADOS.md # Zero-downtime deploy & database migration manual
│   └── plano_claims_modular.md   # Claims module architecture and permissions design
├── tests/
│   ├── test_concurrency_and_deduplication.py# Tests for multi-worker concurrency, idempotency & cleanup
│   ├── test_motos_v5c_trackers.py      # Tests for V5C document management & GPS trackers
│   └── test_vendas_contratos.py        # Automated tests for sales workflow, extras & insurance rules
├── static/
│   ├── css/
│   │   └── styles.css         # Glassmorphism design system & responsive rules
│   ├── js/
│   │   ├── app_shared.js      # Global layout, sorting & universal CSRF fetch interceptor
│   │   ├── claims.js          # Claims lifecycle, sorting, pagination & period filter logic
│   │   ├── detalhe_contrato.js# Contract ledger, modal accounting & inspection handling
│   │   ├── financeiro.js      # Financial transactions filtering & payment modals
│   │   ├── motos.js           # Fleet management logic & maintenance triggers
│   │   ├── usuarios.js        # Modular permissions, accounts & audit log timeline scripts
│   │   └── vistorias_lista.js # Inspection gallery & photo previews
│   ├── images/                # Brand assets (logo, icons)
│   ├── uploads/               # Stored inspection photos & client documents (.gitkeep)
│   └── manifest.json          # PWA progressive web app configuration
└── templates/
    ├── layout.html            # Base master layout with modular permissions sidebar
    ├── login.html             # Glassmorphism dark authentication screen
    ├── index.html             # Executive operational dashboard (filtered by module access)
    ├── claims.html            # Claims & Storage management (insurance claims & yard storage)
    ├── claim_invoice.html     # Dedicated printable Storage Invoice template
    ├── usuarios.html          # User management & audit log dashboard
    ├── contratos.html         # Contracts list & status filtering
    ├── novo_contrato.html     # Agreement wizard (Rentals, Full Sales & Instalments with Extras)
    ├── detalhe_contrato.html  # Comprehensive agreement view & financial statement
    ├── contrato_venda_print.html # Printable vehicle sale agreement template
    ├── financeiro.html        # Central finance statement & transaction ledger
    ├── relatorio_vencidos.html# Fleet-wide overdue receivables & collection hub
    ├── motos.html             # Fleet inventory & maintenance board
    ├── vistorias_lista.html   # Vehicle inspection records & photo history
    ├── recibo.html            # Branded payment receipt printable template
    ├── 404.html               # Modern dark-mode 404 Page Not Found template
    └── 500.html               # Modern dark-mode 500 Internal Error template
```

---

## 🔒 Intellectual Property & License

**Copyright © 2026 Thiago Brandão. All Rights Reserved.**

This software, its source code, database architecture, design, and associated assets are the sole and exclusive intellectual property of **Thiago Brandão**.

* **Portfolio & Showcase Only:** This repository is published strictly for demonstration and professional portfolio evaluation purposes.
* **No Commercial Use:** You may **not** copy, modify, distribute, sell, host, fork, or use this software (in whole or in part) for commercial purposes, business operations, or production deployment without prior explicit written authorization from the author.
* **No Derivative Works:** Creation of derivative works or reproduction of the business logic is strictly prohibited.

For business inquiries or licensing requests, please contact **Thiago Brandão** at **tmuniz570@gmail.com**.

---

<div align="center">
  <sub>Designed and Developed by <strong>Thiago Brandão</strong> (<a href="mailto:tmuniz570@gmail.com">tmuniz570@gmail.com</a>). All rights reserved.</sub>
</div>
