import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


client = TestClient(app)


class TestAPI:
    def test_root(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data

    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_stock_analyze_missing_symbol(self):
        response = client.post("/api/stock/analyze", json={"symbol": ""})
        assert response.status_code == 500

    def test_knowledge_query(self):
        response = client.get("/api/knowledge/query?query=腾讯")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_orchestrate_endpoint(self):
        response = client.post("/api/orchestrate", json={
            "symbols": ["00700"],
            "investment_amount": 100000,
            "risk_preference": "moderate",
            "market": "hk"
        })
        assert response.status_code == 200
