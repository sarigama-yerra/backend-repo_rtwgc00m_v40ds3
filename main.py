import os
from typing import List, Optional
import requests
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Book Search API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"


def map_volume(item: dict) -> dict:
    volume = item.get("volumeInfo", {})
    image_links = volume.get("imageLinks", {})
    return {
        "id": item.get("id"),
        "title": volume.get("title"),
        "authors": volume.get("authors", []),
        "thumbnail": image_links.get("thumbnail") or image_links.get("smallThumbnail"),
        "publishedDate": volume.get("publishedDate"),
        "description": volume.get("description"),
        "pageCount": volume.get("pageCount"),
        "categories": volume.get("categories", []),
        "language": volume.get("language"),
        "infoLink": volume.get("infoLink") or volume.get("canonicalVolumeLink"),
        "previewLink": volume.get("previewLink"),
        "publisher": volume.get("publisher"),
        "rating": volume.get("averageRating"),
        "ratingsCount": volume.get("ratingsCount"),
    }


@app.get("/")
def read_root():
    return {"message": "Book Search Backend is running"}


@app.get("/api/search")
def search_books(
    q: str = Query(..., description="Search query"),
    startIndex: int = Query(0, ge=0),
    maxResults: int = Query(20, ge=1, le=40),
):
    """Search books via Google Books API and return normalized results."""
    params = {"q": q, "startIndex": startIndex, "maxResults": maxResults}
    try:
        resp = requests.get(GOOGLE_BOOKS_API, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        return {
            "total": data.get("totalItems", 0),
            "items": [map_volume(it) for it in items],
            "query": q,
        }
    except Exception as e:
        return {"total": 0, "items": [], "query": q, "error": str(e)}


@app.get("/api/recommendations")
def recommendations():
    """Return curated recommendation queries and sample books for the homepage."""
    suggestion_sets = [
        {"title": "Trending Fiction", "q": "subject:fiction bestsellers"},
        {"title": "Personal Growth", "q": "subject:self-help"},
        {"title": "Tech & Programming", "q": "subject:programming OR subject:technology"},
        {"title": "Business & Strategy", "q": "subject:business strategy"},
        {"title": "Sci‑Fi Classics", "q": "subject:science fiction classics"},
        {"title": "For Kids", "q": "subject:children"},
    ]

    samples: List[dict] = []
    for s in suggestion_sets:
        try:
            r = requests.get(GOOGLE_BOOKS_API, params={"q": s["q"], "maxResults": 6}, timeout=10)
            if r.status_code == 200:
                payload = r.json()
                items = [map_volume(it) for it in payload.get("items", [])]
                samples.append({"title": s["title"], "q": s["q"], "items": items})
        except Exception:
            samples.append({"title": s["title"], "q": s["q"], "items": []})

    return {"sections": samples}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
