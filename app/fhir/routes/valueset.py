from app.fhir import bp_fhir
from app.auth.authentication import token_auth
from app.main.utils.rate_limit import rate_limit
from app.main.utils.etag import etag
from app.fhir.models.codesets import ValueSet
from flask import url_for, jsonify


@bp_fhir.route('fhir/ValueSet/<string:resource_id>', methods=['GET'])
@token_auth.login_required
@rate_limit(limit=5, period=15)
@etag
def get_valueset(resource_id):
    """
    Return a FHIR ValueSet resource as JSON.
    """
    valueset = ValueSet.query.filter(ValueSet.resource_id == resource_id).first_or_404()
    data = valueset.dump_fhir_json()
    response = jsonify(data)
    response.headers['Location'] = url_for('fhir.get_valueset', resource_id=valueset.resource_id)
    response.status_code = 200
    return response


@bp_fhir.route('fhir/ValueSet', methods=['GET'])
@token_auth.login_required
@rate_limit(limit=5, period=15)
@etag
def get_valuesets():
    """
    Return FHIR ValueSet routes as JSON.
    """
    return jsonify('Coming Soon!')