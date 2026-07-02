"""
数据库查询优化工具
提供查询优化装饰器和工具函数
"""
import time
import functools
import logging
from django.db import connection
from django.conf import settings

logger = logging.getLogger('app')


class QueryAnalyzer:
    """查询分析器"""

    @staticmethod
    def analyze_queries(func):
        """
        分析函数执行的数据库查询
        装饰器，用于调试和优化查询
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 清除之前的查询记录
            if settings.DEBUG:
                initial_queries = len(connection.queries)
                start_time = time.time()

            result = func(*args, **kwargs)

            if settings.DEBUG:
                end_time = time.time()
                final_queries = len(connection.queries)
                query_count = final_queries - initial_queries
                execution_time = (end_time - start_time) * 1000  # 毫秒

                # 输出查询分析
                logger.info(f'[查询分析] {func.__name__}:')
                logger.info(f'  - 执行时间: {execution_time:.2f}ms')
                logger.info(f'  - 查询次数: {query_count}')

                # 输出慢查询（超过10ms）
                for i in range(initial_queries, final_queries):
                    query = connection.queries[i]
                    query_time = float(query['time']) * 1000
                    if query_time > 10:  # 超过10ms的查询
                        logger.warning(f'  - 慢查询 ({query_time:.2f}ms): {query["sql"][:200]}...')

                # 警告查询次数过多
                if query_count > 10:
                    logger.warning(f'  - 查询次数过多 ({query_count})，考虑使用 select_related/prefetch_related')

            return result
        return wrapper


def optimize_queryset(queryset, select_fields=None, prefetch_fields=None):
    """
    优化 QuerySet

    Args:
        queryset: Django QuerySet
        select_fields: 需要 select_related 的字段（ForeignKey, OneToOne）
        prefetch_fields: 需要 prefetch_related 的字段（ManyToMany, 反向ForeignKey）

    Returns:
        优化后的 QuerySet
    """
    if select_fields:
        queryset = queryset.select_related(*select_fields)

    if prefetch_fields:
        queryset = queryset.prefetch_related(*prefetch_fields)

    return queryset


def bulk_create_or_update(model, objects, update_fields=None, unique_field='id'):
    """
    批量创建或更新

    Args:
        model: Django Model
        objects: 对象列表
        update_fields: 需要更新的字段
        unique_field: 唯一标识字段

    Returns:
        创建/更新的对象列表
    """
    if not objects:
        return []

    # 获取现有的对象
    unique_values = [getattr(obj, unique_field) for obj in objects]
    existing = model.objects.filter(**{f'{unique_field}__in': unique_values})
    existing_map = {getattr(obj, unique_field): obj for obj in existing}

    to_create = []
    to_update = []

    for obj in objects:
        unique_value = getattr(obj, unique_field)
        if unique_value in existing_map:
            # 更新现有对象
            existing_obj = existing_map[unique_value]
            if update_fields:
                for field in update_fields:
                    setattr(existing_obj, field, getattr(obj, field))
                to_update.append(existing_obj)
        else:
            # 创建新对象
            to_create.append(obj)

    # 批量操作
    created = []
    if to_create:
        created = model.objects.bulk_create(to_create)

    if to_update:
        model.objects.bulk_update(to_update, update_fields or [])

    return created + to_update


def count_exists(queryset):
    """
    优化的存在性检查
    比 count() 或 exists() 更高效
    """
    return queryset.values('id').first() is not None


def chunked_query(queryset, chunk_size=1000):
    """
    分块查询大数据集

    Args:
        queryset: Django QuerySet
        chunk_size: 每块的大小

    Yields:
        查询结果的块
    """
    offset = 0
    while True:
        chunk = list(queryset[offset:offset + chunk_size])
        if not chunk:
            break
        yield chunk
        offset += chunk_size


def get_or_none(model, **kwargs):
    """
    获取对象或返回 None（不抛出异常）
    """
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


def update_or_create_bulk(model, objects, lookup_fields, update_fields=None):
    """
    批量 update_or_create

    Args:
        model: Django Model
        objects: 字典列表
        lookup_fields: 查询字段列表
        update_fields: 更新字段列表

    Returns:
        (created_count, updated_count)
    """
    created_count = 0
    updated_count = 0

    for obj_data in objects:
        lookup_kwargs = {f: obj_data[f] for f in lookup_fields if f in obj_data}
        update_kwargs = {f: obj_data[f] for f in (update_fields or obj_data.keys()) if f not in lookup_fields}

        _, created = model.objects.update_or_create(
            defaults=update_kwargs,
            **lookup_kwargs
        )

        if created:
            created_count += 1
        else:
            updated_count += 1

    return created_count, updated_count
