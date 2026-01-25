#!/usr/bin/env python3
"""
Generate test JWT tokens for authentication testing.

This script creates mock JWT tokens that mimic Clerk's format for testing purposes.
Note: These are for TESTING ONLY - they won't work with real Clerk validation.

Usage:
    python scripts/generate_test_jwt.py                    # Generate valid token with default user
    python scripts/generate_test_jwt.py --user-id test123  # Custom user ID
    python scripts/generate_test_jwt.py --expires-in 60    # Expires in 60 seconds
    python scripts/generate_test_jwt.py --expired          # Generate already-expired token
"""

import argparse
import json
from datetime import datetime, timedelta

from jose import jwt


def generate_test_jwt(
    user_id: str = "test_user_123",
    expires_in: int = 3600,
    issuer: str = "https://clerk.example.com",
    secret: str = "test-secret-key-for-development-only",
) -> str:
    """
    Generate a test JWT token.

    Args:
        user_id: User ID to embed in 'sub' claim
        expires_in: Seconds until token expires (use negative for expired token)
        issuer: JWT issuer claim
        secret: Secret key for signing (HS256 for testing)

    Returns:
        str: Signed JWT token
    """
    now = datetime.utcnow()

    # Create payload with standard JWT claims
    payload = {
        "sub": user_id,  # Subject (user ID) - Clerk format
        "iss": issuer,   # Issuer
        "iat": int(now.timestamp()),  # Issued at
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),  # Expiry
        "azp": "http://localhost:3000",  # Authorized party (frontend URL)
        "sid": "sess_test123",  # Session ID
    }

    # Sign token with HS256 (for testing - Clerk uses RS256)
    token = jwt.encode(payload, secret, algorithm="HS256")

    return token


def decode_test_jwt(token: str, secret: str = "test-secret-key-for-development-only", verify_exp: bool = True) -> dict:
    """
    Decode and verify a test JWT token.

    Args:
        token: JWT token string
        secret: Secret key used for signing
        verify_exp: Whether to verify token expiration

    Returns:
        dict: Decoded payload
    """
    options = {"verify_exp": verify_exp}
    payload = jwt.decode(token, secret, algorithms=["HS256"], options=options)
    return payload


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate test JWT tokens for authentication testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate valid token:
    python scripts/generate_test_jwt.py

  Custom user ID:
    python scripts/generate_test_jwt.py --user-id user_abc123

  Short-lived token (expires in 60 seconds):
    python scripts/generate_test_jwt.py --expires-in 60

  Already-expired token:
    python scripts/generate_test_jwt.py --expired

  Save to file:
    python scripts/generate_test_jwt.py > token.txt
        """
    )

    parser.add_argument(
        "--user-id",
        default="test_user_123",
        help="User ID to embed in token (default: test_user_123)"
    )

    parser.add_argument(
        "--expires-in",
        type=int,
        default=3600,
        help="Seconds until token expires (default: 3600 = 1 hour)"
    )

    parser.add_argument(
        "--expired",
        action="store_true",
        help="Generate already-expired token (expires 1 hour ago)"
    )

    parser.add_argument(
        "--decode",
        action="store_true",
        help="Also decode and display token payload"
    )

    args = parser.parse_args()

    # Override expires_in if --expired flag is used
    if args.expired:
        expires_in = -3600  # 1 hour ago
    else:
        expires_in = args.expires_in

    # Generate token
    token = generate_test_jwt(
        user_id=args.user_id,
        expires_in=expires_in
    )

    # Print token
    print(f"\n{'='*80}")
    print("TEST JWT TOKEN GENERATED")
    print(f"{'='*80}")
    print(f"\nToken:\n{token}\n")

    # Decode and display payload if requested
    if args.decode:
        payload = decode_test_jwt(token)

        print(f"{'='*80}")
        print("DECODED PAYLOAD")
        print(f"{'='*80}")
        # Show expiry info
        exp_timestamp = payload.get("exp", 0)
        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        now = datetime.utcnow()

        print(f"\n{'='*80}")
        print("EXPIRY INFO")
        print(f"{'='*80}")
        print(
            f"Issued:  {datetime.utcfromtimestamp(payload.get('iat', 0)).isoformat()}Z")
        print(f"Expires: {exp_datetime.isoformat()}Z")

        if exp_datetime < now:
            print(
                f"Status:  ❌ EXPIRED ({int((now - exp_datetime).total_seconds())}s ago)")
        else:
            print(
                f"Status:  ✅ VALID (expires in {int((exp_datetime - now).total_seconds())}s)")
            print(
                f"Status:  ✅ VALID (expires in {int((exp_datetime - now).total_seconds())}s)")

    # Usage example
    print(f"\n{'='*80}")
    print("USAGE EXAMPLE")
    print(f"{'='*80}")
    print(f"\ncurl -H 'Authorization: Bearer {token}' \\")
    print(f"     http://localhost:8000/api/v1/documents\n")

    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
