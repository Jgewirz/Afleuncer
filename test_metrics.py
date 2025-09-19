#!/usr/bin/env python3
"""Test Prometheus metrics endpoint"""
import httpx
import asyncio

async def test_metrics():
    """Test the metrics endpoint"""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        # Make some test requests to generate metrics
        print("[TEST] Making requests to generate metrics...")

        # Health check
        r = await client.get(f"{base_url}/health")
        print(f"  Health: {r.status_code}")

        # Database health
        r = await client.get(f"{base_url}/health/database")
        print(f"  DB Health: {r.status_code}")

        # Make a few more requests
        for i in range(5):
            r = await client.get(f"{base_url}/health")

        # Now fetch metrics
        print("\n[TEST] Fetching metrics...")
        r = await client.get(f"{base_url}/metrics")

        if r.status_code == 200:
            metrics_text = r.text

            # Check for expected metrics
            expected_metrics = [
                'http_requests_total',
                'http_request_duration_seconds',
                'redirect_cache_hits_total',
                'redirect_cache_misses_total',
                'webhooks_received_total',
                'conversions_total',
                'platform_fees_total_dollars',
                'database_query_duration_seconds',
                'cache_operations_total',
                'app_uptime_seconds',
                'health_check_status'
            ]

            print("\n[METRICS CHECK]")
            for metric in expected_metrics:
                if metric in metrics_text:
                    print(f"  ✓ {metric} found")
                else:
                    print(f"  ✗ {metric} NOT found")

            # Show sample of actual metrics
            print("\n[SAMPLE METRICS]")
            for line in metrics_text.split('\n')[:20]:
                if not line.startswith('#'):
                    print(f"  {line}")

            print(f"\n[OK] Metrics endpoint working! Total metrics lines: {len(metrics_text.split('\n'))}")
        else:
            print(f"[ERROR] Metrics endpoint returned {r.status_code}")

if __name__ == "__main__":
    asyncio.run(test_metrics())