FROM python:3.13-slim

ENV UV_PROJECT_ENVIRONMENT=/usr/local
RUN pip install -U uv==0.4.27

WORKDIR /project

COPY pyproject.toml uv.lock README.md /project/
RUN uv sync --no-dev --frozen --no-editable

COPY . /project

CMD ./manage.py collectstatic --no-input && ./manage.py migrate && gunicorn kc_django.wsgi --forwarded-allow-ips="*" --access-logfile - -b 0.0.0.0:80
