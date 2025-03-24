import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from routers.v1.search_router import router as search_router
from routers.v1.trending_router import router as trending_router
from routers.v1.category_router import router as category_router
from routers.v1.recent_router import router as recent_router
from routers.v1.combo_routers import router as combo_router
from routers.v1.sites_list_router import router as site_list_router
from routers.home_router import router as home_router
from routers.v1.search_url_router import router as search_url_router
from helper.uptime import getUptime
from helper.dependencies import authenticate_request
from mangum import Mangum
from math import ceil
import time
from functools import wraps

startTime = time.time()

app = FastAPI(
    title="Torrent-Api-Py",
    version="1.0.1",
    description="Unofficial Torrent-Api",
    docs_url="/docs",
    contact={
        "name": "Prince Sharma",
        "url": "https://github.com/ryuk-me",
        "email": "neerajkr1210@gmail.com",
    },
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def cache_with_expiry(expiry_time: int):
    def decorator(func):
        cache = {}

        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(kwargs.items()))
            current_time = time.time()

            # Check cache expiration
            if key in cache:
                result, timestamp = cache[key]
                if current_time - timestamp < expiry_time:
                    return result

            # Fetch fresh data and cache it
            result = func(*args, **kwargs)
            cache[key] = (result, current_time)
            return result

        return wrapper

    return decorator

@app.get("/health")
async def health_route(req: Request):
    """
    Health Route : Returns App details.
    """
    return JSONResponse(
        {
            "app": "Torrent-Api-Py",
            "version": "v" + "1.0.1",
            "ip": req.client.host,
            "uptime": ceil(getUptime(startTime)),
        }
    )

# Apply caching with a 1-hour expiry (3600 seconds)
@cache_with_expiry(3600)
def get_search_router():
    return search_router

@cache_with_expiry(3600)
def get_trending_router():
    return trending_router

@cache_with_expiry(3600)
def get_recent_router():
    return recent_router

@cache_with_expiry(3600)
def get_combo_router():
    return combo_router

app.include_router(get_search_router(), prefix="/api/v1/search", dependencies=[Depends(authenticate_request)])
app.include_router(get_trending_router(), prefix="/api/v1/trending", dependencies=[Depends(authenticate_request)])
app.include_router(category_router, prefix="/api/v1/category", dependencies=[Depends(authenticate_request)])
app.include_router(get_recent_router(), prefix="/api/v1/recent", dependencies=[Depends(authenticate_request)])
app.include_router(get_combo_router(), prefix="/api/v1/all", dependencies=[Depends(authenticate_request)])
app.include_router(site_list_router, prefix="/api/v1/sites", dependencies=[Depends(authenticate_request)])
app.include_router(search_url_router, prefix="/api/v1/search_url", dependencies=[Depends(authenticate_request)])
app.include_router(home_router, prefix="")

handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8009)