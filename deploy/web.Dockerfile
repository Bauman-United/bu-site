FROM node:22-alpine AS build
RUN corepack enable
WORKDIR /web
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm build && pnpm check:robots

FROM node:22-alpine
WORKDIR /web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
RUN addgroup -S bu && adduser -S bu -G bu
COPY --from=build --chown=bu:bu /web/.next/standalone ./
COPY --from=build --chown=bu:bu /web/.next/static ./.next/static
COPY --from=build --chown=bu:bu /web/public ./public
USER bu
EXPOSE 3000
CMD ["node", "server.js"]
