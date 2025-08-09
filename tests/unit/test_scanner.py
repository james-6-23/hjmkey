"""
扫描器模块单元测试
"""

import pytest
from datetime import datetime, timedelta
from app.core.scanner import Scanner, ScanFilter, ScanResult


class TestScanner:
    """扫描器测试类"""
    
    def setup_method(self):
        """测试前设置"""
        self.scanner = Scanner()
    
    def test_extract_keys_from_content(self):
        """测试密钥提取功能"""
        # 测试有效密钥
        content = "API_KEY=AIzaSyA1234567890abcdefghijklmnopqrstuv"
        keys = self.scanner.extract_keys_from_content(content)
        assert len(keys) == 1
        assert keys[0] == "AIzaSyA1234567890abcdefghijklmnopqrstuv"
        
        # 测试多个密钥
        content = """
        key1: AIzaSyA1234567890abcdefghijklmnopqrstuv
        key2: AIzaSyB0987654321zyxwvutsrqponmlkjihgfed
        """
        keys = self.scanner.extract_keys_from_content(content)
        assert len(keys) == 2
        
        # 测试无密钥
        content = "This is just regular text without any keys"
        keys = self.scanner.extract_keys_from_content(content)
        assert len(keys) == 0
    
    def test_placeholder_key_detection(self):
        """测试占位符密钥检测"""
        # 测试占位符密钥
        content = "API_KEY=AIzaSyYOUR_API_KEY_HERE_1234567890abc"
        keys = self.scanner.extract_keys_from_content(content)
        assert len(keys) == 0  # 应该被过滤掉
        
        # 测试包含省略号的密钥
        content = "key: AIzaSy......................................"
        keys = self.scanner.extract_keys_from_content(content)
        assert len(keys) == 0
        
        # 测试重复字符的密钥
        content = "key: AIzaSyAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        keys = self.scanner.extract_keys_from_content(content)
        assert len(keys) == 0
    
    def test_normalize_query(self):
        """测试查询标准化"""
        # 测试基本标准化
        query = "AIzaSy   in:file   language:python"
        normalized = self.scanner.normalize_query(query)
        assert "  " not in normalized  # 不应有多余空格
        
        # 测试引号处理
        query = '"API_KEY" in:file'
        normalized = self.scanner.normalize_query(query)
        assert '"API_KEY"' in normalized
        
        # 测试组件排序
        query = "language:python AIzaSy filename:config"
        normalized = self.scanner.normalize_query(query)
        # 应该按固定顺序排列
        assert normalized.index("AIzaSy") < normalized.index("language:")
        assert normalized.index("language:") < normalized.index("filename:")
    
    def test_scan_filter(self):
        """测试扫描过滤器"""
        filter = ScanFilter(
            date_range_days=30,
            file_path_blacklist=["readme", "docs", ".md"]
        )
        
        # 测试SHA去重
        item = {"sha": "abc123"}
        should_skip, reason = filter.should_skip_item(item)
        assert not should_skip
        
        filter.add_scanned_sha("abc123")
        should_skip, reason = filter.should_skip_item(item)
        assert should_skip
        assert reason == "sha_duplicate"
        
        # 测试文档过滤
        item = {"sha": "def456", "path": "README.md"}
        should_skip, reason = filter.should_skip_item(item)
        assert should_skip
        assert reason == "doc_filter"
        
        # 测试仓库年龄过滤
        old_date = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        item = {
            "sha": "ghi789",
            "path": "config.py",
            "repository": {"pushed_at": old_date}
        }
        should_skip, reason = filter.should_skip_item(item)
        assert should_skip
        assert reason == "age_filter"
    
    def test_scan_result(self):
        """测试扫描结果数据类"""
        result = ScanResult(query="test query")
        
        # 测试添加有效密钥
        result.add_valid_key("key1")
        result.add_valid_key("key2")
        result.add_valid_key("key1")  # 重复
        assert len(result.valid_keys) == 2
        
        # 测试添加限流密钥
        result.add_rate_limited_key("key3")
        assert len(result.rate_limited_keys) == 1
        
        # 测试合并结果
        other = ScanResult(query="other query")
        other.total_items = 10
        other.processed_items = 5
        other.add_valid_key("key4")
        
        result.merge(other)
        assert result.total_items == 10
        assert result.processed_items == 5
        assert len(result.valid_keys) == 3
    
    def test_skip_stats(self):
        """测试跳过统计"""
        self.scanner.reset_skip_stats()
        assert all(v == 0 for v in self.scanner.skip_stats.values())
        
        # 模拟跳过
        self.scanner.skip_stats["time_filter"] = 5
        self.scanner.skip_stats["sha_duplicate"] = 3
        
        summary = self.scanner.get_skip_stats_summary()
        assert "8 items" in summary
        assert "time_filter: 5" in summary
        assert "sha_duplicate: 3" in summary


class TestScanFilter:
    """扫描过滤器测试类"""
    
    def test_processed_queries(self):
        """测试已处理查询管理"""
        filter = ScanFilter()
        
        # 添加查询
        filter.add_processed_query("query1")
        filter.add_processed_query("query2")
        
        assert "query1" in filter.processed_queries
        assert "query2" in filter.processed_queries
        assert "query3" not in filter.processed_queries
    
    def test_scan_time_update(self):
        """测试扫描时间更新"""
        filter = ScanFilter()
        assert filter.last_scan_time is None
        
        filter.update_scan_time()
        assert filter.last_scan_time is not None
        assert isinstance(filter.last_scan_time, datetime)
        
        # 测试时间过滤
        item = {
            "repository": {
                "pushed_at": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        }
        
        should_skip, reason = filter.should_skip_item(item)
        assert should_skip
        assert reason == "time_filter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])