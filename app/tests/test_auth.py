# app/tests/test_auth.py
def test_auth_required(client):
    """Test endpoints require authentication"""
    endpoints = [
        "/api/posts/me",
        "/api/posts/following/teams",
        "/api/posts/following/players"
    ]

    for endpoint in endpoints:
        # Test without token
        response = client.get(endpoint)
        # Accept either unauthorized or forbidden
        assert response.status_code in [401, 403]

        # Test with invalid token
        response = client.get(
            endpoint,
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code in [401, 403]
