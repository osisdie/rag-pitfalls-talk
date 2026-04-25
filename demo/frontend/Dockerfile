FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
# No package-lock committed yet; generate one on first install inside the image.
RUN npm install --omit=dev --legacy-peer-deps

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm install --legacy-peer-deps \
    && npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
# public/ is optional in this project (no static assets yet); create it so
# Next.js's runtime doesn't warn and the COPY below succeeds in future.
RUN mkdir -p public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/next.config.js ./next.config.js
EXPOSE 3000
CMD ["npm", "run", "start"]
