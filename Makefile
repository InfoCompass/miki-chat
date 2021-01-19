include config/production

VERSION=$(shell cat MIKI_ACTION_SERVER_VERSION)
APP_NAME=miki-chat
DOCKER_REPO=mikichatbot

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

