"""
验证器模块单元测试
"""

import pytest
from app.core.validator import (
    ValidationStatus,
    ValidationResult,
    MockKeyValidator,
    KeyValidatorFactory,
    BaseKeyValidator
)


class TestValidationResult:
    """验证结果测试类"""
    
    def test_validation_result_creation(self):
        """测试验证结果创建"""
        result = ValidationResult(
            key="test_key",
            status=ValidationStatus.VALID,
            message="Test message"
        )
        
        assert result.key == "test_key"
        assert result.status == ValidationStatus.VALID
        assert result.message == "Test message"
        assert result.timestamp > 0
    
    def test_is_valid_property(self):
        """测试is_valid属性"""
        valid_result = ValidationResult(
            key="key1",
            status=ValidationStatus.VALID
        )
        assert valid_result.is_valid is True
        
        invalid_result = ValidationResult(
            key="key2",
            status=ValidationStatus.INVALID
        )
        assert invalid_result.is_valid is False
    
    def test_is_rate_limited_property(self):
        """测试is_rate_limited属性"""
        rate_limited_result = ValidationResult(
            key="key1",
            status=ValidationStatus.RATE_LIMITED
        )
        assert rate_limited_result.is_rate_limited is True
        
        valid_result = ValidationResult(
            key="key2",
            status=ValidationStatus.VALID
        )
        assert valid_result.is_rate_limited is False


class TestMockKeyValidator:
    """模拟验证器测试类"""
    
    def test_mock_validator_creation(self):
        """测试模拟验证器创建"""
        validator = MockKeyValidator(["valid_key1", "valid_key2"])
        assert len(validator.valid_keys) == 2
    
    def test_validate_valid_key(self):
        """测试验证有效密钥"""
        validator = MockKeyValidator(["valid_key"])
        result = validator.validate("valid_key")
        
        assert result.is_valid
        assert result.status == ValidationStatus.VALID
        assert "Mock validation: valid key" in result.message
    
    def test_validate_invalid_key(self):
        """测试验证无效密钥"""
        validator = MockKeyValidator(["valid_key"])
        result = validator.validate("invalid_key")
        
        assert not result.is_valid
        assert result.status == ValidationStatus.INVALID
        assert "Mock validation: invalid key" in result.message
    
    def test_add_remove_valid_keys(self):
        """测试添加和移除有效密钥"""
        validator = MockKeyValidator()
        
        # 初始状态
        result = validator.validate("key1")
        assert not result.is_valid
        
        # 添加密钥
        validator.add_valid_key("key1")
        result = validator.validate("key1")
        assert result.is_valid
        
        # 移除密钥
        validator.remove_valid_key("key1")
        result = validator.validate("key1")
        assert not result.is_valid
    
    def test_batch_validation(self):
        """测试批量验证"""
        validator = MockKeyValidator(["key1", "key3"])
        keys = ["key1", "key2", "key3", "key4"]
        
        results = validator.validate_batch(keys)
        
        assert len(results) == 4
        assert results[0].is_valid  # key1
        assert not results[1].is_valid  # key2
        assert results[2].is_valid  # key3
        assert not results[3].is_valid  # key4
    
    def test_validation_stats(self):
        """测试验证统计"""
        validator = MockKeyValidator(["valid_key"])
        
        # 执行一些验证
        validator.validate("valid_key")
        validator.validate("invalid_key")
        
        stats = validator.get_stats()
        assert stats["total_validations"] == 2
        assert stats["error_count"] == 0
        assert stats["error_rate"] == 0


class TestKeyValidatorFactory:
    """验证器工厂测试类"""
    
    def test_create_mock_validator(self):
        """测试创建模拟验证器"""
        validator = KeyValidatorFactory.create("mock")
        assert isinstance(validator, MockKeyValidator)
    
    def test_create_gemini_validator(self):
        """测试创建Gemini验证器"""
        # 注意：这里只测试创建，不测试实际验证（需要API密钥）
        validator = KeyValidatorFactory.create(
            "gemini",
            model_name="gemini-2.0-flash-exp"
        )
        assert isinstance(validator, BaseKeyValidator)
    
    def test_create_invalid_validator(self):
        """测试创建无效验证器类型"""
        with pytest.raises(ValueError) as exc_info:
            KeyValidatorFactory.create("invalid_type")
        
        assert "Unsupported validator type" in str(exc_info.value)
    
    def test_list_validator_types(self):
        """测试列出验证器类型"""
        types = KeyValidatorFactory.list_types()
        assert "mock" in types
        assert "gemini" in types
    
    def test_register_custom_validator(self):
        """测试注册自定义验证器"""
        class CustomValidator(BaseKeyValidator):
            def validate(self, key: str) -> ValidationResult:
                return ValidationResult(
                    key=key,
                    status=ValidationStatus.VALID,
                    message="Custom validation"
                )
        
        # 注册自定义验证器
        KeyValidatorFactory.register("custom", CustomValidator)
        
        # 创建并测试
        validator = KeyValidatorFactory.create("custom")
        assert isinstance(validator, CustomValidator)
        
        result = validator.validate("test_key")
        assert result.is_valid
        assert "Custom validation" in result.message


class TestValidationStatus:
    """验证状态枚举测试"""
    
    def test_status_values(self):
        """测试状态值"""
        assert ValidationStatus.VALID.value == "valid"
        assert ValidationStatus.INVALID.value == "invalid"
        assert ValidationStatus.RATE_LIMITED.value == "rate_limited"
        assert ValidationStatus.SERVICE_DISABLED.value == "service_disabled"
        assert ValidationStatus.NETWORK_ERROR.value == "network_error"
        assert ValidationStatus.UNKNOWN_ERROR.value == "unknown_error"
    
    def test_status_comparison(self):
        """测试状态比较"""
        status1 = ValidationStatus.VALID
        status2 = ValidationStatus.VALID
        status3 = ValidationStatus.INVALID
        
        assert status1 == status2
        assert status1 != status3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])