from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import json
import os
from django.conf import settings

from user.models import UserInfo
from goods.models import GoodsCategory, Goods, FlashSale, Combo, ComboItem


def admin_required(view_func):
    """管理员权限装饰器"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/manage/login/')
        if not request.user.is_admin:
            return JsonResponse({'code': 403, 'msg': '权限不足，需要管理员权限'})
        return view_func(request, *args, **kwargs)
    return wrapper


def admin_login(request):
    """管理员登录"""
    if request.method == 'GET':
        return render(request, 'manage/login.html')

    data = json.loads(request.body)
    username = data.get('username')
    password = data.get('password')

    user = authenticate(request, username=username, password=password)
    if user is not None:
        if user.is_admin:
            login(request, user)
            return JsonResponse({
                'code': 200,
                'msg': '登录成功',
                'url': '/manage/'
            })
        else:
            return JsonResponse({'code': 403, 'msg': '您不是管理员，无法登录'})
    else:
        return JsonResponse({'code': 400, 'msg': '用户名或密码错误'})


@login_required
@admin_required
def admin_index(request):
    """管理后台首页"""
    goods_count = Goods.objects.filter(is_delete=False).count()
    category_count = GoodsCategory.objects.filter(is_delete=False).count()
    flashsale_count = FlashSale.objects.filter(is_delete=False, is_active=True).count()
    user_count = UserInfo.objects.filter(is_delete=False).count()

    context = {
        'goods_count': goods_count,
        'category_count': category_count,
        'flashsale_count': flashsale_count,
        'user_count': user_count,
    }
    return render(request, 'manage/index.html', context)


@login_required
@admin_required
def goods_list(request):
    """商品列表"""
    goods = Goods.objects.filter(is_delete=False).order_by('-sort', '-create_time')
    return render(request, 'manage/goods_list.html', {'goods_list': goods})


@login_required
@admin_required
def goods_add(request):
    """添加商品"""
    if request.method == 'GET':
        categories = GoodsCategory.objects.filter(is_delete=False)
        return render(request, 'manage/goods_form.html', {
            'categories': categories,
            'action': 'add'
        })

    # POST 请求处理
    name = request.POST.get('name', '').strip()
    category_id = request.POST.get('category_id')
    desc = request.POST.get('desc', '').strip()
    price = request.POST.get('price', 0)
    unit = request.POST.get('unit', '份')
    stock = request.POST.get('stock', 0)
    is_on_sale = request.POST.get('is_on_sale') == 'on'
    is_hot = request.POST.get('is_hot') == 'on'
    is_new = request.POST.get('is_new') == 'on'
    sort = request.POST.get('sort', 0)
    image = request.FILES.get('image')

    # 参数校验
    if not name:
        return JsonResponse({'code': 400, 'msg': '商品名称不能为空'})
    if not category_id:
        return JsonResponse({'code': 400, 'msg': '请选择商品分类'})

    try:
        category = GoodsCategory.objects.get(id=category_id)
    except GoodsCategory.DoesNotExist:
        return JsonResponse({'code': 400, 'msg': '分类不存在'})

    goods = Goods.objects.create(
        name=name,
        category=category,
        desc=desc,
        price=price,
        unit=unit,
        stock=stock,
        is_on_sale=is_on_sale,
        is_hot=is_hot,
        is_new=is_new,
        sort=sort,
        image=image
    )

    return JsonResponse({'code': 200, 'msg': '商品添加成功', 'url': '/manage/goods/'})


@login_required
@admin_required
def goods_edit(request, goods_id):
    """编辑商品"""
    goods = get_object_or_404(Goods, id=goods_id)

    if request.method == 'GET':
        categories = GoodsCategory.objects.filter(is_delete=False)
        return render(request, 'manage/goods_form.html', {
            'goods': goods,
            'categories': categories,
            'action': 'edit'
        })

    # POST 请求处理
    goods.name = request.POST.get('name', goods.name).strip()
    category_id = request.POST.get('category_id')
    goods.desc = request.POST.get('desc', goods.desc).strip()
    goods.price = request.POST.get('price', goods.price)
    goods.unit = request.POST.get('unit', goods.unit)
    goods.stock = request.POST.get('stock', goods.stock)
    goods.is_on_sale = request.POST.get('is_on_sale') == 'on'
    goods.is_hot = request.POST.get('is_hot') == 'on'
    goods.is_new = request.POST.get('is_new') == 'on'
    goods.sort = request.POST.get('sort', goods.sort)

    if category_id:
        try:
            goods.category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            pass

    if 'image' in request.FILES:
        # 删除旧图片
        if goods.image:
            old_image_path = os.path.join(settings.MEDIA_ROOT, str(goods.image))
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        goods.image = request.FILES['image']

    goods.save()
    return JsonResponse({'code': 200, 'msg': '商品更新成功', 'url': '/manage/goods/'})


@login_required
@admin_required
def goods_toggle(request, goods_id):
    """上架/下架商品"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    goods = get_object_or_404(Goods, id=goods_id)
    goods.is_on_sale = not goods.is_on_sale
    goods.save()

    status = '上架' if goods.is_on_sale else '下架'
    return JsonResponse({'code': 200, 'msg': f'商品已{status}'})


