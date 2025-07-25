# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install curl for the healthcheck
RUN apt-get update && apt-get install -y curl

# Create a directory for file uploads
RUN mkdir -p /app/uploads

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY ./requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt

# Install the jupyter kernel spec
RUN python -m ipykernel install --user

# Copy the rest of the backend application's source code
COPY . .

# Expose port 8000 to the outside world
EXPOSE 8000
