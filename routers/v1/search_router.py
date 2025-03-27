from fastapi import APIRouter, status
from typing import Optional
from helper.is_site_available import check_if_site_available
from helper.error_messages import error_handler
from aiocache import SimpleMemoryCache

router = APIRouter(tags=["Search"])

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

async def fetch_search_results(site: str, query: str, limit: int, page: int):
    site = site.lower()
    query = query.lower()
    all_sites = check_if_site_available(site)

    if all_sites:
        limit = (
            all_sites[site]["limit"]
            if limit == 0 or limit > all_sites[site]["limit"]
            else limit
        )

        resp = await all_sites[site]["website"]().search(query, page, limit)
        if resp is None:
            return error_handler(
                status_code=status.HTTP_403_FORBIDDEN,
                json_message={"error": "Website Blocked. Change IP or Website Domain."},
            )
        elif len(resp["data"]) > 0:
            return resp
        else:
            return error_handler(
                status_code=status.HTTP_404_NOT_FOUND,
                json_message={"error": "Result not found."},
            )

    return error_handler(
        status_code=status.HTTP_404_NOT_FOUND,
        json_message={"error": "Selected Site Not Available"},
    )

@router.get("/")
@router.get("")
async def search_for_torrents(
    site: str, query: str, limit: Optional[int] = 0, page: Optional[int] = 1
):
    cache_key = f"search:{site}:{query}:{limit}:{page}"
    return await cache_response(cache_key, lambda: fetch_search_results(site, query, limit, page))
