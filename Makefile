include config/production

VERSION=$(shell cat config/APP_VERSION)
APP_NAME=miki-chat
DOCKER_REPO=mikichatbot

test-model:
	rasa test --nlu tests/test_nlu.yml --fail-on-prediction-errors

train-model:
	rasa train --domain data

build:
	docker build -t $(APP_NAME) .

run-local:
	docker run -i -t -p 5055:5055 $(APP_NAME)

publish: build docker-login publish-version

publish-version: tag-version
	docker push $(DOCKER_REPO)/$(APP_NAME):$(VERSION)

tag-version:
	docker tag $(APP_NAME) $(DOCKER_REPO)/$(APP_NAME):$(VERSION)

docker-login:
	cat config/docker_hub_pass | docker login -u ${DOCKER_HUB_LOGIN} --password-stdin


# Install dev requirements
requirements-dev:
	pip install -r requirements-dev.txt
	apt install jq --yes
	python3 -m spacy download de

# Running import script
spreadsheet-to-conversation-data:
	python3 scripts/import_questions.py \
		--client-secret=config/client-secret.json \
		--spreadsheet-url=$(SPREADSHEET_URL) \
		--output-dir=out && \
	cp -a out/data ./

# Running import script
#   Before running this you might want to backup the sheets "Logs" and "Logs Detailed"
spreadsheet-to-conversation-data-with-logs:
	python3 scripts/import_questions.py \
		--client-secret=config/client-secret.json \
		--spreadsheet-url=$(SPREADSHEET_URL) \
		--output-dir=out \
		--save-logs-to-spreadsheet && \
	cp -a out/data ./

rasa-x-token.txt:
	curl -s --header "Content-Type: application/json" \
		--request POST \
		--fail \
		--data "{\"username\":\"me\",\"password\":\"${RASA_X_PASSWORD}\"}" \
              http://${RASA_DOMAIN}/api/auth | jq -r .access_token > rasa-x-token.txt.tmp && \
    mv rasa-x-token.txt.tmp $@

# It uses the most recent model (because it's not possible to specify the output in training very annoyingly
upload-model: rasa-x-token.txt
	MODEL=$$(ls models | sort | tail -n 1) && \
	curl -k --fail \
      -H "Authorization: Bearer `cat $<`" \
      -F "model=@models/$$MODEL" \
      http://${RASA_DOMAIN}/api/projects/default/models

# It uses the most recent model (because it's not possible to specify the output in training very annoyingly
publish-model: rasa-x-token.txt
	MODEL=$$(ls models | sort | tail -n 1) && \
    curl -k --fail -XPUT \
      -H "Authorization: Bearer `cat $<`" \
      http://${RASA_DOMAIN}/api/projects/default/models/$$(basename $$MODEL .tar.gz)/tags/production

update-model: requirements-dev spreadsheet-to-model test-model

