FROM node:26-alpine AS build
RUN npm install --global pnpm@12.16.1
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
ARG API_INTERNAL_URL
ENV API_INTERNAL_URL=$API_INTERNAL_URL
RUN pnpm build

FROM node:26-alpine
# The running app has no use for npm, and it carries known security problems.
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/bin/npm /usr/local/bin/npx
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER node
EXPOSE 3000
CMD ["node", "server.js"]
