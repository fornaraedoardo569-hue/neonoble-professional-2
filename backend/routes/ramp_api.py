from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging

from models.quote import QuoteResponse, RampResponse
from services.ramp_service import RampService
from services.pricing_service import pricing_service, SUPPORTED_CRYPTOS, NENO_PRICE_EUR
from middleware.auth import HMACAuthMiddleware, get_optional_user
from services.api_key_service import PlatformApiKeyService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ramp API"])

# Services will be set by main app
ramp_service: RampService = None
hmac_middleware: HMACAuthMiddleware = None


def set_services(ramp: RampService, api_key_service: PlatformApiKeyService):
    global ramp_service, hmac_middleware
    ramp_service = ramp
    hmac_middleware = HMACAuthMiddleware(api_key_service)


class OnrampQuoteRequest(BaseModel):
    fiat_amount: float = Field(..., gt=0, description="Amount in EUR to convert")
    crypto_currency: str = Field(..., description="Target cryptocurrency (BTC, ETH, NENO, etc.)")


class OfframpQuoteRequest(BaseModel):
    crypto_amount: float = Field(..., gt=0, description="Amount of crypto to convert")
    crypto_currency: str = Field(..., description="Source cryptocurrency (BTC, ETH, NENO, etc.)")


class OnrampExecuteRequest(BaseModel):
    quote_id: str = Field(..., description="Quote ID from onramp-quote endpoint")
    wallet_address: str = Field(..., description="Wallet address to receive crypto")


class OfframpExecuteRequest(BaseModel):
    quote_id: str = Field(..., description="Quote ID from offramp-quote endpoint")
    bank_account: str = Field(..., description="Bank account IBAN to receive fiat")


@router.get("/ramp-api-health")
async def ramp_health():
    """Health check for the Ramp API."""
    return {
        "status": "healthy",
        "service": "NeoNoble Ramp API",
        "version": "1.0.0",
        "supported_cryptos": SUPPORTED_CRYPTOS,
        "neno_price_eur": NENO_PRICE_EUR
    }


@router.get("/ramp-api-prices")
async def get_prices():
    """Get current prices for all supported cryptocurrencies."""
    try:
        prices = await pricing_service.get_all_prices_eur()
        return {
            "success": True,
            "currency": "EUR",
            "prices": prices,
            "neno_note": "NENO is fixed at 10,000 EUR per token"
        }
    except Exception as e:
        logger.error(f"Failed to fetch prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch prices")


@router.post("/ramp-api-onramp-quote", response_model=QuoteResponse)
async def create_onramp_quote(request: OnrampQuoteRequest, http_request: Request):
    """
    Get a quote for onramp (Fiat -> Crypto).
    
    **HMAC Authentication Required**
    
    Headers:
    - X-API-KEY: Your API key
    - X-TIMESTAMP: Unix timestamp in seconds
    - X-SIGNATURE: HMAC-SHA256(timestamp + bodyJson, apiSecret)
    """
    # Authenticate with HMAC
    await hmac_middleware.authenticate(http_request)
    
    # Validate crypto currency
    if request.crypto_currency.upper() not in SUPPORTED_CRYPTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported cryptocurrency. Supported: {SUPPORTED_CRYPTOS}"
        )
    
    try:
        quote = await ramp_service.create_onramp_quote(
            fiat_amount=request.fiat_amount,
            crypto_currency=request.crypto_currency.upper()
        )
        return quote
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create onramp quote: {e}")
        raise HTTPException(status_code=500, detail="Failed to create quote")


@router.post("/ramp-api-onramp", response_model=RampResponse)
async def execute_onramp(request: OnrampExecuteRequest, http_request: Request):
    """
    Execute an onramp transaction (Fiat -> Crypto).
    
    **HMAC Authentication Required**
    
    Use a quote_id from the onramp-quote endpoint.
    """
    auth_info = await hmac_middleware.authenticate(http_request)
    
    result, error = await ramp_service.execute_onramp(
        quote_id=request.quote_id,
        wallet_address=request.wallet_address,
        api_key_id=auth_info["api_key_id"]
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return result


@router.post("/ramp-api-offramp-quote", response_model=QuoteResponse)
async def create_offramp_quote(request: OfframpQuoteRequest, http_request: Request):
    """
    Get a quote for offramp (Crypto -> Fiat).
    
    **HMAC Authentication Required**
    """
    await hmac_middleware.authenticate(http_request)
    
    if request.crypto_currency.upper() not in SUPPORTED_CRYPTOS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported cryptocurrency. Supported: {SUPPORTED_CRYPTOS}"
        )
    
    try:
        quote = await ramp_service.create_offramp_quote(
            crypto_amount=request.crypto_amount,
            crypto_currency=request.crypto_currency.upper()
        )
        return quote
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create offramp quote: {e}")
        raise HTTPException(status_code=500, detail="Failed to create quote")


@router.post("/ramp-api-offramp", response_model=RampResponse)
async def execute_offramp(request: OfframpExecuteRequest, http_request: Request):
    """
    Execute an offramp transaction (Crypto -> Fiat).
    
    **HMAC Authentication Required**
    """
    auth_info = await hmac_middleware.authenticate(http_request)
    
    result, error = await ramp_service.execute_offramp(
        quote_id=request.quote_id,
        bank_account=request.bank_account,
        api_key_id=auth_info["api_key_id"]
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return result
