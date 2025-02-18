import streamlit as st
import google.generativeai as genai
import os
import datetime
import requests
import pandas as pd
from dotenv import load_dotenv

# Set page configuration
st.set_page_config(page_title="Personalized Travel Planner", layout="wide")

# Load API keys from environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
TOMORROW_IO_API_KEY = os.getenv("TOMORROW_IO_API_KEY")

# Configure Gemini AI
genai.configure(api_key=GOOGLE_API_KEY)

def save_to_csv(data, filename="user_searches.csv"):
    df = pd.DataFrame([data])
    df.to_csv(filename, mode="a", header=not os.path.exists(filename), index=False)

def save_review(star_rating, review_text):
    """
    Save user review to CSV file.
    """
    review_data = {"rating": star_rating, "review": review_text}
    save_to_csv(review_data, filename="reviews.csv")

def get_google_places_url(query):
    """
    Returns a Google Maps search URL for the given query.
    """
    if not query:
        return ""
    base_url = "https://www.google.com/maps/search/"
    return f"{base_url}{query.replace(' ', '+')}"

def get_hourly_weather(location, start_date, end_date):
    """
    Fetch hourly weather data using Tomorrow.io API.
    """
    from datetime import datetime
    try:
        start_date_obj = datetime.strptime(str(start_date), "%Y-%m-%d")
        end_date_obj = datetime.strptime(str(end_date), "%Y-%m-%d")
    except ValueError:
        st.error("Invalid date format. Please enter dates in YYYY-MM-DD format.")
        return []

    start_date_iso = start_date_obj.strftime("%Y-%m-%dT00:00:00Z")
    end_date_iso = end_date_obj.strftime("%Y-%m-%dT23:59:59Z")

    url = "https://api.tomorrow.io/v4/timelines"
    params = {
        "location": location,
        "fields": ["temperature", "humidity", "precipitationProbability"],
        "timesteps": "1h",
        "startTime": start_date_iso,
        "endTime": end_date_iso,
        "apikey": TOMORROW_IO_API_KEY
    }
    
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        weather_data = []
        for interval in data.get("data", {}).get("timelines", [])[0].get("intervals", []):
            weather_data.append({
                "time": interval["startTime"],
                "temp": interval["values"].get("temperature", "N/A"),
                "humidity": interval["values"].get("humidity", "N/A"),
                "rain_prob": interval["values"].get("precipitationProbability", "N/A")
            })
        return weather_data
    else:
        st.error("Failed to fetch weather data")
        return []
def show_input_page():
    st.title("🌍 Personalized Travel Planner ✈️")
    location = st.text_input("📍 Enter your destination")
    start_date = st.date_input("📅 From Date", min_value=datetime.date.today())
    end_date = st.date_input("📅 To Date", min_value=start_date)
    budget_currency = st.selectbox("💰 Choose Currency", ["USD", "EUR", "INR", "GBP", "JPY", "AUD"])
    budget_range = st.selectbox("💰 Select Budget Range", ["Low (0-500)", "Medium (500-1000)", "High (1000-5000)", "Luxury (5000+)"])

    preferences = st.multiselect("🎭 Preferences", ["Cafes", "Nature", "Shopping", "Movies", "Restaurants", "Parks", "Others"])
    custom_preference = st.text_input("📝 Custom Preference (if 'Others' selected)") if "Others" in preferences else ""
    if custom_preference:
        preferences.append(custom_preference)
    additional_comments = st.text_area("📝 Additional Comments (Optional)")

    if st.button("🎉 Generate Itinerary"):
        if location and preferences:
            search_data = {
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "budget_currency": budget_currency,
                "budget_range": budget_range,
                "preferences": preferences,
                "additional_comments": additional_comments
            }
            save_to_csv(search_data)
            st.session_state.update(search_data)
            st.session_state.page = "itinerary"
            st.rerun()
        else:
            st.warning("Please enter all required details.")
            
def generate_itinerary(location, start_date, end_date, budget, preferences, hourly_weather, additional_comments):
    """
    Generate a detailed and engaging travel itinerary using Gemini AI.
    """
    model = genai.GenerativeModel("gemini-pro")
    input_text = f"""
    You are a fun and knowledgeable travel planner. Create a detailed travel itinerary for {location} from {start_date} to {end_date} with a {budget} budget.
    Preferences: {preferences}. Additional comments: {additional_comments}. The format should be:
    Day X | 
    Time (Should Start with start_time and end with end_time ( eg 8:00 am - 9:00 am. Do not write start_time end_time)) for each activity |Activity |
    Bold the places. Each activity should be the next line. Include places for breakfast, brunch, lunch, snacks, and dinner.
    Do not include budget in the suggestions. Avoid arrive and depart suggestions unless asked. 
    Use real, specific places that are available on Google Maps and in close proximity.
    Keep it fun and casual, avoiding vague suggestions.
    """
    response = model.generate_content(input_text)
    return response.text if response else "No response from AI."



def show_itinerary_page():
    st.title("🗺️ Your Personalized Itinerary")
    
    location = st.session_state.get("location", "")
    start_date = st.session_state.get("start_date", "")
    end_date = st.session_state.get("end_date", "")
    budget = f"{st.session_state.get('budget_currency', '')} {st.session_state.get('budget_range', '')}"
    preferences = st.session_state.get("preferences", [])
    additional_comments = st.session_state.get("additional_comments", "")
    
    hourly_weather = get_hourly_weather(location, start_date, end_date)
    itinerary = generate_itinerary(location, start_date, end_date, budget, preferences, hourly_weather,additional_comments)
    
    st.subheader("🌤️ Hourly Weather Forecast")
    for entry in hourly_weather:
        st.write(f"🕒 {entry['time']} | 🌡 Temp: {entry['temp']}°C | 💧 Humidity: {entry['humidity']}% | 🌧 Rain Probability: {entry['rain_prob']}%")
    
    st.subheader("📝 Your Fun & Casual Itinerary")
    st.markdown(itinerary, unsafe_allow_html=True)
    
    st.subheader("📍 Search Any Place on Google Maps")
    user_query = st.text_input("Enter a place to search on Google Maps:")
    if st.button("🔎 Search on Google Maps") and user_query:
        google_maps_url = get_google_places_url(user_query)
        st.markdown(f'<a href="{google_maps_url}" target="_blank">🗺️ Open in Google Maps</a>', unsafe_allow_html=True)
    
    st.subheader("⭐ Leave a Review")
    star_rating = st.slider("Rate your itinerary experience", 1, 5, 3)
    review_text = st.text_area("Write your review:")
    if st.button("Submit Review"):
        save_review(star_rating, review_text)
        st.success("Thank you for your feedback!")

def main():
    if "page" not in st.session_state:
        st.session_state.page = "input"
    if st.session_state.page == "input":
        show_input_page()
    elif st.session_state.page == "itinerary":
        show_itinerary_page()

if __name__ == "__main__":
    main()
