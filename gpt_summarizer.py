# gpt_summarizer.py
import streamlit as st

# OpenAI client (safe init)
try:
    from openai import OpenAI
    _api_key = st.secrets.get("OPENAI_API_KEY")
    client = OpenAI(api_key=_api_key) if _api_key else None
except Exception:
    client = None  # graceful no-API fallback


def _extract_fields(data):
    """Support both your normalized dict and raw OpenWeather /weather payloads."""
    if not isinstance(data, dict):
        return None

    # New normalized shape from get_weather()
    if all(k in data for k in ["city", "temperature", "humidity", "condition"]):
        return {
            "city": data.get("city", "your city"),
            "temp": data.get("temperature"),
            "humidity": data.get("humidity"),
            "condition": data.get("condition"),
            "uvi": data.get("uv_index")
        }

    # Fallback: raw /weather response
    try:
        return {
            "city": data.get("name", "your city"),
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "condition": data["weather"][0]["description"],
            "uvi": None  # raw /weather doesn't include UVI
        }
    except Exception:
        return None


def _safe_chat(prompt, *, model="gpt-3.5-turbo", temperature=0.7, max_tokens=160,
               system="You are a concise, upbeat weather stylist. Keep outputs short and friendly. No emojis."):
    """
    Small wrapper that returns None if the OpenAI call fails or client not available.
    """
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception:
        return None


# -----------------------------
# Public API
# -----------------------------
def generate_gpt_summary(data, model="gpt-3.5-turbo", temperature=0.7):
    """
    2–3 sentence current weather blurb. Uses UV if available. Falls back to a deterministic template.
    """
    try:
        fields = _extract_fields(data)
        if not fields:
            return "⚠️ GPT Summary skipped: unrecognized weather data shape."

        city = fields["city"]
        temp = fields["temp"]
        humidity = fields["humidity"]
        condition = fields["condition"]
        uvi = fields["uvi"]

        uv_line = f"\n- UV Index: {uvi:.1f}" if isinstance(uvi, (int, float)) else ""
        prompt = (
            f"Write a fun, engaging 2–3 sentence weather summary for {city}.\n"
            f"- Temperature: {temp}°C\n- Humidity: {humidity}%\n- Sky: {condition}.{uv_line}\n"
            f"Make it conversational like a friendly assistant. Avoid emojis."
        )

        out = _safe_chat(prompt, model=model, temperature=temperature, max_tokens=150)
        if out:
            return out

        # Fallback (deterministic)
        base = f"{city} is currently {temp}°C with {humidity}% humidity and {condition}."
        if isinstance(uvi, (int, float)):
            base += f" UV index is around {uvi:.1f}. "
        else:
            base += " "
        base += "Stay comfortable and plan your day accordingly!"
        return base

    except Exception as e:
        return f"⚠️ GPT Summary failed: {e}"


def generate_outfit_summary(outfit_text, model="gpt-3.5-turbo", temperature=0.7):
    """
    1–2 sentence rephrase of your outfit suggestion.
    """
    try:
        prompt = (
            "Rewrite the following clothing suggestion in 1–2 sentences with a helpful, friendly tone; no emojis:\n\n"
            f"{outfit_text}"
        )
        out = _safe_chat(prompt, model=model, temperature=temperature, max_tokens=90)
        return out or outfit_text
    except Exception as e:
        return f"⚠️ GPT Outfit Summary failed: {e}"


def generate_forecast_summary(forecast_df, model="gpt-3.5-turbo", temperature=0.7):
    """
    Short outlook for next 5 days based on a DataFrame with columns: datetime, temperature, humidity.
    """
    try:
        if forecast_df is None or forecast_df.empty:
            return "A quick outlook isn’t available at the moment."

        max_temp = float(forecast_df['temperature'].max())
        min_temp = float(forecast_df['temperature'].min())
        avg_humidity = float(forecast_df['humidity'].mean())
        days = forecast_df['datetime'].dt.date.unique()
        start, end = days[0], days[-1]

        prompt = (
            f"Create a short, friendly weather outlook for the next 5 days ({start} to {end}). "
            f"Temperatures range from {min_temp:.1f}°C to {max_temp:.1f}°C with average humidity ~{avg_humidity:.1f}%. "
            f"1–2 sentences. No emojis."
        )
        out = _safe_chat(prompt, model=model, temperature=temperature, max_tokens=120)
        if out:
            return out

        # Fallback
        return (f"From {start} to {end}, expect temperatures between {min_temp:.1f}°C and {max_temp:.1f}°C "
                f"with average humidity around {avg_humidity:.1f}%. Plan layers as needed.")

    except Exception as e:
        return f"⚠️ GPT Forecast Summary failed: {e}"


def generate_daily_outfit_summary(date, outfit, colors, model="gpt-3.5-turbo", temperature=0.7):
    """
    One punchy sentence tip for a specific day. Uses color labels if provided.
    """
    try:
        color_list = ', '.join(colors) if colors else "neutral shades"
        prompt = (
            f"For {date}, give a single, punchy styling tip (max 1 sentence). "
            f"Base outfit: {outfit}. Suggested colors: {color_list}. No emojis."
        )
        out = _safe_chat(prompt, model=model, temperature=temperature, max_tokens=60)
        if out:
            return out

        # Fallback
        return f"For {date}, lean into {color_list} to complement {outfit.lower()}."
    except Exception as e:
        return f"⚠️ GPT Outfit Tip failed: {e}"

