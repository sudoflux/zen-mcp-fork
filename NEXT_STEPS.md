# NEXT_STEPS.md — GPT-5 / Opus 4.1 Optimizations Production Roadmap

## Overview
This document outlines the concrete steps to productionize the GPT-5/Opus 4.1 optimizations implemented in the Zen MCP server. It provides actionable items with clear priorities, timelines, and success metrics.

## 1. Production Deployment Checklist

**Priority:** P0  
**Timeline:** 3–5 business days  
**Status:** Ready for immediate execution

### Success Metrics
- p50 latency within +10% of baseline; p95 within +15% during first week
- Error rate (5xx + provider errors) < 1%; timeout rate < 0.5%
- Zero Sev-1 incidents during and 72h after full rollout
- Fallback routing successfully exercises at least once in canary
- Cost/request variance vs baseline ≤ +10%

### Technical Steps

#### 1.1 Release Readiness
- [ ] Verify provider credentials and quotas for GPT-5 and Opus 4.1
- [ ] Configure model router with:
  - Default model per route
  - Per-model timeouts and max tokens
  - Rate limits and concurrency caps
- [ ] Implement feature flags:
  ```python
  # config.py additions
  FEATURE_FLAGS = {
      "enable_gpt5": os.getenv("ENABLE_GPT5", "false").lower() == "true",
      "enable_opus41": os.getenv("ENABLE_OPUS41", "false").lower() == "true",
      "rollout_percentage": int(os.getenv("ROLLOUT_PERCENTAGE", "0")),
      "fallback_to_baseline": os.getenv("FALLBACK_ENABLED", "true").lower() == "true"
  }
  ```
- [ ] Define circuit breaker thresholds:
  - Request timeout: 30s non-streaming; 90s streaming
  - Trip on 50% failure over 2 minutes

#### 1.2 Observability & Safety
- [ ] Instrument OpenTelemetry spans:
  ```python
  # Attributes to track
  span.set_attribute("model_name", model)
  span.set_attribute("tokens_in", input_tokens)
  span.set_attribute("tokens_out", output_tokens)
  span.set_attribute("ttft_ms", time_to_first_token)
  span.set_attribute("fallback_used", used_fallback)
  ```
- [ ] Create dashboards for:
  - Latency (p50/p95/p99)
  - Error rates by model
  - Token usage and costs
  - Fallback activation rates
- [ ] Set up alerting for SLO violations

#### 1.3 Deployment Strategy
- [ ] **Phase 1:** Shadow mode (5-10% traffic, discard responses)
- [ ] **Phase 2:** Canary release (1-5% user traffic)
- [ ] **Phase 3:** Progressive rollout (25%, 50%, 100%)
- [ ] **Rollback:** One-click revert via feature flags

### Dependencies
- OpenAI API access with GPT-5 enabled
- Google Vertex AI access for Opus 4.1
- OpenTelemetry collector configured
- Feature flag service operational

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Provider instability | Circuit breakers + rapid fallback |
| Cost spikes | Per-request token caps + alerts |
| PII in logs | Server-side redaction |

## 2. Performance Monitoring & Metrics

**Priority:** P0  
**Timeline:** 2–3 days  

### Key SLOs to Implement
```yaml
slos:
  chat_latency:
    p50: ≤ 1.0s
    p95: ≤ 3.0s
  streaming_ttft:
    p95: ≤ 1.2s
  error_rate: ≤ 1%
  availability: ≥ 99.9%
```

### Metrics Collection
```python
# Add to server.py
from prometheus_client import Counter, Histogram, Gauge

request_duration = Histogram('mcp_request_duration_seconds', 
                            'Request duration', 
                            ['model', 'provider', 'tool'])
token_usage = Counter('mcp_tokens_total', 
                     'Total tokens used', 
                     ['model', 'direction'])
model_errors = Counter('mcp_model_errors_total', 
                      'Model errors', 
                      ['model', 'error_type'])
```

### Cost Governance
- [ ] Daily budget guardrails per environment
- [ ] Auto-downgrade when budget exceeded
- [ ] Weekly per-tenant spend reports

## 3. Benchmarking Requirements

**Priority:** P0 (launch-gating)  
**Timeline:** 3–5 days  

### Test Workloads
```python
# benchmark_suite.py
WORKLOADS = {
    "chat_short": {"tokens": 500, "streaming": False},
    "chat_long": {"tokens": 50000, "streaming": True},
    "tool_calling": {"tools": 5, "iterations": 3},
    "reasoning": {"complexity": "high", "tokens": 10000}
}
```

### Gating Criteria
- [ ] Meets SLO targets under 1.5x peak load
- [ ] ≥ 95% JSON/schema validity on tool calls
- [ ] Fallback success ≥ 99% when triggered
- [ ] Cost drift ≤ +10% for representative tasks

### Benchmark Harness
```bash
# Run benchmarks
python benchmark_suite.py \
  --models gpt-5,gpt-4.1 \
  --load-multiplier 1.5 \
  --duration 3600 \
  --output results.json
```

## 4. Integration Testing Plan

**Priority:** P0 (smoke tests), P1 (chaos testing)  
**Timeline:** 3–4 days  

