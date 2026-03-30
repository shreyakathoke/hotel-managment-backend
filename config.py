import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    MONGO_URI = os.getenv("MONGO_URI")
    SECRET_KEY = os.getenv("SECRET_KEY")



import cloudinary
import cloudinary.uploader

cloudinary.config(
    cloud_name="your_name",
    api_key="your_key",
    api_secret="your_secret"
)