# feat(docker): multi-stage Dockerfile + deployment configs

**Labels:** enhancement

## Scope

- Multi-stage Dockerfile (build → runtime, minimal image)
- docker-compose.yml with picowatch + prometheus + otel-collector
- Helm chart for Kubernetes (deployment, service, configmap)
- Health probes (/v1/health for liveness/readiness)

## Acceptance Criteria

- [ ] Docker image builds and runs
- [ ] docker-compose up brings up picowatch + prometheus + otel
- [ ] Helm chart renders valid manifests
- [ ] Health probes work in k8s
