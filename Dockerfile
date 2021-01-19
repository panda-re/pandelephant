FROM pandare/panda:latest

# Update packages
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    sudo git python3-psycopg2  postgresql wget  \
    postgresql-contrib libpq-dev postgresql-client-common \
    postgresql-client \
    vim unzip python3-pip tmux screen

# Fix pypanda bug to ensure syscalls2 can load ds files by updating LD_LIBRARY_PATH explicitly
ENV LD_LIBRARY_PATH "/usr/local/lib/python3.8/dist-packages/pandare/data//mips-softmmu/panda/plugins/:~/usr/local/lib/python3.8/dist-packages/pandare/data//arm-softmmu/panda/plugins/"

RUN mkdir /pandelephant
COPY . /pandelephant/
WORKDIR /pandelephant
RUN pip install -r requirements.txt
