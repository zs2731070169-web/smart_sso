# smart_sso

最小化 SSO 服务:RS256 签发 JWT + JWKS 公钥端点。供 `smart_talkflow` 的 `resolve_operator_from_sso` 消费(身份的「颁发替身」)。

> 生产应接企业身份源(LDAP / AD / OIDC);本服务仅用于联调与端到端验证。

## 环境要求

- Python ≥ 3.12(本地 `.python-version` 锁 3.13)
- [uv](https://docs.astral.sh/uv/) 包管理

## 端点

- `POST /login` — `{username, password}` → `{access_token, token_type}`(JWT,RS256;claims:`sub`=userId / `name` / `tenant_id` / `roles` / `iss` / `iat` / `exp`)。
- `GET /.well-known/jwks.json` — 签名公钥(JWKS),消费方拉取验签。

## 快速开始

```bash
cp .env.example .env            # 按需修改配置
uv sync                         # 安装依赖

# 启动(二选一):
uv run python -m app.main                          # 直跑,监听 127.0.0.1:${SSO_PORT}
uv run uvicorn app.main:app --reload --port 48081  # 开发热重载
```

首次启动自动在 `keys/private.pem` 生成 RSA 2048 私钥(已 gitignore),之后复用——故 JWKS / `kid` 稳定。

## 配置

环境变量以 `SSO_` 为前缀(见 `.env.example` / `app/config.py`),优先级:环境变量 > `.env` > 默认值。

| 变量 | 默认 | 说明 |
|------|------|------|
| `SSO_ISSUER` | `smart_sso` | JWT issuer,**须与消费方 `SSO_ISSUER` 一致** |
| `SSO_PORT` | `48081` | 监听端口 |
| `SSO_TOKEN_TTL` | `7200` | JWT 有效期(秒,默认 2 小时) |
| `SSO_IDENTITY_SOURCE` | `stub` | 身份源:`stub`(联调)/ `yudao`(委托 yudao-office) |
| `SSO_YUDAO_BASE_URL` | _空_ | yudao-office 地址(仅 `yudao` 模式) |
| `SSO_DEFAULT_TENANT_ID` | `1` | 默认租户(yudao `tenant-id` 头) |
| `SSO_PRIVATE_KEY_PATH` | _项目根 `keys/private.pem`_ | RSA 私钥路径(建议留空走默认,避免相对路径在不同启动目录下生成多余私钥) |

## 身份源

`SSO_IDENTITY_SOURCE` 选择 `/login` 的认证后端:

- **`stub`**(默认):硬编码用户库 `app/users.py`,联调用。
- **`yudao`**:委托 yudao-office(`/admin-api/system/login` 取 accessToken/userId → `/admin-api/system/auth/get-permission-info` 取 roles),需配 `SSO_YUDAO_BASE_URL`。

## 内置用户(仅 `stub` 模式)

| username | password  | userId | roles     |
|----------|-----------|--------|-----------|
| wangwu   | wangwu123 | 9527   | employee  |
| lili     | lili123   | 9528   | hr_admin  |

## 联调示例

```bash
# 1. 登录拿 token
TOKEN=$(curl -s -XPOST localhost:48081/login -H 'Content-Type: application/json' \
  -d '{"username":"wangwu","password":"wangwu123"}' | jq -r .access_token)

# 2. 看公钥
curl -s localhost:48081/.well-known/jwks.json | jq
```

## 消费方接入(smart_talkflow)

JWT 自包含、无状态——消费方拉公钥本地验签,**不回调** smart_sso。需配置:

- `SSO_JWKS_URI=http://<host>:48081/.well-known/jwks.json`
- `SSO_ISSUER=smart_sso`(与本服务 `SSO_ISSUER` 一致)

消费入口为 `resolve_operator_from_sso`。

## 开源许可

[MIT License](LICENSE),Copyright (c) 2026 Hariku。本服务仅供联调与端到端验证,生产环境请接企业身份源(LDAP / AD / OIDC)。
