# 摘要（TL;DR）

- **统计口径不一致**、**异步停止不彻底**、**功能模块在无事件循环下初始化**、**输出路径混乱**、**明文泄露敏感密钥**、**GitHub 搜索数据丢失严重** 是当前最主要的问题。
- 采用**单一状态机+互斥分类**、**原子化写文件**、**优雅停机（graceful shutdown）**、**统一路径与 run\_id**、**日志脱敏与权限控制**、**按令牌池自适应速率限制**，即可明显稳定产出并降低风险。
- 附：可直接落地的代码框架与清单（见“代码级改造要点”“测试清单”）。

---

# 1. 发现的问题与影响

## 1.1 统计与输出不一致

- 终端“FINAL STATISTICS”与 `data/gemini_keys_summary_*.txt`、`data/keys/keys_validation_summary_*.txt` **数据矛盾**（有效/付费/限流数量互不一致）。
- 同一运行内出现多条“Query complete”（Processed/Valid/Rate limited不同），缺少**最终权威口径**。 **影响**：无法可信复盘，后续流程/告警可能误判。

## 1.2 分类集合交叉/语义不清

- 某些 key 同时出现在“有效”与“限流”列表。
- 一个汇总认为“付费=4”，另一个汇总认为“付费=0”。 **影响**：读者认为类别互斥，但实现是交叉；报表失真。

## 1.3 停止流程混乱

- 收到 `Application cancelled / Orchestrator stop requested` 后仍在**持续验证与写日志**。 **影响**：退出后仍有副作用（写文件/刷统计），产物随机。

## 1.4 功能模块初始化错误（event loop）

- `progress_display`、`connection_pool` 报 *no running event loop*；存在 `coroutine was never awaited`。 **影响**：特性不可用且泄漏协程对象，潜在资源泄漏。

## 1.5 输出路径不统一

- `/app/data` 与 `./data` 并存；`app/data` 为空，而根 `data/` 有文件。 **影响**：依赖“当前工作目录”的相对路径，部署/容器环境下易踩坑。

## 1.6 日志/文件**明文暴露敏感密钥**（高风险）

- 控制台与文件均打印完整 key；日志路径未统一权限。 **影响**：泄露与合规风险（CI、共享节点、备份均可能外泄）。

## 1.7 GitHub 搜索**数据丢失率高**

- 多次出现 `Significant data loss: 58%~68%`，分页/重试品质不足。 **影响**：采样偏差大，漏查、误判比例上升。

## 1.8 速率限制策略粗糙

- 大量 `Rate limit low: 0 remaining`；没有基于令牌池的**全局预算调度**与退避（backoff）。 **影响**：触发 GitHub 风控、吞吐反而下降。

## 1.9 多份“权威产物”

- `gemini_keys_summary_*.txt` 与 `keys_validation_summary_*.txt` 并行输出且结论不同。 **影响**：难以对外给出单一可信结果。

---

# 2. 设计与产品层面的统一约定

1. **定义与层级（互斥）**

- `status ∈ { INVALID, RATE_LIMITED, VALID_FREE, VALID_PAID }`（四类互斥）。
- 导出指标：
  - `VALID = VALID_FREE + VALID_PAID`
  - `PAID = VALID_PAID`
  - `RATE_LIMITED` 作为**最终状态**，不再与 VALID 交叉；若后续重试通过，最终状态会被覆盖为 VALID\_\*。
- 报表必须标注：各指标含义与包含关系。

2. **单一“最终真相”产物**

- 仅输出 **一个最终汇总**（比如 `run_{run_id}/final_report.json` 与 `final_report.md`）。
- 其他文件为**阶段性或中间文件**，在名称/目录上显著标记：`/intermediate/…`。

3. **统一 run\_id 与目录结构**

- 运行开始生成 `run_id = YYYYMMDD_HHMMSS_random4`。
- 所有产出写入 `data/runs/{run_id}/…`；根目录保留**最新软链接**（如 `data/latest -> data/runs/{run_id}`）。

4. **安全与合规**

