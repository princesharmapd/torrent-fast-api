from fastapi import APIRouter, status
from typing import Optional
from helper.is_site_available import check_if_site_available
import time
import asyncio
from helper.error_messages import error_handler
from aiocache import SimpleMemoryCache

router = APIRouter(tags=["Combo Routes"])

# Initialize cache
cache = SimpleMemoryCache()

async def cache_response(key: str, func, expire: int = 86400):
    """
    Caches the response for 24 hours (86400 seconds).
    If data is available in cache, it returns cached data.
    If not, fetches new data, stores in cache, and returns it.
    """
    cached_data = await cache.get(key)
    if cached_data:
        return cached_data

    data = await func()
    await cache.set(key, data, ttl=expire)  # Store with 24-hour expiry
    return data

async def fetch_search_results(query: str, limit: int):
    start_time = time.time()
    query = query.lower()
    all_sites = check_if_site_available("1337x")
    sites_list = list(all_sites.keys())
    tasks = []
    COMBO = {"data": []}
    total_torrents_overall = 0

    for site in sites_list:
        limit = (
            all_sites[site]["limit"]
            if limit == 0 or limit > all_sites[site]["limit"]
            else limit
        )
        tasks.append(
            asyncio.create_task(
                all_sites[site]["website"]().search(query, page=1, limit=limit)
            )
        )

    results = await asyncio.gather(*tasks)
    for res in results:
        if res and len(res["data"]) > 0:
            COMBO["data"].extend(res["data"])
            total_torrents_overall += res["total"]

    COMBO["time"] = time.time() - start_time
    COMBO["total"] = total_torrents_overall

    if total_torrents_overall == 0:
        return error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            json_message={"error": "Result not found."},
        )

    return COMBO

@router.get("/search")
async def get_search_combo(query: str, limit: Optional[int] = 0):
    cache_key = f"search:{query}:{limit}"
    return await cache_response(cache_key, lambda: fetch_search_results(query, limit))


async def fetch_trending_results(limit: int):
    start_time = time.time()
    all_sites = check_if_site_available("1337x")
    sites_list = [
        site
        for site in all_sites.keys()
        if all_sites[site]["trending_available"] and all_sites[site]["website"]
    ]
    tasks = []
    COMBO = {"data": []}
    total_torrents_overall = 0

    for site in sites_list:
        limit = (
            all_sites[site]["limit"]
            if limit == 0 or limit > all_sites[site]["limit"]
            else limit
        )
        tasks.append(
            asyncio.create_task(
                all_sites[site]["website"]().trending(
                    category=None, page=1, limit=limit
                )
            )
        )

    results = await asyncio.gather(*tasks)
    for res in results:
        if res and len(res["data"]) > 0:
            COMBO["data"].extend(res["data"])
            total_torrents_overall += res["total"]

    COMBO["time"] = time.time() - start_time
    COMBO["total"] = total_torrents_overall

    if total_torrents_overall == 0:
        return error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            json_message={"error": "Result not found."},
        )

    return COMBO

@router.get("/trending")
async def get_all_trending(limit: Optional[int] = 0):
    cache_key = f"trending:{limit}"
    return await cache_response(cache_key, lambda: fetch_trending_results(limit))


async def fetch_recent_results(limit: int):
    start_time = time.time()
    all_sites = check_if_site_available("1337x")
    sites_list = [
        site
        for site in all_sites.keys()
        if all_sites[site]["recent_available"] and all_sites[site]["website"]
    ]
    tasks = []
    COMBO = {"data": []}
    total_torrents_overall = 0

    for site in sites_list:
        limit = (
            all_sites[site]["limit"]
            if limit == 0 or limit > all_sites[site]["limit"]
            else limit
        )
        tasks.append(
            asyncio.create_task(
                all_sites[site]["website"]().recent(category=None, page=1, limit=limit)
            )
        )

    results = await asyncio.gather(*tasks)
    for res in results:
        if res and len(res["data"]) > 0:
            COMBO["data"].extend(res["data"])
            total_torrents_overall += res["total"]

    COMBO["time"] = time.time() - start_time
    COMBO["total"] = total_torrents_overall

    if total_torrents_overall == 0:
        return error_handler(
            status_code=status.HTTP_404_NOT_FOUND,
            json_message={"error": "Result not found."},
        )

    return COMBO

@router.get("/recent")
async def get_all_recent(limit: Optional[int] = 0):
    cache_key = f"recent:{limit}"
    return await cache_response(cache_key, lambda: fetch_recent_results(limit))
