FROM apache/superset:4.1.2

USER root
RUN pip install --no-cache-dir "PyAthena[SQLAlchemy]>=3.0"
COPY custom_pythonpath/ /app/pythonpath/
USER superset

