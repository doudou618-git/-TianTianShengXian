# 天天生鲜 - 生鲜电商平台

一个基于 Django 的全栈生鲜电商 Web 应用，包含前台商城和后台管理系统。

## 技术栈

| 类别 | 技术 |
|------|------|
| 后端 | Django 4.2 + MySQL |
| 缓存 | Redis（购物车 / 浏览记录 / 验证码） |
| 前端 | 原生 HTML/CSS/JS，响应式设计 |
| 数据库 | MySQL 8.0 |
| 认证 | Django Auth + 自定义用户模型 |

## 功能模块

### 前台商城

- **用户系统**：注册（短信验证码）、登录、个人中心、头像上传
- **商品展示**：分类浏览、商品详情、规格展示、评论系统（支持图片）
- **购物车**：Redis 存储、数量调整、全选/单选、秒杀价/套餐价自动计算
- **订单系统**：下单、模拟支付、订单状态流转（待付款→待发货→待收货→已完成）、30 分钟超时自动取消
- **营销活动**：限时秒杀（进度条）、组合套餐（按比例分摊价格）
- **个人中心**：收货地址管理、浏览记录、商品收藏

### 后台管理

- **数据看板**：商品数、分类数、秒杀活动数、用户数统计
- **商品管理**：CRUD、上下架、图片上传
- **分类管理**：分类增删改、图标配置
- **秒杀管理**：活动创建、时间设置、库存管理
- **套餐管理**：组合商品配置、价格设置

## 项目结构

```
TianTianShengXian/
├── TianTianShengXian/     # 项目配置
│   ├── settings.py        # Django 配置（支持 .env 环境变量）
│   ├── urls.py            # 总路由
│   └── wsgi.py
├── goods/                 # 商品模块
│   ├── models.py          # 商品、分类、秒杀、评论、套餐模型
│   ├── views.py           # 商品 API
│   └── management/        # 初始化数据命令
├── user/                  # 用户模块
│   ├── models.py          # 用户、地址、收藏、浏览记录模型
│   ├── views.py           # 用户 API
│   └── management/        # 创建管理员命令
├── order/                 # 订单模块
│   ├── models.py          # 订单、购物车模型
│   └── views.py           # 订单 API（含 Redis 购物车操作）
├── home/                  # 首页模块
│   └── views.py           # 首页数据聚合 API
├── manage_app/            # 后台管理模块
│   ├── views.py           # 管理后台视图
│   └── templates/         # 管理后台模板
├── utils/
│   └── redis_helper.py    # Redis 操作封装（购物车、浏览记录、验证码）
├── db/
│   └── base_model.py      # 抽象基类（软删除、时间戳）
├── media/                 # 上传文件目录
├── .env.example           # 环境变量示例
├── requirements.txt       # Python 依赖
├── Dockerfile             # Docker 镜像配置
├── docker-compose.yml     # 一键部署（MySQL + Redis + Web）
└── manage.py
```

## 快速启动

### 环境要求

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/TianTianShengXian.git
cd TianTianShengXian

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的数据库密码等配置

# 5. 创建数据库
mysql -u root -p -e "CREATE DATABASE tiantian DEFAULT CHARACTER SET utf8mb4;"

# 6. 执行数据库迁移
python manage.py migrate

# 7. 初始化商品数据
python manage.py init_data

# 8. 创建管理员账号
python manage.py create_admin

# 9. 启动 Redis
redis-server

# 10. 启动开发服务器
python manage.py runserver
```

访问 http://127.0.0.1:8000/home/ 进入前台商城
访问 http://127.0.0.1:8000/manage/ 进入后台管理

### Docker 一键启动

```bash
# 克隆项目后直接启动
docker compose up -d

# 创建管理员账号
docker compose exec web python manage.py create_admin
```

访问 http://127.0.0.1:8000/home/ 即可。

## API 接口

### 用户模块

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/user/login/` | 用户登录 |
| POST | `/user/register/` | 用户注册 |
| POST | `/user/send-sms-code/` | 发送短信验证码 |
| GET | `/user/info/` | 获取用户信息 |
| POST | `/user/avatar/upload/` | 上传头像 |

### 商品模块

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/goods/categories/` | 获取所有分类 |
| GET | `/goods/category/<id>/` | 获取分类下商品 |
| GET | `/goods/<id>/api/` | 获取商品详情 |
| POST | `/goods/<id>/comment/` | 添加评论 |

### 购物车 & 订单

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/order/cart/` | 获取购物车 |
| POST | `/order/cart/add/` | 添加到购物车 |
| POST | `/order/create/` | 创建订单 |
| GET | `/order/list/` | 获取订单列表 |
| POST | `/order/<id>/pay/confirm/` | 确认支付 |

### 首页

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/home/api/data/` | 获取首页聚合数据（分类、商品、秒杀、套餐） |

## 设计亮点

- **Redis 缓存策略**：购物车使用 Hash 结构存储，浏览记录使用 List（自动去重、保留最新 50 条），短信验证码设置 5 分钟 TTL
- **秒杀系统**：独立的秒杀模型，支持库存管理、进度条展示、时间窗口控制
- **套餐价格分摊**：购物车中自动识别完整套餐，按商品原价比例分配套餐价
- **订单超时机制**：取消支付后设置 30 分钟过期时间，查询时自动取消过期订单
- **软删除**：BaseModel 抽象基类统一管理 `is_delete`、`create_time`、`update_time`
- **权限控制**：自定义 `admin_required` 装饰器实现管理员权限校验
