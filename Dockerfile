from rasa/rasa:2.1.2-full

USER root

RUN pip install pandas
RUN pip install nltk

COPY . /miki-chat

WORKDIR /miki-chat

CMD ["run", "actions", "--actions", "data"]


