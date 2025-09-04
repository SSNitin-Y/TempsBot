# forecast_api.py
import requests
import pandas as pd
import math
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------- Robust HTTP helpers ----------
def _make_session():
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    sess = requests.Session()
    sess.mount("http://", HTTPAdapter(max_retries=retry))
    sess.mount("https://", HTTPAdapter(max_retries=retry))
    return sess

_SESSION = _make_session()

def _get_json(url: str, params: dict | None = None, timeout=(5, 15)):
    r = _SESSION.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

# ---------- Internal helpers ----------
def _safe_to_numeric(v):
    try:
        return float(v) if v is not None and not (isinstance(v, float) and math.isnan(v)) else None
    except Exception:
        return None

def _nearest_merge_uv(df_forecast: pd.DataFrame, onecall: dict) -> pd.DataFrame:
    """
    Add a 'uvi' column into df_forecast by merging from One Call:
      - Prefer hourly uvi for timestamps within ~48h
      - Fall back to daily.uvi for later days (date-level)
    df_forecast must have 'datetime' (Timestamp) and we return the same frame with 'uvi'.
    """
    if df_forecast.empty:
        df_forecast["uvi"] = pd.NA
        return df_forecast

    # Build hourly uvi map
    hourly = onecall.get("hourly") or []
    h_rows = []
    for h in hourly:
        dt = pd.to_datetime(h.get("dt"), unit="s")
        uvi = _safe_to_numeric(h.get("uvi"))
        h_rows.append({"datetime": dt, "uvi_hourly": uvi})
    df_h = pd.DataFrame(h_rows)
    if not df_h.empty:
        # exact timestamp join first
        df = df_forecast.merge(df_h, on="datetime", how="left")
    else:
        df = df_forecast.copy()
        df["uvi_hourly"] = pd.NA

    # Build daily uvi map (date-level)
    daily = onecall.get("daily") or []
    d_rows = []
    for d in daily:
        dt = pd.to_datetime(d.get("dt"), unit="s").normalize()
        uvi = _safe_to_numeric(d.get("uvi"))
        d_rows.append({"date": dt, "uvi_daily": uvi})
    df_d = pd.DataFrame(d_rows)

    df["date"] = df["datetime"].dt.normalize()

    if not df_d.empty:
        df = df.merge(df_d, on="date", how="left")
    else:
        df["uvi_daily"] = pd.NA

    # Prefer hourly value when present; otherwise use daily
    def _pick_uvi(row):
        uh = row.get("uvi_hourly")
        if uh is not None and not pd.isna(uh):
            return uh
        ud = row.get("uvi_daily")
        return ud if ud is not None and not pd.isna(ud) else pd.NA

    df["uvi"] = df.apply(_pick_uvi, axis=1)
    return df.drop(columns=["date", "uvi_hourly", "uvi_daily"], errors="ignore")

# ---------- Public API ----------
def get_forecast(city: str, api_key: str, units: str = "metric") -> pd.DataFrame:
    """
    OpenWeather 5-day/3-hour forecast.
    Returns DataFrame columns:
      datetime (pd.Timestamp), temperature (float), humidity (int),
      condition (str), wind_speed (float), wind_gust (float|None), pop (0..1), uvi (float|NA)
    Empty DataFrame on failure.
    """
    try:
        # Use HTTPS (some hosts block http)
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"q": city, "appid": api_key, "units": units}
        data = _get_json(url, params)

        if "list" not in data:
            print("[ERROR] forecast response:", data)
            return pd.DataFrame()

        rows = []
        for item in data["list"]:
            dt = pd.to_datetime(item.get("dt"), unit="s")
            main = item.get("main", {})
            weather = (item.get("weather") or [{}])[0]
            wind = item.get("wind", {})
            rows.append({
                "datetime": dt,
                "temperature": main.get("temp"),
                "humidity": main.get("humidity"),
                "condition": weather.get("description", ""),
                "wind_speed": wind.get("speed"),          # m/s (metric) or mph (imperial)
                "wind_gust": wind.get("gust"),
                "pop": item.get("pop", 0.0),              # precipitation probability 0..1
            })

        df = pd.DataFrame(rows)

        # ---- Enrich with UVI using One Call for the same coords ----
        try:
            city_obj = data.get("city") or {}
            coord = city_obj.get("coord") or {}
            lat, lon = coord.get("lat"), coord.get("lon")
            if lat is not None and lon is not None:
                oc_url = "https://api.openweathermap.org/data/3.0/onecall"
                oc_params = {"lat": lat, "lon": lon, "appid": api_key, "units": units}
                oc_data = _get_json(oc_url, oc_params)
                df = _nearest_merge_uv(df, oc_data)
            else:
                df["uvi"] = pd.NA
        except Exception as uv_e:
            print("[WARN] UVI merge failed:", uv_e)
            df["uvi"] = pd.NA

        return df

    except requests.exceptions.HTTPError as he:
        print(f"[HTTP ERROR] get_forecast: {he}")
        try:
            print("Server said:", he.response.json())
        except Exception:
            pass
        return pd.DataFrame()
    except requests.exceptions.RequestException as ne:
        print(f"[NETWORK ERROR] get_forecast: {ne}")
        return pd.DataFrame()
    except Exception as e:
        print(f"[EXCEPTION] get_forecast: {e}")
        return pd.DataFrame()


def get_hourly_today(lat: float, lon: float, api_key: str, units: str = "metric") -> pd.DataFrame:
    """
    Hourly forecast for the *next 24 hours* (rolling window in the city's local time)
    using One Call v3 (current + next ~48h).

    Returns DataFrame columns:
      datetime, temp, uvi, wind_speed, wind_gust, pop, rain_1h
    """
    try:
        url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {"lat": lat, "lon": lon, "appid": api_key, "units": units}
        data = _get_json(url, params)

        hourly = data.get("hourly", [])
        if not hourly:
            return pd.DataFrame()

        # Compute city local "now" using timezone_offset from One Call
        tz_offset = int(data.get("timezone_offset", 0) or 0)

        # Current time reference: use One Call's 'current.dt' if available for consistency
        import time
        now_utc = int((data.get("current") or {}).get("dt") or time.time())
        now_local = pd.to_datetime(now_utc + tz_offset, unit="s")
        end_local = now_local + pd.Timedelta(hours=24)

        rows = []
        for x in hourly:
            ts_utc = int(x.get("dt") or 0)
            ts_local = pd.to_datetime(ts_utc + tz_offset, unit="s")

            if now_local <= ts_local <= end_local:
                rows.append({
                    "datetime": ts_local.tz_localize(None),  # return naive local timestamps (your app expects this)
                    "temp": x.get("temp"),
                    "uvi": x.get("uvi"),
                    "wind_speed": x.get("wind_speed"),     # m/s (metric) or mph (imperial)
                    "wind_gust": x.get("wind_gust"),
                    "pop": x.get("pop", 0.0),
                    "rain_1h": (x.get("rain") or {}).get("1h", 0.0),  # mm
                })

        df = pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)
        return df

    except requests.exceptions.HTTPError as he:
        print(f"[HTTP ERROR] get_hourly_today: {he}")
        try:
            print("Server said:", he.response.json())
        except Exception:
            pass
        return pd.DataFrame()
    except requests.exceptions.RequestException as ne:
        print(f"[NETWORK ERROR] get_hourly_today: {ne}")
        return pd.DataFrame()
    except Exception as e:
        print(f"[EXCEPTION] get_hourly_today: {e}")
        return pd.DataFrame()










