#!/bin/bash

# Used in Ansible playbook
export MIKI_VERSION=`cat MIKI_ACTION_SERVER_VERSION`

# Agree to Rasa X license
mkdir -p /etc/rasa/terms
touch /etc/rasa/terms/agree.txt

# Actual install
export RUN_ANSIBLE=false
/bin/bash scripts/rasa-x/install.sh
ansible-playbook --extra-vars terms_confirmed=True -i "localhost," -c local scripts/rasa-x/rasa_x_playbook.yml

# Docker login (which uses the root makefile)
apt install make
make docker-login

# Start Rasa X and Create account with password
source config/production
cd /etc/rasa
docker-compose up -d
sleep 120
python3 rasa_x_commands.py create --update admin me $RASA_X_PASSWORD

