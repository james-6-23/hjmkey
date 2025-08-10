"""
文件工具模块 - 原子写入、路径管理、运行目录组织
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PathManager:
    """统一路径管理器"""
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化路径管理器
        
        Args:
            project_root: 项目根目录（默认自动检测）
        """
        if project_root is None:
            # 从当前文件位置推导项目根目录
            # utils/file_utils.py -> project_root
            self.project_root = Path(__file__).resolve().parent.parent
        else:
            self.project_root = Path(project_root).resolve()
        
        # 数据根目录
        self.data_root = self.project_root / "data"
        
        # 确保数据目录存在
        self.data_root.mkdir(parents=True, exist_ok=True)
        
        # 当前运行目录（需要通过 set_run_id 设置）
        self.current_run_id: Optional[str] = None
        self.current_run_dir: Optional[Path] = None
        
        logger.info(f"📁 Path manager initialized")
        logger.info(f"   Project root: {self.project_root}")
        logger.info(f"   Data root: {self.data_root}")
    
    def generate_run_id(self) -> str:
        """
        生成运行ID
        格式: YYYYMMDD_HHMMSS_XXXX (XXXX为4位随机数)
        
        Returns:
            运行ID
        """
        import random
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = f"{random.randint(1000, 9999)}"
        return f"{timestamp}_{random_suffix}"
    
    def set_run_id(self, run_id: Optional[str] = None) -> str:
        """
        设置当前运行ID
        
        Args:
            run_id: 运行ID（None则自动生成）
            
        Returns:
            运行ID
        """
        if run_id is None:
            run_id = self.generate_run_id()
        
        self.current_run_id = run_id
        self.current_run_dir = self.data_root / "runs" / run_id
        
        # 创建运行目录结构
        self._create_run_directories()
        
        # 更新 latest 软链接
        self._update_latest_link()
        
        logger.info(f"🏃 Run ID set: {run_id}")
        logger.info(f"   Run directory: {self.current_run_dir}")
        
        return run_id
    
    def _create_run_directories(self) -> None:
        """创建运行目录结构"""
        if not self.current_run_dir:
            raise ValueError("Run ID not set")
        
        # 主目录
        self.current_run_dir.mkdir(parents=True, exist_ok=True)
        
        # 子目录
        subdirs = [
            "artifacts",      # 中间产物
            "secrets",        # 敏感数据（严格权限）
            "logs",          # 日志文件
            "checkpoints",   # 检查点
            "reports"        # 报告
        ]
        
        for subdir in subdirs:
            (self.current_run_dir / subdir).mkdir(exist_ok=True)
        
        # 设置 secrets 目录权限（仅 Unix）
        if os.name == 'posix':
            os.chmod(self.current_run_dir / "secrets", 0o700)
    
    def _update_latest_link(self) -> None:
        """更新 latest 软链接指向当前运行"""
        if not self.current_run_dir:
            return
        
        latest_link = self.data_root / "latest"
        
        # 删除旧链接
        if latest_link.exists() or latest_link.is_symlink():
            if latest_link.is_symlink():
                latest_link.unlink()
            elif latest_link.is_dir():
                shutil.rmtree(latest_link)
        
        # 创建新链接（Windows 需要管理员权限，使用目录连接）
        try:
            if os.name == 'nt':
                # Windows: 使用目录连接或复制路径文件
                latest_file = self.data_root / "latest.txt"
                with open(latest_file, 'w') as f:
                    f.write(str(self.current_run_dir))
            else:
                # Unix: 使用符号链接
                latest_link.symlink_to(self.current_run_dir.relative_to(self.data_root))
        except Exception as e:
            logger.warning(f"Could not create latest link: {e}")
    
    def get_run_dir(self, run_id: Optional[str] = None) -> Path:
        """
        获取运行目录
        
        Args:
            run_id: 运行ID（None使用当前）
            
        Returns:
            运行目录路径
        """
        if run_id:
            return self.data_root / "runs" / run_id
        elif self.current_run_dir:
            return self.current_run_dir
        else:
            raise ValueError("No run ID set or provided")
    
    def get_artifact_path(self, filename: str, run_id: Optional[str] = None) -> Path:
        """获取中间产物路径"""
        return self.get_run_dir(run_id) / "artifacts" / filename
    
    def get_secret_path(self, filename: str, run_id: Optional[str] = None) -> Path:
        """获取敏感数据路径"""
        return self.get_run_dir(run_id) / "secrets" / filename
    
    def get_report_path(self, filename: str, run_id: Optional[str] = None) -> Path:
        """获取报告路径"""
        return self.get_run_dir(run_id) / "reports" / filename
    
    def get_checkpoint_path(self, filename: str, run_id: Optional[str] = None) -> Path:
        """获取检查点路径"""
        return self.get_run_dir(run_id) / "checkpoints" / filename
    
    def get_log_path(self, filename: str, run_id: Optional[str] = None) -> Path:
        """获取日志路径"""
        return self.get_run_dir(run_id) / "logs" / filename
    
    def list_runs(self) -> list:
        """
        列出所有运行
        
        Returns:
            运行ID列表（按时间排序）
        """
        runs_dir = self.data_root / "runs"
        if not runs_dir.exists():
            return []
        
        runs = [d.name for d in runs_dir.iterdir() if d.is_dir()]
        return sorted(runs, reverse=True)  # 最新的在前
    
    def get_latest_run_id(self) -> Optional[str]:
        """获取最新的运行ID"""
        runs = self.list_runs()
        return runs[0] if runs else None


