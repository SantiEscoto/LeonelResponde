#!/usr/bin/env python3
"""
Dependency Validator for LeonelResponde Assistant
Validates and documents optional dependencies for robust offline operation
"""

from dataclasses import dataclass
import importlib
from pathlib import Path
import subprocess

# Add parent directory to path for imports
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.backend.utils.error_handler import (
        ErrorCategory,
        ErrorContext,
        ErrorSeverity,
        get_error_handler,
        resilient_operation,
    )
    from src.backend.utils.unified_config import get_config
    from src.backend.utils.unified_logger import get_unified_logger
except ImportError:
    # Fallback for direct execution
    try:
        from utils.error_handler import (
            ErrorCategory,
            ErrorContext,
            ErrorSeverity,
            get_error_handler,
            resilient_operation,
        )
        from utils.unified_config import get_config
        from utils.unified_logger import get_unified_logger
    except ImportError:
        from utils.unified_config import get_config
        from utils.unified_logger import get_unified_logger

        # Error handling fallbacks
        def resilient_operation(operation_name, max_retries=3, timeout=30):
            def decorator(func):
                return func

            return decorator

        class ErrorContext:
            def __init__(self, **kwargs):
                pass

        class ErrorSeverity:
            LOW = "low"
            MEDIUM = "medium"
            HIGH = "high"
            CRITICAL = "critical"

        class ErrorCategory:
            SYSTEM = "system"
            NETWORK = "network"
            VALIDATION = "validation"
            BUSINESS = "business"

        def get_error_handler():
            return None


logger = get_unified_logger("DEPENDENCY_VALIDATOR")


@dataclass
class DependencyInfo:
    """Information about a dependency"""

    name: str
    required: bool
    version_required: Optional[str]
    install_command: str
    description: str
    fallback_available: bool
    category: str
    import_names: List[str]
    installed: bool = False
    version_found: Optional[str] = None
    error_message: Optional[str] = None


