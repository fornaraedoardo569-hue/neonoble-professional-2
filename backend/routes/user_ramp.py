from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
import logging

from models.quote import QuoteResponse
from models.transaction import TransactionResponse
from services.ramp_service import RampService
from services.pricing_service import pricing_service, SUPPORTED_CRYPTOS, NENO_PRICE_EUR
from middleware.auth import get_current_user, get_optional_user
from middleware.kyc_gate import require_kyc_approved

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ramp", tags=["User Ramp"])

# Service will be set by main app
ramp_service: RampService = None


def set_ramp_service(service: RampService):
    global ramp_service
    ramp_service = service


class UserQuoteRequest(BaseModel):
    fiat_amount: Optional[float] = None
    crypto_amount: Optional[float] = None
    crypto_currency: str


class UserRampRequest(BaseModel):
    quote_id: str
    wallet_address: Optional[str] = None
    bank_account: Optional[str] = None


@router.get("/prices")
async def get_prices():
    """Get current crypto prices in EUR."""
    try:
        prices = await pricing_service.get_all_prices_eur()
        return {
            "currency": "EUR",
            "prices": prices,
            "supported": SUPPORTED_CRYPTOS,
            "neno_fixed_price": NENO_PRICE_EUR
        }
    except Exception as e:
        logger.error(f"Failed to fetch prices: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch prices")


@router.post("/onramp/quote", response_model=QuoteResponse)
async def create_onramp_quote(
    request: UserQuoteRequest,
    current_user: dict = Depends(require_kyc_approved)
):
    """Create an onramp quote (EUR -> Crypto) for logged-in users with APPROVED KYC."""
    if not request.fiat_amount:
        raise HTTPException(status_code=400, detail="fiat_amount is required for onramp")
    
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


@router.post("/onramp/execute", response_model=dict)
async def execute_onramp(
    request: UserRampRequest,
    current_user: dict = Depends(require_kyc_approved)
):
    """Execute onramp transaction for logged-in users with APPROVED KYC."""
    if not request.wallet_address:
        raise HTTPException(status_code=400, detail="wallet_address is required for onramp")
    
    result, error = await ramp_service.execute_onramp(
        quote_id=request.quote_id,
        wallet_address=request.wallet_address,
        user_id=current_user["user_id"]
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return result.model_dump()


@router.post("/offramp/quote", response_model=QuoteResponse)
async def create_offramp_quote(
    request: UserQuoteRequest,
    current_user: dict = Depends(require_kyc_approved)
):
    """Create an offramp quote (Crypto -> EUR) for logged-in users with APPROVED KYC."""
    if not request.crypto_amount:
        raise HTTPException(status_code=400, detail="crypto_amount is required for offramp")
    
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


@router.post("/offramp/execute", response_model=dict)
async def execute_offramp(
    request: UserRampRequest,
    current_user: dict = Depends(require_kyc_approved)
):
    """Execute offramp transaction for logged-in users with APPROVED KYC."""
    if not request.bank_account:
        raise HTTPException(status_code=400, detail="bank_account is required for offramp")
    
    result, error = await ramp_service.execute_offramp(
        quote_id=request.quote_id,
        bank_account=request.bank_account,
        user_id=current_user["user_id"]
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return result.model_dump()


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(current_user: dict = Depends(get_current_user)):
    """Get transaction history for logged-in user."""
    transactions = await ramp_service.get_user_transactions(current_user["user_id"])
    return transactions
