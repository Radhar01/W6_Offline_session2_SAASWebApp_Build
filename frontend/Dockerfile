# frontend/Dockerfile
# Multi-stage build for the ClipCreator React/Vite frontend.
# Stage 1 builds the static production bundle with Node.
# Stage 2 serves that bundle with a lightweight nginx image.

# ---------- Stage 1: build ----------
FROM node:20-alpine AS build

WORKDIR /app

# Vite inlines VITE_* env vars into the bundle at build time, not at
# container-run time — must be passed as a build ARG (see docker-compose.yml
# `build.args`), not a runtime `environment:` entry.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---------- Stage 2: serve ----------
FROM nginx:1.27-alpine AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
