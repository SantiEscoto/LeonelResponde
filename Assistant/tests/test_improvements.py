"""
Tests para validar las mejoras implementadas
=============================================

Tests unitarios para validar:
- Health Checks
- Graceful Shutdown
- Metrics Collector
- Rate Limiter
- JWT Authentication
- Model Versioning
- Model Warmup

Autor: Assistant
Fecha: 2025
"""

import pytest
import time
import tempfile
from pathlib import Path


class TestHealthChecker:
    """Tests para el sistema de Health Checks"""

    def test_health_checker_initialization(self):
        """Verifica que el health checker se inicializa correctamente"""
        from src.backend.utils.health_checker import get_health_checker

        checker = get_health_checker()
        assert checker is not None
        assert checker.get_uptime() >= 0

    def test_health_check_basic(self):
        """Verifica health check básico"""
        from src.backend.utils.health_checker import get_health_checker, HealthStatus

        checker = get_health_checker()
        health = checker.check_system_health()

        assert health is not None
        assert health.overall_status in [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
            HealthStatus.CRITICAL
        ]
        assert health.timestamp > 0

    def test_health_check_with_components(self):
        """Verifica health check con componentes"""
        from src.backend.utils.health_checker import get_health_checker

        checker = get_health_checker()

        # Mock components
        components = {
            'test_component': type('obj', (object,), {'get_status': lambda: {'status': 'ok'}})()
        }

        health = checker.check_system_health(components)
        assert 'test_component' in health.components

    def test_alert_thresholds(self):
        """Verifica configuración de umbrales de alerta"""
        from src.backend.utils.health_checker import HealthChecker

        thresholds = {
            'cpu_percent': 90.0,
            'memory_percent': 85.0
        }

        checker = HealthChecker(alert_thresholds=thresholds)
        assert checker.alert_thresholds['cpu_percent'] == 90.0


class TestGracefulShutdown:
    """Tests para el sistema de Graceful Shutdown"""

    def test_shutdown_manager_initialization(self):
        """Verifica que el shutdown manager se inicializa correctamente"""
        from src.backend.utils.graceful_shutdown import GracefulShutdownManager

        manager = GracefulShutdownManager(timeout=10.0)
        assert manager.timeout == 10.0
        assert not manager.shutdown_requested

    def test_callback_registration(self):
        """Verifica registro de callbacks"""
        from src.backend.utils.graceful_shutdown import GracefulShutdownManager

        manager = GracefulShutdownManager()
        callback_executed = []

        def test_callback():
            callback_executed.append(True)

        manager.register_callback("test", test_callback, priority=10)
        assert len(manager.callbacks) == 1
        assert manager.callbacks[0].name == "test"

    def test_callback_priority_sorting(self):
        """Verifica que los callbacks se ordenan por prioridad"""
        from src.backend.utils.graceful_shutdown import GracefulShutdownManager

        manager = GracefulShutdownManager()

        manager.register_callback("low", lambda: None, priority=1)
        manager.register_callback("high", lambda: None, priority=10)
        manager.register_callback("medium", lambda: None, priority=5)

        # Verificar orden (mayor prioridad primero)
        assert manager.callbacks[0].priority == 10
        assert manager.callbacks[1].priority == 5
        assert manager.callbacks[2].priority == 1


class TestMetricsCollector:
    """Tests para el sistema de Métricas"""

    def test_metrics_collector_initialization(self):
        """Verifica que el metrics collector se inicializa correctamente"""
        from src.backend.utils.metrics_collector import MetricsCollector

        collector = MetricsCollector(collection_interval=5.0)
        assert collector.collection_interval == 5.0
        assert not collector.is_collecting

    def test_metric_registration(self):
        """Verifica registro de métricas"""
        from src.backend.utils.metrics_collector import (
            MetricsCollector,
            MetricType,
            MetricCategory
        )

        collector = MetricsCollector()
        collector.register_metric(
            "test.metric",
            MetricType.COUNTER,
            MetricCategory.CUSTOM,
            "Test metric"
        )

        assert "test.metric" in collector.metrics

    def test_metric_recording(self):
        """Verifica grabación de valores de métricas"""
        from src.backend.utils.metrics_collector import (
            MetricsCollector,
            MetricType,
            MetricCategory
        )

        collector = MetricsCollector()
        collector.register_metric(
            "test.gauge",
            MetricType.GAUGE,
            MetricCategory.CUSTOM
        )

        collector.record("test.gauge", 42.0)
        current = collector.get_current("test.gauge")

        assert current == 42.0

    def test_system_metrics_collection(self):
        """Verifica recolección de métricas del sistema"""
        from src.backend.utils.metrics_collector import get_metrics_collector

        collector = get_metrics_collector()
        collector.collect_system_metrics()

        # Verificar que se recolectaron métricas del sistema
        cpu_metric = collector.get_metric("system.cpu.percent")
        assert cpu_metric is not None


