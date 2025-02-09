#Step 1 DAG Skeleton and sales DATA extract
# etl_pipeline.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import requests
import logging
from pymongo import MongoClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# My Credentials for Mongo DB, Sales CSV on Github, API Key
API_KEY = "912abd7d529b4a84a2e1749fce5095ce"
MONGO_URI = "mongodb+srv://lamyseammar:Laura9966@cluster0.pfzed.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
SALES_DATA_URL = "https://raw.githubusercontent.com/lamyse1/Data-Engineering-Projects/refs/heads/main/week%203/Final%20Project%20Sales%20Data.csv"

# Default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 2, 1),
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    "etl_pipeline_myweather_project",
    default_args=default_args,
    description="ETL pipeline integrating sales and weather data",
    schedule_interval='0 6 * * *',  
    catchup=False
)

def extract_sales_data(**kwargs):
    """
    Extracts sales data from the CSV file on GitHub,
    writes the DataFrame to a local CSV file for later use.
    """
    try:
        logger.info("Starting extraction of sales data.")
        sales_df = pd.read_csv(SALES_DATA_URL)
        logger.info("Sales data extracted successfully. Preview:\n%s", sales_df.head())
        
        # Write the DataFrame to a temporary CSV file
        sales_df.to_csv('/tmp/sales_data.csv', index=False)
        logger.info("Sales data saved to /tmp/sales_data.csv")
        return "Extraction successful"
    except Exception as e:
        logger.error("Error during extraction: %s", str(e))
        raise

# Define the extract task
extract_task = PythonOperator(
    task_id='extract_sales_data',
    python_callable=extract_sales_data,
    provide_context=True,
    dag=dag
)
#Step 2: Adding weather data extraction and integration.
import requests
import pandas as pd
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Key for OpenWeather
API_KEY = "912abd7d529b4a84a2e1749fce5095ce"

# Function to fetch weather data for a store location
def fetch_weather_data(city, api_key):
    try:
        logger.info(f"Fetching weather data for: {city}")
        base_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
        response = requests.get(base_url)

        if response.status_code == 200:
            data = response.json()
            temperature = round(data['main']['temp'] - 273.15, 2)  # Convert from Kelvin to Celsius
            humidity = data['main']['humidity']
            weather_description = data['weather'][0]['description']
            return temperature, humidity, weather_description
        else:
            logger.warning(f"Weather data fetch failed for {city}. Status Code: {response.status_code}")
            return None, None, None
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None, None, None

# Function to transform sales data by adding weather information
def transform_data():
    try:
        logger.info("Starting transformation step...")
        
        # Load sales data from GitHub CSV
        SALES_DATA_URL = "https://raw.githubusercontent.com/lamyse1/Data-Engineering-Projects/refs/heads/main/week%203/Final%20Project%20Sales%20Data.csv"
        sales_data = pd.read_csv(SALES_DATA_URL)
        
        # Add new columns for weather data
        sales_data["Temperature (°C)"] = None
        sales_data["Humidity (%)"] = None
        sales_data["Weather Description"] = None

        # Loop through rows and enrich sales data with weather info
        for index, row in sales_data.iterrows():
            temp, humidity, description = fetch_weather_data(row["store_location"], API_KEY)
            sales_data.at[index, "Temperature (°C)"] = temp
            sales_data.at[index, "Humidity (%)"] = humidity
            sales_data.at[index, "Weather Description"] = description
        
        logger.info("Transformation complete.")
        return sales_data
    except Exception as e:
        logger.error(f"Error in transformation: {e}")
        raise
