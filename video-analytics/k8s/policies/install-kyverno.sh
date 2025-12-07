#!/bin/bash
# Script to install Kyverno for Kubernetes policy enforcement

set -e

echo "Installing Kyverno..."

# Install Kyverno
kubectl apply -f https://github.com/kyverno/kyverno/releases/latest/download/install.yaml

# Wait for Kyverno to be ready
echo "Waiting for Kyverno to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=kyverno -n kyverno --timeout=300s

# Apply security policies
echo "Applying security policies..."
kubectl apply -f kyverno-policies.yaml

echo "Kyverno installation and policy configuration complete!"

