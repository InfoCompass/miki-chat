
# Introduction

These are the instructions to install and maintain MIKI chatbot.

MIKI chatbot has been built using [Rasa](https://rasa.com/).

Once deployed, the server has a number of services running in a docker compose setup.
The following services are relevant to our purposes:
 * A Rasa backend endpoint for conversations, this endpoint provides Chatbot responses
   to user messages, there is no need for the client to be aware of other supporting services.
   This endpoint can be accessed by a frontend
   such as [Botfront's Rasa Webchat](https://github.com/botfront/rasa-webchat).
 * An action server which provides supporting backend code accessible through http endpoints.
   For some user messages, a specific intent will be recognized that requires a backend request
   to the Beratungsnetz site. This action server mediates such requests, when the specific intent
   is recognized, a request is issued to the action server with the recognized entities (filter keywords),
   the action server performs some synonym conversions and issues a request to Beratungsnetz, it finally
   processes the results, processes corner cases and returns utterances and an error code in form of a slot.
 * Another useful service is the Rasa X UI which allows one to test the Chatbot directly without deploying
   a frontend.
   
   
Now we will describe the maintenance steps for MIKI Chatbot

# Checkout and unlock the MIKI Chatbot repo

In order to unlock the secrets, you need to install transcrypt and unlock using the instructions you have received.

# Update the Action Server Image

The action server's Docker image needs to be updated in a new installation or whenever the conversation
data was updated.

To do this, run the following Makefile target:

`make publish`
   
This target should take care of building the docker image and pushing it into the DockerHub repo.

# BLAH


On an Ubuntu 20 System, checkout the repository.

Install transcrypt and unlock the miki-chat repository.

`cd miki-chat`

Then run

`sudo bash scripts/install.sh`


