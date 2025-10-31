"""
Integration tests for complete API workflow
Tests: PDF upload → ingestion → query → results
"""

import pytest
import os
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def sample_pdf():
    """Create a sample PDF file for testing"""
    # In real scenario, use a real PDF
    # For now, we'll test with file upload structure
    content = b"%PDF-1.4 Sample PDF content for testing"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


class TestHealthCheck:
    """Test API health endpoint"""
    
    def test_health_endpoint(self):
        """Should return healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestIngestionAPI:
    """Test PDF ingestion endpoints"""
    
    def test_ingest_pdf_endpoint_exists(self, sample_pdf):
        """POST /api/v1/ingest endpoint exists"""
        with open(sample_pdf, "rb") as f:
            response = client.post(
                "/api/v1/ingest",
                files={"file": ("test.pdf", f, "application/pdf")},
                data={
                    "device_name": "Digitakt II",
                    "manufacturer": "Elektron"
                }
            )
        
        # Should return 200 or 202 (accepted)
        assert response.status_code in [200, 202, 422]  # 422 if validation fails
        
    def test_ingest_without_file(self):
        """Should reject request without file"""
        response = client.post(
            "/api/v1/ingest",
            data={
                "device_name": "Test Device",
                "manufacturer": "Test"
            }
        )
        
        assert response.status_code == 422
        
    def test_ingest_with_invalid_file_type(self):
        """Should reject non-PDF files"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"Not a PDF")
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "rb") as f:
                response = client.post(
                    "/api/v1/ingest",
                    files={"file": ("test.txt", f, "text/plain")},
                    data={
                        "device_name": "Test",
                        "manufacturer": "Test"
                    }
                )
            
            # Should reject
            assert response.status_code in [400, 422]
        finally:
            os.unlink(tmp_path)
    
    def test_get_ingestion_status(self):
        """GET /api/v1/ingest/status/{job_id}"""
        job_id = "test-job-123"
        response = client.get(f"/api/v1/ingest/status/{job_id}")
        
        # Should return 200 or 404
        assert response.status_code in [200, 404]
        

class TestQueryAPI:
    """Test documentation query endpoints"""
    
    def test_query_endpoint_exists(self):
        """POST /api/v1/query endpoint exists"""
        response = client.post(
            "/api/v1/query",
            json={
                "query": "How to connect MIDI devices?",
                "device_id": None
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        
    def test_query_with_device_filter(self):
        """Should accept device_id filter"""
        response = client.post(
            "/api/v1/query",
            json={
                "query": "What are the MIDI ports?",
                "device_id": "digitakt-ii"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        
    def test_query_missing_query_text(self):
        """Should reject request without query text"""
        response = client.post(
            "/api/v1/query",
            json={}
        )
        
        assert response.status_code == 422
        
    def test_query_empty_string(self):
        """Should reject empty query"""
        response = client.post(
            "/api/v1/query",
            json={"query": ""}
        )
        
        assert response.status_code in [400, 422]
    
    def test_query_history_endpoint(self):
        """GET /api/v1/query/history"""
        response = client.get("/api/v1/query/history")
        
        # Should return 200 with array
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDevicesAPI:
    """Test devices endpoints"""
    
    def test_get_device_connections(self):
        """GET /api/v1/devices/{device_id}/connections"""
        device_id = "digitakt-ii"
        response = client.get(f"/api/v1/devices/{device_id}/connections")
        
        # Should return 200 or 404
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "connections" in data
            
    def test_list_devices(self):
        """GET /api/v1/devices"""
        response = client.get("/api/v1/devices")
        
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data
        assert isinstance(data["devices"], list)
        
    def test_list_devices_with_filters(self):
        """Should accept filter parameters"""
        response = client.get(
            "/api/v1/devices",
            params={
                "manufacturer": "Elektron",
                "device_type": "drum_machine"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "devices" in data


class TestIntegrationWorkflow:
    """Integration tests for complete workflows"""
    
    @pytest.mark.integration
    def test_full_workflow(self, sample_pdf):
        """
        Complete workflow:
        1. Upload PDF
        2. Check ingestion status
        3. Query documentation
        4. Get device connections
        """
        
        # Step 1: Upload PDF
        with open(sample_pdf, "rb") as f:
            ingest_response = client.post(
                "/api/v1/ingest",
                files={"file": ("digitakt_manual.pdf", f, "application/pdf")},
                data={
                    "device_name": "Digitakt II",
                    "manufacturer": "Elektron"
                }
            )
        
        # Should accept
        if ingest_response.status_code in [200, 202]:
            # Step 2: Check status (if job_id returned)
            if "job_id" in ingest_response.json():
                job_id = ingest_response.json()["job_id"]
                status_response = client.get(f"/api/v1/ingest/status/{job_id}")
                assert status_response.status_code == 200
        
        # Step 3: Query documentation
        query_response = client.post(
            "/api/v1/query",
            json={
                "query": "How to connect MIDI?",
                "device_id": "digitakt-ii"
            }
        )
        assert query_response.status_code == 200
        assert "answer" in query_response.json()
        
        # Step 4: Get device connections
        devices_response = client.get("/api/v1/devices/digitakt-ii/connections")
        # Should return 200 or 404 (if device not in DB yet)
        assert devices_response.status_code in [200, 404]
    
    @pytest.mark.integration
    def test_query_after_ingestion(self):
        """
        Test that query works after PDF ingestion
        (Assumes database is populated)
        """
        
        # Query general question
        response = client.post(
            "/api/v1/query",
            json={"query": "What types of devices are supported?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0
        
    @pytest.mark.integration
    def test_concurrent_queries(self):
        """Test handling multiple concurrent queries"""
        import concurrent.futures
        
        def make_query(i):
            return client.post(
                "/api/v1/query",
                json={"query": f"Test query {i}"}
            )
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_query, i) for i in range(10)]
            responses = [f.result() for f in futures]
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_endpoint(self):
        """Should return 404 for invalid endpoints"""
        response = client.get("/api/v1/invalid")
        assert response.status_code == 404
        
    def test_method_not_allowed(self):
        """Should return 405 for wrong HTTP method"""
        response = client.get("/api/v1/ingest")  # Should be POST
        assert response.status_code == 405
        
    def test_large_query(self):
        """Should handle very long queries"""
        long_query = "How to connect MIDI? " * 1000
        response = client.post(
            "/api/v1/query",
            json={"query": long_query}
        )
        
        # Should return 200 or 400 (too long)
        assert response.status_code in [200, 400, 413]
        
    def test_special_characters_in_query(self):
        """Should handle special characters"""
        response = client.post(
            "/api/v1/query",
            json={"query": "Test: <script>alert('xss')</script>"}
        )
        
        assert response.status_code == 200
        # Should sanitize output
        data = response.json()
        assert "<script>" not in data["answer"]


class TestPerformance:
    """Performance and load tests"""
    
    @pytest.mark.slow
    def test_query_response_time(self):
        """Query should respond within reasonable time"""
        import time
        
        start = time.time()
        response = client.post(
            "/api/v1/query",
            json={"query": "What is a synthesizer?"}
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        # Should respond within 5 seconds (mock data is fast)
        assert elapsed < 5.0
        
    @pytest.mark.slow
    def test_multiple_sequential_queries(self):
        """Test performance with sequential queries"""
        import time
        
        start = time.time()
        for i in range(10):
            response = client.post(
                "/api/v1/query",
                json={"query": f"Test query number {i}"}
            )
            assert response.status_code == 200
        
        elapsed = time.time() - start
        avg_time = elapsed / 10
        
        # Average should be reasonable
        assert avg_time < 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
