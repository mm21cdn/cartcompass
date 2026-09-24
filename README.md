# CartCompass UK — 20km Grocery & Loyalty Price Optimizer (`£ GBP`)

**CartCompass UK** is an agentic weekly grocery & loyalty price optimization application designed for UK shoppers (defaulting to **Eastergate, West Sussex, `PO20 3SJ`**, `50.845561, -0.643677`) with instant UK postcode location reset, a **20.0 km Haversine radius supermarket filter**, **online wholefood shop basket validity auditing** (**Amazon UK**, **Grape Tree Health Foods**, **Whole Food Earth**), and **Loyalty Membership ROI analysis** (**Tesco Clubcard**, **Sainsbury's Nectar**, **Lidl Plus**, **Costco UK**, **Waitrose**, **Morrisons**, **Asda**).

---

## Key Features

1. **UK Postcode Location Reset & 20km Haversine Search**:
   - Default origin: **`PO20 3SJ` — Home (Eastergate, West Sussex, UK)** (`50.845561, -0.643677`).
   - Enter any UK postcode (e.g., `PO20 3SJ`, `PO19 1RD`, `RH12 1HQ`, `BN1 4GQ`, `SW1A 1AA`) to reset your home coordinates and trigger a fresh $\le 20.0\text{ km}$ supermarket search.
2. **Paste-In Multi-Line Grocery List Parser**:
   - Paste an entire weekly shopping list at once (e.g., `2x British Semi-Skimmed Milk 2L`, `1 dozen Free-Range Large Eggs`, `1.5kg British Chicken Breast Fillets`, `1 pack Whole Almonds, Walnuts & Chia Seeds 1kg`).
   - Automatically parses quantities, UK units (`kg`, `g`, `L`, `ml`, `dozen`, `loaf`, `pack`), and normalizes item names.
3. **Online Shop Basket Validity Check (`Amazon UK`, `Grape Tree`, `Whole Food Earth`)**:
   - Audits whether online wholefood/ambient retailers can realistically fulfill your entire grocery list standalone.
   - Flags fresh/chilled items (`Milk`, `Eggs`, `Fresh Bakery Sourdough`, `Chilled Chicken Breast`, `Salmon`, `Yogurt`, `Cheddar`) as **unsupported for ambient online parcel post**, preventing partial online quotes from falsely ranking #1 as a single-store winner.
4. **"Purchase Certain Items Online + Rest from a Regular 20km Shop" Split Plan**:
   - Generates a concrete 2-step split-purchase plan (`ONLINE_PLUS_REGULAR_SHOP`):
     - **Step 1 (Purchase Online)**: Order eligible ambient/wholefood items (nuts, seeds, pasta, extra virgin olive oil, coffee) from **Whole Food Earth**, **Grape Tree**, or **Amazon UK** at bulk online member pricing (`0.0 km` extra driving).
     - **Step 2 (Buy Rest at Regular 20km Shop)**: Purchase all remaining fresh & chilled essentials from your best 20km supermarket (**Lidl**, **Tesco**, **Sainsbury's**, or **Costco**), including round-trip fuel cost (`£0.18/km`).
5. **Persistent SQLite Multi-Run Memory & OpenTelemetry-Style Tracing**:
   - Saves each weekly shopping list run in SQLite, tracks frequently ordered staples, and records hierarchical execution spans and latency metrics.

---

## Quick Start (Zero External Dependencies — Python 3.10+)

### 1. Run the Web App Server
```bash
python3 app.py --host 0.0.0.0 --port 8765
```
Then open `http://localhost:8765` in your browser.

### 2. Run a CLI Optimization Report
```bash
python3 app.py --cli --postcode "PO20 3SJ" --title "Eastergate Weekly Shop"
```

### 3. Run the Unit & Integration Test Suite
```bash
python3 -m unittest discover -s cartcompass -p "*_test.py" -v
```

---

## Project Structure

- `cartcompass/models.py` — Strongly typed domain models (`GeoCoordinate`, `GroceryStore`, `StoreBasketQuote`, `LoyaltyAdvantageAnalysis`, `SplitBasketOption`, `OptimizationRecommendation`).
- `cartcompass/tools.py` — Geospatial 20km discovery, UK postcode geocoder (`resolve_uk_postcode`), free-text pasted list parser, online shop basket validity auditor, loyalty ROI engine, and hybrid Online + Regular 20km Shop split optimizer.
- `cartcompass/memory_store.py` — Persistent SQLite storage (`user_profiles`, `shopping_lists`, `item_frequency_memory`, `sku_price_history`).
- `cartcompass/orchestrator.py` — Multi-stage optimization pipeline with OpenTelemetry-style span instrumentation.
- `cartcompass/observability.py` — Distributed trace context, span waterfall, and histogram/counter telemetry registry.
- `cartcompass/ui_template.py` — Fresh Grocery Theme (`#F4F7F4` canvas, `#FFFFFF` cards, `#E2EFE2` borders, `#15803D` primary actions, `#12532D` headings) single-page web UI.
- `cartcompass/server.py` — HTTP JSON API + Web UI server and CLI runner.
- `cartcompass/grocery_app_test.py` — Automated unit and integration tests.
