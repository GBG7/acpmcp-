# syntax=docker/dockerfile:1.7

# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY . .
# Optional: if you ever want to hardcode a WS URL at build time
ARG VITE_WS_URL
ENV VITE_WS_URL=${VITE_WS_URL}
RUN npm run build

# --- run stage (static server, no nginx) ---
FROM node:20-alpine AS run
WORKDIR /srv
# lightweight static file server
RUN npm i -g serve
COPY --from=build /app/dist /srv/dist
ENV PORT=8501
EXPOSE 8501
# serve the prebuilt static assets
CMD ["serve", "-s", "dist", "-l", "8501"]
