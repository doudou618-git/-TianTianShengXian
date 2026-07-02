import json
import logging
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage
from django.utils import timezone
from django.db.models import Prefetch
from datetime import timedelta

from .models import Order, OrderGoods
from goods.models import Goods, FlashSale, Combo
from utils import redis_helper

logger = logging.getLogger('order')


@login_required
def get_cart(request):
    """获取购物车列表（从Redis读取）"""
    cart_data = redis_helper.get_cart_items(request.user.id)

    items = []
    total_price = 0
    selected_count = 0

    if cart_data:
        goods_ids = list(cart_data.keys())
        goods_map = {g.id: g for g in Goods.objects.filter(id__in=goods_ids, is_delete=False, is_on_sale=True)}

        # 查询进行中的秒杀活动
        now = timezone.now()
        flash_sales = FlashSale.objects.filter(
            goods_id__in=goods_ids,
            is_delete=False,
            is_active=True,
            start_time__lte=now,
            end_time__gte=now,
        )
        flash_price_map = {fs.goods_id: float(fs.flash_price) for fs in flash_sales}

        # 查询套餐关联信息
        combo_cart_info = redis_helper.get_combo_cart_info(request.user.id)
        # 检查哪些套餐是完整的（所有商品都在购物车中且数量足够）
        complete_combos = {}  # goods_id -> combo_id (标记属于完整套餐的商品)
        combo_prices = {}     # combo_id -> combo_price
        for combo_id, cinfo in combo_cart_info.items():
            is_complete = True
            for item in cinfo['items']:
                gid = item['goods_id']
                required_qty = item['quantity']
                cart_item = cart_data.get(gid)
                if not cart_item or cart_item['quantity'] < required_qty:
                    is_complete = False
                    break
            if is_complete:
                combo_prices[combo_id] = cinfo['combo_price']
                # 计算套餐内商品原价总和，用于按比例分配套餐价
                original_total = 0
                for item in cinfo['items']:
                    g = goods_map.get(item['goods_id'])
                    if g:
                        original_total += float(g.price) * item['quantity']
                # 按比例分配套餐价到各商品
                for item in cinfo['items']:
                    gid = item['goods_id']
                    g = goods_map.get(gid)
                    if g and original_total > 0:
                        item_original = float(g.price) * item['quantity']
                        ratio = item_original / original_total
                        allocated_price = cinfo['combo_price'] * ratio / item['quantity']
                        complete_combos[gid] = {
                            'combo_id': combo_id,
                            'unit_price': round(allocated_price, 2),
                        }

        for goods_id, cart_info in cart_data.items():
            goods = goods_map.get(goods_id)
            if not goods:
                continue

            # 价格优先级：秒杀 > 套餐 > 原价
            if goods_id in flash_price_map:
                goods_price = flash_price_map[goods_id]
                is_flash = True
                is_combo = False
            elif goods_id in complete_combos:
                goods_price = complete_combos[goods_id]['unit_price']
                is_flash = False
                is_combo = True
            else:
                goods_price = float(goods.price)
                is_flash = False
                is_combo = False

            subtotal = goods_price * cart_info['quantity']

            items.append({
                'goods_id': goods.id,
                'name': goods.name,
                'desc': goods.desc,
                'price': goods_price,
                'original_price': float(goods.price),
                'image': goods.image_url,
                'quantity': cart_info['quantity'],
                'selected': cart_info['selected'],
                'subtotal': subtotal,
                'is_flash': is_flash,
                'is_combo': is_combo,
            })

            if cart_info['selected']:
                total_price += subtotal
                selected_count += cart_info['quantity']

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'items': items,
            'total_price': total_price,
            'total_count': sum(item['quantity'] for item in items),
            'selected_count': selected_count,
        }
    })


@login_required
def add_to_cart(request):
    """添加商品到购物车（存入Redis）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '请求数据格式错误'})

    goods_id = data.get('goods_id')
    quantity = data.get('quantity', 1)

    if not goods_id:
        return JsonResponse({'code': 400, 'msg': '商品ID不能为空'})

    try:
        goods = Goods.objects.get(id=goods_id, is_delete=False, is_on_sale=True)
    except Goods.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '商品不存在或已下架'})

    if quantity < 1:
        return JsonResponse({'code': 400, 'msg': '数量不能小于1'})

    current_qty, created = redis_helper.add_to_cart(request.user.id, goods_id, quantity)

    return JsonResponse({
        'code': 200,
        'msg': '添加成功',
        'data': {
            'goods_id': goods_id,
            'quantity': current_qty,
        }
    })


@login_required
def update_cart(request, goods_id):
    """更新购物车商品数量（Redis）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '请求数据格式错误'})

    quantity = data.get('quantity')
    selected = data.get('selected')

    if quantity is not None and quantity < 1:
        return JsonResponse({'code': 400, 'msg': '数量不能小于1'})

    result = redis_helper.set_cart_item(request.user.id, goods_id, quantity=quantity, selected=selected)
    if result is None:
        return JsonResponse({'code': 404, 'msg': '购物车商品不存在'})

    return JsonResponse({
        'code': 200,
        'msg': '更新成功',
        'data': {
            'goods_id': goods_id,
            'quantity': result['quantity'],
            'selected': result['selected'],
        }
    })


