FROM apache/superset:4.1.2

USER root
RUN pip install --no-cache-dir "PyAthena[SQLAlchemy]>=3.0" psycopg2-binary
COPY custom_pythonpath/ /app/pythonpath/
COPY assets/ /app/codex_assets/
COPY scripts/ /app/codex_scripts/
RUN chmod +x /app/codex_scripts/start_superset.sh \
    && chown -R superset:superset /app/codex_assets
USER superset

CMD ["/app/codex_scripts/start_superset.sh"]
