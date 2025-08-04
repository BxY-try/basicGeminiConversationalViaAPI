import requests
import datetime
import json
from config import OPENWEATHERMAP_API_KEY, NEWSAPI_API_KEY

def get_current_date_and_time() -> str:
    """
    Returns the current date and time in a human-readable format.
    """
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

def get_weather(location: str) -> str:
    """
    Gets the current weather for a given location using the OpenWeatherMap API.
    
    Args:
        location (str): The city name, e.g., "San Francisco", "Tokyo".
    """
    if not OPENWEATHERMAP_API_KEY:
        return "Error: OpenWeatherMap API key is not configured."
        
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": location,
        "appid": OPENWEATHERMAP_API_KEY,
        "units": "metric"  # Use Celsius
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        
        weather_description = data['weather'][0]['description']
        temperature = data['main']['temp']
        feels_like = data['main']['feels_like']
        humidity = data['main']['humidity']
        wind_speed = data['wind']['speed']
        
        return json.dumps({
            "location": location,
            "description": weather_description,
            "temperature_celsius": temperature,
            "feels_like_celsius": feels_like,
            "humidity_percent": humidity,
            "wind_speed_mps": wind_speed
        })
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {e}"
    except KeyError:
        return f"Error: Could not parse weather data for {location}. The location might be invalid."

def get_news(topic: str) -> str:
    """
    Gets the top 5 recent news headlines for a given topic from the NewsAPI.
    
    Args:
        topic (str): The topic to search for, e.g., "technology", "business", "indonesia".
    """
    if not NEWSAPI_API_KEY:
        return "Error: NewsAPI API key is not configured."
        
    base_url = "https://newsapi.org/v2/everything" # Use the 'everything' endpoint for keyword search
    params = {
        "q": topic,
        "apiKey": NEWSAPI_API_KEY,
        "pageSize": 5,
        "language": "en",
        "sortBy": "relevancy" # Sort by relevancy for better results
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        articles = data.get("articles", [])
        if not articles:
            return f"No recent news found for the topic: {topic}"
            
        # Return a JSON string of the articles
        return json.dumps(articles)
        
    except requests.exceptions.RequestException as e:
        return f"Error fetching news data: {e}"

# This dictionary maps function names to their actual implementation.
# It will be used by the tool calling logic to execute the correct function.
available_tools = {
    "get_current_date_and_time": get_current_date_and_time,
    "get_weather": get_weather,
    "get_news": get_news,
}