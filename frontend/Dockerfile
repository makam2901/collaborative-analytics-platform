# --- Stage 1: The Builder ---
FROM node:20 AS builder

WORKDIR /app

COPY package.json ./
COPY package-lock.json ./

RUN npm ci

# --- Stage 2: The Final Image ---
FROM node:20

WORKDIR /app

# Copy the installed dependencies from the 'builder' stage
COPY --from=builder /app/node_modules ./node_modules

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
