
# def lambda_handler(event, context):
#     # get session_id
#     session_id = event['session_id']
#     return {
#         "statusCode": 200,
#         "response": "Hello, World from Lambda fuction 2!"
#         + f" session_id: {session_id}"
#     }

import json
import boto3
import base64
import logging
# from datetime import datetime
import psycopg
import uuid
ssm_client = boto3.client("ssm")
secretsmanager = boto3.client("secretsmanager")

s3_bucket_name_parameter = "/AgenticLLMAssistantWorkshop/AgentDataBucketParameter"
db_secret_arn = "arn:aws:secretsmanager:us-east-1:381491977872:secret:ServerlessLlmAssistantStack-abhVMLv8At4Q-KYkTlW"

secret_response = secretsmanager.get_secret_value(
    SecretId=db_secret_arn
)
S3_BUCKET_NAME = ssm_client.get_parameter(Name=s3_bucket_name_parameter)
BUCKET_NAME = S3_BUCKET_NAME["Parameter"]["Value"]
# Initialize the S3 client
s3 = boto3.client('s3')
MAX_FILE_SIZE_MB = 5  # Maximum file size in MB
ALLOWED_FILE_TYPE = 'application/pdf'

database_secrets = json.loads(secret_response["SecretString"])

# Extract database connection parameters from secrets
host = database_secrets['host']
dbname = database_secrets['dbname']
username = database_secrets['username']
password = database_secrets['password']
port = database_secrets["port"]

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def connect_to_db():
    """Establish a connection to the PostgreSQL database."""
    return psycopg.connect(
    host=host,
    port=port,
    dbname=dbname,
    user=username,
    password=password,
)

def validate_files(files):
    """Validate all files in the payload."""
    errors = []

    for file in files:
        file_name = file.get('fileName')
        file_type = file.get('fileType')
        file_content = file.get('fileContent')
        category = file.get('category')

        # Check for missing fields
        if not (file_name and file_type and file_content and category):
            errors.append({
                "fileName": file_name or "unknown",
                "error": "Missing file name, type, or content."
            })
            continue

        # Validate file type
        if file_type != ALLOWED_FILE_TYPE:
            errors.append({
                "fileName": file_name,
                "error": f"Invalid file type. Only '{ALLOWED_FILE_TYPE}' is allowed."
            })
            continue

        # Validate file size
        try:
            decoded_content = base64.b64decode(file_content)
            file_size_mb = len(decoded_content) / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                errors.append({
                    "fileName": file_name,
                    "error": f"File size exceeds the {MAX_FILE_SIZE_MB} MB limit."
                })
        except Exception as e:
            errors.append({
                "fileName": file_name,
                "error": f"Error decoding file content: {str(e)}"
            })

    return errors

def insert_into_db(cursor, file_id, category, file_name, doc_url, user_id):
    """Insert file details into the database."""
    query = """
        INSERT INTO upload_documents (id, job, year, file_name, doc_url, status, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s);
    """
    cursor.execute(query, (file_id, category, 2024, file_name, doc_url, 0, user_id))

def lambda_handler(event, context):
    try:
        # Parse the incoming request body
        # body = json.loads(event['body'])
        session_id = event.get('session_id')   
        files = event.get('files', [])  # Expecting a list of files
        if not session_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Session ID is missing."})
            }
        if not files:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No files provided in the request."})
            }

        # Validate all files
        validation_errors = validate_files(files)
        if validation_errors:
            return {
                "statusCode": 400,
                "body": json.dumps({"validationErrors": validation_errors})
            }

        # Connect to the database
        conn = connect_to_db()
        cursor = conn.cursor()

        # Upload files to S3 and store details in the database
        upload_results = []
        for file in files:
            file_name = file['fileName']
            file_type = file['fileType']
            file_content = file['fileContent']
            category = file['category']
            s3_key = f"{category}/{file_name}" 
            doc_url = f"https://{BUCKET_NAME}.s3.us-east-1.amazonaws.com/{s3_key}"
            decoded_content = base64.b64decode(file_content)
            # file_source = f"s3://{BUCKET_NAME}/{file_name}"
            # doc_url = f"s3://{BUCKET_NAME}/{file_name}"
            try:
                # Check if file_name already exists in the database
                cursor.execute("SELECT COUNT(*) FROM upload_documents WHERE file_name = %s AND session_id = %s", (file_name, session_id))
                exists = cursor.fetchone()[0] > 0

                if exists:
                    upload_results.append({
                        "fileName": file_name,
                        "status": "skipped",
                        "message": "File already exists in the database."
                    })
                    continue  # Skip to the next file
                # Generate a UUID v4 for the file ID
                file_id = str(uuid.uuid4())

                # Upload to S3
                s3.put_object(
                    Bucket=BUCKET_NAME,
                    Key=s3_key,
                    Body=decoded_content,
                    ContentType=file_type
                )

                # Insert into database
                insert_into_db(cursor, file_id, category, file_name, doc_url, session_id)
                conn.commit()

                upload_results.append({
                    "fileName": file_name,
                    "status": "success",
                    "message": f"File uploaded successfully with ID {file_id}.",
                    "fileSource": doc_url
                })
            except Exception as e:
                conn.rollback()
                upload_results.append({
                    "fileName": file_name,
                    "status": "failed",
                    "error": f"Error: {str(e)}"
                })

        # Close the database connection
        cursor.close()
        conn.close()

        return {
            "statusCode": 200,
            "body": json.dumps({"uploadResults": upload_results})
        }

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        # logger.error(e)
        # print(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error."})
        }