@login_required
@admin_required
def goods_delete(request, goods_id):
    """删除商品（软删除）"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    goods = get_object_or_404(Goods, id=goods_id)
    goods.is_delete = True
    goods.save()

    return JsonResponse({'code': 200, 'msg': '商品已删除'})


@login_required
@admin_required
def category_list(request):
    """分类列表"""
    categories = GoodsCategory.objects.filter(is_delete=False).order_by('sort')
    return render(request, 'manage/category_list.html', {'categories': categories})


@login_required
@admin_required
def category_add(request):
    """添加分类"""
    if request.method == 'GET':
        return render(request, 'manage/category_form.html', {'action': 'add'})

    name = request.POST.get('name', '').strip()
    icon = request.POST.get('icon', '📦').strip()
    sort = request.POST.get('sort', 0)

    if not name:
        return JsonResponse({'code': 400, 'msg': '分类名称不能为空'})

    GoodsCategory.objects.create(name=name, icon=icon, sort=sort)
    return JsonResponse({'code': 200, 'msg': '分类添加成功', 'url': '/manage/categories/'})


@login_required
@admin_required
def category_edit(request, cat_id):
    """编辑分类"""
    category = get_object_or_404(GoodsCategory, id=cat_id)

    if request.method == 'GET':
        return render(request, 'manage/category_form.html', {
            'category': category,
            'action': 'edit'
        })

    category.name = request.POST.get('name', category.name).strip()
    category.icon = request.POST.get('icon', category.icon).strip()
    category.sort = request.POST.get('sort', category.sort)
    category.save()

    return JsonResponse({'code': 200, 'msg': '分类更新成功', 'url': '/manage/categories/'})


@login_required
@admin_required
def flashsale_list(request):
    """秒杀活动列表"""
    flashsales = FlashSale.objects.filter(is_delete=False).order_by('-create_time')
    return render(request, 'manage/flashsale_list.html', {'flashsales': flashsales})


@login_required
@admin_required
def flashsale_add(request):
    """添加秒杀活动"""
    if request.method == 'GET':
        goods = Goods.objects.filter(is_delete=False, is_on_sale=True)
        return render(request, 'manage/flashsale_form.html', {
            'goods_list': goods,
            'action': 'add'
        })

    goods_id = request.POST.get('goods_id')
    flash_price = request.POST.get('flash_price')
    stock = request.POST.get('stock')
    start_time = request.POST.get('start_time')
    end_time = request.POST.get('end_time')
    image = request.FILES.get('image')

    try:
        goods = Goods.objects.get(id=goods_id)
    except Goods.DoesNotExist:
        return JsonResponse({'code': 400, 'msg': '商品不存在'})

    FlashSale.objects.create(
        goods=goods,
        flash_price=flash_price,
        original_price=goods.price,
        stock=stock,
        start_time=start_time,
        end_time=end_time,
        image=image
    )

    return JsonResponse({'code': 200, 'msg': '秒杀活动添加成功', 'url': '/manage/flashsale/'})


@login_required
@admin_required
def flashsale_edit(request, sale_id):
    """编辑秒杀活动"""
    flashsale = get_object_or_404(FlashSale, id=sale_id)

    if request.method == 'GET':
        goods = Goods.objects.filter(is_delete=False, is_on_sale=True)
        return render(request, 'manage/flashsale_form.html', {
            'flashsale': flashsale,
            'goods_list': goods,
            'action': 'edit'
        })

    flashsale.flash_price = request.POST.get('flash_price', flashsale.flash_price)
    flashsale.stock = request.POST.get('stock', flashsale.stock)
    flashsale.start_time = request.POST.get('start_time', flashsale.start_time)
    flashsale.end_time = request.POST.get('end_time', flashsale.end_time)
    flashsale.is_active = request.POST.get('is_active') == 'on'

    # 处理图片上传
    if 'image' in request.FILES:
        # 删除旧图片
        if flashsale.image:
            old_image_path = os.path.join(settings.MEDIA_ROOT, str(flashsale.image))
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        flashsale.image = request.FILES['image']

    flashsale.save()

    return JsonResponse({'code': 200, 'msg': '秒杀活动更新成功', 'url': '/manage/flashsale/'})


@login_required
@admin_required
def flashsale_delete(request, sale_id):
    """删除秒杀活动"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    flashsale = get_object_or_404(FlashSale, id=sale_id)
    flashsale.is_delete = True
    flashsale.save()

    return JsonResponse({'code': 200, 'msg': '秒杀活动已删除'})


