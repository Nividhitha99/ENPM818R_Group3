# ============================================================================
# Frontend Dockerfile - Multi-Stage Build for React SPA
# ============================================================================
# This Dockerfile builds and serves the React frontend with:
# - Multi-stage build: Separate build and runtime environments
# - Optimized static asset serving via Nginx
# - Security: Unprivileged Nginx (non-root)
# - Small final image size (Alpine Linux base)
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build Stage - Compile React application to static assets
# ----------------------------------------------------------------------------
# Using Alpine variant for minimal build environment
FROM node:18-alpine AS builder

# Set working directory for build
WORKDIR /app

# Copy package files first for better layer caching
# npm install will only re-run if package.json or package-lock.json changes
COPY package*.json ./

# Install Node.js dependencies
# Includes both runtime and build dependencies (webpack, babel, etc.)
RUN npm install

# Copy entire source code
# This layer is rebuilt whenever source files change
COPY . .

# Build production-optimized React bundle
# Creates minified, optimized static files in /app/build
# - Code splitting for faster initial load
# - Tree shaking to remove unused code
# - Asset optimization (images, CSS)
RUN npm run build

# ----------------------------------------------------------------------------
# Stage 2: Runtime Stage - Serve static files with Nginx
# ----------------------------------------------------------------------------
# Using unprivileged Nginx for security (doesn't run as root)
# Alpine variant keeps image size minimal (~23MB vs ~133MB for standard Nginx)
# Updated to Alpine 3.21.4+ to fix libxml2 vulnerabilities (CVE-2025-49794, CVE-2025-49796, CVE-2025-49795, CVE-2025-6021)
FROM nginxinc/nginx-unprivileged:1.27-alpine3.21

# Bring libxml2 to the patched release to resolve CVE-2025-49794/49796/49795/6021
USER root
RUN apk add --no-cache --upgrade libxml2=2.13.9-r0
USER 101

# Copy built static files from builder stage
# Only production-ready assets are included (no source code, node_modules, etc.)
# Destination: /usr/share/nginx/html is default Nginx document root
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom Nginx configuration for SPA routing
# Ensures all routes fall back to index.html (required for React Router)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 8080 (unprivileged Nginx uses 8080 instead of 80)
# Port 80 requires root; 8080 is safe for non-root user
EXPOSE 8080

# No CMD needed - inherited from base image
# Default: nginx -g 'daemon off;' (runs Nginx in foreground)
