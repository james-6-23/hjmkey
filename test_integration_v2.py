"""
集成测试脚本 - 验证 V2 优化组件
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

# 导入所有新组件
from app.core.stats import RunStats, KeyStatus, StatsManager
from app.core.graceful_shutdown import (
    GracefulShutdownManager, 
    OrchestratorState, 
    StateMachine
)
from utils.file_utils import PathManager, AtomicFileWriter, RunArtifactManager
from utils.security_utils import (
    mask_key, 
    SecureKeyStorage, 
    setup_secure_logging,
    validate_environment,
    compute_hmac
)
from utils.token_pool import TokenPool, TokenSelectionStrategy, TokenMetrics
from utils.github_client_v2 import create_github_client_v2

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationTestSuite:
    """集成测试套件"""
    
    def __init__(self):
        self.test_results = {}
        self.passed = 0
        self.failed = 0
        
    def run_test(self, test_name: str, test_func):
        """运行单个测试"""
        try:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Running test: {test_name}")
            logger.info(f"{'='*60}")
            
            result = test_func()
            
            if result:
                self.passed += 1
                self.test_results[test_name] = "PASSED"
                logger.info(f"✅ {test_name}: PASSED")
            else:
                self.failed += 1
                self.test_results[test_name] = "FAILED"
                logger.error(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            self.failed += 1
            self.test_results[test_name] = f"ERROR: {e}"
            logger.error(f"💥 {test_name}: ERROR - {e}")
    
    def print_summary(self):
        """打印测试摘要"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 TEST SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total: {self.passed + self.failed}")
        logger.info(f"Passed: {self.passed} ✅")
        logger.info(f"Failed: {self.failed} ❌")
        logger.info(f"Success Rate: {(self.passed/(self.passed+self.failed)*100):.1f}%")
        logger.info(f"{'='*60}")
        
        for test_name, result in self.test_results.items():
            status_icon = "✅" if result == "PASSED" else "❌"
            logger.info(f"{status_icon} {test_name}: {result}")


def test_stats_model():
    """测试统一统计模型"""
    logger.info("Testing RunStats and KeyStatus...")
    
    # 创建统计实例
    stats = RunStats(run_id="test_run_001")
    
    # 测试互斥分类
    test_key = "AIzaSyBxZJpQpK0H4lI7YkVr_lZdj9Ns8VYK1co"
    
    # 标记为 INVALID
    stats.mark_key(test_key, KeyStatus.INVALID)
    assert stats.by_status[KeyStatus.INVALID] == 1
    
    # 更新为 VALID_FREE（应该从 INVALID 中移除）
    stats.mark_key(test_key, KeyStatus.VALID_FREE)
    assert stats.by_status[KeyStatus.INVALID] == 0
    assert stats.by_status[KeyStatus.VALID_FREE] == 1
    
    # 再更新为 VALID_PAID
    stats.mark_key(test_key, KeyStatus.VALID_PAID)
    assert stats.by_status[KeyStatus.VALID_FREE] == 0
    assert stats.by_status[KeyStatus.VALID_PAID] == 1
    
    # 测试统计摘要
    summary = stats.summary()
    assert summary['keys']['valid_total'] == 1
    assert summary['keys']['valid_paid'] == 1
    assert summary['keys']['valid_free'] == 0
    
    logger.info("  ✓ KeyStatus mutual exclusion works")
    logger.info("  ✓ RunStats summary generation works")
    
    return True


def test_security_utils():
    """测试安全工具"""
    logger.info("Testing security utilities...")
    
    # 测试密钥脱敏
    test_key = "AIzaSyBxZJpQpK0H4lI7YkVr_lZdj9Ns8VYK1co"
    masked = mask_key(test_key)
    assert masked == "AIzaSy…1co"
    assert test_key not in masked
    logger.info(f"  ✓ Key masking: {test_key} -> {masked}")
    
    # 测试 HMAC
    hmac1 = compute_hmac(test_key)
    hmac2 = compute_hmac(test_key)
    assert hmac1 == hmac2  # 相同输入应该产生相同输出
    assert len(hmac1) == 64  # SHA256 产生 64 个十六进制字符
    logger.info(f"  ✓ HMAC generation: {hmac1[:16]}...")
    
    # 测试环境验证
    is_valid = validate_environment()
    logger.info(f"  ✓ Environment validation: {'Valid' if is_valid else 'Has warnings'}")
    
    return True


