FROM freqtradeorg/freqtrade:stable

RUN mkdir -p /freqtrade/user_data/logs /freqtrade/user_data/strategies /freqtrade/user_data/backups

COPY user_data/config.json /freqtrade/user_data/config.json
COPY user_data/strategies/SampleStrategy.py /freqtrade/user_data/strategies/SampleStrategy.py

USER root
RUN chmod -R 777 /freqtrade/user_data
