FROM python:3.11-slim as base

# The following is adapted from:
# https://sourcery.ai/blog/python-docker/

# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

FROM base AS python-deps

# Install pipenv and compilation dependencies
RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc

RUN mkdir -p /base
WORKDIR /base

# Install python dependencies in /.venv
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

# Copy virtualenv from python-deps stage
COPY --from=python-deps /base/.venv /base/.venv
ENV PATH="/base/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends jq

# Create and switch to a new user
RUN useradd --create-home appuser
WORKDIR /home/appuser
USER appuser

# Install application into container
COPY . .

EXPOSE 8000

# Run the application
ENTRYPOINT ["gunicorn", "-w", "1", "app:app", "-b", "0.0.0.0:8000", "--log-level", "INFO", "--access-logfile", "-"]