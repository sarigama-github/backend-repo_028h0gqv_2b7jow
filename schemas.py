"""
Database Schemas for PoolBnB (Airbnb for Pools)

Each Pydantic model represents a MongoDB collection. The collection name is the
lowercased class name (e.g., Pool -> "pool").
"""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, EmailStr


class Pool(BaseModel):
    """
    Pools available for hourly/day rentals.
    Collection: "pool"
    """
    title: str = Field(..., description="Listing title")
    description: Optional[str] = Field(None, description="Detailed description")
    host_name: str = Field(..., description="Pool owner's display name")
    location: str = Field(..., description="City or neighborhood")
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    price_per_hour: float = Field(..., ge=0, description="Price per hour in USD")
    capacity: int = Field(..., ge=1, description="Max guests")
    amenities: List[str] = Field(default_factory=list, description="Amenities list")
    photos: List[HttpUrl] = Field(default_factory=list, description="Image URLs")
    rating: Optional[float] = Field(None, ge=0, le=5)


class Booking(BaseModel):
    """
    Bookings for pools.
    Collection: "booking"
    """
    pool_id: str = Field(..., description="Referenced pool ID as string")
    guest_name: str = Field(..., description="Guest full name")
    guest_email: EmailStr = Field(..., description="Guest email")
    date: str = Field(..., description="ISO date (YYYY-MM-DD)")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    total_price: float = Field(..., ge=0)
    status: str = Field("pending", description="pending|confirmed|cancelled")
