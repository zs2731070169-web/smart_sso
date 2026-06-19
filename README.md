# smart_sso

最小化 SSO 服务:RS256 签发 JWT + 暴露 JWKS 公钥端点。供 `smart_talkflow` 的 `resolve_operator_from_sso` 消费(身份的「颁发替身」)。

> 生产应接企业身份源(LDAP / AD / OIDC);本服务仅用于联调与端到端验证。

## 端点

- `POST /login` — `{username, password}` → `{access_token, token_type}`(JWT,RS256;claims:`sub`=userId / `name` / `tenant_id` / `roles` / `iss` / `iat` / `exp`)。
- `GET /.well-known/jwks.json` — 签名公钥(JWKS),消费方拉取验签。

## 内置用户(联调)

| username | password  | userId | roles     |
|----------|-----------|--------|-----------|
| wangwu   | wangwu123 | 9527   | employee  |
| lili     | lili123   | 9528   | hr_admin  |

## 运行

```bash
cp .env.example .env            # 按需修改
uv run uvicorn app.main:app --port 48081
```

首次启动自动在 `keys/private.pem` 生成 RSA 私钥(已 gitignore),之后复用——故 JWKS / kid 稳定。

## 联调示例

```bash
# 1. 登录拿 token
TOKEN=$(curl -s -XPOST localhost:48081/login -H 'Content-Type: application/json' \
  -d '{"username":"wangwu","password":"wangwu123"}' | jq -r .access_token)

# 2. 看公钥
curl -s localhost:48081/.well-known/jwks.json | jq
```

消费方(smart_talkflow)需配置:`SSO_ISSUER=smart_sso`、`SSO_JWKS_URI=http://localhost:48081/.well-known/jwks.json`。
