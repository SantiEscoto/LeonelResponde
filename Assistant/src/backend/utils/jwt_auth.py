"""
Sistema de Autenticación JWT
=============================

Módulo para autenticación basada en JSON Web Tokens (JWT) con:
- Generación y validación de tokens JWT
- Refresh tokens para sesiones de larga duración
- Roles y permisos de usuario
- Blacklist de tokens revocados
- Integración con FastAPI
- Seguridad: tokens firmados, expiración, validación

Autor: Assistant
Fecha: 2025
"""

import secrets
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import base64

try:
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("JWT_AUTH")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("JWT_AUTH")


class UserRole(str, Enum):
    """Roles de usuario"""
    GUEST = "guest"
    USER = "user"
    PREMIUM = "premium"
    ADMIN = "admin"
    SYSTEM = "system"


class Permission(str, Enum):
    """Permisos del sistema"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    MANAGE_USERS = "manage_users"
    MANAGE_RATE_LIMITS = "manage_rate_limits"


# Mapeo de roles a permisos
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.GUEST: [Permission.READ],
    UserRole.USER: [Permission.READ, Permission.WRITE],
    UserRole.PREMIUM: [Permission.READ, Permission.WRITE, Permission.DELETE],
    UserRole.ADMIN: [
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.ADMIN,
        Permission.MANAGE_USERS,
        Permission.MANAGE_RATE_LIMITS
    ],
    UserRole.SYSTEM: list(Permission),  # Todos los permisos
}


@dataclass
class TokenPayload:
    """Payload de un token JWT"""
    user_id: str
    username: str
    role: UserRole
    permissions: List[Permission]
    issued_at: float
    expires_at: float
    token_type: str = "access"  # "access" o "refresh"
    jti: str = field(default_factory=lambda: secrets.token_hex(16))  # JWT ID único

    def to_dict(self) -> Dict:
        """Convierte a diccionario"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "permissions": [p.value for p in self.permissions],
            "iat": self.issued_at,
            "exp": self.expires_at,
            "type": self.token_type,
            "jti": self.jti
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TokenPayload":
        """Crea desde diccionario"""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            role=UserRole(data["role"]),
            permissions=[Permission(p) for p in data["permissions"]],
            issued_at=data["iat"],
            expires_at=data["exp"],
            token_type=data.get("type", "access"),
            jti=data.get("jti", secrets.token_hex(16))
        )

    def is_expired(self) -> bool:
        """Verifica si el token ha expirado"""
        return time.time() > self.expires_at

    def has_permission(self, permission: Permission) -> bool:
        """Verifica si tiene un permiso específico"""
        return permission in self.permissions


