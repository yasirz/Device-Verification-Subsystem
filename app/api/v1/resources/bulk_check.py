import os

from app import GlobalConfig, UploadDir, AllowedFiles, celery
from ..assets.error_handling import *
from ..assets.responses import responses, mime_types

from ..helpers.bulk_summary import BulkSummary

from flask import request, send_from_directory

upload_folder = os.path.join(app.root_path, UploadDir)


class BulkCheck:

    task_list = []

    @staticmethod
    def summary():
        try:
            file = request.files.get('file')
            if file:
                if file.filename != '':
                        if file and '.' in file.filename and \
                                file.filename.rsplit('.', 1)[1].lower() in AllowedFiles:  # input file type validation
                            imeis = list(set(line.decode('ascii', errors='ignore') for line in (l.strip() for l in file) if line))
                            if imeis and int(GlobalConfig['MinFileContent']) < len(imeis) < int(GlobalConfig['MaxFileContent']):  # input file content validation
                                response = BulkSummary.get_summary.apply_async((imeis, "imeis"))
                                data = {
                                    "message": "Please wait your file is being processed.",
                                    "task_id": response.id
                                }
                                BulkCheck.task_list.append(response.id)
                                return Response(json.dumps(data), status=200, mimetype='application/json')

                            else:
                                return custom_response("File contains incorrect/no content.", status=responses.get('bad_request'), mimetype=mime_types.get('json'))
                        else:
                            return custom_response("System only accepts tsv/txt files.", responses.get('bad_request'), mime_types.get('json'))
                else:
                    return custom_response('No file selected.', responses.get('bad_request'), mime_types.get('json'))
            else:  # check for tac if file not uploaded
                tac = request.form.get('tac')
                if tac:
                    if tac.isdigit() and len(tac) == int(GlobalConfig['TacLength']):
                        imei = tac + str(GlobalConfig['MinImeiRange'])
                        imei_list = [int(imei) + x for x in range(int(GlobalConfig['MaxImeiRange']))]
                        response = BulkSummary.get_summary.apply_async((imei_list, "tac", tac))
                        data = {
                            "message": "Please wait your request is being processed.",
                            "task_id": response.id
                        }
                        BulkCheck.task_list.append(response.id)
                        return Response(json.dumps(data), status=200, mimetype='application/json')
                    else:
                        return custom_response("Invalid TAC", responses.get('bad_request'), mime_types.get('json'))
                else:
                    return custom_response("Upload file or enter TAC.", status=responses.get('bad_request'), mimetype=mime_types.get('json'))
        except Exception as e:
            app.logger.info("Error occurred while retrieving summary.")
            app.logger.exception(e)
            return custom_response("Failed to verify bulk imeis.", responses.get('service_unavailable'), mime_types.get('json'))

    @staticmethod
    def send_file(filename):
        try:
            return send_from_directory(directory=upload_folder, filename=filename)  # returns file when user wnats to download non compliance report
        except Exception as e:
            app.logger.info("Error occurred while downloading non compliant report.")
            app.logger.exception(e)
            return custom_response("Compliant report not found.", responses.get('not_found'), mime_types.get('json'))

    @staticmethod
    def check_status(task_id):
        if task_id in BulkCheck.task_list:
            task = BulkSummary.get_summary.AsyncResult(task_id)
            if task.state == 'SUCCESS':
                response = {
                    "state": task.state,
                    "result": task.get()
                }
            elif task.state == 'PENDING':
                # job did not start yet
                response = {
                    'state': task.state
                }
            elif task.state != 'FAILURE':
                response = {
                    'state': task.state
                }
            else:
                # something went wrong in the background job
                response = {
                    'state': task.state
                }
        else:
            response = {
                "state": "task not found enter a valid task id"
            }

        return Response(json.dumps(response), status=200, mimetype='application/json')

