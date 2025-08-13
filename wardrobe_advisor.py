# wardrobe_advisor.py

def _extract_weather_fields(d):
    """Supports both your new normalized dict and the raw /weather payload."""
    if not isinstance(d, dict):
        return None

    # New normalized shape from get_weather()
    if all(k in d for k in ["temperature", "humidity", "condition"]):
        return {
            "temp": d["temperature"],
            "humidity": d["humidity"],
            "condition": str(d.get("condition", "")).lower()
        }

    # Fallback: raw OpenWeather /weather response
    try:
        return {
            "temp": d["main"]["temp"],
            "humidity": d["main"]["humidity"],
            "condition": str(
                d["weather"][0].get("description") or d["weather"][0].get("main", "")
            ).lower()
        }
    except Exception:
        return None


def get_outfit_recommendation(weather_data):
    """
    Core outfit logic (temp/condition/humidity) + UV-aware hints.
    """
    fields = _extract_weather_fields(weather_data)
    if not fields:
        return "⚠️ Unable to suggest clothing due to invalid weather data."

    temp = fields["temp"]
    humidity = fields["humidity"]
    condition = fields["condition"]
    uv = weather_data.get("uv_index")  # ← from your get_weather()

    suggestions = []

    # Temperature-based base layer
    if temp < 5:
        suggestions.append("Wear a heavy coat, gloves, and thermal layers.")
    elif temp < 15:
        suggestions.append("A jacket or sweater is recommended.")
    elif temp < 25:
        suggestions.append("Light clothing with a hoodie or long sleeves should be fine.")
    else:
        suggestions.append("Go with a t-shirt and shorts. Stay hydrated!")

    # Weather conditions
    if "rain" in condition or "drizzle" in condition or "shower" in condition:
        suggestions.append("Carry an umbrella or wear a waterproof jacket.")
    if "snow" in condition or "sleet" in condition:
        suggestions.append("Wear boots and a warm hat.")
    if "wind" in condition or "breeze" in condition or "gale" in condition:
        suggestions.append("Consider a windbreaker.")
    if "storm" in condition or "thunder" in condition:
        suggestions.append("Avoid exposed areas and wear waterproof layers.")

    # Humidity comfort
    if humidity is not None and humidity > 70 and temp > 20:
        suggestions.append("Prefer breathable, moisture‑wicking, light‑colored fabrics.")

    # 🌞 UV-aware additions (WHO categories)
    # Low (0–2), Moderate (3–5), High (6–7), Very High (8–10), Extreme (11+)
    if uv is not None:
        if uv >= 11:
            suggestions.append("UV extreme: wear UPF long sleeves & pants, wide‑brim hat, UV sunglasses; minimize midday exposure.")
        elif uv >= 8:
            suggestions.append("UV very high: UPF shirt, wide‑brim hat, UV sunglasses; seek shade around midday.")
        elif uv >= 6:
            suggestions.append("UV high: consider a UPF long‑sleeve or a lightweight overshirt and a cap/hat.")
        elif uv >= 3 and temp > 18:
            suggestions.append("UV moderate: a cap/hat and UV sunglasses are a good idea.")

    return "👕 Outfit Suggestion: " + " ".join(suggestions)


def add_accessory_tips(outfit_text, *, wind_gust_ms=None, uv=None):
    """
    Layer small accessory notes *without duplicating* UV lines you already add above.
    We intentionally ignore `uv` to avoid repeating the same UV advice.

    Pass `wind_gust_ms` (m/s if using metric from OpenWeather). We'll add a short wind tip.
    """
    tips = []
    # ~25 km/h ≈ 6.94 m/s; use 7.0 m/s as a clear threshold
    if wind_gust_ms is not None and wind_gust_ms >= 7.0:
        tips.append("Windy: secure hat (strap) or avoid very flowy fabrics.")
    return outfit_text + (" " + " ".join(tips) if tips else "")


