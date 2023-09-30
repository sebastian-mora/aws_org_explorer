import boto3
import botocore

from core.iamEnum import get_roles, get_users
from core.db import Db
from boto3 import session


import os
from dotenv import load_dotenv

load_dotenv()


def process_account(iamClient, db):
    # print(f"\tListing {account['accountId']} using role, {assumed_role_arn}")

    try:
        roles = get_roles(iamClient)
        users = get_users(iamClient)

        for role in roles:
            db.add_aws_role(role)
        for user in users:
            db.add_aws_user(user)

    except botocore.exceptions.ClientError as error:
        return error


def assume_aws_role(role_arn, session_name, duration_seconds=3600) -> session:
    sts_client = boto3.client("sts")
    response = sts_client.assume_role(
        RoleArn=role_arn, RoleSessionName=session_name, DurationSeconds=duration_seconds
    )

    # Create a new Boto3 session using the temporary credentials
    temporary_credentials = response["Credentials"]
    session = boto3.Session(
        aws_access_key_id=temporary_credentials["AccessKeyId"],
        aws_secret_access_key=temporary_credentials["SecretAccessKey"],
        aws_session_token=temporary_credentials["SessionToken"],
    )

    return session


if __name__ == "__main__":
    db = Db(
        uri=os.getenv("NEO4J_URI"),
        password=os.getenv("NEO4J_PASSWORD"),
        user=os.getenv("NEO4J_USER"),
    )

    # Assume role in account
    assume_role_arn = ""
    session = assume_aws_role(assume_aws_role)
    iamClient = session.client("ec2")

    process_account(iamClient, db)
