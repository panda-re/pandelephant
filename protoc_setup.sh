#! /bin/bash

YELLOW='\033[1;33m'
NORMAL='\033[0m'

# https://grpc.io/docs/protoc-installation/

PB_REL="https://github.com/protocolbuffers/protobuf/releases"
PBC="protoc-3.15.6-linux-x86_64.zip"

cd $(dirname "$0")
curl -LO $PB_REL/download/v3.15.6/$PBC
unzip $PBC -d $HOME/.local
rm $PBC

echo -e "\n# Protoc 3.15.6" >> ~/.bashrc
echo "export PATH=\"$PATH:$HOME/.local/bin\"" >> ~/.bashrc

echo -e "${YELLOW}Please run \"source ~/.bashrc\"${NORMAL}"