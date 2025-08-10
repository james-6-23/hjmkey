# 🏗️ Modular Architecture Design

## Overview

This document describes the modular architecture system that allows all enhancement features to be individually enabled or disabled through environment variable configuration. The core program runs independently without dependencies on optional components.

## Architecture Principles

1. **Independence**: Core functionality operates without optional modules
2. **Isolation**: Each feature module is completely isolated
3. **Graceful Degradation**: System falls back to default behavior when features are disabled
4. **Dynamic Loading**: Features are conditionally imported based on configuration
5. **Error Resilience**: Core remains stable even if optional modules fail

## Feature Modules

### 1. Asynchronous Batch Validation
**Environment Variable**: `ENABLE_ASYNC_VALIDATION=true/false`
**Configuration**:
- `ASYNC_BATCH_SIZE=50` (number of keys per batch)
- `ASYNC_MAX_CONCURRENT=10` (max concurrent validations)
- `ASYNC_TIMEOUT=30` (timeout in seconds)

**Implementation**:
```python
# app/features/async_validation.py
class AsyncValidationFeature:
    def __init__(self, config):
        self.enabled = config.get('ENABLE_ASYNC_VALIDATION', False)
        self.batch_size = config.get('ASYNC_BATCH_SIZE', 50)
        self.max_concurrent = config.get('ASYNC_MAX_CONCURRENT', 10)
    
    async def validate_batch(self, keys):
        # 10x performance improvement through concurrent validation
        pass
```

### 2. Real-time Progress Display
**Environment Variable**: `ENABLE_PROGRESS_DISPLAY=true/false`
**Configuration**:
- `PROGRESS_UPDATE_INTERVAL=1` (seconds between updates)
- `PROGRESS_DISPLAY_TYPE=bar/spinner/percentage`
- `PROGRESS_SHOW_ETA=true/false`

**Implementation**:
```python
# app/features/progress_display.py
class ProgressDisplayFeature:
    def __init__(self, config):
        self.enabled = config.get('ENABLE_PROGRESS_DISPLAY', False)
        self.update_interval = config.get('PROGRESS_UPDATE_INTERVAL', 1)
        
    def create_progress_bar(self, total):
        if not self.enabled:
            return NullProgressBar()  # No-op implementation
        return RichProgressBar(total)
```

### 3. Structured Logging
**Environment Variable**: `ENABLE_STRUCTURED_LOGGING=true/false`
**Configuration**:
- `LOG_FORMAT=json/xml/yaml`
- `LOG_LEVEL=DEBUG/INFO/WARNING/ERROR`
- `LOG_OUTPUT=console/file/both`
- `LOG_FILE_PATH=./logs/app.log`

**Implementation**:
```python
# app/features/structured_logging.py
class StructuredLoggingFeature:
    def __init__(self, config):
        self.enabled = config.get('ENABLE_STRUCTURED_LOGGING', False)
        self.format = config.get('LOG_FORMAT', 'json')
        
    def get_logger(self, name):
        if not self.enabled:
            return standard_logger
        return StructuredLogger(name, format=self.format)
```

### 4. Connection Pool Optimization
**Environment Variable**: `ENABLE_CONNECTION_POOL=true/false`
**Configuration**:
- `POOL_SIZE=100` (max connections)
- `POOL_TIMEOUT=30` (connection timeout)
- `POOL_RETRY_COUNT=3` (retry attempts)
- `POOL_KEEPALIVE=300` (keepalive in seconds)

**Implementation**:
```python
# app/features/connection_pool.py
class ConnectionPoolFeature:
    def __init__(self, config):
        self.enabled = config.get('ENABLE_CONNECTION_POOL', False)
        self.pool_size = config.get('POOL_SIZE', 100)
        
    def get_session(self):
        if not self.enabled:
            return requests.Session()
        return PooledSession(size=self.pool_size)
```

### 5. Database Persistence Layer
**Environment Variable**: `ENABLE_DATABASE=true/false`
**Configuration**:
- `DB_TYPE=sqlite/postgres/mysql`
- `DB_HOST=localhost`
- `DB_PORT=5432`
- `DB_NAME=hajimi_king`
- `DB_USER=admin`
- `DB_PASSWORD=secret`

**Implementation**:
```python
# app/features/database.py
class DatabaseFeature:
    def __init__(self, config):
        self.enabled = config.get('ENABLE_DATABASE', False)
        self.db_type = config.get('DB_TYPE', 'sqlite')
        
    def get_storage(self):
        if not self.enabled:
            return FileStorage()  # Fallback to file storage
        
        if self.db_type == 'sqlite':
            return SqliteStorage()
        elif self.db_type == 'postgres':
            return PostgresStorage()
        elif self.db_type == 'mysql':
            return MysqlStorage()
```

### 6. Plugin System
**Environment Variable**: `ENABLE_PLUGINS=true/false`
**Configuration**:
- `PLUGIN_DIR=./plugins`
- `PLUGIN_AUTO_RELOAD=true/false`
- `PLUGIN_RELOAD_INTERVAL=60` (seconds)
- `PLUGIN_WHITELIST=plugin1,plugin2`

