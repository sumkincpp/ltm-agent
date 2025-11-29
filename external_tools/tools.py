"""Example external tools for the agent pipeline."""

import logging

import requests

logger = logging.getLogger(__name__)


def get_weather(location: str) -> dict:
    """Get weather info without using an API key (Open-Meteo)."""
    # logger.warning(f"Getting weather for location='{location}'")

    try:
        # 1. Convert city → coordinates
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
        geo_res = requests.get(geo_url).json()

        if not geo_res.get("results"):
            return {"error": "location not found"}

        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]

        # 2. Get weather
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code"
        w = requests.get(weather_url).json()["current"]

        return {
            "location": location,
            "temperature": w["temperature_2m"],
            "humidity": w["relative_humidity_2m"],
            "weather_code": w["weather_code"],
        }
    except Exception as e:
        logger.error(f"Error getting weather for location='{location}': {e}")
        return {"error": str(e)}


def get_current_time(timezone: str) -> dict:
    """Get current date and time for a given timezone using python standard library.

    timezone is provided in tz database format, e.g. "America/New_York", "Europe/London", "Asia/Tokyo".
    """
    from datetime import datetime
    from zoneinfo import ZoneInfo

    # logger.warning(f"Getting current time for timezone='{timezone}'")

    try:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        return {
            "timezone": timezone,
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        logger.error(f"Error getting time for timezone='{timezone}': {e}")
        return {"error": str(e)}


# def get_weather(location: str) -> dict:
#     """Get weather information for a location."""
#     # Simulated weather data
#     return {"location": location, "temperature": 72, "condition": "Sunny", "humidity": 45}


def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    # logger.info(f"Calculating Fibonacci for n={n}")
    result = calculate_fibonacci_internal(n)
    # logger.info(f"Fibonacci number for n={n} is {result}")
    return result


# Global cache for Fibonacci numbers
_fibonacci_cache = {0: 0, 1: 1}


def calculate_fibonacci_internal(n: int) -> int:
    """Calculate Fibonacci number iteratively with global cache."""
    if n in _fibonacci_cache:
        return _fibonacci_cache[n]

    # find the highest consecutive cached index
    # so we avoid cases like {0, 100} causing wrong start points
    start = max(k for k in _fibonacci_cache.keys() if k - 1 in _fibonacci_cache)

    a = _fibonacci_cache[start - 1]
    b = _fibonacci_cache[start]

    for i in range(start + 1, n + 1):
        a, b = b, a + b
        _fibonacci_cache[i] = b

    return _fibonacci_cache[n]


class DatabaseClient:
    """Example database client class."""

    @staticmethod
    def search(query: str) -> list:
        """Search database for query."""
        return [
            {"id": 1, "title": f"Result for '{query}' #1"},
            {"id": 2, "title": f"Result for '{query}' #2"},
        ]

    @staticmethod
    def get_user(user_id: int) -> dict:
        """Get user by ID."""
        return {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}