@login_required
def delete_cart(request, goods_id):
    """删除购物车商品（Redis）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    redis_helper.remove_from_cart(request.user.id, goods_id)
    return JsonResponse({'code': 200, 'msg': '删除成功'})


@login_required
def select_all_cart(request):
    """全选/取消全选购物车（Redis）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '请求数据格式错误'})

    selected = data.get('selected', True)
    redis_helper.select_all_cart(request.user.id, selected=selected)

    return JsonResponse({
        'code': 200,
        'msg': '操作成功'
    })


@login_required
def clear_cart(request):
    """清空购物车（Redis）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    redis_helper.clear_cart(request.user.id)
    redis_helper.clear_combo_cart(request.user.id)

    return JsonResponse({
        'code': 200,
        'msg': '清空成功'
    })


@login_required
def add_combo_to_cart(request):
    """将套餐加入购物车"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '请求数据格式错误'})

    combo_id = data.get('combo_id')
    if not combo_id:
        return JsonResponse({'code': 400, 'msg': '套餐ID不能为空'})

    try:
        combo = Combo.objects.prefetch_related('comboitem_set__goods').get(
            id=combo_id, is_delete=False, is_active=True
        )
    except Combo.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '套餐不存在或已下架'})

    items = []
    for ci in combo.comboitem_set.all():
        items.append({
            'goods_id': ci.goods.id,
            'quantity': ci.quantity,
        })

    redis_helper.add_combo_to_cart(
        request.user.id,
        combo.id,
        float(combo.price),
        items,
    )

    return JsonResponse({
        'code': 200,
        'msg': '套餐添加成功',
    })


# ========== 订单相关 ==========

