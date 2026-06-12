from typing import Final, Dict, List


class Securities:
    PUBLIC_GET_ENDPOINT: Final[List[str]] = [
        "/",
    ]

    PUBLIC_POST_ENDPOINT: Final[List[str]] = [
        "/auth/login",
        "/auth/register",
        "/auth/logout",
    ]

    PUBLIC_PUT_ENDPOINT: Final[List[str]] = [

    ]

    PUBLIC_DELETE_ENDPOINT: Final[List[str]] = [

    ]

    SECURITY_MATCHERS: Final[Dict[str, List[str]]] = {
        "GET": PUBLIC_GET_ENDPOINT,
        "POST": PUBLIC_POST_ENDPOINT,
        "PUT": PUBLIC_PUT_ENDPOINT,
        "DELETE": PUBLIC_DELETE_ENDPOINT,
    }