**Implementation**:
```python
# app/features/plugin_system.py
class PluginSystemFeature:
    def __init__(self, config):
        self.enabled = config.get('ENABLE_PLUGINS', False)
        self.plugin_dir = config.get('PLUGIN_DIR', './plugins')
        
    def load_plugins(self):
        if not self.enabled:
            return []
        return self._discover_and_load_plugins()
```

### 7. Monitoring and Alerting
**Environment Variable**: `ENABLE_MONITORING=true/false`
**Configuration**:
- `ALERT_WEBHOOK_URL=https://hooks.slack.com/...`
- `ALERT_EMAIL_TO=admin@example.com`
- `ALERT_EMAIL_FROM=monitor@example.com`
- `ALERT_SMTP_HOST=smtp.gmail.com`
- `ALERT_SMTP_PORT=587`
- `METRICS_PORT=8080` (Prometheus metrics port)

**Implementation**:
```python
# app/features/monitoring.py
class MonitoringFeature:
    def __init__(self, config):
        self.enabled = config.get('ENABLE_MONITORING', False)
        self.webhook_url = config.get('ALERT_WEBHOOK_URL')
        
    def send_alert(self, message, level='warning'):
        if not self.enabled:
            return
        self._send_to_webhook(message, level)
```

## Feature Manager

The Feature Manager is the central component that handles feature loading and dependency resolution:

```python
# app/features/feature_manager.py
class FeatureManager:
    def __init__(self, config):
        self.config = config
        self.features = {}
        self.compatibility_matrix = self._load_compatibility_matrix()
        
    def initialize_features(self):
        """Conditionally load and initialize features based on config"""
        
        # Check and load async validation
        if self.config.get('ENABLE_ASYNC_VALIDATION'):
            try:
                from .async_validation import AsyncValidationFeature
                self.features['async_validation'] = AsyncValidationFeature(self.config)
                logger.info("✅ Async validation feature loaded")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load async validation: {e}")
        
        # Check and load progress display
        if self.config.get('ENABLE_PROGRESS_DISPLAY'):
            try:
                from .progress_display import ProgressDisplayFeature
                self.features['progress_display'] = ProgressDisplayFeature(self.config)
                logger.info("✅ Progress display feature loaded")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load progress display: {e}")
        
        # Continue for other features...
        
        # Validate compatibility
        self._validate_feature_compatibility()
        
    def _validate_feature_compatibility(self):
        """Check for conflicts between enabled features"""
        enabled = [name for name in self.features.keys()]
        
        for feature1 in enabled:
            for feature2 in enabled:
                if feature1 != feature2:
                    if not self.compatibility_matrix.get(feature1, {}).get(feature2, True):
                        raise FeatureConflictError(f"{feature1} conflicts with {feature2}")
    
    def get_feature(self, name):
        """Get a feature instance or return None if not enabled"""
        return self.features.get(name)
    
    def is_enabled(self, name):
        """Check if a feature is enabled"""
        return name in self.features
```

## Feature Compatibility Matrix

| Feature | Async Validation | Progress Display | Structured Logging | Connection Pool | Database | Plugins | Monitoring |
|---------|-----------------|------------------|-------------------|-----------------|----------|---------|------------|
| **Async Validation** | - | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Progress Display** | ✅ | - | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Structured Logging** | ✅ | ✅ | - | ✅ | ✅ | ✅ | ✅ |
| **Connection Pool** | ✅ | ✅ | ✅ | - | ✅ | ✅ | ✅ |
| **Database** | ✅ | ✅ | ✅ | ✅ | - | ✅ | ✅ |
| **Plugins** | ✅ | ✅ | ✅ | ✅ | ✅ | - | ✅ |
| **Monitoring** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | - |

## Integration with Core Application

### Modified Main Application

```python
# app/main.py
import os
from app.features.feature_manager import FeatureManager
from app.core.orchestrator import Orchestrator

def main():
    # Load configuration from environment
    config = load_config_from_env()
    
    # Initialize feature manager
    feature_manager = FeatureManager(config)
    feature_manager.initialize_features()
    
    # Create orchestrator with optional features
    orchestrator = Orchestrator(
        validator=create_validator(feature_manager),
        logger=create_logger(feature_manager),
        storage=create_storage(feature_manager)
    )
    
    # Run with optional progress display
    progress = None
    if feature_manager.is_enabled('progress_display'):
        progress = feature_manager.get_feature('progress_display').create_progress_bar(total_items)
    
    # Execute main logic
    orchestrator.run(progress=progress)

def create_validator(feature_manager):
    """Create validator with optional async support"""
    if feature_manager.is_enabled('async_validation'):
        return feature_manager.get_feature('async_validation').create_validator()
    return StandardValidator()  # Fallback to synchronous validator

def create_logger(feature_manager):
    """Create logger with optional structured logging"""
    if feature_manager.is_enabled('structured_logging'):
        return feature_manager.get_feature('structured_logging').get_logger(__name__)
    return standard_logger  # Fallback to standard logger

def create_storage(feature_manager):
    """Create storage with optional database support"""
    if feature_manager.is_enabled('database'):
        return feature_manager.get_feature('database').get_storage()
    return FileStorage()  # Fallback to file storage
```