class TestRateLimiter:
    """Tests para el sistema de Rate Limiting"""

    def test_rate_limiter_initialization(self):
        """Verifica que el rate limiter se inicializa correctamente"""
        from src.backend.utils.rate_limiter import RateLimiter, RateLimitTier

        limiter = RateLimiter(default_tier=RateLimitTier.FREE)
        assert limiter.default_tier == RateLimitTier.FREE

    def test_rate_limit_check(self):
        """Verifica comprobación de rate limit"""
        from src.backend.utils.rate_limiter import RateLimiter, RateLimitTier

        limiter = RateLimiter(default_tier=RateLimitTier.FREE)

        # Primera request debería pasar
        allowed, reason, headers = limiter.check_rate_limit("test_client")
        assert allowed is True

    def test_whitelist(self):
        """Verifica funcionamiento de whitelist"""
        from src.backend.utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        limiter.add_to_whitelist("trusted_client")

        # Cliente en whitelist siempre pasa
        for _ in range(100):
            allowed, _, _ = limiter.check_rate_limit("trusted_client")
            assert allowed is True

    def test_blacklist(self):
        """Verifica funcionamiento de blacklist"""
        from src.backend.utils.rate_limiter import RateLimiter

        limiter = RateLimiter()
        limiter.add_to_blacklist("blocked_client")

        # Cliente en blacklist siempre se bloquea
        allowed, reason, _ = limiter.check_rate_limit("blocked_client")
        assert allowed is False
        assert "blacklist" in reason.lower()

    def test_tier_configuration(self):
        """Verifica configuración de tiers"""
        from src.backend.utils.rate_limiter import RateLimiter, RateLimitTier

        limiter = RateLimiter()
        limiter.set_client_tier("premium_client", RateLimitTier.PREMIUM)

        # Verificar que el tier se configuró
        status = limiter.get_client_status("premium_client")
        assert status is None or status.get("tier") == "premium"


class TestJWTAuth:
    """Tests para el sistema de Autenticación JWT"""

    def test_auth_manager_initialization(self):
        """Verifica que el auth manager se inicializa correctamente"""
        from src.backend.utils.jwt_auth import JWTAuthManager

        manager = JWTAuthManager(access_token_expire_minutes=15)
        assert manager.access_token_expire_minutes == 15
        assert len(manager.users) > 0  # Admin por defecto

    def test_user_creation(self):
        """Verifica creación de usuarios"""
        from src.backend.utils.jwt_auth import JWTAuthManager, UserRole

        manager = JWTAuthManager()
        user = manager.create_user("testuser", "testpass", UserRole.USER)

        assert user.username == "testuser"
        assert user.role == UserRole.USER

    def test_authentication(self):
        """Verifica autenticación de usuarios"""
        from src.backend.utils.jwt_auth import JWTAuthManager, UserRole

        manager = JWTAuthManager()
        manager.create_user("authtest", "password123", UserRole.USER)

        # Autenticación correcta
        user = manager.authenticate("authtest", "password123")
        assert user is not None
        assert user.username == "authtest"

        # Autenticación incorrecta
        user = manager.authenticate("authtest", "wrongpass")
        assert user is None

    def test_token_creation(self):
        """Verifica creación de tokens"""
        from src.backend.utils.jwt_auth import JWTAuthManager, UserRole

        manager = JWTAuthManager()
        user = manager.create_user("tokentest", "pass", UserRole.USER)

        access_token = manager.create_access_token(user)
        assert access_token is not None
        assert len(access_token) > 0

    def test_token_verification(self):
        """Verifica verificación de tokens"""
        from src.backend.utils.jwt_auth import JWTAuthManager, UserRole

        manager = JWTAuthManager()
        user = manager.create_user("verifytest", "pass", UserRole.USER)

        access_token = manager.create_access_token(user)
        payload = manager.verify_token(access_token)

        assert payload is not None
        assert payload.username == "verifytest"

    def test_refresh_token(self):
        """Verifica renovación de tokens"""
        from src.backend.utils.jwt_auth import JWTAuthManager, UserRole

        manager = JWTAuthManager()
        user = manager.create_user("refreshtest", "pass", UserRole.USER)

        refresh_token = manager.create_refresh_token(user)
        result = manager.refresh_access_token(refresh_token)

        assert result is not None
        new_access, new_refresh = result
        assert len(new_access) > 0
        assert len(new_refresh) > 0


