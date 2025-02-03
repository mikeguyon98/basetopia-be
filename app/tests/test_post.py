# app/tests/test_posts.py
import pytest
from datetime import datetime


class TestPostEndpoints:
    """Test all post-related endpoints"""

    def test_get_user_posts(self, client, test_token):
        """Test getting user's own posts"""
        # Test basic fetch
        response = client.get(
            "/api/posts/me",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        assert "next_page_cursor" in data
        assert "page_size" in data

        # Test pagination
        response = client.get(
            "/api/posts/me?page_size=5",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["posts"]) <= 5

        # Test invalid token
        response = client.get(
            "/api/posts/me",
            headers={"Authorization": "Bearer invalid"}
        )
        assert response.status_code == 401

    def test_get_team_posts(self, client, test_token):
        """Test getting posts for followed teams"""
        response = client.get(
            "/api/posts/following/teams",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        assert "next_page_cursor" in data

        # Test pagination
        response = client.get(
            "/api/posts/following/teams?page_size=5",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["posts"]) <= 5

    def test_get_player_posts(self, client, test_token):
        """Test getting posts for followed players"""
        response = client.get(
            "/api/posts/following/players",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "posts" in data
        assert "next_page_cursor" in data

        # Test pagination
        response = client.get(
            "/api/posts/following/players?page_size=5",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["posts"]) <= 5

    def test_cursor_pagination(self, client, test_token):
        """Test cursor-based pagination functionality"""
        # Get first page
        response = client.get(
            "/api/posts/me?page_size=2",
            headers={"Authorization": test_token}
        )
        assert response.status_code == 200
        first_page = response.json()

        # If there's a next page
        if first_page["next_page_cursor"]:
            cursor = first_page["next_page_cursor"]
            # Get next page using cursor
            response = client.get(
                f"/api/posts/me?page_size=2&last_created_at={
                    cursor['created_at']}&last_id={cursor['id']}",
                headers={"Authorization": test_token}
            )
            assert response.status_code == 200
            second_page = response.json()

            # Ensure pages are different
            if first_page["posts"] and second_page["posts"]:
                assert first_page["posts"][0] != second_page["posts"][0]
