"""
统一统计模型 - 单一真相源
解决统计口径不一致问题
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from collections import Counter
from typing import Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path


class KeyStatus(Enum):
    """密钥状态枚举 - 互斥分类"""
    INVALID = auto()
    RATE_LIMITED = auto()
    VALID_FREE = auto()
    VALID_PAID = auto()


@dataclass
class RunStats:
    """
    运行统计 - 单一真相源
    所有统计数据的唯一来源，避免口径漂移
    """
    run_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # 密钥统计 - 使用互斥分类
    by_status: Counter = field(default_factory=Counter)
    
    # 密钥集合 - 用于去重和详细记录
    keys_by_status: Dict[KeyStatus, set] = field(default_factory=lambda: {
        KeyStatus.INVALID: set(),
        KeyStatus.RATE_LIMITED: set(),
        KeyStatus.VALID_FREE: set(),
        KeyStatus.VALID_PAID: set()
    })
    
    # 处理统计
    items_processed: int = 0
    queries_planned: int = 0
    queries_completed: int = 0
    queries_failed: int = 0
    
    # 错误统计
    errors: int = 0
    error_details: list = field(default_factory=list)
    
    # 数据质量统计
    pages_attempted: int = 0
    pages_successful: int = 0
    expected_items: int = 0
    actual_items: int = 0
    
    # GitHub API 统计
    github_requests_total: int = 0
    github_rate_limit_hits: int = 0
    
    def mark_key(self, key: str, status: KeyStatus) -> None:
        """
        标记密钥状态（确保互斥）
        
        Args:
            key: 密钥
            status: 新状态
        """
        # 从其他状态集合中移除（确保互斥）
        for s in KeyStatus:
            if s != status and key in self.keys_by_status[s]:
                self.keys_by_status[s].remove(key)
                self.by_status[s] -= 1
        
        # 添加到新状态
        if key not in self.keys_by_status[status]:
            self.keys_by_status[status].add(key)
            self.by_status[status] += 1
    
    def update_key_status(self, key: str, old_status: Optional[KeyStatus], new_status: KeyStatus) -> None:
        """
        更新密钥状态（例如从 RATE_LIMITED 变为 VALID_FREE）
        
        Args:
            key: 密钥
            old_status: 旧状态（可选）
            new_status: 新状态
        """
        if old_status and key in self.keys_by_status[old_status]:
            self.keys_by_status[old_status].remove(key)
            self.by_status[old_status] -= 1
        
        if key not in self.keys_by_status[new_status]:
            self.keys_by_status[new_status].add(key)
            self.by_status[new_status] += 1
    
    def add_error(self, error_type: str, error_msg: str, context: Optional[Dict] = None) -> None:
        """
        记录错误详情
        
        Args:
            error_type: 错误类型
            error_msg: 错误消息
            context: 上下文信息
        """
        self.errors += 1
        self.error_details.append({
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_msg,
            "context": context or {}
        })
    
    def mark_query_complete(self, success: bool = True) -> None:
        """标记查询完成"""
        if success:
            self.queries_completed += 1
        else:
            self.queries_failed += 1
    
    def update_data_quality(self, expected: int, actual: int) -> None:
        """更新数据质量统计"""
        self.expected_items += expected
        self.actual_items += actual
    
    @property
    def data_loss_ratio(self) -> float:
        """计算数据丢失率"""
        if self.expected_items == 0:
            return 0.0
        return 1.0 - (self.actual_items / self.expected_items)
    
    @property
    def query_success_rate(self) -> float:
        """计算查询成功率"""
        total = self.queries_completed + self.queries_failed
        if total == 0:
            return 0.0
        return self.queries_completed / total
    
    @property
    def page_success_rate(self) -> float:
        """计算页面成功率"""
        if self.pages_attempted == 0:
            return 0.0
        return self.pages_successful / self.pages_attempted
    
    def summary(self) -> Dict[str, Any]:
        """
        生成统计摘要（单一口径）
        这是所有输出的唯一数据源
        
        Returns:
            统计摘要字典
        """
        # 计算导出指标
        valid_total = self.by_status[KeyStatus.VALID_FREE] + self.by_status[KeyStatus.VALID_PAID]
        
        # 计算运行时长
        if self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        else:
            duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            # 运行信息
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            
            # 查询统计
            "queries": {
                "planned": self.queries_planned,
                "completed": self.queries_completed,
                "failed": self.queries_failed,
                "success_rate": f"{self.query_success_rate:.1%}"
            },
            
            # 处理统计
            "processing": {
                "items_processed": self.items_processed,
                "pages_attempted": self.pages_attempted,
                "pages_successful": self.pages_successful,
                "page_success_rate": f"{self.page_success_rate:.1%}"
            },
            
            # 密钥统计（核心指标）
            "keys": {
                "valid_total": valid_total,
                "valid_free": self.by_status[KeyStatus.VALID_FREE],
                "valid_paid": self.by_status[KeyStatus.VALID_PAID],
                "rate_limited": self.by_status[KeyStatus.RATE_LIMITED],
                "invalid": self.by_status[KeyStatus.INVALID]
            },
            
            # 数据质量
            "data_quality": {
                "expected_items": self.expected_items,
                "actual_items": self.actual_items,
                "data_loss_ratio": f"{self.data_loss_ratio:.1%}"
            },
            
            # GitHub API 统计
            "github_api": {
                "requests_total": self.github_requests_total,
                "rate_limit_hits": self.github_rate_limit_hits
            },
            
            # 错误统计
            "errors": {
                "total": self.errors,
                "recent": self.error_details[-5:] if self.error_details else []
            }
        }
    
    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.summary(), ensure_ascii=False, indent=indent)
    
    def to_markdown(self) -> str:
        """
        生成 Markdown 格式报告
        
        Returns:
            Markdown 格式的报告
        """
        summary = self.summary()
        
        md = f"""# 运行报告 ({self.run_id})

