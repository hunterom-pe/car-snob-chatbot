# Use a lightweight Python base image
FROM python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies first
# This helps with Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000, which is where our Flask app will run
EXPOSE 5000

# Command to run the Flask application when the container starts
CMD ["python", "app.py"]