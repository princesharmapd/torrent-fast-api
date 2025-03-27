from fastapi import APIRouter, status
from typing import Optional
from helper.is_site_available import check_if_site_available
from helper.error_messages import error_handler
from motor.motor_asyncio import AsyncIOMotorClient
import datetime
import ssl
from pymongo import MongoClient

router = APIRouter(tags=["Trending Torrents"])

# MongoDB Connection
MONGO_URI = "mongodb+srv://princesharmaofficial1:cnCUNJBik9DV7LpB@cluster0.nb8ou4f.mongodb.net/torrent_cache?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["torrent_cache"]

# Function to create TTL index for automatic cache expiration
async def create_ttl_index(collection_name: str):
    await db[collection_name].create_index("createdAt", expireAfterSeconds=86400)  # 24 hours

# Helper function to check cache
async def get_cached_data(collection_name: str, key: str):
    cached_data = await db[collection_name].find_one({"query": key})
    if cached_data:
        return cached_data["data"]
    return None

# Helper function to store cache
async def store_cache(collection_name: str, key: str, data: dict):
    await db[collection_name].insert_one({
        "query": key,
        "data": data,
        "createdAt": datetime.datetime.utcnow()
    })

@router.get("/")
@router.get("")
async def get_trending(
    site: str,
    limit: Optional[int] = 0,
    category: Optional[str] = None,
    page: Optional[int] = 1,
):
    site = site.lower()
    category = category.lower() if category is not None else None
    all_sites = check_if_site_available(site)

    if not all_sites:
        return error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            json_message={"error": "Selected Site Not Available"},
        )

    # Define collection name dynamically based on site
    collection_name = f"trending_cache_{site}"
    await create_ttl_index(collection_name)  # Ensure TTL index exists

    # Generate cache key
    cache_key = f"trending_{category}_page{page}_limit{limit}"
    
    # Check MongoDB cache
    cached_data = await get_cached_data(collection_name, cache_key)
    if cached_data:
        return cached_data

    # Validate limits and category availability
    limit = (
        all_sites[site]["limit"]
        if limit == 0 or limit > all_sites[site]["limit"]
        else limit
    )

    if not all_sites[site]["trending_available"]:
        return error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            json_message={"error": f"Trending search not available for {site}."},
        )

    if category and not all_sites[site]["trending_category"]:
        return error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            json_message={"error": f"Search by trending category not available for {site}."},
        )

    if category and category not in all_sites[site]["categories"]:
        return error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            json_message={
                "error": "Selected category not available.",
                "available_categories": all_sites[site]["categories"],
            },
        )

    # Fetch new data if cache is empty
    resp = await all_sites[site]["website"]().trending(category, page, limit)

    if resp is None:
        return error_handler(
            status_code=status.HTTP_403_FORBIDDEN,
            json_message={"error": "Website Blocked. Change IP or Website Domain."},
        )

    elif len(resp["data"]) > 0:
        # Store data in MongoDB cache
        await store_cache(collection_name, cache_key, resp)
        return resp

    return error_handler(
        status_code=status.HTTP_404_NOT_FOUND,
        json_message={"error": "Result not found."},
    )
