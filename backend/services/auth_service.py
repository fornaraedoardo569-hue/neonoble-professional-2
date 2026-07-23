from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from datetime import datetime, timezone
import logging

from models.user import User, UserCreate, UserResponse, UserRole
from utils.password import hash_password, verify_password
from utils.jwt_utils import create_access_token, create_refresh_token, create_password_reset_token
import uuid

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.users
    
    @staticmethod
    def _normalize_email(email: str) -> str:
        """Canonicalise an email so lookups are case-insensitive.
        Pydantic's EmailStr lowercases the domain but keeps the local part as-is,
        which leads to subtle 'user not found' bugs when the same human types
        their email with slightly different casing across register/login.
        """
        return (email or "").strip().lower()

    async def register(self, user_data: UserCreate) -> tuple[Optional[User], Optional[str]]:
        """Register a new user.
        
        Returns:
            Tuple of (User, None) on success, or (None, error_message) on failure
        """
        try:
            email = self._normalize_email(user_data.email)
            # Check if email already exists
            existing = await self.collection.find_one({"email": email})
            if existing:
                logger.warning(f"Registration failed: email already exists - {email}")
                return None, "Email already registered"
            
            # Create user
            password_hash = hash_password(user_data.password)
            user = User(
                email=email,
                password_hash=password_hash,
                role=user_data.role
            )
            
            # Save to database
            user_dict = user.model_dump()
            user_dict['created_at'] = user_dict['created_at'].isoformat()
            user_dict['updated_at'] = user_dict['updated_at'].isoformat()
            
            await self.collection.insert_one(user_dict)
            logger.info(f"User registered successfully: {user.email} (role: {user.role})")
            
            return user, None
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return None, f"Registration failed: {str(e)}"
    
    async def login(self, email: str, password: str) -> tuple[Optional[dict], Optional[str]]:
        """Login a user.
        
        Returns:
            Tuple of ({access_token, refresh_token, user_id, email, role}, None) on success,
            or (None, error_message) on failure
        """
        try:
            email = self._normalize_email(email)
            # Find user
            user_doc = await self.collection.find_one({"email": email})
            if not user_doc:
                logger.warning(f"Login failed: user not found - {email}")
                return None, "Invalid email or password"
            
            # Verify password
            if not verify_password(password, user_doc['password_hash']):
                logger.warning(f"Login failed: incorrect password - {email}")
                return None, "Invalid email or password"
            
            # Check if active
            if not user_doc.get('is_active', True):
                logger.warning(f"Login failed: user inactive - {email}")
                return None, "Account is deactivated"
            
            tokens = self._issue_tokens(user_doc)
            logger.info(f"User logged in: {email}")
            return tokens, None
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None, f"Login failed: {str(e)}"

    def _issue_tokens(self, user_doc: dict) -> dict:
        """Issue a fresh access + refresh token pair for a user document."""
        access_token = create_access_token(
            user_id=user_doc['id'],
            email=user_doc['email'],
            role=user_doc['role'],
        )
        refresh_token = create_refresh_token(
            user_id=user_doc['id'],
            email=user_doc['email'],
            role=user_doc['role'],
        )
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user_id': user_doc['id'],
            'email': user_doc['email'],
            'role': user_doc['role'],
        }

    async def refresh_tokens(self, user_id: str) -> Optional[dict]:
        """Issue a new token pair for the given user_id (used by /auth/refresh)."""
        user_doc = await self.collection.find_one({"id": user_id})
        if not user_doc or not user_doc.get('is_active', True):
            return None
        return self._issue_tokens(user_doc)

    async def issue_password_reset_token(self, email: str) -> Optional[tuple[str, str]]:
        """Generate + persist a single-use password reset token.

        Returns (token, email) if the user exists, None otherwise.
        Caller is responsible for emailing the token. The endpoint MUST
        return the same response in both cases (no user enumeration).
        """
        email = self._normalize_email(email)
        user_doc = await self.collection.find_one({"email": email})
        if not user_doc or not user_doc.get('is_active', True):
            return None
        jti = uuid.uuid4().hex
        token = create_password_reset_token(user_id=user_doc['id'], jti=jti)
        await self.collection.update_one(
            {"id": user_doc['id']},
            {"$set": {
                "password_reset_jti": jti,
                "password_reset_requested_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        return token, user_doc['email']

    async def reset_password_with_token(self, payload: dict, new_password: str) -> tuple[bool, Optional[str]]:
        """Consume a password-reset token and update the user's password.
        Single-use: the stored jti must match the token's jti, and is cleared on success.
        """
        if len(new_password) < 8:
            return False, "Password must be at least 8 characters"
        user_id = payload.get('sub')
        token_jti = payload.get('jti')
        if not user_id or not token_jti:
            return False, "Invalid token"
        user_doc = await self.collection.find_one({"id": user_id})
        if not user_doc:
            return False, "Invalid token"
        if user_doc.get('password_reset_jti') != token_jti:
            return False, "Reset link has already been used or is no longer valid"
        new_hash = hash_password(new_password)
        # Update password, clear the single-use jti, and bump token_version to
        # implicitly invalidate any in-flight refresh tokens (best-effort).
        new_token_version = int(user_doc.get('token_version', 0)) + 1
        await self.collection.update_one(
            {"id": user_id},
            {"$set": {
                "password_hash": new_hash,
                "password_reset_jti": None,
                "token_version": new_token_version,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"Password reset successful for user {user_id}")
        return True, None

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> tuple[bool, Optional[str]]:
        """Change password for a logged-in user (requires the current password)."""
        if len(new_password) < 8:
            return False, "New password must be at least 8 characters"
        user_doc = await self.collection.find_one({"id": user_id})
        if not user_doc:
            return False, "User not found"
        if not verify_password(current_password, user_doc['password_hash']):
            return False, "Current password is incorrect"
        new_hash = hash_password(new_password)
        new_token_version = int(user_doc.get('token_version', 0)) + 1
        await self.collection.update_one(
            {"id": user_id},
            {"$set": {
                "password_hash": new_hash,
                "token_version": new_token_version,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        )
        logger.info(f"Password changed for user {user_id}")
        return True, None
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        user_doc = await self.collection.find_one({"id": user_id})
        if user_doc:
            # Convert ISO strings back to datetime
            if isinstance(user_doc.get('created_at'), str):
                user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
            if isinstance(user_doc.get('updated_at'), str):
                user_doc['updated_at'] = datetime.fromisoformat(user_doc['updated_at'])
            return User(**user_doc)
        return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        email = self._normalize_email(email)
        user_doc = await self.collection.find_one({"email": email})
        if user_doc:
            if isinstance(user_doc.get('created_at'), str):
                user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
            if isinstance(user_doc.get('updated_at'), str):
                user_doc['updated_at'] = datetime.fromisoformat(user_doc['updated_at'])
            return User(**user_doc)
        return None
    
    def user_to_response(self, user: User) -> UserResponse:
        """Convert User to UserResponse (without sensitive data)."""
        return UserResponse(
            id=user.id,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at
        )
