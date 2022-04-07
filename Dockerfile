FROM python:3.8-slim-buster AS builder

RUN apt-get update && apt-get install -y curl git git-lfs &&\
    git lfs install && \
    rm -rf /var/lib/apt/lists/* &&\
    apt-get clean

RUN curl -LO https://dl.k8s.io/release/v1.17.17/bin/linux/amd64/kubectl && \
    curl -LO "https://dl.k8s.io/release/v1.17.17/bin/linux/amd64/kubectl.sha256" && \
    echo "$(cat kubectl.sha256)  kubectl" | sha256sum -c

RUN mkdir /package &&\
    chmod +x kubectl && mv kubectl /usr/local/bin/kubectl

COPY package/requirements.txt /package
RUN pip install --no-cache-dir -r /package/requirements.txt 

COPY package /package/

# USER 1001 

ENTRYPOINT [ "kubectl" ]
CMD [ "--help" ]