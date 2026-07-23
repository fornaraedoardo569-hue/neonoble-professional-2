from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from routes.ramp_webhook import router as ramp_webhook_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate required environment variables
def validate_env():
    required_vars = ['MONGO_URL', 'DB_NAME']
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
    
    # Warn about optional but recommended vars
    if not os.environ.get('API_SECRET_ENCRYPTION_KEY'):
        logger.warning(
            "API_SECRET_ENCRYPTION_KEY not set. Platform API keys will not work."
        )
    
    # Log blockchain integration status
    if os.environ.get('BSC_RPC_URL'):
        logger.info("BSC_RPC_URL configured - blockchain integration enabled")
    else:
        logger.warning("BSC_RPC_URL not set - blockchain monitoring disabled")
    
    if os.environ.get('NENO_WALLET_MNEMONIC'):
        logger.info("NENO_WALLET_MNEMONIC configured - HD wallet enabled")
    else:
        logger.warning("NENO_WALLET_MNEMONIC not set - deposit address generation disabled")
    
    if os.environ.get('STRIPE_SECRET_KEY'):
        logger.info("STRIPE_SECRET_KEY configured - Stripe payouts enabled")
    else:
        logger.warning("STRIPE_SECRET_KEY not set - payouts will be logged for manual processing")

validate_env()

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'neonoble_ramp')]

# Import services
from services.auth_service import AuthService
from services.api_key_service import PlatformApiKeyService
from services.ramp_service import RampService
from services.pricing_service import pricing_service
from services.wallet_service import WalletService
from services.blockchain_listener import BlockchainListener
from services.stripe_payout_service import StripePayoutService
from services.transak_service import TransakService
from services.email_service import EmailService
from services.audit_log_service import AuditLogService
from services.casp_service import CaspService

# Import routes
from routes.auth import router as auth_router, set_auth_service, set_email_service
from routes.dev_portal import router as dev_router, set_api_key_service
from routes.ramp_api import router as ramp_api_router, set_services as set_ramp_api_services
from routes.user_ramp import router as user_ramp_router, set_ramp_service
from routes.webhooks import router as webhooks_router, set_payout_service as set_webhooks_payout_service
from routes.transak import router as transak_router, set_transak_service
from routes.casp import router as casp_router, set_services as set_casp_services
from routes.onboarding import router as onboarding_router, set_services as set_onboarding_services
from routes.chat import router as chat_router, set_db as set_chat_db
from middleware.casp_rbac import bind_db as bind_casp_db
from middleware.kyc_gate import bind_db as bind_kyc_gate_db

# Initialize services
auth_service = AuthService(db)
api_key_service = PlatformApiKeyService(db)
ramp_service = RampService(db)
wallet_service = WalletService(db)
blockchain_listener = BlockchainListener(db)
payout_service = StripePayoutService(db)
transak_service = TransakService(db)
email_service = EmailService()
audit_log_service = AuditLogService(db)
casp_service = CaspService(db, audit_log_service, wallet_service=wallet_service)
bind_casp_db(db)
bind_kyc_gate_db(db)

# Wire up services
ramp_service.set_wallet_service(wallet_service)
ramp_service.set_blockchain_listener(blockchain_listener)
ramp_service.set_payout_service(payout_service)

# Wire up services to routes
set_auth_service(auth_service)
set_api_key_service(api_key_service)
set_ramp_api_services(ramp_service, api_key_service)
set_ramp_service(ramp_service)
set_webhooks_payout_service(payout_service)
set_transak_service(transak_service)
set_email_service(email_service)
set_casp_services(casp_service, audit_log_service)
set_onboarding_services(casp_service)
set_chat_db(db)

# Background task for blockchain monitoring
blockchain_poll_task = None

async def on_deposit_confirmed(result: dict):
    """Callback when a deposit is confirmed on-chain."""
    quote_id = result['quote_id']
    tx_hash = result['transfer']['transaction_hash']
    amount = result['transfer']['amount']
    
    logger.info(f"Deposit confirmed for quote {quote_id}: {amount} NENO (tx: {tx_hash})")
    
    # Process the deposit
    success, error = await ramp_service.process_deposit_received(
        quote_id=quote_id,
        tx_hash=tx_hash,
        amount_received=amount
    )
    
    if success:
        logger.info(f"Successfully processed deposit for quote {quote_id}")
    else:
        logger.error(f"Failed to process deposit for quote {quote_id}: {error}")

