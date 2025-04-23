FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app
COPY . .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN playwright install --with-deps

CMD ["python", "bot.py"]
