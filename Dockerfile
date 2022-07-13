FROM python:3.10.5-slim

ADD . /app
WORKDIR /app

RUN pip install pipenv
RUN pipenv install

CMD pipenv run start