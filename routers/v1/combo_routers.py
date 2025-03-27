from fastapi import APIRouter, status
from typing import Optional
from helper.is_site_available import check_if_site_available
import time
import asyncio
from helper.error_messages import error_handler
from motor.motor_asyncio import AsyncIOMotorClient
import datetime
from pymongo import MongoClient
import ssl

router = APIRouter(tags=["Combo Routes"])

# MongoDB Connection
MONGO_URI = "mongodb+srv://princesharmaofficial1:cnCUNJBik9DV7LpB@cluster0.nb8ou4f.mongodb.net/torrent_cache?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = client["torrent_cache"]

# Create TTL Index for automatic cache expiry (24 hours)
async def create_ttl_index():
    await db.search_cache.create_index("createdAt", expireAfterSeconds=86400)  # 24 hours
    await db.trending_cache.create_index("createdAt", expireAfterSeconds=86400)
    await db.recent_cache.create_index("createdAt", expireAfterSeconds=86400)

@router.on_event("startup")
async def startup_db():
    await create_ttl_index()

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

@router.get("/search")
async def get_search_combo(query: str, limit: Optional[int] = 0):
    start_time = time.time()
    query = query.lower()

    # Check MongoDB cache
    cached_data = await get_cached_data("search_cache", query)
    if cached_data:
        return cached_data

    all_sites = check_if_site_available("1337x")
    sites_list = list(all_sites.keys())
    tasks = []
    COMBO = {"data": []}
    total_torrents_overall = 0

    for site in sites_list:
        site_limit = all_sites[site]["limit"]
        limit = site_limit if limit == 0 or limit > site_limit else limit
        tasks.append(
            asyncio.create_task(
                all_sites[site]["website"]().search(query, page=1, limit=limit)
            )
        )

    results = await asyncio.gather(*tasks)
    for res in results:
        if res and "data" in res and res["data"]:
            COMBO["data"].extend(res["data"])
            total_torrents_overall += res["total"]

    COMBO["time"] = time.time() - start_time
    COMBO["total"] = total_torrents_overall

    if total_torrents_overall == 0:
        return error_handler(status_code=status.HTTP_404_NOT_FOUND, json_message={"error": "Result not found."})

    # Store data in MongoDB cache
    await store_cache("search_cache", query, COMBO)

    return COMBO


@router.get("/trending")
async def get_all_trending(limit: Optional[int] = 0):
    start_time = time.time()

    # Check MongoDB cache
    cached_data = await get_cached_data("trending_cache", "trending")
    if cached_data:
        return cached_data

    all_sites = check_if_site_available("1337x")
    sites_list = [
        site for site in all_sites.keys()
        if all_sites[site]["trending_available"] and all_sites[site]["website"]
    ]
    tasks = []
    COMBO = {"data": []}
    total_torrents_overall = 0

    for site in sites_list:
        site_limit = all_sites[site]["limit"]
        limit = site_limit if limit == 0 or limit > site_limit else limit
        tasks.append(
            asyncio.create_task(
                all_sites[site]["website"]().trending(category=None, page=1, limit=limit)
            )
        )

    results = await asyncio.gather(*tasks)
    for res in results:
        if res and "data" in res and res["data"]:
            COMBO["data"].extend(res["data"])
            total_torrents_overall += res["total"]

    COMBO["time"] = time.time() - start_time
    COMBO["total"] = total_torrents_overall

    if total_torrents_overall == 0:
        return error_handler(status_code=status.HTTP_404_NOT_FOUND, json_message={"error": "Result not found."})

    # Store data in MongoDB cache
    await store_cache("trending_cache", "trending", COMBO)

    return COMBO


@router.get("/recent")
async def get_all_recent(limit: Optional[int] = 0):
    start_time = time.time()

    # Check MongoDB cache
    cached_data = await get_cached_data("recent_cache", "recent")
    if cached_data:
        return cached_data

    all_sites = check_if_site_available("1337x")
    sites_list = [
        site for site in all_sites.keys()
        if all_sites[site]["recent_available"] and all_sites[site]["website"]
    ]
    tasks = []
    COMBO = {"data": []}
    total_torrents_overall = 0

    for site in sites_list:
        site_limit = all_sites[site]["limit"]
        limit = site_limit if limit == 0 or limit > site_limit else limit
        tasks.append(
            asyncio.create_task(
                all_sites[site]["website"]().recent(category=None, page=1, limit=limit)
            )
        )

    results = await asyncio.gather(*tasks)
    for res in results:
        if res and "data" in res and res["data"]:
            COMBO["data"].extend(res["data"])
            total_torrents_overall += res["total"]

    COMBO["time"] = time.time() - start_time
    COMBO["total"] = total_torrents_overall

    if total_torrents_overall == 0:
        return error_handler(status_code=status.HTTP_404_NOT_FOUND, json_message={"error": "Result not found."})

    # Store data in MongoDB cache
    await store_cache("recent_cache", "recent", COMBO)

    return COMBO
