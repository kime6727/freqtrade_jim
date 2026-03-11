# FreqTrade Dokploy 部署指南

## 项目结构

```
.
├── Dockerfile                    # FreqTrade 主服务镜像
├── docker-compose.yml            # 本地开发配置
├── dokploy-compose.yml           # Dokploy 部署配置
├── config-server/                # 配置管理 Web 服务
│   ├── Dockerfile
│   ├── app.py                    # FastAPI 后端
│   ├── static/
│   │   └── config-editor.html    # 配置编辑网页
│   └── requirements.txt
└── user_data/
    ├── config.json               # FreqTrade 配置文件
    └── strategies/               # 交易策略
        └── SampleStrategy.py
```

## 服务说明

### 1. FreqTrade 主服务 (端口 8080)
- 量化交易核心服务
- 提供 Web UI 查看交易状态
- 默认用户名: `freqtrade`
- 默认密码: `KJDD9773LJKDkjkj`

### 2. 配置管理服务 (端口 8000)
- 提供可视化配置编辑界面
- 支持配置保存、备份、恢复
- 支持查看日志
- 支持重启 FreqTrade 服务

## Dokploy 部署步骤

### 步骤 1: 准备 Dokploy 服务器

1. 访问 Dokploy 面板: http://128.1.40.110:3000
2. 创建新项目，命名为 `freqtrade`

### 步骤 2: 配置 Git 仓库

在 Dokploy 面板中：
1. 选择 "Git" 部署方式
2. 填写仓库信息：
   - Repository: `https://github.com/kime6727/freqtrade_jim.git`
   - Branch: `main` 或 `master`
3. 添加 GitHub Access Token（在 Dokploy 面板的安全设置中添加）

### 步骤 3: 配置 Docker Compose

在 Dokploy 面板的 "Docker Compose" 选项卡中：

1. 选择 `dokploy-compose.yml` 文件
2. 或者直接将内容粘贴到编辑器

### 步骤 4: 配置域名和端口

1. 进入项目设置
2. 添加域名（可选）
3. 配置端口映射：
   - FreqTrade Web UI: 8080
   - 配置管理界面: 8000

### 步骤 5: 部署

点击 "Deploy" 按钮开始部署

## 访问服务

部署完成后，可以通过以下地址访问：

| 服务 | 地址 | 说明 |
|------|------|------|
| FreqTrade Web UI | http://128.1.40.110:8080 | 交易监控界面 |
| 配置管理界面 | http://128.1.40.110:8000 | 配置编辑器 |

## 配置管理界面使用说明

### 登录
1. 打开 http://128.1.40.110:8000
2. 输入用户名和密码（默认与 FreqTrade API 相同）

### 功能说明

#### 1. 基本设置
- 最大同时持仓数
- 每笔交易金额
- K线周期（1m/5m/15m/1h/4h/1d）
- 模拟/实盘模式切换

#### 2. 交易所设置
- 选择交易所（币安、Bitget、Bybit、OKX 等）
- 配置 API Key 和 Secret
- 设置交易对白名单/黑名单

#### 3. 风险控制
- 止损比例设置
- 追踪止损配置
- 订单超时设置

#### 4. 保存配置
- **仅保存**: 保存配置但不重启，需手动重启生效
- **保存并重启**: 保存配置并自动重启 FreqTrade 服务

#### 5. 备份管理
- 自动创建配置备份
- 支持恢复到历史版本

#### 6. 日志查看
- 实时查看 FreqTrade 运行日志
- 支持自定义显示行数

## 重要安全提示

1. **API 密钥安全**
   - 不要在代码仓库中提交真实的 API 密钥
   - 通过配置管理界面设置 API 密钥
   - 定期更换 API 密钥

2. **初始配置**
   - 默认使用模拟交易模式（dry_run: true）
   - 测试稳定后再切换到实盘模式

3. **密码修改**
   - 首次部署后请修改默认密码
   - 修改 `user_data/config.json` 中的 `api_server.password`

## 故障排查

### 服务无法启动
1. 检查日志：`docker logs freqtrade`
2. 确认配置文件格式正确
3. 检查端口是否被占用

### 配置保存失败
1. 确认配置管理服务运行正常
2. 检查磁盘空间
3. 查看配置管理服务日志：`docker logs freqtrade-config`

### 重启失败
- 如果自动重启失败，请手动在 Dokploy 面板重启容器

## 更新部署

修改代码后推送到 GitHub，Dokploy 会自动触发重新部署。

或者手动在 Dokploy 面板点击 "Redeploy" 按钮。