- 控制台与文件默认**脱敏**：`prefix(6)…suffix(4)`；
- 明文密钥若必须落盘，放入 `data/runs/{run_id}/secrets/`，`chmod 600`，并且**不写日志路径**；
- 支持 `--no-plaintext` 模式仅存 **HMAC(key, salt)**。

---

# 3. 代码级改造要点

## 3.1 统一统计模型（单一来源）

```python
# stats.py
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import Counter

class KeyStatus(Enum):
    INVALID = auto()
    RATE_LIMITED = auto()
    VALID_FREE = auto()
    VALID_PAID = auto()

@dataclass
class RunStats:
    run_id: str
    by_status: Counter = field(default_factory=Counter)
    items_processed: int = 0
    queries_planned: int = 0
    queries_completed: int = 0
    errors: int = 0

    def mark(self, status: KeyStatus):
        self.by_status[status] += 1

    def summary(self) -> dict:
        valid = self.by_status[KeyStatus.VALID_FREE] + self.by_status[KeyStatus.VALID_PAID]
        return {
            "run_id": self.run_id,
            "items_processed": self.items_processed,
            "queries_planned": self.queries_planned,
            "queries_completed": self.queries_completed,
            "valid": valid,
            "valid_free": self.by_status[KeyStatus.VALID_FREE],
            "valid_paid": self.by_status[KeyStatus.VALID_PAID],
            "rate_limited": self.by_status[KeyStatus.RATE_LIMITED],
            "invalid": self.by_status[KeyStatus.INVALID],
            "errors": self.errors,
        }
```

- 所有 UI/日志/文件**只读自** `RunStats.summary()`，避免口径漂移。

## 3.2 原子写文件 + 明确目录

```python
from pathlib import Path
import json, os, tempfile

ROOT = Path(__file__).resolve().parents[1]  # app/
DATA = ROOT / ".." / "data"  # 归一到仓库根 data/
RUN_DIR = DATA / "runs" / run_id
RUN_DIR.mkdir(parents=True, exist_ok=True)


def atomic_write_text(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent)) as tf:
        tf.write(content)
        tmp = Path(tf.name)
    os.replace(tmp, path)


def write_json_atomically(path: Path, obj: dict):
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2))
```

- 写 `final_report.json/md` **只在退出阶段**一次性落盘。

## 3.3 优雅停机（graceful shutdown）

- Orchestrator 接收信号后：
  1. **拒绝新任务**提交；
  2. `await`/`join` 已在跑的任务（设置超时与取消）；
  3. 聚合最终 `RunStats`；
  4. 一次性输出最终产物；
  5. 退出。
- 明确日志阶段：`SCANNING → VALIDATING → FINALIZE`，确保“FINAL STATISTICS”只打印一次。

## 3.4 功能模块加载与事件循环

- **不要在 import 时创建任务**；在 `Feature.start()` 中显式 `async def start()`，由上层在**已存在的事件循环**里启动：

```python
# feature_manager.py
async def start_features(features):
    for f in features:
        await f.start()

async def main_async():
    # … init …
    await start_features([progress_display, connection_pool, ...])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main_async())
```

- `progress_display` 的刷新协程仅在 `start()` 内 `asyncio.create_task(self._refresh_display())`；关闭时取消并 `await`。

## 3.5 GitHub 速率限制与令牌池调度

- 统一 `TokenPool`：按 token 的 **剩余额度/复位时间** 动态选择；全局节流器（令牌桶/漏斗）。
- 退避策略：命中次级 403/超时 → **指数退避 + 抖动**；
- 查询分页：记录 `since`/`page` 的**断点续扫**，失败页自动重试并限制上限（N 次），仍失败则记入 *data loss registry* 并在最终报告中呈现。

## 3.6 数据丢失度量与补偿

- 统一统计 `expected_total/item_count/page_success_count/data_loss_ratio`；
- 对 `data_loss_ratio > 阈值` 的查询：自动触发 **二次补扫**（降低并发、延长 sleep、切换 token）。

## 3.7 输出规范化

- 仅保留：
  - `runs/{run_id}/final_report.json`（机器可读）
  - `runs/{run_id}/final_report.md`（人类可读）
  - `runs/{run_id}/artifacts/`（中间产物、原始响应、失败列表、数据丢失登记表）
