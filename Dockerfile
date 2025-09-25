FROM python:3.12-slim
WORKDIR /app
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY pyproject.toml ./
RUN pip install gunicorn && \
    pip install .
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5000", "app:app"]
