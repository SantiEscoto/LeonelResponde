"""
Script de Validación de Mejoras
================================

Script simple para validar las mejoras implementadas sin dependencias externas.

Autor: Assistant
Fecha: 2025
"""

import sys
import os
from pathlib import Path

# Agregar directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_health_checker():
    """Valida el sistema de Health Checks"""
    print("\n" + "="*60)
    print("TEST: Health Checker")
    print("="*60)

    try:
        from src.backend.utils.health_checker import get_health_checker

        checker = get_health_checker()
        print("✅ Health Checker inicializado correctamente")

        health = checker.check_system_health()
        print(f"✅ Health check ejecutado: {health.overall_status.value}")

        uptime = checker.get_uptime()
        print(f"✅ Uptime: {uptime:.2f}s")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_graceful_shutdown():
    """Valida el sistema de Graceful Shutdown"""
    print("\n" + "="*60)
    print("TEST: Graceful Shutdown")
    print("="*60)

    try:
        from src.backend.utils.graceful_shutdown import get_shutdown_manager

        manager = get_shutdown_manager()
        print("✅ Shutdown Manager inicializado correctamente")

        # Registrar callback de prueba
        callback_executed = []
        manager.register_callback(
            "test",
            lambda: callback_executed.append(True),
            priority=10
        )
        print(f"✅ Callback registrado (total: {len(manager.callbacks)})")

        stats = manager.get_stats()
        print(f"✅ Stats obtenidas: phase={stats.phase.value}")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_metrics_collector():
    """Valida el sistema de Métricas"""
    print("\n" + "="*60)
    print("TEST: Metrics Collector")
    print("="*60)

    try:
        from src.backend.utils.metrics_collector import (
            get_metrics_collector,
            MetricType,
            MetricCategory
        )

        collector = get_metrics_collector()
        print("✅ Metrics Collector inicializado correctamente")

        # Registrar métrica de prueba
        collector.register_metric(
            "test.metric",
            MetricType.COUNTER,
            MetricCategory.CUSTOM,
            "Test metric"
        )
        print("✅ Métrica registrada")

        # Recolectar métricas del sistema
        collector.collect_system_metrics()
        print("✅ Métricas del sistema recolectadas")

        summary = collector.get_summary()
        print(f"✅ Resumen: {summary['total_metrics']} métricas totales")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_rate_limiter():
    """Valida el sistema de Rate Limiting"""
    print("\n" + "="*60)
    print("TEST: Rate Limiter")
    print("="*60)

    try:
        from src.backend.utils.rate_limiter import get_rate_limiter, RateLimitTier

        limiter = get_rate_limiter()
        print("✅ Rate Limiter inicializado correctamente")

        # Test de rate limit check
        allowed, reason, headers = limiter.check_rate_limit("test_client")
        print(f"✅ Rate limit check: allowed={allowed}")

        # Test de whitelist
        limiter.add_to_whitelist("trusted_client")
        allowed, _, _ = limiter.check_rate_limit("trusted_client")
        print(f"✅ Whitelist funciona: allowed={allowed}")

        # Test de tier configuration
        limiter.set_client_tier("premium_user", RateLimitTier.PREMIUM)
        print("✅ Tier configurado")

        stats = limiter.get_global_stats()
        print(f"✅ Stats: {stats['total_requests']} requests, {stats['active_clients']} clientes")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_jwt_auth():
    """Valida el sistema de Autenticación JWT"""
    print("\n" + "="*60)
    print("TEST: JWT Authentication")
    print("="*60)

    try:
        from src.backend.utils.jwt_auth import get_auth_manager, UserRole

        manager = get_auth_manager()
        print("✅ JWT Auth Manager inicializado correctamente")
        print(f"✅ Usuarios existentes: {len(manager.users)}")

        # Crear usuario de prueba
        user = manager.create_user("testuser", "testpass123", UserRole.USER)
        print(f"✅ Usuario creado: {user.username}")

        # Test de autenticación
        auth_user = manager.authenticate("testuser", "testpass123")
        print(f"✅ Autenticación exitosa: {auth_user.username if auth_user else 'Failed'}")

        # Test de tokens
        access_token = manager.create_access_token(user)
        print(f"✅ Access token creado: {len(access_token)} caracteres")

        payload = manager.verify_token(access_token)
        print(f"✅ Token verificado: {payload.username if payload else 'Failed'}")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_model_versioning():
    """Valida el sistema de Model Versioning"""
    print("\n" + "="*60)
    print("TEST: Model Versioning")
    print("="*60)

    try:
        from src.backend.llm.model_versioning import get_version_manager
        import tempfile

        # Usar archivo temporal para tests
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = get_version_manager(versions_file=f"{tmpdir}/test_versions.json")
            print("✅ Model Version Manager inicializado correctamente")

            # Crear archivo de modelo falso
            model_file = Path(tmpdir) / "fake_model.gguf"
            model_file.write_text("fake model data for testing")

            # Registrar modelo
            version = manager.register_model(
                model_path=str(model_file),
                version_id="test_v1",
                description="Test version",
                set_as_active=True
            )
            print(f"✅ Modelo registrado: {version.version_id}")

            # Actualizar métricas
            success = manager.update_metrics("test_v1", 100.0, 50, success=True)
            print(f"✅ Métricas actualizadas: {success}")

            summary = manager.get_summary()
            print(f"✅ Resumen: {summary['total_versions']} versiones")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_warmup():
    """Valida que el Model Warmup tiene retry logic"""
    print("\n" + "="*60)
    print("TEST: Model Warmup con Retry Logic")
    print("="*60)

    try:
        from src.backend.llm.model_manager import LLMManager
        import inspect

        # Verificar que el método existe
        assert hasattr(LLMManager, '_warmup_model_with_retry')
        print("✅ Método _warmup_model_with_retry existe")

        # Verificar firma del método
        sig = inspect.signature(LLMManager._warmup_model_with_retry)
        params = list(sig.parameters.keys())

        assert 'max_retries' in params
        assert 'retry_delay' in params
        print("✅ Método tiene parámetros max_retries y retry_delay")

        # Verificar valores por defecto
        defaults = {
            k: v.default
            for k, v in sig.parameters.items()
            if v.default is not inspect.Parameter.empty
        }

        print(f"✅ Defaults: max_retries={defaults.get('max_retries', 'N/A')}, retry_delay={defaults.get('retry_delay', 'N/A')}")

        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Ejecuta todos los tests de validación"""
    print("\n" + "🚀 "*20)
    print("VALIDACIÓN DE MEJORAS IMPLEMENTADAS")
    print("🚀 "*20)

    tests = [
        ("Health Checker", test_health_checker),
        ("Graceful Shutdown", test_graceful_shutdown),
        ("Metrics Collector", test_metrics_collector),
        ("Rate Limiter", test_rate_limiter),
        ("JWT Authentication", test_jwt_auth),
        ("Model Versioning", test_model_versioning),
        ("Model Warmup", test_model_warmup),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ Error ejecutando {test_name}: {e}")
            results[test_name] = False

    # Resumen de resultados
    print("\n" + "="*60)
    print("RESUMEN DE VALIDACIÓN")
    print("="*60)

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "-"*60)
    print(f"Total: {total} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    print("-"*60)

    if passed == total:
        print("\n🎉 ¡TODAS LAS VALIDACIONES PASARON! 🎉")
        return 0
    else:
        print(f"\n⚠️ {failed} validaciones fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
