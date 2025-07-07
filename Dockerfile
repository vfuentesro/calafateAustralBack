# Usa una imagen oficial de Python
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de requerimientos
COPY requirements.txt .

# Instala dependencias del sistema para mysqlclient
RUN apt-get update && apt-get install -y gcc default-libmysqlclient-dev pkg-config && rm -rf /var/lib/apt/lists/*

# Instala dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código
COPY . .

# Expone el puerto (Cloud Run usará $PORT)
EXPOSE 8080

# Variables de entorno para Django
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Comando para correr el servidor
CMD ["sh", "-c", "python manage.py migrate && gunicorn Backedn_Calafate_Austral.wsgi:application --bind 0.0.0.0:8080"]