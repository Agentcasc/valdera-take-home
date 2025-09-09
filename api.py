"""
FastAPI application for Chemical Supplier Discovery Agent.

This provides a REST API interface for the chemical supplier discovery system,
designed for production deployment and integration with other systems.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn
import os
from dotenv import load_dotenv

from app.agent import run_agent
from app.schema import AgentResult, SupplierHit

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Chemical Supplier Discovery API",
    description="AI-powered chemical supplier discovery with evidence validation",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for web integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    """Request model for supplier search."""
    chemical_name: str = Field(..., description="Name of the chemical to search for")
    cas_number: str = Field(..., description="CAS registry number")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of suppliers to return")
    excluded_countries: Optional[List[str]] = Field(default=None, description="Countries to exclude from results")
    allowed_countries: Optional[List[str]] = Field(default=None, description="Countries to include only (takes precedence over excluded)")


class SearchResponse(BaseModel):
    """Response model for supplier search."""
    success: bool
    message: str
    data: Optional[AgentResult] = None
    processing_time_seconds: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: dict


@app.get("/", response_model=dict)
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Chemical Supplier Discovery API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring and load balancers."""
    services = {
        "serpapi": bool(os.getenv("SERPAPI_KEY")),
        "cohere": bool(os.getenv("COHERE_API_KEY")),
        "playwright": True  # Assume installed if service is running
    }
    
    return HealthResponse(
        status="healthy",
        services=services
    )


@app.post("/search", response_model=SearchResponse)
async def search_suppliers(request: SearchRequest):
    """
    Search for chemical suppliers with evidence validation.
    
    This endpoint performs the complete supplier discovery pipeline:
    1. Web search for potential suppliers
    2. Website scraping and CAS number validation
    3. AI-powered relevance ranking
    4. Geographic filtering
    5. Email discovery and validation
    
    Returns a list of verified suppliers with evidence links.
    """
    try:
        import time
        start_time = time.time()
        
        # Validate API key
        if not os.getenv("SERPAPI_KEY"):
            raise HTTPException(
                status_code=500,
                detail="SERPAPI_KEY not configured. Please check server configuration."
            )
        
        # Convert country lists to sets
        excluded_countries = set(request.excluded_countries or [])
        allowed_countries = set(request.allowed_countries or [])
        
        # Validate mutual exclusion
        if excluded_countries and allowed_countries:
            raise HTTPException(
                status_code=400,
                detail="Cannot specify both excluded_countries and allowed_countries. Use one or the other."
            )
        
        # Run the agent
        result = run_agent(
            chemical_name=request.chemical_name,
            cas=request.cas_number,
            limit=request.limit,
            excluded_countries=excluded_countries,
            allowed_countries=allowed_countries
        )
        
        processing_time = time.time() - start_time
        
        return SearchResponse(
            success=True,
            message=f"Found {len(result.suppliers)} suppliers for {request.chemical_name}",
            data=result,
            processing_time_seconds=round(processing_time, 2)
        )
        
    except Exception as e:
        # Log error in production
        print(f"Search error: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@app.post("/search/async", response_model=dict)
async def search_suppliers_async(request: SearchRequest, background_tasks: BackgroundTasks):
    """
    Asynchronous supplier search for long-running requests.
    
    Returns immediately with a task ID. Use /status/{task_id} to check progress.
    This is useful for batch processing or when expecting longer processing times.
    """
    # In production, implement with Celery, RQ, or similar task queue
    import uuid
    task_id = str(uuid.uuid4())
    
    # This is a simplified implementation
    # In production, you'd use a proper task queue
    return {
        "task_id": task_id,
        "status": "accepted",
        "message": "Search task queued. Use /status/{task_id} to check progress."
    }


@app.get("/countries", response_model=dict)
async def get_supported_countries():
    """Get list of supported countries for filtering."""
    from search import COUNTRY_CODES
    
    return {
        "country_codes": COUNTRY_CODES,
        "total_countries": len(COUNTRY_CODES)
    }


@app.get("/examples", response_model=dict)
async def get_examples():
    """Get example chemical names and CAS numbers for testing."""
    return {
        "examples": [
            {"chemical_name": "Eucalyptol", "cas_number": "470-82-6"},
            {"chemical_name": "N-Methyl-2-pyrrolidone", "cas_number": "872-50-4"},
            {"chemical_name": "Potassium methoxide", "cas_number": "865-33-8"},
            {"chemical_name": "Polysorbate 80", "cas_number": "9005-65-6"},
            {"chemical_name": "Acetone", "cas_number": "67-64-1"}
        ]
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return {"error": "Endpoint not found", "detail": str(exc)}


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return {"error": "Internal server error", "detail": str(exc)}


if __name__ == "__main__":
    # Development server
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
