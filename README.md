# TempsBot 
## Is a Weather Bot integrated with AI ("Temps" means weather in French).

Live app: [Link](https://tempsbotai.streamlit.app/) <!-- paste your Streamlit URL -->

This repo mirrors the **top-level `app.py`** only, for review/demo.
The full project (APIs, GPT, color engine, etc.) remains private.

# TempsBot — Product Overview & Technical Document

## 1) Executive summary
**TempsBot** is a Streamlit-based web application that blends short-term weather intelligence with style guidance. It fetches current conditions and forecasts, summarizes the climate, predicts UV exposure, and recommends day-appropriate outfits with color pairings for photos. The app also offers interactive charts (hourly and 5-day), developer-friendly data tables, and one-click exports to Markdown, PDF, and PNG.

---

## 2) Core value proposition
- **Plan your day quickly:** clear climate summary and outfit guidance in one view.
- **Dress smart:** context-aware clothing and accessory tips (e.g., sunscreen, wind).
- **Visualize at a glance:** interactive graphs for hourly and multi-day trends.
- **Share & save:** export a “5-Day Outfit Plan” as Markdown, PDF, or a color grid PNG.

---

## 3) Key features

### 3.1 Climate & safety
- **Current weather summary**: temperature, humidity, conditions, and a GPT-authored human summary.
- **UV index insights**: current UVI, five-day UVI outlook, and skin-type-specific sunscreen guidance (Fitzpatrick I–VI).
- **Weather alerts**: expandable alert cards (title, sender, start/end, full text) with optional condensed view and quick download.

### 3.2 Forecasts & analytics
- **Hourly (next 24h, rolling window)**: table and interactive chart for temperature, UVI, precipitation probability (PoP), wind speed, and gusts.
- **5-day / 3-hour forecast**: table (Date/Time, Temp, Humidity, PoP%, UVI, Condition) and interactive chart.
- **Interactive series toggles**: checkbox controls to add or remove series per chart; consistent colors for each metric.
- **Timezone-corrected timestamps**: city local time with DST awareness; no double-shifting.

### 3.3 Wardrobe intelligence
- **What to wear today**: rule-based outfit proposal informed by temperature, UVI, wind, and general conditions—then enhanced with GPT phrasing.
- **Accessory tips**: context-aware additions (e.g., “hat/sunglasses under high UVI”, “windproof layer”).
- **5-day outfit & color suggestions**: HTML blocks showing suggested outfits and curated **color pairs** for aesthetically pleasing photos.
- **Click-to-copy HEX**: instant color code copying in the UI.

### 3.4 Export & sharing
- **Markdown**: single file capturing the 5-day outfit plan.
- **PDF**: professionally laid-out multi-page document with date headers and color swatch rectangles; footer branding.
- **PNG**: compact color grid (via `export_utils.color_grid_image`).

---

## 4) Data sources & APIs

| Capability | Provider | Endpoint(s) | Notes |
|---|---|---|---|
| Current weather & coordinates | OpenWeather | `/data/2.5/weather` | City→lat/lon, temp, humidity, condition |
| Hourly & UV & alerts | OpenWeather One Call v3 | `/data/3.0/onecall` | Hourly (≈48h), current UVI, daily UVI, alerts, timezone & offset |
| 5-day forecast | OpenWeather | `/data/2.5/forecast` | 5 days @ 3-hour steps; temp, humidity, wind, PoP, condition |
| GPT summaries | Local functions | `gpt_summarizer.*` | Wraps LLM calls (in your project context) |
| Outfit logic | Local functions | `wardrobe_advisor.*`, `outfit_forecast.*` | Deterministic rules + GPT phrasing |

> The app honors **units** (Metric/Imperial) from the sidebar settings.

---

## 5) UX flow

1. **User inputs**: City and Fitzpatrick skin type (I–VI); toggles for daily tips.
2. **Data fetch** (cached):
   - Current conditions + coordinates → One Call v3 for UVI, alerts, timezone.
   - 5-day forecast → merged with One Call UVI (hourly/daily) when available.
3. **Computation & summaries**:
   - GPT produces a human-friendly weather note and an outfit rationale.
   - Outfit+color suggestions generated for each forecast day.
4. **Presentation**:
   - **Climate Summary** and **What to Wear Today**.
   - **UV & Sunscreen Advice** with 5-day UVI line.
   - **Forecast** expander:
     - **Today (hourly)**: table + chart; checkbox series selection.
     - **Next 5 days**: table + chart; checkbox series selection.
   - **5-Day Outfit & Color Suggestions** with copyable HEX codes.
5. **Exports**: Markdown / PDF / PNG download buttons.

---

## 6) Architecture & modules

App.py
├─ fetch_weather() → weather_api.get_weather()
├─ fetch_forecast() → forecast_api.get_forecast()
├─ fetch_hourly() → forecast_api.get_hourly_today()
├─ cached_gpt_summary() → gpt_summarizer
├─ cached_daily_tip() → gpt_summarizer
├─ get_tz_info()/get_tz_offset → One Call v3 (timezone name + offset)
├─ PDF builder → ReportLab
└─ UI → Streamlit + Plotly

### 6.1 `weather_api.py`
- Gets current weather (for basic conditions + city name + coords).
- Calls One Call v3 for **current UVI**, **daily UVI (next 5)**, **alerts**, and **timezone** info.
- Returns a consolidated dict including `coord`, `uv_index`, `uv_next5`, `alerts`, and `uv_source`.

### 6.2 `forecast_api.py`
- Fetches the **5-day 3-hour** forecast.
- Enriches the forecast with **UVI** by merging One Call v3:
  - Uses hourly UVI where timestamps align (≈48h horizon).
  - Falls back to daily UVI (date-level) for later steps.
- Provides **hourly (next 24h local)** via One Call v3 with **local timestamps already computed** (prevents double offset).

### 6.3 Outfit & GPT modules
- `wardrobe_advisor.*` and `outfit_forecast.*` encode rule-based recommendations (temperature bands, wind, UVI).
- `gpt_summarizer.*` produces:
  - A narrative “GPT Says” weather blurb.
  - An “GPT on Your Look” paragraph.
  - Optional daily style tips per forecast day.

---

## 7) Time & timezone handling

**Why it matters:** OpenWeather timestamps are UTC. Cities can observe DST; adding a raw offset can be wrong during transitions.

- **Hourly table & chart (today)**:
  - `get_hourly_today` returns **naive local timestamps** (already converted using One Call’s `timezone_offset` at call time).
  - **App never adds the offset again** → prevents double shifting.
- **5-day forecast table & chart**:
  - App reads 5-day UTC timestamps and converts them using the **timezone name** from One Call (e.g., `Europe/London`), then drops tz info for display. This remains **DST-safe**.

---

## 8) Interactivity & visualization

### 8.1 Tables
- **Hourly**: `datetime`, `temp`, `uvi`, `pop`, `wind_speed`, `wind_gust`.
- **5-day**: `datetime`, `temperature`, `humidity`, `pop`, `uvi`, `condition`.
  - PoP displayed as a **percentage**; temperature and humidity are nicely rounded.

### 8.2 Charts
- **Consistent series colors** across views (e.g., Temp = red, UVI = orange, PoP% = blue).
- **Dual-axis strategy**:
  - Left y-axis: Temperature (and Winds in hourly).
  - Right y-axis: Percentage scale for **PoP%** and **UVI** (UVI scaled to 0–100% using dynamic baseline set to `max(11, daily max)`).
- **Checkbox series selectors**:
  - **Hourly:** Temp, PoP%, UVI, Wind speed, Wind gust.
  - **5-day:** Temp, Humidity%, PoP%, UVI.
  - The **Condition** column is included in the table but never plotted (per requirement).
- Quality of life:
  - Hover labels, light grid, sticky spikes, range slider (hourly), unified hover mode.

---

## 9) Exports

- **Markdown**: human-readable 5-day outfit plan.
- **PDF**: paginated layout with date headings and color swatch rectangles; footer branding.
- **PNG**: compact color grid (via `export_utils.color_grid_image`).

---

## 10) Reliability, performance, and caching

- **HTTP resilience**: retries with exponential backoff (handles 429/5xx).
- **Caching**: `@st.cache_data` on weather/forecast/hourly/GPT summaries to reduce latency and API calls (typical TTL: 10 minutes).
- **Graceful degradation**:
  - If UVI enrichment fails, the app continues with weather and forecast data.
  - UI shows friendly warnings for missing data (“Forecast data unavailable”, etc.).

---

## 11) Security & configuration

- **Secrets**: `OPENWEATHER_API_KEY` loaded from `st.secrets`.
- **No key leakage**: API calls reside server-side; keys never embedded in client JS.
- **Timeouts**: Short network timeouts guard against slow API hangs.

---

## 12) Known limitations

- **UVI granularity beyond ≈48h**: dependent on daily UVI (less precise than hourly).
- **City name resolution**: relies on OpenWeather geocoding; ambiguous city names may need disambiguation (e.g., “Paris, FR”).
- **Outfit logic**: deterministic rules + GPT phrasing; may be tuned further for local culture/weather nuances.

---

## 13) Roadmap (suggested)

- **Rain/snow accumulation** series in charts.
- **Feels-like** (apparent) temperature and heat/cold advisory badges.
- **Air quality index (AQI)** integration.
- **Localization**: multi-language UI and units auto-detection.
- **Calendar export**: add outfit/UV reminders to user calendars.
- **Offline PDF render queue** for heavy traffic.

---

## 14) Setup & run (developer)

1. **Requirements**
   - Python 3.10+
   - `streamlit`, `pandas`, `requests`, `plotly`, `beautifulsoup4`, `reportlab` (optional for PDF)

2. **Secrets**
   - Create `.streamlit/secrets.toml`:
     ```toml
     OPENWEATHER_API_KEY = "YOUR_KEY"
     ```

3. **Run**
   ```bash
   pip install -r requirements.txt
   streamlit run App.py

---

## 15) Module glossary

- **App.py** — UI, caching, charts, exports, and orchestration.  
- **weather_api.py** — current weather + One Call (UVI, alerts, timezone).  
- **forecast_api.py** — 5-day forecast + UVI merge; hourly (next 24h local).  
- **wardrobe_advisor.py** — rule-based outfit & accessory tips.  
- **outfit_forecast.py** — multi-day outfit & color recommendations.  
- **gpt_summarizer.py** — concise weather & outfit narratives + daily tips.  
- **sunscreen_advisor.py** — skin-type aware UV/sunscreen guidance.  
- **color_utils.py** — HEX→closest color name helper (optional).  
- **export_utils.py** — PNG color grid (optional).  

---

## 16) Visual identity (charts & UI)

- **Series colors (fixed):**
  - Temp → `#E53935` (red)  
  - Humidity → `#3949AB` (indigo)  
  - PoP% → `#1E88E5` (blue)  
  - UVI% → `#FB8C00` (orange)  
  - Wind speed → `#43A047` (green)  
  - Wind gust → `#6A1B9A` (purple)  

- **Tables**  
  - Compact, rounded numbers.  
  - Percent suffix for PoP/Humidity.  
  - Human-friendly `Date/Time` formatting.  

- **Accessibility**  
  - High-contrast black axes/labels.  
  - Hover tooltips include units and friendly formatting.  

---

## 17) Example user journeys

### 17.1 Daily planner
1. Enter **“London”**.  
2. Review **climate summary**.  
3. Check **UVI & sunscreen advice**.  
4. Toggle hourly chart to show **Temp, PoP%, UVI**.  
5. Decide to carry sunglasses and a light jacket.  

### 17.2 Trip packing
1. Enter **destination city**.  
2. Open **“Next 5 days”**.  
3. Scan **temperature bands & humidity**.  
4. Export **Markdown/PDF**.  
5. Pack outfits accordingly.  

### 17.3 Content creator
1. Open **5-Day Outfit & Color Suggestions**.  
2. Copy **HEX colors** for photoshoot mood board.  
3. Export **PNG color grid** for reference.  



> Note: This code is **not runnable** on its own. It references modules kept private.