# ========== 套餐管理 ==========

@login_required
@admin_required
def combo_list(request):
    """套餐列表"""
    combos = Combo.objects.filter(is_delete=False).order_by('-sort', '-create_time')
    # 预加载套餐商品
    for combo in combos:
        combo.items = combo.comboitem_set.select_related('goods').all()
        combo.items_count = combo.items.count()
        combo.original = combo.original_price
    return render(request, 'manage/combo_list.html', {'combos': combos})


@login_required
@admin_required
def combo_add(request):
    """添加套餐"""
    if request.method == 'GET':
        goods = Goods.objects.filter(is_delete=False, is_on_sale=True)
        return render(request, 'manage/combo_form.html', {
            'goods_list': goods,
            'action': 'add'
        })

    name = request.POST.get('name', '').strip()
    desc = request.POST.get('desc', '').strip()
    price = request.POST.get('price', 0)
    sort = request.POST.get('sort', 0)
    is_active = request.POST.get('is_active') == 'on'
    image = request.FILES.get('image')

    if not name:
        return JsonResponse({'code': 400, 'msg': '套餐名称不能为空'})

    # 获取套餐商品列表
    goods_ids = request.POST.getlist('goods_ids[]')
    quantities = request.POST.getlist('quantities[]')

    if not goods_ids:
        return JsonResponse({'code': 400, 'msg': '请至少添加一个套餐商品'})

    combo = Combo.objects.create(
        name=name,
        desc=desc,
        price=price,
        sort=sort,
        is_active=is_active,
        image=image,
    )

    for gid, qty in zip(goods_ids, quantities):
        try:
            goods = Goods.objects.get(id=int(gid))
            ComboItem.objects.create(
                combo=combo,
                goods=goods,
                quantity=int(qty),
            )
        except (Goods.DoesNotExist, ValueError):
            continue

    return JsonResponse({'code': 200, 'msg': '套餐添加成功', 'url': '/manage/combo/'})


@login_required
@admin_required
def combo_edit(request, combo_id):
    """编辑套餐"""
    combo = get_object_or_404(Combo, id=combo_id)

    if request.method == 'GET':
        goods = Goods.objects.filter(is_delete=False, is_on_sale=True)
        combo_items = combo.comboitem_set.select_related('goods').all()
        return render(request, 'manage/combo_form.html', {
            'combo': combo,
            'combo_items': combo_items,
            'goods_list': goods,
            'action': 'edit'
        })

    combo.name = request.POST.get('name', combo.name).strip()
    combo.desc = request.POST.get('desc', combo.desc).strip()
    combo.price = request.POST.get('price', combo.price)
    combo.sort = request.POST.get('sort', combo.sort)
    combo.is_active = request.POST.get('is_active') == 'on'

    if 'image' in request.FILES:
        if combo.image:
            old_image_path = os.path.join(settings.MEDIA_ROOT, str(combo.image))
            if os.path.exists(old_image_path):
                os.remove(old_image_path)
        combo.image = request.FILES['image']

    combo.save()

    # 更新套餐商品：先删除旧的，再创建新的
    goods_ids = request.POST.getlist('goods_ids[]')
    quantities = request.POST.getlist('quantities[]')

    if goods_ids:
        combo.comboitem_set.all().delete()
        for gid, qty in zip(goods_ids, quantities):
            try:
                goods = Goods.objects.get(id=int(gid))
                ComboItem.objects.create(
                    combo=combo,
                    goods=goods,
                    quantity=int(qty),
                )
            except (Goods.DoesNotExist, ValueError):
                continue

    return JsonResponse({'code': 200, 'msg': '套餐更新成功', 'url': '/manage/combo/'})


@login_required
@admin_required
def combo_delete(request, combo_id):
    """删除套餐"""
    if request.method != 'POST':
        return JsonResponse({'code': 405, 'msg': '请求方法不允许'})

    combo = get_object_or_404(Combo, id=combo_id)
    combo.is_delete = True
    combo.save()

    return JsonResponse({'code': 200, 'msg': '套餐已删除'})
