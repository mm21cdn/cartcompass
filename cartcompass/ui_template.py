"""Fresh Grocery Theme (#F4F7F4 / #FFFFFF / #E2EFE2 / #15803D / #12532D) HTML5/CSS/JS UI for CartCompass UK."""

HTML_UI_PAGE = """<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CartCompass UK — Eastergate 20km &amp; Online Grocery Price Optimizer (£ GBP)</title>
  <meta name="description" content="Paste your weekly grocery list, compare all supermarkets within a 20km radius of Eastergate, West Sussex, UK (Tesco, Sainsbury's, Lidl, Costco, Waitrose) alongside online shops (Amazon, Grape Tree, Whole Food Earth), and evaluate loyalty membership savings in GBP (£)." />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400..700;1,9..40,400..600&family=Fraunces:opsz,wght@9..144,600;9..144,700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      /* Fresh Grocery Palette Requested by User */
      --bg-canvas: #F4F7F4;
      --bg-surface: #FFFFFF;
      --bg-elevated: #EBF3EB;
      --border-subtle: #E2EFE2;
      --accent-primary: #15803D;
      --accent-primary-hover: #126B32;
      --accent-soft-bg: #E6F4EA;
      --heading-strong: #12532D;
      --text-primary: #12532D;
      --text-secondary: #2F5C3F;
      --text-muted: #557962;
      --accent-amber: #B45309;
      --accent-amber-bg: #FEF3C7;
      --accent-online: #0F766E;
      --accent-online-bg: #CCFBF1;
      --accent-coral: #B91C1C;
      --shadow-card: 0 4px 18px -2px rgba(18, 83, 45, 0.06), 0 1px 4px -1px rgba(18, 83, 45, 0.04);
      --radius-md: 12px;
      --radius-lg: 16px;
      --font-serif: 'Fraunces', Georgia, serif;
      --font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background-color: var(--bg-canvas);
      color: var(--text-primary);
      font-family: var(--font-sans);
      line-height: 1.55;
      -webkit-font-smoothing: antialiased;
    }

    h1, h2, h3, h4, .panel-title, .site-title, .winner-headline {
      color: var(--heading-strong);
    }

    /* Fresh Grocery Header */
    header.site-header {
      background-color: var(--bg-surface);
      color: var(--heading-strong);
      padding: 1.15rem 2rem;
      border-bottom: 2px solid var(--border-subtle);
      box-shadow: 0 2px 10px rgba(18, 83, 45, 0.04);
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 1rem;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 0.9rem;
    }

    .brand-emblem {
      width: 44px;
      height: 44px;
      border-radius: 10px;
      background: var(--accent-primary);
      border: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-family: var(--font-mono);
      color: #FFFFFF;
      font-size: 0.92rem;
    }

    h1.site-title {
      font-family: var(--font-serif);
      font-size: 1.42rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--heading-strong);
    }

    .site-subtitle {
      font-size: 0.84rem;
      color: var(--text-secondary);
    }

    .header-meta {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .status-chip {
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      color: var(--heading-strong);
      padding: 0.38rem 0.78rem;
      border-radius: 999px;
      font-size: 0.78rem;
      font-family: var(--font-mono);
      font-weight: 600;
    }

    main.workspace-container {
      max-width: 1440px;
      margin: 0 auto;
      padding: 1.5rem 1.75rem 3rem;
      display: grid;
      grid-template-columns: 410px 1fr;
      gap: 1.5rem;
      align-items: start;
    }

    @media (max-width: 1080px) {
      main.workspace-container {
        grid-template-columns: 1fr;
      }
    }

    .panel-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-card);
      padding: 1.35rem;
      margin-bottom: 1.25rem;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 0.65rem;
      border-bottom: 1px solid var(--border-subtle);
      gap: 0.5rem;
    }

    .panel-title {
      font-family: var(--font-serif);
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--heading-strong);
    }

    .badge-tag {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 600;
      padding: 0.22rem 0.58rem;
      border-radius: 6px;
      background: var(--accent-soft-bg);
      color: var(--accent-primary);
      border: 1px solid var(--border-subtle);
    }

    .badge-online {
      background: var(--accent-online-bg);
      color: var(--accent-online);
      border: 1px solid #99F6E4;
    }

    .badge-amber {
      background: var(--accent-amber-bg);
      color: var(--accent-amber);
    }

    .field-group {
      margin-bottom: 0.85rem;
    }

    .field-label {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--heading-strong);
      margin-bottom: 0.35rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .input-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.6rem;
    }

    input[type="text"],
    input[type="number"],
    select,
    textarea {
      width: 100%;
      padding: 0.6rem 0.75rem;
      border-radius: 8px;
      border: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      color: var(--heading-strong);
      font-family: var(--font-sans);
      font-size: 0.9rem;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }

    input[type="checkbox"] {
      accent-color: #15803D;
      width: 16px;
      height: 16px;
      cursor: pointer;
    }

    textarea#paste-grocery-list-textarea {
      font-family: var(--font-mono);
      font-size: 0.83rem;
      line-height: 1.5;
      min-height: 215px;
      resize: vertical;
      background: var(--bg-surface);
    }

    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: var(--accent-primary);
      box-shadow: 0 0 0 3px rgba(21, 128, 61, 0.16);
    }

    .btn {
      cursor: pointer;
      border: none;
      border-radius: 8px;
      font-family: var(--font-sans);
      font-weight: 600;
      font-size: 0.9rem;
      padding: 0.65rem 1rem;
      transition: all 0.16s ease;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 0.45rem;
    }

    .btn-primary {
      background: #15803D;
      color: #FFFFFF;
      width: 100%;
      padding: 0.84rem 1.2rem;
      font-size: 0.95rem;
      box-shadow: 0 3px 12px rgba(21, 128, 61, 0.24);
    }

    .btn-primary:hover {
      background: var(--accent-primary-hover);
      transform: translateY(-1px);
    }

    .btn-secondary {
      background: var(--bg-canvas);
      color: var(--heading-strong);
      border: 1px solid var(--border-subtle);
    }

    .btn-secondary:hover {
      background: var(--bg-elevated);
    }

    .btn-sm {
      padding: 0.32rem 0.65rem;
      font-size: 0.76rem;
    }

    .staples-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 0.38rem;
      margin-bottom: 0.85rem;
    }

    .staple-chip {
      font-size: 0.74rem;
      padding: 0.22rem 0.55rem;
      border-radius: 999px;
      background: var(--accent-soft-bg);
      color: var(--accent-primary);
      border: 1px solid var(--border-subtle);
      cursor: pointer;
      font-weight: 600;
      transition: background 0.15s;
    }

    .staple-chip:hover {
      background: #D1EBD8;
    }

    .loyalty-wallet-grid {
      display: flex;
      flex-direction: column;
      gap: 0.45rem;
      margin-top: 0.4rem;
    }

    .loyalty-checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.55rem;
      font-size: 0.82rem;
      padding: 0.42rem 0.6rem;
      border-radius: 7px;
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      color: var(--heading-strong);
      cursor: pointer;
    }

    /* Fresh Grocery Hero Card (#FFFFFF surface, #E2EFE2 border, #12532D strong heading, #15803D accents) */
    .winner-banner {
      background: var(--bg-surface);
      color: var(--heading-strong);
      border: 2px solid #15803D;
      border-radius: var(--radius-lg);
      padding: 1.5rem;
      margin-bottom: 1.35rem;
      box-shadow: var(--shadow-card);
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 1.25rem;
      align-items: center;
    }

    @media (max-width: 820px) {
      .winner-banner {
        grid-template-columns: 1fr;
      }
    }

    .winner-kicker {
      font-family: var(--font-mono);
      font-size: 0.76rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: #15803D;
      margin-bottom: 0.35rem;
    }

    .winner-headline {
      font-family: var(--font-serif);
      font-size: 1.52rem;
      margin-bottom: 0.5rem;
      color: #12532D;
    }

    .winner-summary-text {
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.52;
    }

    .winner-metrics-box {
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1rem 1.15rem;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 0.75rem;
    }

    .metric-stat-label {
      font-size: 0.73rem;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .metric-stat-value {
      font-family: var(--font-mono);
      font-size: 1.3rem;
      font-weight: 700;
      color: #15803D;
    }

    .store-cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
      gap: 1rem;
      margin-bottom: 1.25rem;
    }

    .store-quote-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.1rem;
      position: relative;
    }

    .store-quote-card.best-choice {
      border: 2px solid #15803D;
      background: #FAFDFA;
    }

    .store-rank-ribbon {
      display: inline-block;
      font-family: var(--font-mono);
      font-size: 0.71rem;
      font-weight: 700;
      padding: 0.2rem 0.55rem;
      border-radius: 5px;
      margin-bottom: 0.5rem;
      background: var(--bg-canvas);
      color: var(--heading-strong);
      border: 1px solid var(--border-subtle);
    }

    .store-quote-card.best-choice .store-rank-ribbon {
      background: #15803D;
      color: #FFFFFF;
      border-color: #15803D;
    }

    .price-comparison-row {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin: 0.65rem 0;
      padding: 0.55rem 0.7rem;
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
    }

    .price-big {
      font-family: var(--font-mono);
      font-size: 1.25rem;
      font-weight: 700;
      color: #15803D;
    }

    .price-strike {
      font-family: var(--font-mono);
      font-size: 0.85rem;
      text-decoration: line-through;
      color: var(--text-muted);
    }

    .loyalty-verdict-box {
      margin-top: 0.65rem;
      padding: 0.65rem 0.75rem;
      border-radius: 8px;
      font-size: 0.81rem;
      background: var(--accent-soft-bg);
      color: var(--heading-strong);
      border-left: 3px solid #15803D;
    }

    .data-table-wrapper {
      overflow-x: auto;
    }

    table.comparison-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.84rem;
    }

    table.comparison-table th,
    table.comparison-table td {
      padding: 0.65rem 0.75rem;
      text-align: left;
      border-bottom: 1px solid var(--border-subtle);
    }

    table.comparison-table th {
      background: var(--bg-canvas);
      font-weight: 700;
      color: var(--heading-strong);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .mono-cell {
      font-family: var(--font-mono);
    }

    .item-qty-pill {
      font-family: var(--font-mono);
      font-size: 0.73rem;
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      padding: 0.14rem 0.44rem;
      border-radius: 5px;
      color: var(--text-secondary);
      margin-inline-start: 0.4rem;
    }

    .two-col-subgrid {
      display: grid;
      grid-template-columns: 1fr 1.15fr;
      gap: 1.25rem;
      margin-bottom: 1.25rem;
    }

    @media (max-width: 920px) {
      .two-col-subgrid {
        grid-template-columns: 1fr;
      }
    }

    .history-list {
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
      max-height: 320px;
      overflow-y: auto;
    }

    .history-card {
      padding: 0.7rem 0.85rem;
      border-radius: 9px;
      border: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 0.75rem;
    }

    .history-card:hover {
      border-color: #15803D;
      background: var(--bg-canvas);
    }

    .trace-span-row {
      display: grid;
      grid-template-columns: 245px 1fr 80px;
      gap: 0.75rem;
      align-items: center;
      padding: 0.42rem 0.6rem;
      border-bottom: 1px solid var(--border-subtle);
      font-family: var(--font-mono);
      font-size: 0.76rem;
    }

    .trace-bar-track {
      height: 10px;
      background: var(--bg-canvas);
      border: 1px solid var(--border-subtle);
      border-radius: 999px;
      overflow: hidden;
      position: relative;
    }

    .trace-bar-fill {
      height: 100%;
      background: #15803D;
      border-radius: 999px;
    }
  </style>
</head>
<body>
  <header class="site-header">
    <div class="brand-group">
      <div class="brand-emblem">£20KM</div>
      <div>
        <h1 class="site-title">CartCompass UK — Eastergate 20km &amp; Online Grocery Optimizer</h1>
        <p class="site-subtitle">Eastergate, West Sussex (50.845561, -0.643677) &bull; Tesco, Sainsbury's, Lidl, Costco + Amazon, Grape Tree &amp; Whole Food Earth</p>
      </div>
    </div>
    <div class="header-meta">
      <span class="status-chip" id="header-radius-chip">&#10003; Radius &le; 20.0 km + Online UK</span>
      <span class="status-chip" id="header-history-count-chip">Saved Weekly Lists: 0</span>
      <span class="status-chip" id="header-currency-chip">Currency: GBP (£)</span>
    </div>
  </header>

  <main class="workspace-container">
    <!-- LEFT COLUMN: Paste-in Grocery List, Eastergate 20km + Online Toggle, UK Loyalty Wallet & Saved Runs -->
    <aside aria-label="Paste Grocery List and UK Loyalty Controls">
      <section class="panel-card" id="shopping-list-builder-panel">
        <div class="panel-header">
          <h2 class="panel-title">1. Paste Weekly Grocery List</h2>
          <button type="button" class="btn btn-secondary btn-sm" id="reset-new-list-btn" title="Load another sample UK weekly list">+ Next Weekly List</button>
        </div>

        <div class="field-group">
          <label class="field-label" for="new-list-title-input">
            <span>Weekly List Title (Saved to Memory on Run)</span>
          </label>
          <input type="text" id="new-list-title-input" value="Week of 23 Sep — Eastergate Family & Wholefood Shop" placeholder="e.g. Week of 30 Sep — Weekly Shop" />
        </div>

        <div class="field-group">
          <label class="field-label" for="paste-grocery-list-textarea">
            <span>Paste Full Grocery List (One Item Per Line)</span>
            <span class="badge-tag" id="parsed-item-count-badge">9 items</span>
          </label>
          <textarea id="paste-grocery-list-textarea" placeholder="Paste your entire weekly grocery list here, e.g.:&#10;2x Semi-Skimmed Milk 2L&#10;12 Free-Range Large Eggs&#10;1.5kg British Chicken Breast&#10;1 Sourdough Loaf&#10;500g Raw Almonds &amp; Chia Seeds">2x British Semi-Skimmed Milk 2L
1 dozen British Free-Range Large Eggs
1.5kg British Chicken Breast Fillets
1 Artisan White Sourdough Bloomer
1.5kg Sussex Braeburn Apples
1 pack Rich Roast Arabica Coffee 400g
1L Extra Virgin Olive Oil
2 packs Greek Style Natural Yogurt
1 pack Raw Almonds, Walnuts & Chia Seeds 500g</textarea>
          <p style="font-size:0.76rem; color:var(--text-muted); margin-top:0.35rem;">
            Paste any multi-line grocery list — automatically matches local supermarket &amp; specialist wholefood SKUs.
          </p>
        </div>

        <div class="field-group">
          <span class="field-label">Click to Append Recurring Staples from Memory</span>
          <div class="staples-bar" id="frequent-staples-container"></div>
        </div>

        <button type="button" class="btn btn-primary" id="run-optimization-btn">
          &#10003; Save Pasted Weekly List &amp; Optimize (£ GBP)
        </button>
      </section>

      <section class="panel-card" id="location-and-loyalty-panel">
        <div class="panel-header">
          <h2 class="panel-title">2. UK Postcode Reset (20km Search) &amp; Loyalty</h2>
          <span class="badge-tag" id="active-postcode-badge">PO20 3SJ</span>
        </div>

        <div class="field-group" style="background:var(--bg-canvas); padding:0.75rem; border-radius:10px; border:1px solid var(--border-subtle);">
          <label class="field-label" for="postcode-input">
            <span>Enter UK Postcode to Reset Location &amp; 20km Search</span>
          </label>
          <div style="display:grid; grid-template-columns:1fr auto; gap:0.5rem; margin-bottom:0.45rem;">
            <input type="text" id="postcode-input" value="PO20 3SJ" placeholder="e.g. PO20 3SJ, RH12 1HQ, BN1 4GQ, SW1A 1AA" style="font-family:var(--font-mono); font-weight:700; text-transform:uppercase;" />
            <button type="button" class="btn btn-primary" id="btn-reset-postcode" style="width:auto; padding:0.6rem 0.95rem; font-size:0.82rem; white-space:nowrap;">
              &#10003; Reset Postcode &amp; 20km Search
            </button>
          </div>
          <div class="staples-bar" style="margin-bottom:0.35rem;">
            <button type="button" class="staple-chip postcode-preset-chip" data-postcode="PO20 3SJ">PO20 3SJ Eastergate (Home)</button>
            <button type="button" class="staple-chip postcode-preset-chip" data-postcode="PO19 1RD">PO19 1RD Chichester</button>
            <button type="button" class="staple-chip postcode-preset-chip" data-postcode="RH12 1HQ">RH12 1HQ Horsham</button>
            <button type="button" class="staple-chip postcode-preset-chip" data-postcode="BN1 4GQ">BN1 4GQ Brighton</button>
            <button type="button" class="staple-chip postcode-preset-chip" data-postcode="SW1A 1AA">SW1A 1AA London</button>
          </div>
          <div id="postcode-status-note" style="font-size:0.76rem; color:var(--accent-primary); font-weight:600;">
            Active Origin: Home (Eastergate, West Sussex, UK — PO20 3SJ) [50.845561, -0.643677]
          </div>
        </div>

        <div class="field-group">
          <label class="field-label" for="location-preset-select">Resolved Address &amp; Coordinates</label>
          <select id="location-preset-select">
            <option value="50.845561,-0.643677,Home (Eastergate, West Sussex, UK),PO20 3SJ" selected>Home — Eastergate, West Sussex, UK (PO20 3SJ)</option>
            <option value="50.836500,-0.779200,Chichester, West Sussex, UK (PO19 1RD),PO19 1RD">Chichester City Centre (PO19 1RD)</option>
            <option value="51.063200,-0.326200,Horsham Town Centre, West Sussex, UK (RH12 1HQ),RH12 1HQ">Horsham Town Centre (RH12 1HQ)</option>
            <option value="50.822500,-0.137200,Brighton, East Sussex, UK (BN1 4GQ),BN1 4GQ">Brighton, East Sussex (BN1 4GQ)</option>
            <option value="51.501400,-0.141900,Westminster, Central London, UK (SW1A 1AA),SW1A 1AA">Central London (SW1A 1AA)</option>
          </select>
        </div>

        <div class="input-row field-group">
          <div>
            <label class="field-label" for="user-lat-input">Latitude</label>
            <input type="number" id="user-lat-input" value="50.845561" step="0.000001" />
          </div>
          <div>
            <label class="field-label" for="user-lon-input">Longitude</label>
            <input type="number" id="user-lon-input" value="-0.643677" step="0.000001" />
          </div>
        </div>

        <div class="input-row field-group">
          <div>
            <label class="field-label" for="radius-km-input">Physical Radius (km)</label>
            <input type="number" id="radius-km-input" value="20.0" min="2" max="50" step="1" />
          </div>
          <div style="display:flex; align-items:flex-end;">
            <label class="loyalty-checkbox-label" style="width:100%; margin-bottom:1px;">
              <input type="checkbox" id="include-online-shops-checkbox" checked />
              <span><strong>Include Online Shops</strong> (Amazon, Grape Tree, Whole Food Earth)</span>
            </label>
          </div>
        </div>

        <div class="field-group">
          <span class="field-label">Your Active Loyalty &amp; Online Memberships</span>
          <div class="loyalty-wallet-grid" id="loyalty-wallet-checkboxes">
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-TESCO-CLUBCARD" checked />
              <span><strong>Tesco Clubcard</strong> (Active Member — Free Tier)</span>
            </label>
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-SAINSBURYS-NECTAR" checked />
              <span><strong>Sainsbury's Nectar</strong> (Active Member — Free Tier)</span>
            </label>
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-LIDL-PLUS" checked />
              <span><strong>Lidl Plus</strong> (Active Member — Free App Tier)</span>
            </label>
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-COSTCO-GOLDSTAR" checked />
              <span><strong>Costco Membership</strong> (Active Member — £33.60/yr Paid)</span>
            </label>
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-GRAPETREE-LOYALTY" checked />
              <span><strong>Grape Tree Loyalty Club</strong> (Online — Free Bulk Tier)</span>
            </label>
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-WHOLEFOODEARTH-REWARDS" checked />
              <span><strong>Whole Food Earth Eco-Rewards</strong> (Online — Free Tier)</span>
            </label>
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-AMAZON-PRIME" />
              <span>Amazon Prime &amp; Subscribe &amp; Save (£95/yr — Toggle to Compare)</span>
            </label>
            <label class="loyalty-checkbox-label">
              <input type="checkbox" value="LP-WAITROSE-MY" />
              <span>myWaitrose (Optional Comparison)</span>
            </label>
          </div>
        </div>
      </section>

      <section class="panel-card" id="persistent-history-panel">
        <div class="panel-header">
          <h2 class="panel-title">3. Saved Weekly Shopping Lists</h2>
          <span class="badge-tag badge-amber" id="history-badge-count">0 Runs</span>
        </div>
        <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:0.75rem;">
          Each run saves your pasted list to SQLite persistent memory. Click any past week to reload its items:
        </p>
        <div class="history-list" id="saved-shopping-lists-container"></div>
      </section>
    </aside>

    <!-- RIGHT COLUMN: Optimization Results, Online Validity Check, Hybrid Online+Regular Plan, Loyalty ROI & OTel Traces -->
    <section aria-label="UK Store and Online Optimization Results">
      <div class="winner-banner" id="winner-recommendation-banner">
        <div>
          <div class="winner-kicker" id="winner-strategy-kicker">&#10003; OPTIMAL SHOPPING STRATEGY (20KM + ONLINE VALIDITY CHECK)</div>
          <h2 class="winner-headline" id="winner-store-headline">Evaluating 20km supermarkets &amp; online shop validity...</h2>
          <p class="winner-summary-text" id="winner-executive-summary"></p>
        </div>
        <div class="winner-metrics-box">
          <div>
            <div class="metric-stat-label">Winning Net Total</div>
            <div class="metric-stat-value" id="winner-best-total-val">£0.00</div>
          </div>
          <div>
            <div class="metric-stat-label">Max Weekly Saving</div>
            <div class="metric-stat-value" id="winner-savings-val">£0.00</div>
          </div>
          <div>
            <div class="metric-stat-label">Loyalty Benefit</div>
            <div class="metric-stat-value" id="winner-loyalty-benefit-val">+£0.00/wk</div>
          </div>
          <div>
            <div class="metric-stat-label">Active Postcode</div>
            <div class="metric-stat-value" id="winner-stores-count-val">PO20 3SJ</div>
          </div>
        </div>
      </div>

      <!-- NEW: Online Shop Validity Check & "Purchase Specific Items Online + Rest from Regular 20km Shop" Card -->
      <div class="panel-card" id="online-validity-and-hybrid-plan-card" style="border: 2px solid #15803D;">
        <div class="panel-header">
          <h2 class="panel-title">&#10003; Online Shop Fulfilment Validity &amp; &ldquo;Buy Certain Items Online + Rest at Regular 20km Shop&rdquo; Plan</h2>
          <span class="badge-tag">Online Validity &amp; Split Action</span>
        </div>
        <div id="online-validity-audit-container" style="margin-bottom:1.1rem;"></div>
        <div id="online-hybrid-split-plan-container"></div>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h2 class="panel-title">Supermarket (&le; 20km Full List) &amp; Online Partial Basket Comparison (£ GBP)</h2>
          <span class="badge-tag">Full-List 20km Supermarkets Ranked #1–#5 &bull; Partial Online Retailers Flagged Below</span>
        </div>
        <div class="store-cards-grid" id="store-ranking-cards-container"></div>
      </div>

      <div class="panel-card">
        <div class="panel-header">
          <h2 class="panel-title">Loyalty &amp; Subscription Advantage Analysis (52-Week GBP £ ROI)</h2>
          <span class="badge-tag">Clubcard &bull; Nectar &bull; Lidl Plus &bull; Costco &bull; Online Rewards</span>
        </div>
        <div class="data-table-wrapper">
          <table class="comparison-table" id="loyalty-roi-comparison-table">
            <thead>
              <tr>
                <th>Store / Online Shop &amp; Scheme</th>
                <th>List Coverage</th>
                <th>Status</th>
                <th>Annual Fee</th>
                <th>Member Discount</th>
                <th>Points / Rebate</th>
                <th>Net Weekly Advantage</th>
                <th>Annual ROI</th>
                <th>Verdict</th>
              </tr>
            </thead>
            <tbody id="loyalty-roi-tbody"></tbody>
          </table>
        </div>
      </div>

      <div class="two-col-subgrid">
        <div class="panel-card">
          <div class="panel-header">
            <h2 class="panel-title">20km Postcode Radar + Online Doorstep Delivery</h2>
            <span class="badge-tag" id="radar-postcode-badge">Haversine &le; 20.0 km</span>
          </div>
          <div id="radar-svg-container" style="display:flex; justify-content:center; align-items:center; padding:0.5rem 0;"></div>
          <div id="excluded-stores-note" style="font-size:0.79rem; color:var(--text-secondary); margin-top:0.5rem;"></div>
        </div>

        <div class="panel-card">
          <div class="panel-header">
            <h2 class="panel-title">Best Single 20km Regular Supermarket Itemized Basket (£ GBP)</h2>
            <span class="badge-tag">100% Full List In-Store</span>
          </div>
          <div id="split-basket-analysis-container"></div>
          <div style="margin-top:0.8rem;">
            <div class="data-table-wrapper" style="max-height:275px; overflow-y:auto;">
              <table class="comparison-table">
                <thead>
                  <tr>
                    <th>Parsed Item &amp; Matched SKU</th>
                    <th>Category</th>
                    <th>Regular</th>
                    <th>Member</th>
                  </tr>
                </thead>
                <tbody id="itemized-basket-tbody"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <div class="panel-card" id="observability-trace-panel">
        <div class="panel-header">
          <h2 class="panel-title">Observability &amp; OpenTelemetry Trace Waterfall</h2>
          <span class="badge-tag" id="trace-id-badge">trace_id: —</span>
        </div>
        <div id="trace-spans-waterfall-container"></div>
      </div>
    </section>
  </main>

  <script>
    const gbpFmt = new Intl.NumberFormat('en-GB', {
      style: 'currency',
      currency: 'GBP',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
    const kmFmt = new Intl.NumberFormat('en-GB', {
      style: 'unit',
      unit: 'kilometer',
      unitDisplay: 'short',
      maximumFractionDigits: 2
    });

    function fmtGBP(val) {
      return gbpFmt.format(Number(val) || 0);
    }

    const samplePastedLists = [
      {
        title: "Week of 30 Sep — Wholefood Pantry & Fresh Shop",
        text: [
          "2 packs Raw Almonds, Walnuts & Chia Seeds 500g",
          "2L Extra Virgin Olive Oil",
          "2 packs Rich Roast Arabica Coffee 400g",
          "3 packs Italian Durum Wheat Penne Pasta",
          "2x British Semi-Skimmed Milk 2L",
          "1 dozen British Free-Range Large Eggs",
          "1.5kg British Chicken Breast Fillets"
        ].join("\\n")
      },
      {
        title: "Week of 07 Oct — Sunday Roast & Family Staples",
        text: [
          "1kg Scottish Atlantic Salmon Fillets",
          "2 packs Triple-Washed Baby Spinach",
          "1 pack Cathedral Vintage Mature Cheddar",
          "1 Artisan White Sourdough Bloomer",
          "1.5kg Sussex Braeburn Apples",
          "2 packs Greek Style Natural Yogurt",
          "1 pack Raw Almonds, Walnuts & Chia Seeds 500g"
        ].join("\\n")
      }
    ];
    let sampleListIndex = 0;

    function updateLineCountBadge() {
      const raw = document.getElementById('paste-grocery-list-textarea').value || '';
      const lines = raw.split(/[\\r\\n;]+/).map(s => s.trim()).filter(Boolean);
      const count = lines.length === 1 && lines[0].includes(',')
        ? lines[0].split(',').map(s => s.trim()).filter(Boolean).length
        : lines.length;
      document.getElementById('parsed-item-count-badge').textContent = `${count} ${count === 1 ? 'item' : 'items'}`;
    }

    function getSelectedLoyaltyPrograms() {
      const checkboxes = document.querySelectorAll('#loyalty-wallet-checkboxes input[type="checkbox"]');
      const active = [];
      checkboxes.forEach(cb => {
        if (cb.checked) active.push(cb.value);
      });
      return active;
    }

    function renderRadarSvg(rec) {
      const container = document.getElementById('radar-svg-container');
      const radiusKm = rec.search_radius_km || 20.0;
      const maxPlotKm = 34.0;
      const size = 295;
      const center = size / 2;
      const scale = (size / 2 - 24) / maxPlotKm;
      const r20Px = radiusKm * scale;
      const r10Px = (radiusKm / 2) * scale;
      const activePc = (rec.user_location && rec.user_location.postcode) || 'PO20 3SJ';
      document.getElementById('radar-postcode-badge').textContent = `${activePc} <= ${radiusKm} km`;

      let dotsHtml = '';
      const physicalQuotes = rec.ranked_single_stores.filter(sq => sq.store.store_type !== 'ONLINE_UK');
      const onlineQuotes = rec.ranked_single_stores.filter(sq => sq.store.store_type === 'ONLINE_UK');

      physicalQuotes.forEach((sq) => {
        const st = sq.store;
        const dLatKm = (st.coordinate.latitude - rec.user_location.latitude) * 111.32;
        const dLonKm = (st.coordinate.longitude - rec.user_location.longitude) * 111.32 * Math.cos(rec.user_location.latitude * Math.PI / 180);
        const cx = center + dLonKm * scale;
        const cy = center - dLatKm * scale;
        const isBest = sq.store.store_id === rec.best_single_store.store.store_id;
        const color = isBest ? '#15803D' : '#12532D';
        dotsHtml += `
          <circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${isBest ? 7 : 5}" fill="${color}" stroke="#FFFFFF" stroke-width="1.5" />
          <text x="${(cx + 8).toFixed(1)}" y="${(cy + 3).toFixed(1)}" font-size="9.2" font-family="JetBrains Mono" fill="#12532D" font-weight="${isBest ? '700' : '500'}">${st.chain} (${st.distance_km}km)</text>
        `;
      });

      (rec.stores_excluded_outside_radius || []).forEach(ex => {
        const angle = ex.store_id.includes('06') ? 1.08 : -0.1;
        const dist = Math.min(32.0, ex.distance_km);
        const cx = center + Math.cos(angle) * dist * scale;
        const cy = center - Math.sin(angle) * dist * scale;
        dotsHtml += `
          <circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="4.5" fill="#B91C1C" stroke="#FFFFFF" stroke-width="1.2" />
          <text x="${(cx - 65).toFixed(1)}" y="${(cy - 6).toFixed(1)}" font-size="8.5" font-family="JetBrains Mono" fill="#991B1B">${ex.name.split(' ')[0]} (${ex.distance_km}km &gt;20km)</text>
        `;
      });

      container.innerHTML = `
        <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="20km Postcode Radar Map">
          <circle cx="${center}" cy="${center}" r="${size/2 - 12}" fill="#F4F7F4" stroke="#E2EFE2" stroke-dasharray="3,3" />
          <circle cx="${center}" cy="${center}" r="${r20Px.toFixed(1)}" fill="#E6F4EA" stroke="#15803D" stroke-width="1.75" />
          <circle cx="${center}" cy="${center}" r="${r10Px.toFixed(1)}" fill="none" stroke="#86EFAC" stroke-dasharray="4,4" />
          <line x1="${center}" y1="12" x2="${center}" y2="${size-12}" stroke="#E2EFE2" stroke-width="1" />
          <line x1="12" y1="${center}" x2="${size-12}" y2="${center}" stroke="#E2EFE2" stroke-width="1" />
          <text x="${center + 4}" y="${(center - r20Px + 12).toFixed(1)}" font-size="9" font-family="JetBrains Mono" fill="#15803D" font-weight="700">20.0 km Limit (${activePc})</text>
          <circle cx="${center}" cy="${center}" r="6.5" fill="#15803D" stroke="#FFFFFF" stroke-width="2" />
          <text x="${center + 8}" y="${center - 5}" font-size="9.2" font-family="DM Sans" font-weight="700" fill="#12532D">${activePc} (+${onlineQuotes.length} Online)</text>
          ${dotsHtml}
        </svg>
      `;

      const excludedNames = (rec.stores_excluded_outside_radius || []).map(e => `${e.name} (${kmFmt.format(e.distance_km)})`).join(', ');
      const onlineNames = onlineQuotes.map(o => o.store.chain).join(', ');
      document.getElementById('excluded-stores-note').innerHTML =
        `<strong>Geospatial &amp; Online Audit (${activePc}):</strong> Evaluated <strong>${physicalQuotes.length}</strong> physical supermarkets within ${kmFmt.format(rec.search_radius_km)} of ${rec.user_location.label} PLUS <strong>${onlineQuotes.length}</strong> UK online retailers (${onlineNames || 'None'}). Excluded <strong>${(rec.stores_excluded_outside_radius || []).length}</strong> distant stores &gt;20km: ${excludedNames || 'None'}.`;
    }

    function renderOnlineValidityAndHybridPlan(rec) {
      const auditContainer = document.getElementById('online-validity-audit-container');
      const hybridContainer = document.getElementById('online-hybrid-split-plan-container');
      const audits = rec.online_validity_audit || [];
      const hp = rec.online_hybrid_plan || rec.best_split_basket;

      if (!audits.length) {
        auditContainer.innerHTML = `<p style="font-size:0.84rem; color:var(--text-secondary);">Online shops are currently disabled. Enable the checkbox in Panel 2 to check online store fulfilment validity.</p>`;
        hybridContainer.innerHTML = '';
        return;
      }

      const auditRows = audits.map(a => {
        const isFull = a.can_fulfill_entire_list;
        const statusPill = isFull
          ? `<span class="badge-tag">&#10003; SUPPORTS 100% OF LIST (${a.fulfilled_item_count}/${a.total_requested_item_count})</span>`
          : `<span class="badge-tag badge-amber">&#9888; CANNOT SUPPORT WHOLE LIST — ONLY ${a.fulfilled_item_count}/${a.total_requested_item_count} ITEMS (${a.fulfillment_coverage_pct}%)</span>`;
        const supportedHtml = (a.supported_items || []).length
          ? (a.supported_items || []).map(it => `<span class="badge-tag" style="margin:2px;">&#10003; ${it}</span>`).join(' ')
          : `<span style="font-size:0.75rem; color:var(--text-muted);">No ambient/wholefood items on current list</span>`;
        const missingHtml = (a.missing_items || []).length
          ? (a.missing_items || []).map(m => `<span class="badge-tag badge-amber" style="margin:2px;">&#10007; ${m.split(' (')[0]}</span>`).join(' ')
          : `<span class="badge-tag">&#10003; None missing</span>`;

        return `
          <div style="padding:0.8rem 0.95rem; border-radius:10px; border:1px solid var(--border-subtle); background:var(--bg-canvas); margin-bottom:0.55rem;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.4rem; margin-bottom:0.4rem;">
              <strong style="color:#12532D; font-size:0.92rem;">${a.store_name}</strong>
              ${statusPill}
            </div>
            <div style="font-size:0.79rem; color:var(--text-secondary); margin-bottom:0.4rem;">
              <strong>Can Purchase Online Here (Ambient / Wholefoods):</strong> ${supportedHtml}
            </div>
            <div style="font-size:0.79rem; color:var(--text-secondary);">
              <strong>Not Stocked Online (Fresh / Chilled — Must Buy at Regular 20km Shop):</strong> ${missingHtml}
            </div>
          </div>
        `;
      }).join('');

      auditContainer.innerHTML = `
        <div style="margin-bottom:0.5rem; font-size:0.84rem; color:#12532D; font-weight:600;">
          1. Online Retailer Fulfilment Check — Can Amazon UK, Grape Tree, or Whole Food Earth fulfill your whole list standalone?
        </div>
        ${auditRows}
      `;

      if (hp && hp.stores && hp.stores.length === 2) {
        const onlineLeg = hp.stores.find(s => s.store_type === 'ONLINE_UK') || hp.stores[0];
        const regularLeg = hp.stores.find(s => s.store_type !== 'ONLINE_UK') || hp.stores[1];

        const onlineItemsList = (onlineLeg.assigned_items || []).map(it =>
          `<li style="margin-bottom:0.25rem;"><strong>${it.requested_item}</strong> (${it.quantity} ${it.unit}) &rarr; <strong style="color:#15803D;">${fmtGBP(onlineLeg.use_loyalty ? it.loyalty_line_total : it.regular_line_total)}</strong> <span style="font-size:0.73rem; color:var(--text-muted);">(${it.promo_badge || 'Online Bulk Deal'})</span></li>`
        ).join('');

        const regularItemsList = (regularLeg.assigned_items || []).map(it =>
          `<li style="margin-bottom:0.25rem;"><strong>${it.requested_item}</strong> (${it.quantity} ${it.unit}) &rarr; <strong style="color:#12532D;">${fmtGBP(regularLeg.use_loyalty ? it.loyalty_line_total : it.regular_line_total)}</strong> <span style="font-size:0.73rem; color:var(--text-muted);">(${it.promo_badge || 'In-Store Fresh/Chilled'})</span></li>`
        ).join('');

        hybridContainer.innerHTML = `
          <div style="padding:1rem 1.1rem; border-radius:12px; border:2px solid #15803D; background:#FAFDFA;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.5rem; margin-bottom:0.55rem;">
              <div>
                <span class="badge-tag" style="background:#15803D; color:#FFFFFF;">&#10003; RECOMMENDED ACTION: BUY AMBIENT ONLINE + FRESH AT REGULAR 20KM SHOP</span>
                <h3 style="font-size:1.08rem; color:#12532D; margin-top:0.35rem;">
                  Split Purchase Plan: ${onlineLeg.store_name.replace('[ONLINE ORDER] ', '')} + ${regularLeg.store_name.replace('[REGULAR 20KM SHOP] ', '')}
                </h3>
              </div>
              <div style="text-align:right;">
                <div style="font-size:0.73rem; color:var(--text-secondary); text-transform:uppercase; font-weight:700;">100% Complete Split Total</div>
                <div style="font-family:var(--font-mono); font-size:1.35rem; font-weight:700; color:#15803D;">${fmtGBP(hp.total_cost_with_travel)}</div>
                <div style="font-size:0.74rem; color:#15803D; font-weight:600;">
                  ${hp.savings_vs_best_single_store >= 0 ? `Saves ${fmtGBP(hp.savings_vs_best_single_store)} vs Best Single Store` : `Within ${fmtGBP(Math.abs(hp.savings_vs_best_single_store))} of Best Single Store`}
                </div>
              </div>
            </div>
            <p style="font-size:0.83rem; color:var(--text-secondary); margin-bottom:0.8rem;">${hp.rationale}</p>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.85rem;">
              <div style="padding:0.8rem; background:#FFFFFF; border:1px solid #E2EFE2; border-radius:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.45rem;">
                  <strong style="color:#15803D; font-size:0.88rem;">&#10003; STEP 1: PURCHASE ONLINE (${onlineLeg.assigned_items.length} Items)</strong>
                  <span class="mono-cell" style="font-weight:700; color:#15803D;">Subtotal: ${fmtGBP(onlineLeg.subtotal)}</span>
                </div>
                <div style="font-size:0.77rem; color:var(--text-muted); margin-bottom:0.4rem;">Store: <strong>${onlineLeg.store_name.replace('[ONLINE ORDER] ', '')}</strong> (0.0 km extra driving)</div>
                <ul style="padding-left:1.1rem; font-size:0.81rem; color:var(--heading-strong);">${onlineItemsList}</ul>
              </div>
              <div style="padding:0.8rem; background:#FFFFFF; border:1px solid #E2EFE2; border-radius:10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.45rem;">
                  <strong style="color:#12532D; font-size:0.88rem;">&#10003; STEP 2: BUY REST AT REGULAR 20KM SHOP (${regularLeg.assigned_items.length} Items)</strong>
                  <span class="mono-cell" style="font-weight:700; color:#12532D;">Subtotal: ${fmtGBP(regularLeg.subtotal)}</span>
                </div>
                <div style="font-size:0.77rem; color:var(--text-muted); margin-bottom:0.4rem;">Store: <strong>${regularLeg.store_name.replace('[REGULAR 20KM SHOP] ', '')}</strong> (${kmFmt.format(regularLeg.distance_km)} away &bull; Return Fuel: ${fmtGBP(regularLeg.delivery_or_fuel_fee)})</div>
                <ul style="padding-left:1.1rem; font-size:0.81rem; color:var(--heading-strong);">${regularItemsList}</ul>
              </div>
            </div>
            ${hp.free_delivery_tip ? `<div style="margin-top:0.65rem; font-size:0.78rem; color:#15803D; font-weight:600;">&#128161; ${hp.free_delivery_tip}</div>` : ''}
          </div>
        `;
      } else {
        hybridContainer.innerHTML = '';
      }
    }

    function renderRecommendation(rec) {
      const best = rec.best_single_store;
      const sb = rec.online_hybrid_plan || rec.best_split_basket;
      const isSplitWinner = rec.winning_strategy_type === 'SPLIT_BASKET' && sb;
      const activePc = (rec.user_location && rec.user_location.postcode) || 'PO20 3SJ';

      document.getElementById('active-postcode-badge').textContent = activePc;
      document.getElementById('header-radius-chip').innerHTML = `&#10003; ${activePc} &le; ${rec.search_radius_km} km + Online`;
      document.getElementById('postcode-status-note').textContent =
        `Active Origin: ${rec.user_location.label} [${rec.user_location.latitude}, ${rec.user_location.longitude}]`;

      document.getElementById('winner-strategy-kicker').innerHTML =
        `&#10003; WINNING STRATEGY (${activePc}): ${rec.winning_strategy_type.replace('_', ' ')} — ${rec.shopping_list_title}`;
      if (isSplitWinner) {
        const pairNames = sb.stores.map(s => s.store_name.replace('[ONLINE ORDER] ', '').replace('[REGULAR 20KM SHOP] ', '')).join(' + ');
        document.getElementById('winner-store-headline').textContent =
          `Best Overall: Online + Regular 20km Split (${pairNames}) at ${fmtGBP(rec.winning_total_cost)}`;
      } else {
        document.getElementById('winner-store-headline').textContent =
          `Best Single 100%-List Supermarket: ${best.store.name} (${kmFmt.format(best.store.distance_km)})`;
      }
      document.getElementById('winner-executive-summary').textContent = rec.executive_summary;
      document.getElementById('winner-best-total-val').textContent = fmtGBP(rec.winning_total_cost);
      document.getElementById('winner-savings-val').textContent = fmtGBP(rec.max_savings_vs_worst_store);
      document.getElementById('winner-loyalty-benefit-val').textContent =
        `+${fmtGBP(best.loyalty_analysis.total_weekly_member_benefit)}/wk`;
      document.getElementById('winner-stores-count-val').textContent = activePc;

      renderOnlineValidityAndHybridPlan(rec);

      const cardsContainer = document.getElementById('store-ranking-cards-container');
      cardsContainer.innerHTML = '';
      rec.ranked_single_stores.forEach((sq, idx) => {
        const la = sq.loyalty_analysis;
        const isOnline = sq.store.store_type === 'ONLINE_UK';
        const canAll = sq.can_fulfill_entire_list !== false;
        const channelPill = isOnline
          ? `<span class="badge-tag ${canAll ? 'badge-online' : 'badge-amber'}">${canAll ? 'ONLINE (100% LIST)' : `PARTIAL ONLINE (${sq.fulfilled_item_count}/${sq.total_requested_item_count} ITEMS)`}</span>`
          : `<span class="badge-tag">${kmFmt.format(sq.store.distance_km)} from ${activePc}</span>`;
        const ribbonLabel = canAll
          ? (idx === 0 ? '&#10003; #1 FULL-LIST SUPERMARKET' : `#${idx + 1} FULL-LIST (100%)`)
          : `&#9888; PARTIAL BASKET ONLY (${sq.fulfillment_coverage_pct}%)`;
        const card = document.createElement('div');
        card.className = `store-quote-card ${idx === 0 && canAll ? 'best-choice' : ''}`;
        card.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.45rem;">
            <span class="store-rank-ribbon" style="margin-bottom:0;">${ribbonLabel}</span>
            ${channelPill}
          </div>
          <h3 style="font-size:1.03rem; margin-bottom:0.2rem; color:#12532D;">${sq.store.name}</h3>
          <p style="font-size:0.76rem; color:var(--text-muted); margin-bottom:0.35rem;">${sq.store.address}</p>
          <div style="font-size:0.75rem; padding:0.38rem 0.55rem; border-radius:6px; background:${canAll ? 'var(--accent-soft-bg)' : 'var(--accent-amber-bg)'}; color:${canAll ? '#15803D' : 'var(--accent-amber)'}; font-weight:600; margin-bottom:0.45rem;">
            ${canAll ? `&#10003; Can fulfill all ${sq.total_requested_item_count} items standalone` : `&#9888; Cannot fulfill whole list (${sq.missing_items.length} fresh/chilled items missing) — use in Online + Regular Split above`}
          </div>
          <div class="price-comparison-row">
            <div>
              <div style="font-size:0.73rem; color:var(--text-secondary);">${canAll ? `Full List Total (inc. Fuel)` : `Subtotal for ${sq.fulfilled_item_count} Eligible Items`}</div>
              <div class="price-big">${fmtGBP(sq.effective_best_total)}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:0.73rem; color:var(--text-muted);">Non-Member</div>
              <div class="price-strike">${fmtGBP(sq.total_regular_with_travel)}</div>
            </div>
          </div>
          <div style="font-size:0.78rem; display:flex; justify-content:space-between; color:var(--text-secondary);">
            <span>Member Items: <strong>${fmtGBP(sq.loyalty_subtotal)}</strong></span>
            <span>${isOnline ? 'Delivery Fee' : 'Return Fuel'}: <strong>${fmtGBP(sq.estimated_roundtrip_fuel_cost)}</strong></span>
          </div>
          <div class="loyalty-verdict-box">
            <strong>${la.program_name}:</strong> ${la.user_already_member ? '&#10003; ACTIVE MEMBER' : (la.is_advantageous ? 'ADVANTAGEOUS' : 'NOT ADVANTAGEOUS')}<br/>
            Net Weekly Advantage: <strong>+${fmtGBP(la.net_weekly_advantage)}/wk</strong> (+${fmtGBP(la.projected_annual_net_savings)}/yr)
          </div>
        `;
        cardsContainer.appendChild(card);
      });

      const roiTbody = document.getElementById('loyalty-roi-tbody');
      roiTbody.innerHTML = '';
      rec.ranked_single_stores.forEach(sq => {
        const la = sq.loyalty_analysis;
        const canAll = sq.can_fulfill_entire_list !== false;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${sq.store.name}</strong><br/><span style="font-size:0.76rem; color:var(--text-secondary);">${la.program_name}</span></td>
          <td><span class="badge-tag ${canAll ? '' : 'badge-amber'}">${canAll ? `100% (${sq.fulfilled_item_count}/${sq.total_requested_item_count})` : `Partial (${sq.fulfilled_item_count}/${sq.total_requested_item_count})`}</span></td>
          <td><span class="badge-tag ${la.user_already_member ? '' : 'badge-amber'}">${la.user_already_member ? '&#10003; Active Member' : 'Not Enrolled'}</span></td>
          <td class="mono-cell">${fmtGBP(la.annual_membership_fee)}/yr<br/><span style="font-size:0.73rem; color:var(--text-muted);">(${fmtGBP(la.amortized_weekly_fee)}/wk eff.)</span></td>
          <td class="mono-cell" style="color:#15803D; font-weight:700;">-${fmtGBP(la.gross_weekly_loyalty_discount)}</td>
          <td class="mono-cell">-${fmtGBP(la.points_cashback_value)}</td>
          <td class="mono-cell" style="font-weight:700; color:${la.net_weekly_advantage >= 0 ? '#15803D' : 'var(--accent-coral)'};">
            ${la.net_weekly_advantage >= 0 ? '+' : ''}${fmtGBP(la.net_weekly_advantage)}/wk
          </td>
          <td class="mono-cell" style="font-weight:700;">+${fmtGBP(la.projected_annual_net_savings)}/yr</td>
          <td style="font-size:0.78rem; max-width:255px;">${la.rationale}</td>
        `;
        roiTbody.appendChild(tr);
      });

      const splitBox = document.getElementById('split-basket-analysis-container');
      splitBox.innerHTML = `
        <div style="padding:0.75rem; border-radius:8px; border:1px solid var(--border-subtle); background:var(--bg-canvas); font-size:0.81rem; color:var(--text-secondary);">
          <strong>Best 100%-In-Store Regular Supermarket:</strong> <strong style="color:#12532D;">${best.store.name}</strong> (${kmFmt.format(best.store.distance_km)} from ${activePc}) fulfills all ${best.total_requested_item_count} items in a single trip for <strong style="color:#15803D;">${fmtGBP(best.effective_best_total)}</strong>.
        </div>
      `;

      const itemTbody = document.getElementById('itemized-basket-tbody');
      itemTbody.innerHTML = '';
      best.line_items.forEach(li => {
        const isAmbient = li.item_category === 'AMBIENT_WHOLEFOOD';
        const catBadge = isAmbient
          ? `<span class="badge-tag badge-online" style="font-size:0.68rem;">Ambient / Online Eligible</span>`
          : `<span class="badge-tag" style="font-size:0.68rem;">Fresh / Chilled (20km Store)</span>`;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${li.matched_product_name}</strong> <span class="item-qty-pill">${li.quantity} ${li.unit}</span></td>
          <td>${catBadge}</td>
          <td class="mono-cell">${fmtGBP(li.regular_line_total)}</td>
          <td class="mono-cell" style="color:#15803D; font-weight:700;">${fmtGBP(li.loyalty_line_total)}</td>
        `;
        itemTbody.appendChild(tr);
      });

      renderRadarSvg(rec);

      const traceSummary = rec.trace_summary || {};
      document.getElementById('trace-id-badge').textContent = `trace_id: ${rec.trace_id}`;
      const wfContainer = document.getElementById('trace-spans-waterfall-container');
      wfContainer.innerHTML = '';
      const maxDur = Math.max(0.5, ...(traceSummary.spans || []).map(s => s.duration_ms || 0.1));
      (traceSummary.spans || []).forEach(sp => {
        const pct = Math.min(100, Math.max(6, (sp.duration_ms / maxDur) * 100));
        const row = document.createElement('div');
        row.className = 'trace-span-row';
        row.innerHTML = `
          <div style="overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${sp.operation_name}">
            ${sp.parent_span_id ? '&hookrightarrow; ' : '<strong>&bull;</strong> '}${sp.operation_name}
          </div>
          <div class="trace-bar-track">
            <div class="trace-bar-fill" style="width:${pct.toFixed(1)}%;"></div>
          </div>
          <div style="text-align:right; font-weight:600;">${sp.duration_ms.toFixed(2)} ms</div>
        `;
        wfContainer.appendChild(row);
      });
    }

    function renderHistoryAndStaples(historyList, staples) {
      document.getElementById('header-history-count-chip').textContent = `Saved Weekly Lists: ${historyList.length}`;
      document.getElementById('history-badge-count').textContent = `${historyList.length} Runs`;

      const histContainer = document.getElementById('saved-shopping-lists-container');
      histContainer.innerHTML = '';
      historyList.forEach(entry => {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.innerHTML = `
          <div>
            <div style="font-weight:700; font-size:0.86rem; color:#12532D;">${entry.title}</div>
            <div style="font-size:0.75rem; color:var(--text-secondary);">
              ${entry.item_count} items &bull; Winner: <strong>${entry.winning_store_summary}</strong>
            </div>
          </div>
          <div style="text-align:right;">
            <div class="mono-cell" style="font-weight:700; color:#15803D;">${fmtGBP(entry.winning_total_cost)}</div>
            <div style="font-size:0.71rem; color:var(--text-muted);">Saved -${fmtGBP(entry.loyalty_savings_usd)}</div>
          </div>
        `;
        card.addEventListener('click', () => {
          const lines = (entry.items || []).map(i => `${i.quantity} ${i.unit} ${i.name}`).join('\\n');
          document.getElementById('paste-grocery-list-textarea').value = lines;
          document.getElementById('new-list-title-input').value = `${entry.title} (Re-run)`;
          updateLineCountBadge();
          if (entry.recommendation) {
            renderRecommendation(entry.recommendation);
          }
        });
        histContainer.appendChild(card);
      });

      const staplesBar = document.getElementById('frequent-staples-container');
      staplesBar.innerHTML = '';
      (staples || []).slice(0, 8).forEach(st => {
        const chip = document.createElement('button');
        chip.type = 'button';
        chip.className = 'staple-chip';
        chip.textContent = `+ ${st.display_name} (${st.times_ordered}x)`;
        chip.addEventListener('click', () => {
          const ta = document.getElementById('paste-grocery-list-textarea');
          const prefix = ta.value.trim() ? ta.value.trim() + '\\n' : '';
          ta.value = `${prefix}${st.last_quantity || 1} ${st.default_unit || 'count'} ${st.display_name}`;
          updateLineCountBadge();
        });
        staplesBar.appendChild(chip);
      });
    }

    async function resetLocationByPostcode(postcodeStr) {
      const cleanPc = (postcodeStr || document.getElementById('postcode-input').value || 'PO20 3SJ').trim();
      document.getElementById('postcode-input').value = cleanPc.toUpperCase();
      const radiusKm = parseFloat(document.getElementById('radius-km-input').value) || 20.0;
      const res = await fetch('/api/postcode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ postcode: cleanPc, radius_km: radiusKm })
      });
      const data = await res.json();
      if (data.resolved_location) {
        const loc = data.resolved_location;
        document.getElementById('postcode-input').value = loc.postcode;
        document.getElementById('user-lat-input').value = loc.latitude;
        document.getElementById('user-lon-input').value = loc.longitude;
        document.getElementById('active-postcode-badge').textContent = loc.postcode;
        document.getElementById('postcode-status-note').textContent =
          `Active Origin Reset: ${loc.label} [${loc.latitude}, ${loc.longitude}]`;
      }
      await runPastedListOptimization();
    }

    async function runPastedListOptimization() {
      updateLineCountBadge();
      const postcodeVal = (document.getElementById('postcode-input').value || 'PO20 3SJ').trim();
      const pastedText = document.getElementById('paste-grocery-list-textarea').value;
      const includeOnline = document.getElementById('include-online-shops-checkbox').checked;
      const res = await fetch('/api/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: document.getElementById('new-list-title-input').value,
          postcode: postcodeVal,
          latitude: parseFloat(document.getElementById('user-lat-input').value),
          longitude: parseFloat(document.getElementById('user-lon-input').value),
          radius_km: parseFloat(document.getElementById('radius-km-input').value),
          include_online_shops: includeOnline,
          active_loyalty_programs: getSelectedLoyaltyPrograms(),
          pasted_list_text: pastedText,
          persist_run: true
        })
      });
      const data = await res.json();
      if (data.recommendation) {
        renderRecommendation(data.recommendation);
      }
      if (data.history) {
        renderHistoryAndStaples(data.history, data.frequent_staples || []);
      }
    }

    document.getElementById('paste-grocery-list-textarea').addEventListener('input', updateLineCountBadge);
    document.getElementById('include-online-shops-checkbox').addEventListener('change', runPastedListOptimization);

    document.getElementById('btn-reset-postcode').addEventListener('click', () => {
      resetLocationByPostcode(document.getElementById('postcode-input').value);
    });

    document.getElementById('postcode-input').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        resetLocationByPostcode(document.getElementById('postcode-input').value);
      }
    });

    document.querySelectorAll('.postcode-preset-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        resetLocationByPostcode(btn.getAttribute('data-postcode'));
      });
    });

    document.getElementById('reset-new-list-btn').addEventListener('click', () => {
      const sample = samplePastedLists[sampleListIndex % samplePastedLists.length];
      sampleListIndex += 1;
      document.getElementById('new-list-title-input').value = sample.title;
      document.getElementById('paste-grocery-list-textarea').value = sample.text;
      updateLineCountBadge();
    });

    document.getElementById('location-preset-select').addEventListener('change', (e) => {
      const parts = e.target.value.split(',');
      document.getElementById('user-lat-input').value = parts[0];
      document.getElementById('user-lon-input').value = parts[1];
      const pc = parts[parts.length - 1] || 'PO20 3SJ';
      document.getElementById('postcode-input').value = pc;
      resetLocationByPostcode(pc);
    });

    document.getElementById('run-optimization-btn').addEventListener('click', async () => {
      const btn = document.getElementById('run-optimization-btn');
      btn.textContent = 'Optimizing 20km Stores & Online Validity...';
      await runPastedListOptimization();
      btn.textContent = '✓ Save Pasted Weekly List & Optimize (£ GBP)';
    });

    window.addEventListener('DOMContentLoaded', runPastedListOptimization);
  </script>
</body>
</html>
"""
