import uvicorn
import aiohttp
import asyncio
import aiocron
import hashlib
import time
from math import ceil
from functools import wraps
from urllib.parse import quote_plus
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from mangum import Mangum

# Import routers
from routers.v1.search_router import router as search_router
from routers.v1.trending_router import router as trending_router
from routers.v1.catergory_router import router as catergory_router
from routers.v1.recent_router import router as recent_router
from routers.v1.combo_routers import router as combo_router
from routers.v1.sites_list_router import router as site_list_router
from routers.home_router import router as home_router
from routers.v1.search_url_router import router as search_url_router

# Import helper functions
from helper.uptime import getUptime
from helper.dependencies import authenticate_request

# MongoDB Configuration with URL Encoding
USERNAME = "princesharmaofficial1"
PASSWORD = "Aaspl@12761234"  # Your password

ENCODED_USERNAME = quote_plus(USERNAME)
ENCODED_PASSWORD = quote_plus(PASSWORD)

MONGO_URI = (
    f"mongodb://{ENCODED_USERNAME}:{ENCODED_PASSWORD}@"
    "cluster0-shard-00-00.3soyt.mongodb.net:27017," 
    "cluster0-shard-00-01.3soyt.mongodb.net:27017," 
    "cluster0-shard-00-02.3soyt.mongodb.net:27017/"
    "?replicaSet=atlas-c8y6jc-shard-0&ssl=true&authSource=admin&retryWrites=true&w=majority&appName=Cluster0"
)

# Connect to MongoDB
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["cache_db"]
cache_collection = db["api_cache"]

startTime = time.time()

# FastAPI app setup
app = FastAPI(
    title="Torrent-Api-Py",
    version="1.0.1",
    description="Unofficial Torrent-Api",
    docs_url="/docs",
    contact={
        "name": "Neeraj Kumar",
        "url": "https://github.com/ryuk-me",
        "email": "neerajkr1210@gmail.com",
    },
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to generate cache key
def generate_cache_key(*args, **kwargs):
    key_str = f"{args}-{kwargs}"
    return hashlib.md5(key_str.encode()).hexdigest()

# Async MongoDB caching functions
async def get_cached_response(key):
    return await cache_collection.find_one({"_id": key})

async def set_cached_response(key, response, expiry_time=3600):
    await cache_collection.update_one(
        {"_id": key},
        {"$set": {"response": response, "timestamp": time.time()}},
        upsert=True,
    )

# Decorator for caching with MongoDB
def cache_with_mongo(expiry_time: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = generate_cache_key(args, kwargs)
            cached_data = await get_cached_response(key)

            if cached_data and (time.time() - cached_data["timestamp"] < expiry_time):
                return cached_data["response"]

            result = await func(*args, **kwargs)
            await set_cached_response(key, result, expiry_time)
            return result

        return wrapper
    return decorator

@app.get("/health")
async def health_route(req: Request):
    """
    Health Route: Returns App details.
    """
    return JSONResponse(
        {
            "app": "Torrent-Api-Py",
            "version": "v1.0.1",
            "ip": req.client.host,
            "uptime": ceil(getUptime(startTime)),
        }
    )

# Scheduled task to ping /health every 5 minutes
@aiocron.crontab('*/5 * * * *')
async def keep_alive():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("http://localhost:8009/health") as response:
                print(f"[Keep-Alive] Health Check Status: {response.status}")
        except Exception as e:
            print(f"[Keep-Alive] Failed to ping health route: {e}")

# Include routers
app.include_router(search_router, prefix="/api/v1/search", dependencies=[Depends(authenticate_request)])
app.include_router(trending_router, prefix="/api/v1/trending", dependencies=[Depends(authenticate_request)])
app.include_router(catergory_router, prefix="/api/v1/category", dependencies=[Depends(authenticate_request)])
app.include_router(recent_router, prefix="/api/v1/recent", dependencies=[Depends(authenticate_request)])
app.include_router(combo_router, prefix="/api/v1/all", dependencies=[Depends(authenticate_request)])
app.include_router(site_list_router, prefix="/api/v1/sites", dependencies=[Depends(authenticate_request)])
app.include_router(search_url_router, prefix="/api/v1/search_url", dependencies=[Depends(authenticate_request)])
app.include_router(home_router, prefix="")

# AWS Lambda handler
handler = Mangum(app)

# Run the FastAPI application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8009)
