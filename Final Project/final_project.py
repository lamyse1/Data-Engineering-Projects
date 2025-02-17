# -*- coding: utf-8 -*-
"""Final Project.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1YEhxVYdXBN1Ly9vjP9KhDVXP9zNILkec
"""

# File: Final project.py
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

# My Credentials
API_KEY = "912abd7d529b4a84a2e1749fce5095ce"
MONGO_URI = "mongodb+srv://lamyseammar:Laura9966@cluster0.pfzed.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
SALES_DATA_URL = "https://raw.githubusercontent.com/lamyse1/Data-Engineering-Projects/refs/heads/main/week%203/Final%20Project%20Sales%20Data.csv"

# Default DAG arguments
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

# Step 1: Extract Sales Data
def extract_sales_data(**kwargs):
    """
    Extracts sales data from the CSV file on GitHub
    and saves it to a temporary file for later use.
    """
    try:
        logger.info("Starting extraction of sales data.")
        sales_df = pd.read_csv(SALES_DATA_URL)
        logger.info("Sales data extracted successfully. Preview:\n%s", sales_df.head())

        # Save extracted data to a temporary CSV file
        sales_df.to_csv('/tmp/sales_data.csv', index=False)
        logger.info("Sales data saved to /tmp/sales_data.csv")
    except Exception as e:
        logger.error("Error during extraction: %s", str(e))
        raise

# Step 2: Transform Data by Adding Weather Information
def fetch_weather_data(city, api_key):
    """
    Fetches weather data for the given city from OpenWeather API.
    Returns temperature (in °C), humidity, and a weather description.
    """
    try:
        logger.info(f"Fetching weather data for: {city}")
        base_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
        response = requests.get(base_url)

        if response.status_code == 200:
            data = response.json()
            temperature = round(data['main']['temp'] - 273.15, 2)
            humidity = data['main']['humidity']
            weather_description = data['weather'][0]['description']
            return temperature, humidity, weather_description
        else:
            logger.warning(f"Weather data fetch failed for {city}. Status Code: {response.status_code}")
            return None, None, None
    except Exception as e:
        logger.error(f"Error fetching weather data for {city}: {e}")
        return None, None, None

def transform_data(**kwargs):
    """
    Reads the sales data, fetches weather data for each store location,
    and writes the enriched dataset to a temporary CSV file.
    """
    try:
        logger.info("Starting transformation step...")

        # Load extracted sales data
        sales_data = pd.read_csv('/tmp/sales_data.csv')

        # Add new columns for weather data
        sales_data["Temperature (°C)"] = None
        sales_data["Humidity (%)"] = None
        sales_data["Weather Description"] = None

        # Loop through each store location and fetch weather data
        for index, row in sales_data.iterrows():
            temp, humidity, description = fetch_weather_data(row["store_location"], API_KEY)
            sales_data.at[index, "Temperature (°C)"] = temp
            sales_data.at[index, "Humidity (%)"] = humidity
            sales_data.at[index, "Weather Description"] = description

        logger.info("Transformation complete. Preview:\n%s", sales_data.head())

        # Save the transformed data to a temporary CSV file
        sales_data.to_csv('/tmp/transformed_data.csv', index=False)
        logger.info("Transformed data saved to /tmp/transformed_data.csv")
    except Exception as e:
        logger.error(f"Error in transformation: {e}")
        raise

# Step 3: Load Data into MongoDB
def load_data_to_mongo(**kwargs):
    """
    Loads transformed data from CSV into MongoDB collection 'final_sales_weather'.
    Includes error handling for connection issues and duplicate entries.
    """
    try:
        logger.info("Starting load step...")

        # Read the transformed data
        transformed_data = pd.read_csv('/tmp/transformed_data.csv')

        if transformed_data.empty:
            logger.warning("⚠ Transformed data is empty. Skipping MongoDB insertion.")
            return

        # Connect to MongoDB with timeout
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client['myweather_db']
        collection = db['final_sales_weather']

        # Convert DataFrame to list of dictionaries
        records = transformed_data.to_dict(orient="records")

        # Insert records into MongoDB with duplicate handling
        try:
            collection.insert_many(records, ordered=False)
            logger.info(f"Successfully loaded {len(records)} records into MongoDB.")
        except Exception as e:
            logger.error(f"⚠ Error inserting records: {e}")

    except Exception as e:
        logger.error(f"Error in MongoDB Load step: {e}")
        raise


# Define the Airflow tasks
extract_task = PythonOperator(
    task_id='extract_sales_data',
    python_callable=extract_sales_data,
    provide_context=True,
    dag=dag
)

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    provide_context=True,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_data_to_mongo',
    python_callable=load_data_to_mongo,
    provide_context=True,
    dag=dag
)

# Set task dependencies
extract_task >> transform_task >> load_task