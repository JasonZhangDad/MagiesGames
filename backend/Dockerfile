FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 数据目录（持久化挂载点）
RUN mkdir -p /app/data

ENV MAGIES_DATA=/app/data
EXPOSE 8102

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8102"]
