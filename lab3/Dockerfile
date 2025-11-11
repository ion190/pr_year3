FROM node:20-alpine
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY tsconfig.json ./
COPY src ./src
COPY public ./public
COPY boards ./boards

RUN npx tsc

EXPOSE 8080
ENTRYPOINT ["node", "dist/server.js"]
CMD ["8080", "boards/perfect.txt"]