@login_required
def create_order(request):
    """从购物车创建订单（从Redis读取购物车）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'msg': '请求数据格式错误'})

    goods_ids = data.get('goods_ids', [])
    receiver_name = data.get('receiver_name', '')
    receiver_mobile = data.get('receiver_mobile', '')
    receiver_address = data.get('receiver_address', '')
    remark = data.get('remark', '')

    if not goods_ids:
        return JsonResponse({'code': 400, 'msg': '请选择商品'})

    # 从Redis获取购物车数据
    cart_data = redis_helper.get_cart_items(request.user.id)
    if not cart_data:
        return JsonResponse({'code': 400, 'msg': '购物车为空'})

    # 获取商品信息
    goods_map = {g.id: g for g in Goods.objects.filter(id__in=goods_ids, is_delete=False, is_on_sale=True)}
    if not goods_map:
        return JsonResponse({'code': 400, 'msg': '没有找到有效商品'})

    # 查询进行中的秒杀活动
    now = timezone.now()
    flash_sales = FlashSale.objects.filter(
        goods_id__in=goods_ids,
        is_delete=False,
        is_active=True,
        start_time__lte=now,
        end_time__gte=now,
    )
    flash_price_map = {fs.goods_id: float(fs.flash_price) for fs in flash_sales}

    # 查询套餐关联信息，检查完整套餐
    combo_cart_info = redis_helper.get_combo_cart_info(request.user.id)
    combo_price_map = {}  # goods_id -> unit_price (按比例分配的套餐价)
    for combo_id, cinfo in combo_cart_info.items():
        is_complete = True
        for item in cinfo['items']:
            gid = item['goods_id']
            required_qty = item['quantity']
            cart_item = cart_data.get(gid)
            if not cart_item or cart_item['quantity'] < required_qty:
                is_complete = False
                break
        if is_complete:
            original_total = 0
            for item in cinfo['items']:
                g = goods_map.get(item['goods_id'])
                if g:
                    original_total += float(g.price) * item['quantity']
            if original_total > 0:
                for item in cinfo['items']:
                    gid = item['goods_id']
                    g = goods_map.get(gid)
                    if g:
                        item_original = float(g.price) * item['quantity']
                        ratio = item_original / original_total
                        allocated_price = cinfo['combo_price'] * ratio / item['quantity']
                        combo_price_map[gid] = round(allocated_price, 2)

    # 创建订单
    order = Order.objects.create(
        user=request.user,
        receiver_name=receiver_name,
        receiver_mobile=receiver_mobile,
        receiver_address=receiver_address,
        remark=remark,
    )

    total_amount = 0
    ordered_goods_ids = []
    for gid in goods_ids:
        goods = goods_map.get(gid)
        cart_info = cart_data.get(gid)
        if not goods or not cart_info:
            continue

        quantity = cart_info['quantity']
        # 价格优先级：秒杀 > 套餐 > 原价
        unit_price = flash_price_map.get(gid, combo_price_map.get(gid, float(goods.price)))
        OrderGoods.objects.create(
            order=order,
            goods=goods,
            quantity=quantity,
            price=unit_price,
        )
        total_amount += unit_price * quantity
        ordered_goods_ids.append(gid)

    # 更新订单总金额
    order.total_amount = total_amount
    order.save()

    # 从Redis购物车中删除已下单的商品
    for gid in ordered_goods_ids:
        redis_helper.remove_from_cart(request.user.id, gid)

    return JsonResponse({
        'code': 200,
        'msg': '下单成功',
        'data': {
            'order_id': order.id,
            'order_no': order.order_no,
            'total_amount': float(order.total_amount),
        }
    })


@login_required
def get_orders(request):
    """获取订单列表（支持筛选和分页）- 已优化查询"""
    user = request.user

    # 批量取消已过期的待付款订单（单次查询）
    now = timezone.now()
    expired_count = Order.objects.filter(
        user=user,
        status='pending',
        is_delete=False,
        expire_time__isnull=False,
        expire_time__lte=now
    ).update(status='cancelled')

    if expired_count > 0:
        logger.info(f'用户 {user.username} 自动取消 {expired_count} 个过期订单')

    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    page_size = request.GET.get('page_size', 10)

    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    try:
        page_size = int(page_size)
    except (ValueError, TypeError):
        page_size = 10

    # 限制每页数量
    if page_size > 20:
        page_size = 20

    # 优化查询：使用 select_related 和 prefetch_related
    # 使用 Prefetch 对象更精确地控制预加载
    goods_prefetch = Prefetch(
        'goods_items',
        queryset=OrderGoods.objects.select_related('goods').only(
            'id', 'goods__id', 'goods__name', 'goods__image',
            'price', 'quantity'
        )
    )

    orders = Order.objects.filter(
        user=user,
        is_delete=False
    ).prefetch_related(goods_prefetch).only(
        'id', 'order_no', 'total_amount', 'status',
        'receiver_name', 'receiver_mobile', 'receiver_address',
        'remark', 'create_time', 'expire_time'
    )

    # 按状态筛选
    if status and status != 'all':
        orders = orders.filter(status=status)

    # 分页
    paginator = Paginator(orders, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # 构建订单数据
    order_list = []
    for order in page_obj:
        goods_items = []
        for item in order.goods_items.all():
            goods_items.append({
                'id': item.id,
                'goods_id': item.goods.id,
                'name': item.goods.name,
                'image': item.goods.image_url,
                'price': float(item.price),
                'quantity': item.quantity,
                'subtotal': float(item.price) * item.quantity,
            })

        order_list.append({
            'id': order.id,
            'order_no': order.order_no,
            'total_amount': float(order.total_amount),
            'status': order.status,
            'status_display': order.get_status_display(),
            'receiver_name': order.receiver_name,
            'receiver_mobile': order.receiver_mobile,
            'receiver_address': order.receiver_address,
            'remark': order.remark,
            'create_time': order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'expire_time': order.expire_time.isoformat() if order.expire_time else None,
            'goods_items': goods_items,
        })

    # 优化：使用单次聚合查询统计各状态订单数量
    from django.db.models import Count, Case, When, IntegerField

    status_counts_result = Order.objects.filter(
        user=user,
        is_delete=False
    ).aggregate(
        all_count=Count('id'),
        pending_count=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
        paid_count=Count(Case(When(status='paid', then=1), output_field=IntegerField())),
        shipped_count=Count(Case(When(status='shipped', then=1), output_field=IntegerField())),
        completed_count=Count(Case(When(status='completed', then=1), output_field=IntegerField())),
        cancelled_count=Count(Case(When(status='cancelled', then=1), output_field=IntegerField())),
    )

    status_counts = {
        'all': status_counts_result['all_count'],
        'pending': status_counts_result['pending_count'],
        'paid': status_counts_result['paid_count'],
        'shipped': status_counts_result['shipped_count'],
        'completed': status_counts_result['completed_count'],
        'cancelled': status_counts_result['cancelled_count'],
    }

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'list': order_list,
            'total': paginator.count,
            'page': page_obj.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'status_counts': status_counts,
        }
    })


@login_required
def get_order_detail(request, order_id):
    """获取订单详情"""
    try:
        order = Order.objects.prefetch_related('goods_items__goods').get(
            id=order_id,
            user=request.user,
            is_delete=False
        )
    except Order.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '订单不存在'})

    goods_items = []
    for item in order.goods_items.all():
        goods_items.append({
            'id': item.id,
            'goods_id': item.goods.id,
            'name': item.goods.name,
            'image': item.goods.image_url,
            'price': float(item.price),
            'quantity': item.quantity,
            'subtotal': float(item.price) * item.quantity,
        })

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'id': order.id,
            'order_no': order.order_no,
            'total_amount': float(order.total_amount),
            'status': order.status,
            'status_display': order.get_status_display(),
            'receiver_name': order.receiver_name,
            'receiver_mobile': order.receiver_mobile,
            'receiver_address': order.receiver_address,
            'remark': order.remark,
            'create_time': order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'goods_items': goods_items,
        }
    })


@login_required
def pay_order(request, order_id):
    """模拟付款（将订单状态改为已付款）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        order = Order.objects.get(id=order_id, user=request.user, is_delete=False)
    except Order.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '订单不存在'})

    if order.status != 'pending':
        return JsonResponse({'code': 400, 'msg': '该订单状态无法付款'})

    order.status = 'paid'
    order.save()

    return JsonResponse({
        'code': 200,
        'msg': '付款成功'
    })


