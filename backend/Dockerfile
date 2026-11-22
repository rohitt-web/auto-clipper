FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgomp1 curl ca-certificates unzip git && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://deno.land/install.sh | sh
ENV PATH="/root/.deno/bin:${PATH}"
RUN git clone --depth 1 --branch 2.0.2 https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git /opt/bgutil-ytdlp-pot-provider \
    && cd /opt/bgutil-ytdlp-pot-provider/server \
    && deno install --allow-scripts=npm:canvas --frozen
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY web/ /app/web/
ENV DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8000
CMD ["sh", "-c", "cd /opt/bgutil-ytdlp-pot-provider/server/node_modules && deno run --allow-env --allow-net --allow-ffi=. --allow-read=. ../src/main.ts --host 127.0.0.1 & exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