class DependencyValidator:
    """Validates system dependencies and provides installation guidance"""

    def __init__(self):
        self.config = get_config()
        self.error_handler = get_error_handler()
        self.dependencies = self._define_dependencies()
        self.validation_results: Dict[str, DependencyInfo] = {}

    def _define_dependencies(self) -> Dict[str, DependencyInfo]:
        """Define all system dependencies with their requirements"""
        return {
            # Core LLM Dependencies
            "torch": DependencyInfo(
                name="PyTorch",
                required=True,
                version_required=">=2.0.0",
                install_command="pip install torch torchvision torchaudio",
                description="Deep learning framework for model inference",
                fallback_available=False,
                category="LLM",
                import_names=["torch"],
            ),
            "transformers": DependencyInfo(
                name="Transformers",
                required=True,
                version_required=">=4.30.0",
                install_command="pip install transformers",
                description="Hugging Face transformers library",
                fallback_available=False,
                category="LLM",
                import_names=["transformers"],
            ),
            "llama_cpp_python": DependencyInfo(
                name="llama-cpp-python",
                required=True,
                version_required=">=0.2.0",
                install_command="pip install llama-cpp-python",
                description="Python bindings for llama.cpp (GGUF model support)",
                fallback_available=False,
                category="LLM",
                import_names=["llama_cpp"],
            ),
            # Voice Processing
            "vosk": DependencyInfo(
                name="Vosk",
                required=True,
                version_required=">=0.3.45",
                install_command="pip install vosk",
                description="Offline speech recognition",
                fallback_available=False,
                category="Voice",
                import_names=["vosk"],
            ),
            "sounddevice": DependencyInfo(
                name="SoundDevice",
                required=True,
                version_required=">=0.4.0",
                install_command="pip install sounddevice",
                description="Audio input/output for voice processing",
                fallback_available=False,
                category="Voice",
                import_names=["sounddevice"],
            ),
            "TTS": DependencyInfo(
                name="Coqui TTS",
                required=True,
                version_required=">=0.20.0",
                install_command="pip install TTS",
                description="Text-to-speech synthesis (xTTS-v2)",
                fallback_available=True,
                category="Voice",
                import_names=["TTS"],
            ),
            # Vision Processing
            "cv2": DependencyInfo(
                name="OpenCV",
                required=False,
                version_required=">=4.8.0",
                install_command="pip install opencv-python",
                description="Computer vision and image processing",
                fallback_available=True,
                category="Vision",
                import_names=["cv2"],
            ),
            "easyocr": DependencyInfo(
                name="EasyOCR",
                required=False,
                version_required=">=1.7.0",
                install_command="pip install easyocr",
                description="Optical character recognition",
                fallback_available=True,
                category="Vision",
                import_names=["easyocr"],
            ),
            "face_recognition": DependencyInfo(
                name="Face Recognition",
                required=False,
                version_required=">=1.3.0",
                install_command="pip install face_recognition",
                description="Face detection and recognition",
                fallback_available=True,
                category="Vision",
                import_names=["face_recognition"],
            ),
            "ultralytics": DependencyInfo(
                name="Ultralytics YOLO",
                required=False,
                version_required=">=8.0.0",
                install_command="pip install ultralytics",
                description="Object detection and segmentation",
                fallback_available=True,
                category="Vision",
                import_names=["ultralytics"],
            ),
            # Memory and Storage
            "faiss": DependencyInfo(
                name="FAISS",
                required=True,
                version_required=">=1.7.0",
                install_command="pip install faiss-cpu",
                description="Vector similarity search for knowledge base",
                fallback_available=False,
                category="Memory",
                import_names=["faiss"],
            ),
            "sentence_transformers": DependencyInfo(
                name="Sentence Transformers",
                required=True,
                version_required=">=2.2.0",
                install_command="pip install sentence-transformers",
                description="Embedding models for semantic search",
                fallback_available=False,
                category="Memory",
                import_names=["sentence_transformers"],
            ),
            # Web Interface
            "fastapi": DependencyInfo(
                name="FastAPI",
                required=True,
                version_required=">=0.100.0",
                install_command="pip install fastapi",
                description="Web API framework",
                fallback_available=False,
                category="Web",
                import_names=["fastapi"],
            ),
            "uvicorn": DependencyInfo(
                name="Uvicorn",
                required=True,
                version_required=">=0.23.0",
                install_command="pip install uvicorn",
                description="ASGI server for FastAPI",
                fallback_available=False,
                category="Web",
                import_names=["uvicorn"],
            ),
            # Performance Optimization
            "tensorrt": DependencyInfo(
                name="TensorRT",
                required=False,
                version_required=">=8.6.0",
                install_command="pip install tensorrt",
                description="NVIDIA GPU acceleration (optional)",
                fallback_available=True,
                category="Performance",
                import_names=["tensorrt"],
            ),
            "onnxruntime": DependencyInfo(
                name="ONNX Runtime",
                required=False,
                version_required=">=1.15.0",
                install_command="pip install onnxruntime",
                description="Cross-platform ML inference (optional)",
                fallback_available=True,
                category="Performance",
                import_names=["onnxruntime"],
            ),
            # Utility Libraries
            "numpy": DependencyInfo(
                name="NumPy",
                required=True,
                version_required=">=1.24.0",
                install_command="pip install numpy",
                description="Numerical computing library",
                fallback_available=False,
                category="Utility",
                import_names=["numpy"],
            ),
            "pandas": DependencyInfo(
                name="Pandas",
                required=False,
                version_required=">=2.0.0",
                install_command="pip install pandas",
                description="Data manipulation and analysis",
                fallback_available=True,
                category="Utility",
                import_names=["pandas"],
            ),
            "requests": DependencyInfo(
                name="Requests",
                required=True,
                version_required=">=2.31.0",
                install_command="pip install requests",
                description="HTTP library for API calls",
                fallback_available=False,
                category="Utility",
                import_names=["requests"],
            ),
        }

    def _get_package_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a package"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Version:"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
        return None

    def _check_import(self, import_names: List[str]) -> Tuple[bool, Optional[str]]:
        """Check if modules can be imported"""
        for import_name in import_names:
            try:
                importlib.import_module(import_name)
                return True, None
            except ImportError:
                continue
        return False, f"Cannot import any of: {', '.join(import_names)}"

    def validate_dependency(self, dep_key: str) -> DependencyInfo:
        """Validate a single dependency"""
        dep = self.dependencies[dep_key] if dep_key in self.dependencies else None
        if not dep:
            raise ValueError(f"Unknown dependency: {dep_key}")

        # Check if package is installed
        dep.version_found = self._get_package_version(dep_key)

        # Check if modules can be imported
        can_import, import_error = self._check_import(dep.import_names)

        if dep.version_found and can_import:
            dep.installed = True
            dep.error_message = None
        else:
            dep.installed = False
            if not dep.version_found:
                dep.error_message = f"Package '{dep_key}' not installed"
            elif not can_import:
                dep.error_message = import_error

        return dep

    def validate_all_dependencies(self) -> Dict[str, DependencyInfo]:
        """Validate all dependencies"""
        logger.info("Starting dependency validation...")

        for dep_key in self.dependencies.keys():
            try:
                self.validation_results[dep_key] = self.validate_dependency(dep_key)
            except Exception as e:
                logger.error(f"Error validating {dep_key}: {e}")
                dep = self.dependencies[dep_key]
                dep.installed = False
                dep.error_message = str(e)
                self.validation_results[dep_key] = dep

        logger.info("Dependency validation completed")
        return self.validation_results

    def get_missing_required_dependencies(self) -> List[DependencyInfo]:
        """Get list of missing required dependencies"""
        return [
            dep for dep in self.validation_results.values() if dep.required and not dep.installed
        ]

    def get_missing_optional_dependencies(self) -> List[DependencyInfo]:
        """Get list of missing optional dependencies"""
        return [
            dep
            for dep in self.validation_results.values()
            if not dep.required and not dep.installed
        ]

    def generate_installation_script(self, include_optional: bool = False) -> str:
        """Generate installation script for missing dependencies"""
        missing_deps = self.get_missing_required_dependencies()
        if include_optional:
            missing_deps.extend(self.get_missing_optional_dependencies())

        if not missing_deps:
            return "# All dependencies are already installed!\n"

        script_lines = [
            "#!/bin/bash",
            "# Auto-generated dependency installation script",
            "# for LeonelResponde Assistant",
            "",
            "echo 'Installing missing dependencies...'",
            "",
        ]

        # Group by category
        by_category = {}
        for dep in missing_deps:
            if dep.category not in by_category:
                by_category[dep.category] = []
            by_category[dep.category].append(dep)

        for category, deps in by_category.items():
            script_lines.append(f"# {category} Dependencies")
            for dep in deps:
                script_lines.append(f"echo 'Installing {dep.name}...'")
                script_lines.append(dep.install_command)
                script_lines.append("")

        script_lines.extend(
            [
                "echo 'Installation completed!'",
                "echo 'Please restart the application to use new dependencies.'",
            ]
        )

        return "\n".join(script_lines)

    def generate_report(self) -> str:
        """Generate comprehensive dependency report"""
        if not self.validation_results:
            self.validate_all_dependencies()

        report_lines = [
            "# LeonelResponde Assistant - Dependency Report",
            f"Generated on: {Path(__file__).stat().st_mtime}",
            "",
            "## Summary",
            "",
        ]

        # Summary statistics
        total_deps = len(self.validation_results)
        installed_deps = sum(1 for dep in self.validation_results.values() if dep.installed)
        required_deps = sum(1 for dep in self.validation_results.values() if dep.required)
        required_installed = sum(
            1 for dep in self.validation_results.values() if dep.required and dep.installed
        )

        report_lines.extend(
            [
                f"- Total dependencies: {total_deps}",
                f"- Installed: {installed_deps}/{total_deps}",
                f"- Required dependencies: {required_deps}",
                f"- Required installed: {required_installed}/{required_deps}",
                "",
            ]
        )

        # Status by category
        by_category = {}
        for dep in self.validation_results.values():
            if dep.category not in by_category:
                by_category[dep.category] = {"total": 0, "installed": 0}
            by_category[dep.category]["total"] += 1
            if dep.installed:
                by_category[dep.category]["installed"] += 1

        report_lines.append("## Status by Category")
        report_lines.append("")
        for category, stats in sorted(by_category.items()):
            status = "✅" if stats["installed"] == stats["total"] else "⚠️"
            report_lines.append(f"- {status} {category}: {stats['installed']}/{stats['total']}")
        report_lines.append("")

        # Detailed dependency status
        report_lines.append("## Detailed Status")
        report_lines.append("")

        for category in sorted(by_category.keys()):
            report_lines.append(f"### {category} Dependencies")
            report_lines.append("")

            category_deps = [
                dep for dep in self.validation_results.values() if dep.category == category
            ]
            category_deps.sort(key=lambda x: (not x.required, x.name))

            for dep in category_deps:
                status_icon = "✅" if dep.installed else "❌"
                required_text = "(Required)" if dep.required else "(Optional)"
                fallback_text = " - Fallback available" if dep.fallback_available else ""

                report_lines.append(
                    f"- {status_icon} **{dep.name}** {required_text}{fallback_text}"
                )
                report_lines.append(f"  - Description: {dep.description}")

                if dep.installed:
                    report_lines.append(f"  - Version: {dep.version_found or 'Unknown'}")
                else:
                    report_lines.append(f"  - Status: {dep.error_message or 'Not installed'}")
                    report_lines.append(f"  - Install: `{dep.install_command}`")

                report_lines.append("")

        # Installation instructions
        missing_required = self.get_missing_required_dependencies()
        missing_optional = self.get_missing_optional_dependencies()

        if missing_required or missing_optional:
            report_lines.append("## Installation Instructions")
            report_lines.append("")

            if missing_required:
                report_lines.append("### Required Dependencies (Must Install)")
                report_lines.append("```bash")
                for dep in missing_required:
                    report_lines.append(dep.install_command)
                report_lines.append("```")
                report_lines.append("")

            if missing_optional:
                report_lines.append("### Optional Dependencies (Recommended)")
                report_lines.append("```bash")
                for dep in missing_optional:
                    report_lines.append(dep.install_command)
                report_lines.append("```")
                report_lines.append("")

        return "\n".join(report_lines)

    def save_report(self, filepath: Optional[Path] = None) -> Path:
        """Save dependency report to file"""
        if filepath is None:
            filepath = self.config.paths.logs_dir / "dependency_report.md"

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.generate_report())

        logger.info(f"Dependency report saved to: {filepath}")
        return filepath

    def save_installation_script(
        self, filepath: Optional[Path] = None, include_optional: bool = False
    ) -> Path:
        """Save installation script to file"""
        if filepath is None:
            filepath = self.config.paths.project_root / "install_dependencies.sh"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.generate_installation_script(include_optional))

        # Make script executable
        filepath.chmod(0o755)

        logger.info(f"Installation script saved to: {filepath}")
        return filepath


def main():
    """Main function for command-line usage"""
    validator = DependencyValidator()

    print("🔍 Validating dependencies...")
    results = validator.validate_all_dependencies()

    # Print summary
    total = len(results)
    installed = sum(1 for dep in results.values() if dep.installed)
    missing_required = validator.get_missing_required_dependencies()

    print(f"\n📊 Summary: {installed}/{total} dependencies installed")

    if missing_required:
        print(f"❌ Missing {len(missing_required)} required dependencies:")
        for dep in missing_required:
            print(f"   - {dep.name}: {dep.install_command}")
    else:
        print("✅ All required dependencies are installed!")

    # Save reports
    report_path = validator.save_report()
    script_path = validator.save_installation_script(include_optional=True)

    print(f"\n📄 Full report saved to: {report_path}")
    print(f"🔧 Installation script saved to: {script_path}")

    if missing_required:
        print("\n⚠️  Please install missing required dependencies before running the assistant.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
