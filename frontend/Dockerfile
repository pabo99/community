# Development-oriented frontend image for the Community platform.
# Runs the Vite dev server with HMR. A production static-serving stage
# (build + nginx) is intentionally NOT included here; production frontend
# packaging belongs to deployment/CI work.

FROM node:22-slim

ENV NODE_ENV=development

WORKDIR /app

# Install dependencies first for cache-friendly, reproducible builds.
# node_modules is kept at /app and shielded from the development bind mount by
# an anonymous volume declared in docker-compose.yml.
COPY package.json package-lock.json ./
RUN npm ci

# Copy the application source (the compose bind mount overrides this in dev).
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
