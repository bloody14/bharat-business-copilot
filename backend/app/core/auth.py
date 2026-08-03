"""Clerk JWT authentication and organization role authorization."""
from functools import lru_cache
import logging
from fastapi import HTTPException, Request
from pydantic import BaseModel
from jwt import PyJWKClient, decode
from jwt.exceptions import InvalidTokenError, PyJWKClientError
from app.core.config import get_settings

logger = logging.getLogger(__name__)
class Principal(BaseModel): organization_id: str; user_id: str; role: str = "viewer"

@lru_cache
def jwks() -> PyJWKClient:
    settings=get_settings()
    if not settings.clerk_issuer_url: raise RuntimeError("CLERK_ISSUER_URL is required")
    return PyJWKClient(settings.clerk_jwks_url or f"{settings.clerk_issuer_url.rstrip('/')}/.well-known/jwks.json")

def get_principal(request: Request) -> Principal:
    header=request.headers.get("Authorization", "")
    if not header.startswith("Bearer "): raise HTTPException(401,"Missing bearer token")
    settings=get_settings()
    if not settings.clerk_issuer_url: raise HTTPException(503,"Authentication is not configured")
    try:
        token=header.removeprefix("Bearer "); key=jwks().get_signing_key_from_jwt(token)
        claims=decode(token,key.key,algorithms=["RS256"],audience=settings.clerk_audience,issuer=settings.clerk_issuer_url,options={"verify_aud": bool(settings.clerk_audience)})
    except PyJWKClientError as error:
        logger.error(f"PyJWKClient failed. Reason: {type(error).__name__}: {str(error)}")
        raise HTTPException(401,"Invalid token") from error
    except InvalidTokenError as error:
        logger.error(f"JWT Verification failed. Reason: {type(error).__name__}: {str(error)}")
        raise HTTPException(401,"Invalid token") from error
    organization=claims.get("o") or {}
    org=organization.get("id") or claims.get("org_id")
    role=organization.get("rol") or claims.get("org_role")
    if not org or not role: raise HTTPException(403,"An active organization and role are required")
    return Principal(organization_id=org,user_id=claims["sub"],role=role.removeprefix("org:"))
