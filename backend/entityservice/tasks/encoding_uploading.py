
import io

import more_itertools

from entityservice import cache
from entityservice.database import *
from entityservice.error_checking import check_dataproviders_encoding, handle_invalid_encoding_data, \
    InvalidEncodingError
from entityservice.object_store import connect_to_object_store
from entityservice.serialization import binary_pack_filters, deserialize_bitarray, binary_format
from entityservice.settings import Config as config
from entityservice.async_worker import celery, logger
from entityservice.tasks.base_task import TracedTask
from entityservice.tasks.pre_run_check import check_for_executable_runs

from entityservice.utils import iterable_to_stream, fmt_bytes, clks_uploaded_to_project


@celery.task(base=TracedTask, ignore_result=True, args_as_tags=('project_id', 'dp_id'))
def handle_raw_upload(project_id, dp_id, receipt_token, parent_span=None):
    # User has uploaded base64 encodings as JSON
    log = logger.bind(pid=project_id, dp_id=dp_id)
    log.info("Handling user provided base64 encodings")

    with DBConn() as db:
        if not check_project_exists(db, project_id):
            log.info("Project deleted, stopping immediately")
            return
        expected_count = get_number_of_hashes(db, dp_id)

    log.info(f"Expecting to handle {expected_count} encodings")
    mc = connect_to_object_store()

    # Input file is line separated base64 record encodings.
    raw_file = config.RAW_FILENAME_FMT.format(receipt_token)
    raw_data_response = mc.get_object(config.MINIO_BUCKET, raw_file)

    # Set up streaming processing pipeline
    buffered_stream = iterable_to_stream(raw_data_response.stream())
    text_stream = io.TextIOWrapper(buffered_stream, newline='\n')

    clkcounts = []

    def filter_generator():
        log.debug("Deserializing json filters")
        first_encoding_size = None
        for i, line in enumerate(text_stream):
            ba = deserialize_bitarray(line)
            yield (ba, i, ba.count())
            clkcounts.append(ba.count())
            encsize = len(ba)
            if i == 0:
                first_encoding_size = encsize
            if encsize != first_encoding_size:
                raise ValueError("Encodings were not all the same size")

        log.info(f"Processed {len(clkcounts)} hashes")

    # We peek at the first element as we need the encoding size
    # for the ret of our processing pipeline
    python_filters = more_itertools.peekable(filter_generator())
    # Note the len of a bitarray is returned in bits but we require
    # this to be a multiple of 8 so we use bytes.
    uploaded_encoding_size = len(python_filters.peek()[0])//8

    # This is the first time we've seen the encoding size from this data provider
    try:
        check_dataproviders_encoding(project_id, uploaded_encoding_size)
    except InvalidEncodingError as e:
        log.warning(e.args[0])
        handle_invalid_encoding_data(project_id, dp_id)

    with DBConn() as db:
        # Save the encoding size as metadata
        set_uploaded_encoding_size(db, dp_id, uploaded_encoding_size)

    # Output file is our custom binary packed file
    filename = config.BIN_FILENAME_FMT.format(receipt_token)
    bit_packed_element_size = binary_format(uploaded_encoding_size).size
    num_bytes = expected_count * bit_packed_element_size

    # If small enough preload the data into our redis cache
    if expected_count < config.ENTITY_CACHE_THRESHOLD:
        log.info("Caching pickled clk data")
        python_filters = list(python_filters)
        cache.set_deserialized_filter(dp_id, python_filters)
    else:
        log.info("Not caching clk data as it is too large")

    packed_filters = binary_pack_filters(python_filters, uploaded_encoding_size)
    packed_filter_stream = iterable_to_stream(packed_filters)

    # Upload to object store
    log.info(f"Uploading {expected_count} encodings of size {uploaded_encoding_size} " +
             f"to object store. Total Size: {fmt_bytes(num_bytes)}")
    mc.put_object(config.MINIO_BUCKET, filename, data=packed_filter_stream, length=num_bytes)

    with DBConn() as conn:
        update_encoding_metadata(conn, filename, dp_id)

    # Now work out if all parties have added their data
    if clks_uploaded_to_project(project_id, check_data_ready=True):
        log.info("All parties' data present. Scheduling any queued runs")
        print('and the span is: {}'.format(handle_raw_upload.span))
        check_for_executable_runs.delay(project_id, handle_raw_upload.get_serialized_span())
