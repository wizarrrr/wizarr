import os
from json import dumps, loads
from uuid import uuid4
from flask import send_from_directory, current_app, request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, reqparse
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

api = Namespace("Image", description="Image related operations", path="/image")

# Define the file upload parser
file_upload_parser = reqparse.RequestParser()
file_upload_parser.add_argument('file', location='files',
                                type=FileStorage, required=True,
                                help='Image file')

@api.route("")
class ImageListApi(Resource):
    """API resource for all images"""

    @jwt_required()
    @api.doc(security="jwt")
    @api.expect(file_upload_parser)
    def post(self):
        """Upload image"""
        # Check if the post request has the file part
        if 'file' not in request.files:
            return {"message": "No file part"}, 400
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            return {"message": "No selected file"}, 400
        if file:
            # Extract the file extension
            file_extension = os.path.splitext(secure_filename(file.filename))[1].lower()
            if file_extension not in ['.png', '.jpg', '.jpeg']:
                return {"message": "Unsupported file format"}, 400

            upload_folder = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            # Generate a unique filename using UUID
            filename = f"{uuid4()}{file_extension}"

            # Check if the file exists and generate a new UUID if it does
            while os.path.exists(os.path.join(upload_folder, filename)):
                filename = f"{uuid4()}{file_extension}"
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            return {"message": f"File {filename} uploaded successfully", "filename": filename}, 201


@api.route("/<filename>")
class ImageAPI(Resource):
    """API resource for a single image"""

    @api.response(404, "Image not found")
    @api.response(500, "Internal server error")
    def get(self, filename):
        """Get image"""
        # Sanitize the filename to avoid directory traversal
        filename = secure_filename(filename)

        # Assuming images are stored in a directory specified by UPLOAD_FOLDER config
        upload_folder = current_app.config['UPLOAD_FOLDER']
        image_path = os.path.join(upload_folder, filename)
        if os.path.exists(image_path):
            return send_from_directory(upload_folder, filename)
        else:
            return {"message": "Image not found"}, 404

    @jwt_required()
    @api.doc(description="Delete a single image")
    @api.response(404, "Image not found")
    @api.response(500, "Internal server error")
    def delete(self, filename):
        """Delete image"""
        # Sanitize the filename to avoid directory traversal
        filename = secure_filename(filename)

        upload_folder = current_app.config['UPLOAD_FOLDER']
        image_path = os.path.join(upload_folder, filename)

        # Check if the file exists
        if not os.path.exists(image_path):
            return {"message": "Image not found"}, 404

        os.remove(image_path)
        return {"message": "Image deleted successfully"}, 200
