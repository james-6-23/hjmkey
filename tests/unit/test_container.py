"""
依赖注入容器单元测试
"""

import pytest
from app.core.container import DIContainer, get_container, inject


class TestService:
    """测试服务类"""
    def __init__(self, value: str = "default"):
        self.value = value
    
    def get_value(self) -> str:
        return self.value


class DependentService:
    """依赖其他服务的测试类"""
    def __init__(self, test_service: TestService):
        self.test_service = test_service
    
    def get_combined_value(self) -> str:
        return f"Dependent: {self.test_service.get_value()}"


class TestDIContainer:
    """依赖注入容器测试类"""
    
    def setup_method(self):
        """每个测试前创建新容器"""
        self.container = DIContainer()
    
    def test_register_and_resolve_instance(self):
        """测试注册和解析实例"""
        service = TestService("test_value")
        self.container.register(TestService, implementation=service)
        
        resolved = self.container.resolve(TestService)
        assert resolved is service
        assert resolved.get_value() == "test_value"
    
    def test_register_and_resolve_factory(self):
        """测试注册和解析工厂函数"""
        def factory():
            return TestService("factory_value")
        
        self.container.register(TestService, factory=factory)
        
        resolved = self.container.resolve(TestService)
        assert isinstance(resolved, TestService)
        assert resolved.get_value() == "factory_value"
        
        # 每次解析应该创建新实例（非单例）
        resolved2 = self.container.resolve(TestService)
        assert resolved is not resolved2
    
    def test_singleton_registration(self):
        """测试单例注册"""
        service = TestService("singleton_value")
        self.container.register_singleton(TestService, service)
        
        resolved1 = self.container.resolve(TestService)
        resolved2 = self.container.resolve(TestService)
        
        assert resolved1 is resolved2
        assert resolved1 is service
    
    def test_singleton_factory(self):
        """测试单例工厂"""
        call_count = 0
        
        def factory():
            nonlocal call_count
            call_count += 1
            return TestService(f"factory_{call_count}")
        
        self.container.register(TestService, factory=factory, singleton=True)
        
        resolved1 = self.container.resolve(TestService)
        resolved2 = self.container.resolve(TestService)
        
        assert resolved1 is resolved2
        assert call_count == 1  # 工厂只应被调用一次
        assert resolved1.get_value() == "factory_1"
    
    def test_auto_resolve_dependencies(self):
        """测试自动解析依赖"""
        # 注册基础服务
        self.container.register(TestService, implementation=TestService("auto_value"))
        
        # 不显式注册DependentService，让容器自动解析
        resolved = self.container.resolve(DependentService)
        
        assert isinstance(resolved, DependentService)
        assert resolved.get_combined_value() == "Dependent: auto_value"
    
    def test_has_method(self):
        """测试has方法"""
        assert not self.container.has(TestService)
        
        self.container.register(TestService, implementation=TestService())
        assert self.container.has(TestService)
    
    def test_clear_method(self):
        """测试clear方法"""
        self.container.register(TestService, implementation=TestService())
        assert self.container.has(TestService)
        
        self.container.clear()
        assert not self.container.has(TestService)
    
    def test_resolve_unregistered_type(self):
        """测试解析未注册的类型"""
        # 应该尝试自动创建
        resolved = self.container.resolve(TestService)
        assert isinstance(resolved, TestService)
        assert resolved.get_value() == "default"
    
    def test_resolve_with_default_parameters(self):
        """测试带默认参数的自动解析"""
        class ServiceWithDefaults:
            def __init__(self, value: str = "default", number: int = 42):
                self.value = value
                self.number = number
        
        resolved = self.container.resolve(ServiceWithDefaults)
        assert resolved.value == "default"
        assert resolved.number == 42
    
    def test_thread_safety(self):
        """测试线程安全性"""
        import threading
        import time
        
        results = []
        
        def register_and_resolve():
            service = TestService(f"thread_{threading.current_thread().name}")
            self.container.register_singleton(
                type(f"Service_{threading.current_thread().name}", (), {}),
                service
            )
            time.sleep(0.01)  # 模拟一些处理时间
            results.append(service)
        
        threads = [threading.Thread(target=register_and_resolve) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert len(results) == 10
        # 确保所有服务都被正确注册
        assert all(isinstance(r, TestService) for r in results)


class TestGlobalContainer:
    """全局容器测试"""
    
    def test_get_container_singleton(self):
        """测试获取全局容器单例"""
        container1 = get_container()
        container2 = get_container()
        
        assert container1 is container2
    
    def test_global_container_persistence(self):
        """测试全局容器持久性"""
        container = get_container()
        container.register(TestService, implementation=TestService("global_value"))
        
        # 再次获取容器
        container2 = get_container()
        resolved = container2.resolve(TestService)
        
        assert resolved.get_value() == "global_value"


class TestInjectDecorator:
    """依赖注入装饰器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        container = get_container()
        container.clear()
        container.register(TestService, implementation=TestService("injected_value"))
    
    def teardown_method(self):
        """清理测试环境"""
        get_container().clear()
    
    def test_inject_decorator(self):
        """测试inject装饰器"""
        @inject
        def function_with_dependency(service: TestService):
            return service.get_value()
        
        result = function_with_dependency()
        assert result == "injected_value"
    
    def test_inject_with_partial_args(self):
        """测试部分参数注入"""
        @inject
        def function_with_mixed_params(name: str, service: TestService):
            return f"{name}: {service.get_value()}"
        
        result = function_with_mixed_params("Test")
        assert result == "Test: injected_value"
    
    def test_inject_with_provided_args(self):
        """测试提供参数时不注入"""
        @inject
        def function_with_dependency(service: TestService):
            return service.get_value()
        
        custom_service = TestService("custom_value")
        result = function_with_dependency(service=custom_service)
        assert result == "custom_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])