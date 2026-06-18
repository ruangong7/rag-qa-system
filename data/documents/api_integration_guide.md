# API Integration Guide v2.3

## Overview
This guide describes the standard patterns for integrating third-party services
with the Enterprise Knowledge Management Platform (EKMP).

## Authentication
All API requests require authentication via OAuth 2.0 Bearer tokens.
Tokens are obtained through the `/oauth/token` endpoint using client credentials grant.

```bash
curl -X POST https://api.example.com/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=YOUR_ID&client_secret=YOUR_SECRET"
```

Token expiry: 3600 seconds (1 hour). Clients must implement token refresh logic.

## Rate Limiting
- Standard tier: 100 requests per minute per API key
- Premium tier: 1000 requests per minute per API key
- Rate limit headers are included in all responses:
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Unix timestamp when the window resets

When rate limited, the API returns HTTP 429 with a `Retry-After` header.

## Error Handling
All error responses follow the standard format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error description",
    "request_id": "uuid-for-tracing"
  }
}
```

Common error codes:
- `AUTHENTICATION_FAILED`: Invalid or expired token
- `AUTHORIZATION_FAILED`: Insufficient permissions
- `VALIDATION_ERROR`: Invalid request parameters
- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INTERNAL_ERROR`: Unexpected server error

## Pagination
List endpoints support cursor-based pagination:
- Request: `GET /api/v1/resources?limit=50&cursor=abc123`
- Response includes `next_cursor` for fetching the next page
- Maximum page size: 200 items

## Webhooks
The platform supports webhook notifications for asynchronous events.
Webhook endpoints must:
- Respond with HTTP 200 within 5 seconds
- Verify webhook signatures using HMAC-SHA256
- Implement idempotency (retries may deliver the same event multiple times)

Webhook retry schedule: 1s, 5s, 25s, 125s, 625s (exponential backoff with jitter).
