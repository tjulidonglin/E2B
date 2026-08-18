# E2B

E2B SDK 测试用例集合

## 冷启动时间测试

`cold_start_test.py` 用于测试 E2B 沙箱的冷启动时间，测量从调用 API 创建沙箱到沙箱内部执行 `echo 0` 命令完成的时间。

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API Key

方式一：设置环境变量
```bash
export E2B_API_KEY="your-api-key"
```

方式二：通过命令行参数传入（优先级更高）

### 使用方法

```bash
# 运行默认 10 次测试
python cold_start_test.py

# 指定测试次数
python cold_start_test.py --count 20

# 指定并发数（同时启动多个沙箱）
python cold_start_test.py --count 10 --concurrency 3

# 通过命令行传入 API Key
python cold_start_test.py --api-key your-api-key

# 组合使用
python cold_start_test.py --count 20 --concurrency 5 --api-key your-api-key
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--count` | 测试次数 | 10 |
| `--concurrency` | 并发沙箱数量 | 1 |
| `--api-key` | E2B API Key | 从环境变量 `E2B_API_KEY` 读取 |

### 输出说明

脚本会输出：
- 每次测试的详细时间
- 统计结果：
  - **Mean**: 平均冷启动时间
  - **Min**: 最小冷启动时间
  - **Max**: 最大冷启动时间
  - **P95**: 95% 分位数
  - **P99**: 99% 分位数

### 示例输出

```
============================================================
E2B Sandbox Cold Start Time Test
============================================================
Number of tests: 10
Test command: echo 0
============================================================

[1/10] Starting test...
[1/10] Completed in 2.345s
...

============================================================
E2B Sandbox Cold Start Time Test Results
============================================================

Individual Test Times:
----------------------------------------
  Test   1: 2.345s
  Test   2: 2.123s
  ...

----------------------------------------
Statistics:
----------------------------------------
  Test Count:  10
  Mean:        2.234s
  Min:         2.001s
  Max:         2.567s
  P95:         2.456s
  P99:         2.534s
============================================================