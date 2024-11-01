import openai
from fastapi import FastAPI, HTTPException
from openai import OpenAI, RateLimitError
import os
import requests
import time
from pydantic import BaseModel
from typing import List

BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
CITY = "Turan" # Da Nang, Vietnam
MAX_RETRIES = 5
RETRY_DELAY = 2 

app = FastAPI()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_weather_data(city: str, api_key: str) -> dict:
    """Fetch weather data from OpenWeather API."""
    complete_url = f"{BASE_URL}appid={api_key}&q={city}"
    response = requests.get(complete_url)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()

class WardrobeRequest(BaseModel):
    image_urls: List[str]

@app.post("/wardrobe_recommend")
async def wardrobe_recommend(request: WardrobeRequest):
    # Get weather data
    try:
        weather = get_weather_data(CITY, OPENWEATHER_API_KEY)
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error fetching weather data: {e}")

    image_urls = request.image_urls
    if not image_urls:
        raise HTTPException(status_code=400, detail="No image URLs provided.")


    weather_description = weather.get("weather", [{}])[0].get("description", "unknown weather")
    messages = [
        {"role": "system", "content": "You are a helpful assistant that recommends multiple outfits based on weather and available wardrobe items."},
        {"role": "user", "content": f"Given today's weather is '{weather_description}', suggest at least five appropriate clothing items from the following URLs: {', '.join(image_urls)}."}
    ]



    attempt = 0
    while attempt < MAX_RETRIES:
        try:
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
            )


            recommendation = response.choices[0].message.content.strip()
            recommended_images = [url for url in image_urls if url in recommendation]

            if len(recommended_images) < 1:
                raise HTTPException(status_code=400, detail="Not enough items were recommended. Please try again.")

            return {"recommendations": recommended_images}

        except RateLimitError:
            attempt += 1
            time.sleep(RETRY_DELAY)
            RETRY_DELAY *= 2  


    raise HTTPException(status_code=429, detail="Rate limit exceeded. Please try again later.")

