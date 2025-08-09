"""
依赖注入容器
用于管理应用程序中的依赖关系和服务实例
"""

import inspect
from typing import Dict, Any, Type, Optional, Callable, TypeVar
from functools import wraps
import threading

T = TypeVar('T')


class DIContainer:
    """
    依赖注入容器
    支持单例模式、工厂模式和自动依赖解析
    """
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._lock = threading.Lock()
        
    def register(
        self, 
        interface: Type[T], 
        implementation: Optional[Any] = None,
        factory: Optional[Callable[[], T]] = None,
        singleton: bool = False
    ) -> None:
        """
        注册服务或工厂
        
        Args:
            interface: 接口类型
            implementation: 实现实例（可选）
            factory: 工厂函数（可选）
            singleton: 是否为单例模式
        """
        with self._lock:
            if factory:
                self._factories[interface] = factory
                if singleton:
                    # 包装工厂函数以实现单例
                    original_factory = factory
                    @wraps(original_factory)
                    def singleton_factory():
                        if interface not in self._singletons:
                            self._singletons[interface] = original_factory()
                        return self._singletons[interface]
                    self._factories[interface] = singleton_factory
            elif implementation:
                if singleton:
                    self._singletons[interface] = implementation
                else:
                    self._services[interface] = implementation
            else:
                # 如果没有提供实现或工厂，则尝试自动创建
                self._factories[interface] = lambda: self._auto_resolve(interface)
                
    def resolve(self, interface: Type[T]) -> T:
        """
        解析依赖
        
        Args:
            interface: 要解析的接口类型
            
        Returns:
            解析后的实例
            
        Raises:
            ValueError: 如果无法解析依赖
        """
        with self._lock:
            # 检查单例
            if interface in self._singletons:
                return self._singletons[interface]
                
            # 检查服务
            if interface in self._services:
                return self._services[interface]
                
            # 检查工厂
            if interface in self._factories:
                return self._factories[interface]()
                
            # 尝试自动解析
            return self._auto_resolve(interface)
            
    def _auto_resolve(self, interface: Type[T]) -> T:
        """
        自动解析依赖（通过构造函数注入）
        
        Args:
            interface: 要解析的类型
            
        Returns:
            自动创建的实例
        """
        if not inspect.isclass(interface):
            raise ValueError(f"Cannot auto-resolve non-class type: {interface}")
            
        # 获取构造函数签名
        sig = inspect.signature(interface.__init__)
        kwargs = {}
        
        for name, param in sig.parameters.items():
            if name == 'self':
                continue
                
            # 如果参数有类型注解，尝试解析
            if param.annotation != param.empty:
                try:
                    kwargs[name] = self.resolve(param.annotation)
                except ValueError:
                    # 如果有默认值，使用默认值
                    if param.default != param.empty:
                        kwargs[name] = param.default
                    else:
                        raise ValueError(
                            f"Cannot resolve dependency {param.annotation} for {interface}"
                        )
            elif param.default != param.empty:
                kwargs[name] = param.default
                
        return interface(**kwargs)
        
    def register_singleton(self, interface: Type[T], implementation: T) -> None:
        """
        注册单例服务
        
        Args:
            interface: 接口类型
            implementation: 实现实例
        """
        self.register(interface, implementation=implementation, singleton=True)
        
    def register_factory(
        self, 
        interface: Type[T], 
        factory: Callable[[], T],
        singleton: bool = False
    ) -> None:
        """
        注册工厂函数
        
        Args:
            interface: 接口类型
            factory: 工厂函数
            singleton: 是否为单例模式
        """
        self.register(interface, factory=factory, singleton=singleton)
        
    def has(self, interface: Type) -> bool:
        """
        检查是否已注册指定的接口
        
        Args:
            interface: 接口类型
            
        Returns:
            是否已注册
        """
        return (
            interface in self._services or
            interface in self._factories or
            interface in self._singletons
        )
        
    def clear(self) -> None:
        """清空容器中的所有注册"""
        with self._lock:
            self._services.clear()
            self._factories.clear()
            self._singletons.clear()


# 全局容器实例
_container: Optional[DIContainer] = None
_container_lock = threading.Lock()


def get_container() -> DIContainer:
    """
    获取全局容器实例（单例）
    
    Returns:
        全局DI容器实例
    """
    global _container
    if _container is None:
        with _container_lock:
            if _container is None:
                _container = DIContainer()
    return _container


def inject(func: Callable) -> Callable:
    """
    依赖注入装饰器
    自动注入函数参数中的依赖
    
    Args:
        func: 要装饰的函数
        
    Returns:
        装饰后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        container = get_container()
        sig = inspect.signature(func)
        
        # 解析未提供的参数
        for name, param in sig.parameters.items():
            if name not in kwargs and param.annotation != param.empty:
                if container.has(param.annotation):
                    kwargs[name] = container.resolve(param.annotation)
                    
        return func(*args, **kwargs)
    
    return wrapper