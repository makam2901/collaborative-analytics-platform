# --- Stage 1: The Builder ---
# This stage installs all dependencies

FROM node:18 AS builder

WORKDIR /app

# Copy package files
COPY package.json ./
COPY package-lock.json ./

# Use 'npm ci' for a clean, reliable install
RUN npm ci

# --- Stage 2: The Final Image ---
# This stage creates the final, lean container

FROM node:18

WORKDIR /app

# Copy the installed dependencies from the 'builder' stage
COPY --from=builder /app/node_modules ./node_modules

# Copy the rest of the application source code
COPY . .

# Expose port 3000
EXPOSE 3000

# The command to start the app
CMD ["npm", "start"]
