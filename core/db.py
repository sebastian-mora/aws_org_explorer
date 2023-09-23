from py2neo import Graph


class Db:
    def __init__(self, uri, user, password) -> None:
        self.graph = Graph(uri, auth=(user, password))

    def ping(self):
        try:
            self.graph.run("Match () Return 1 Limit 1")
        except Exception as e:
            return e

    def add_aws_account(self, account):
        account = _convert_dict_to_string(account)
        self.graph.run(f"MERGE (a:Account {account})  ")

    def add_aws_role(self, role):
        accountId = _get_account_id(role["Arn"])

        tx = f"""
        MATCH (account:Account {{ accountId: '{accountId}' }})
        MERGE (account)-[:OWNS]-(r:Role {{RoleName: '{role['RoleName']}', accountId: '{accountId}', Arn: '{role['Arn']}', RoleId: '{role['RoleId']}'}})
        """
        self.graph.run(tx)
        self.add_role_trusts(role)

    def add_aws_user(self, user):
        accountId = _get_account_id(user["Arn"])

        tx = f"""
        MATCH (account:Account {{ accountId: '{accountId}' }})
        MERGE (account) -[:OWNS]->(u:User {{UserName: '{user['UserName']}', accountId: '{accountId}', Arn: '{user['Arn']}'}})
        """

        self.graph.run(tx)

    def __create_service_trust(self, role, trust):
        tx = f"""
        MATCH (r) WHERE r.Arn="{role['Arn']}"
        MERGE (s:Service {{Service: '{trust}'}})
        MERGE (r) <-[:ASSUMES] -(s)
        """
        self.graph.run(tx)

    def __create_role_trust(self, role, trust):
        # If the trust using AROA (Role Iden format)
        if trust[:4] == "AROA":
            tx = f"""
            MATCH (r:Role {{Arn: '{role['Arn']}'}}), (n:Role {{RoleId:'{trust}'}})
            MERGE (r) <-[:ASSUMES] - (n)
        """

        # If the trust specifices the root account, map to account node
        elif trust.split(":")[5] == "root":
            tx = f"""
            MATCH (r:Role {{Arn: '{role['Arn']}'}}), (a:Account {{accountId: '{_get_account_id(trust)}'}})
            MERGE (r) <-[:ASSUMES] -(a)
        """

        else:
            tx = f"""
            MATCH (r) WHERE r.Arn="{role['Arn']}" 
            MATCH (n) WHERE n.Arn="{trust}"
            MERGE (r) <-[:ASSUMES] - (n)
        """

        self.graph.run(tx)

    def add_role_trusts(self, role):
        for statement in role["AssumeRolePolicyDocument"]["Statement"]:
            for key in statement["Principal"].keys():
                if key != "Federated":
                    # This could be either a string or a list of strings
                    trusts = statement["Principal"][key]

                    # If a string create a list
                    if isinstance(trusts, str):
                        trusts = [trusts]

                    try:
                        for trust in trusts:
                            # If the role is trusting a service "lambda.aws.com"
                            if key == "Service":
                                self.__create_service_trust(role, trust)

                            else:
                                self.__create_role_trust(role, trust)

                    except Exception as e:
                        print(f"FAILED to create trust: {role['Arn']}, {key}, {trust}")
                        print(e)


def _convert_dict_to_string(o):
    formated = "{"

    for k in o.keys():
        formated += f"{k}: '{o[k]}',"

    return formated[:-1] + "}"


def _get_account_id(arn):
    return arn.split(":")[4]


def _get_service_name(service):
    return service.split(".")[0]
