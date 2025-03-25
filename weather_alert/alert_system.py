import http.client
import logging
import urllib.parse
from typing import List, Optional

from weather_alert.weather_service import WeatherCondition


class AlertSystem:
    """
    System responsible for sending notifications about weather conditions
    """

    def __init__(
        self,
        pushover_user_key: str,
        pushover_app_token: str,
        notification_threshold: str = "warning",
    ):
        """
        Initialize AlertSystem

        :param pushover_user_key: Pushover user key
        :param pushover_app_token: Pushover application token
        :param notification_threshold: Minimum severity to trigger notification
        """
        self.logger = logging.getLogger(self.__class__.__name__)

        # Severity hierarchy
        self.severity_levels = {"info": 0, "warning": 1, "severe": 2, "extreme": 3}

        self.notification_threshold = notification_threshold
        self.pushover_user_key = pushover_user_key
        self.pushover_app_token = pushover_app_token

    def _format_condition_message(self, conditions: List[WeatherCondition]) -> str:
        """
        Format weather conditions into a human-readable message

        :param conditions: List of weather conditions
        :return: Formatted message string
        """
        if not conditions:
            return "No significant weather conditions detected."

        message_parts = ["⚠️ Weather Alert:\n"]

        for condition in conditions:
            # Format the condition message based on its type
            if condition.type == "temperature":
                message_parts.append(
                    f"🌡️ {condition.severity.capitalize()} {condition.description}: "
                    f"{condition.value}{condition.unit}"
                )
            elif condition.type == "wind":
                message_parts.append(
                    f"💨 {condition.severity.capitalize()} {condition.description}: "
                    f"{condition.value}{condition.unit}"
                )
            elif condition.type == "precipitation":
                message_parts.append(
                    f"🌧️ {condition.severity.capitalize()} {condition.description}: "
                    f"{condition.value}{condition.unit}"
                )
            else:
                message_parts.append(
                    f"⚡ {condition.severity.capitalize()} {condition.description}"
                )

        return "\n".join(message_parts)

    def filter_conditions(
        self, conditions: List[WeatherCondition]
    ) -> List[WeatherCondition]:
        """
        Filter conditions based on severity threshold

        :param conditions: List of weather conditions
        :return: Filtered list of conditions
        """
        return [
            condition
            for condition in conditions
            if self.severity_levels.get(condition.severity, 0)
            >= self.severity_levels.get(self.notification_threshold, 0)
        ]

    def send_notification(
        self, conditions: List[WeatherCondition], title: Optional[str] = None
    ) -> bool:
        """
        Send push notification for weather conditions

        :param conditions: List of weather conditions
        :param title: Optional custom notification title
        :return: Whether notification was sent successfully
        """
        # Filter conditions based on threshold
        filtered_conditions = self.filter_conditions(conditions)

        # If no conditions meet the threshold, do not send
        if not filtered_conditions:
            self.logger.info("No conditions meet notification threshold")
            return False

        # Prepare message
        message = self._format_condition_message(filtered_conditions)

        # Send notification
        try:
            conn = http.client.HTTPSConnection("api.pushover.net:443")
            conn.request(
                "POST",
                "/1/messages.json",
                urllib.parse.urlencode(
                    {
                        "token": self.pushover_app_token,
                        "user": self.pushover_user_key,
                        "message": message,
                        "title": title or "Weather Alert System",
                    }
                ),
                {"Content-type": "application/x-www-form-urlencoded"},
            )
            response = conn.getresponse()

            if response.status == 200:
                self.logger.info("Notification sent successfully")
                return True
            else:
                self.logger.error(
                    f"Failed to send notification. Status: {response.status}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return False
