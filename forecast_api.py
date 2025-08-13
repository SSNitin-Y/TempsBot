# forecast_api.py
import requests
import pandas as pd
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

# ---------- Public API ----------
def get_forecast(city: str, api_key: str, units: str = "metric") -> pd.DataFrame:
    """
    OpenWeather 5‑day/3‑hour forecast.
    Returns DataFrame columns:
      datetime (pd.Timestamp), temperature (float), humidity (int),
      condition (str), wind_speed (float), wind_gust (float|None), pop (0..1)
    Empty DataFrame on failure.
    """
    try:
        url = "http://api.openweathermap.org/data/2.5/forecast"
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

        return pd.DataFrame(rows)

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
    Filters rows to today's date (UTC-normalized to first row's date).
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

        rows = []
        for x in hourly:
            rows.append({
                "datetime": pd.to_datetime(x.get("dt"), unit="s"),
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

        # Keep only today's rows (normalized to the date of first hour)
        first_day = df["datetime"].dt.normalize().iloc[0]
        return df[df["datetime"].dt.normalize().eq(first_day)].reset_index(drop=True)

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



