import httpx
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
import asyncio

logger = logging.getLogger(__name__)

# CoinGecko API configuration
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

# Fixed NENO price in EUR
NENO_PRICE_EUR = 10000.0

# Cache for prices (to avoid rate limiting)
_price_cache: Dict[str, tuple[float, datetime]] = {}
CACHE_TTL_SECONDS = 60  # Cache prices for 1 minute

# Mapping of our crypto codes to CoinGecko IDs
CRYPTO_TO_COINGECKO = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "USDC": "usd-coin",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "MATIC": "matic-network",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "UNI": "uniswap",
}

# Supported cryptocurrencies
SUPPORTED_CRYPTOS = list(CRYPTO_TO_COINGECKO.keys()) + ["NENO"]

# Fee configuration
FEE_PERCENTAGE = 1.5  # 1.5% fee


class PricingService:
    """Pricing service with real-time prices from CoinGecko and fixed NENO price."""
    
    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=10.0)
        return self._http_client
    
    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
    
    def _get_cached_price(self, crypto: str) -> Optional[float]:
        """Get price from cache if still valid."""
        if crypto in _price_cache:
            price, cached_at = _price_cache[crypto]
            if datetime.now(timezone.utc) - cached_at < timedelta(seconds=CACHE_TTL_SECONDS):
                return price
        return None
    
    def _cache_price(self, crypto: str, price: float):
        """Cache a price."""
        _price_cache[crypto] = (price, datetime.now(timezone.utc))
    
    async def get_price_eur(self, crypto: str) -> float:
        """Get the price of a cryptocurrency in EUR.
        
        Args:
            crypto: Cryptocurrency code (BTC, ETH, NENO, etc.)
        
        Returns:
            Price in EUR
        
        Raises:
            ValueError: If cryptocurrency is not supported
        """
        crypto = crypto.upper()
        
        # NENO has a fixed price
        if crypto == "NENO":
            return NENO_PRICE_EUR
        
        # Check if supported
        if crypto not in CRYPTO_TO_COINGECKO:
            raise ValueError(f"Unsupported cryptocurrency: {crypto}. Supported: {SUPPORTED_CRYPTOS}")
        
        # Check cache
        cached_price = self._get_cached_price(crypto)
        if cached_price is not None:
            logger.debug(f"Using cached price for {crypto}: {cached_price} EUR")
            return cached_price
        
        # Fetch from CoinGecko
        try:
            coingecko_id = CRYPTO_TO_COINGECKO[crypto]
            client = await self.get_http_client()
            
            response = await client.get(
                f"{COINGECKO_API_URL}/simple/price",
                params={
                    "ids": coingecko_id,
                    "vs_currencies": "eur"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            price = data[coingecko_id]["eur"]
            self._cache_price(crypto, price)
            logger.info(f"Fetched price for {crypto}: {price} EUR")
            return price
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch price from CoinGecko: {e}")
            # Return cached price even if expired, as fallback
            if crypto in _price_cache:
                price, _ = _price_cache[crypto]
                logger.warning(f"Using expired cached price for {crypto}: {price} EUR")
                return price
            raise ValueError(f"Unable to fetch price for {crypto}")
    
    async def get_all_prices_eur(self) -> Dict[str, float]:
        """Get prices for all supported cryptocurrencies."""
        prices = {"NENO": NENO_PRICE_EUR}
        
        # Fetch all other prices from CoinGecko in one request
        try:
            coingecko_ids = ",".join(CRYPTO_TO_COINGECKO.values())
            client = await self.get_http_client()
            
            response = await client.get(
                f"{COINGECKO_API_URL}/simple/price",
                params={
                    "ids": coingecko_ids,
                    "vs_currencies": "eur"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            for crypto, coingecko_id in CRYPTO_TO_COINGECKO.items():
                if coingecko_id in data and "eur" in data[coingecko_id]:
                    price = data[coingecko_id]["eur"]
                    prices[crypto] = price
                    self._cache_price(crypto, price)
            
            logger.info(f"Fetched all prices: {len(prices)} currencies")
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch prices from CoinGecko: {e}")
            # Use cached prices as fallback
            for crypto in CRYPTO_TO_COINGECKO.keys():
                if crypto in _price_cache:
                    prices[crypto], _ = _price_cache[crypto]
        
        return prices
    
    def calculate_fee(self, fiat_amount: float) -> float:
        """Calculate fee for a transaction."""
        return round(fiat_amount * (FEE_PERCENTAGE / 100), 2)
    
    async def calculate_onramp_quote(
        self,
        fiat_amount: float,
        crypto: str,
        fiat_currency: str = "EUR"
    ) -> dict:
        """Calculate onramp quote (Fiat -> Crypto).
        
        User pays fiat_amount + fee, receives crypto.
        """
        price = await self.get_price_eur(crypto)
        fee = self.calculate_fee(fiat_amount)
        crypto_amount = fiat_amount / price
        
        return {
            "fiat_amount": fiat_amount,
            "fiat_currency": fiat_currency,
            "crypto_amount": round(crypto_amount, 8),
            "crypto_currency": crypto,
            "exchange_rate": price,
            "fee_amount": fee,
            "fee_currency": fiat_currency,
            "fee_percentage": FEE_PERCENTAGE,
            "total_fiat": round(fiat_amount + fee, 2),
            "price_source": "fixed" if crypto == "NENO" else "coingecko"
        }
    
    async def calculate_offramp_quote(
        self,
        crypto_amount: float,
        crypto: str,
        fiat_currency: str = "EUR"
    ) -> dict:
        """Calculate offramp quote (Crypto -> Fiat).
        
        User sends crypto, receives fiat_amount - fee.
        """
        price = await self.get_price_eur(crypto)
        fiat_amount = crypto_amount * price
        fee = self.calculate_fee(fiat_amount)
        
        return {
            "fiat_amount": round(fiat_amount, 2),
            "fiat_currency": fiat_currency,
            "crypto_amount": crypto_amount,
            "crypto_currency": crypto,
            "exchange_rate": price,
            "fee_amount": fee,
            "fee_currency": fiat_currency,
            "fee_percentage": FEE_PERCENTAGE,
            "total_fiat": round(fiat_amount - fee, 2),  # User receives this
            "price_source": "fixed" if crypto == "NENO" else "coingecko"
        }


# Singleton instance
pricing_service = PricingService()
