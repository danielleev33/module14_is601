"""
FastAPI Main Application Module

This module defines the main FastAPI application, including:
- Application initialization and configuration
- API endpoints for user authentication
- API endpoints for calculation management (BREAD operations)
- Web routes for HTML templates
- Database table creation on startup

The application follows a RESTful API design with proper separation of concerns:
- Routes handle HTTP requests and responses
- Models define database structure
- Schemas validate request/response data
- Dependencies handle authentication and database sessions
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import List

# FastAPI imports
from fastapi import Body, FastAPI, Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr

from sqlalchemy.orm import Session

import uvicorn

# Application imports
from app.auth.jwt import get_current_user
from app.models.calculation import Calculation
from app.models.user import User
from app.schemas.calculation import CalculationBase, CalculationResponse, CalculationUpdate
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.database import Base, get_db, engine


# ------------------------------------------------------------------------------
# Create tables on startup using the lifespan event
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.

    This runs when the application starts and creates all database tables
    defined in SQLAlchemy models. It's an alternative to using Alembic
    for simpler applications.

    Args:
        app: FastAPI application instance
    """
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    yield


# Initialize the FastAPI application with metadata and lifespan
app = FastAPI(
    title="Calculations API",
    description="API for managing calculations",
    version="1.0.0",
    lifespan=lifespan
)

# ------------------------------------------------------------------------------
# Static Files and Templates Configuration
# ------------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ------------------------------------------------------------------------------
# Profile API Schemas
# ------------------------------------------------------------------------------
class ProfileResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    is_active: bool
    is_verified: bool

    class Config:
        from_attributes = True


class ProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr


# ------------------------------------------------------------------------------
# Web (HTML) Routes
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, tags=["web"])
def read_index(request: Request):
    """
    Landing page.

    Displays the welcome page with links to register and login.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse, tags=["web"])
def login_page(request: Request):
    """
    Login page.

    Displays a form for users to enter credentials and log in.
    """
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse, tags=["web"])
def register_page(request: Request):
    """
    Registration page.

    Displays a form for new users to create an account.
    """
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse, tags=["web"])
def dashboard_page(request: Request):
    """
    Dashboard page, listing calculations & new calculation form.

    This is the main interface after login, where users can:
    - See all their calculations
    - Create a new calculation
    - Access links to view/edit/delete calculations

    JavaScript in this page calls the API endpoints to fetch and display data.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/dashboard/view/{calc_id}", response_class=HTMLResponse, tags=["web"])
def view_calculation_page(request: Request, calc_id: str):
    """
    Page for viewing a single calculation (Read).
    """
    return templates.TemplateResponse(
        "view_calculation.html",
        {"request": request, "calc_id": calc_id}
    )


@app.get("/dashboard/edit/{calc_id}", response_class=HTMLResponse, tags=["web"])
def edit_calculation_page(request: Request, calc_id: str):
    """
    Page for editing a calculation (Update).
    """
    return templates.TemplateResponse(
        "edit_calculation.html",
        {"request": request, "calc_id": calc_id}
    )


# ------------------------------------------------------------------------------
# Health Endpoint
# ------------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def read_health():
    """Health check."""
    return {"status": "ok"}


# ------------------------------------------------------------------------------
# User Registration Endpoint
# ------------------------------------------------------------------------------
@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["auth"]
)
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user account.
    """
    user_data = user_create.dict(exclude={"confirm_password"})
    try:
        user = User.register(db, user_data)
        db.commit()
        db.refresh(user)
        return user
    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ------------------------------------------------------------------------------
# User Login Endpoints
# ------------------------------------------------------------------------------
@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Login with JSON payload (username & password).
    Returns an access token, refresh token, and user info.
    """
    auth_result = User.authenticate(db, user_login.username, user_login.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_result["user"]
    db.commit()

    expires_at = auth_result.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    return TokenResponse(
        access_token=auth_result["access_token"],
        refresh_token=auth_result["refresh_token"],
        token_type="bearer",
        expires_at=expires_at,
        user_id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified
    )


@app.post("/auth/token", tags=["auth"])
def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login with form data (Swagger/UI).
    Returns an access token.
    """
    auth_result = User.authenticate(db, form_data.username, form_data.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": auth_result["access_token"],
        "token_type": "bearer"
    }


# ------------------------------------------------------------------------------
# User Profile Endpoints
# ------------------------------------------------------------------------------
@app.get("/users/me", response_model=ProfileResponse, tags=["users"])
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.
    """
    return current_user


@app.put("/users/me", response_model=ProfileResponse, tags=["users"])
async def update_my_profile(
    profile_data: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update the current authenticated user's profile.
    """
    first_name = profile_data.first_name.strip()
    last_name = profile_data.last_name.strip()
    email = profile_data.email.strip().lower()

    if not first_name or not last_name or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First name, last name, and email are required."
        )

    existing_user = db.query(User).filter(
        User.email == email,
        User.id != current_user.id
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already in use."
        )

    current_user.first_name = first_name
    current_user.last_name = last_name
    current_user.email = email

    db.commit()
    db.refresh(current_user)
    return current_user


# ------------------------------------------------------------------------------
# Calculations Endpoints (BREAD)
# ------------------------------------------------------------------------------
@app.post(
    "/calculations",
    response_model=CalculationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["calculations"],
)
def create_calculation(
    calculation_data: CalculationBase,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new calculation for the authenticated user.
    Automatically computes the result.
    """
    try:
        new_calculation = Calculation.create(
            calculation_type=calculation_data.type,
            user_id=current_user.id,
            inputs=calculation_data.inputs,
        )
        new_calculation.result = new_calculation.get_result()

        db.add(new_calculation)
        db.commit()
        db.refresh(new_calculation)
        return new_calculation

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.get("/calculations", response_model=List[CalculationResponse], tags=["calculations"])
def list_calculations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all calculations belonging to the current authenticated user.
    """
    calculations = db.query(Calculation).filter(
        Calculation.user_id == current_user.id
    ).all()
    return calculations


@app.get("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def get_calculation(
    calc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve a single calculation by its UUID, if it belongs to the current user.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid calculation id format."
        )

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()

    if not calculation:
        raise HTTPException(
            status_code=404,
            detail="Calculation not found."
        )

    return calculation


@app.put("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def update_calculation(
    calc_id: str,
    calculation_update: CalculationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the inputs (and thus the result) of a specific calculation.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid calculation id format."
        )

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()

    if not calculation:
        raise HTTPException(
            status_code=404,
            detail="Calculation not found."
        )

    if calculation_update.inputs is not None:
        calculation.inputs = calculation_update.inputs
        calculation.result = calculation.get_result()

    calculation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calculation)
    return calculation


@app.delete("/calculations/{calc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["calculations"])
def delete_calculation(
    calc_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a calculation by its UUID, if it belongs to the current user.
    """
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid calculation id format."
        )

    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()

    if not calculation:
        raise HTTPException(
            status_code=404,
            detail="Calculation not found."
        )

    db.delete(calculation)
    db.commit()
    return None


# ------------------------------------------------------------------------------
# Main Block to Run the Server
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="info")