FROM python:3.8-slim-buster

RUN mkdir /recommendation-engine

COPY . /recommendation-engine

WORKDIR /recommendation-engine

RUN pip3 install -r requirements.txt

CMD [ "python3", "-m" , "flask", "run", "--host=0.0.0.0"]
