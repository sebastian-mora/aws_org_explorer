import time

import boto3
import botocore

from config import sso_config


###
# Code from https://github.com/christophetd/aws-sso-device-code-authentication
###

def create_oidc_application(sso_oidc_client):
    print("Creating temporary AWS SSO OIDC application")
    client = sso_oidc_client.register_client(
        clientName='never-gonna-give-you-up',
        clientType='public'
    )
    client_id = client.get('clientId')
    client_secret = client.get('clientSecret')
    return client_id, client_secret


def initiate_device_code_flow(sso_oidc_client, oidc_application, start_url):
    print("Initiating device code flow")
    authz = sso_oidc_client.start_device_authorization(
        clientId=oidc_application[0],
        clientSecret=oidc_application[1],
        startUrl=start_url
    )

    url = authz.get('verificationUriComplete')
    deviceCode = authz.get('deviceCode')
    return url, deviceCode


def create_device_code_url(sso_oidc_client, start_url):
    oidc_application = create_oidc_application(sso_oidc_client)
    url, device_code = initiate_device_code_flow(
        sso_oidc_client, oidc_application, start_url)
    return url, device_code, oidc_application


def await_user_prompt_validation(sso_oidc_client, oidc_application, device_code, sleep_interval=3):
    sso_token = ''
    print("Waiting indefinitely for user to validate the AWS SSO prompt...")
    while True:
        time.sleep(sleep_interval)
        try:
            token_response = sso_oidc_client.create_token(
                clientId=oidc_application[0],
                clientSecret=oidc_application[1],
                grantType="urn:ietf:params:oauth:grant-type:device_code",
                deviceCode=device_code
            )
            aws_sso_token = token_response.get('accessToken')
            return aws_sso_token
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != 'AuthorizationPendingException':
                raise e


def retrieve_aws_sso_token(args):


    sso_oidc_client = boto3.client('sso-oidc', region_name=sso_config['region'])
    url, device_code, oidc_application = create_device_code_url(sso_oidc_client, sso_config['url'])

    print(f"Device code URL: {url}")
    aws_sso_token = await_user_prompt_validation(
        sso_oidc_client, oidc_application, device_code)
    print("Successfully retrieved AWS SSO token!")

    return aws_sso_token


def retrieve_aws_accounts(sso_client, aws_sso_token):
    aws_accounts_response = sso_client.list_accounts(
        accessToken=aws_sso_token,
        maxResults=100
    )
    if len(aws_accounts_response.get('accountList', [])) == 0:
        raise RuntimeError('Unable to retrieve AWS SSO account list\n')
    return aws_accounts_response.get('accountList')


def retrieve_roles_in_account(sso_client, aws_sso_token, account):
    account_id = account.get('accountId')
    roles_response = sso_client.list_account_roles(
        accessToken=aws_sso_token, accountId=account_id)
    if len(roles_response.get('roleList', [])) == 0:
        raise RuntimeError(
            f'Unable to retrieve roles in account {account_id}\n')

    return [role.get('roleName') for role in roles_response.get('roleList')]


def retrieve_credentials(sso_client, aws_sso_token, account_id, role_name):
    sts_creds = sso_client.get_role_credentials(
        accessToken=aws_sso_token,
        roleName=role_name,
        accountId=account_id
    )
    if 'roleCredentials' not in sts_creds:
        raise RuntimeError('Unable to retrieve STS credentials')
    credentials = sts_creds.get('roleCredentials')
    if 'accessKeyId' not in credentials:
        raise RuntimeError('Unable to retrieve STS credentials')

    return credentials.get('accessKeyId'), credentials.get('secretAccessKey'), credentials.get('sessionToken')