## 📊 概览
- **开始时间**: {summary['start_time']}
- **结束时间**: {summary['end_time'] or '运行中...'}
- **运行时长**: {summary['duration_seconds']:.1f} 秒

## 🔍 查询统计
- **计划查询**: {summary['queries']['planned']}
- **完成查询**: {summary['queries']['completed']}
- **失败查询**: {summary['queries']['failed']}
- **成功率**: {summary['queries']['success_rate']}

## 📈 处理统计
- **处理项目**: {summary['processing']['items_processed']}
- **尝试页面**: {summary['processing']['pages_attempted']}
- **成功页面**: {summary['processing']['pages_successful']}
- **页面成功率**: {summary['processing']['page_success_rate']}

## 🔑 密钥统计（互斥分类）
| 类型 | 数量 | 说明 |
|------|------|------|
| **有效总计** | {summary['keys']['valid_total']} | VALID_FREE + VALID_PAID |
| 免费版 | {summary['keys']['valid_free']} | 验证通过的免费密钥 |
| 付费版 | {summary['keys']['valid_paid']} | 验证通过的付费密钥 |
| 限流中 | {summary['keys']['rate_limited']} | 暂时限流（不计入有效） |
| 无效 | {summary['keys']['invalid']} | 验证失败的密钥 |

## 📉 数据质量
- **预期项目**: {summary['data_quality']['expected_items']}
- **实际项目**: {summary['data_quality']['actual_items']}
- **数据丢失率**: {summary['data_quality']['data_loss_ratio']}

## 🌐 GitHub API
- **总请求数**: {summary['github_api']['requests_total']}
- **限流次数**: {summary['github_api']['rate_limit_hits']}

## ❌ 错误统计
- **错误总数**: {summary['errors']['total']}
"""
        
        if summary['errors']['recent']:
            md += "\n### 最近错误\n"
            for error in summary['errors']['recent']:
                md += f"- [{error['timestamp']}] {error['type']}: {error['message']}\n"
        
        return md
    
    def finalize(self) -> None:
        """完成统计，记录结束时间"""
        self.end_time = datetime.now()
    
    def get_keys_list(self, status: KeyStatus) -> list:
        """
        获取指定状态的密钥列表
        
        Args:
            status: 密钥状态
            
        Returns:
            密钥列表
        """
        return sorted(list(self.keys_by_status[status]))
    
    def get_all_valid_keys(self) -> list:
        """获取所有有效密钥（免费+付费）"""
        return sorted(
            list(self.keys_by_status[KeyStatus.VALID_FREE]) +
            list(self.keys_by_status[KeyStatus.VALID_PAID])
        )


class StatsManager:
    """统计管理器 - 负责统计的持久化和加载"""
    
    def __init__(self, data_dir: Path):
        """
        初始化统计管理器
        
        Args:
            data_dir: 数据目录
        """
        self.data_dir = data_dir
        self.current_stats: Optional[RunStats] = None
    
    def create_run(self) -> RunStats:
        """创建新的运行统计"""
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_stats = RunStats(run_id=run_id)
        return self.current_stats
    
    def save_checkpoint(self, stats: RunStats) -> Path:
        """
        保存统计检查点
        
        Args:
            stats: 统计对象
            
        Returns:
            检查点文件路径
        """
        run_dir = self.data_dir / "runs" / stats.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_file = run_dir / "checkpoint.json"
        
        # 保存完整状态（包括密钥集合）
        checkpoint_data = {
            "summary": stats.summary(),
            "keys_by_status": {
                status.name: list(keys)
                for status, keys in stats.keys_by_status.items()
            }
        }
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        
        return checkpoint_file
    
    def load_checkpoint(self, run_id: str) -> Optional[RunStats]:
        """
        加载统计检查点
        
        Args:
            run_id: 运行ID
            
        Returns:
            统计对象或None
        """
        checkpoint_file = self.data_dir / "runs" / run_id / "checkpoint.json"
        
        if not checkpoint_file.exists():
            return None
        
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建统计对象
        stats = RunStats(run_id=run_id)
        
        # 恢复密钥集合
        if "keys_by_status" in data:
            for status_name, keys in data["keys_by_status"].items():
                status = KeyStatus[status_name]
                stats.keys_by_status[status] = set(keys)
                stats.by_status[status] = len(keys)
        
        # 恢复其他统计数据
        summary = data.get("summary", {})
        stats.items_processed = summary.get("processing", {}).get("items_processed", 0)
        stats.queries_planned = summary.get("queries", {}).get("planned", 0)
        stats.queries_completed = summary.get("queries", {}).get("completed", 0)
        stats.queries_failed = summary.get("queries", {}).get("failed", 0)
        stats.errors = summary.get("errors", {}).get("total", 0)
        
        return stats