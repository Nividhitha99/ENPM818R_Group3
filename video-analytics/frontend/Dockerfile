# Stage 1: Build React App
FROM node:18-alpine AS builder
WORKDIR /app

# Copy package.json and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the application
COPY . .

# Build the frontend
RUN npm run build

# Stage 2: Nginx server to serve static frontend (unprivileged)
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 8080
USER 101
