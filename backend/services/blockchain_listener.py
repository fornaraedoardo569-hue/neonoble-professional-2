"""
BSC Blockchain Listener for NENO BEP-20 Token Transfers.

Monitors deposit addresses for incoming NENO transfers
and triggers the appropriate callbacks when detected.
"""

import os
import asyncio
import logging
from typing import Optional, Callable, Dict, List
from datetime import datetime, timezone
from decimal import Decimal
from web3 import Web3
from web3.exceptions import Web3Exception
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

# NENO Token Contract on BSC
NENO_CONTRACT_ADDRESS = "0xeF3F5C1892A8d7A3304E4A15959E124402d69974"

# Standard BEP-20/ERC-20 Transfer event ABI
TRANSFER_EVENT_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"}
        ],
        "name": "Transfer",
        "type": "event"
    }
]

# Minimal BEP-20 ABI for balance and decimals
BEP20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function"
    }
] + TRANSFER_EVENT_ABI


class BlockchainListener:
    """
    Polling-based blockchain listener for BSC NENO token transfers.
    
    Monitors active deposit addresses and detects incoming transfers.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.events_collection = db.blockchain_events
        self._web3: Optional[Web3] = None
        self._contract = None
        self._running = False
        self._poll_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
        self._last_block: int = 0
        self._token_decimals: int = 18  # Default, will be fetched
    
    def _get_web3(self) -> Web3:
        """Get or create Web3 instance."""
        if self._web3 is not None:
            return self._web3
        
        rpc_url = os.environ.get('BSC_RPC_URL')
        if not rpc_url:
            raise ValueError(
                "BSC_RPC_URL environment variable is not set. "
                "Please provide a valid BSC RPC endpoint."
            )
        
        self._web3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not self._web3.is_connected():
            raise ConnectionError(f"Failed to connect to BSC RPC: {rpc_url}")
        
        logger.info(f"Connected to BSC RPC")
        return self._web3
    
    def _get_contract(self):
        """Get NENO token contract instance."""
        if self._contract is not None:
            return self._contract
        
        web3 = self._get_web3()
        self._contract = web3.eth.contract(
            address=Web3.to_checksum_address(NENO_CONTRACT_ADDRESS),
            abi=BEP20_ABI
        )
        
        # Fetch token decimals
        try:
            self._token_decimals = self._contract.functions.decimals().call()
            symbol = self._contract.functions.symbol().call()
            logger.info(f"NENO token: {symbol}, decimals: {self._token_decimals}")
        except Exception as e:
            logger.warning(f"Could not fetch token info: {e}")
        
        return self._contract
    
    def get_required_confirmations(self) -> int:
        """Get required number of confirmations from env."""
        return int(os.environ.get('BSC_CONFIRMATIONS', '5'))
    
    def register_callback(self, callback: Callable):
        """Register a callback for when transfers are detected."""
        self._callbacks.append(callback)
    
    async def initialize(self):
        """Initialize the blockchain listener."""
        # Create indexes
        await self.events_collection.create_index("transaction_hash", unique=True)
        await self.events_collection.create_index("to_address")
        await self.events_collection.create_index("status")
        
        # Get current block
        try:
            web3 = self._get_web3()
            self._last_block = web3.eth.block_number
            logger.info(f"Blockchain listener initialized at block {self._last_block}")
        except Exception as e:
            logger.error(f"Failed to initialize blockchain listener: {e}")
    
    async def get_token_balance(self, address: str) -> Decimal:
        """Get NENO token balance for an address."""
        try:
            contract = self._get_contract()
            balance_wei = contract.functions.balanceOf(
                Web3.to_checksum_address(address)
            ).call()
            return Decimal(balance_wei) / Decimal(10 ** self._token_decimals)
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            return Decimal(0)
    
    async def check_address_for_transfers(
        self,
        address: str,
        from_block: int,
        to_block: int
    ) -> List[Dict]:
        """
        Check for NENO transfers to a specific address.
        
        Returns list of transfer events.
        """
        transfers = []
        
        try:
            contract = self._get_contract()
            web3 = self._get_web3()
            
            # Get Transfer events to this address
            transfer_filter = contract.events.Transfer.create_filter(
                from_block=from_block,
                to_block=to_block,
                argument_filters={'to': Web3.to_checksum_address(address)}
            )
            
            events = transfer_filter.get_all_entries()
            
            for event in events:
                tx_hash = event['transactionHash'].hex()
                block_number = event['blockNumber']
                
                # Get transaction receipt for confirmation count
                current_block = web3.eth.block_number
                confirmations = current_block - block_number
                
                amount_wei = event['args']['value']
                amount = Decimal(amount_wei) / Decimal(10 ** self._token_decimals)
                
                transfer = {
                    'transaction_hash': tx_hash,
                    'from_address': event['args']['from'].lower(),
                    'to_address': event['args']['to'].lower(),
                    'amount': float(amount),
                    'amount_wei': str(amount_wei),
                    'block_number': block_number,
                    'confirmations': confirmations,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                transfers.append(transfer)
                
                logger.info(
                    f"Found NENO transfer: {amount} NENO to {address} "
                    f"(tx: {tx_hash[:16]}..., {confirmations} confirmations)"
                )
            
        except Exception as e:
            logger.error(f"Error checking transfers for {address}: {e}")
        
        return transfers
    
    async def process_transfer(
        self,
        transfer: Dict,
        quote_id: str,
        expected_amount: float
    ) -> Dict:
        """
        Process a detected transfer.
        
        Validates:
        - Correct amount (no partial deposits)
        - Sufficient confirmations
        
        Returns processing result.
        """
        required_confirmations = self.get_required_confirmations()
        
        result = {
            'valid': False,
            'error': None,
            'transfer': transfer,
            'quote_id': quote_id
        }
        
        # Check confirmations
        if transfer['confirmations'] < required_confirmations:
            result['error'] = (
                f"Insufficient confirmations: {transfer['confirmations']}/{required_confirmations}"
            )
            result['status'] = 'PENDING_CONFIRMATIONS'
            return result
        
        # Check amount (with small tolerance for floating point)
        tolerance = 0.0001
        if abs(transfer['amount'] - expected_amount) > tolerance:
            result['error'] = (
                f"Amount mismatch: received {transfer['amount']}, expected {expected_amount}"
            )
            result['status'] = 'AMOUNT_MISMATCH'
            
            if transfer['amount'] < expected_amount:
                result['error'] = f"Partial deposit rejected: {transfer['amount']} < {expected_amount}"
                result['status'] = 'PARTIAL_DEPOSIT'
            
            return result
        
        # All validations passed
        result['valid'] = True
        result['status'] = 'CONFIRMED'
        
        # Store the event
        event_doc = {
            **transfer,
            'quote_id': quote_id,
            'expected_amount': expected_amount,
            'status': 'CONFIRMED',
            'processed_at': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await self.events_collection.update_one(
                {'transaction_hash': transfer['transaction_hash']},
                {'$set': event_doc},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to store event: {e}")
        
        return result
    
    async def poll_for_transfers(
        self,
        addresses_with_quotes: List[Dict],
        callback: Callable
    ):
        """
        Poll for transfers to a list of addresses.
        
        Args:
            addresses_with_quotes: List of {address, quote_id, expected_amount}
            callback: Async function to call when transfer is confirmed
        """
        try:
            web3 = self._get_web3()
            current_block = web3.eth.block_number
            
            # Look back 1000 blocks (~50 minutes on BSC)
            from_block = max(0, current_block - 1000)
            
            for item in addresses_with_quotes:
                address = item['address']
                quote_id = item['quote_id']
                expected_amount = item['expected_amount']
                
                # Check if already processed
                existing = await self.events_collection.find_one({
                    'to_address': address.lower(),
                    'quote_id': quote_id,
                    'status': 'CONFIRMED'
                })
                
                if existing:
                    continue
                
                # Check for transfers
                transfers = await self.check_address_for_transfers(
                    address, from_block, current_block
                )
                
                for transfer in transfers:
                    result = await self.process_transfer(
                        transfer, quote_id, expected_amount
                    )
                    
                    if result['valid']:
                        # Trigger callback
                        await callback(result)
                        break
                    elif result.get('status') == 'PENDING_CONFIRMATIONS':
                        logger.info(
                            f"Transfer pending confirmations for {quote_id}: "
                            f"{transfer['confirmations']}/{self.get_required_confirmations()}"
                        )
        
        except Exception as e:
            logger.error(f"Error polling for transfers: {e}")
    
    async def start_polling(self, get_active_quotes: Callable, on_transfer: Callable):
        """
        Start the polling loop.
        
        Args:
            get_active_quotes: Async function that returns list of active quotes with addresses
            on_transfer: Async callback when transfer is confirmed
        """
        self._running = True
        poll_interval = int(os.environ.get('BSC_POLL_INTERVAL', '15'))  # seconds
        
        logger.info(f"Starting blockchain polling (interval: {poll_interval}s)")
        
        while self._running:
            try:
                # Get active quotes with deposit addresses
                active_quotes = await get_active_quotes()
                
                if active_quotes:
                    await self.poll_for_transfers(active_quotes, on_transfer)
                
            except Exception as e:
                logger.error(f"Polling error: {e}")
            
            await asyncio.sleep(poll_interval)
    
    def stop_polling(self):
        """Stop the polling loop."""
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
