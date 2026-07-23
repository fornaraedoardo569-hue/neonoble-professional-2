"""
Stripe SEPA Payout Service for NeoNoble Ramp.

PRODUCTION-READY implementation for SEPA bank transfers
after successful crypto deposits.

Environment Variables:
- STRIPE_SECRET_KEY: Stripe API secret key (required)
- STRIPE_WEBHOOK_SECRET: Webhook signing secret (optional)
- STRIPE_PAYOUT_MODE: 'live' or 'test' (default: 'live')
- STRIPE_PAYOUT_IBAN: Destination IBAN
- STRIPE_PAYOUT_BENEFICIARY_NAME: Beneficiary name
"""

import os
import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone
import stripe
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class StripePayoutService:
    """
    Stripe integration for SEPA payouts.
    
    Handles creating payouts to the configured IBAN after
    crypto deposits are confirmed on-chain.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.payouts_collection = db.stripe_payouts
        self._initialized = False
        self._stripe_configured = False
    
    def _get_config(self) -> Dict:
        """Get payout configuration from environment."""
        return {
            'iban': os.environ.get('STRIPE_PAYOUT_IBAN', 'IT22B0200822800000103317304'),
            'beneficiary_name': os.environ.get('STRIPE_PAYOUT_BENEFICIARY_NAME', 'Massimo Fornara'),
            'mode': os.environ.get('STRIPE_PAYOUT_MODE', 'live'),
            'webhook_secret': os.environ.get('STRIPE_WEBHOOK_SECRET')
        }
    
    def _initialize_stripe(self) -> bool:
        """
        Initialize Stripe with API key from environment.
        
        Returns True if initialized successfully, False otherwise.
        """
        if self._stripe_configured:
            return True
        
        api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not api_key:
            logger.error(
                "STRIPE_SECRET_KEY not set. Stripe payouts are DISABLED. "
                "Set this environment variable with your live Stripe key."
            )
            return False
        
        stripe.api_key = api_key
        self._stripe_configured = True
        
        config = self._get_config()
        logger.info(
            f"Stripe initialized in {config['mode'].upper()} mode. "
            f"Payouts will go to: {config['beneficiary_name']} ({config['iban'][:8]}...)"
        )
        return True
    
    async def initialize(self):
        """Initialize the payout service."""
        # Create indexes
        await self.payouts_collection.create_index("payout_id", unique=True, sparse=True)
        await self.payouts_collection.create_index("quote_id", unique=True)
        await self.payouts_collection.create_index("transaction_id")
        await self.payouts_collection.create_index("status")
        await self.payouts_collection.create_index("created_at")
        
        # Check Stripe configuration
        self._initialize_stripe()
        self._initialized = True
    
    def is_available(self) -> bool:
        """Check if Stripe payouts are available."""
        return self._initialize_stripe()
    
    async def create_payout(
        self,
        quote_id: str,
        transaction_id: str,
        amount_eur: float,
        reference: str = None
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Create a SEPA payout via Stripe.

        Orchestrates: idempotency check → record preparation → Stripe API call → persistence.
        """
        existing = await self._find_existing_payout(quote_id)
        if existing:
            logger.warning(f"Payout already exists for quote {quote_id}: {existing.get('payout_id')}")
            return existing, None

        payout_record = self._build_payout_record(
            quote_id=quote_id,
            transaction_id=transaction_id,
            amount_eur=amount_eur,
            reference=reference,
        )

        if not self._initialize_stripe():
            return await self._persist_failure(
                payout_record,
                "STRIPE_SECRET_KEY not configured - payout cannot be processed",
                log_prefix=f"Stripe not configured - payout FAILED for quote {quote_id}",
            )

        return await self._execute_stripe_payout(payout_record)

    async def _find_existing_payout(self, quote_id: str) -> Optional[Dict]:
        """Return any in-flight/successful payout for this quote, else None."""
        return await self.payouts_collection.find_one({
            'quote_id': quote_id,
            'status': {'$in': ['pending', 'paid', 'in_transit', 'processing']},
        })

    def _build_payout_record(
        self,
        quote_id: str,
        transaction_id: str,
        amount_eur: float,
        reference: Optional[str],
    ) -> Dict:
        """Assemble the MongoDB payout record (not yet persisted)."""
        config = self._get_config()
        return {
            'quote_id': quote_id,
            'transaction_id': transaction_id,
            'amount_eur': amount_eur,
            'amount_cents': int(amount_eur * 100),
            'iban': config['iban'],
            'beneficiary_name': config['beneficiary_name'],
            'reference': reference or f"NENO-{quote_id[:8]}",
            'mode': config['mode'],
            'status': 'pending',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'payout_id': None,
            'stripe_response': None,
            'error': None,
        }

    async def _execute_stripe_payout(
        self, payout_record: Dict
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """Call Stripe to create the payout and persist the result."""
        quote_id = payout_record['quote_id']
        amount_eur = payout_record['amount_eur']

        try:
            logger.info(
                f"Creating Stripe payout: €{amount_eur} to {payout_record['beneficiary_name']} "
                f"(IBAN: {payout_record['iban'][:8]}...) [Quote: {quote_id}]"
            )

            payout = stripe.Payout.create(
                amount=payout_record['amount_cents'],
                currency='eur',
                description=f"NeoNoble Ramp - {payout_record['reference']}",
                statement_descriptor="NEONOBLE RAMP",
                metadata={
                    'quote_id': quote_id,
                    'transaction_id': payout_record['transaction_id'],
                    'iban': payout_record['iban'],
                    'beneficiary': payout_record['beneficiary_name'],
                    'source': 'neonoble_ramp',
                    'mode': payout_record['mode'],
                },
            )

            payout_record.update({
                'payout_id': payout.id,
                'status': payout.status,
                'stripe_response': {
                    'id': payout.id,
                    'object': payout.object,
                    'status': payout.status,
                    'amount': payout.amount,
                    'currency': payout.currency,
                    'arrival_date': payout.arrival_date,
                    'created': payout.created,
                    'method': payout.method,
                    'type': payout.type,
                },
                'processed_at': datetime.now(timezone.utc).isoformat(),
            })

            await self.payouts_collection.insert_one(payout_record)
            logger.info(
                f"✓ Stripe payout CREATED: {payout.id} - €{amount_eur} to {payout_record['iban']} "
                f"(Status: {payout.status}, Arrival: {payout.arrival_date})"
            )
            return payout_record, None

        except stripe.error.AuthenticationError:
            return await self._persist_failure(
                payout_record,
                "Stripe AuthenticationError: Invalid API key",
                log_prefix=f"Payout failed for {quote_id}",
            )
        except stripe.error.InvalidRequestError as e:
            return await self._persist_failure(
                payout_record,
                f"Stripe InvalidRequestError: {str(e)}",
                log_prefix=f"Payout failed for {quote_id}",
            )
        except stripe.error.StripeError as e:
            return await self._persist_failure(
                payout_record,
                f"Stripe Error: {str(e)}",
                log_prefix=f"Payout failed for {quote_id}",
            )
        except Exception as e:
            return await self._persist_failure(
                payout_record,
                f"Unexpected error: {str(e)}",
                log_prefix=f"Payout failed for {quote_id}",
            )

    async def _persist_failure(
        self,
        payout_record: Dict,
        error_msg: str,
        log_prefix: str,
    ) -> Tuple[Optional[Dict], str]:
        """Mark a payout record as failed, persist it, and return the failure tuple."""
        payout_record['status'] = 'failed'
        payout_record['error'] = error_msg
        await self.payouts_collection.insert_one(payout_record)
        logger.error(f"{log_prefix}: {error_msg}")
        # Preserve previous behaviour: configuration-failure returns (None, msg);
        # Stripe-call failures return (payout_record, msg).
        if "STRIPE_SECRET_KEY not configured" in error_msg:
            return None, error_msg
        return payout_record, error_msg
    
    async def handle_webhook(self, payload: bytes, sig_header: str) -> Tuple[bool, Optional[str]]:
        """
        Handle Stripe webhook events.
        
        Args:
            payload: Raw webhook payload
            sig_header: Stripe-Signature header value
            
        Returns:
            Tuple of (success, error_message)
        """
        config = self._get_config()
        webhook_secret = config['webhook_secret']
        
        if not webhook_secret:
            logger.warning("STRIPE_WEBHOOK_SECRET not configured - webhook verification skipped")
            return False, "Webhook secret not configured"
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            return False, "Invalid payload"
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            return False, "Invalid signature"
        
        # Handle the event
        event_type = event['type']
        data = event['data']['object']
        
        logger.info(f"Received Stripe webhook: {event_type}")
        
        if event_type == 'payout.paid':
            await self._handle_payout_paid(data)
        elif event_type == 'payout.failed':
            await self._handle_payout_failed(data)
        elif event_type == 'payout.canceled':
            await self._handle_payout_canceled(data)
        
        return True, None
    
    async def _handle_payout_paid(self, payout_data: dict):
        """Handle payout.paid webhook event."""
        payout_id = payout_data['id']
        
        result = await self.payouts_collection.update_one(
            {'payout_id': payout_id},
            {
                '$set': {
                    'status': 'paid',
                    'paid_at': datetime.now(timezone.utc).isoformat(),
                    'arrival_date': payout_data.get('arrival_date')
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"✓ Payout {payout_id} marked as PAID")
        else:
            logger.warning(f"Payout {payout_id} not found in database")
    
    async def _handle_payout_failed(self, payout_data: dict):
        """Handle payout.failed webhook event."""
        payout_id = payout_data['id']
        failure_message = payout_data.get('failure_message', 'Unknown failure')
        
        result = await self.payouts_collection.update_one(
            {'payout_id': payout_id},
            {
                '$set': {
                    'status': 'failed',
                    'error': failure_message,
                    'failed_at': datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.error(f"✗ Payout {payout_id} FAILED: {failure_message}")
    
    async def _handle_payout_canceled(self, payout_data: dict):
        """Handle payout.canceled webhook event."""
        payout_id = payout_data['id']
        
        result = await self.payouts_collection.update_one(
            {'payout_id': payout_id},
            {
                '$set': {
                    'status': 'canceled',
                    'canceled_at': datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.warning(f"Payout {payout_id} was CANCELED")
    
    async def get_payout_status(self, payout_id: str) -> Optional[Dict]:
        """Get the current status of a payout from Stripe."""
        if not self._initialize_stripe():
            return None
        
        try:
            payout = stripe.Payout.retrieve(payout_id)
            return {
                'id': payout.id,
                'status': payout.status,
                'amount': payout.amount / 100,
                'currency': payout.currency,
                'arrival_date': payout.arrival_date,
                'failure_message': payout.failure_message
            }
        except stripe.error.StripeError as e:
            logger.error(f"Failed to get payout status: {e}")
            return None
    
    async def get_payout_by_quote(self, quote_id: str) -> Optional[Dict]:
        """Get payout record by quote ID."""
        return await self.payouts_collection.find_one({'quote_id': quote_id})
    
    async def get_payout_by_id(self, payout_id: str) -> Optional[Dict]:
        """Get payout record by Stripe payout ID."""
        return await self.payouts_collection.find_one({'payout_id': payout_id})
    
    async def list_payouts(self, limit: int = 50, status: str = None) -> list:
        """List recent payouts."""
        query = {}
        if status:
            query['status'] = status
        
        cursor = self.payouts_collection.find(query).sort('created_at', -1).limit(limit)
        return await cursor.to_list(length=limit)
    
    async def sync_payout_status(self, payout_id: str) -> Optional[Dict]:
        """
        Sync payout status from Stripe to database.
        
        Useful for manual reconciliation.
        """
        stripe_status = await self.get_payout_status(payout_id)
        if not stripe_status:
            return None
        
        await self.payouts_collection.update_one(
            {'payout_id': payout_id},
            {
                '$set': {
                    'status': stripe_status['status'],
                    'synced_at': datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return stripe_status
