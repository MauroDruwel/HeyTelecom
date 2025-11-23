# Use Python 3.14 slim image for a lighter base
FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Copy necessary files
COPY app.py .

# Install Python dependencies
RUN pip install --no-cache-dir heytelecom flask

# Install Playwright browsers
RUN playwright install chromium --with-deps --only-shell

# Expose port
EXPOSE 8099

# Run the Flask app
CMD ["python", "app.py"]
