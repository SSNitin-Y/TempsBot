# weather_api.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------- Robust HTTP helpers ----------
def _make_session():
    retry = Retry(
        total=3,                # up to 3 retries
        backoff_factor=0.5,     # 0.5s, 1s, 2s between tries
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    sess = requests.Session()
    sess.mount("http://", HTTPAdapter(max_retries=retry))
    sess.mount("https://", HTTPAdapter(max_retries=retry))
    return sess

_SESSION = _make_session()

def _get_json(url: str, params: dict, timeout=(5, 15)):
    """GET JSON with retries + timeouts. Raises for network/HTTP errors."""
    r = _SESSION.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

# ---------- Public API ----------
def get_weather(city: str, api_key: str):
    """
    Returns:
      dict or None (on failure).
      {
        "city": str,
        "temperature": float,
        "humidity": int,
        "condition": str,
        "uv_index": float | None,
        "uv_next5": list[float|None],   # NEW: next 5 days UVI
        "uv_source": "v3",
        "alerts": list,                  # may be empty
        "coord": {"lat": float, "lon": float},  # NEW: for hourly view
        "name": str                      # raw OpenWeather name
      }
    """
    try:
        # 1) Current conditions + coords (v2.5)
        geo_url = "http://api.openweathermap.org/data/2.5/weather"
        geo_params = {"q": city, "appid": api_key, "units": "metric"}
        geo_res = _get_json(geo_url, geo_params)

        # validate
        if not all(k in geo_res for k in ("coord", "main", "weather")):
            print("[ERROR] Incomplete geo response:", geo_res)
            return None

        lat = geo_res["coord"]["lat"]
        lon = geo_res["coord"]["lon"]

        # 2) One Call v3 for UV + alerts + daily UVI
        onecall_url = "https://api.openweathermap.org/data/3.0/onecall"
        one_params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
        onecall_res = _get_json(onecall_url, one_params)

        current = onecall_res.get("current") or {}
        daily   = onecall_res.get("daily") or []
        uv_index = current.get("uvi")
        uv_next5 = [d.get("uvi") for d in daily[:5]]  # NEW
        alerts   = onecall_res.get("alerts") or []

        return {
            "city": city,
            "temperature": geo_res["main"]["temp"],
            "humidity": geo_res["main"]["humidity"],
            "condition": geo_res["weather"][0]["description"],
            "uv_index": uv_index,
            "uv_next5": uv_next5,                 # NEW
            "uv_source": "v3",
            "alerts": alerts,
            "coord": {"lat": lat, "lon": lon},    # NEW
            "name": geo_res.get("name", city),
        }

    except requests.exceptions.HTTPError as he:
        # e.g., 401 invalid key, 404 city not found
        print(f"[HTTP ERROR] get_weather: {he}")
        try:
            print("Server said:", he.response.json())
        except Exception:
            pass
        return None
    except requests.exceptions.RequestException as ne:
        print(f"[NETWORK ERROR] get_weather: {ne}")
        return None
    except Exception as e:
        print(f"[EXCEPTION] get_weather: {e}")
        return None




