"""
Dependency Injection Container for Orchestrix Application

This module provides a lightweight dependency injection container to manage
component lifecycle and reduce tight coupling between services.
"""

import logging
from typing import Any, Dict, Type, Callable, Optional, TypeVar, Generic
from abc import ABC, abstractmethod
from enum import Enum
import threading

T = TypeVar('T')


class ServiceLifetime(Enum):
    """Service lifetime management options"""
    SINGLETON = "singleton"
    TRANSIENT = "transient"
    SCOPED = "scoped"


class ServiceDescriptor:
    """Describes how a service should be created and managed"""
    
    def __init__(self, 
                 service_type: Type[T],
                 implementation: Optional[Type[T]] = None,
                 factory: Optional[Callable[..., T]] = None,
                 lifetime: ServiceLifetime = ServiceLifetime.SINGLETON,
                 dependencies: Optional[Dict[str, Type]] = None):
        self.service_type = service_type
        self.implementation = implementation or service_type
        self.factory = factory
        self.lifetime = lifetime
        self.dependencies = dependencies or {}
        self.instance = None
        self._lock = threading.Lock()


class DependencyInjectionContainer:
    """
    Lightweight dependency injection container that manages service lifecycle
    and resolves dependencies automatically.
    """
    
    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._scoped_instances: Dict[Type, Any] = {}
        self._lock = threading.Lock()
        self._disposing = False
    
    def register_singleton(self, service_type: Type[T], implementation: Optional[Type[T]] = None) -> 'DependencyInjectionContainer':
        """Register a service as singleton"""
        return self.register(service_type, implementation, ServiceLifetime.SINGLETON)
    
    def register_transient(self, service_type: Type[T], implementation: Optional[Type[T]] = None) -> 'DependencyInjectionContainer':
        """Register a service as transient (new instance each time)"""
        return self.register(service_type, implementation, ServiceLifetime.TRANSIENT)
    
    def register_scoped(self, service_type: Type[T], implementation: Optional[Type[T]] = None) -> 'DependencyInjectionContainer':
        """Register a service as scoped (one instance per scope)"""
        return self.register(service_type, implementation, ServiceLifetime.SCOPED)
    
    def register(self, 
                 service_type: Type[T], 
                 implementation: Optional[Type[T]] = None,
                 lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> 'DependencyInjectionContainer':
        """Register a service with the container"""
        with self._lock:
            if self._disposing:
                raise RuntimeError("Cannot register services while disposing")
            
            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation=implementation,
                lifetime=lifetime
            )
            self._services[service_type] = descriptor
            
            logging.debug(f"Registered {service_type.__name__} as {lifetime.value}")
            return self
    
    def register_factory(self, 
                        service_type: Type[T], 
                        factory: Callable[..., T],
                        lifetime: ServiceLifetime = ServiceLifetime.SINGLETON) -> 'DependencyInjectionContainer':
        """Register a service with a factory method"""
        with self._lock:
            if self._disposing:
                raise RuntimeError("Cannot register services while disposing")
            
            descriptor = ServiceDescriptor(
                service_type=service_type,
                factory=factory,
                lifetime=lifetime
            )
            self._services[service_type] = descriptor
            
            logging.debug(f"Registered {service_type.__name__} factory as {lifetime.value}")
            return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'DependencyInjectionContainer':
        """Register an existing instance as a singleton"""
        with self._lock:
            if self._disposing:
                raise RuntimeError("Cannot register services while disposing")
            
            descriptor = ServiceDescriptor(
                service_type=service_type,
                lifetime=ServiceLifetime.SINGLETON
            )
            descriptor.instance = instance
            self._services[service_type] = descriptor
            
            logging.debug(f"Registered {service_type.__name__} instance as singleton")
            return self
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service instance from the container"""
        if self._disposing:
            raise RuntimeError("Cannot get services while disposing")
        
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} is not registered")
        
        descriptor = self._services[service_type]
        
        # Handle different lifetimes
        if descriptor.lifetime == ServiceLifetime.SINGLETON:
            return self._get_singleton_instance(descriptor)
        elif descriptor.lifetime == ServiceLifetime.TRANSIENT:
            return self._create_instance(descriptor)
        elif descriptor.lifetime == ServiceLifetime.SCOPED:
            return self._get_scoped_instance(descriptor)
        
        raise ValueError(f"Unknown service lifetime: {descriptor.lifetime}")
    
    def _get_singleton_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Get or create a singleton instance"""
        if descriptor.instance is None:
            with descriptor._lock:
                if descriptor.instance is None:  # Double-check locking
                    descriptor.instance = self._create_instance(descriptor)
        return descriptor.instance
    
    def _get_scoped_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Get or create a scoped instance"""
        service_type = descriptor.service_type
        if service_type not in self._scoped_instances:
            with self._lock:
                if service_type not in self._scoped_instances:
                    self._scoped_instances[service_type] = self._create_instance(descriptor)
        return self._scoped_instances[service_type]
    
    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """Create a new instance of the service"""
        try:
            if descriptor.factory:
                # Use factory method
                return descriptor.factory(self)
            else:
                # Use constructor
                return descriptor.implementation()
        except Exception as e:
            logging.error(f"Failed to create instance of {descriptor.service_type.__name__}: {e}")
            raise
    
    def clear_scope(self):
        """Clear all scoped instances"""
        with self._lock:
            for instance in self._scoped_instances.values():
                if hasattr(instance, 'dispose'):
                    try:
                        instance.dispose()
                    except Exception as e:
                        logging.error(f"Error disposing scoped instance: {e}")
            self._scoped_instances.clear()
    
    def dispose(self):
        """Dispose of the container and all managed instances"""
        with self._lock:
            self._disposing = True
            
            # Dispose scoped instances
            self.clear_scope()
            
            # Dispose singleton instances
            for descriptor in self._services.values():
                if descriptor.instance and hasattr(descriptor.instance, 'dispose'):
                    try:
                        descriptor.instance.dispose()
                    except Exception as e:
                        logging.error(f"Error disposing singleton instance: {e}")
            
            self._services.clear()
            logging.info("Dependency injection container disposed")
    
    def is_registered(self, service_type: Type) -> bool:
        """Check if a service type is registered"""
        return service_type in self._services
    
    def get_registered_services(self) -> Dict[Type, ServiceDescriptor]:
        """Get all registered services (for debugging)"""
        return self._services.copy()


# Global container instance
_container: Optional[DependencyInjectionContainer] = None
_container_lock = threading.Lock()


def get_container() -> DependencyInjectionContainer:
    """Get the global dependency injection container"""
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DependencyInjectionContainer()
    return _container


def reset_container():
    """Reset the global container (mainly for testing)"""
    global _container
    with _container_lock:
        if _container:
            _container.dispose()
        _container = None


class ServiceProvider:
    """
    Service provider interface for components that need access to services
    """
    
    def __init__(self, container: Optional[DependencyInjectionContainer] = None):
        self._container = container or get_container()
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service from the container"""
        return self._container.get_service(service_type)
    
    def get_container(self) -> DependencyInjectionContainer:
        """Get the underlying container"""
        return self._container


# Decorator for automatic dependency injection
def inject(service_type: Type[T]) -> T:
    """
    Decorator for automatic dependency injection
    
    Usage:
        @inject
        def my_function(kubernetes_service: KubernetesService):
            # kubernetes_service will be automatically injected
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            container = get_container()
            service = container.get_service(service_type)
            return func(service, *args, **kwargs)
        return wrapper
    return decorator