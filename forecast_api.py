# forecast_api.py
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any

# ---------- Robust HTTP helpers ----------
def _make_session() -> requests.Session:
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

def _get_json(url: str, params: Optional[Dict[str, Any]] = None, timeout=(5, 15)) -> Dict[str, Any]:
    r = _SESSION.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

# ---------- Public API ----------
def get_forecast(city: str, api_key: str, units: str = "metric") -> pd.DataFrame:
    """
    OpenWeather 5-day/3-hour forecast (city-based).
    Returns DataFrame columns:
      datetime (UTC pd.Timestamp), temperature (float), humidity (int),
      condition (str), wind_speed (float), wind_gust (float|None),
      pop (0..1), uvi (float|None, mapped from One Call daily by LOCAL date)
    Empty DataFrame on failure.

    Note: We keep 'datetime' in UTC because the app converts it to local later.
    """
    try:
        url = "http://api.openweathermap.org/data/2.5/forecast"
        params = {"q": city, "appid": api_key, "units": units}
        data = _get_json(url, params)

        # Basic validation
        if "list" not in data:
            print("[ERROR] forecast response:", data)
            return pd.DataFrame()

        # --- Build 3-hour rows (UTC) ---
        rows = []
        for item in data["list"]:
            dt_utc = pd.to_datetime(item.get("dt"), unit="s", utc=True).tz_convert(None)  # naive UTC
            main = item.get("main", {})
            weather = (item.get("weather") or [{}])[0]
            wind = item.get("wind", {})
            rows.append({
                "datetime": dt_utc,                       # UTC naive (app will localize)
                "temperature": main.get("temp"),
                "humidity": main.get("humidity"),
                "condition": weather.get("description", ""),
                "wind_speed": wind.get("speed"),          # m/s (metric) or mph (imperial)
                "wind_gust": wind.get("gust"),
                "pop": item.get("pop", 0.0),              # precipitation probability 0..1
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # --- NEW: Fetch daily UVI from One Call v3 and map by LOCAL date ---
        # Use city coords returned by forecast payload
        coord = (data.get("city") or {}).get("coord") or {}
        lat, lon = coord.get("lat"), coord.get("lon")
        if lat is not None and lon is not None:
            try:
                oc_url = "https://api.openweathermap.org/data/3.0/onecall"
                # Exclude everything except 'daily' to keep payload small
                oc_params = {
                    "lat": lat,
                    "lon": lon,
                    "appid": api_key,
                    "units": units,
                    "exclude": "minutely,hourly,current,alerts",
                }
                oc = _get_json(oc_url, oc_params)

                tz_offset = int(oc.get("timezone_offset", 0) or 0)  # seconds
                daily = oc.get("daily", []) or []

                # Build LOCAL date -> daily UVI map
                date_to_uvi = {}
                for d in daily:
                    # 'dt' is in UTC seconds; shift by tz_offset to local midnight
                    d_local_date = (pd.to_datetime(d.get("dt"), unit="s") +
                                    pd.to_timedelta(tz_offset, unit="s")).normalize().date()
                    date_to_uvi[d_local_date] = d.get("uvi")

                # Shift each 3h timestamp to LOCAL date to map the UVI value consistently
                df["_local_date"] = (df["datetime"] + pd.to_timedelta(tz_offset, unit="s")).dt.normalize().dt.date
                df["uvi"] = df["_local_date"].map(date_to_uvi)
                df.drop(columns=["_local_date"], inplace=True)
            except Exception as _err:
                # Leave 'uvi' missing if One Call fails; table code handles missing columns
                pass

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
    Hourly forecast for *today* using One Call v3 (current + next ~48h).
    Filters rows to the location's LOCAL calendar "today".
    Returns DataFrame columns:
      datetime (UTC naive), temp, uvi, wind_speed, wind_gust, pop, rain_1h

    Note: We keep 'datetime' in UTC because the app already converts to local
    using get_tz_offset_seconds(). This avoids double-shifting.
    """
    try:
        url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {"lat": lat, "lon": lon, "appid": api_key, "units": units}
        data = _get_json(url, params)

        hourly = data.get("hourly", [])
        if not hourly:
            return pd.DataFrame()

        rows = []
        for x in hourly:
            rows.append({
                # Keep as naive UTC here; app converts once to local
                "datetime": pd.to_datetime(x.get("dt"), unit="s", utc=True).tz_convert(None),
                "temp": x.get("temp"),
                "uvi": x.get("uvi"),
                "wind_speed": x.get("wind_speed"),     # m/s (metric) or mph (imperial)
                "wind_gust": x.get("wind_gust"),
                "pop": x.get("pop", 0.0),
                "rain_1h": (x.get("rain") or {}).get("1h", 0.0),  # mm
            })
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # ---- Filter to LOCAL "today" using timezone_offset ----
        tz_offset = int(data.get("timezone_offset", 0) or 0)  # seconds

        # Local "now" at the location, then take that calendar date
        local_now = pd.Timestamp.utcnow() + pd.to_timedelta(tz_offset, unit="s")
        local_today = local_now.normalize().date()

        # Compute local date for each hourly timestamp (without changing stored UTC datetime)
        local_dates = (df["datetime"] + pd.to_timedelta(tz_offset, unit="s")).dt.date
        df_today = df.loc[local_dates == local_today].reset_index(drop=True)

        return df_today

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










