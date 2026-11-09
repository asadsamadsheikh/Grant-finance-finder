"""
IBM Cloud Object Storage (COS) Cache Service
Uses IBM COS Lite plan (FREE) to persist grant data, avoid redundant API calls,
and store generated proposals for retrieval.
"""

import os
import json
import logging
import time
from typing import Optional, Any
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class IBMCOSCacheService:
    """
    IBM Cloud Object Storage integration for persistent grant caching.
    IBM COS Lite: 25GB storage + 20GB outbound FREE per month.
    Falls back to in-memory cache when COS is not configured.
    """

    IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

    def __init__(self):
        self.api_key = os.getenv("IBM_COS_API_KEY", "")
        self.instance_crn = os.getenv("IBM_COS_INSTANCE_CRN", "")
        self.bucket = os.getenv("IBM_COS_BUCKET_NAME", "grant-finder-cache")
        self.endpoint = os.getenv("IBM_COS_ENDPOINT", "https://s3.us-south.cloud-object-storage.appdomain.cloud")
        self.auth_endpoint = os.getenv("IBM_COS_AUTH_ENDPOINT", "https://iam.cloud.ibm.com/identity/token")
        self.ttl = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
        self._iam_token: Optional[str] = None
        self._token_expiry: float = 0.0
        # In-memory fallback cache
        self._memory_cache: dict[str, tuple[Any, float]] = {}

    def _is_cos_configured(self) -> bool:
        return bool(self.api_key and self.instance_crn)

    async def _get_iam_token(self) -> str:
        if self._iam_token and time.time() < self._token_expiry - 60:
            return self._iam_token
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                self.IAM_TOKEN_URL,
                data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": self.api_key},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            self._iam_token = data["access_token"]
            self._token_expiry = time.time() + data.get("expires_in", 3600)
            return self._iam_token

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve cached value. Returns None if expired or not found."""
        # Try in-memory first
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if time.time() < expiry:
                logger.debug(f"Memory cache HIT: {key}")
                return value
            else:
                del self._memory_cache[key]

        if not self._is_cos_configured():
            return None

        try:
            token = await self._get_iam_token()
            url = f"{self.endpoint}/{self.bucket}/{key}.json"
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}", "ibm-service-instance-id": self.instance_crn},
                )
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                cached = resp.json()
                if time.time() > cached.get("expiry", 0):
                    logger.debug(f"COS cache EXPIRED: {key}")
                    return None
                logger.debug(f"COS cache HIT: {key}")
                # Also populate memory cache
                self._memory_cache[key] = (cached["data"], cached["expiry"])
                return cached["data"]
        except Exception as e:
            logger.warning(f"COS get error for {key}: {e}")
            return None

    async def _ensure_bucket_exists(self, token: str) -> bool:
        """
        Create the COS bucket if it doesn't exist (404 on HEAD).
        IBM COS Lite: 25 GB free. Bucket names must be globally unique.
        Requires ibm-service-instance-id header for both HEAD and PUT.
        """
        try:
            bucket_url = f"{self.endpoint}/{self.bucket}"
            # Strip trailing '::' from CRN if present for the header
            crn = self.instance_crn.rstrip(":")
            headers = {
                "Authorization": f"Bearer {token}",
                "ibm-service-instance-id": crn,
            }
            async with httpx.AsyncClient(timeout=15) as client:
                head = await client.head(bucket_url, headers=headers)
                if head.status_code == 200:
                    return True  # Already exists
                if head.status_code in (404, 403):
                    # Create the bucket — must include instance CRN header
                    put = await client.put(
                        bucket_url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "ibm-service-instance-id": crn,
                            "Content-Length": "0",
                        },
                    )
                    if put.status_code in (200, 201, 204):
                        logger.info(f"COS bucket '{self.bucket}' created automatically")
                        return True
                    logger.warning(f"COS bucket create returned {put.status_code}: {put.text[:300]}")
                    return False
        except Exception as e:
            logger.warning(f"COS bucket check/create error: {e}")
            return False

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store value in cache with TTL."""
        ttl = ttl or self.ttl
        expiry = time.time() + ttl
        # Always store in memory
        self._memory_cache[key] = (value, expiry)

        if not self._is_cos_configured():
            return True

        try:
            token = await self._get_iam_token()
            await self._ensure_bucket_exists(token)
            url = f"{self.endpoint}/{self.bucket}/{key}.json"
            payload = json.dumps({"data": value, "expiry": expiry, "key": key})
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.put(
                    url,
                    content=payload.encode(),
                    headers={
                        "Authorization": f"Bearer {token}",
                        "ibm-service-instance-id": self.instance_crn,
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                logger.debug(f"COS cache SET: {key}")
                return True
        except Exception as e:
            logger.warning(f"COS set error for {key}: {e}")
            return False

    async def store_proposal(self, proposal_id: str, proposal_data: dict) -> bool:
        """Persist a generated proposal to COS for later retrieval."""
        return await self.set(f"proposal_{proposal_id}", proposal_data, ttl=86400 * 7)

    async def get_proposal(self, proposal_id: str) -> Optional[dict]:
        """Retrieve a previously generated proposal."""
        return await self.get(f"proposal_{proposal_id}")


# Singleton instance
cos_cache = IBMCOSCacheService()
