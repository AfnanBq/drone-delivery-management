FROM python:3.12

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

COPY ./scripts/start.sh /start.sh

RUN chmod +x /start.sh

CMD ["/start.sh"]