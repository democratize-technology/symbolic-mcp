"""
SPDX-License-Identifier: MIT
Copyright (c) 2025 Symbolic MCP Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
Dependency Injection Container

Provides inversion of control for test dependencies, enabling
isolated testing without direct main module coupling.
"""

import threading
from typing import Dict, Any, Optional, Type, TypeVar, Union
from dataclasses import dataclass
from enum import Enum

from .interfaces import (
    SecurityValidatorInterface,
    RestrictedImporterInterface,
    SymbolicAnalyzerInterface,
    MemoryManagerInterface,
    ProcessIsolationInterface,
    MockSecurityValidator,
    MockRestrictedImporter,
    MockSymbolicAnalyzer,
    MockMemoryManager,
    MockProcessIsolation
)

T = TypeVar('T')


class EnvironmentType(Enum):
    """Types of environments for dependency configuration"""
    TESTING = "testing"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


@dataclass
class DependencyConfig:
    """Configuration for dependency injection"""
    environment: EnvironmentType
    use_mocks: bool = False
    mock_implementations: Dict[Type, Any] = None

    def __post_init__(self):
        if self.mock_implementations is None:
            self.mock_implementations = {}


class DIContainer:
    """
    Dependency Injection Container for test isolation.

    This container manages all dependencies for the test harnesses,
    allowing for mock implementations and easy switching between
    real and test environments.
    """

    def __init__(self, config: Optional[DependencyConfig] = None):
        self.config = config or DependencyConfig(EnvironmentType.TESTING, use_mocks=True)
        self._dependencies: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._setup_default_dependencies()

    def _setup_default_dependencies(self):
        """Setup default mock dependencies for testing"""
        if self.config.use_mocks:
            # Register mock implementations
            self.register_singleton(SecurityValidatorInterface, MockSecurityValidator)
            self.register_singleton(RestrictedImporterInterface, MockRestrictedImporter)
            self.register_singleton(SymbolicAnalyzerInterface, MockSymbolicAnalyzer)
            self.register_singleton(MemoryManagerInterface, MockMemoryManager)
            self.register_singleton(ProcessIsolationInterface, MockProcessIsolation)

    def register_singleton(self, interface: Type[T], implementation: Type[T]):
        """Register a singleton dependency implementation"""
        with self._lock:
            self._dependencies[interface] = ('singleton', implementation)

    def register_factory(self, interface: Type[T], factory_func):
        """Register a factory function for dependency creation"""
        with self._lock:
            self._dependencies[interface] = ('factory', factory_func)

    def register_instance(self, interface: Type[T], instance: T):
        """Register a specific instance as dependency"""
        with self._lock:
            self._singletons[interface] = instance
            self._dependencies[interface] = ('instance', None)

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency from the container"""
        with self._lock:
            # Check if we have a specific instance
            if interface in self._singletons:
                return self._singletons[interface]

            # Check if we have a registration
            if interface not in self._dependencies:
                raise ValueError(f"No dependency registered for {interface}")

            dependency_type, dependency_value = self._dependencies[interface]

            if dependency_type == 'singleton':
                # Create and cache singleton instance
                if interface not in self._singletons:
                    self._singletons[interface] = dependency_value()
                return self._singletons[interface]
            elif dependency_type == 'factory':
                # Call factory function
                return dependency_value()
            elif dependency_type == 'instance':
                # Should be handled above, but just in case
                return self._singletons[interface]
            else:
                raise ValueError(f"Unknown dependency type: {dependency_type}")

    def has(self, interface: Type[T]) -> bool:
        """Check if a dependency is registered"""
        with self._lock:
            return interface in self._dependencies or interface in self._singletons

    def clear(self):
        """Clear all registered dependencies"""
        with self._lock:
            self._dependencies.clear()
            self._singletons.clear()

    def get_registered_types(self) -> list[Type]:
        """Get list of registered dependency types"""
        with self._lock:
            return list(self._dependencies.keys())

    def create_child_container(self) -> 'DIContainer':
        """Create a child container that inherits dependencies"""
        child = DIContainer(self.config)
        with self._lock:
            child._dependencies = self._dependencies.copy()
            child._singletons = self._singletons.copy()
        return child


# Global container instance
_global_container: Optional[DIContainer] = None
_container_lock = threading.Lock()


def get_container() -> DIContainer:
    """Get the global dependency container"""
    global _global_container
    with _container_lock:
        if _global_container is None:
            _global_container = DIContainer()
        return _global_container


def set_container(container: DIContainer):
    """Set the global dependency container"""
    global _global_container
    with _container_lock:
        _global_container = container


def create_test_container(use_mocks: bool = True) -> DIContainer:
    """Create a container configured for testing"""
    config = DependencyConfig(EnvironmentType.TESTING, use_mocks=use_mocks)
    return DIContainer(config)


def create_production_container() -> DIContainer:
    """Create a container configured for production (real implementations)"""
    config = DependencyConfig(EnvironmentType.PRODUCTION, use_mocks=False)
    container = DIContainer(config)

    # Register real implementations (these would import from main module)
    try:
        # Import real implementations lazily to avoid direct coupling
        main_module = None
        try:
            main_module = __import__('main')
        except ImportError:
            pass

        if main_module:
            SecurityValidator = getattr(main_module, 'SecurityValidator', None)
            RestrictedImporter = getattr(main_module, 'RestrictedImporter', None)

            if SecurityValidator and RestrictedImporter:
                container.register_singleton(SecurityValidatorInterface, SecurityValidator)
                container.register_singleton(RestrictedImporterInterface, RestrictedImporter)

            # Create symbolic analyzer wrapper
            class RealSymbolicAnalyzer:
                def __init__(self):
                    self.logic_symbolic_check = getattr(main_module, 'logic_symbolic_check', None)
                    self.logic_find_path_to_exception = getattr(main_module, 'logic_find_path_to_exception', None)
                    self.logic_compare_functions = getattr(main_module, 'logic_compare_functions', None)
                    self.logic_analyze_branches = getattr(main_module, 'logic_analyze_branches', None)

                def analyze_function(self, code: str, function_name: str, timeout_seconds: int):
                    if self.logic_symbolic_check:
                        return self.logic_symbolic_check(code, function_name, timeout_seconds)
                    raise NotImplementedError("logic_symbolic_check not available")

                def find_exception_paths(self, code: str, function_name: str, exception_type: str, timeout_seconds: int):
                    if self.logic_find_path_to_exception:
                        return self.logic_find_path_to_exception(code, function_name, exception_type, timeout_seconds)
                    raise NotImplementedError("logic_find_path_to_exception not available")

                def compare_functions(self, code: str, function_a: str, function_b: str, timeout_seconds: int):
                    if self.logic_compare_functions:
                        return self.logic_compare_functions(code, function_a, function_b, timeout_seconds)
                    raise NotImplementedError("logic_compare_functions not available")

                def analyze_branches(self, code: str, function_name: str, timeout_seconds: int):
                    if self.logic_analyze_branches:
                        return self.logic_analyze_branches(code, function_name, timeout_seconds)
                    raise NotImplementedError("logic_analyze_branches not available")

        # Create real memory manager
        class RealMemoryManager:
            def set_memory_limit(self, limit_mb: int) -> bool:
                import resource
                try:
                    limit_bytes = limit_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, -1))
                    return True
                except (ValueError, ImportError):
                    return False

            def get_memory_usage(self) -> Dict[str, float]:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                return {
                    "current_usage_mb": memory_info.rss / 1024 / 1024,
                    "limit_mb": 2048,  # Default
                    "usage_percent": process.memory_percent()
                }

            def check_memory_limit_exceeded(self) -> bool:
                usage = self.get_memory_usage()
                return usage["current_usage_mb"] > usage["limit_mb"]

            def cleanup_memory(self) -> bool:
                import gc
                gc.collect()
                return True

        # Register real implementations
        container.register_singleton(SecurityValidatorInterface, SecurityValidator)
        container.register_singleton(RestrictedImporterInterface, RestrictedImporter)
        container.register_singleton(SymbolicAnalyzerInterface, RealSymbolicAnalyzer)
        container.register_singleton(MemoryManagerInterface, RealMemoryManager)

    except ImportError as e:
        # Fallback to mocks if main module not available
        from .interfaces import MockSymbolicAnalyzer, MockMemoryManager
        container.register_singleton(SymbolicAnalyzerInterface, MockSymbolicAnalyzer)
        container.register_singleton(MemoryManagerInterface, MockMemoryManager)
        print(f"Warning: Could not load real implementations, using mocks: {e}")

    return container


# Context managers for temporary container configuration
class ContainerContext:
    """Context manager for temporary container configuration"""

    def __init__(self, container: DIContainer):
        self.container = container
        self.previous_container: Optional[DIContainer] = None

    def __enter__(self) -> DIContainer:
        global _global_container
        with _container_lock:
            self.previous_container = _global_container
            _global_container = self.container
        return self.container

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _global_container
        with _container_lock:
            _global_container = self.previous_container


def with_test_container(use_mocks: bool = True):
    """Decorator to run function with test container"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = create_test_container(use_mocks)
            with ContainerContext(container):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def with_production_container():
    """Decorator to run function with production container"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = create_production_container()
            with ContainerContext(container):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions for resolving common dependencies
def get_security_validator() -> SecurityValidatorInterface:
    """Get the security validator from container"""
    return get_container().resolve(SecurityValidatorInterface)


def get_restricted_importer() -> RestrictedImporterInterface:
    """Get the restricted importer from container"""
    return get_container().resolve(RestrictedImporterInterface)


def get_symbolic_analyzer() -> SymbolicAnalyzerInterface:
    """Get the symbolic analyzer from container"""
    return get_container().resolve(SymbolicAnalyzerInterface)


def get_memory_manager() -> MemoryManagerInterface:
    """Get the memory manager from container"""
    return get_container().resolve(MemoryManagerInterface)


def get_process_isolation() -> ProcessIsolationInterface:
    """Get the process isolation from container"""
    return get_container().resolve(ProcessIsolationInterface)