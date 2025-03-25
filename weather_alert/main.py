import logging
import os
import time

import schedule
from dotenv import load_dotenv

from weather_alert.alert_system import AlertSystem
from weather_alert.weather_service import WeatherService


def setup_logging():
    """
    Configure logging for the application
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("weather_alert.log")],
    )


def main():
    """
    Main application entry point
    """
    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logging()
    logger = logging.getLogger("WeatherAlertApp")

    try:
        # Initialize services from environment variables
        weather_service = WeatherService(
            api_key=os.getenv("OPENWEATHERMAP_API_KEY", ""),
            location=os.getenv("LOCATION", "London,UK"),
        )

        alert_system = AlertSystem(
            pushover_user_key=os.getenv("PUSHOVER_USER_KEY", ""),
            pushover_app_token=os.getenv("PUSHOVER_APP_TOKEN", ""),
            notification_threshold=os.getenv("NOTIFICATION_THRESHOLD", "warning"),
        )

        def check_weather():
            """
            Periodic weather checking function
            """
            try:
                # Fetch and analyze weather conditions
                conditions = weather_service.get_weather_conditions()

                # Send notifications if conditions are met
                alert_system.send_notification(conditions)

            except Exception as e:
                logger.error(f"Error in weather check: {e}")

        # Schedule weather checks
        schedule.every(1).hour.do(check_weather)

        logger.info("Weather Alert System started")

        # Run initial check
        check_weather()

        # Keep the application running
        while True:
            schedule.run_pending()
            time.sleep(1)

    except Exception as e:
        logger.error(f"Fatal error in weather alert system: {e}")


if __name__ == "__main__":
    main()
