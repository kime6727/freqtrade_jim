FROM freqtradeorg/freqtrade:stable

COPY user_data/config.json /freqtrade/user_data/config.json
COPY user_data/strategies/ /freqtrade/user_data/strategies/

RUN mkdir -p /freqtrade/user_data/logs
