FROM python:3.11-slim

WORKDIR /app

# copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# copy project
COPY . .

# run app
CMD ["python", "agent.py"]
