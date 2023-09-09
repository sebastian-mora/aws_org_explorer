import boto3
import botocore

from core.iamEnum import retreive_roles, retreive_users
from core.db import Db

import concurrent.futures

from config import neo4j_config, sso_config


def process_account(assumed_role_arn, db):
    print(f"\tListing {account['accountId']} using role, {assumed_role_arn}")

    iamClient = boto3.client("iam")
    try:
        roles = retreive_roles(iamClient)
        users = retreive_users(iamClient)

        for role in roles:
            db.add_aws_role(role)
        for user in users:
            db.add_aws_user(user)

    except botocore.exceptions.ClientError as error:
        if error.response["Error"]["Code"] == "AccessDenied":
            print(
                f"\tRole {assumed_role_arn} does not have permissions to list users/roles...trying next role"
            )


if __name__ == "__main__":
    db = Db(neo4j_config["host"], neo4j_config["user"], neo4j_config["pass"])

    account = ""
    role = ""

    db.add_aws_account(account)

    process_account(role, db)
