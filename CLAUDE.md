# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

smart_sso 是最小化的 SSO「颁发替身」:用 RS256 签发 JWT、暴露 JWKS 公钥端点。它**不是用户体系的真相源**——真实身份(账号/密码/角色)归属企业 IdP,本服务只负责认证后颁发令牌,供下游业务方(smart_talkflow)拉公钥本地验签。生产应接 LDAP/AD/OIDC,当前实现仅用于联调与端到端验证。

## 常用命令

- 安装/同步依赖:`uv sync`
- 启动服务(两种等价方式):
  - `uv run python -m app.main` —— 直跑,监听 `127.0.0.1:{SSO_PORT}`(默认 48081)
  - `uv run uvicorn app.main:app --reload --port 48081` —— 开发热重载
- 初始化配置:`cp .env.example .env`(环境变量以 `SSO_` 为前缀,见 `app/config.py`)
- 联调登录:
  ```bash
  curl -XPOST localhost:48081/login -H 'Content-Type: application/json' \
    -d '{"username":"wangwu","password":"wangwu123"}'
  ```

> 当前**未配置 lint/测试工具,无测试套件**(`pyproject.toml` 无 dev 依赖、无 `[tool.*]` 段)。不要假设 `pytest`/`ruff` 可用——需要时再自行加入 `[dependency-groups].dev`。

## 架构

### 两条端点的职责分离(app/main.py)
- `POST /login`:委托身份源认证用户名密码 → 签发 RS256 JWT。
- `GET /.well-known/jwks.json`:暴露验签公钥。

JWT 是**自包含、无状态**的:下游拉公钥本地验签,**不回调 smart_sso**。这是 SSO 的核心——登录集中、验签分散、不共享 session。新增「用 token 换用户信息」的 `/me` 类端点通常无必要(claims 已含身份),除非要放 JWT 装不下的额外字段。

### 身份源可插拔(app/identity.py)
`IdentitySource` 抽象 + `build_identity_source()` 工厂,按 `SSO_IDENTITY_SOURCE` 选实现:
- `stub`:硬编码用户库 `app/users.py`(联调,内置 wangwu/lili)。
- `yudao`:委托 yudao-office(`/admin-api/system/login` 取 accessToken/userId → `/admin-api/system/auth/get-permission-info` 取 roles;任一步失败返回 `None`)。需配 `SSO_YUDAO_BASE_URL`。

新增身份源:实现 `IdentitySource.authenticate` 并在 `build_identity_source()` 注册。

### 密钥生命周期(app/keys.py)
启动时加载 `keys/private.pem`;不存在则生成 RSA 2048(PKCS8 无加密)并保存,之后复用——以此**保证 JWKS / kid 稳定**。kid = 公钥模数 n 的 SHA256 前 12 字符,前缀 `sso-`。私钥已 gitignore(`keys/*.pem`),勿提交;运行中删除/换密钥会使所有已签发 token 失效。

### 配置(app/config.py)
pydantic-settings,`SSO_` 前缀,优先级:环境变量 > `.env` > 默认。关键项:
- `SSO_ISSUER`(默认 `smart_sso`):**必须与消费方 smart_talkflow 的 `SSO_ISSUER` 完全一致**,否则下游验签后 `iss` 校验失败。
- `SSO_TOKEN_TTL`(默认 7200 秒 / 2 小时)
- `SSO_PORT`(默认 48081)
- `SSO_IDENTITY_SOURCE`(`stub` / `yudao`)
- `SSO_YUDAO_BASE_URL`、`SSO_DEFAULT_TENANT_ID`(仅 yudao 模式)

### JWT claims
`sub`(userId) / `name` / `tenant_id` / `roles` / `iss` / `iat` / `exp`。

## 跨项目契约(消费方 smart_talkflow)
- 验签方须配 `SSO_JWKS_URI=http://<host>:48081/.well-known/jwks.json`。
- 验签方须配 `SSO_ISSUER=smart_sso`(与本服务 issuer 一致)。
- 消费入口为 smart_talkflow 的 `resolve_operator_from_sso`。

## 约定
- Python `>=3.12`(本地 `.python-version` 锁 3.13);uv 包管理;无打包配置(纯应用,`uv run` 运行,未配 `[build-system]`/`[project.scripts]`)。
- 注释与文档用简体中文。
