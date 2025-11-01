"""
Sistema de Rate Limiting Avanzado
==================================

Módulo para control de tasa de peticiones (rate limiting) con:
- Límites por IP y por endpoint
- Algoritmo Token Bucket para rate limiting flexible
- Configuración por niveles (free, premium, admin)
- Whitelist/blacklist de IPs
- Métricas y logging de rate limiting
- Thread-safe para concurrencia

Autor: Assistant
Fecha: 2025
"""

import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Dict, List, Optional, Set, Tuple

try:
    from src.backend.utils.unified_logger import get_unified_logger
    logger = get_unified_logger("RATE_LIMITER")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("RATE_LIMITER")


class RateLimitTier(str, Enum):
    """Niveles de rate limiting"""
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"
    UNLIMITED = "unlimited"


@dataclass
class RateLimitConfig:
    """Configuración de rate limiting"""
    requests_per_minute: int
    requests_per_hour: int
    burst_size: int = 10  # Máximo de requests en ráfaga
    tier: RateLimitTier = RateLimitTier.FREE

    def __post_init__(self):
        """Validar configuración"""
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute debe ser mayor a 0")
        if self.requests_per_hour <= 0:
            raise ValueError("requests_per_hour debe ser mayor a 0")
        if self.burst_size <= 0:
            raise ValueError("burst_size debe ser mayor a 0")


# Configuraciones predefinidas por tier
TIER_CONFIGS = {
    RateLimitTier.FREE: RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        burst_size=5,
        tier=RateLimitTier.FREE
    ),
    RateLimitTier.PREMIUM: RateLimitConfig(
        requests_per_minute=60,
        requests_per_hour=1000,
        burst_size=20,
        tier=RateLimitTier.PREMIUM
    ),
    RateLimitTier.ADMIN: RateLimitConfig(
        requests_per_minute=300,
        requests_per_hour=10000,
        burst_size=100,
        tier=RateLimitTier.ADMIN
    ),
    RateLimitTier.UNLIMITED: RateLimitConfig(
        requests_per_minute=999999,
        requests_per_hour=999999,
        burst_size=999999,
        tier=RateLimitTier.UNLIMITED
    ),
}


