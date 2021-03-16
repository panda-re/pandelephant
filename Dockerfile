FROM pandare/panda:latest

# Update packages
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    sudo git python3-psycopg2  postgresql wget  \
    postgresql-contrib libpq-dev postgresql-client-common \
    postgresql-client \
    vim unzip python3-pip tmux screen

# Workaround PANDA issue #901
ENV LD_LIBRARY_PATH "/usr/local/lib/python3.8/dist-packages/pandare/data/mips-softmmu/panda/plugins/:/usr/local/lib/python3.8/dist-packages/pandare/data//arm-softmmu/panda/plugins/"

RUN mkdir /pandelephant

# Install requirements before copying everything
WORKDIR /pandelephant
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /pandelephant/
