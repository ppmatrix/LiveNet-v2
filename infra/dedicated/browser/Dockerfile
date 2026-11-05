# DEV-07 disposable browser client only. No application source is copied.
ARG DEV07_NODE_IMAGE
FROM ${DEV07_NODE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends chromium libnss3-tools ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /browser
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org \
    && npm cache clean --force
RUN groupadd --gid 10001 browser && useradd --uid 10001 --gid 10001 --create-home browser
ENV HOME=/home/browser
USER 10001:10001
ENTRYPOINT ["node"]
