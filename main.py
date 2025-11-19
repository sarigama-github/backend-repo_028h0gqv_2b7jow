import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Pool, Booking


app = FastAPI(title="PoolBnB API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "PoolBnB API is running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                response["collections"] = db.list_collection_names()[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# ---------- Helper ----------
class PoolOut(Pool):
    id: str


class BookingOut(Booking):
    id: str


# ---------- Pool Endpoints ----------
@app.post("/api/pools", response_model=dict)
def create_pool(pool: Pool):
    pool_id = create_document("pool", pool)
    return {"id": pool_id}


@app.get("/api/pools", response_model=List[PoolOut])
def list_pools(q: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None):
    filt = {}
    if q:
        # simple case-insensitive search on title/location using regex
        filt["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"location": {"$regex": q, "$options": "i"}},
        ]
    if min_price is not None or max_price is not None:
        price_cond = {}
        if min_price is not None:
            price_cond["$gte"] = float(min_price)
        if max_price is not None:
            price_cond["$lte"] = float(max_price)
        filt["price_per_hour"] = price_cond

    docs = get_documents("pool", filt)
    out: List[PoolOut] = []
    for d in docs:
        d["id"] = str(d.get("_id"))
        d.pop("_id", None)
        out.append(PoolOut(**d))
    return out


@app.get("/api/pools/{pool_id}", response_model=PoolOut)
def get_pool(pool_id: str):
    if db is None:
        raise HTTPException(500, "Database not available")
    doc = db["pool"].find_one({"_id": ObjectId(pool_id)})
    if not doc:
        raise HTTPException(404, "Pool not found")
    doc["id"] = str(doc["_id"]) ; doc.pop("_id", None)
    return PoolOut(**doc)


# ---------- Booking Endpoints ----------
@app.post("/api/bookings", response_model=dict)
def create_booking(booking: Booking):
    # Basic conflict check for overlapping times (same pool/date)
    if db is None:
        raise HTTPException(500, "Database not available")

    existing = list(db["booking"].find({
        "pool_id": booking.pool_id,
        "date": booking.date,
        "status": {"$in": ["pending", "confirmed"]},
    }))

    def to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    new_start = to_minutes(booking.start_time)
    new_end = to_minutes(booking.end_time)
    if new_end <= new_start:
        raise HTTPException(400, "End time must be after start time")

    for b in existing:
        s = to_minutes(b.get("start_time"))
        e = to_minutes(b.get("end_time"))
        # overlap if start < other_end and end > other_start
        if new_start < e and new_end > s:
            raise HTTPException(409, "Time slot already booked")

    booking_id = create_document("booking", booking)
    return {"id": booking_id}


@app.get("/api/pools/{pool_id}/availability", response_model=List[dict])
def get_availability(pool_id: str, date: str):
    if db is None:
        raise HTTPException(500, "Database not available")
    # Return booked ranges for given date
    bookings = list(db["booking"].find({
        "pool_id": pool_id,
        "date": date,
        "status": {"$in": ["pending", "confirmed"]},
    }, {"start_time": 1, "end_time": 1, "_id": 0}))
    return bookings


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
