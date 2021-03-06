from flask import request, g
from structlog import get_logger
import opentracing

from entityservice import database as db
from entityservice.serialization import get_similarity_scores
from entityservice.utils import safe_fail_request
from entityservice.views import bind_log_and_span
from entityservice.views.auth_checks import abort_if_run_doesnt_exist, get_authorization_token_type_or_abort

logger = get_logger()


def get(project_id, run_id):
    log, parent_span = bind_log_and_span(project_id, run_id)
    log.info("Checking for results of run.")

    with opentracing.tracer.start_span('check-auth', child_of=parent_span) as span:
        # Check the project and run resources exist
        abort_if_run_doesnt_exist(project_id, run_id)
        # Check the caller has a valid results token.
        token = request.headers.get('Authorization')
        log.info("request to access run result authorized")
    with db.DBConn() as conn:
        with opentracing.tracer.start_span('get-run-state', child_of=parent_span) as span:
            state = db.get_run_state(conn, run_id)
            log.info("run state is '{}'".format(state))

        # Check that the run is not in a terminal state, otherwise 404
        if state == 'completed':
            with opentracing.tracer.start_span('get-run-result', child_of=parent_span) as span:
                return get_result(conn, project_id, run_id, token)
        elif state == 'error':
            safe_fail_request(500, message='Error during computation of run')
        else:
            safe_fail_request(404, message='run is not complete')


def get_result(dbinstance, project_id, run_id, token):
    result_type = db.get_project_column(dbinstance, project_id, 'result_type')
    auth_token_type = get_authorization_token_type_or_abort(project_id, token)

    if result_type == 'groups':
        logger.info("Groups result being returned")
        result = db.get_run_result(dbinstance, run_id)
        return {"groups": result}

    elif result_type == 'similarity_scores':
        logger.info("Similarity result being returned")
        return get_similarity_score_result(dbinstance, run_id)

    elif result_type == 'permutations':
        logger.info("Permutation result being returned")
        return get_permutations_result(project_id, run_id, dbinstance, token, auth_token_type)
    else:
        logger.warning("Unimplemented result type")
        safe_fail_request(500, message='Project has unknown result type')


def get_similarity_score_result(dbinstance, run_id):
    logger.info("Similarity score result being returned")
    try:
        filename = db.get_similarity_scores_filename(dbinstance, run_id)
        return get_similarity_scores(filename)

    except TypeError:
        logger.exception("Couldn't find the similarity score file for the runId %s", run_id)
        safe_fail_request(500, "Failed to retrieve similarity scores")


def get_permutations_result(project_id, run_id, dbinstance, token, auth_token_type):
    logger.info("Permutations and mask result type being returned")
    if auth_token_type == 'receipt_token':
        logger.debug("auth type receipt_token")
        dp_id = db.select_dataprovider_id(dbinstance, project_id, token)
        perm = db.get_permutation_result(dbinstance, dp_id, run_id)
        rows = db.get_smaller_dataset_size_for_project(dbinstance, project_id)
        result = {
            'permutation': perm,
            'rows': rows
        }
    elif auth_token_type == "result_token":
        logger.debug("auth type result_token")
        logger.info("Returning unencrypted mask to coordinator")
        # The mask is a json blob of an
        # array of 0/1 ints
        mask = db.get_permutation_unencrypted_mask(dbinstance, project_id, run_id)
        result = {
            "mask": mask
        }
    else:
        logger.warning("Didn't recognize the auth token type of {}".format(auth_token_type))
        safe_fail_request(500, "Unknown error. Please report to the developers")
    return result
