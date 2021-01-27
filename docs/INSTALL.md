
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

# Requirements

The installation instructions are targetted to an Ubuntu 20 System.

You will need to install Make and Docker.

# Checkout and unlock the MIKI Chatbot repo

In order to unlock the secrets, you need to install [Transcrypt](https://github.com/elasticdog/transcrypt)
and unlock using the instructions you have received.

# Install MIKI Chatbot

Please before starting an install, make sure that the Action Server Image is up to date.

## Install server

On a target box with an Ubuntu 20 System, checkout the repository and unlock it as described above.

From within the repository,

`cd miki-chat`

run the installation script as follows:

`sudo bash scripts/install.sh`

You should be able to access the UI at the http endpoint using the "me" user and the password in secrets.

## Try out conversation data

Before continuing the installation check if the chatbot works properly by first updating the model.

# Update the Action Server Image

The action server's Docker image needs to be updated in a new installation or whenever the conversation
data was updated.

To do this, run the following Makefile target (You might need to install make):

`make publish`
   
This target should take care of building the docker image and pushing it into the DockerHub repo.

# Update model

Here we update the conversation model by training it from the conversation data and pushing it
to the Rasa server.

First of all make sure that you have all the required dependencies:
`sudo make requirements-dev`
For this step you will need to have `pip` installed.

Now generate conversation model using the corresponding make target:
`make train-model`

Then upload to the sever:
`make upload-model`
This step will upload the most recent model from the directory `models`.

At this point the model will be at the server, now before publishing it to production, please
make sure that you have updated the action server image and redeployed it.
This step is important as the new model might require an updated action server.

When you have done it, now you can publish to production:
`make publish-model`