## Environment Configuration Example

```env
# Core Configuration (Always Required)
GITHUB_TOKENS=ghp_xxx,ghp_yyy
DATA_PATH=./data

# Optional Feature Flags
ENABLE_ASYNC_VALIDATION=true
ASYNC_BATCH_SIZE=100
ASYNC_MAX_CONCURRENT=20

ENABLE_PROGRESS_DISPLAY=true
PROGRESS_UPDATE_INTERVAL=0.5
PROGRESS_DISPLAY_TYPE=bar

ENABLE_STRUCTURED_LOGGING=true
LOG_FORMAT=json
LOG_LEVEL=INFO

ENABLE_CONNECTION_POOL=true
POOL_SIZE=200
POOL_TIMEOUT=60

ENABLE_DATABASE=false
DB_TYPE=postgres
DB_HOST=localhost
DB_PORT=5432

ENABLE_PLUGINS=true
PLUGIN_DIR=./plugins
PLUGIN_AUTO_RELOAD=true

ENABLE_MONITORING=true
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/xxx
METRICS_PORT=8080
```

## Error Handling Strategy

### Graceful Degradation

Each feature module implements graceful degradation:

1. **Feature Load Failure**: Log warning and continue without the feature
2. **Runtime Error**: Catch exceptions and fall back to default behavior
3. **Dependency Missing**: Use null object pattern or default implementation
4. **Configuration Error**: Use sensible defaults

### Example Error Handling

```python
class FeatureWrapper:
    def __init__(self, feature_class, config, fallback):
        self.fallback = fallback
        try:
            self.feature = feature_class(config)
            self.enabled = True
        except Exception as e:
            logger.warning(f"Feature {feature_class.__name__} failed to load: {e}")
            self.feature = None
            self.enabled = False
    
    def execute(self, *args, **kwargs):
        if self.enabled and self.feature:
            try:
                return self.feature.execute(*args, **kwargs)
            except Exception as e:
                logger.error(f"Feature execution failed: {e}")
        return self.fallback(*args, **kwargs)
```

## Testing Strategy

### Feature Isolation Testing

```python
# tests/features/test_feature_manager.py
def test_feature_loads_when_enabled():
    config = {'ENABLE_ASYNC_VALIDATION': True}
    manager = FeatureManager(config)
    manager.initialize_features()
    assert manager.is_enabled('async_validation')

def test_feature_not_loaded_when_disabled():
    config = {'ENABLE_ASYNC_VALIDATION': False}
    manager = FeatureManager(config)
    manager.initialize_features()
    assert not manager.is_enabled('async_validation')

def test_core_runs_without_features():
    config = {}  # All features disabled
    manager = FeatureManager(config)
    manager.initialize_features()
    orchestrator = Orchestrator()
    result = orchestrator.run()  # Should work without any features
    assert result.success
```

## Performance Considerations

### Feature Impact Analysis

| Feature | Memory Overhead | CPU Impact | Startup Time | Dependencies |
|---------|----------------|------------|--------------|--------------|
| Async Validation | Low | -90% (improvement) | +100ms | aiohttp |
| Progress Display | Minimal | Low | +50ms | rich |
| Structured Logging | Low | Low | +20ms | structlog |
| Connection Pool | Medium | -50% (improvement) | +200ms | - |
| Database | High | Medium | +500ms | sqlalchemy |
| Plugins | Variable | Variable | +100ms per plugin | - |
| Monitoring | Low | Low | +150ms | prometheus-client |

## Migration Guide

### Enabling Features Gradually

1. **Phase 1**: Run with all features disabled (baseline)
2. **Phase 2**: Enable logging and monitoring
3. **Phase 3**: Enable performance features (async, connection pool)
4. **Phase 4**: Enable persistence (database)
5. **Phase 5**: Enable extensibility (plugins)

### Rollback Strategy

If a feature causes issues:

1. Set `ENABLE_<FEATURE>=false` in environment
2. Restart application
3. System automatically falls back to default behavior
4. No code changes required

## Future Enhancements

### Planned Features

1. **Feature Hot-Reload**: Change feature configuration without restart
2. **Feature Metrics**: Track feature usage and performance impact
3. **Feature Dependencies**: Automatic dependency resolution
4. **Feature Profiles**: Predefined feature combinations (dev, staging, production)
5. **Feature A/B Testing**: Gradual rollout and comparison

### Extension Points

The architecture provides extension points for:

- Custom feature modules
- Third-party integrations
- Performance optimizations
- Security enhancements
- Monitoring integrations

## Conclusion

This modular architecture provides:

- **Flexibility**: Enable/disable features as needed
- **Stability**: Core functionality always works
- **Maintainability**: Features are isolated and testable
- **Scalability**: Add new features without affecting existing ones
- **Performance**: Optional optimizations when needed