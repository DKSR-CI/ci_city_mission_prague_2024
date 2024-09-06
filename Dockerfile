FROM python:3.11 AS base

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

FROM base AS energy

COPY usecase_energy/requirements.txt ./requirements_energy.txt
RUN pip install -r requirements_energy.txt
COPY usecase_energy ./

FROM base AS heat_waves

COPY usecase_heat_waves/requirements.txt ./requirements_heat_waves.txt
RUN pip install -r requirements_heat_waves.txt
COPY usecase_heat_waves ./

FROM base AS mobility

COPY usecase_mobility/requirements.txt ./requirements_mobility.txt
RUN pip install -r requirements_mobility.txt
COPY usecase_mobility ./
