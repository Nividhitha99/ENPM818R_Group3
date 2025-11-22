# Observability Runbook

## Metrics (Prometheus)
- **Endpoint**: `/metrics` exposed on all microservices.
- **Key Metrics**:
  - `video_uploads_total`: Counter of received uploads.
  - `video_processing_seconds`: Histogram of transcoding duration.
  - `http_request_duration_seconds`: API latency.

## Logging (FluentBit + CloudWatch)
- Logs are structured JSON.
- Shipped to CloudWatch Logs via FluentBit daemonset (standard EKS addon).

## Alerts
1. **HighErrorRate**: > 5% 5xx errors for 5 minutes.
2. **HighLatency**: P95 latency > 2s for 5 minutes.
3. **QueueBacklog**: SQS visible messages > 1000.

## Dashboards (Grafana)
- **Overview**: Traffic, Success Rates, Overall Health.
- **Worker Performance**: Queue depth vs Processing time.

