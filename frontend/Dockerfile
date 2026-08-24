# Frontend-Container: Vite-Build (Node) → statisch via nginx
# Bau-Arg VITE_API_URL = öffentlich erreichbare Backend-URL (z. B. http://<pi-ip>:8000)
# Hinweis: bullseye (glibc) statt alpine (musl), weil Rolldown (Vite 8) für ARMv7
# nur ein glibc-Binding (@rolldown/binding-linux-arm-gnueabihf) bereitstellt.
FROM node:20-bullseye AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
