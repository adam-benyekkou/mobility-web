FROM mambaorg/micromamba:latest

USER root

# Install system dependencies
# git is needed for pip install git+... if any
RUN apt-get update && apt-get install -y \
    build-essential \
    libgdal-dev \
    git \
    curl \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

# Create user home directories for mobility to avoid interactive prompts
# We create them in /home/mambauser because that's the default user
RUN mkdir -p /home/mambauser/.mobility/data/projects && \
    mkdir -p /home/mambauser/.mobility/cache && \
    chown -R mambauser:mambauser /home/mambauser/.mobility

USER mambauser

# Install python and R dependencies via conda
# We use conda-forge for binary R packages to avoid compilation
RUN micromamba install -y -n base -c conda-forge \
    python=3.12 \
    r-base=4.3.3 \
    gdal \
    geos \
    proj \
    osmium-tool \
    r-sf \
    r-dplyr \
    r-data.table \
    r-arrow \
    r-ggplot2 \
    r-duckdb \
    r-stringi \
    r-curl \
    r-xml2 \
    r-cluster \
    r-fnn \
    r-dbscan \
    && micromamba clean --all --yes

# Activate environment for subsequent instructions
ARG MAMBA_DOCKERFILE_ACTIVATE=1

WORKDIR /app

# Copy dependency definition to leverage Docker cache
COPY --chown=mambauser:mambauser pyproject.toml /app/pyproject.toml
COPY --chown=mambauser:mambauser environment.yml /app/environment.yml
COPY --chown=mambauser:mambauser requirements-front.txt /app/requirements-front.txt

# Install python dependencies
# Installing mobility dependencies first
# We use --no-deps for mobility itself later, but here we want dependencies
# Actually pip install . will install dependencies defined in pyproject.toml
# But we can pre-install them to cache
# pip install -e . is not good for docker.
# We will just install deps.
RUN pip install "geopandas" "numpy<2" "pandas<3" "scipy" "requests" "shortuuid" "pyarrow" "openpyxl" "py7zr" "rich" "python-dotenv" "geojson" "matplotlib" "seaborn" "pyogrio" "polars" "psutil" "networkx" "plotly" "scikit-learn" "gtfs_kit"

# Install front requirements
RUN pip install -r requirements-front.txt

# Copy mobility source code
COPY --chown=mambauser:mambauser mobility /app/mobility
COPY --chown=mambauser:mambauser README.md /app/README.md
COPY --chown=mambauser:mambauser DESCRIPTION /app/DESCRIPTION
COPY --chown=mambauser:mambauser .Rbuildignore /app/.Rbuildignore

# Install mobility package
RUN pip install .

# Pre-install R packages using mobility's own logic
# This ensures that any package not in conda is installed via R
# We set force_reinstall=False so it skips existing ones
# We force download method to 'curl' or 'auto'
ENV MOBILITY_PACKAGE_DATA_FOLDER=/home/mambauser/.mobility/data
ENV MOBILITY_PROJECT_DATA_FOLDER=/home/mambauser/.mobility/data/projects

# Configure R to use Posit Public Package Manager (P3M) for fast binary downloads
RUN echo 'options(repos = c(CRAN = "https://packagemanager.posit.co/cran/__linux__/bookworm/latest"))' >> /home/mambauser/.Rprofile

RUN python -c "from mobility.set_params import set_params; set_params(r_packages=True, r_packages_download_method='curl', debug=True)"

# Copy front source code
COPY --chown=mambauser:mambauser front /app/front


# Patch legacy windows-specific code for Linux environment
RUN sed -i 's/wininet/auto/g' front/app/scenario/scenario_001_from_docs.py && \
    sed -i 's/wininet/auto/g' front/app/services/scenario_service.py

# Ensure frontend module is in python path
ENV PYTHONPATH=/app/front:$PYTHONPATH

# [MVP] Pre-calculation is now handled via manual warmup at runtime to respect memory limits
# RUN python front/precalculate.py

# Expose required ports
EXPOSE 8050

# Default command
# Default command with hot-patching for mounted volumes
# Default command with hot-patching for mounted volumes and editable install
CMD ["sh", "-c", "pip install -e . --no-deps && sed -i 's/wininet/auto/g' front/app/scenario/scenario_001_from_docs.py && python front/app/pages/main/main.py"]
