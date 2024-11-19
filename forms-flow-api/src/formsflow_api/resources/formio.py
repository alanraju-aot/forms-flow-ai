"""API endpoints for managing formio resource."""

import json
from http import HTTPStatus
from typing import Dict

import jwt
from flask import after_this_request, current_app
from flask_restx import Namespace, Resource, fields
from formsflow_api_utils.exceptions import BusinessException, ExternalError
from formsflow_api_utils.utils import (
    CLIENT_GROUP,
    DESIGNER_GROUP,
    REVIEWER_GROUP,
    Cache,
    auth,
    cors_preflight,
    get_role_ids_from_user_groups,
    profiletime,
)
from formsflow_api_utils.utils.enums import FormioRoles
from formsflow_api_utils.utils.startup import (
    collect_role_ids,
    collect_user_resource_ids,
)
from formsflow_api_utils.utils.user_context import UserContext, user_context

API = Namespace("Formio", description="formio")

role = API.model(
    "Role",
    {
        "roleId": fields.String(description="The role or resource Id"),
        "type": fields.String(
            description="The Id type",
            enum=["DESIGNER", "ANONYMOUS", "CLIENT", "REVIEWER", "RESOURCE_ID"],
        ),
    },
)
role_success_response_model = API.model(
    "Roles",
    {
        "form": fields.List(
            fields.Nested(role, description="List of role / resource Ids")
        ),
    },
)


@cors_preflight("GET, OPTIONS")
@API.route("/roles", methods=["GET", "OPTIONS"])
class FormioResource(Resource):
    """Resource for retrieving roles from Formio."""

    @staticmethod
    @auth.require
    @profiletime
    @user_context
    @API.response(
        200,
        "OK:- Successful request.",
        headers={"x-jwt-token": "Formio token"},
        model=role_success_response_model,
    )
    @API.response(
        401,
        "UNAUTHORIZED:- Authorization header not provided or an invalid token passed.",
    )
    @API.response(503, "SERVICE_UNAVAILABLE:- Service failed to serve the request.")
    def get(**kwargs):
        """
        Get formio role ids.

        For requests with designer authorization, the server will send a response
        with role Ids of the following roles `DESIGNER`, `REVIEWER`, `CLIENT`,
        `ANONYMOUS` along with `RESOURCE_ID`.

        For requests without designer authorization, no resource / role Ids will be returned.
        This is because only designer will be expected to use the resource and role Ids.

        All successful response will contain `x-jwt-token` in the response header
        which is the formio token generated from the server.
        """
        user: UserContext = kwargs["user"]
        assert user.token_info is not None

        def filter_user_based_role_ids(item):
            filter_list = []
            if DESIGNER_GROUP in user.roles:
                filter_list.append(FormioRoles.DESIGNER.name)
            if REVIEWER_GROUP in user.roles:
                filter_list.append(FormioRoles.REVIEWER.name)
            if CLIENT_GROUP in user.roles:
                filter_list.append(FormioRoles.CLIENT.name)
            return item["type"] in filter_list

        @after_this_request
        def add_jwt_token_as_header(response):
            if response.status_code != 200:
                return response
            _role_ids = [
                role["roleId"]
                for role in list(
                    filter(
                        filter_user_based_role_ids,
                        response.json.get("form"),
                    )
                )
            ]
            _resource_id = next(
                role["roleId"]
                for role in response.json.get("form")
                if role["type"] == FormioRoles.RESOURCE_ID.value
            )

            unique_user_id = (
                user.email or f"{user.user_name}@formsflow.ai"
            )  # Email is not mandatory in keycloak
            project_id: str = current_app.config.get("FORMIO_PROJECT_URL")
            payload: Dict[str, any] = {
                "external": True,
                "form": {"_id": _resource_id},
                "user": {"_id": unique_user_id, "roles": _role_ids, "customRoles": user.roles},
            }
            if project_id:
                payload["project"] = {"_id": project_id}
            response.headers["x-jwt-token"] = jwt.encode(
                payload=payload,
                key=current_app.config.get("FORMIO_JWT_SECRET"),
                algorithm="HS256",
            )
            response.headers["Access-Control-Expose-Headers"] = "x-jwt-token"
            if DESIGNER_GROUP not in user.roles:
                response.set_data(json.dumps({"form": []}))
                return response
            return response

        user_role = user.roles
        role_ids = Cache.get("formio_role_ids")
        formio_user_resource_id = Cache.get("user_resource_id")
        current_app.logger.info(f"role_ids , formio_user_resource_id : {role_ids}, {formio_user_resource_id}")
        if not role_ids:
            collect_role_ids(current_app)
            role_ids = Cache.get("formio_role_ids")
        if not formio_user_resource_id:
            collect_user_resource_ids(current_app)
            formio_user_resource_id = Cache.get("user_resource_id")

        roles = get_role_ids_from_user_groups(role_ids, user_role)
        current_app.logger.info(f"roles : {roles}")
        if roles is not None:
            roles.append(
                {
                    "roleId": formio_user_resource_id,
                    "type": FormioRoles.RESOURCE_ID.value,
                }
            )
            result = {"form": roles}
            return result, HTTPStatus.OK

        raise BusinessException(ExternalError.FORM_SERVICE_UNAVAILABLE)
