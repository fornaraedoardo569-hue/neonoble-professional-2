from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime
from models.transaction import Transaction
from services.auth_service import get_current_user
import hmac
import hashlib

router = APIRouter(prefix="/api/ramp", tags=["ramp"])

class TransakWebhook(BaseModel):
    event: str
    data: dict

# Secret per validare i webhook (imposta in .env)
TRANSAK_WEBHOOK_SECRET = "IL_TUO_SECRET_TRANSAK_QUI"

@router.post("/transak-webhook")
async def transak_webhook(request: Request, webhook: TransakWebhook, user=Depends(get_current_user)):
    """
    Riceve webhook da Transak e registra la transazione.
    """
    try:
        # Validazione base (opzionale ma consigliata)
        body = await request.body()
        signature = request.headers.get("X-Signature")
        # Puoi aggiungere controllo HMAC qui se Transak lo supporta

        event = webhook.event
        order = webhook.data

        if event in ["TRANSAK_ORDER_SUCCESSFUL", "order_successful"]:
            transaction = Transaction(
                user_id=user.id,
                type="onramp" if order.get("cryptoCurrency") else "offramp",
                amount_fiat=float(order.get("fiatAmount", 0)),
                currency_fiat=order.get("fiatCurrency"),
                amount_crypto=float(order.get("cryptoAmount", 0)),
                currency_crypto=order.get("cryptoCurrency"),
                transak_order_id=order.get("id") or order.get("orderId"),
                status="COMPLETED",
                timestamp=datetime.utcnow(),
                raw_data=order
            )
            
            await transaction.insert()
            
            return {"status": "success", "message": "Transazione registrata"}

        return {"status": "ignored", "event": event}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
