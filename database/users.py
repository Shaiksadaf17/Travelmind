from database.supabase_client import supabase


def get_user_by_name(name: str):
    name = name.strip()

    response = (
        supabase
        .table("users")
        .select("*")
        .eq("name", name)
        .execute()
    )

    if response.data:
        return response.data[0]

    return None


def get_or_create_user(name: str):
    user = get_user_by_name(name)

    if user:
        return user

    response = (
        supabase
        .table("users")
        .insert({
            "name": name.strip()
        })
        .execute()
    )

    return response.data[0]