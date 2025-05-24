FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y ffmpeg  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*  # 清理缓存减小镜像体积 

WORKDIR /bili-sync-py

COPY ./requirements.txt /bili-sync-py/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /bili-sync-py/requirements.txt

ENV PYTHONPATH="${PYTHONPATH}:/app"

COPY ./app /bili-sync-py/app

CMD [ "fastapi", "run" , "app/main.py", "--port", "8080"]