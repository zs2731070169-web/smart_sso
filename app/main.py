"""smart_sso:最小化 SSO 服务(RS256 签发 JWT + JWKS 公钥端点)。

供 smart_talkflow 的 ``resolve_operator_from_sso`` 消费:

- ``POST /login``:{username, password} → JWT(RS256,claims:sub/tenant_id/roles/iss/exp)。
- ``GET /.well-known/jwks.json``:签名公钥(JWKS),供下游验签拉取。
"""
from __future__ import annotations

import time

import jwt
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.identity import build_identity_source
from app.keys import key_material

app = FastAPI(title="smart_sso", description="最小化 SSO:JWT 签发 + JWKS")

# 身份源(按 SSO_IDENTITY_SOURCE 选择:stub 测试数据 / yudao 真实委托 yudao-office)
_identity_source = build_identity_source()


class LoginRequest(BaseModel):
    username: str
    password: str


@app.get("/.well-known/jwks.json")
def jwks() -> dict:
    """签名公钥(JWKS),供 smart_talkflow 验签拉取。"""
    return key_material.jwks


@app.post("/login")
async def login(req: LoginRequest) -> dict:
    """在SSO端点, 根据用户名和密码登录至数据源, 从数据源获取用户信息, 并构建为令牌返回"""
    # 获取用户信息源
    identity = await _identity_source.authenticate(
        req.username, req.password, settings.default_tenant_id
    )
    if identity is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    now = int(time.time())

    # 构建令牌
    token = jwt.encode(
        payload={
            "sub": identity.user_id,
            "name": identity.name,
            "tenant_id": identity.tenant_id,
            "roles": identity.roles,
            "iss": settings.issuer,
            "iat": now,
            "exp": now + settings.token_ttl,
        },
        key=key_material.private_pem,
        algorithm="RS256",
        headers={"kid": key_material.kid},
    )

    return {"access_token": token, "token_type": "bearer"}


if __name__ == "__main__":
    # 本地直跑:python -m app.main(或 python app/main.py)
    # 需要热重载改用 CLI:uvicorn app.main:app --reload --port 48081
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=settings.port)