class AtomicFileWriter:
    """原子文件写入器"""
    
    @staticmethod
    def write_text(path: Union[str, Path], content: str, encoding: str = 'utf-8') -> Path:
        """
        原子写入文本文件
        
        Args:
            path: 文件路径
            content: 文件内容
            encoding: 编码
            
        Returns:
            文件路径
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            delete=False,
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix='.tmp'
        ) as tf:
            tf.write(content)
            temp_path = Path(tf.name)
        
        # 原子替换
        try:
            # Windows 需要先删除目标文件
            if os.name == 'nt' and path.exists():
                path.unlink()
            os.replace(temp_path, path)
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise e
        
        logger.debug(f"Atomically wrote {len(content)} bytes to {path}")
        return path
    
    @staticmethod
    def write_json(path: Union[str, Path], data: Any, 
                   indent: int = 2, ensure_ascii: bool = False) -> Path:
        """
        原子写入 JSON 文件
        
        Args:
            path: 文件路径
            data: 数据对象
            indent: 缩进
            ensure_ascii: 是否转义非ASCII字符
            
        Returns:
            文件路径
        """
        content = json.dumps(data, indent=indent, ensure_ascii=ensure_ascii)
        return AtomicFileWriter.write_text(path, content)
    
    @staticmethod
    def write_lines(path: Union[str, Path], lines: list, encoding: str = 'utf-8') -> Path:
        """
        原子写入多行文本
        
        Args:
            path: 文件路径
            lines: 行列表
            encoding: 编码
            
        Returns:
            文件路径
        """
        content = '\n'.join(str(line) for line in lines)
        if lines and not content.endswith('\n'):
            content += '\n'
        return AtomicFileWriter.write_text(path, content, encoding)
    
    @staticmethod
    def append_line(path: Union[str, Path], line: str, encoding: str = 'utf-8') -> Path:
        """
        原子追加行（读取-修改-写入）
        
        Args:
            path: 文件路径
            line: 要追加的行
            encoding: 编码
            
        Returns:
            文件路径
        """
        path = Path(path)
        
        # 读取现有内容
        if path.exists():
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
        else:
            content = ""
        
        # 追加新行
        if content and not content.endswith('\n'):
            content += '\n'
        content += line
        if not content.endswith('\n'):
            content += '\n'
        
        # 原子写入
        return AtomicFileWriter.write_text(path, content, encoding)


class RunArtifactManager:
    """运行产物管理器"""
    
    def __init__(self, path_manager: PathManager):
        """
        初始化产物管理器
        
        Args:
            path_manager: 路径管理器
        """
        self.path_manager = path_manager
        self.writer = AtomicFileWriter()
    
    def save_final_report(self, stats_summary: Dict[str, Any]) -> Dict[str, Path]:
        """
        保存最终报告（JSON + Markdown）
        
        Args:
            stats_summary: 统计摘要
            
        Returns:
            保存的文件路径字典
        """
        saved_files = {}
        
        # JSON 报告
        json_path = self.path_manager.get_report_path("final_report.json")
        self.writer.write_json(json_path, stats_summary)
        saved_files['json'] = json_path
        
        # Markdown 报告
        md_content = self._generate_markdown_report(stats_summary)
        md_path = self.path_manager.get_report_path("final_report.md")
        self.writer.write_text(md_path, md_content)
        saved_files['markdown'] = md_path
        
        logger.info(f"📊 Final reports saved:")
        logger.info(f"   JSON: {json_path}")
        logger.info(f"   Markdown: {md_path}")
        
        return saved_files
    
    def _generate_markdown_report(self, summary: Dict[str, Any]) -> str:
        """生成 Markdown 报告"""
        md = f"""# 最终报告 - {summary.get('run_id', 'Unknown')}

