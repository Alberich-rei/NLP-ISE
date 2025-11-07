
import requests
import yfinance as yf
import os

OWM_KEY = os.getenv("OPENWEATHER_API_KEY","")

def get_weather(city):
    if not OWM_KEY:
        return "OpenWeather API key missing."

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q":city, "appid":OWM_KEY, "units":"metric", "cnt":8}
    r = requests.get(url, params=params, timeout=10)

    if r.status_code != 200:
        return f"Weather API error: {r.text}"

    data = r.json()
    out = []
    for x in data["list"][:4]:
        out.append(f"{x['dt_txt']}: {x['weather'][0]['description']}, {x['main']['temp']}°C")
    return "\n".join(out)

def get_stock(symbol):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="5d")
        if hist.empty:
            return f"No data for {symbol}"

        close = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2]
        change = (close - prev)/prev*100
        return f"{symbol} close: {close:.2f} ({change:.2f}%)"
    except Exception as e:
        return f"Stock error: {e}"
