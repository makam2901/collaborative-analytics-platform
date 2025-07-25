# Use the full Debian-based Node image for better compatibility
FROM node:18

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json (if it exists)
COPY package*.json ./

# Clean the npm cache and install dependencies forcefully
# This ensures a completely fresh installation
RUN npm cache clean --force
RUN npm install

# Copy the rest of the application source code
COPY . .

# Expose port 3000
EXPOSE 3000

# The command to start the app
CMD ["npm", "start"]
