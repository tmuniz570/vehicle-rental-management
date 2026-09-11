# 🏍️ FF Motors — Motorcycle Fleet & Rental Operations System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![PWA](https://img.shields.io/badge/PWA-Ready-orange?style=for-the-badge&logo=pwa&logoColor=white)
![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red?style=for-the-badge)
![Location](https://img.shields.io/badge/Location-Birmingham%2C%20UK-red?style=for-the-badge)

**A modern, mobile-first Fleet Operations, Rental Agreement, and Financial Management platform tailored for motorcycle rental businesses in the UK.**

</div>

---

## 📌 Overview

**FF Motors Management System** is an end-to-end web application developed to automate and streamline motorcycle rental operations. Built specifically to handle day-to-day motorcycle fleet management, client agreements, security deposit accounting, and digital vehicle inspections directly from the rental yard using smartphones or desktop computers.

The system features an installable **PWA (Progressive Web App)** interface with a custom **mobile bottom navigation bar**, client-side image compression for mobile cameras, automated recurring weekly rent generation, and instant receipt printing.

---

## ✨ Key Features

### 📊 1. Executive Dashboard & Fleet Allocation
* **Live KPI Counters:** Real-time visibility into total fleet, available bikes, active rentals, motorcycles in maintenance, registered customers, and expected weekly revenue.
* **Interactive Fleet Allocation Bar:** Visual percentage breakdown of available, rented, and workshop-held motorbikes.
* **Instant Overdue Alerts:** Immediate notification of late payments and actionable shortcuts.

### 🛵 2. Fleet & Vehicle Lifecycle
* **UK Registration Plate Standardization:** Dedicated plate badges (e.g., `XX10 YYY`) and status management (`Available`, `Rented`, `Maintenance`).
* **Maintenance Workflow:** One-click dispatch of motorbikes to the workshop with maintenance reason logging and quick release back to the active fleet.

### 👥 3. Customer Relationship Management
* **Driver Records:** Full tracking of client contact info, residential address, driving license (DVLA), and utility proof uploads.
* **1-Tap WhatsApp Integration:** Automatic normalization and international formatting of UK phone numbers (`+447...`) allowing instant WhatsApp chat links from any contract or customer card.

### 📋 4. Contract & Security Deposit Accounting
* **Automated Initial Billing:** Creating a contract instantly provisions Week 1 rent (due upon collection) and Week 2 recurring rent (scheduled for the client's chosen weekday payment cycle).
* **Deposit Lifecycle Management:** Security deposit holding, balance calculation, and automated deductions when damages or fines occur.
* **Contract Completion Workflow:** Return inspection mandatory review, deposit refund processing, and proof of bank transfer attachment.

### 🔍 5. Digital Mobile Inspections & Incident Logging
* **Multi-Angle Camera Capture:** Tailored for yard operators using smartphones to snap vehicle photos at check-out, return check-in, or road incidents.
* **Client-Side Image Compression:** Automatic compression via `browser-image-compression` converting high-res smartphone captures to lightweight WebP formats before upload, saving bandwidth and cloud storage.
* **High-Definition Gallery:** Inspection modals with zoomable image grids and timestamped condition logs.

### 💳 6. Financial Statements & Receipts
* **Full Contract Ledger:** Itemized breakdown of Rent, Security Deposits, Fines, and Repair charges with status tracking (`Pending`, `Paid`, `Overdue`).
* **Receipt Printing:** Printable payment confirmation receipts with branded layout, QR/ID transaction reference, and PDF-friendly styling.
* **Automated Rent Generation:** Integrated background scheduler (`APScheduler`) generating recurring rental invoices on designated weekly payment days.

### 📱 7. Mobile-First & PWA Experience
* **Native-Style Bottom Navigation:** High-usability bottom navigation bar enabled exclusively on mobile viewports (`<= 768px`) with iOS Safe Area Insets support.
* **Installable App:** Manifest configuration (`manifest.json`) and app icons allowing home screen installation on iOS (Safari) and Android (Chrome).

### 🛡️ 8. Data Security & Backup Suite
* **Point-in-Time Backups:** Automated script (`backup.py`) packaging database snapshots and asset files into compressed zip archives.
* **Disaster Recovery:** Dedicated restore script (`restore.py`) and development sanitation utility (`reset_data.py`).

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+, Flask 3.0, Flask-SQLAlchemy, SQLAlchemy 2.0 |
| **Scheduler** | APScheduler (Background task runner for automated rent billing) |
| **Database** | SQLite 3 (ACID-compliant relational database with foreign key support) |
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
git clone https://github.com/your-username/ff-motors-app.git
cd ff-motors-app
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

### 4. Populate Demo / Seed Data (Optional)
To test the platform with realistic sample motorbikes, customers, and active agreements:
```bash
python seed_data.py
```

### 5. Run the Application
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📱 Testing Remotely on Mobile (4G / 5G)

To access and test the app on your mobile device outside the local Wi-Fi network using Cloudflare Tunnel (HTTPS is required for mobile camera permissions and PWA):

1. Install `cloudflared` (Windows):
   ```powershell
   winget install Cloudflare.cloudflared
   ```
2. Start the tunnel while `app.py` is running:
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
├── database.py                # Database models (Clients, Motos, Contracts, Inspections, Transactions)
├── backup.py                  # Automated database & asset backup utility
├── restore.py                 # Restoration utility for backup archives
├── reset_data.py              # Development data wipe utility
├── seed_data.py               # Demo data seeder for immediate testing
├── requirements.txt           # Production Python dependencies
├── static/
│   ├── css/
│   │   └── styles.css         # Glassmorphism design system & responsive rules
│   ├── js/
│   │   ├── app_shared.js      # Global layout scripts
│   │   ├── detalhe_contrato.js# Contract ledger, modal accounting & inspection handling
│   │   ├── financeiro.js      # Financial transactions filtering & payment modals
│   │   ├── motos.js           # Fleet management logic & maintenance triggers
│   │   └── vistorias_lista.js # Inspection gallery & photo previews
│   ├── images/                # Brand assets (logo, icons)
│   ├── uploads/               # Stored inspection photos & client documents (.gitkeep)
│   └── manifest.json          # PWA progressive web app configuration
└── templates/
    ├── layout.html            # Base master layout with mobile bottom navigation
    ├── index.html             # Executive operational dashboard
    ├── contratos.html         # Contracts list & status filtering
    ├── detalhe_contrato.html  # Comprehensive agreement view & financial statement
    ├── financeiro.html        # Central finance statement & transaction ledger
    ├── motos.html             # Fleet inventory & maintenance board
    ├── vistorias_lista.html   # Vehicle inspection records & photo history
    └── recibo.html            # Branded payment receipt printable template
```

---

## 🔒 Intellectual Property & License

**Copyright © 2026 Thiago Muniz. All Rights Reserved.**

This software, its source code, database architecture, design, and associated assets are the sole and exclusive intellectual property of **Thiago Muniz**.

* **Portfolio & Showcase Only:** This repository is published strictly for demonstration and professional portfolio evaluation purposes.
* **No Commercial Use:** You may **not** copy, modify, distribute, sell, host, fork, or use this software (in whole or in part) for commercial purposes, business operations, or production deployment without prior explicit written authorization from the author.
* **No Derivative Works:** Creation of derivative works or reproduction of the business logic is strictly prohibited.

For business inquiries or licensing requests, please contact **Thiago Muniz** directly.

---

<div align="center">
  <sub>Designed and Developed by <strong>Thiago Muniz</strong>. All rights reserved.</sub>
</div>