@dataclass
class User:
    """Usuario del sistema"""
    user_id: str
    username: str
    password_hash: str
    role: UserRole
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    is_active: bool = True
    metadata: Dict = field(default_factory=dict)

    def get_permissions(self) -> List[Permission]:
        """Obtiene los permisos del usuario"""
        return ROLE_PERMISSIONS.get(self.role, [])

    def has_permission(self, permission: Permission) -> bool:
        """Verifica si tiene un permiso específico"""
        return permission in self.get_permissions()

    def to_dict(self) -> Dict:
        """Convierte a diccionario (sin password)"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "permissions": [p.value for p in self.get_permissions()],
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active": self.is_active,
            "metadata": self.metadata
        }


class JWTAuthManager:
    """
    Gestor de autenticación JWT

    Maneja la creación, validación y revocación de tokens JWT.
    Implementa autenticación basada en tokens con refresh tokens.
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        algorithm: str = "HS256"
    ):
        """
        Inicializa el gestor de autenticación

        Args:
            secret_key: Clave secreta para firmar tokens (se genera si no se proporciona)
            access_token_expire_minutes: Minutos de validez para access tokens
            refresh_token_expire_days: Días de validez para refresh tokens
            algorithm: Algoritmo de firma (solo HS256 soportado en esta versión)
        """
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.algorithm = algorithm

        # Almacenamiento de usuarios (en producción, usar base de datos)
        self.users: Dict[str, User] = {}

        # Blacklist de tokens revocados (JTI)
        self.revoked_tokens: Set[str] = set()

        # Refresh tokens activos
        self.active_refresh_tokens: Dict[str, str] = {}  # jti -> user_id

        logger.info(
            f"🔐 JWT Auth Manager inicializado "
            f"(access: {access_token_expire_minutes}m, refresh: {refresh_token_expire_days}d)"
        )

        # Crear usuario admin por defecto
        self._create_default_admin()

    def _create_default_admin(self) -> None:
        """Crea un usuario admin por defecto"""
        admin_id = "admin_" + secrets.token_hex(8)
        admin_password = secrets.token_urlsafe(16)

        admin = User(
            user_id=admin_id,
            username="admin",
            password_hash=self._hash_password(admin_password),
            role=UserRole.ADMIN,
            metadata={"default_user": True}
        )

        self.users[admin_id] = admin

        logger.info(f"👤 Usuario admin creado: username='admin', password='{admin_password}'")
        logger.warning("⚠️ CAMBIAR CONTRASEÑA DEL ADMIN EN PRODUCCIÓN")

    def _hash_password(self, password: str) -> str:
        """
        Hash de contraseña usando PBKDF2-HMAC-SHA256

        Args:
            password: Contraseña en texto plano

        Returns:
            Hash de la contraseña
        """
        # Usar salt fijo por simplicidad (en producción, usar salt aleatorio por usuario)
        salt = b"leonel_responde_salt_2025"
        iterations = 100000

        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations
        )

        return base64.b64encode(hash_bytes).decode('utf-8')

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verifica una contraseña contra su hash

        Args:
            password: Contraseña en texto plano
            password_hash: Hash de la contraseña

        Returns:
            True si coinciden
        """
        computed_hash = self._hash_password(password)
        return hmac.compare_digest(computed_hash, password_hash)

    def _encode_jwt(self, payload: Dict) -> str:
        """
        Codifica un payload como JWT

        Args:
            payload: Diccionario con los datos del token

        Returns:
            Token JWT codificado
        """
        # Header
        header = {
            "alg": self.algorithm,
            "typ": "JWT"
        }

        # Codificar header y payload en base64
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode('utf-8')
        ).decode('utf-8').rstrip('=')

        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode('utf-8')
        ).decode('utf-8').rstrip('=')

        # Crear firma
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()

        signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

        # JWT = header.payload.signature
        return f"{header_b64}.{payload_b64}.{signature_b64}"

    def _decode_jwt(self, token: str) -> Optional[Dict]:
        """
        Decodifica y valida un JWT

        Args:
            token: Token JWT

        Returns:
            Payload decodificado o None si es inválido
        """
        try:
            # Separar partes del token
            parts = token.split('.')
            if len(parts) != 3:
                logger.warning("Token JWT malformado (partes incorrectas)")
                return None

            header_b64, payload_b64, signature_b64 = parts

            # Verificar firma
            message = f"{header_b64}.{payload_b64}"
            expected_signature = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).digest()

            # Decodificar firma recibida
            # Agregar padding si es necesario
            signature_b64_padded = signature_b64 + '=' * (4 - len(signature_b64) % 4)
            received_signature = base64.urlsafe_b64decode(signature_b64_padded.encode('utf-8'))

            # Verificar firma con comparación segura
            if not hmac.compare_digest(expected_signature, received_signature):
                logger.warning("Token JWT con firma inválida")
                return None

            # Decodificar payload
            payload_b64_padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64_padded.encode('utf-8'))
            payload = json.loads(payload_bytes.decode('utf-8'))

            return payload

        except Exception as e:
            logger.error(f"Error decodificando JWT: {e}")
            return None

    def create_user(
        self,
        username: str,
        password: str,
        role: UserRole = UserRole.USER,
        metadata: Optional[Dict] = None
    ) -> User:
        """
        Crea un nuevo usuario

        Args:
            username: Nombre de usuario
            password: Contraseña en texto plano
            role: Rol del usuario
            metadata: Metadatos adicionales

        Returns:
            Usuario creado

        Raises:
            ValueError: Si el usuario ya existe
        """
        # Verificar si el usuario ya existe
        for user in self.users.values():
            if user.username == username:
                raise ValueError(f"Usuario '{username}' ya existe")

        # Crear usuario
        user_id = f"user_{secrets.token_hex(8)}"
        user = User(
            user_id=user_id,
            username=username,
            password_hash=self._hash_password(password),
            role=role,
            metadata=metadata or {}
        )

        self.users[user_id] = user

        logger.info(f"👤 Usuario creado: {username} (role: {role.value})")

        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Autentica un usuario

        Args:
            username: Nombre de usuario
            password: Contraseña

        Returns:
            Usuario autenticado o None si falla
        """
        # Buscar usuario por username
        user = None
        for u in self.users.values():
            if u.username == username:
                user = u
                break

        if not user:
            logger.warning(f"❌ Intento de login fallido: usuario '{username}' no encontrado")
            return None

        # Verificar contraseña
        if not self._verify_password(password, user.password_hash):
            logger.warning(f"❌ Intento de login fallido: contraseña incorrecta para '{username}'")
            return None

        # Verificar si el usuario está activo
        if not user.is_active:
            logger.warning(f"❌ Intento de login fallido: usuario '{username}' inactivo")
            return None

        # Actualizar último login
        user.last_login = time.time()

        logger.info(f"✅ Usuario autenticado: {username}")

        return user

    def create_access_token(self, user: User) -> str:
        """
        Crea un access token para un usuario

        Args:
            user: Usuario

        Returns:
            Access token JWT
        """
        now = time.time()
        expires_at = now + (self.access_token_expire_minutes * 60)

        payload = TokenPayload(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            permissions=user.get_permissions(),
            issued_at=now,
            expires_at=expires_at,
            token_type="access"
        )

        token = self._encode_jwt(payload.to_dict())

        logger.debug(f"🎫 Access token creado para {user.username} (expira en {self.access_token_expire_minutes}m)")

        return token

    def create_refresh_token(self, user: User) -> str:
        """
        Crea un refresh token para un usuario

        Args:
            user: Usuario

        Returns:
            Refresh token JWT
        """
        now = time.time()
        expires_at = now + (self.refresh_token_expire_days * 24 * 60 * 60)

        payload = TokenPayload(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            permissions=user.get_permissions(),
            issued_at=now,
            expires_at=expires_at,
            token_type="refresh"
        )

        token = self._encode_jwt(payload.to_dict())

        # Guardar en tokens activos
        self.active_refresh_tokens[payload.jti] = user.user_id

        logger.debug(f"🎫 Refresh token creado para {user.username} (expira en {self.refresh_token_expire_days}d)")

        return token

    def verify_token(self, token: str) -> Optional[TokenPayload]:
        """
        Verifica y decodifica un token

        Args:
            token: Token JWT

        Returns:
            Payload del token o None si es inválido
        """
        # Decodificar token
        payload_dict = self._decode_jwt(token)
        if not payload_dict:
            return None

        try:
            payload = TokenPayload.from_dict(payload_dict)

            # Verificar expiración
            if payload.is_expired():
                logger.warning(f"Token expirado para usuario {payload.username}")
                return None

            # Verificar si está revocado
            if payload.jti in self.revoked_tokens:
                logger.warning(f"Token revocado para usuario {payload.username}")
                return None

            return payload

        except Exception as e:
            logger.error(f"Error verificando token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        Genera un nuevo access token usando un refresh token

        Args:
            refresh_token: Refresh token válido

        Returns:
            Tupla (nuevo_access_token, nuevo_refresh_token) o None si falla
        """
        # Verificar refresh token
        payload = self.verify_token(refresh_token)
        if not payload:
            return None

        # Verificar que es un refresh token
        if payload.token_type != "refresh":
            logger.warning("Token no es un refresh token")
            return None

        # Verificar que está en tokens activos
        if payload.jti not in self.active_refresh_tokens:
            logger.warning("Refresh token no está activo")
            return None

        # Obtener usuario
        user = self.users.get(payload.user_id)
        if not user or not user.is_active:
            logger.warning(f"Usuario {payload.user_id} no encontrado o inactivo")
            return None

        # Revocar refresh token anterior
        self.revoke_token(payload.jti)

        # Crear nuevos tokens
        new_access_token = self.create_access_token(user)
        new_refresh_token = self.create_refresh_token(user)

        logger.info(f"🔄 Tokens renovados para usuario {user.username}")

        return (new_access_token, new_refresh_token)

    def revoke_token(self, jti: str) -> None:
        """
        Revoca un token por su JTI

        Args:
            jti: JWT ID del token
        """
        self.revoked_tokens.add(jti)

        # Remover de refresh tokens activos si existe
        if jti in self.active_refresh_tokens:
            del self.active_refresh_tokens[jti]

        logger.info(f"🚫 Token revocado: {jti}")

    def logout(self, token: str) -> bool:
        """
        Cierra sesión revocando el token

        Args:
            token: Token a revocar

        Returns:
            True si se revocó correctamente
        """
        payload = self.verify_token(token)
        if not payload:
            return False

        self.revoke_token(payload.jti)

        logger.info(f"👋 Logout de usuario {payload.username}")

        return True

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Obtiene un usuario por ID"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Obtiene un usuario por username"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def list_users(self) -> List[Dict]:
        """Lista todos los usuarios (sin contraseñas)"""
        return [user.to_dict() for user in self.users.values()]

    def cleanup_expired_tokens(self) -> int:
        """
        Limpia tokens expirados de la blacklist

        Returns:
            Número de tokens limpiados
        """
        # En una implementación real, deberíamos almacenar timestamp de revocación
        # Por ahora, simplemente reportamos el tamaño
        count = len(self.revoked_tokens)
        logger.info(f"🧹 Tokens revocados en blacklist: {count}")
        return count


# Instancia global del auth manager (lazy initialization)
_global_auth_manager: Optional[JWTAuthManager] = None


def get_auth_manager(
    secret_key: Optional[str] = None,
    access_token_expire_minutes: int = 30,
    refresh_token_expire_days: int = 7
) -> JWTAuthManager:
    """
    Obtiene la instancia global del auth manager (singleton)

    Args:
        secret_key: Clave secreta (solo primera inicialización)
        access_token_expire_minutes: Minutos de expiración (solo primera inicialización)
        refresh_token_expire_days: Días de expiración (solo primera inicialización)

    Returns:
        JWTAuthManager: Instancia global
    """
    global _global_auth_manager

    if _global_auth_manager is None:
        _global_auth_manager = JWTAuthManager(
            secret_key=secret_key,
            access_token_expire_minutes=access_token_expire_minutes,
            refresh_token_expire_days=refresh_token_expire_days
        )

    return _global_auth_manager
