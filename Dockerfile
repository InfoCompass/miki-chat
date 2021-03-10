from rasa/rasa:2.1.2-full

USER root

RUN pip install pandas==1.2.0
RUN pip install nltk==3.5

COPY . /miki-chat

RUN mkdir /rasa-extensions
COPY fallback.py /rasa-extensions
ENV PYTHONPATH "${PYTHONPATH}:/rasa-extensions"

WORKDIR /miki-chat

CMD ["run", "actions", "--actions", "data"]