## 📅 运行信息
- **开始时间**: {summary.get('start_time', 'N/A')}
- **结束时间**: {summary.get('end_time', 'N/A')}
- **运行时长**: {summary.get('duration_seconds', 0):.1f} 秒

## 🔍 查询统计
- **计划/完成/失败**: {summary['queries']['planned']}/{summary['queries']['completed']}/{summary['queries']['failed']}
- **成功率**: {summary['queries']['success_rate']}

## 🔑 密钥统计
| 类型 | 数量 |
|------|------|
| **有效总计** | {summary['keys']['valid_total']} |
| 免费版 | {summary['keys']['valid_free']} |
| 付费版 | {summary['keys']['valid_paid']} |
| 限流中 | {summary['keys']['rate_limited']} |
| 无效 | {summary['keys']['invalid']} |

## 📊 数据质量
- **数据丢失率**: {summary['data_quality']['data_loss_ratio']}
- **实际/预期**: {summary['data_quality']['actual_items']}/{summary['data_quality']['expected_items']}

## ⚠️ 错误
- **总计**: {summary['errors']['total']}
"""
        
        if summary['errors']['recent']:
            md += "\n### 最近错误\n"
            for error in summary['errors']['recent']:
                md += f"- `{error['type']}`: {error['message']}\n"
        
        return md
    
    def save_artifact(self, filename: str, content: Union[str, Dict, list]) -> Path:
        """
        保存中间产物
        
        Args:
            filename: 文件名
            content: 内容
            
        Returns:
            文件路径
        """
        path = self.path_manager.get_artifact_path(filename)
        
        if isinstance(content, (dict, list)):
            self.writer.write_json(path, content)
        else:
            self.writer.write_text(path, str(content))
        
        logger.debug(f"Saved artifact: {path}")
        return path
    
    def save_checkpoint(self, checkpoint_data: Dict[str, Any]) -> Path:
        """
        保存检查点
        
        Args:
            checkpoint_data: 检查点数据
            
        Returns:
            检查点文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"checkpoint_{timestamp}.json"
        path = self.path_manager.get_checkpoint_path(filename)
        
        self.writer.write_json(path, checkpoint_data)
        
        # 清理旧检查点（保留最近5个）
        self._cleanup_old_checkpoints()
        
        logger.info(f"💾 Checkpoint saved: {path}")
        return path
    
    def _cleanup_old_checkpoints(self, keep_count: int = 5) -> None:
        """清理旧检查点"""
        checkpoint_dir = self.path_manager.get_checkpoint_path("")
        if not checkpoint_dir.exists():
            return
        
        checkpoints = sorted(checkpoint_dir.glob("checkpoint_*.json"))
        if len(checkpoints) > keep_count:
            for old_checkpoint in checkpoints[:-keep_count]:
                old_checkpoint.unlink()
                logger.debug(f"Deleted old checkpoint: {old_checkpoint.name}")


# 全局实例
_path_manager: Optional[PathManager] = None


def get_path_manager() -> PathManager:
    """获取全局路径管理器"""
    global _path_manager
    if _path_manager is None:
        _path_manager = PathManager()
    return _path_manager


# 使用示例
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # 初始化路径管理器
    pm = PathManager()
    run_id = pm.set_run_id()
    
    # 原子写入测试
    writer = AtomicFileWriter()
    
    # 写入文本
    test_file = pm.get_artifact_path("test.txt")
    writer.write_text(test_file, "Hello, World!")
    
    # 写入 JSON
    test_json = pm.get_artifact_path("test.json")
    writer.write_json(test_json, {"status": "success", "count": 42})
    
    # 产物管理器测试
    artifact_mgr = RunArtifactManager(pm)
    
    # 保存最终报告
    test_summary = {
        "run_id": run_id,
        "start_time": datetime.now().isoformat(),
        "queries": {"planned": 10, "completed": 8, "failed": 2, "success_rate": "80.0%"},
        "keys": {"valid_total": 15, "valid_free": 10, "valid_paid": 5, "rate_limited": 3, "invalid": 7},
        "data_quality": {"expected_items": 1000, "actual_items": 850, "data_loss_ratio": "15.0%"},
        "errors": {"total": 2, "recent": []}
    }
    
    artifact_mgr.save_final_report(test_summary)
    
    print(f"✅ Test completed. Check: {pm.current_run_dir}")