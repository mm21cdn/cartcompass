FROM python:3.11-slim

LABEL org.opencontainers.image.title="CartCompass UK 20km Grocery & Loyalty Agent" \
      org.opencontainers.image.description="Google ADK Multi-Agent UK Grocery & Loyalty Optimizer (GBP £)" \
      org.opencontainers.image.vendor="mrmitchell"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GROCERY_APP_STATE_DIR=/var/lib/cartcompass \
    PORT=8765

WORKDIR /app

# Create non-root runtime user and persistent SQLite directory
RUN groupadd -r cartcompass && useradd -r -g cartcompass cartcompass \
    && mkdir -p /var/lib/cartcompass \
    && chown -R cartcompass:cartcompass /var/lib/cartcompass /app

COPY pyproject.toml README.md app.py ./
COPY cartcompass/ ./cartcompass/

# Run automated Golden Evaluation Harness & Unit Tests at image build time
RUN python3 -m unittest discover -s cartcompass -p "*_test.py" -v \
    && python3 -m cartcompass.eval_harness

USER cartcompass
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/state')" || exit 1

ENTRYPOINT ["python3", "app.py"]
CMD ["--host", "0.0.0.0", "--port", "8765"]