async def get_active_quotes_for_monitoring():
    """Get active quotes for blockchain monitoring."""
    return await ramp_service.get_active_offramp_quotes()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    global blockchain_poll_task
    
    # Startup
    logger.info("NeoNoble Ramp API starting up...")
    
    # Create database indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.platform_api_keys.create_index("api_key", unique=True)
    await db.platform_api_keys.create_index("id", unique=True)
    await db.platform_api_keys.create_index("user_id")
    await db.transactions.create_index("id", unique=True)
    await db.transactions.create_index("user_id")
    await db.transactions.create_index("reference", unique=True)
    await db.transactions.create_index("metadata.quote_id")
    
    # Initialize wallet service
    try:
        await wallet_service.initialize()
        logger.info("Wallet service initialized")
    except Exception as e:
        logger.warning(f"Wallet service initialization failed: {e}")
    
    # Initialize payout service
    try:
        await payout_service.initialize()
        logger.info("Payout service initialized")
    except Exception as e:
        logger.warning(f"Payout service initialization failed: {e}")
    
    # Initialize Transak service
    try:
        await transak_service.initialize()
        logger.info("Transak service initialized")
    except Exception as e:
        logger.warning(f"Transak service initialization failed: {e}")

    # Initialize CASP layer (audit log + collections + indexes)
    try:
        await audit_log_service.initialize()
        await casp_service.initialize()
        logger.info("CASP stack initialized")
    except Exception as e:
        logger.warning(f"CASP stack initialization failed: {e}")
    
    # Start blockchain monitoring if configured
    if os.environ.get('BSC_RPC_URL'):
        try:
            await blockchain_listener.initialize()
            blockchain_poll_task = asyncio.create_task(
                blockchain_listener.start_polling(
                    get_active_quotes_for_monitoring,
                    on_deposit_confirmed
                )
            )
            logger.info("Blockchain monitoring started")
        except Exception as e:
            logger.warning(f"Blockchain monitoring failed to start: {e}")
    
    logger.info("Database indexes created")
    yield
    
    # Shutdown
    logger.info("NeoNoble Ramp API shutting down...")
    
    # Stop blockchain monitoring
    if blockchain_poll_task:
        blockchain_listener.stop_polling()
        blockchain_poll_task.cancel()
        try:
            await blockchain_poll_task
        except asyncio.CancelledError:
            pass
    
    await pricing_service.close()
    client.close()

# Create the main app
app = FastAPI(
    title="NeoNoble Ramp API",
    description="Crypto on/off-ramp platform with HMAC-secured API access and BSC blockchain integration",
    version="2.0.0",
    lifespan=lifespan
)

# Root-level health check for Kubernetes (without /api prefix)
@app.get("/health")
async def root_health():
    return {"status": "healthy", "service": "NeoNoble Ramp"}

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Root endpoint
@api_router.get("/")
async def root():
    return {
        "message": "Welcome to NeoNoble Ramp API",
        "version": "2.0.0",
        "features": {
            "blockchain_monitoring": bool(os.environ.get('BSC_RPC_URL')),
            "hd_wallet": bool(os.environ.get('NENO_WALLET_MNEMONIC')),
            "stripe_payouts": bool(os.environ.get('STRIPE_SECRET_KEY'))
        },
        "docs": "/docs"
    }

# Health check (also available at /api/health)
@api_router.get("/health")
async def health():
    return {"status": "healthy", "service": "NeoNoble Ramp"}

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(dev_router)
api_router.include_router(ramp_api_router)
api_router.include_router(user_ramp_router)
api_router.include_router(webhooks_router)
api_router.include_router(transak_router)
api_router.include_router(casp_router)
api_router.include_router(onboarding_router)
api_router.include_router(chat_router)

# Include the main router
app.include_router(api_router)
app.include_router(ramp_webhook_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# Security headers middleware (defense-in-depth hardening)
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response
