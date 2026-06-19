"""smart_sso 配置(环境变量,``SSO_`` 前缀)。

基于 pydantic-settings:从环境变量 / ``.env`` 读取(优先级:环境变量 > ``.env`` > 默认值),
字段带类型校验与默认值。
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_PATH = Path(__file__).parents[1]


class Settings(BaseSettings):
    """从环境变量(``SSO_`` 前缀)/ ``.env`` 读取的配置,缺失走默认值。"""

    model_config = SettingsConfigDict(
        env_prefix="SSO_",
        env_file=ROOT_PATH / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    issuer: str = "smart_sso"  # JWT issuer claim(消费方 smart_talkflow 的 SSO_ISSUER 须与此一致)

    private_key_path: str = str(ROOT_PATH / "keys" / "private.pem")  # RSA 私钥路径(默认指向项目根 keys/private.pem)

    token_ttl: int = 7200  # JWT 有效期(秒)

    port: int = 48081  # 监听端口

    # 身份源:stub(硬编码联调,见 app/users.py)/ yudao(委托 yudao-office 认证)
    identity_source: str = "stub"

    yudao_base_url: str = ""  # yudao-office 地址(仅 identity_source=yudao 时用)

    default_tenant_id: str = "1"  # 默认租户(yudao tenant-id 头)


settings = Settings()
