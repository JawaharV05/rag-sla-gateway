from prometheus_client import Counter, Histogram, Gauge

REQUEST_LATENCY = Histogram(
    "gateway_request_latency_ms",
    "Request latency in milliseconds",
    ["client_id"]
)

REQUESTS_TOTAL = Counter(
    "gateway_requests_total",
    "Total requests processed",
    ["client_id", "outcome"]
)

SLA_COMPLIANCE = Counter(
    "gateway_sla_compliance_total",
    "Requests broken down by whether they met their SLA",
    ["client_id", "within_sla"]
)

DEGRADED_TOTAL = Counter(
    "gateway_degraded_total",
    "Total degraded (non-full) answers",
    ["client_id"]
)

BREAKER_STATE = Gauge(
    "gateway_circuit_breaker_state",
    "Circuit breaker state: 0=CLOSED, 1=HALF_OPEN, 2=OPEN"
)