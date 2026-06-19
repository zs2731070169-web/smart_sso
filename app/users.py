"""硬编码用户库(最小化,仅联调用)。

⚠️ 生产应接企业身份源(LDAP / AD / OIDC),不在本服务自建用户体系——
smart_sso 只是身份的「颁发替身」,真实身份归属企业 IdP。
"""
from __future__ import annotations

# username -> 用户信息(password 仅联调用)
USERS: dict[str, dict] = {
    "wangwu": {
        "password": "wangwu123",
        "user_id": "9527",
        "name": "王五",
        "tenant_id": "1",
        "roles": ["employee"],
    },
    "lili": {
        "password": "lili123",
        "user_id": "9528",
        "name": "李丽",
        "tenant_id": "1",
        "roles": ["hr_admin"],
    },
}


def find_user(username: str, password: str) -> dict | None:
    """用户名密码校验,命中返回用户信息,否则 None。"""
    user = USERS.get(username)
    if user and user["password"] == password:
        return user
    return None
