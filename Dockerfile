# Use an official Python runtime as the base image
FROM python:3.11.3

# Set the working directory in the container
WORKDIR /dbackup-server

# Copy the requirements file to the container
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create /saved_data folder inside /dbackup-server
RUN mkdir /dbackup-server/saved_data

# Copy the FastAPI server files to the container
COPY . .

# Expose a port (change if necessary)
EXPOSE 80
