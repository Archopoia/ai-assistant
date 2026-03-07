from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .config import settings
from .database import engine, Base
from .database import SessionLocal
from .api import auth, users, health_profile, analytics, ai_insights, recipes, meal_plans, shopping_list, nutrition, assistant
from .services.rag_service import rag_service

# Create database tables
Base.metadata.create_all(bind=engine)

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

app = FastAPI(
    title="Wellness Platform API",
    description="AI-powered wellness platform API",
    version="1.0.0",
    swagger_ui_parameters={
        "syntaxHighlight.theme": "agate",
        "persistAuthorization": True,
    }
)

# Custom Swagger UI with white background
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )
    
    # Get the HTML content from HTMLResponse
    html_content = html_response.body
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8')
    
    # Inject custom CSS to make background white
    custom_css = """
    <style>
        body { background-color: #ffffff !important; }
        .swagger-ui { background-color: #ffffff !important; }
        .swagger-ui .topbar { background-color: #ffffff !important; }
        .swagger-ui .wrapper { background-color: #ffffff !important; }
        .swagger-ui .scheme-container { background-color: #ffffff !important; }
        .swagger-ui .info { background-color: #ffffff !important; }
        .swagger-ui .opblock { background-color: #ffffff !important; }
        .swagger-ui .scheme-container { background-color: #ffffff !important; padding: 10px; }
    </style>
    """
    
    # Insert CSS before closing head tag
    modified_html = html_content.replace("</head>", custom_css + "</head>")
    return HTMLResponse(content=modified_html, media_type="text/html")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    same_site="lax",
    https_only=settings.ENFORCE_HTTPS,
)

if settings.ENFORCE_HTTPS:
    app.add_middleware(HTTPSRedirectMiddleware)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(health_profile.router)
app.include_router(analytics.router)
app.include_router(ai_insights.router)
app.include_router(recipes.router)
app.include_router(meal_plans.router)
app.include_router(shopping_list.router)
app.include_router(nutrition.router)
app.include_router(assistant.router)


@app.on_event("startup")
async def seed_rag_data() -> None:
    db = SessionLocal()
    try:
        rag_service.ensure_seed_data(db)
    finally:
        db.close()


@app.get("/")
async def root():
    return {"message": "Wellness Platform API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
