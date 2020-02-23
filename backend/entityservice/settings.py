#!/usr/bin/env python3.4
"""
Config shared between the application backend and the celery workers.
"""
import datetime
import os


class Config(object):
    """
    Hard coded default configuration which can be overwritten with environment variables.
    """

    # If adding or deleting any, please ensure that the changelog will mention them.

    DEBUG = os.getenv("DEBUG", "false") == "true"

    CONNEXION_STRICT_VALIDATION = os.getenv("CONNEXION_STRICT_VALIDATION", "true").lower() == "true"
    CONNEXION_RESPONSE_VALIDATION = os.getenv("CONNEXION_RESPONSE_VALIDATION", "true").lower() == "true"

    LOG_CONFIG_FILENAME = os.getenv("LOG_CFG")
    TRACING_CONFIG_FILENAME = os.getenv("TRACE_CFG")

    LOGFILE = os.getenv("LOGFILE")
    LOG_HTTP_HEADER_FIELDS = os.getenv("LOG_HTTP_HEADER_FIELDS")

    REDIS_SERVER = os.getenv('REDIS_SERVER', 'redis')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    REDIS_USE_SENTINEL = os.getenv('REDIS_USE_SENTINEL', 'false').lower() == "true"
    REDIS_SENTINEL_NAME = os.getenv('REDIS_SENTINEL_NAME', 'mymaster')

    MINIO_SERVER = os.getenv('MINIO_SERVER', 'minio:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', '')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', '')
    MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'entityservice')

    DATABASE_SERVER = os.getenv('DATABASE_SERVER', 'db')
    DATABASE = os.getenv('DATABASE', 'postgres')
    DATABASE_USER = os.getenv('DATABASE_USER', 'postgres')
    DATABASE_PASSWORD = os.getenv('DATABASE_PASSWORD', '')

    FLASK_DB_MIN_CONNECTIONS = os.getenv('FLASK_DB_MIN_CONNECTIONS', '1')
    FLASK_DB_MAX_CONNECTIONS = os.getenv('FLASK_DB_MAX_CONNECTIONS', '10')

    CELERY_BROKER_URL = os.getenv(
        'CELERY_BROKER_URL',
        ('sentinel://:{}@{}:26379/0' if REDIS_USE_SENTINEL else 'redis://:{}@{}:6379/0').format(REDIS_PASSWORD, REDIS_SERVER)
    )

    CELERY_DB_MIN_CONNECTIONS = os.getenv('CELERY_DB_MIN_CONNECTIONS', '1')
    CELERY_DB_MAX_CONNECTIONS = os.getenv('CELERY_DB_MAX_CONNECTIONS', '3')

    CELERY_BROKER_TRANSPORT_OPTIONS = {'master_name': "mymaster"} if REDIS_USE_SENTINEL else {}

    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
    CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {'master_name': "mymaster"} if REDIS_USE_SENTINEL else {}

    CELERY_ANNOTATIONS = {
        # Note that these are per worker instance per task rate limits.
        # tasks would get delayed before being run
        # https://celery.readthedocs.io/en/latest/userguide/tasks.html#Task.rate_limit
        #'entityservice.tasks.comparing.create_comparison_jobs': {'rate_limit': '1/m'}
    }

    CELERY_ROUTES = {
        'async_worker.calculate_mapping': {'queue': 'celery'},
        'async_worker.compute_similarity': {'queue': 'compute'},
        'async_worker.aggregate_filter_chunks': {'queue': 'highmemory'},
        'async_worker.solver_task': {'queue': 'highmemory'},
        'async_worker.save_and_permute': {'queue': 'highmemory'},
        'async_worker.handle_raw_upload': {'queue': 'celery'}
    }

    CELERYD_PREFETCH_MULTIPLIER = int(os.getenv('CELERYD_PREFETCH_MULTIPLIER', '1'))
    CELERYD_MAX_TASKS_PER_CHILD = int(os.getenv('CELERYD_MAX_TASKS_PER_CHILD', '4'))
    CELERYD_CONCURRENCY = int(os.getenv("CELERYD_CONCURRENCY", '0'))
    CELERY_ACKS_LATE = os.getenv('CELERY_ACKS_LATE', 'false') == 'true'

    # Number of comparisons per chunk (on average).
    CHUNK_SIZE_AIM = int(os.getenv('CHUNK_SIZE_AIM', '300_000_000'))

    # If there are more than 1M CLKS, don't cache them in redis
    MAX_CACHE_SIZE = int(os.getenv('MAX_CACHE_SIZE', '1000000'))

    _CACHE_EXPIRY_SECONDS = int(os.getenv('CACHE_EXPIRY_SECONDS', datetime.timedelta(days=10).total_seconds()))
    CACHE_EXPIRY = datetime.timedelta(seconds=_CACHE_EXPIRY_SECONDS)

    ENTITY_CACHE_THRESHOLD = int(os.getenv('ENTITY_CACHE_THRESHOLD', '1000000'))

    RAW_FILENAME_FMT = "quarantine/{}.txt"
    BIN_FILENAME_FMT = "raw-clks/{}.bin"
    SIMILARITY_SCORES_FILENAME_FMT = "similarity-scores/{}.bin"
    BLOCKING_DATA_FILENAME_FMT = "blocked-encodings/{}.bin"

    # Encoding size (in bytes)
    MIN_ENCODING_SIZE = int(os.getenv('MIN_ENCODING_SIZE', '1'))
    MAX_ENCODING_SIZE = int(os.getenv('MAX_ENCODING_SIZE', '1024'))