- `data/latest` 指向最新 run。

## 3.8 日志脱敏与权限

```python
def mask_key(k: str) -> str:
    return f"{k[:6]}…{k[-4:]}"

# Logger 始终打印 mask 后的 key；
# 明文文件：落盘到 RUN_DIR / "secrets"，并 chmod 0o600。
```

- 支持 `--no-plaintext`：只存 HMAC（盐来自环境变量）。

## 3.9 报表模板（单一口径）

- `final_report.md` 示例段：

```
# 运行概览（{run_id}）
- Queries: {queries_completed}/{queries_planned}
- Items processed: {items_processed}
- Valid (total/free/paid): {valid}/{valid_free}/{valid_paid}
- Rate-limited: {rate_limited}
- Invalid: {invalid}
- Data loss: {loss_ratio_overall}% (see artifacts/data_loss.csv)
```

---

# 4. 配置与路径策略

- **强制绝对路径**：由 `__file__` 推导项目根；
- 配置项集中在 `config_service`：`DATA_ROOT`, `RUN_OUTPUT_ROOT`, `ALLOW_PLAINTEXT`, `MASK_PATTERN`, `GITHUB_QPS_MAX`, `GITHUB_PAGE_RETRY_MAX`；
- 启动时打印一次：工作目录、数据目录、运行目录（mask 路径中的敏感部分）。

---

# 5. 安全与合规建议

- **默认不在控制台打印明文 key**；
- 输出文件权限：`umask 077`，关键文件 `chmod 600`；
- 如部署在容器：将 `data/` 绑定到受控卷，并禁用自动备份到非受控节点。

---

# 6. 监控与可观测性

- 指标：`github_requests_total`、`github_rate_remaining`、`data_loss_ratio`、`keys_validated_total`、`keys_status_count{status}`、`orchestrator_phase`；
- 日志：结构化 JSON（已有），字段与 `RunStats.summary()` 对齐；
- 告警：当 `data_loss_ratio > 0.2` 或连续三页失败时告警并降速。

---

# 7. 测试清单（可复制到 CI）

- 单元：
  - 统计互斥：`VALID_FREE + VALID_PAID == VALID`；`RATE_LIMITED` 不计入 `VALID`；
  - atomic write：中断/并发下仅保留完整文件；
  - mask：长度变化、非 ASCII；
- 集成：
  - 速率限制模拟（返回 403/429），验证退避与 token 切换；
  - `Ctrl+C`/信号测试：确保 FINAL 只输出一次、任务被收敛；
  - 数据丢失模拟（丢页/超时），确认补扫与报告。

---

# 8. 近期落地路线图（1\~2 天）

1. 引入 `RunStats` 与 `KeyStatus`，统一口径（半天）。
2. 改造写文件为原子写，合并“最终产物”，移除重复汇总（半天）。
3. 事件循环/特性启动重构（`asyncio.run(main_async)` + `Feature.start/stop`）（半天）。
4. 速率限制/令牌池与退避（半天）。
5. 路径/权限/脱敏（半天）。
6. GitHub 数据丢失侦测与补扫（半天）。

---

# 9. 额外建议

- 为“验证器”引入**幂等缓存**（key → 最近一次验证结果 + 时间 + 计费属性），在同一运行与短期内避免重复验证。
- 为“付费判定”建立**二次确认**（发现“付费”→ 额外调用一次不同端点/quota 验证，降低误报）。
- 在报表中加入 **样本列表（已脱敏）** 与 **重放脚本**，便于复查。

---

# 附：示例退出序列（伪代码）

```python
try:
    orchestrator.start()
    await orchestrator.run()
except KeyboardInterrupt:
    logger.info("stop requested")
finally:
    await orchestrator.graceful_shutdown()  # 停提交→等在跑→聚合→一次性写最终报告
    write_json_atomically(RUN_DIR/"final_report.json", stats.summary())
    atomic_write_text(RUN_DIR/"final_report.md", render_markdown(stats))
    symlink_latest(RUN_DIR)
```

