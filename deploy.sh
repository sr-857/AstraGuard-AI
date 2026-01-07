#!/bin/bash
# AstraGuard Deployment Script
# This script provides automated deployment capabilities for different environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
ENVIRONMENT="staging"
ACTION="deploy"
VALUES_FILE=""
DRY_RUN=false
WAIT=true
TIMEOUT="10m"

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat << EOF
AstraGuard Deployment Script

USAGE:
    $0 [OPTIONS] [ACTION]

ACTIONS:
    deploy          Deploy AstraGuard to Kubernetes (default)
    upgrade         Upgrade existing deployment
    rollback        Rollback to previous release
    uninstall       Remove AstraGuard from cluster
    status          Show deployment status
    test            Run post-deployment tests

OPTIONS:
    -e, --environment ENV    Target environment (staging|production) [default: staging]
    -f, --values FILE        Additional values file to use
    -n, --namespace NS       Kubernetes namespace [default: astraguard]
    --dry-run                Show what would be deployed without actually deploying
    --no-wait                Don't wait for deployment to complete
    --timeout DURATION       Timeout for deployment operations [default: 10m]
    -h, --help               Show this help message

EXAMPLES:
    $0 deploy -e production
    $0 upgrade -f custom-values.yaml
    $0 status
    $0 rollback --dry-run

EOF
}

check_dependencies() {
    log_info "Checking dependencies..."

    if ! command -v helm &> /dev/null; then
        log_error "Helm is not installed. Please install Helm v3."
        exit 1
    fi

    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed. Please install kubectl."
        exit 1
    fi

    log_success "Dependencies check passed"
}

setup_kubernetes() {
    log_info "Setting up Kubernetes context..."

    # Check if we can connect to the cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster. Please check your kubeconfig."
        exit 1
    fi

    # Create namespace if it doesn't exist
    kubectl create namespace astraguard --dry-run=client -o yaml | kubectl apply -f -

    log_success "Kubernetes setup complete"
}

deploy_astraguard() {
    log_info "Deploying AstraGuard to $ENVIRONMENT environment..."

    local helm_args=(
        upgrade --install astraguard ./helm/astraguard
        --namespace astraguard
        --values helm/astraguard/values.yaml
    )

    # Add environment-specific values
    if [ -f "helm/astraguard/values-$ENVIRONMENT.yaml" ]; then
        helm_args+=(--values "helm/astraguard/values-$ENVIRONMENT.yaml")
        log_info "Using environment-specific values: values-$ENVIRONMENT.yaml"
    fi

    # Add custom values file
    if [ -n "$VALUES_FILE" ]; then
        if [ -f "$VALUES_FILE" ]; then
            helm_args+=(--values "$VALUES_FILE")
            log_info "Using custom values file: $VALUES_FILE"
        else
            log_error "Values file not found: $VALUES_FILE"
            exit 1
        fi
    fi

    # Add dry-run flag
    if [ "$DRY_RUN" = true ]; then
        helm_args+=(--dry-run)
        log_info "Running in dry-run mode"
    fi

    # Add wait and timeout
    if [ "$WAIT" = true ]; then
        helm_args+=(--wait --timeout "$TIMEOUT")
    fi

    # Execute deployment
    if helm "${helm_args[@]}"; then
        if [ "$DRY_RUN" = false ]; then
            log_success "AstraGuard deployed successfully to $ENVIRONMENT"
            run_post_deploy_tests
        else
            log_success "Dry-run completed successfully"
        fi
    else
        log_error "Deployment failed"
        exit 1
    fi
}

upgrade_deployment() {
    log_info "Upgrading AstraGuard deployment..."
    deploy_astraguard
}

rollback_deployment() {
    log_info "Rolling back AstraGuard deployment..."

    if [ "$DRY_RUN" = true ]; then
        log_info "Would rollback to previous release"
        helm history astraguard --namespace astraguard
        return
    fi

    if helm rollback astraguard --namespace astraguard; then
        log_success "Rollback completed successfully"
    else
        log_error "Rollback failed"
        exit 1
    fi
}

uninstall_deployment() {
    log_warning "Uninstalling AstraGuard from cluster..."

    if [ "$DRY_RUN" = true ]; then
        log_info "Would uninstall AstraGuard"
        return
    fi

    read -p "Are you sure you want to uninstall AstraGuard? This will delete all data. (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if helm uninstall astraguard --namespace astraguard; then
            log_success "AstraGuard uninstalled successfully"
        else
            log_error "Uninstallation failed"
            exit 1
        fi
    else
        log_info "Uninstallation cancelled"
    fi
}

show_status() {
    log_info "Checking AstraGuard deployment status..."

    echo "=== Helm Release Status ==="
    helm status astraguard --namespace astraguard 2>/dev/null || echo "No Helm release found"

    echo -e "\n=== Pod Status ==="
    kubectl get pods -n astraguard --sort-by=.metadata.creationTimestamp

    echo -e "\n=== Service Status ==="
    kubectl get services -n astraguard

    echo -e "\n=== Ingress Status ==="
    kubectl get ingress -n astraguard

    echo -e "\n=== HPA Status ==="
    kubectl get hpa -n astraguard
}

run_post_deploy_tests() {
    log_info "Running post-deployment tests..."

    # Wait for pods to be ready
    log_info "Waiting for pods to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=astra-guard --namespace astraguard --timeout=300s || {
        log_warning "Some pods are not ready, but continuing with tests..."
    }

    # Run smoke tests
    log_info "Running smoke tests..."
    if kubectl run smoke-test --image=curlimages/curl --rm -i --restart=Never --namespace astraguard -- curl -f --max-time 10 http://astra-guard.astraguard.svc.cluster.local:8000/health/live; then
        log_success "Smoke tests passed"
    else
        log_error "Smoke tests failed"
        exit 1
    fi

    # Test monitoring endpoints
    log_info "Testing monitoring endpoints..."
    kubectl run monitor-test --image=curlimages/curl --rm -i --restart=Never --namespace astraguard -- curl -f --max-time 10 http://prometheus.astraguard.svc.cluster.local:9090/-/healthy || log_warning "Prometheus health check failed"
    kubectl run grafana-test --image=curlimages/curl --rm -i --restart=Never --namespace astraguard -- curl -f --max-time 10 http://grafana.astraguard.svc.cluster.local:3000/api/health || log_warning "Grafana health check failed"

    log_success "Post-deployment tests completed"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -f|--values)
            VALUES_FILE="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-wait)
            WAIT=false
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        deploy|upgrade|rollback|uninstall|status|test)
            ACTION="$1"
            shift
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    log_error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'"
    exit 1
fi

# Main execution
log_info "AstraGuard Deployment Script"
log_info "Environment: $ENVIRONMENT"
log_info "Action: $ACTION"

check_dependencies
setup_kubernetes

case $ACTION in
    deploy)
        deploy_astraguard
        ;;
    upgrade)
        upgrade_deployment
        ;;
    rollback)
        rollback_deployment
        ;;
    uninstall)
        uninstall_deployment
        ;;
    status)
        show_status
        ;;
    test)
        run_post_deploy_tests
        ;;
    *)
        log_error "Unknown action: $ACTION"
        show_help
        exit 1
        ;;
esac

log_success "Script completed successfully"
