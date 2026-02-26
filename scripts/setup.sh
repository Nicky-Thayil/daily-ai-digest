#!/bin/bash
set -e

PROJECT_ID="ai-digest-488601"
REGION="us-central1"
REPO="ai-digest"
SERVICE_ACCOUNT_NAME="ai-digest-deployer"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
GITHUB_REPO="Nicky-Thayil/daily-ai-digest"

gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION \
  --description="AI Digest Docker images" \
  --project=$PROJECT_ID

gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
  --display-name="AI Digest GitHub Actions Deployer" \
  --project=$PROJECT_ID

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/iam.serviceAccountUser"

gcloud iam workload-identity-pools create "github-pool" \
  --project=$PROJECT_ID \
  --location="global" \
  --display-name="GitHub Actions Pool"

POOL_NAME=$(gcloud iam workload-identity-pools describe "github-pool" \
  --project=$PROJECT_ID \
  --location="global" \
  --format="value(name)")

gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project=$PROJECT_ID \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT_EMAIL \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}"

PROVIDER_NAME=$(gcloud iam workload-identity-pools providers describe "github-provider" \
  --project=$PROJECT_ID \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)")

read -p "OPENAI_API_KEY: " OPENAI_API_KEY
echo -n "$OPENAI_API_KEY" | gcloud secrets create OPENAI_API_KEY \
  --data-file=- --project=$PROJECT_ID

read -p "DATABASE_URL (port 6543): " DATABASE_URL
echo -n "$DATABASE_URL" | gcloud secrets create DATABASE_URL \
  --data-file=- --project=$PROJECT_ID

read -p "DATABASE_MIGRATION_URL (port 5432): " DATABASE_MIGRATION_URL
echo -n "$DATABASE_MIGRATION_URL" | gcloud secrets create DATABASE_MIGRATION_URL \
  --data-file=- --project=$PROJECT_ID

read -p "REDIS_URL: " REDIS_URL
echo -n "$REDIS_URL" | gcloud secrets create REDIS_URL \
  --data-file=- --project=$PROJECT_ID

COMPUTE_SA="${PROJECT_ID}-compute@developer.gserviceaccount.com"

for SECRET in OPENAI_API_KEY DATABASE_URL DATABASE_MIGRATION_URL REDIS_URL; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --project=$PROJECT_ID \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/secretmanager.secretAccessor"
done

echo ""
echo "Add these to GitHub -> Settings -> Secrets -> Actions:"
echo ""
echo "WIF_PROVIDER: $PROVIDER_NAME"
echo "WIF_SERVICE_ACCOUNT: $SERVICE_ACCOUNT_EMAIL"