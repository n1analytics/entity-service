#!/usr/bin/env python3.4
"""
Config shared between the application backend and the celery workers.
"""
import os
import logging


class Config(object):
    """
    Hard coded default configuration which can be overwritten with environment variables
    """

    DEBUG = os.environ.get("DEBUG", "false") == "true"

    LOGFILE = os.environ.get("LOGFILE", None)
    fileFormat = logging.Formatter('%(asctime)-15s %(name)-12s %(levelname)-8s: %(message)s')
    consoleFormat = logging.Formatter('%(asctime)-10s %(levelname)-8s %(message)s',
                                      datefmt="%H:%M:%S")

    DATABASE_SERVER = os.environ.get('DATABASE_SERVER', 'db')
    REDIS_SERVER = os.environ.get('REDIS_SERVER', 'redis')
    DATABASE = os.environ.get('DATABASE', 'postgres')
    DATABASE_USER = os.environ.get('DATABASE_USER', 'postgres')
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', '')

    BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://{}:6379/0'.format(REDIS_SERVER))

    CELERY_RESULT_BACKEND = BROKER_URL

    CELERY_ANNOTATIONS = {
        'async_worker.calculate_mapping': {'rate_limit': '1/s'}
    }

    ENCRYPTION_CHUNK_SIZE = int(os.environ.get('ENCRYPTION_CHUNK_SIZE', '100'))

    # Matches that have more than this number of entities will use the
    # faster greedy solver
    GREEDY_SIZE = int(os.environ.get('GREEDY_SIZE', '1000'))

    # Number of comparisons to match per chunk. Default is 20M.
    # Larger jobs will favor larger chunks
    GREEDY_CHUNK_SIZE = int(os.environ.get('GREEDY_CHUNK_SIZE', '20000000'))

    ENTITY_MATCH_THRESHOLD = float(os.environ.get('ENTITY_MATCH_THRESHOLD', '0.95'))


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True


