#!/bin/bash
set -Eeuo pipefail

#######################################
#
# installing ansible and roles
#
#######################################

source /etc/os-release

RUN_ANSIBLE=${RUN_ANSIBLE:-true}

echo "Installing pip and ansible"

if [[ $ID =~ centos|rhel ]]; then

    sudo yum update -y
    sudo yum install -y python3
    sudo yum install -y python3-distutils || :  # if the package is not available and the command fails, do nothing,
                                                    # the distutils are already installed
elif [[ $ID =~ ubuntu|debian ]]; then
    sudo apt-get update -y
    sudo apt-get install -y python3
    sudo apt-get install -y python3-distutils || :  # if the package is not available and the command fails, do nothing,
                                                       # the distutils are already installed
    sudo apt-get install -y wget || :  # wget may already be installed; do nothing if it is
fi

curl -O https://bootstrap.pypa.io/get-pip.py
sudo python3 get-pip.py
sudo /usr/local/bin/pip install "ansible>-2.9, <2.10"

echo "Installing docker role"
sudo /usr/local/bin/ansible-galaxy install geerlingguy.docker
echo "Docker role for ansible has been installed"


if [[ "$RUN_ANSIBLE" == "true" ]]; then
    #######################################
    #
    # downloading the ansible playbook
    # for the passed in version or latest
    #
    #######################################
    echo "Downloading Rasa X playbook"
    wget -qO rasa_x_playbook.yml https://storage.googleapis.com/rasa-x-releases/0.34.0/rasa_x_playbook.yml

    #######################################
    #
    # running the ansible playbook
    # (starts docker und serves Rasa X)
    #
    #######################################
    echo "Running playbook"
    sudo /usr/local/bin/ansible-playbook -i "localhost," -c local rasa_x_playbook.yml
fi
