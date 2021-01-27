
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

Take note of the action server version. You will need it to deploy it on the server.

# Deploy Updated Action Server Image

Go to the directory where the server is installed

`cd /etc/rasa`

Modify the version of the action server in place to the version that you want to deploy.
Where is the version specified, have a look at the file `config/APP_VERSION`

`sudo sed 's/MIKI_VERSION=.*$/MIKI_VERSION=YOUR_DESIRED_VERSION/' -i .env`

Restart the action server component:

`sudo docker-compose up -d`

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
So in summary before continuing you have to have:
 * An up to date action server
 * The updated action server should have been deployed in the Rasa X server.

When you have done it, now you can publish to production:
`make publish-model`

# Import new conversation data from spreadsheet

This section explains how to update the chatbot with conversation data from the configuration Spreadsheet.

The steps are:
 * Import conversation data
 * Train a model
 * Test the model
 * Update version and commit conversation data.
 * Update chatbot
 
 
## Import conversation data from Spreadsheet

In order to import conversation data you need to run the following target:

`make spreadsheet-to-model`

The script will import conversation data from the Spreadsheet into the directory `out` and
subsequently copied to the data directories.

Consider the above a test run. You will prefer to run the following target rather:

`make spreadsheet-to-model-with-logs`

Before you run this target, make sure you duplicate the sheets "Logs" and "Logs Detailed"
so that you can compare the import logs of the new run with the previous runs. After you are
happy with the results, you can delete the copies.

## Train a model

You run `make train-model` as before

## Test a model

You run `make test-model` to make sure that some important scenarios haven't been broken.
There is a corner case with a Question Answer involing a filter keyword, you might need to
comment a test and uncomment another to make the test pass. See the test documentation.

## Update version and commit conversation data

At this point you can commit the modified conversation files in `data` and also bump the
version in `config/APP_VERSION`.

## Update Chatbot

At this point you have to update the conversation model and the action server as described above.
Just recapping the above, the steps have to be done in the following order:
 * Upload model to server
 * Update action server
 * Deploy up-to-date version of action server
 * Publish model to production

