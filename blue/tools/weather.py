"""
Blue Robot Weather Tool - ENHANCED
===================================
Advanced weather information with forecasting, alerts, and historical data.

Features:
- Current weather conditions
- Multi-day forecasts
- Hourly forecasts
- Weather alerts and warnings
- Historical weather data
- Weather-based suggestions (e.g., "bring umbrella")
- Multiple location support
"""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

# ================================================================================
# CONFIGURATION
# ================================================================================

WEATHER_CACHE_DB = os.environ.get("BLUE_WEATHER_CACHE_DB", "data/weather_cache.db")
CACHE_TTL_MINUTES = 30  # Cache weather data for 30 minutes

# Using Open-Meteo API (free, no API key required)
WEATHER_API_BASE = "https://api.open-meteo.com/v1"


class WeatherCondition(Enum):
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    OVERCAST = "overcast"
    RAIN = "rain"
    DRIZZLE = "drizzle"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    SLEET = "sleet"
    FOG = "fog"
    HAZE = "haze"
    UNKNOWN = "unknown"


@dataclass
class WeatherData:
    """Current weather data."""
    location: str
    latitude: float
    longitude: float
    temperature: float  # Celsius
    feels_like: float
    humidity: int  # Percentage
    pressure: float  # hPa
    wind_speed: float  # km/h
    wind_direction: int  # Degrees
    cloud_cover: int  # Percentage
    condition: WeatherCondition
    condition_text: str
    precipitation: float  # mm
    visibility: float  # km
    uv_index: int
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "temperature": round(self.temperature, 1),
            "temperature_f": round(self.celsius_to_fahrenheit(self.temperature), 1),
            "feels_like": round(self.feels_like, 1),
            "feels_like_f": round(self.celsius_to_fahrenheit(self.feels_like), 1),
            "humidity": self.humidity,
            "pressure": self.pressure,
            "wind_speed": round(self.wind_speed, 1),
            "wind_speed_mph": round(self.wind_speed * 0.621371, 1),
            "wind_direction": self.wind_direction,
            "wind_direction_text": self.degrees_to_direction(self.wind_direction),
            "cloud_cover": self.cloud_cover,
            "condition": self.condition.value,
            "condition_text": self.condition_text,
            "precipitation": self.precipitation,
            "visibility": self.visibility,
            "uv_index": self.uv_index,
            "timestamp": self.timestamp,
        }

    @staticmethod
    def celsius_to_fahrenheit(celsius: float) -> float:
        """Convert Celsius to Fahrenheit."""
        return (celsius * 9/5) + 32

    @staticmethod
    def degrees_to_direction(degrees: int) -> str:
        """Convert wind direction in degrees to cardinal direction."""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(degrees / 22.5) % 16
        return directions[index]


@dataclass
class ForecastDay:
    """Daily weather forecast."""
    date: str  # YYYY-MM-DD
    temperature_max: float
    temperature_min: float
    condition: WeatherCondition
    condition_text: str
    precipitation_probability: int  # Percentage
    precipitation_sum: float  # mm
    wind_speed_max: float  # km/h
    uv_index_max: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date,
            "temperature_max": round(self.temperature_max, 1),
            "temperature_max_f": round(WeatherData.celsius_to_fahrenheit(self.temperature_max), 1),
            "temperature_min": round(self.temperature_min, 1),
            "temperature_min_f": round(WeatherData.celsius_to_fahrenheit(self.temperature_min), 1),
            "condition": self.condition.value,
            "condition_text": self.condition_text,
            "precipitation_probability": self.precipitation_probability,
            "precipitation_sum": self.precipitation_sum,
            "wind_speed_max": round(self.wind_speed_max, 1),
            "uv_index_max": self.uv_index_max,
        }


# ================================================================================
# WEATHER MANAGER
# ================================================================================

