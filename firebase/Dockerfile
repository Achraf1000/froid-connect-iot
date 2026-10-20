FROM node:24-bookworm-slim AS tooling
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=tooling /usr/local/bin/node /usr/local/bin/node
COPY --from=tooling /app/node_modules /app/node_modules
COPY firebase/database.rules.json firebase/database.rules.json
COPY firebase/firebase.docker.json firebase.json
RUN node node_modules/firebase-tools/lib/bin/firebase.js setup:emulators:database
EXPOSE 9000 9099
CMD ["node", "node_modules/firebase-tools/lib/bin/firebase.js", "emulators:start", "--only", "database,auth", "--project", "demo-cold-chain", "--export-on-exit=/data"]
