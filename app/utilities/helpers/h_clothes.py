from flask import jsonify, render_template, Response, request

from config import settings


def h_bck_clothes_tnved() -> Response:

    status = 'danger'
    message = settings.Messages.MANUAL_TNVED_ERROR
    cl_type = request.form.get('cl_type', '').replace('--', '')

    if not cl_type or cl_type not in settings.Clothes.TYPES:
        return jsonify(dict(status=status, message=message + settings.Messages.STRANGE_REQUESTS))

    tnved_list: tuple = settings.Clothes.CLOTHES_TNVED_DICT.get(cl_type)[1]
    status = 'success'
    message = settings.Messages.MANUAL_TNVED_SUCCESS
    return jsonify(dict(status=status, message=message,
                        tnved_report=render_template('helpers/clothes/manual_tnved_modal_report.html', **locals())))