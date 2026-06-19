"""身份源:smart_sso 的 /login 委托企业身份源认证。

抽象 :class:`IdentitySource`,按 ``settings.identity_source`` 选择实现:

- :class:`YudaoIdentitySource`:委托 yudao-office(`/admin-api/system/login` +
  `/admin-api/system/auth/get-permission-info`),user/tenant/role 来自 yudao 建模。
- :class:`StubIdentitySource`:硬编码用户库(见 :mod:`app.users`),无 yudao 时联调用。

⚠️ yudao 的 login / permission-info 请求与响应字段按 yudao-office 实际版本校准;
若登录强校验 captcha,需在 yudao 关闭验证码或走免验通道。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.config import settings
from app.users import USERS


@dataclass(frozen=True)
class UserIdentity:
    """认证通过的用户身份(供签发 JWT)。"""

    user_id: str
    name: str = ""
    tenant_id: str = ""
    roles: list[str] = field(default_factory=list)


class IdentitySource:
    """身份源协议:认证用户名密码,返回身份或 ``None``(认证失败)。"""

    async def authenticate(
            self, username: str, password: str, tenant_id: str
    ) -> UserIdentity | None:
        raise NotImplementedError


class StubIdentitySource(IdentitySource):
    """联调替身:硬编码用户库。"""

    async def authenticate(
            self, username: str, password: str, tenant_id: str
    ) -> UserIdentity | None:
        user = USERS.get(username)
        if not user or user["password"] != password:
            return None
        return UserIdentity(
            user_id=user["user_id"],
            name=user["name"],
            tenant_id=user.get("tenant_id") or tenant_id,
            roles=list(user.get("roles", [])),
        )


class YudaoIdentitySource(IdentitySource):
    """委托 yudao-office 认证。

    流程:
    1. ``POST /admin-api/system/login``(body {username,password},头 ``tenant-id``)
       → 取 ``accessToken`` + ``userId``(yudao CommonResult code==0 视为成功);
    2. ``GET /admin-api/system/auth/get-permission-info``(头 Authorization: Bearer)
       → 取 roles。

    任一步失败(非 200 / code!=0 / 字段缺失 / 网络)→ ``None``。
    """

    def __init__(self, yudao_base_url: str) -> None:
        self._base_url = (yudao_base_url or "").rstrip("/")

    async def authenticate(
            self, username: str, password: str, tenant_id: str
    ) -> UserIdentity | None:
        import httpx  # 延迟导入:stub 模式不强依赖 httpx

        tenant = tenant_id or "1"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self._base_url}/admin-api/system/login",
                    json={"username": username, "password": password},
                    headers={"tenant-id": tenant},
                )
                login_data = resp.json() if resp.status_code == 200 else {}
                if login_data.get("code") != 0:
                    return None
                data = login_data.get("data") or {}
                access_token = data.get("accessToken")
                user_id = str(data.get("userId") or "")
                if not access_token or not user_id:
                    return None

                perm = await client.get(
                    f"{self._base_url}/admin-api/system/auth/get-permission-info",
                    headers={"Authorization": f"Bearer {access_token}", "tenant-id": tenant},
                )
                roles: list[str] = []
                if perm.status_code == 200:
                    perm_data = perm.json()
                    if perm_data.get("code") == 0:
                        roles = [
                            r.get("code") or r.get("name") or str(r)
                            for r in ((perm_data.get("data") or {}).get("roles") or [])
                            if isinstance(r, dict)
                        ]
        except httpx.HTTPError:
            return None

        return UserIdentity(
            user_id=user_id,
            name=username,  # yudao login 响应未必含 name,暂用 username
            tenant_id=tenant,
            roles=roles,
        )


def build_identity_source() -> IdentitySource:
    """按 :attr:`settings.identity_source` 选择身份源(``stub`` / ``yudao``)。"""
    if settings.identity_source == "yudao" and settings.yudao_base_url:
        return YudaoIdentitySource(settings.yudao_base_url)
    return StubIdentitySource()