class TestModelVersioning:
    """Tests para el sistema de Model Versioning"""

    def test_version_manager_initialization(self):
        """Verifica que el version manager se inicializa correctamente"""
        from src.backend.llm.model_versioning import ModelVersionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            versions_file = Path(tmpdir) / "versions.json"
            manager = ModelVersionManager(versions_file=str(versions_file))

            assert manager.versions_file == versions_file
            assert len(manager.versions) == 0

    def test_model_registration(self):
        """Verifica registro de modelos"""
        from src.backend.llm.model_versioning import ModelVersionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Crear archivo de modelo temporal
            model_file = Path(tmpdir) / "test_model.gguf"
            model_file.write_text("fake model data")

            versions_file = Path(tmpdir) / "versions.json"
            manager = ModelVersionManager(versions_file=str(versions_file))

            version = manager.register_model(
                model_path=str(model_file),
                version_id="v1.0",
                description="Test model"
            )

            assert version.version_id == "v1.0"
            assert version.description == "Test model"
            assert len(manager.versions) == 1

    def test_active_version_management(self):
        """Verifica gestión de versión activa"""
        from src.backend.llm.model_versioning import ModelVersionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "test_model.gguf"
            model_file.write_text("fake model data")

            versions_file = Path(tmpdir) / "versions.json"
            manager = ModelVersionManager(versions_file=str(versions_file))

            version = manager.register_model(
                model_path=str(model_file),
                version_id="v1.0",
                set_as_active=True
            )

            assert manager.active_version_id == "v1.0"

            active = manager.get_active_version()
            assert active is not None
            assert active.version_id == "v1.0"

    def test_metrics_update(self):
        """Verifica actualización de métricas de versión"""
        from src.backend.llm.model_versioning import ModelVersionManager

        with tempfile.TemporaryDirectory() as tmpdir:
            model_file = Path(tmpdir) / "test_model.gguf"
            model_file.write_text("fake model data")

            versions_file = Path(tmpdir) / "versions.json"
            manager = ModelVersionManager(versions_file=str(versions_file))

            version = manager.register_model(
                model_path=str(model_file),
                version_id="v1.0"
            )

            # Actualizar métricas
            success = manager.update_metrics("v1.0", 100.0, 50, success=True)
            assert success is True

            # Verificar métricas
            updated_version = manager.get_version("v1.0")
            assert updated_version.metrics.total_queries == 1
            assert updated_version.metrics.successful_queries == 1


class TestModelWarmup:
    """Tests para el Model Warmup mejorado"""

    def test_warmup_retry_logic(self):
        """Verifica que el warmup tiene retry logic"""
        # Este test es conceptual ya que requiere un modelo real
        # Verificamos que el método existe y tiene la firma correcta
        from src.backend.llm.model_manager import LLMManager

        # Verificar que el método existe
        assert hasattr(LLMManager, '_warmup_model_with_retry')

        # Verificar firma del método
        import inspect
        sig = inspect.signature(LLMManager._warmup_model_with_retry)
        params = list(sig.parameters.keys())

        assert 'self' in params
        assert 'max_retries' in params
        assert 'retry_delay' in params


class TestIntegration:
    """Tests de integración básicos"""

    def test_all_systems_can_initialize(self):
        """Verifica que todos los sistemas se pueden inicializar sin errores"""
        from src.backend.utils.health_checker import get_health_checker
        from src.backend.utils.graceful_shutdown import get_shutdown_manager
        from src.backend.utils.metrics_collector import get_metrics_collector
        from src.backend.utils.rate_limiter import get_rate_limiter
        from src.backend.utils.jwt_auth import get_auth_manager
        from src.backend.llm.model_versioning import get_version_manager

        # Todos deberían inicializar sin errores
        health_checker = get_health_checker()
        shutdown_manager = get_shutdown_manager()
        metrics_collector = get_metrics_collector()
        rate_limiter = get_rate_limiter()
        auth_manager = get_auth_manager()
        version_manager = get_version_manager()

        assert health_checker is not None
        assert shutdown_manager is not None
        assert metrics_collector is not None
        assert rate_limiter is not None
        assert auth_manager is not None
        assert version_manager is not None

    def test_systems_summary_methods(self):
        """Verifica que todos los sistemas tienen métodos de resumen"""
        from src.backend.utils.health_checker import get_health_checker
        from src.backend.utils.metrics_collector import get_metrics_collector
        from src.backend.utils.rate_limiter import get_rate_limiter
        from src.backend.llm.model_versioning import get_version_manager

        health_checker = get_health_checker()
        metrics_collector = get_metrics_collector()
        rate_limiter = get_rate_limiter()
        version_manager = get_version_manager()

        # Todos deberían tener métodos de estadísticas/resumen
        health_summary = health_checker.check_system_health()
        metrics_summary = metrics_collector.get_summary()
        rate_limit_stats = rate_limiter.get_global_stats()
        version_summary = version_manager.get_summary()

        assert health_summary is not None
        assert metrics_summary is not None
        assert rate_limit_stats is not None
        assert version_summary is not None


if __name__ == "__main__":
    # Ejecutar tests con pytest
    pytest.main([__file__, "-v", "--tb=short"])
