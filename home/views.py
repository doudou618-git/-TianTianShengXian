from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json

from goods.models import GoodsCategory, Goods, FlashSale, Combo


def home(request):
    """首页"""
    return render(request, 'home.html')


def get_home_data(request):
    """获取首页数据API"""
    # 获取商品分类
    categories = GoodsCategory.objects.filter(is_delete=False).order_by('sort')

    cat_list = []
    for c in categories:
        cat_list.append({
            'id': c.id,
            'name': c.name,
            'icon': c.icon,
        })

    # 获取所有上架商品
    goods = Goods.objects.filter(
        is_delete=False,
        is_on_sale=True
    ).select_related('category').order_by('-sort', '-create_time')

    goods_list = []
    for g in goods:
        goods_list.append({
            'id': g.id,
            'cat': g.category_id,
            'name': g.name,
            'desc': g.desc,
            'price': float(g.price),
            'unit': g.unit,
            'stock': g.stock,
            'sales': g.sales,
            'image': g.image_url,
            'emoji': g.category.icon,
            'badge': 'hot' if g.is_hot else ('new' if g.is_new else ''),
            'specs': [s.name for s in g.specs.all()]
        })

    # 获取进行中的秒杀活动
    now = timezone.now()
    ongoing_sales = FlashSale.objects.filter(
        is_delete=False,
        is_active=True,
        start_time__lte=now,
        end_time__gte=now
    ).select_related('goods', 'goods__category')

    # 获取即将开始的秒杀活动
    upcoming_sales = FlashSale.objects.filter(
        is_delete=False,
        is_active=True,
        start_time__gt=now
    ).select_related('goods', 'goods__category').order_by('start_time')

    def build_flash_list(sales):
        result = []
        for s in sales:
            # 将UTC时间转换为本地时间
            start_local = timezone.localtime(s.start_time)
            end_local = timezone.localtime(s.end_time)
            result.append({
                'id': s.goods.id,
                'flash_id': s.id,
                'name': s.goods.name,
                'desc': s.goods.desc,
                'flash_price': float(s.flash_price),
                'original_price': float(s.original_price),
                'unit': s.goods.unit,
                'sold': s.progress,
                'image': s.image_url,
                'emoji': s.goods.category.icon,
                'start_time': start_local.strftime('%Y-%m-%d %H:%M'),
                'end_time': end_local.strftime('%Y-%m-%d %H:%M'),
            })
        return result

    # 获取套餐
    combos = Combo.objects.filter(
        is_delete=False, is_active=True
    ).prefetch_related('comboitem_set__goods', 'comboitem_set__goods__category').order_by('-sort', '-create_time')[:8]

    combo_list = []
    for c in combos:
        items = []
        original_total = 0
        for ci in c.comboitem_set.all():
            items.append({
                'name': ci.goods.name,
                'quantity': ci.quantity,
                'unit': ci.goods.unit,
                'image': ci.goods.image_url,
                'emoji': ci.goods.category.icon,
            })
            original_total += float(ci.goods.price) * ci.quantity
        combo_list.append({
            'id': c.id,
            'name': c.name,
            'desc': c.desc,
            'price': float(c.price),
            'original_price': original_total,
            'image': c.image_url,
            'items': items,
        })

    return JsonResponse({
        'code': 200,
        'msg': '获取成功',
        'data': {
            'categories': cat_list,
            'goods': goods_list,
            'flash_sales': build_flash_list(ongoing_sales),
            'upcoming_sales': build_flash_list(upcoming_sales),
            'combos': combo_list,
        }
    })


@login_required
def add_address_api(request):
    """新建地址API - 保留兼容性，实际使用 user 应用的 API"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    from user.models import Address

    data = json.loads(request.body)
    receiver_name = data.get('receiver_name', '').strip()
    receiver_mobile = data.get('receiver_mobile', '').strip()
    address = data.get('address', '').strip()
    is_default = data.get('is_default', False)

    # 参数校验
    if not receiver_name or len(receiver_name) < 2:
        return JsonResponse({'code': 400, 'msg': '请输入有效的收件人姓名'})
    if not receiver_mobile or not receiver_mobile.isdigit() or len(receiver_mobile) != 11:
        return JsonResponse({'code': 400, 'msg': '请输入正确的11位手机号码'})
    if not address or len(address) < 5:
        return JsonResponse({'code': 400, 'msg': '请输入完整的详细地址'})

    # 如果设为默认，先取消其他默认地址
    if is_default:
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)

    Address.objects.create(
        user=request.user,
        receiver_name=receiver_name,
        receiver_mobile=receiver_mobile,
        address=address,
        is_default=is_default,
    )

    return JsonResponse({'code': 200, 'msg': '地址添加成功'})
