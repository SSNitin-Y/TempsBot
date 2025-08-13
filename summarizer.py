def summarize_weather(data):
    if not data:
        return "⚠️ Unable to fetch weather data. Please check the summarizer.py."

    temp = data['temperature']
    humidity = data['humidity']
    desc = data['condition']
    city = data['city']

    return (
        f"📍 In {city}, the current temperature is {temp}°C with {humidity}% humidity.\n"
        f"The sky is described as '{desc}'. Stay weather-aware!"
    )
