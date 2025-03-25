from unittest.mock import Mock, patch

import pytest
import requests

from weather_alert.alert_system import AlertSystem
from weather_alert.weather_service import WeatherCondition, WeatherService


@pytest.fixture
def mock_api_key():
    return "test_api_key"


@pytest.fixture
def mock_location():
    return "TestCity"


@pytest.fixture
def weather_service(mock_api_key, mock_location):
    return WeatherService(mock_api_key, mock_location)


@pytest.fixture
def alert_system():
    return AlertSystem(
        pushover_user_key="test_user_key", pushover_app_token="test_app_token"
    )


def test_weather_condition_creation():
    """Test WeatherCondition dataclass creation"""
    condition = WeatherCondition(
        type="temperature",
        severity="extreme",
        description="Extreme Heat",
        value=42.5,
        unit="°C",
    )

    assert condition.type == "temperature"
    assert condition.severity == "extreme"
    assert condition.description == "Extreme Heat"
    assert condition.value == 42.5
    assert condition.unit == "°C"


@pytest.mark.parametrize(
    "forecast_data, expected_conditions",
    [
        # Test case with extreme heat
        (
            {"list": [{"main": {"temp": 41}, "wind": {"speed": 5}, "weather": []}]},
            1,  # Expected number of conditions
        ),
        # Test case with high winds
        (
            {
                "list": [
                    {
                        "main": {"temp": 25},
                        "wind": {"speed": 25},  # 90 km/h
                        "weather": [],
                    }
                ]
            },
            1,  # Expected number of conditions
        ),
        # Test case with severe weather condition
        (
            {
                "list": [
                    {
                        "main": {"temp": 25},
                        "wind": {"speed": 5},
                        "weather": [
                            {"main": "Thunderstorm", "description": "Thunderstorm"}
                        ],
                    }
                ]
            },
            1,  # Expected number of conditions
        ),
    ],
)
def test_analyze_forecast(weather_service, forecast_data, expected_conditions):
    """Test weather forecast analysis with different scenarios"""
    conditions = weather_service.analyze_forecast(forecast_data)

    assert len(conditions) == expected_conditions


@patch("requests.get")
def test_fetch_forecast_success(mock_get, weather_service):
    """Test successful weather forecast retrieval"""
    # Mock successful API response
    mock_response = Mock()
    mock_response.json.return_value = {"list": []}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    forecast = weather_service.fetch_forecast()

    assert forecast is not None
    mock_get.assert_called_once()


@patch("requests.get")
def test_fetch_forecast_failure(mock_get, weather_service):
    """Test weather forecast retrieval failure"""
    # Simulate a request exception
    mock_get.side_effect = requests.RequestException("Network error")

    forecast = weather_service.fetch_forecast()

    assert forecast is None


def test_alert_system_filter_conditions(alert_system):
    """Test filtering weather conditions based on severity threshold"""
    conditions = [
        WeatherCondition(
            type="temperature", severity="info", description="Mild", value=25, unit="°C"
        ),
        WeatherCondition(
            type="temperature",
            severity="warning",
            description="Getting Hot",
            value=35,
            unit="°C",
        ),
        WeatherCondition(
            type="wind",
            severity="severe",
            description="High Winds",
            value=80,
            unit="km/h",
        ),
    ]

    # Test with default "warning" threshold
    filtered_conditions = alert_system.filter_conditions(conditions)

    assert len(filtered_conditions) == 2
    assert all(
        condition.severity in ["warning", "severe"] for condition in filtered_conditions
    )


@patch("http.client.HTTPSConnection")
def test_send_notification_success(mock_https_connection, alert_system):
    """Test successful notification sending"""
    # Prepare test conditions
    conditions = [
        WeatherCondition(
            type="temperature",
            severity="warning",
            description="High Temp",
            value=35,
            unit="°C",
        )
    ]

    # Mock the HTTPSConnection
    mock_response = Mock()
    mock_response.status = 200
    mock_connection = Mock()
    mock_connection.getresponse.return_value = mock_response
    mock_https_connection.return_value = mock_connection

    # Send notification
    result = alert_system.send_notification(conditions)

    assert result is True
    mock_connection.request.assert_called_once()


@patch("http.client.HTTPSConnection")
def test_send_notification_failure(mock_https_connection, alert_system):
    """Test notification sending failure"""
    # Prepare test conditions
    conditions = [
        WeatherCondition(
            type="temperature",
            severity="warning",
            description="High Temp",
            value=35,
            unit="°C",
        )
    ]

    # Mock the HTTPSConnection with a failure response
    mock_response = Mock()
    mock_response.status = 400
    mock_connection = Mock()
    mock_connection.getresponse.return_value = mock_response
    mock_https_connection.return_value = mock_connection

    # Send notification
    result = alert_system.send_notification(conditions)

    assert result is False


def test_format_condition_message(alert_system):
    """Test formatting of weather condition messages"""
    conditions = [
        WeatherCondition(
            type="temperature",
            severity="warning",
            description="High Temp",
            value=35,
            unit="°C",
        ),
        WeatherCondition(
            type="wind",
            severity="severe",
            description="Strong Winds",
            value=80,
            unit="km/h",
        ),
    ]

    message = alert_system._format_condition_message(conditions)

    assert "🌡️ Warning High Temp: 35°C" in message
    assert "💨 Severe Strong Winds: 80km/h" in message
