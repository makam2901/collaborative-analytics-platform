# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install curl for the healthcheck
RUN apt-get update && apt-get install -y curl

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY ./requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt

# Copy the rest of the backend application's source code from your host to your image filesystem.
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000
