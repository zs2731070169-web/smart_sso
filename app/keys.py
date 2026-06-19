"""RSA 密钥加载/生成 + JWKS 导出。

启动时若 ``private_key_path`` 不存在则生成 RSA 2048 并保存(之后重启复用,保证
JWKS 稳定);公钥导出为 JWKS(``kid`` 取公钥模数指纹),供 ``/.well-known/jwks.json``
暴露给 smart_talkflow 验签。
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from app.config import settings


def _load_or_create_private_key(path: str) -> RSAPrivateKey:
    """私钥不存在则生成 RSA 2048(PKCS8/PEM 无加密)保存;存在则加载。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # 加载私钥文件
    if path.exists():
        loaded = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(loaded, RSAPrivateKey):
            raise TypeError(f"{path} 不是 RSA 私钥")
        return loaded

    # 如果没有私钥就重新生成并保存到路径下
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return key


def _int_to_bytes(value: int) -> bytes:
    """大整数 → 最小大端字节串(JWK kid 与 n/e 编码共用)。"""
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def _kid(public_numbers) -> str:
    """公钥模数 n 的 SHA256 前 12 字符作 kid(密钥不变则稳定)。"""
    return "sso-" + hashlib.sha256(_int_to_bytes(public_numbers.n)).hexdigest()[:12]


def _b64url_uint(value: int) -> str:
    """大整数 → base64url(无填充),RFC 7518 用于 JWK 的 n/e 字段。"""
    return base64.urlsafe_b64encode(_int_to_bytes(value)).decode().rstrip("=")


class KeyMaterial:
    """RSA 密钥材料(模块级单例)。"""

    def __init__(self) -> None:
        self._private: RSAPrivateKey = _load_or_create_private_key(settings.private_key_path)  # 私钥
        self._public: RSAPublicKey = self._private.public_key()  # 公钥
        self.kid = _kid(self._public.public_numbers())  # 钥匙id

    @property
    def private_pem(self) -> bytes:
        """私钥 PEM(签发 JWT 用)。"""
        return self._private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    @property
    def jwks(self) -> dict:
        """JWKS(RSA 公钥 JWK,含 kid/use/alg),供 /.well-known/jwks.json。"""
        numbers = self._public.public_numbers()
        return {"keys": [{
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": self.kid,
            "n": _b64url_uint(numbers.n),
            "e": _b64url_uint(numbers.e),
        }]}


key_material = KeyMaterial()
