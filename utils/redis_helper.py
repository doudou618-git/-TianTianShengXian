import json
from django_redis import get_redis_connection
from django.core.cache import cache


def _get_cart_key(user_id):
    return f'cart:{user_id}'


def _get_history_key(user_id):
    return f'history:{user_id}'


# ==================== 购物车操作 ====================

def get_cart_items(user_id):
    """获取用户购物车所有商品
    返回: {goods_id: {quantity, selected}, ...}
    """
    conn = get_redis_connection('cart')
    key = _get_cart_key(user_id)
    raw = conn.hgetall(key)
    items = {}
    for goods_id_bytes, data_bytes in raw.items():
        goods_id = int(goods_id_bytes)
        items[goods_id] = json.loads(data_bytes)
    return items


def get_cart_item(user_id, goods_id):
    """获取购物车中单个商品"""
    conn = get_redis_connection('cart')
    key = _get_cart_key(user_id)
    data = conn.hget(key, goods_id)
    if data:
        return json.loads(data)
    return None


def add_to_cart(user_id, goods_id, quantity=1):
    """添加商品到购物车，已存在则累加数量
    返回: (当前数量, 是否新建)
    """
    conn = get_redis_connection('cart')
    key = _get_cart_key(user_id)
    existing = conn.hget(key, goods_id)
    if existing:
        item = json.loads(existing)
        item['quantity'] += quantity
        conn.hset(key, goods_id, json.dumps(item))
        return item['quantity'], False
    else:
        item = {'quantity': quantity, 'selected': True}
        conn.hset(key, goods_id, json.dumps(item))
        return quantity, True


def set_cart_item(user_id, goods_id, quantity=None, selected=None):
    """更新购物车商品数量或选中状态
    返回: 更新后的 {quantity, selected}，商品不存在返回 None
    """
    conn = get_redis_connection('cart')
    key = _get_cart_key(user_id)
    data = conn.hget(key, goods_id)
    if not data:
        return None
    item = json.loads(data)
    if quantity is not None:
        item['quantity'] = quantity
    if selected is not None:
        item['selected'] = selected
    conn.hset(key, goods_id, json.dumps(item))
    return item


def remove_from_cart(user_id, goods_id):
    """从购物车删除商品"""
    conn = get_redis_connection('cart')
    conn.hdel(_get_cart_key(user_id), goods_id)


def select_all_cart(user_id, selected=True):
    """全选/取消全选购物车"""
    conn = get_redis_connection('cart')
    key = _get_cart_key(user_id)
    raw = conn.hgetall(key)
    for goods_id_bytes, data_bytes in raw.items():
        item = json.loads(data_bytes)
        item['selected'] = selected
        conn.hset(key, goods_id_bytes, json.dumps(item))


def clear_cart(user_id):
    """清空购物车"""
    conn = get_redis_connection('cart')
    conn.delete(_get_cart_key(user_id))


def get_cart_count(user_id):
    """获取购物车商品种类数"""
    conn = get_redis_connection('cart')
    return conn.hlen(_get_cart_key(user_id))


# ==================== 浏览记录操作 ====================

def add_browse_history(user_id, goods_id, goods_name, goods_image, goods_price, max_items=50):
    """添加浏览记录（最新在前，自动去重，超过上限删除最旧的）"""
    conn = get_redis_connection('history')
    key = _get_history_key(user_id)
    entry = json.dumps({
        'goods_id': goods_id,
        'goods_name': goods_name,
        'goods_image': goods_image,
        'goods_price': float(goods_price),
    })

    # 去重：移除已有的相同商品记录
    existing_list = conn.lrange(key, 0, -1)
    for raw in existing_list:
        item = json.loads(raw)
        if item['goods_id'] == goods_id:
            conn.lrem(key, 1, raw)
            break

    # 插入到最前面
    conn.lpush(key, entry)

    # 裁剪，只保留最新的 max_items 条
    conn.ltrim(key, 0, max_items - 1)


def get_browse_history(user_id, page=1, page_size=5):
    """获取浏览记录（分页）
    返回: (列表, 总数)
    """
    conn = get_redis_connection('history')
    key = _get_history_key(user_id)
    total = conn.llen(key)
    start = (page - 1) * page_size
    end = start + page_size - 1
    raw_list = conn.lrange(key, start, end)

    result = []
    for raw in raw_list:
        item = json.loads(raw)
        result.append(item)

    return result, total


def delete_browse_history(user_id, goods_id):
    """删除指定商品的浏览记录"""
    conn = get_redis_connection('history')
    key = _get_history_key(user_id)
    existing_list = conn.lrange(key, 0, -1)
    for raw in existing_list:
        item = json.loads(raw)
        if item['goods_id'] == goods_id:
            conn.lrem(key, 1, raw)
            return True
    return False


def clear_browse_history(user_id):
    """清空浏览记录"""
    conn = get_redis_connection('history')
    conn.delete(_get_history_key(user_id))


# ==================== 套餐购物车操作 ====================

def _get_combo_key(user_id):
    return f'combo:{user_id}'


def add_combo_to_cart(user_id, combo_id, combo_price, items):
    """将套餐商品加入购物车
    items: [{'goods_id': int, 'quantity': int}, ...]
    """
    cart_conn = get_redis_connection('cart')
    combo_conn = get_redis_connection('cart')  # 使用同一个连接
    cart_key = _get_cart_key(user_id)
    combo_key = _get_combo_key(user_id)

    # 将套餐内每个商品加入购物车（累加数量）
    for item in items:
        goods_id = str(item['goods_id'])
        quantity = item['quantity']
        existing = cart_conn.hget(cart_key, goods_id)
        if existing:
            cart_item = json.loads(existing)
            cart_item['quantity'] += quantity
            cart_conn.hset(cart_key, goods_id, json.dumps(cart_item))
        else:
            cart_conn.hset(cart_key, goods_id, json.dumps({
                'quantity': quantity,
                'selected': True,
            }))

    # 记录套餐关联信息
    combo_info = {
        'combo_price': float(combo_price),
        'items': items,
    }
    combo_conn.hset(combo_key, combo_id, json.dumps(combo_info))


def get_combo_cart_info(user_id):
    """获取购物车中的套餐关联信息
    返回: {combo_id: {combo_price, items: [...]}, ...}
    """
    conn = get_redis_connection('cart')
    key = _get_combo_key(user_id)
    raw = conn.hgetall(key)
    result = {}
    for combo_id_bytes, data_bytes in raw.items():
        combo_id = int(combo_id_bytes)
        result[combo_id] = json.loads(data_bytes)
    return result


def remove_combo_from_cart(user_id, combo_id):
    """删除套餐关联（不删除商品）"""
    conn = get_redis_connection('cart')
    conn.hdel(_get_combo_key(user_id), combo_id)


def clear_combo_cart(user_id):
    """清空套餐关联"""
    conn = get_redis_connection('cart')
    conn.delete(_get_combo_key(user_id))


# ==================== 短信验证码操作 ====================

def _get_sms_code_key(phone):
    return f'sms_code:{phone}'


def save_sms_code(phone, code, ttl=300):
    """存储短信验证码，ttl 默认5分钟"""
    cache.set(_get_sms_code_key(phone), code, ttl)


def get_sms_code(phone):
    """获取短信验证码"""
    return cache.get(_get_sms_code_key(phone))


def delete_sms_code(phone):
    """删除短信验证码"""
    cache.delete(_get_sms_code_key(phone))
