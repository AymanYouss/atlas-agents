# Deploying Atlas

Three layers, from laptop to production.

## 1. Local (Docker Compose)

```bash
make sandbox-image          # build the code-execution sandbox image once
export ANTHROPIC_API_KEY=...  TAVILY_API_KEY=...
docker compose -f deploy/docker/docker-compose.yml up --build
```

- API: http://localhost:8000 (`/docs` for the OpenAPI UI)
- UI: http://localhost:8080
- Postgres: localhost:5432

The API container mounts the Docker socket so `code_exec` can launch hardened
sandbox containers on the host daemon.

## 2. Kubernetes

Images are published to ECR/GHCR by CI. Apply with Kustomize:

```bash
kubectl apply -k deploy/k8s
```

Includes: namespace with the `restricted` Pod Security Standard, a Postgres
StatefulSet (swap for RDS in production), the API Deployment with an init
container that runs `alembic upgrade head`, an HPA (3–12 replicas on CPU), a
PodDisruptionBudget, the nginx-served frontend, an ALB Ingress with SSE-friendly
idle timeouts, and default-deny NetworkPolicies.

Secrets are illustrative in `config.yaml`; in production they are projected from
AWS Secrets Manager by the External Secrets Operator (IRSA role provisioned by
Terraform).

## 3. AWS (Terraform)

```bash
cd deploy/aws
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
aws eks update-kubeconfig --region <region> --name atlas
```

Provisions a 3-AZ VPC, an EKS cluster (managed node group, IRSA, core add-ons),
a Multi-AZ encrypted RDS Postgres, immutable ECR repositories with scan-on-push
and lifecycle policies, a Secrets Manager entry (with the assembled database
URL), and IRSA roles for the AWS Load Balancer Controller and External Secrets
Operator.

## Code sandbox in-cluster

On the host/Compose the sandbox uses the local Docker daemon. In Kubernetes,
point `DockerSandbox` at a hardened runtime (gVisor or Kata via a
`runtimeClassName`) — the sandbox interface is driver-agnostic, so no
application code changes are required.
