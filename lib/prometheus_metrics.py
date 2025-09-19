"""
Prometheus metrics for SkinStack
Following standard naming conventions: https://prometheus.io/docs/practices/naming/
"""
from prometheus_client import Counter, Histogram, Gauge, Info
import time

# ============================================================================
# HTTP Metrics (following Prometheus naming standards)
# ============================================================================

# Total HTTP requests
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# HTTP request duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# HTTP response size
http_response_size_bytes = Histogram(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint'],
    buckets=[100, 1000, 10000, 100000, 1000000, 10000000]
)

# ============================================================================
# Redirect & Click Metrics
# ============================================================================

# Total redirects processed
redirects_total = Counter(
    'redirects_total',
    'Total number of redirects processed',
    ['link_id', 'status']  # status: success, invalid, error
)

# Redirect latency
redirect_duration_seconds = Histogram(
    'redirect_duration_seconds',
    'Redirect processing latency in seconds',
    buckets=[0.0001, 0.0005, 0.001, 0.002, 0.003, 0.004, 0.005, 0.01, 0.025, 0.05]
)

# Redirect cache hits
redirect_cache_hits_total = Counter(
    'redirect_cache_hits_total',
    'Total number of redirect cache hits'
)

# Redirect cache misses
redirect_cache_misses_total = Counter(
    'redirect_cache_misses_total',
    'Total number of redirect cache misses'
)

# Click tracking
clicks_total = Counter(
    'clicks_total',
    'Total number of clicks tracked',
    ['link_id', 'source']
)

# ============================================================================
# Webhook Metrics
# ============================================================================

# Total webhooks received
webhooks_received_total = Counter(
    'webhooks_received_total',
    'Total number of webhooks received',
    ['source', 'event_type']
)

# Webhook processing duration
webhook_duration_seconds = Histogram(
    'webhook_duration_seconds',
    'Webhook processing duration in seconds',
    ['source', 'event_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Duplicate webhooks (idempotency)
webhook_duplicates_total = Counter(
    'webhook_duplicates_total',
    'Total number of duplicate webhooks detected',
    ['source']
)

# Webhook signature verification
webhook_signature_verifications_total = Counter(
    'webhook_signature_verifications_total',
    'Total webhook signature verification attempts',
    ['source', 'result']  # result: success, failure
)

# ============================================================================
# Conversion & Commission Metrics
# ============================================================================

# Total conversions
conversions_total = Counter(
    'conversions_total',
    'Total number of conversions tracked',
    ['program_id', 'status']
)

# Conversion value
conversion_value_dollars = Histogram(
    'conversion_value_dollars',
    'Conversion value in dollars',
    ['program_id'],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000, 10000]
)

# Commission amount
commission_amount_dollars = Histogram(
    'commission_amount_dollars',
    'Commission amount in dollars',
    ['program_id'],
    buckets=[0.1, 0.5, 1, 5, 10, 25, 50, 100, 250, 500]
)

# Platform fees collected
platform_fees_total_dollars = Counter(
    'platform_fees_total_dollars',
    'Total platform fees collected in dollars'
)

# ============================================================================
# Database Metrics
# ============================================================================

# Database query duration
database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query execution time in seconds',
    ['query_type', 'table'],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

# Database connection pool
database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections'
)

database_connections_idle = Gauge(
    'database_connections_idle',
    'Number of idle database connections'
)

database_connections_total = Gauge(
    'database_connections_total',
    'Total number of database connections'
)

# ============================================================================
# Redis Cache Metrics
# ============================================================================

# Cache operations
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result']  # operation: get, set, delete; result: hit, miss, error
)

# Cache operation duration
cache_operation_duration_seconds = Histogram(
    'cache_operation_duration_seconds',
    'Cache operation duration in seconds',
    ['operation'],
    buckets=[0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.025, 0.05]
)

# ============================================================================
# Application Info & Health
# ============================================================================

# Application info
app_info = Info(
    'app',
    'Application information'
)
app_info.info({
    'version': '1.0.0',
    'name': 'skinstack',
    'environment': 'production'
})

# Application uptime
app_uptime_seconds = Gauge(
    'app_uptime_seconds',
    'Application uptime in seconds'
)

# Health check status
health_check_status = Gauge(
    'health_check_status',
    'Health check status (1 = healthy, 0 = unhealthy)',
    ['check_type']  # check_type: database, redis, api
)

# ============================================================================
# Rate Limiting Metrics
# ============================================================================

# Rate limit hits
rate_limit_hits_total = Counter(
    'rate_limit_hits_total',
    'Total number of rate limit hits',
    ['endpoint', 'identifier']
)

# Rate limit remaining
rate_limit_remaining = Gauge(
    'rate_limit_remaining',
    'Remaining rate limit tokens',
    ['endpoint', 'identifier']
)

# ============================================================================
# Helper Functions
# ============================================================================

def track_request_duration(method: str, endpoint: str):
    """Context manager to track request duration"""
    class RequestTimer:
        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            duration = time.time() - self.start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

    return RequestTimer()

def track_database_query(query_type: str, table: str):
    """Context manager to track database query duration"""
    class QueryTimer:
        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            duration = time.time() - self.start_time
            database_query_duration_seconds.labels(
                query_type=query_type,
                table=table
            ).observe(duration)

    return QueryTimer()

def track_cache_operation(operation: str):
    """Context manager to track cache operation duration"""
    class CacheTimer:
        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            duration = time.time() - self.start_time
            cache_operation_duration_seconds.labels(
                operation=operation
            ).observe(duration)

    return CacheTimer()

# Initialize app start time for uptime tracking
APP_START_TIME = time.time()

def update_uptime():
    """Update application uptime metric"""
    app_uptime_seconds.set(time.time() - APP_START_TIME)