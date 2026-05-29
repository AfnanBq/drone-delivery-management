FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

# Install postgres tools (pg_isready etc.)
RUN apt-get update && apt-get install -y postgresql-client

COPY . .

COPY ./scripts/start.sh /start.sh

RUN chmod +x /start.sh

CMD ["/start.sh"]