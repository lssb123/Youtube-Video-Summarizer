# Use the official Python image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port that FastAPI runs on
EXPOSE 8000

# Set environment variables (optional but can be used to manage configurations)
ENV PYTHONUNBUFFERED=1

# Run the FastAPI server
CMD ["uvicorn", "practice:app", "--host", "0.0.0.0", "--port", "8000"]
