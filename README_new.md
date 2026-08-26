# E2B

E2B SDK 测试用例集合 - 针对E2B生态沙箱产品的完整测试套件

## 📋 测试套件概览

本测试套件提供从**性能**和**安全**两个维度对E2B沙箱产品进行全面测试。

### 测试模块

| 模块 | 测试类型 | 测试内容 |
|------|---------|---------|
| **性能测试** | 吞吐量测试 | 并发创建能力、命令执行吞吐量 |
| | 命令延迟测试 | echo/ls/pwd等简单命令的执行延迟 |
| | 资源监控 | CPU、内存、磁盘使用率监控 |
| | 冷启动测试 | 沙箱冷启动时间测量 |
| **安全测试** | 网络隔离 | 外网访问限制、DNS解析限制 |
| | 文件系统安全 | 沙箱间文件隔离、目录隔离 |
| | 进程安全 | 沙箱间进程隔离 |
| | 资源隔离 | CPU/内存/磁盘资源限制 |

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 必需：E2B API Key
export E2B_API_KEY="your-api-key"

# 必需：沙箱模板ID
export CUBE_TEMPLATE_ID="your-template-id"
```

### 3. 运行测试

```bash
# 运行所有测试
python run_tests.py --all

# 仅运行性能测试
python run_tests.py --performance

# 仅运行安全测试
python run_tests.py --security

# 运行特定测试
python run_tests.py --test throughput
python run_tests.py --test network_isolation

# 自定义并发数（默认50）
python run_tests.py --all --concurrency 100

# 指定输出报告文件名
python run_tests.py --all --output custom_report.html
```

---

## 📁 项目结构

```
E2B/
├── run_tests.py                 # 统一测试入口
├── config.yaml                  # 测试配置文件
├── requirements.txt             # Python依赖
├── tests/                       # 测试套件目录
│   ├── __init__.py
│   ├── performance/             # 性能测试模块
│   │   ├── test_throughput.py
│   │   ├── test_cmd_latency.py
│   │   └── test_resource_monitor.py
│   ├── security/                # 安全测试模块
│   │   ├── test_network_isolation.py
│   │   ├── test_filesystem_security.py
│   │   ├── test_process_isolation.py
│   │   └── test_resource_isolation.py
│   └── utils/                   # 测试工具库
│       ├── sandbox_manager.py
│       ├── metrics_collector.py
│       └── report_generator.py
├── reports/                     # 测试报告输出目录
└── README.md                    # 本文档
```

---

## 🧪 测试用例详情

### 一、性能测试

#### 1.1 吞吐量测试 (test_throughput.py)
- 并发创建能力测试（支持5/10/20/50/100个并发）
- 命令执行吞吐量测试

#### 1.2 命令执行延迟测试 (test_cmd_latency.py)
- echo/ls/pwd/whoami/date命令延迟测试

#### 1.3 资源利用率监控 (test_resource_monitor.py)
- CPU、内存、磁盘使用率监控

---

### 二、安全测试

#### 2.1 网络隔离测试 (test_network_isolation.py)
- 外网访问限制验证

#### 2.2 文件系统安全测试 (test_filesystem_security.py)
- 沙箱间文件隔离测试

#### 2.3 进程隔离测试 (test_process_isolation.py)
- 沙箱间进程隔离测试

#### 2.4 资源隔离测试 (test_resource_isolation.py)
- CPU/内存/磁盘资源限制测试

---

## 📊 测试报告

测试完成后自动生成HTML格式报告，保存在`reports/`目录。

---

## 🔗 相关链接

- [E2B 官方文档](https://e2b.dev/docs)
- [E2B Dashboard](https://e2b.dev/dashboard)