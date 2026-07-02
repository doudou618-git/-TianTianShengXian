"""
接口限流模块
基于 Redis 实现，支持用户级和 IP 级限流
"""
import time
import functools
from django.http import JsonResponse
from django_redis import get_redis_connection


class RateLimiter:
    """令牌桶限流器"""

    def __init__(self, key_prefix, rate, capacity):
        """
        Args:
            key_prefix: Redis key 前缀
            rate: 每秒产生的令牌数
            capacity: 令牌桶容量
        """
        self.key_prefix = key_prefix
        self.rate = rate
        self.capacity = capacity
        self.conn = get_redis_connection('default')

    def _get_key(self, identifier):
        """获取 Redis key"""
        return f'{self.key_prefix}:{identifier}'

    def allow_request(self, identifier):
        """
        检查是否允许请求

        Args:
            identifier: 标识符（用户ID或IP）

        Returns:
            tuple: (是否允许, 剩余令牌数, 需要等待时间)
        """
        key = self._get_key(identifier)
        now = time.time()

        # 使用 Lua 脚本保证原子性
        lua_script = """
        local key = KEYS[1]
        local rate = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])
        local requested = tonumber(ARGV[4])

        local last_time = tonumber(redis.call('HGET', key, 'last_time') or 0)
        local tokens = tonumber(redis.call('HGET', key, 'tokens') or capacity)

        -- 计算时间差，添加新令牌
        local elapsed = now - last_time
        tokens = math.min(capacity, tokens + elapsed * rate)

        -- 检查是否有足够令牌
        local allowed = 0
        local wait_time = 0
        if tokens >= requested then
            tokens = tokens - requested
            allowed = 1
        else
            wait_time = (requested - tokens) / rate
        end

        -- 更新 Redis
        redis.call('HSET', key, 'tokens', tokens)
        redis.call('HSET', key, 'last_time', now)
        redis.call('EXPIRE', key, 3600)

        return {allowed, math.floor(tokens), math.ceil(wait_time * 1000)}
        """

        result = self.conn.eval(
            lua_script,
            1,
            key,
            self.rate,
            self.capacity,
            now,
            1
        )

        return bool(result[0]), int(result[1]), int(result[2])


# 创建限流器实例
# 用户登录限流：5次/分钟
login_limiter = RateLimiter('throttle:login', rate=5/60, capacity=5)

# 注册限流：3次/分钟
register_limiter = RateLimiter('throttle:register', rate=3/60, capacity=3)

# 验证码限流：1次/分钟
sms_limiter = RateLimiter('throttle:sms', rate=1/60, capacity=1)

# API 通用限流：60次/分钟
api_limiter = RateLimiter('throttle:api', rate=60/60, capacity=60)

# 搜索限流：30次/分钟
search_limiter = RateLimiter('throttle:search', rate=30/60, capacity=30)


def get_client_ip(request):
    """获取客户端真实 IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def rate_limit(limiter, key_func=None, error_msg='请求过于频繁，请稍后再试'):
    """
    限流装饰器

    Args:
        limiter: RateLimiter 实例
        key_func: 获取限流 key 的函数，默认使用 IP
        error_msg: 超限时的错误信息
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # 获取限流 key
            if key_func:
                identifier = key_func(request)
            else:
                identifier = get_client_ip(request)

            # 检查是否允许
            allowed, remaining, wait_time = limiter.allow_request(identifier)

            if not allowed:
                return JsonResponse({
                    'code': 429,
                    'msg': error_msg,
                    'data': {
                        'retry_after': wait_time / 1000,  # 秒
                    }
                }, status=429)

            # 执行视图函数
            response = view_func(request, *args, **kwargs)

            # 添加限流信息到响应头
            if hasattr(response, '__setitem__'):
                response['X-RateLimit-Remaining'] = str(remaining)
                response['X-RateLimit-Limit'] = str(limiter.capacity)

            return response
        return wrapper
    return decorator


def user_rate_limit(limiter, error_msg='请求过于频繁，请稍后再试'):
    """
    用户级限流装饰器（需要登录）

    Args:
        limiter: RateLimiter 实例
        error_msg: 超限时的错误信息
    """
    def get_user_key(request):
        if request.user.is_authenticated:
            return f'user:{request.user.id}'
        return get_client_ip(request)

    return rate_limit(limiter, key_func=get_user_key, error_msg=error_msg)
