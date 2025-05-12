FROM python:3.9-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos primeiro (para cache do Docker)
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Criar diretório de logs
RUN mkdir -p /var/log

# Configurar buffer Python para saída imediata
ENV PYTHONUNBUFFERED=1

# Comando para executar
CMD ["python", "-u", "disconnect_expired_users.py"]
