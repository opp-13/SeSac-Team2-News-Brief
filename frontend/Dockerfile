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
# Template, not a static conf -- the base image's docker-entrypoint.d envsubst
# step renders it to /etc/nginx/conf.d/default.conf at container *startup*,
# substituting BACKEND_HOST/BACKEND_PORT from the environment. That lets one
# image be pointed at a different backend per environment via `docker run -e`
# instead of rebuilding.
COPY default.conf.template /etc/nginx/templates/default.conf.template
ENV BACKEND_HOST=api.team2.local
ENV BACKEND_PORT=8000
COPY --from=build /app/dist /usr/share/nginx/html
