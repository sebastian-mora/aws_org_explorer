
def retreive_roles(client):

    res = client.list_roles()
    roles = res['Roles']

    while res.get("Marker"):
        res = client.list_roles(Marker=res.get("Marker"))
        roles.extend(res['Roles'])

    return roles

def retreive_users(client):

    res = client.list_users()
    users = res['Users']

    while res.get("Marker"):
        res = client.list_roles(Marker=res.get("Marker"))
        users.extend(res['Users'])

    return users