def test_file_utils():
    """测试文件工具"""
    logger.info("Testing file utilities...")
    
    # 测试路径管理器
    pm = PathManager()
    run_id = pm.set_run_id("test_run_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    
    assert pm.current_run_id == run_id
    assert pm.current_run_dir.exists()
    logger.info(f"  ✓ PathManager initialized: {run_id}")
    
    # 测试原子写入
    writer = AtomicFileWriter()
    test_file = pm.get_artifact_path("test_atomic.txt")
    test_content = "This is a test content"
    
    writer.write_text(test_file, test_content)
    assert test_file.exists()
    assert test_file.read_text() == test_content
    logger.info(f"  ✓ Atomic write successful")
    
    # 测试 JSON 写入
    test_json = pm.get_artifact_path("test_data.json")
    test_data = {"status": "success", "count": 42}
    
    writer.write_json(test_json, test_data)
    assert test_json.exists()
    loaded_data = json.loads(test_json.read_text())
    assert loaded_data == test_data
    logger.info(f"  ✓ JSON atomic write successful")
    
    # 清理测试文件
    import shutil
    if pm.current_run_dir.exists():
        shutil.rmtree(pm.current_run_dir)
    
    return True


def test_graceful_shutdown():
    """测试优雅停机"""
    logger.info("Testing graceful shutdown...")
    
    # 创建状态机
    sm = StateMachine(OrchestratorState.IDLE)
    
    # 测试状态转换
    assert sm.state == OrchestratorState.IDLE
    
    # 允许的转换
    success = sm.transition_to(OrchestratorState.INITIALIZING)
    assert success
    assert sm.state == OrchestratorState.INITIALIZING
    
    success = sm.transition_to(OrchestratorState.SCANNING)
    assert success
    assert sm.state == OrchestratorState.SCANNING
    
    # 不允许的转换（SCANNING 不能直接到 STOPPED）
    success = sm.transition_to(OrchestratorState.STOPPED)
    assert not success  # 应该失败
    assert sm.state == OrchestratorState.SCANNING  # 状态不变
    
    # 强制转换
    success = sm.transition_to(OrchestratorState.STOPPED, force=True)
    assert success
    assert sm.state == OrchestratorState.STOPPED
    
    logger.info("  ✓ State machine transitions work correctly")
    
    # 测试停机管理器
    shutdown_mgr = GracefulShutdownManager(StateMachine())
    
    # 注册回调
    cleanup_called = False
    finalize_called = False
    
    def cleanup_callback():
        nonlocal cleanup_called
        cleanup_called = True
    
    def finalize_callback():
        nonlocal finalize_called
        finalize_called = True
    
    shutdown_mgr.register_cleanup(cleanup_callback)
    shutdown_mgr.register_finalize(finalize_callback)
    
    # 执行停机（同步版本）
    async def test_shutdown():
        await shutdown_mgr.shutdown(timeout=1.0)
    
    asyncio.run(test_shutdown())
    
    assert cleanup_called
    assert finalize_called
    assert shutdown_mgr.state_machine.state == OrchestratorState.STOPPED
    
    logger.info("  ✓ Graceful shutdown callbacks work")
    
    return True


def test_token_pool():
    """测试 TokenPool"""
    logger.info("Testing TokenPool...")
    
    # 创建测试令牌
    test_tokens = [
        "token_001_" + "A" * 50,
        "token_002_" + "B" * 50,
        "token_003_" + "C" * 50,
    ]
    
    # 创建池
    pool = TokenPool(test_tokens, strategy=TokenSelectionStrategy.ROUND_ROBIN)
    
    # 测试轮询选择
    selected_tokens = []
    for _ in range(6):  # 选择6次，应该循环2轮
        token = pool.select_token()
        assert token is not None
        selected_tokens.append(token)
    
    # 验证轮询
    assert selected_tokens[0] == selected_tokens[3]  # 第1次和第4次应该相同
    assert selected_tokens[1] == selected_tokens[4]  # 第2次和第5次应该相同
    logger.info("  ✓ Round-robin selection works")
    
    # 测试健康分数
    pool.metrics[test_tokens[0]].record_success(response_time=0.5)
    pool.metrics[test_tokens[1]].record_failure("test error")
    
    health_0 = pool.metrics[test_tokens[0]].health_score
    health_1 = pool.metrics[test_tokens[1]].health_score
    
    assert health_0 > health_1  # 成功的应该有更高的健康分数
    logger.info(f"  ✓ Health scoring works: {health_0:.1f} > {health_1:.1f}")
    
    # 测试配额更新
    pool.metrics[test_tokens[2]].update_quota(0, int(datetime.now().timestamp()) + 3600)
    assert pool.metrics[test_tokens[2]].status.name == "EXHAUSTED"
    logger.info("  ✓ Quota tracking works")
    
    # 测试池状态
    status = pool.get_pool_status()
    assert status['total_tokens'] == 3
    assert status['exhausted'] == 1
    logger.info(f"  ✓ Pool status: {status['healthy']} healthy, {status['exhausted']} exhausted")
    
    return True


def test_github_client_v2():
    """测试 GitHub 客户端 V2"""
    logger.info("Testing GitHub Client V2...")
    
    # 创建测试令牌（模拟）
    test_tokens = [
        "test_token_001",
        "test_token_002",
    ]
    
    # 创建客户端
    client = create_github_client_v2(test_tokens, strategy="ADAPTIVE")
    
    # 验证初始化
    assert client.token_pool is not None
    assert len(client.token_pool.tokens) == 2
    logger.info("  ✓ Client initialized with TokenPool")
    
    # 获取统计
    stats = client.get_statistics()
    assert 'token_pool_status' in stats
    assert stats['total_requests'] == 0
    logger.info("  ✓ Statistics tracking works")
    
    # 关闭客户端
    client.close()
    logger.info("  ✓ Client closed successfully")
    
    return True


async def test_integration_flow():
    """测试完整的集成流程"""
    logger.info("Testing complete integration flow...")
    
    # 1. 初始化路径管理
    pm = PathManager()
    run_id = pm.set_run_id()
    logger.info(f"  ✓ Run initialized: {run_id}")
    
    # 2. 初始化统计
    stats = RunStats(run_id=run_id)
    stats.queries_planned = 3
    
    # 3. 初始化停机管理
    shutdown_mgr = GracefulShutdownManager()
    
    # 4. 模拟处理
    test_keys = [
        "key1_invalid",
        "key2_valid_free",
        "key3_valid_paid",
        "key4_rate_limited"
    ]
    
    stats.mark_key(test_keys[0], KeyStatus.INVALID)
    stats.mark_key(test_keys[1], KeyStatus.VALID_FREE)
    stats.mark_key(test_keys[2], KeyStatus.VALID_PAID)
    stats.mark_key(test_keys[3], KeyStatus.RATE_LIMITED)
    
    # 5. 生成报告
    stats.finalize()
    summary = stats.summary()
    
    # 6. 保存报告（原子写入）
    artifact_mgr = RunArtifactManager(pm)
    saved_files = artifact_mgr.save_final_report(summary)
    
    assert saved_files['json'].exists()
    assert saved_files['markdown'].exists()
    logger.info("  ✓ Reports saved atomically")
    
    # 7. 安全存储密钥
    secure_storage = SecureKeyStorage(pm.current_run_dir, allow_plaintext=False)
    keys_by_status = {
        KeyStatus.VALID_FREE.name: [test_keys[1]],
        KeyStatus.VALID_PAID.name: [test_keys[2]],
    }
    secure_storage.save_keys(keys_by_status)
    logger.info("  ✓ Keys saved securely")
    
    # 8. 执行停机
    await shutdown_mgr.shutdown(timeout=1.0)
    assert shutdown_mgr.state_machine.state == OrchestratorState.STOPPED
    logger.info("  ✓ Graceful shutdown completed")
    
    # 清理
    import shutil
    if pm.current_run_dir.exists():
        shutil.rmtree(pm.current_run_dir)
    
    return True


def main():
    """主测试函数"""
    logger.info("\n" + "="*60)
    logger.info("🧪 HAJIMI KING V2.0 - INTEGRATION TEST SUITE")
    logger.info("="*60)
    
    # 创建测试套件
    suite = IntegrationTestSuite()
    
    # 运行各个测试
    suite.run_test("Stats Model", test_stats_model)
    suite.run_test("Security Utils", test_security_utils)
    suite.run_test("File Utils", test_file_utils)
    suite.run_test("Graceful Shutdown", test_graceful_shutdown)
    suite.run_test("Token Pool", test_token_pool)
    suite.run_test("GitHub Client V2", test_github_client_v2)
    
    # 运行异步集成测试
    suite.run_test("Integration Flow", lambda: asyncio.run(test_integration_flow()))
    
    # 打印摘要
    suite.print_summary()
    
    # 返回状态码
    return 0 if suite.failed == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)