@dataclass
class TokenBucket:
    """
    Implementación del algoritmo Token Bucket para rate limiting

    Permite ráfagas de requests mientras mantiene un promedio a largo plazo.
    """
    capacity: int  # Capacidad máxima del bucket
    refill_rate: float  # Tokens por segundo
    tokens: float = field(init=False)
    last_refill: float = field(init=False)
    lock: Lock = field(default_factory=Lock)

    def __post_init__(self):
        """Inicializar bucket lleno"""
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def _refill(self) -> None:
        """Rellena el bucket basado en el tiempo transcurrido"""
        now = time.time()
        elapsed = now - self.last_refill

        # Calcular tokens a agregar
        tokens_to_add = elapsed * self.refill_rate

        # Rellenar sin exceder capacidad
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Intenta consumir tokens del bucket

        Args:
            tokens: Número de tokens a consumir

        Returns:
            True si se pudieron consumir los tokens, False si no hay suficientes
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False

    def get_available_tokens(self) -> int:
        """Obtiene el número de tokens disponibles"""
        with self.lock:
            self._refill()
            return int(self.tokens)

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Calcula el tiempo de espera para obtener N tokens

        Args:
            tokens: Número de tokens necesarios

        Returns:
            Tiempo de espera en segundos
        """
        with self.lock:
            self._refill()

            if self.tokens >= tokens:
                return 0.0

            tokens_needed = tokens - self.tokens
            return tokens_needed / self.refill_rate


@dataclass
class ClientRateLimit:
    """Rate limit para un cliente específico"""
    client_id: str
    config: RateLimitConfig
    minute_bucket: TokenBucket = field(init=False)
    hour_bucket: TokenBucket = field(init=False)
    request_history: deque = field(default_factory=lambda: deque(maxlen=1000))
    total_requests: int = 0
    blocked_requests: int = 0
    first_seen: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)

    def __post_init__(self):
        """Inicializar buckets"""
        # Bucket de minuto: refill_rate = requests_per_minute / 60
        self.minute_bucket = TokenBucket(
            capacity=self.config.burst_size,
            refill_rate=self.config.requests_per_minute / 60.0
        )

        # Bucket de hora: refill_rate = requests_per_hour / 3600
        self.hour_bucket = TokenBucket(
            capacity=self.config.requests_per_hour,
            refill_rate=self.config.requests_per_hour / 3600.0
        )

    def check_rate_limit(self) -> Tuple[bool, Optional[str]]:
        """
        Verifica si el cliente puede hacer una request

        Returns:
            Tupla (allowed, reason)
            - allowed: True si se permite la request
            - reason: Razón del bloqueo (si allowed=False)
        """
        # Verificar bucket de minuto
        if not self.minute_bucket.consume(1):
            wait_time = self.minute_bucket.get_wait_time(1)
            return False, f"Rate limit per minute exceeded. Retry after {wait_time:.1f}s"

        # Verificar bucket de hora
        if not self.hour_bucket.consume(1):
            wait_time = self.hour_bucket.get_wait_time(1)
            return False, f"Rate limit per hour exceeded. Retry after {wait_time:.1f}s"

        return True, None

    def record_request(self, allowed: bool, endpoint: str = "") -> None:
        """
        Registra una request en el historial

        Args:
            allowed: Si la request fue permitida
            endpoint: Endpoint solicitado
        """
        now = time.time()
        self.total_requests += 1
        if not allowed:
            self.blocked_requests += 1

        self.last_request = now
        self.request_history.append({
            "timestamp": now,
            "allowed": allowed,
            "endpoint": endpoint
        })

    def get_status(self) -> Dict:
        """Obtiene el estado actual del rate limit"""
        return {
            "client_id": self.client_id,
            "tier": self.config.tier.value,
            "limits": {
                "requests_per_minute": self.config.requests_per_minute,
                "requests_per_hour": self.config.requests_per_hour,
                "burst_size": self.config.burst_size
            },
            "available_tokens": {
                "minute": self.minute_bucket.get_available_tokens(),
                "hour": self.hour_bucket.get_available_tokens()
            },
            "statistics": {
                "total_requests": self.total_requests,
                "blocked_requests": self.blocked_requests,
                "block_rate": self.blocked_requests / max(self.total_requests, 1),
                "first_seen": self.first_seen,
                "last_request": self.last_request
            }
        }


class RateLimiter:
    """
    Gestor central de rate limiting

    Controla las tasas de peticiones por cliente con soporte para:
    - Rate limiting por IP
    - Múltiples tiers (free, premium, admin)
    - Whitelist/blacklist
    - Métricas y estadísticas
    """

    def __init__(
        self,
        default_tier: RateLimitTier = RateLimitTier.FREE,
        enable_metrics: bool = True
    ):
        """
        Inicializa el rate limiter

        Args:
            default_tier: Tier por defecto para nuevos clientes
            enable_metrics: Si habilitar recolección de métricas
        """
        self.default_tier = default_tier
        self.enable_metrics = enable_metrics

        # Almacenamiento de clientes
        self.clients: Dict[str, ClientRateLimit] = {}
        self.client_tiers: Dict[str, RateLimitTier] = {}

        # Whitelist/Blacklist
        self.whitelist: Set[str] = set()
        self.blacklist: Set[str] = set()

        # Locks para thread-safety
        self.clients_lock = Lock()
        self.whitelist_lock = Lock()
        self.blacklist_lock = Lock()

        # Métricas globales
        self.total_requests = 0
        self.total_blocked = 0
        self.start_time = time.time()

        logger.info(
            f"🚦 Rate Limiter inicializado (default_tier: {default_tier.value}, "
            f"metrics: {enable_metrics})"
        )

    def check_rate_limit(
        self,
        client_id: str,
        endpoint: str = ""
    ) -> Tuple[bool, Optional[str], Dict]:
        """
        Verifica si un cliente puede hacer una request

        Args:
            client_id: Identificador del cliente (normalmente IP)
            endpoint: Endpoint solicitado (opcional)

        Returns:
            Tupla (allowed, reason, headers)
            - allowed: True si se permite la request
            - reason: Razón del bloqueo (si allowed=False)
            - headers: Headers HTTP para agregar a la respuesta
        """
        self.total_requests += 1

        # Verificar blacklist
        with self.blacklist_lock:
            if client_id in self.blacklist:
                self.total_blocked += 1
                logger.warning(f"🚫 Request bloqueada - IP en blacklist: {client_id}")
                return False, "IP address is blacklisted", self._get_headers(client_id, blocked=True)

        # Verificar whitelist (bypass rate limiting)
        with self.whitelist_lock:
            if client_id in self.whitelist:
                logger.debug(f"✅ Request permitida - IP en whitelist: {client_id}")
                return True, None, self._get_headers(client_id, unlimited=True)

        # Obtener o crear cliente
        client = self._get_or_create_client(client_id)

        # Verificar rate limit
        allowed, reason = client.check_rate_limit()

        # Registrar request
        client.record_request(allowed, endpoint)

        # Actualizar métricas globales
        if not allowed:
            self.total_blocked += 1
            logger.warning(
                f"⚠️ Rate limit excedido - Client: {client_id}, "
                f"Endpoint: {endpoint}, Reason: {reason}"
            )
        else:
            logger.debug(f"✅ Request permitida - Client: {client_id}, Endpoint: {endpoint}")

        # Generar headers
        headers = self._get_headers(client_id, blocked=not allowed)

        return allowed, reason, headers

    def _get_or_create_client(self, client_id: str) -> ClientRateLimit:
        """Obtiene o crea un ClientRateLimit"""
        with self.clients_lock:
            if client_id not in self.clients:
                # Determinar tier del cliente
                tier = self.client_tiers.get(client_id, self.default_tier)
                config = TIER_CONFIGS[tier]

                # Crear nuevo cliente
                self.clients[client_id] = ClientRateLimit(
                    client_id=client_id,
                    config=config
                )

                logger.info(f"📝 Nuevo cliente registrado: {client_id} (tier: {tier.value})")

            return self.clients[client_id]

    def _get_headers(
        self,
        client_id: str,
        blocked: bool = False,
        unlimited: bool = False
    ) -> Dict[str, str]:
        """
        Genera headers HTTP para la respuesta

        Args:
            client_id: ID del cliente
            blocked: Si la request fue bloqueada
            unlimited: Si el cliente tiene acceso ilimitado

        Returns:
            Diccionario de headers
        """
        headers = {}

        if unlimited:
            headers["X-RateLimit-Limit"] = "unlimited"
            headers["X-RateLimit-Remaining"] = "unlimited"
            return headers

        # Obtener cliente
        client = self.clients.get(client_id)
        if not client:
            return headers

        # Headers estándar de rate limiting
        headers["X-RateLimit-Limit-Minute"] = str(client.config.requests_per_minute)
        headers["X-RateLimit-Limit-Hour"] = str(client.config.requests_per_hour)
        headers["X-RateLimit-Remaining-Minute"] = str(client.minute_bucket.get_available_tokens())
        headers["X-RateLimit-Remaining-Hour"] = str(client.hour_bucket.get_available_tokens())
        headers["X-RateLimit-Tier"] = client.config.tier.value

        if blocked:
            # Calcular retry-after
            wait_minute = client.minute_bucket.get_wait_time(1)
            wait_hour = client.hour_bucket.get_wait_time(1)
            retry_after = max(wait_minute, wait_hour)
            headers["Retry-After"] = str(int(retry_after) + 1)

        return headers

    def set_client_tier(self, client_id: str, tier: RateLimitTier) -> None:
        """
        Establece el tier de un cliente

        Args:
            client_id: ID del cliente
            tier: Nuevo tier
        """
        with self.clients_lock:
            self.client_tiers[client_id] = tier

            # Si el cliente ya existe, actualizar su configuración
            if client_id in self.clients:
                old_tier = self.clients[client_id].config.tier
                self.clients[client_id].config = TIER_CONFIGS[tier]

                # Recrear buckets con nueva configuración
                self.clients[client_id].__post_init__()

                logger.info(
                    f"🔄 Tier actualizado para cliente {client_id}: "
                    f"{old_tier.value} → {tier.value}"
                )
            else:
                logger.info(f"📝 Tier configurado para cliente {client_id}: {tier.value}")

    def add_to_whitelist(self, client_id: str) -> None:
        """Agrega un cliente a la whitelist"""
        with self.whitelist_lock:
            self.whitelist.add(client_id)
            logger.info(f"✅ Cliente agregado a whitelist: {client_id}")

    def remove_from_whitelist(self, client_id: str) -> None:
        """Remueve un cliente de la whitelist"""
        with self.whitelist_lock:
            self.whitelist.discard(client_id)
            logger.info(f"➖ Cliente removido de whitelist: {client_id}")

    def add_to_blacklist(self, client_id: str) -> None:
        """Agrega un cliente a la blacklist"""
        with self.blacklist_lock:
            self.blacklist.add(client_id)
            logger.warning(f"🚫 Cliente agregado a blacklist: {client_id}")

    def remove_from_blacklist(self, client_id: str) -> None:
        """Remueve un cliente de la blacklist"""
        with self.blacklist_lock:
            self.blacklist.discard(client_id)
            logger.info(f"➖ Cliente removido de blacklist: {client_id}")

    def get_client_status(self, client_id: str) -> Optional[Dict]:
        """Obtiene el estado de un cliente específico"""
        client = self.clients.get(client_id)
        if client:
            status = client.get_status()

            # Agregar información de whitelist/blacklist
            with self.whitelist_lock:
                status["is_whitelisted"] = client_id in self.whitelist

            with self.blacklist_lock:
                status["is_blacklisted"] = client_id in self.blacklist

            return status

        return None

    def get_global_stats(self) -> Dict:
        """Obtiene estadísticas globales del rate limiter"""
        with self.clients_lock:
            active_clients = len(self.clients)

            # Calcular estadísticas por tier
            tier_stats = defaultdict(int)
            for client in self.clients.values():
                tier_stats[client.config.tier.value] += 1

        uptime = time.time() - self.start_time

        return {
            "uptime_seconds": uptime,
            "total_requests": self.total_requests,
            "total_blocked": self.total_blocked,
            "block_rate": self.total_blocked / max(self.total_requests, 1),
            "requests_per_second": self.total_requests / max(uptime, 1),
            "active_clients": active_clients,
            "clients_by_tier": dict(tier_stats),
            "whitelist_size": len(self.whitelist),
            "blacklist_size": len(self.blacklist)
        }

    def reset_client(self, client_id: str) -> bool:
        """
        Resetea el rate limit de un cliente

        Args:
            client_id: ID del cliente

        Returns:
            True si se reseteó correctamente
        """
        with self.clients_lock:
            if client_id in self.clients:
                # Recrear cliente con configuración actual
                tier = self.clients[client_id].config.tier
                config = TIER_CONFIGS[tier]

                self.clients[client_id] = ClientRateLimit(
                    client_id=client_id,
                    config=config
                )

                logger.info(f"🔄 Rate limit reseteado para cliente: {client_id}")
                return True

        return False

    def cleanup_inactive_clients(self, inactive_threshold: float = 3600.0) -> int:
        """
        Limpia clientes inactivos

        Args:
            inactive_threshold: Tiempo de inactividad en segundos

        Returns:
            Número de clientes eliminados
        """
        now = time.time()
        removed = 0

        with self.clients_lock:
            inactive_clients = [
                client_id
                for client_id, client in self.clients.items()
                if (now - client.last_request) > inactive_threshold
            ]

            for client_id in inactive_clients:
                del self.clients[client_id]
                removed += 1

        if removed > 0:
            logger.info(f"🧹 Limpiados {removed} clientes inactivos")

        return removed


# Instancia global del rate limiter (lazy initialization)
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter(
    default_tier: RateLimitTier = RateLimitTier.FREE,
    enable_metrics: bool = True
) -> RateLimiter:
    """
    Obtiene la instancia global del rate limiter (singleton)

    Args:
        default_tier: Tier por defecto (solo primera inicialización)
        enable_metrics: Si habilitar métricas (solo primera inicialización)

    Returns:
        RateLimiter: Instancia global
    """
    global _global_rate_limiter

    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter(
            default_tier=default_tier,
            enable_metrics=enable_metrics
        )

    return _global_rate_limiter
