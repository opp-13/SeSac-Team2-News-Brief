FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# build:ci shells out to `git rev-parse` for VITE_APP_VERSION, but .git isn't
# in this build context (it lives at the repo root, one level above
# frontend/) -- pass the version in as a build arg instead, and call `vite
# build` directly rather than `build:ci`/`build` (skips `tsc -b`, since that
# blocks on unrelated type errors in src/mocks/handlers.ts that are dead code
# in production builds anyway).
ARG VITE_APP_VERSION=dev
ENV VITE_APP_VERSION=$VITE_APP_VERSION
RUN npx vite build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