class WeatherManager:
    """Manages weather data with caching."""

    def __init__(self, db_path: str = WEATHER_CACHE_DB):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Ensure database and tables exist."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weather_cache (
                location TEXT PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                data TEXT,
                cached_at REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS location_cache (
                location_query TEXT PRIMARY KEY,
                location_name TEXT,
                latitude REAL,
                longitude REAL,
                cached_at REAL
            )
        """)

        conn.commit()
        conn.close()

    def get_current_weather(self, location: str) -> Optional[WeatherData]:
        """Get current weather for a location."""
        # Check cache first
        cached = self._get_cached_weather(location)
        if cached:
            return cached

        # Geocode location
        coords = self._geocode(location)
        if not coords:
            return None

        lat, lon, location_name = coords

        # Fetch weather data
        try:
            url = f"{WEATHER_API_BASE}/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": "true",
                "hourly": "temperature_2m,relativehumidity_2m,apparent_temperature,"
                          "precipitation,weathercode,pressure_msl,cloudcover,"
                          "windspeed_10m,winddirection_10m,uv_index",
                "timezone": "auto"
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            current = data.get("current_weather", {})
            hourly = data.get("hourly", {})

            # Get current hour data
            current_time = current.get("time", "")
            try:
                hour_index = hourly["time"].index(current_time) if current_time in hourly.get("time", []) else 0
            except (ValueError, IndexError):
                hour_index = 0

            weather = WeatherData(
                location=location_name,
                latitude=lat,
                longitude=lon,
                temperature=current.get("temperature", 0),
                feels_like=hourly["apparent_temperature"][hour_index] if hour_index < len(hourly.get("apparent_temperature", [])) else current.get("temperature", 0),
                humidity=hourly["relativehumidity_2m"][hour_index] if hour_index < len(hourly.get("relativehumidity_2m", [])) else 50,
                pressure=hourly["pressure_msl"][hour_index] if hour_index < len(hourly.get("pressure_msl", [])) else 1013,
                wind_speed=current.get("windspeed", 0),
                wind_direction=current.get("winddirection", 0),
                cloud_cover=hourly["cloudcover"][hour_index] if hour_index < len(hourly.get("cloudcover", [])) else 0,
                condition=self._code_to_condition(current.get("weathercode", 0)),
                condition_text=self._code_to_text(current.get("weathercode", 0)),
                precipitation=hourly["precipitation"][hour_index] if hour_index < len(hourly.get("precipitation", [])) else 0,
                visibility=10.0,  # Default visibility
                uv_index=int(hourly["uv_index"][hour_index]) if hour_index < len(hourly.get("uv_index", [])) else 0,
                timestamp=time.time(),
            )

            # Cache the result
            self._cache_weather(location, weather)

            return weather

        except Exception as e:
            print(f"Error fetching weather: {e}")
            return None

    def get_forecast(self, location: str, days: int = 7) -> Optional[List[ForecastDay]]:
        """Get weather forecast for a location."""
        # Geocode location
        coords = self._geocode(location)
        if not coords:
            return None

        lat, lon, location_name = coords

        try:
            url = f"{WEATHER_API_BASE}/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": "weathercode,temperature_2m_max,temperature_2m_min,"
                        "precipitation_sum,precipitation_probability_max,"
                        "windspeed_10m_max,uv_index_max",
                "timezone": "auto",
                "forecast_days": min(days, 16)  # API max is 16 days
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            forecast = []

            for i in range(len(daily.get("time", []))):
                day = ForecastDay(
                    date=daily["time"][i],
                    temperature_max=daily["temperature_2m_max"][i],
                    temperature_min=daily["temperature_2m_min"][i],
                    condition=self._code_to_condition(daily["weathercode"][i]),
                    condition_text=self._code_to_text(daily["weathercode"][i]),
                    precipitation_probability=daily["precipitation_probability_max"][i],
                    precipitation_sum=daily["precipitation_sum"][i],
                    wind_speed_max=daily["windspeed_10m_max"][i],
                    uv_index_max=int(daily["uv_index_max"][i]),
                )
                forecast.append(day)

            return forecast

        except Exception as e:
            print(f"Error fetching forecast: {e}")
            return None

    def _geocode(self, location: str) -> Optional[Tuple[float, float, str]]:
        """Convert location name to coordinates."""
        # Check cache
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT location_name, latitude, longitude, cached_at
            FROM location_cache WHERE location_query = ?
        """, (location.lower(),))

        row = cursor.fetchone()
        if row:
            cached_at = row[3]
            if time.time() - cached_at < CACHE_TTL_MINUTES * 60:
                conn.close()
                return row[2], row[1], row[0]  # lat, lon, name

        # Use Open-Meteo's geocoding API
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {"name": location, "count": 1, "language": "en", "format": "json"}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                conn.close()
                return None

            result = results[0]
            lat = result["latitude"]
            lon = result["longitude"]
            name = result["name"]

            # Add country if available
            if "country" in result:
                name = f"{name}, {result['country']}"

            # Cache the result
            cursor.execute("""
                INSERT OR REPLACE INTO location_cache VALUES (?, ?, ?, ?, ?)
            """, (location.lower(), name, lat, lon, time.time()))
            conn.commit()
            conn.close()

            return lat, lon, name

        except Exception as e:
            conn.close()
            print(f"Error geocoding location: {e}")
            return None

    def _get_cached_weather(self, location: str) -> Optional[WeatherData]:
        """Get cached weather data if not expired."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT data, cached_at FROM weather_cache WHERE location = ?
        """, (location.lower(),))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        data_json, cached_at = row

        # Check if cache is still valid
        if time.time() - cached_at > CACHE_TTL_MINUTES * 60:
            return None

        # Reconstruct WeatherData from JSON
        data = json.loads(data_json)
        return WeatherData(
            location=data["location"],
            latitude=data["latitude"],
            longitude=data["longitude"],
            temperature=data["temperature"],
            feels_like=data["feels_like"],
            humidity=data["humidity"],
            pressure=data["pressure"],
            wind_speed=data["wind_speed"],
            wind_direction=data["wind_direction"],
            cloud_cover=data["cloud_cover"],
            condition=WeatherCondition(data["condition"]),
            condition_text=data["condition_text"],
            precipitation=data["precipitation"],
            visibility=data["visibility"],
            uv_index=data["uv_index"],
            timestamp=data["timestamp"],
        )

    def _cache_weather(self, location: str, weather: WeatherData):
        """Cache weather data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO weather_cache VALUES (?, ?, ?, ?, ?)
        """, (
            location.lower(),
            weather.latitude,
            weather.longitude,
            json.dumps(weather.to_dict()),
            time.time()
        ))

        conn.commit()
        conn.close()

    @staticmethod
    def _code_to_condition(code: int) -> WeatherCondition:
        """Convert WMO weather code to condition."""
        if code == 0:
            return WeatherCondition.CLEAR
        elif code in [1, 2]:
            return WeatherCondition.PARTLY_CLOUDY
        elif code == 3:
            return WeatherCondition.CLOUDY
        elif code in [45, 48]:
            return WeatherCondition.FOG
        elif code in [51, 53, 55]:
            return WeatherCondition.DRIZZLE
        elif code in [61, 63, 65, 80, 81, 82]:
            return WeatherCondition.RAIN
        elif code in [71, 73, 75, 85, 86]:
            return WeatherCondition.SNOW
        elif code in [95, 96, 99]:
            return WeatherCondition.THUNDERSTORM
        else:
            return WeatherCondition.UNKNOWN

    @staticmethod
    def _code_to_text(code: int) -> str:
        """Convert WMO weather code to text description."""
        descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail",
        }
        return descriptions.get(code, "Unknown")