@login_required
def receive_order(request, order_id):
    """确认收货"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        order = Order.objects.get(id=order_id, user=request.user, is_delete=False)
    except Order.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '订单不存在'})

    if order.status != 'shipped':
        return JsonResponse({'code': 400, 'msg': '该订单状态无法确认收货'})

    order.status = 'completed'
    order.save()

    return JsonResponse({
        'code': 200,
        'msg': '确认收货成功'
    })


@login_required
def cancel_order(request, order_id):
    """取消订单"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        order = Order.objects.get(id=order_id, user=request.user, is_delete=False)
    except Order.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '订单不存在'})

    if order.status not in ('pending', 'paid'):
        return JsonResponse({'code': 400, 'msg': '该订单状态无法取消'})

    order.status = 'cancelled'
    order.save()

    return JsonResponse({
        'code': 200,
        'msg': '取消成功'
    })


@login_required
def set_order_expire(request, order_id):
    """设置订单30分钟过期时间（取消支付时调用）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        order = Order.objects.get(id=order_id, user=request.user, is_delete=False)
    except Order.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '订单不存在'})

    if order.status != 'pending':
        return JsonResponse({'code': 400, 'msg': '该订单状态无法设置过期时间'})

    order.expire_time = timezone.now() + timedelta(minutes=30)
    order.save()

    return JsonResponse({
        'code': 200,
        'msg': '设置成功'
    })


@login_required
def payment_page(request, order_id):
    """支付页面"""
    order = get_object_or_404(Order, id=order_id, user=request.user, is_delete=False)

    # 只有待付款状态的订单才能进入支付页面
    if order.status != 'pending':
        return redirect('/home/')

    goods_items = order.goods_items.select_related('goods').all()

    return render(request, 'order/payment.html', {
        'order': order,
        'goods_items': goods_items,
    })


@login_required
def confirm_payment(request, order_id):
    """确认支付（模拟支付成功）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    try:
        order = Order.objects.get(id=order_id, user=request.user, is_delete=False)
    except Order.DoesNotExist:
        return JsonResponse({'code': 404, 'msg': '订单不存在'})

    if order.status != 'pending':
        return JsonResponse({'code': 400, 'msg': '该订单状态无法支付'})

    # 获取支付方式
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}

    payment_method = data.get('payment_method', 'mock')

    # 模拟支付成功，更新订单状态
    order.status = 'paid'
    order.save()

    return JsonResponse({
        'code': 200,
        'msg': '支付成功',
        'data': {
            'order_id': order.id,
            'order_no': order.order_no,
            'payment_method': payment_method,
        }
    })
