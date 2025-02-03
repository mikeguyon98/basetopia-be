#!/bin/bash

# Exit on any error
set -e

# Configuration
PROJECT_ID="basetopia-b9302"  # Replace with your project ID
REGION="us-east1"          # Replace with your preferred region
SERVICE_NAME="basetopia-be"  # Replace with your service name
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Print colored output
print_step() {
    echo -e "\n\033[1;34m👉 $1\033[0m"
}

print_success() {
    echo -e "\n\033[1;32m✅ $1\033[0m"
}

# Ensure we're logged into gcloud
print_step "Verifying gcloud auth..."
if ! gcloud auth print-access-token >/dev/null 2>&1; then
    echo "Not logged in to gcloud. Please run 'gcloud auth login' first."
    exit 1
fi

# Set the correct project
print_step "Setting project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Build the Docker image
print_step "Building and pushing Docker image..."
gcloud builds submit --tag $IMAGE_NAME

# Deploy to Cloud Run
print_step "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --timeout 300s

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format='value(status.url)')

# # Update ALLOWED_ORIGINS with the service URL
# print_step "Updating ALLOWED_ORIGINS with service URL..."
# gcloud run services update $SERVICE_NAME \
#     --platform managed \
#     --region $REGION

print_success "Deployment completed successfully!"
echo "Service URL: $SERVICE_URL"