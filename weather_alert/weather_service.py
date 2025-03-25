import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass
class WeatherCondition:
    """
    Represents a specific weather condition
    """

    type: str
    severity: str
    description: str
    value: float
    unit: str


class WeatherService:
    """
    Service responsible for fetching and analyzing weather data
    """

    def __init__(self, api_key: str, location: str):
        """
        Initialize WeatherService

        :param api_key: OpenWeatherMap API key
        :param location: City or location for weather monitoring
        """
        self.api_key = api_key
        self.location = location
        self.logger = logging.getLogger(self.__class__.__name__)

        # Weather condition thresholds
        self.thresholds = {
            "temperature": {
                "extreme_high": 40,  # Celsius
                "extreme_low": -15,
                "warning_high": 35,
                "warning_low": -10,
            },
            "wind": {
                "severe": 75,  # km/h
                "warning": 50,
            },
            "precipitation": {
                "heavy_rain": {
                    "3h": 50,  # mm in 3 hours
                    "6h": 80,  # mm in 6 hours
                },
                "snow": {
                    "3h": 20,  # cm in 3 hours
                    "6h": 40,  # cm in 6 hours
                },
            },
            "severe_conditions": [
                "thunderstorm",
                "hurricane",
                "tornado",
                "cyclone",
                "typhoon",
                "blizzard",
            ],
        }

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def fetch_forecast(self) -> Optional[Dict]:
        """
        Fetch weather forecast from OpenWeatherMap API

        :return: Weather forecast data or None
        """
        base_url = "http://api.openweathermap.org/data/2.5/forecast"
        params = {
            "q": self.location,
            "appid": self.api_key,
            "units": "metric",  # Use metric units
        }

        try:
            self.logger.info(f"Fetching weather forecast for {self.location}")
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"Error fetching weather data: {e}")
            return None

    def analyze_forecast(self, forecast: Dict) -> List[WeatherCondition]:
        """
        Analyze forecast data and detect potentially dangerous conditions

        :param forecast: Weather forecast data
        :return: List of detected weather conditions
        """
        if not forecast or "list" not in forecast:
            self.logger.warning("Invalid forecast data")
            return []

        dangerous_conditions = []

        for entry in forecast["list"]:
            # Temperature analysis
            temp = entry["main"]["temp"]
            if temp > self.thresholds["temperature"]["extreme_high"]:
                dangerous_conditions.append(
                    WeatherCondition(
                        type="temperature",
                        severity="extreme",
                        description="Extreme Heat",
                        value=temp,
                        unit="°C",
                    )
                )
            elif temp < self.thresholds["temperature"]["extreme_low"]:
                dangerous_conditions.append(
                    WeatherCondition(
                        type="temperature",
                        severity="extreme",
                        description="Extreme Cold",
                        value=temp,
                        unit="°C",
                    )
                )

            # Wind speed analysis
            wind_speed = entry["wind"]["speed"] * 3.6  # Convert m/s to km/h
            if wind_speed > self.thresholds["wind"]["severe"]:
                dangerous_conditions.append(
                    WeatherCondition(
                        type="wind",
                        severity="severe",
                        description="High Winds",
                        value=wind_speed,
                        unit="km/h",
                    )
                )

            # Precipitation checks
            if "rain" in entry and "3h" in entry["rain"]:
                rain_volume = entry["rain"]["3h"]
                if rain_volume > self.thresholds["precipitation"]["heavy_rain"]["3h"]:
                    dangerous_conditions.append(
                        WeatherCondition(
                            type="precipitation",
                            severity="heavy",
                            description="Heavy Rain",
                            value=rain_volume,
                            unit="mm",
                        )
                    )

            # Severe weather conditions
            for weather in entry.get("weather", []):
                if any(
                    condition in weather["main"].lower()
                    for condition in self.thresholds["severe_conditions"]
                ):
                    dangerous_conditions.append(
                        WeatherCondition(
                            type="weather",
                            severity="severe",
                            description=f"Severe Weather: {weather['description']}",
                            value=0,
                            unit="",
                        )
                    )

        return dangerous_conditions

    def get_weather_conditions(self) -> List[WeatherCondition]:
        """
        Comprehensive method to fetch and analyze weather conditions

        :return: List of detected weather conditions
        """
        forecast = self.fetch_forecast()
        if forecast:
            return self.analyze_forecast(forecast)
        return []