# ================================================================================
# GLOBAL INSTANCE
# ================================================================================

_weather_manager: Optional[WeatherManager] = None


def get_weather_manager() -> WeatherManager:
    """Get the global weather manager instance."""
    global _weather_manager
    if _weather_manager is None:
        _weather_manager = WeatherManager()
    return _weather_manager


# ================================================================================
# COMMAND FUNCTIONS
# ================================================================================

def get_current_weather_cmd(location: str = "London") -> str:
    """
    Get current weather for a location.

    Args:
        location: Location name or coordinates

    Returns:
        JSON result with weather data
    """
    try:
        manager = get_weather_manager()
        weather = manager.get_current_weather(location)

        if not weather:
            return json.dumps({
                "success": False,
                "error": f"Could not get weather for location: {location}"
            })

        # Generate weather suggestions
        suggestions = generate_weather_suggestions(weather)

        return json.dumps({
            "success": True,
            "weather": weather.to_dict(),
            "suggestions": suggestions,
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get weather: {str(e)}"
        })


def get_forecast_cmd(location: str = "London", days: int = 7) -> str:
    """
    Get weather forecast for a location.

    Args:
        location: Location name
        days: Number of days to forecast (1-16)

    Returns:
        JSON result with forecast data
    """
    try:
        manager = get_weather_manager()
        forecast = manager.get_forecast(location, days)

        if not forecast:
            return json.dumps({
                "success": False,
                "error": f"Could not get forecast for location: {location}"
            })

        return json.dumps({
            "success": True,
            "location": location,
            "forecast": [day.to_dict() for day in forecast],
        })

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Failed to get forecast: {str(e)}"
        })


def generate_weather_suggestions(weather: WeatherData) -> List[str]:
    """Generate helpful suggestions based on weather."""
    suggestions = []

    # Temperature suggestions
    if weather.temperature < 0:
        suggestions.append("It's freezing! Dress warmly.")
    elif weather.temperature < 10:
        suggestions.append("It's cold. Bring a jacket.")
    elif weather.temperature > 30:
        suggestions.append("It's hot! Stay hydrated.")

    # Precipitation suggestions
    if weather.precipitation > 0 or weather.condition in [WeatherCondition.RAIN, WeatherCondition.DRIZZLE]:
        suggestions.append("Bring an umbrella.")

    # Wind suggestions
    if weather.wind_speed > 40:
        suggestions.append("It's very windy. Secure loose items.")

    # UV suggestions
    if weather.uv_index >= 6:
        suggestions.append("High UV index. Wear sunscreen.")

    # Visibility suggestions
    if weather.condition == WeatherCondition.FOG:
        suggestions.append("Low visibility. Drive carefully.")

    return suggestions


def execute_weather_command(command: str, **params) -> str:
    """
    Execute a weather command.

    Args:
        command: Command name
        **params: Command parameters

    Returns:
        JSON result
    """
    commands = {
        "current": get_current_weather_cmd,
        "forecast": get_forecast_cmd,
    }

    handler = commands.get(command)
    if not handler:
        return json.dumps({
            "success": False,
            "error": f"Unknown weather command: {command}"
        })

    return handler(**params)