### Critical Test Coverage
```python
# test_integration_models.py
def test_gpt5_streaming():
    """Test GPT-5 streaming with reasoning"""
    response = await client.chat(
        model="gpt-5",
        stream=True,
        reasoning_tokens=5000
    )
    assert response.ttft_ms < 1200
    assert response.reasoning_used > 0

def test_opus41_large_context():
    """Test Opus 4.1 with large file context"""
    files = load_test_files(count=50, total_tokens=500000)
    response = await client.analyze(
        model="gpt-4.1",
        files=files
    )
    assert response.files_processed == 50
    assert response.tokens_used < 1000000

def test_model_fallback():
    """Test automatic fallback on failure"""
    with mock_provider_failure("gpt-5"):
        response = await client.chat(model="gpt-5")
        assert response.model_used != "gpt-5"
        assert response.fallback_activated
```

### Resilience Testing
- [ ] Inject 429, 500, timeouts - verify retries
- [ ] Test circuit breaker trip/reset
- [ ] Validate feature flag rollback

## 5. User Migration Guide

**Priority:** P0  
**Timeline:** 2–3 days for docs, 1 week phased migration  

### Communication Plan
```markdown
# Announcement Template
Subject: New Models Available: GPT-5 & Opus 4.1

We're excited to announce support for:
- GPT-5: 400K context, advanced reasoning
- GPT-4.1 (Opus): 1M context for large codebases

Benefits:
- 30% faster debugging with GPT-5 reasoning
- 5x more files analyzed with Opus 4.1
- Smart model selection based on task

Migration: Opt-in via config or auto-selection
Support: #model-migration channel
```

### Configuration Examples
```python
# User configuration options

# Option 1: Explicit model selection
config = {
    "model": "gpt-5",
    "reasoning_mode": "high"
}

# Option 2: Auto-selection based on task
config = {
    "model": "auto",  # System picks best model
    "optimize_for": "quality"  # or "speed" or "cost"
}

# Option 3: Fallback configuration
config = {
    "preferred_model": "gpt-5",
    "fallback_models": ["gpt-4.1", "o3"],
    "max_cost_per_request": 0.50
}
```

## 6. Future Enhancement Roadmap

### P1 - Near Term (2-8 weeks)
| Enhancement | Timeline | Impact |
|------------|----------|--------|
| Adaptive model routing | 3 weeks | -20% cost |
| Prompt/result caching | 2 weeks | -30% latency |
| Quality evaluation pipeline | 4 weeks | Quality assurance |
| Streaming optimizations | 2 weeks | -15% TTFT |
| Enhanced cost controls | 3 weeks | Budget compliance |

### P2 - Long Term (1-3 quarters)
| Enhancement | Timeline | Impact |
|------------|----------|--------|
| Multi-region failover | 1 quarter | 99.99% availability |
| Async/batch inference | 2 quarters | New use cases |
| Schema registry | 1 quarter | Tool reliability |
| Safety upgrades | 2 quarters | Compliance |
| Experimentation platform | 3 quarters | Data-driven optimization |

## Immediate Actions (First 72 Hours)

### Day 1
- [ ] Lock SLOs and configure alerting
- [ ] Deploy feature flags to staging
- [ ] Begin shadow mode testing
- [ ] Create rollback procedures

### Day 2
- [ ] Run initial benchmarks
- [ ] Verify provider quotas
- [ ] Set up monitoring dashboards
- [ ] Document runbooks

### Day 3
- [ ] Complete integration tests
- [ ] Publish migration guide
- [ ] Start canary rollout (1%)
- [ ] Open support channels

## Success Criteria

### Week 1
- ✅ Canary at 5% with stable metrics
- ✅ Zero P0 incidents
- ✅ Cost within budget

### Week 2
- ✅ 50% traffic on new models
- ✅ User satisfaction maintained
- ✅ Performance SLOs met

### Month 1
- ✅ 100% rollout complete
- ✅ 20% performance improvement
- ✅ ROI positive

## Support & Resources

- **Documentation:** `/docs/gpt5-opus-optimization.md`
- **Runbooks:** `/runbooks/model-incidents.md`
- **Support:** #zen-mcp-support
- **Monitoring:** [Dashboard Link]
- **Status Page:** [Status Link]

## Appendix: Quick Reference

### Model Capabilities
| Model | Input | Output | Reasoning | Best For |
|-------|-------|--------|-----------|----------|
| GPT-5 | 400K | 128K | Yes (128K) | Complex reasoning, debugging |
| GPT-4.1 | 1M | 32K | No | Large codebases, refactoring |

### Cost Estimates
| Operation | GPT-5 | GPT-4.1 | Baseline |
|-----------|-------|---------|----------|
| Simple chat | $0.03 | $0.02 | $0.01 |
| Code review | $0.15 | $0.12 | $0.08 |
| Large refactor | $0.40 | $0.25 | $0.30 |

### Performance Targets
| Metric | Target | Current | Goal |
|--------|--------|---------|------|
| TTFT | <1.2s | 1.5s | -20% |
| p95 Latency | <3s | 4s | -25% |
| Success Rate | >99% | 97% | +2% |

---

*Last Updated: January 2025*  
*Version: 1.0*  
*Owner: Zen MCP Team*